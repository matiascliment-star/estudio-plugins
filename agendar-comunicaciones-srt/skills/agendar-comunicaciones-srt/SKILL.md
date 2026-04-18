---
name: agendar-comunicaciones-srt
description: >
  Agendamiento automático diario (L-V 9am AR) de comunicaciones de Mi Ventanilla
  SRT. Cubre 5 tipos con plazo procesal o fecha de audiencia: (1) Dictamen Médico
  3 días hábiles, (2) ITM 3 días hábiles, (3) Constancia de Orden de Estudio 5
  días hábiles para contestar intimación, (4) Citación a Examen Físico agenda la
  fecha de audiencia + aviso al cliente, (5) Citación al Servicio de Homologación
  agenda fecha + link Teams + aviso al cliente. Lee el texto extraído de los PDFs
  (columna `adjuntos_miventanilla.texto_extraido`). Marca cada comunicación como
  procesada. Reporte diario al grupo "Claude SRT". Triggers: "agendar
  comunicaciones SRT", "procesar comunicaciones", "mi ventanilla".
version: 1.2.0
---

# Agendar Comunicaciones SRT — v1.2.0

## OBJETIVO

Chequeo diario (L-V 9am AR) de comunicaciones nuevas de Mi Ventanilla con plazo procesal o audiencia. Crea eventos en Google Calendar, agenda fechas de audiencias, manda avisos a clientes cuando corresponde, y reporta al grupo WhatsApp "Claude SRT".

## TIPOS CUBIERTOS

| Tipo | Plazo / Acción | Calendar | Aviso al cliente |
|------|----------------|----------|------------------|
| Dictamen Médico | 3 días hábiles impugnar | Principal | No |
| ITM | 3 días hábiles impugnar | Principal | No |
| Constancia Orden Estudio (intimación) | 5 días hábiles contestar | Principal | No |
| Constancia Orden Estudio (al cliente) | Fecha estudio directa | Principal | **Sí** (cálido) |
| Citación Examen Físico | Fecha audiencia directa | Principal | **Sí** (cálido) |
| Citación Homologación (Teams) | Fecha audiencia directa | Principal | **Sí** (con link) |
| **Acto Administrativo (Clausura)** | **15d CABA / 15+90d Pcia** | **✱ Vencimientos** | No (el cliente no se entera) |

Nota: las clausuras también las verifica el skill `control-clausuras-srt` los lunes. Acá se **crean diariamente** apenas llegan, el otro skill **controla** que estén bien agendadas. Dos IAs, un fiscaliza lo de la otra.

## REGLAS

- **Día 1** = día hábil SIGUIENTE a la `fecha_notificacion`
- **Feriados AR**: tabla `feriados_ar` en Supabase (Paso 0)
- **Idempotencia**: skip si `comunicaciones_miventanilla.agendado_en_calendar_at IS NOT NULL`
- **Ventana**: últimos 30 días (para plazos) / 60 días (para audiencias — a veces agendan con anticipación)
- **Nunca** modificar eventos existentes

## CONSTANTES

- **Supabase project_id**: `wdgdbbcwcrirpnfdmykh`
- **Calendario**: `flirteador84@gmail.com` (principal)
- **WhatsApp grupo reporte**: `120363407310742955@g.us` (Claude SRT)

## WORKFLOW

### Paso 0 — Feriados

```sql
SELECT fecha::text FROM feriados_ar
WHERE fecha BETWEEN (now() - interval '30 days')::date AND (now() + interval '120 days')::date
ORDER BY fecha;
```
→ `/tmp/feriados.json`

### Paso 1 — Comunicaciones pendientes con texto

```sql
SELECT m.id AS comunicacion_id,
  m.srt_expediente_nro AS srt,
  (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date::text AS fecha_notif,
  m.tipo_comunicacion,
  m.detalle,                         -- necesario para detectar Clausura
  c.nombre AS nombre_actor,
  c.comision_medica AS cm,          -- necesario para clausuras CABA vs Pcia
  c.wa_chat_id AS grupo_cliente_wa,  -- chat_id del grupo WhatsApp con el cliente
  a.texto_extraido
FROM comunicaciones_miventanilla m
LEFT JOIN casos_srt c ON c.numero_srt = m.srt_expediente_nro
LEFT JOIN adjuntos_miventanilla a ON a.comunicacion_id = m.id
WHERE m.tipo_comunicacion IN (
    'Notificación de Dictamen Médico',
    'Notificación de ITM',
    'Notificación de Constancia de Orden de Estudio',
    'Notificación de Citación',
    'Notificación de Citación al Servicio de Homologación',
    'Notificación de Acto Administrativo'  -- clausuras (filtradas por detalle en el procesador)
  )
  AND m.agendado_en_calendar_at IS NULL
  AND m.fecha_notificacion >= (now() - interval '60 days')
ORDER BY m.fecha_notificacion ASC;
```

→ `/tmp/comunicaciones.json`

### Paso 2 — Procesar por tipo

Para cada comunicación, determinar:
- **fecha_evento**: fecha del evento en Calendar
- **summary**: título del evento
- **aviso_cliente_text**: texto del WA al cliente (o None)

```python
import json, re
from datetime import date, timedelta

FERIADOS = set(json.load(open('/tmp/feriados.json')))

def sumar_dh(fi, n):
    d = fi; c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() >= 5: continue
        if d.isoformat() in FERIADOS: continue
        c += 1
    return d

DIAS_SEM = {0:'Lunes',1:'Martes',2:'Miércoles',3:'Jueves',4:'Viernes',5:'Sábado',6:'Domingo'}
STOP_APELLIDO = {'DE','LA','DEL','LOS','LAS','VAN','VON','Y'}

def primer_nombre(nombre_actor):
    """Extrae un primer nombre razonable de 'APELLIDO NOMBRE1 NOMBRE2'.
    Heurística: skip apellido (1ra palabra) y stopwords de partícula; toma la siguiente.
    No es infalible con apellidos compuestos (ej: 'ARANDA PEREIRA OSCAR'→'Pereira'),
    pero funciona para la mayoría. Si falla, queda con apellido segundo — no ofensivo."""
    if not nombre_actor: return ''
    # Quitar sufijos con dígitos tipo "2 ACC", "3ºACC"
    partes = [p for p in nombre_actor.strip().split() if not any(ch.isdigit() for ch in p)]
    if len(partes) <= 1:
        return partes[0].title() if partes else ''
    i = 1
    while i < len(partes) and partes[i].upper() in STOP_APELLIDO:
        i += 1
    return partes[i].title() if i < len(partes) else partes[0].title()

def proc_dictamen_itm(c, tipo_label):
    notif = date.fromisoformat(c['fecha_notif'])
    fecha_ev = sumar_dh(notif, 3)
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- VENCE IMPUGNAR {tipo_label}",
        'aviso_cliente': None,
    }

def proc_constancia_orden_estudio(c):
    """Dos variantes según contenido del PDF:
    1) Intimación al abogado/trabajador (pide describir accidente + docs) → agenda 5 hábiles
    2) Orden de estudio médico al cliente (con fecha/hora/dirección prestador) → aviso al grupo + agenda fecha
    """
    t = c.get('texto_extraido') or ''
    notif = date.fromisoformat(c['fecha_notif'])

    # Caso 2: orden de estudio real al cliente
    if 'Fecha/Hora de Prestación' in t or 'Fecha/Hora de Prestac' in t:
        m_fh = re.search(r'Fecha/Hora de Prestac[^:]*:\s*(\d{2}/\d{2}/\d{4})\s*[-\s]+\s*(\d{1,2}[:.]?\d{2})', t)
        if not m_fh: return None
        fecha_str = m_fh.group(1)
        hora_str = m_fh.group(2).replace('.', ':')
        fecha_ev = date(*[int(x) for x in reversed(fecha_str.split('/'))])
        # Estudios solicitados (texto después de "ESTUDIOS SOLICITADOS" hasta "Fecha/Hora")
        m_est = re.search(r'ESTUDIOS\s+SOLICITADOS[^\n]*\n(.*?)(?:Fecha/Hora|a\s*Fecha/Hora)', t, re.S | re.I)
        estudios_raw = (m_est.group(1).strip() if m_est else '')
        estudios = re.sub(r'\s+', ' ', estudios_raw)[:180]
        # Dirección: "Lugar donde se efectuarán los estudios: XXX"
        m_dir = re.search(r'Lugar\s+donde\s+se\s+efectuar[aá]n\s+los?\s+estudios?[:\s]+([A-Z0-9\s\.\-,/]+?)(?:Local|Código|Provincia|Tel)', t, re.S | re.I)
        direccion = re.sub(r'\s+', ' ', (m_dir.group(1).strip() if m_dir else '')).strip()
        m_loc = re.search(r'Localidad[^:]*:\s*([A-Z\s]+?)\s*/', t)
        localidad = (m_loc.group(1).strip() if m_loc else '')
        dir_completa = f"{direccion}, {localidad}".strip(', ')
        dia_sem = DIAS_SEM[fecha_ev.weekday()]
        saludo = f"Hola {primer_nombre(c['nombre_actor'])}!\n" if c.get('nombre_actor') else ''
        aviso = (f"{saludo}*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
                 f"para *{estudios}*.  *DIRECCION:* {dir_completa or '(ver PDF)'}")
        return {
            'fecha_evento': fecha_ev,
            'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- ESTUDIO SRT {hora_str} {estudios[:60]}",
            'aviso_cliente': aviso,
            'hora': hora_str,
            'direccion': dir_completa,
            'estudios': estudios,
            'subtipo': 'orden_estudio_cliente',
        }

    # Caso 1: intimación al abogado (default si no hay Fecha/Hora Prestación)
    fecha_ev = sumar_dh(notif, 5)
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- VENCE CONTESTAR INTIMACION SRT",
        'aviso_cliente': None,
        'subtipo': 'intimacion_abogado',
    }

def proc_citacion_examen(c):
    """Parsear: fecha DD/MM/YYYY, hora HH:MM, dirección completa, tipo estudio."""
    t = c.get('texto_extraido') or ''
    m_fecha = re.search(r'(\d{2}/\d{2}/\d{4})\s*a\s*las?\s*(\d{1,2}[:.]?\d{2})', t)
    if not m_fecha: return None
    fecha_str = m_fecha.group(1)
    hora_str = m_fecha.group(2).replace('.', ':')
    fecha_ev = date(*[int(x) for x in reversed(fecha_str.split('/'))])
    m_dir = re.search(r'sito\s+en\s+la\s+calle\s+(.+?)\s*,?\s*a\s+fin\s+de\s+realizar', t, re.S | re.I)
    direccion = re.sub(r'\s+', ' ', m_dir.group(1).strip()) if m_dir else '(ver PDF en Mi Ventanilla)'
    m_tipo = re.search(r'fin de realizar\s+la?\s+([^\.\n]+)', t, re.I)
    tipo_estudio = (m_tipo.group(1).strip() if m_tipo else 'Examen Físico').rstrip('.').strip()
    dia_sem = DIAS_SEM[fecha_ev.weekday()]
    saludo = f"Hola {primer_nombre(c['nombre_actor'])}!\n" if c.get('nombre_actor') else ''
    aviso = (f"{saludo}*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
             f"para *{tipo_estudio}*.  *DIRECCION:* {direccion}")
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- {tipo_estudio.upper()} SRT {hora_str}",
        'aviso_cliente': aviso, 'hora': hora_str, 'direccion': direccion,
    }

def proc_citacion_homologacion(c):
    t = c.get('texto_extraido') or ''
    m_fecha = re.search(r'virtual el d[ií]a\s+(\d{2}/\d{2}/\d{4})\s*a las\s+(\d{1,2}[:.]?\d{2})', t)
    if not m_fecha: return None
    fecha_str = m_fecha.group(1); hora_str = m_fecha.group(2).replace('.', ':')
    fecha_ev = date(*[int(x) for x in reversed(fecha_str.split('/'))])
    m_link = re.search(r'https://go\.srt\.gob\.ar/\S+', t)
    link = m_link.group(0) if m_link else ''
    dia_sem = DIAS_SEM[fecha_ev.weekday()]
    saludo = f"Hola {primer_nombre(c['nombre_actor'])}!\n" if c.get('nombre_actor') else ''
    aviso = (f"{saludo}*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
             f"*Audiencia Homologación SRT* (virtual Teams): {link}".strip())
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- AUDIENCIA HOMOLOGACION SRT {hora_str} (Teams)",
        'aviso_cliente': aviso, 'hora': hora_str, 'link': link,
    }

def proc_clausura(c):
    """Notificación de Acto Administrativo con Clausura en detalle.
    15 días hábiles CABA (CM 10L, CABA), 15+90 días hábiles Pcia BsAs.
    Va al calendario ✱ Vencimientos (no al principal).
    NO manda aviso al cliente (es un plazo interno del estudio).
    """
    notif = date.fromisoformat(c['fecha_notif'])
    cm = (c.get('cm') or '').upper()
    is_caba = cm in ('CABA', 'CM 10L')
    # Siempre el 15d
    f15 = sumar_dh(notif, 15)
    ciudad = 'CABA' if is_caba else (cm or 'PCIA').upper()
    # Retorna info estructurada que Paso 3 usa para crear los 1-2 eventos
    eventos = [{
        'fecha_evento': f15,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'} - {c['srt']} - VENCE APELAR CLAUSURA (15 DIAS) {ciudad}",
        'calendar_override': 'f98t26v6l01v4ss922e069rid0@group.calendar.google.com',
        'colorId_override': '11',
    }]
    if not is_caba:
        f90 = sumar_dh(notif, 90)
        eventos.append({
            'fecha_evento': f90,
            'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'} - {c['srt']} - VENCE APELAR CLAUSURA (90 DÍAS) {ciudad}",
            'calendar_override': 'f98t26v6l01v4ss922e069rid0@group.calendar.google.com',
            'colorId_override': '10',
        })
    # Devolvemos el primer evento en fecha_evento + lista completa en 'eventos_extra' para agendar
    return {
        'fecha_evento': eventos[0]['fecha_evento'],
        'summary': eventos[0]['summary'],
        'aviso_cliente': None,
        'eventos_extra': eventos,
        'subtipo': 'clausura_caba' if is_caba else 'clausura_pcia',
        'calendar_override': eventos[0]['calendar_override'],
        'colorId_override': eventos[0]['colorId_override'],
    }

def dispatch_acto_administrativo(c):
    """Clausuras entran acá porque su tipo_comunicacion es 'Notificación de Acto Administrativo'
    pero solo tratamos las que tienen 'Clausura' en el detalle."""
    if 'Clausura' in (c.get('detalle') or ''):
        return proc_clausura(c)
    return None  # otros actos administrativos los ignora el skill (no sabemos qué hacer)

PROCESADORES = {
    'Notificación de Dictamen Médico': lambda c: proc_dictamen_itm(c, 'DICTAMEN MEDICO'),
    'Notificación de ITM': lambda c: proc_dictamen_itm(c, 'ITM'),
    'Notificación de Constancia de Orden de Estudio': proc_constancia_orden_estudio,
    'Notificación de Citación': proc_citacion_examen,
    'Notificación de Citación al Servicio de Homologación': proc_citacion_homologacion,
    'Notificación de Acto Administrativo': dispatch_acto_administrativo,
}

comunic = json.load(open('/tmp/comunicaciones.json'))
procesadas = []
errores = []
for c in comunic:
    fn = PROCESADORES.get(c['tipo_comunicacion'])
    if not fn: continue
    try:
        res = fn(c)
        if res is None:
            errores.append({**c, 'error': 'no se pudo parsear texto'})
            continue
        procesadas.append({**c, **res, 'fecha_evento': res['fecha_evento'].isoformat()})
    except Exception as e:
        errores.append({**c, 'error': str(e)})

json.dump(procesadas, open('/tmp/procesadas.json','w'), default=str)
json.dump(errores, open('/tmp/errores_proceso.json','w'))
print(f'Procesadas: {len(procesadas)} | Errores de parseo: {len(errores)}')
```

### Paso 3 — Crear eventos en Calendar

Para cada item en `/tmp/procesadas.json`, crear 1 o más eventos (clausuras Pcia crean 2):

- **calendarId**: usar `item.calendar_override` si existe (clausuras → `✱ Vencimientos`), sino default `flirteador84@gmail.com`
- **summary**: `item.summary` (o recorrer `item.eventos_extra` si existe, para clausuras Pcia)
- **allDay**: true
- **startTime**: `{fecha_evento}T00:00:00`
- **endTime**: `{fecha_evento + 2 días}T00:00:00` (pattern Mara)
- **colorId**: `item.colorId_override` si existe, sino `'6'` (default naranja)
- **description**: `Fecha de notif: DD/MM/YYYY — auto-agendado por agendar-comunicaciones-srt`. Para citación agregar hora/dirección/link.
- **timeZone**: `America/Argentina/Buenos_Aires`

Loop para clausuras Pcia (2 eventos por comunicación):
```python
eventos_a_crear = item.get('eventos_extra') or [item]
for ev in eventos_a_crear:
    # crear con calendar_override / colorId_override
    ...
```

Chequear response. Si `status: confirmed` → marcar `agendado_ok=True` y guardar `event_id`. Si falla, guardar en errores.

### Paso 4 — Marcar como procesado en Supabase

```sql
UPDATE comunicaciones_miventanilla
SET agendado_en_calendar_at = now(),
    agendado_por = 'claude',
    calendar_event_id = $event_id,
    calendar_event_fecha = $fecha_evento
WHERE id = $comunicacion_id;
```

### Paso 5 — Avisos al grupo del cliente (SOLO citaciones)

Para items que tengan `aviso_cliente` no-null Y `grupo_cliente_wa` no-null, mandar al **grupo de WhatsApp compartido con el cliente** (no al teléfono individual). El grupo es del estilo "Apellido Nombre - Abogados Matías".

Usar `pg_net.http_post` contra la edge function `wa-send` (que internamente llama al MCP WA Railway):

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object(
    'chatId', $grupo_cliente_wa,   -- ej: '120363398764842372@g.us'
    'text', $aviso_cliente_text
  )
);
```

Verificar en `net._http_response` que el status sea 200 antes de dar por exitoso el envío.

Si **no hay `grupo_cliente_wa`** para el caso (no se encontró match automático por nombre) → incluir en el reporte del grupo Claude SRT con flag "sin grupo WA del cliente, avisar manual". Mara/Noe pueden actualizar manualmente la columna `casos_srt.wa_chat_id` cuando encuentren el grupo correcto.

### Paso 6 — Generar reporte

```python
import json
from datetime import date

procesadas = json.load(open('/tmp/procesadas.json'))
errores = json.load(open('/tmp/errores_proceso.json'))
sin_grupo_citacion = [p for p in procesadas if p.get('aviso_cliente') and not p.get('grupo_cliente_wa')]
avisos_enviados = [p for p in procesadas if p.get('aviso_cliente') and p.get('grupo_cliente_wa') and p.get('aviso_ok')]

hoy = date.today()
L = [f'📋 *AGENDAR COMUNICACIONES SRT* — {hoy.strftime("%d/%m/%Y")}']
L.append(f'Agendadas: {len(procesadas)} | Avisos WA clientes: {len(avisos_enviados)} | Sin grupo: {len(sin_grupo_citacion)} | Errores: {len(errores)}')

# Listado por tipo
def grupo(tipo):
    return [p for p in procesadas if p['tipo_comunicacion'] == tipo]

dict_itm = grupo('Notificación de Dictamen Médico') + grupo('Notificación de ITM')
if dict_itm:
    L.append('\n✅ *DICTAMEN MÉDICO / ITM — agendados a 3 hábiles*')
    for p in dict_itm:
        t = 'DICT MED' if 'Dictamen' in p['tipo_comunicacion'] else 'ITM'
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) {t}: vence {p['fecha_evento']}")

const = grupo('Notificación de Constancia de Orden de Estudio')
const_intim = [p for p in const if p.get('subtipo') == 'intimacion_abogado']
const_estudio = [p for p in const if p.get('subtipo') == 'orden_estudio_cliente']
if const_intim:
    L.append('\n📝 *CONSTANCIA (INTIMACIÓN AL ABOGADO) — agendadas a 5 hábiles para contestar*')
    for p in const_intim:
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}): vence {p['fecha_evento']}")
if const_estudio:
    L.append('\n🏥 *ORDEN DE ESTUDIO AL CLIENTE — agendadas + avisos cliente*')
    for p in const_estudio:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) {p['fecha_evento']} {p.get('hora','')} {p.get('estudios','')[:50]}{mk}")

examen = grupo('Notificación de Citación')
if examen:
    L.append('\n🏥 *CITACIÓN EXAMEN FÍSICO — agendadas + avisos cliente*')
    for p in examen:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) {p['fecha_evento']} {p.get('hora','')}{mk}")

clausuras = [p for p in procesadas if p['tipo_comunicacion'] == 'Notificación de Acto Administrativo' and 'Clausura' in (p.get('detalle') or '')]
if clausuras:
    L.append('\n🏛️ *CLAUSURAS SRT — agendadas en ✱ Vencimientos*')
    for p in clausuras:
        sub = p.get('subtipo','')
        plazos = '15+90d' if 'pcia' in sub else '15d'
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) {plazos}: vence {p['fecha_evento']}")

homo = grupo('Notificación de Citación al Servicio de Homologación')
if homo:
    L.append('\n⚖️ *AUDIENCIA HOMOLOGACIÓN — agendadas + avisos cliente*')
    for p in homo:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) {p['fecha_evento']} {p.get('hora','')}{mk}")

if sin_grupo_citacion:
    L.append('\n📞 *CITACIONES SIN GRUPO WA DEL CLIENTE — avisar manual*')
    for s in sin_grupo_citacion:
        L.append(f"• {s['nombre_actor']} ({s['srt']}) — matchear grupo con casos_srt.wa_chat_id")

if errores:
    L.append('\n🔴 *ERRORES DE PROCESAMIENTO*')
    for e in errores:
        L.append(f"• {e.get('nombre_actor','?')} ({e['srt']}) {e['tipo_comunicacion']}: {e['error']}")

if not procesadas and not errores:
    L.append('\n✅ Sin comunicaciones nuevas hoy.')

open('/tmp/reporte.txt','w').write('\n'.join(L))
```

### Paso 7 — INSERT run (dispara WA al grupo)

```sql
INSERT INTO agendar_comunicaciones_runs (
  total_procesadas, agendados_hoy, errores, sin_caso_srt, reporte_texto
) VALUES (
  $total,
  $procesadas_jsonb,
  $errores_jsonb,
  $sin_tel_jsonb,
  $reporte_texto
)
RETURNING id, whatsapp_jobid;
```

El trigger `trg_agendar_comunicaciones_wa` dispara el envío al grupo Claude SRT via pg_net.

### Paso 8 — Confirmar

Reportar: total procesadas, agendadas por tipo, avisos WA enviados a clientes, sin teléfono, errores de parseo, ID del run.

## NOTAS

- **Traslado de Apelación y Agravios**: pendiente Fase 3. Requiere leer texto y detectar si apeló ART; solo en ese caso agendar 10 hábiles para contestar agravios.
- **Parseo frágil**: los regex de citaciones asumen el template estándar SRT. Si cambia el formato del PDF, el parseo falla y aparece en "errores de procesamiento" sin romper el resto.
- **Normalización teléfono cliente**: formato esperado por `wa-send` es `5491XXXXXXXX@s.whatsapp.net` o solo dígitos `5491XXXXXXXX`. Normalizar antes de POST.
