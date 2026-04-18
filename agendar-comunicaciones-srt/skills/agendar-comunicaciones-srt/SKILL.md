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

| Tipo | Plazo / Acción | Evento en Calendar | Aviso al cliente |
|------|----------------|---------------------|------------------|
| Notificación de Dictamen Médico | 3 días hábiles para impugnar | `NOMBRE-SRT- VENCE IMPUGNAR DICTAMEN MEDICO` | No |
| Notificación de ITM | 3 días hábiles para impugnar | `NOMBRE-SRT- VENCE IMPUGNAR ITM` | No |
| Notificación de Constancia de Orden de Estudio | 5 días hábiles para contestar intimación | `NOMBRE-SRT- VENCE CONTESTAR INTIMACION SRT` | No |
| Notificación de Citación | Fecha de audiencia directa | `NOMBRE-SRT- EXAMEN FISICO SRT HH:MM DIR` | **Sí** (WA formato Mara) |
| Notificación de Citación al Servicio de Homologación | Fecha de audiencia directa | `NOMBRE-SRT- AUDIENCIA HOMOLOGACION HH:MM (Teams)` | **Sí** (WA con link) |

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
  c.nombre AS nombre_actor,
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
    'Notificación de Citación al Servicio de Homologación'
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
        aviso = (f"*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
                 f"para *Estudio SRT ({estudios})*.  *DIRECCION:* {dir_completa or '(ver PDF)'}")
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
    # Dirección: "en el domicilio sito en la calle ... a fin de realizar"
    m_dir = re.search(r'sito en la calle\s+([^,\.]+?(?:CP\.?\s*\d+)?)[,\.\s]+a fin', t, re.S | re.I)
    direccion = m_dir.group(1).strip().replace('\n', ' ') if m_dir else '(dir no encontrada)'
    # Tipo de estudio / examen
    m_tipo = re.search(r'fin de realizar\s+la?\s+([^\.\n]+)', t, re.I)
    tipo_estudio = (m_tipo.group(1).strip() if m_tipo else 'Examen Físico').rstrip('.').strip()
    dia_sem = DIAS_SEM[fecha_ev.weekday()]
    aviso = (f"*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
             f"para *{tipo_estudio}*.  *DIRECCION:* {direccion}")
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- {tipo_estudio.upper()} SRT {hora_str}",
        'aviso_cliente': aviso,
        'hora': hora_str,
        'direccion': direccion,
    }

def proc_citacion_homologacion(c):
    t = c.get('texto_extraido') or ''
    m_fecha = re.search(r'virtual el día\s+(\d{2}/\d{2}/\d{4})\s*a las\s+(\d{1,2}[:.]?\d{2})', t)
    if not m_fecha: return None
    fecha_str = m_fecha.group(1)
    hora_str = m_fecha.group(2).replace('.', ':')
    fecha_ev = date(*[int(x) for x in reversed(fecha_str.split('/'))])
    m_link = re.search(r'https://go\.srt\.gob\.ar/\S+', t)
    link = m_link.group(0) if m_link else ''
    dia_sem = DIAS_SEM[fecha_ev.weekday()]
    aviso = (f"*{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs* "
             f"*Audiencia de Homologación SRT* (virtual por Teams).\n{link}".strip())
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- AUDIENCIA HOMOLOGACION SRT {hora_str} (Teams)",
        'aviso_cliente': aviso,
        'hora': hora_str,
        'link': link,
    }

PROCESADORES = {
    'Notificación de Dictamen Médico': lambda c: proc_dictamen_itm(c, 'DICTAMEN MEDICO'),
    'Notificación de ITM': lambda c: proc_dictamen_itm(c, 'ITM'),
    'Notificación de Constancia de Orden de Estudio': proc_constancia_orden_estudio,
    'Notificación de Citación': proc_citacion_examen,
    'Notificación de Citación al Servicio de Homologación': proc_citacion_homologacion,
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

Para cada item en `/tmp/procesadas.json`:

- **calendarId**: `flirteador84@gmail.com`
- **summary**: `item.summary`
- **allDay**: true
- **startTime**: `{fecha_evento}T00:00:00`
- **endTime**: `{fecha_evento + 2 días}T00:00:00` (mismo pattern que Mara)
- **colorId**: `'6'` (Tangerine naranja)
- **description**:
  - Para dictamen/itm/constancia: `Fecha de notif: DD/MM/YYYY — auto-agendado por agendar-comunicaciones-srt`
  - Para citación: incluir `Hora: {hora}`, `Dirección: {direccion}` (o `Link: {link}` para homologación)
- **timeZone**: `America/Argentina/Buenos_Aires`

Chequear response. Si `status: confirmed` → marcar item como `agendado_ok=True` y guardar `event_id`. Si falla, guardar en errores.

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
