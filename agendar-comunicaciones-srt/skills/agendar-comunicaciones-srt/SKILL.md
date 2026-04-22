---
name: agendar-comunicaciones-srt
description: >
  Agendamiento automático diario (L-V 9am AR) de comunicaciones de Mi Ventanilla
  SRT. Cubre 4 tipos con plazo procesal o fecha de audiencia: (1) Dictamen Médico
  3 días hábiles, (2) Constancia de Orden de Estudio 5 días hábiles para
  contestar intimación, (3) Citación a Examen Físico agenda la fecha de audiencia
  + aviso al cliente, (4) Citación al Servicio de Homologación agenda fecha +
  link Teams + aviso al cliente. Las ITMs NO se agendan (no se impugnan). Lee el texto extraído de los PDFs
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
| Constancia Orden Estudio (intimación) | 5 días hábiles contestar | Principal | No |
| Constancia Orden Estudio (al cliente) | Fecha estudio directa | Principal | **Sí** (cálido) |
| Citación Examen Físico | Fecha audiencia directa | Principal | **Sí** (cálido) |
| Citación Homologación (Teams) | Fecha audiencia directa | Principal | **Sí** (con link) |
| **Clausura con acuerdo** (homologación) | **5d contestar intimación** | **Principal + ✱ Vencimientos** | No |
| **Clausura rechazo / divergencia CABA** | **15d apelar** | **Principal + ✱ Vencimientos** | No |
| **Clausura rechazo / divergencia Pcia** | **15d + 90d apelar** | **Principal + ✱ Vencimientos** | No |

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
WHERE fecha BETWEEN
    ((now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date - interval '30 days')::date
  AND
    ((now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date + interval '120 days')::date
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
  c.comision_medica AS cm,          -- fallback final de CM si no se detecta del PDF
  c.wa_chat_id AS grupo_cliente_wa,  -- chat_id del grupo WhatsApp con el cliente
  a.texto_extraido,
  -- Para clausuras: fallback al PDF del dictamen más reciente del mismo SRT
  -- (por si la clausura aún no tiene texto_extraido del scraper v2.5).
  (SELECT a2.texto_extraido
   FROM adjuntos_miventanilla a2
   JOIN comunicaciones_miventanilla m2 ON m2.id = a2.comunicacion_id
   WHERE m2.srt_expediente_nro = m.srt_expediente_nro
     AND m2.tipo_comunicacion = 'Notificación de Dictamen Médico'
     AND a2.texto_extraido IS NOT NULL
   ORDER BY m2.fecha_notificacion DESC
   LIMIT 1) AS texto_dictamen_previo
FROM comunicaciones_miventanilla m
LEFT JOIN casos_srt c ON c.numero_srt = m.srt_expediente_nro
LEFT JOIN adjuntos_miventanilla a ON a.comunicacion_id = m.id
WHERE m.tipo_comunicacion IN (
    'Notificación de Dictamen Médico',
    'Notificación de Constancia de Orden de Estudio',
    'Notificación de Citación',
    'Notificación de Citación al Servicio de Homologación',
    'Notificación de Acto Administrativo',  -- clausuras (filtradas por detalle en el procesador)
    'Envío de Comunicación'                 -- prestación dineraria (filtrada por detalle en el procesador)
  )
  -- NO filtrar por m.estado: el scraper contamina el campo (marca Leído al abrir
  -- DetalleComunicacion.aspx para extraer adjuntos), y el equipo no usa la app
  -- del estudio para marcarlas. Idempotencia real solo por agendado_en_calendar_at.
  AND m.agendado_en_calendar_at IS NULL      -- SIN procesar por Claude en corridas anteriores
  -- Ventana: hoy + ayer + anteayer (días calendario completos AR).
  -- Ejemplo: si corre el 18/04 a las 9am AR, procesa TODAS las notificaciones
  -- del 16/04, 17/04 y 18/04 completas. Cubre hoy + 2 días atrás.
  -- IMPORTANTE: `hoy` se calcula en TZ Argentina (no UTC), porque el server
  -- puede correr en UTC y los 9am AR son las 12:00 UTC → mismo día AR.
  AND (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
      BETWEEN ((now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date - interval '2 days')::date
          AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
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

# Estudios que típicamente requieren asesoramiento previo (respuestas del cliente influyen)
TRIGGERS_ASESORAMIENTO = ['PSICO','PSIQU','OFTAL','ORL','OTORRIN','AUDIO','AUDIOMETR',
                          'POTENCIAL','NEURO','TRAUMATO','INTERCONSULT','EXAMEN',
                          'EVALUAC','VIDEO','ENDOSCOP','ELECTRO','ECO','RESONANC','TOMOGR']

def estudio_requiere_asesoramiento(estudios_text):
    """True si el estudio requiere asesoramiento (respuestas del paciente influyen).
    False solo si es RX/radiografía pura (no hay respuestas del paciente).
    Fail-safe: ante duda, True."""
    t = (estudios_text or '').upper()
    if any(k in t for k in TRIGGERS_ASESORAMIENTO):
        return True
    # Si contiene solo radiografía/RX y nada más, es simple
    if ('RADIOGRAF' in t or ' RX ' in t or t.startswith('RX')) and len(t) < 200:
        return False
    return True  # default: pedir asesoramiento

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

def proc_dictamen_medico(c, tipo_label):
    notif = date.fromisoformat(c['fecha_notif'])
    fecha_ev = sumar_dh(notif, 3)
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- VENCE IMPUGNAR {tipo_label}",
        'aviso_cliente': None,
        'colorId_override': '6',  # naranja: dictamen para impugnar
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
        pn = primer_nombre(c['nombre_actor']) if c.get('nombre_actor') else ''
        saludo = f"Hola {pn}!" if pn else "Hola!"
        requiere = estudio_requiere_asesoramiento(estudios)
        aviso_previo = (
            "⚠️ *Importante*: antes de asistir comunicate con nosotros por acá para "
            "recibir el asesoramiento previo.\n\n"
        ) if requiere else ""
        aviso = (
            f"{saludo} Te avisamos que la SRT te ordenó un *estudio médico* "
            f"en el marco de tu expediente. Tenés que ir a hacértelo:\n\n"
            f"🩺 Estudio: {estudios}\n"
            f"📅 *{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs*\n"
            f"📍 {dir_completa or '(ver PDF en Mi Ventanilla)'}\n\n"
            f"{aviso_previo}"
            f"Llevá tu DNI. *Confirmanos por acá si vas a poder ir.* "
            f"Si no podés, avisanos con tiempo así lo reprogramamos."
        )
        return {
            'fecha_evento': fecha_ev,
            'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- ESTUDIO SRT {hora_str} {estudios[:60]}",
            'aviso_cliente': aviso,
            'hora': hora_str,
            'direccion': dir_completa,
            'estudios': estudios,
            'subtipo': 'orden_estudio_cliente',
            'con_hora': True,
            'colorId_override': '9',  # azul: estudio al cliente (orden prestador)
        }

    # Caso 1: intimación al abogado (default si no hay Fecha/Hora Prestación)
    fecha_ev = sumar_dh(notif, 5)
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- VENCE CONTESTAR INTIMACION SRT",
        'aviso_cliente': None,
        'subtipo': 'intimacion_abogado',
        'colorId_override': '6',  # naranja: intimación (plazo procesal)
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
    pn = primer_nombre(c['nombre_actor']) if c.get('nombre_actor') else ''
    saludo = f"Hola {pn}!" if pn else "Hola!"
    aviso = (
        f"{saludo} Te avisamos que la SRT (Superintendencia de Riesgos del Trabajo) "
        f"te citó a *{tipo_estudio}* para avanzar con tu expediente.\n\n"
        f"📅 *{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs*\n"
        f"📍 {direccion}\n\n"
        f"⚠️ *Importante*: antes de asistir comunicate con nosotros por acá para "
        f"recibir el asesoramiento previo. Llevá tu DNI y, si usás, anteojos o audífonos.\n\n"
        f"*Confirmanos por acá si vas a poder ir.* Si no podés, avisanos con tiempo así vemos cómo seguimos."
    )
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- {tipo_estudio.upper()} SRT {hora_str}",
        'aviso_cliente': aviso, 'hora': hora_str, 'direccion': direccion,
        'con_hora': True,  # evento con hora específica (no all-day)
        'colorId_override': '9',  # azul: citación médica / estudio (orden prestador)
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
    pn = primer_nombre(c['nombre_actor']) if c.get('nombre_actor') else ''
    saludo = f"Hola {pn}!" if pn else "Hola!"
    aviso = (
        f"{saludo} Te avisamos que tenés una *audiencia virtual* ante el Servicio de "
        f"Homologación de la SRT. Ahí se evalúa un posible acuerdo en tu expediente.\n\n"
        f"📅 *{dia_sem} {fecha_ev.strftime('%d/%m/%Y')}* a las *{hora_str}hs*\n"
        f"💻 Por Microsoft Teams: {link}\n\n"
        f"⚠️ *Importante*: antes de conectarte comunicate con nosotros por acá para "
        f"recibir el asesoramiento previo. Conectate unos minutos antes, con buena señal "
        f"y el DNI a mano.\n\n"
        f"*Confirmanos por acá que vas a poder asistir.*"
    )
    return {
        'fecha_evento': fecha_ev,
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- AUDIENCIA HOMOLOGACION SRT {hora_str} (Teams)",
        'aviso_cliente': aviso, 'hora': hora_str, 'link': link,
        'con_hora': True,
        'colorId_override': '9',  # azul: audiencia de acuerdo virtual (Tami/Mara)
    }

def detectar_cm_emisora(texto):
    """Extrae el código de la Comisión Médica que EMITE la clausura/dictamen.
    Devuelve el código (ej: '10', '10L', '13', '37', '372') o None si no detecta.

    La CM emisora es la que firma la disposición — NO la ciudad de emisión.
    Ej: una clausura puede estar emitida desde SAN ISIDRO pero firmada por la
    CM 10 (CABA). Lo que vale es quién firma.

    Patrones posibles (ordenados por especificidad):
      1. Número de disposición: "DIAPA-2026-7647-APN-SHC10#SRT" → '10'
      2. Encabezado art.1°:    "SERVICIO DE HOMOLOGACIÓN DE LA COMISION MEDICA N° 10 DISPONE" → '10'
      3. Firma al pie:         "Servicio de Homologación C.M. 10" → '10'
      4. Considerando clausura: "esta Comisión Medica N° 10 de la Ciudad Autónoma" → '10'
      5. Dictamen médico:      "Comisión Médica: 10L - DELEGACIÓN VILLA URQUIZA" → '10L'
    """
    if not texto: return None
    patrones = [
        r'DIAPA[^A-Za-z0-9]+\d+[^A-Za-z0-9]+\d+[^A-Za-z0-9]+APN[^A-Za-z0-9]+SHC(\w+?)#',
        r'SERVICIO\s+DE\s+HOMOLOGACI[OÓ]N\s+DE\s+LA\s+COMISI[OÓ]N\s+M[EÉ]DICA\s+N[°º]?\s*(\w+)',
        r'Servicio\s+de\s+Homologaci[oó]n\s+C\.?\s*M\.?\s*(\w+)',
        r'esta\s+Comisi[oó]n\s+M[eé]dica\s+N[°º]?\s*(\w+)',
        r'Comisi[oó]n\s+M[eé]dica\s*:\s*(\w+)',
    ]
    for pat in patrones:
        m = re.search(pat, texto, re.I)
        if m:
            return m.group(1).strip().upper()
    return None

def cm_es_caba(codigo):
    """CM 10 (y variantes 10L, 10A, etc.) → CABA. Cualquier otra → Pcia."""
    if not codigo: return None
    return bool(re.fullmatch(r'10[A-Z]*', codigo.strip().upper()))

def es_clausura_con_acuerdo(texto):
    """Detecta si la Disposición de Clausura es por homologación de acuerdo.
    Frases clave (CONSIDERANDO + articulado):
      - "resolvieron celebrar el acuerdo acompañado"
      - "Homológase el acuerdo celebrado"
    En ese caso NO se apela → el trabajador tiene 5 hábiles para contestar
    una intimación (aclarar si acepta/rechaza el acuerdo).
    """
    if not texto: return False
    t = texto.lower()
    return ('resolvieron celebrar el acuerdo acompañado' in t
            or 'resolvieron celebrar el acuerdo acompanado' in t
            or 'homológase el acuerdo celebrado' in t
            or 'homologase el acuerdo celebrado' in t)

def proc_clausura(c):
    """Notificación de Acto Administrativo con 'Clausura' en detalle.

    Dos variantes según el texto del PDF:

    1) CLAUSURA CON ACUERDO (homologación): el trabajador y la ART firmaron un
       acuerdo. Plazo: 5 días hábiles para contestar intimación. Color amarillo.
       Eventos all-day en calendar principal + ✱ Vencimientos.

    2) CLAUSURA DE RECHAZO/DIVERGENCIA: no hubo acuerdo, o no tiene incapacidad.
       Plazos: 15 días hábiles CABA (CM 10/10L), 15+90 días hábiles Pcia.
       Color por jurisdicción: rojo CABA, verde Pcia. Eventos all-day en
       calendar principal + ✱ Vencimientos.

    Detecta CABA/Pcia leyendo del PDF qué CM firma (la ciudad de emisión NO vale:
    una clausura emitida desde SAN ISIDRO puede estar firmada por la CM 10 de CABA).
    Fallback chain: texto de clausura → texto dictamen previo → casos_srt.comision_medica.
    Si no se puede clasificar → retorna None (reporta para revisión manual).

    NO manda aviso al cliente (es un plazo interno del estudio).
    """
    CAL_VENC = 'f98t26v6l01v4ss922e069rid0@group.calendar.google.com'  # ✱ Vencimientos
    CAL_PRINC = 'flirteador84@gmail.com'                               # principal
    notif = date.fromisoformat(c['fecha_notif'])
    texto = c.get('texto_extraido') or ''
    nombre = c['nombre_actor'] or '(SIN NOMBRE)'
    srt = c['srt']

    def _dup(lista, fecha, summary, colorId):
        """Agrega 2 eventos (✱ Vencimientos + principal) con el mismo contenido."""
        for cal in (CAL_VENC, CAL_PRINC):
            lista.append({'fecha_evento': fecha, 'summary': summary,
                          'calendar_override': cal, 'colorId_override': colorId})

    # ─── VARIANTE 1: clausura con ACUERDO ───
    if es_clausura_con_acuerdo(texto):
        fecha_ev = sumar_dh(notif, 5)
        eventos = []
        _dup(eventos, fecha_ev,
             f"{nombre} - {srt} - VENCE CONTESTAR INTIMACION CLAUSURA (ACUERDO)",
             '5')  # amarillo
        return {
            'fecha_evento': eventos[0]['fecha_evento'],
            'summary': eventos[0]['summary'],
            'aviso_cliente': None, 'eventos_extra': eventos,
            'subtipo': 'clausura_acuerdo',
            'calendar_override': eventos[0]['calendar_override'],
            'colorId_override': '5',
        }

    # ─── VARIANTE 2: clausura de RECHAZO/DIVERGENCIA ───
    codigo = (detectar_cm_emisora(texto)
              or detectar_cm_emisora(c.get('texto_dictamen_previo')))
    if codigo:
        is_caba = cm_es_caba(codigo)
        ciudad = f'CM {codigo}' + (' (CABA)' if is_caba else '')
    else:
        cm_manual = (c.get('cm') or '').upper()
        if cm_manual in ('CABA', 'CM 10L', 'CM 10'):
            is_caba = True; ciudad = 'CABA'
        elif cm_manual:
            is_caba = False; ciudad = cm_manual
        else:
            return None  # reporta para revisión manual

    color = '11' if is_caba else '10'  # rojo CABA, verde Pcia — toda la clausura misma jurisdicción
    eventos = []
    f15 = sumar_dh(notif, 15)
    _dup(eventos, f15, f"{nombre} - {srt} - VENCE APELAR CLAUSURA (15 DIAS) {ciudad}", color)
    if not is_caba:
        f90 = sumar_dh(notif, 90)
        _dup(eventos, f90, f"{nombre} - {srt} - VENCE APELAR CLAUSURA (90 DÍAS) {ciudad}", color)

    return {
        'fecha_evento': eventos[0]['fecha_evento'],
        'summary': eventos[0]['summary'],
        'aviso_cliente': None, 'eventos_extra': eventos,
        'subtipo': 'clausura_caba' if is_caba else 'clausura_pcia',
        'calendar_override': eventos[0]['calendar_override'],
        'colorId_override': color,
    }

# Sentinel: los dispatchers lo devuelven cuando la comunicación no aplica a su sub-tipo.
# Se usa para distinguir "no es mi caso, skip silencioso" de "fallo de parseo" (que es None).
SKIP_DISPATCH = object()

def dispatch_acto_administrativo(c):
    """Clausuras entran acá porque su tipo_comunicacion es 'Notificación de Acto Administrativo'
    pero solo tratamos las que tienen 'Clausura' en el detalle."""
    if 'Clausura' in (c.get('detalle') or ''):
        return proc_clausura(c)
    return SKIP_DISPATCH  # otros actos administrativos los ignora el skill

def proc_prestacion_dineraria(c):
    """Notificación de Cálculo de Prestación Dineraria.
    Informativo: no agenda evento, no manda WA, solo aparece en el reporte
    para que el equipo lo vea y controle el monto liquidado."""
    notif = date.fromisoformat(c['fecha_notif'])
    return {
        'fecha_evento': notif,         # usamos notif como placeholder (no crea evento)
        'summary': f"{c['nombre_actor'] or '(SIN NOMBRE)'}-{c['srt']}- PREST DINERARIA (informativo)",
        'aviso_cliente': None,
        'subtipo': 'prest_dineraria',
        'skip_calendar': True,          # Paso 3 debe saltearlo
    }

def dispatch_envio_comunicacion(c):
    """'Envío de Comunicación' es muy genérico. Solo procesamos las que son
    Notificación de Cálculo de Prestación Dineraria — el resto se ignora."""
    det = (c.get('detalle') or '').lower()
    if 'prest' in det and 'dinerari' in det:
        return proc_prestacion_dineraria(c)
    return SKIP_DISPATCH

PROCESADORES = {
    'Notificación de Dictamen Médico': lambda c: proc_dictamen_medico(c, 'DICTAMEN MEDICO'),
    'Notificación de Constancia de Orden de Estudio': proc_constancia_orden_estudio,
    'Notificación de Citación': proc_citacion_examen,
    'Notificación de Citación al Servicio de Homologación': proc_citacion_homologacion,
    'Notificación de Acto Administrativo': dispatch_acto_administrativo,
    'Envío de Comunicación': dispatch_envio_comunicacion,
}

comunic = json.load(open('/tmp/comunicaciones.json'))
procesadas = []
errores = []
for c in comunic:
    fn = PROCESADORES.get(c['tipo_comunicacion'])
    if not fn: continue
    try:
        res = fn(c)
        if res is SKIP_DISPATCH:
            continue  # dispatcher filtró: no aplica a ningún sub-procesador, no es error
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

### Paso 2.5 — Generar `create_event_calls.json` con args EXACTOS

⚠️ CRÍTICO para eliminar bugs repetidos (colores mal, end=start+2, defaults):

Agregá este bloque inmediatamente después del Paso 2. Transforma `procesadas.json`
en una lista plana de llamadas `create_event` con **todos los args exactos
pre-calculados** (startTime/endTime ISO, colorId, calendarId, allDay, description).
El Paso 3 solo hace `create_event(**item)` sin interpretar nada.

```python
import json
from datetime import date, datetime, timedelta

procesadas = json.load(open('/tmp/procesadas.json'))

CAL_PRINC = 'flirteador84@gmail.com'
TZ = 'America/Argentina/Buenos_Aires'

def fecha_desc(fecha_notif_iso):
    """DD/MM/YYYY para description."""
    d = date.fromisoformat(fecha_notif_iso)
    return d.strftime('%d/%m/%Y')

def iso_allday(fecha_iso):
    """'2026-04-27' → '2026-04-27T00:00:00Z'"""
    return f'{fecha_iso}T00:00:00Z'

def iso_allday_next(fecha_iso):
    """'2026-04-27' → '2026-04-28T00:00:00Z' (start + 1 día, end-exclusive)"""
    d = date.fromisoformat(fecha_iso) + timedelta(days=1)
    return f'{d.isoformat()}T00:00:00Z'

def iso_con_hora(fecha_iso, hora_str, add_hour=0):
    """fecha='2026-04-27', hora='09:45' → '2026-04-27T09:45:00-03:00' (o +1h si add_hour=1)"""
    hh, mm = hora_str.split(':')
    hh = int(hh) + add_hour
    return f'{fecha_iso}T{hh:02d}:{mm}:00-03:00'

calls = []
for item in procesadas:
    if item.get('skip_calendar'):
        continue
    eventos_a_crear = item.get('eventos_extra') or [item]
    for ev in eventos_a_crear:
        fecha_ev = ev.get('fecha_evento') or item.get('fecha_evento')
        if isinstance(fecha_ev, date):
            fecha_ev = fecha_ev.isoformat()
        summary = ev.get('summary') or item.get('summary')
        color = ev.get('colorId_override') or item.get('colorId_override') or '6'
        cal = ev.get('calendar_override') or item.get('calendar_override') or CAL_PRINC
        con_hora = item.get('con_hora', False)

        desc_base = f"Fecha de notif: {fecha_desc(item['fecha_notif'])} — auto-agendado por agendar-comunicaciones-srt"
        # Para eventos con hora, agregar hora/dirección/link al description
        descripcion = desc_base
        if con_hora:
            extras = []
            if item.get('hora'):      extras.append(f"Hora: {item['hora']}")
            if item.get('direccion'): extras.append(f"Dirección: {item['direccion']}")
            if item.get('link'):      extras.append(item['link'])
            if item.get('estudios'):  extras.append(f"Estudios: {item['estudios'][:120]}")
            if extras:
                descripcion = desc_base + ' | ' + ' | '.join(extras)

        call = {
            'calendarId': cal,
            'summary': summary,
            'timeZone': TZ,
            'colorId': color,
            'description': descripcion,
            # fields útiles para Paso 4 (marcar en Supabase)
            '_comunicacion_id': item.get('comunicacion_id'),
            '_srt': item.get('srt'),
            '_fecha_evento': fecha_ev,
            '_nombre_actor': item.get('nombre_actor'),
            '_tipo': item.get('tipo_comunicacion'),
        }
        if con_hora:
            hora = item.get('hora')
            call['startTime'] = iso_con_hora(fecha_ev, hora, add_hour=0)
            call['endTime']   = iso_con_hora(fecha_ev, hora, add_hour=1)
            # NO pasar allDay para con_hora
        else:
            call['startTime'] = iso_allday(fecha_ev)
            call['endTime']   = iso_allday_next(fecha_ev)
            call['allDay']    = True
        calls.append(call)

json.dump(calls, open('/tmp/create_event_calls.json','w'), ensure_ascii=False)
print(f'Llamadas a create_event pre-calculadas: {len(calls)}')
# Sanity check: imprimir primeros 2 para inspección
for c in calls[:2]:
    print(json.dumps({k:v for k,v in c.items() if not k.startswith('_')}, ensure_ascii=False))
```

### Paso 3 — Crear eventos en Calendar (LOOP TRIVIAL, no interpretar nada)

⚠️ **NO calcular fechas, colores, calendars ni defaults.** Todos los args ya
están pre-calculados en `/tmp/create_event_calls.json` por el Paso 2.5.

Para cada item del JSON:
1. Tomar los fields SIN los que empiezan con `_` (son metadata para Paso 4)
2. Llamar `create_event` con esos args **tal cual** — copiar-pegar literal
3. Guardar el `event_id` de la response en `/tmp/eventos_creados.json` con el
   metadata (`_comunicacion_id`, `_srt`, `_fecha_evento`)

Ejemplo de item que viene del JSON:

```json
{
  "calendarId": "flirteador84@gmail.com",
  "summary": "MIÑO PABLO GASTON-571662/25- VENCE CONTESTAR INTIMACION SRT",
  "timeZone": "America/Argentina/Buenos_Aires",
  "colorId": "6",
  "description": "Fecha de notif: 21/04/2026 — auto-agendado por agendar-comunicaciones-srt",
  "startTime": "2026-04-28T00:00:00Z",
  "endTime": "2026-04-29T00:00:00Z",
  "allDay": true,
  "_comunicacion_id": "xxx",
  "_srt": "571662/25",
  "_fecha_evento": "2026-04-28",
  "_nombre_actor": "MIÑO PABLO GASTON",
  "_tipo": "Notificación de Constancia de Orden de Estudio"
}
```

La llamada a `create_event` recibe los 7 primeros fields (`calendarId`,
`summary`, `timeZone`, `colorId`, `description`, `startTime`, `endTime`,
`allDay`) — literal, sin modificar. Los que empiezan con `_` son metadata
para el Paso 4 (el marcado en Supabase).

Si la respuesta trae `"status": "confirmed"` → OK, guardar el `id` del evento.
Si falla → guardar en `/tmp/errores_calendar.json`.

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
from datetime import datetime
from zoneinfo import ZoneInfo

procesadas = json.load(open('/tmp/procesadas.json'))
errores = json.load(open('/tmp/errores_proceso.json'))
sin_grupo_citacion = [p for p in procesadas if p.get('aviso_cliente') and not p.get('grupo_cliente_wa')]
avisos_enviados = [p for p in procesadas if p.get('aviso_cliente') and p.get('grupo_cliente_wa') and p.get('aviso_ok')]

# Fecha en timezone AR (el server puede estar en UTC)
hoy = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
L = [f'📋 *AGENDAR COMUNICACIONES SRT* — {hoy.strftime("%d/%m/%Y")}']
L.append(f'Agendadas: {len(procesadas)} | Avisos WA clientes: {len(avisos_enviados)} | Sin grupo: {len(sin_grupo_citacion)} | Errores: {len(errores)}')

# Listado por tipo
def grupo(tipo):
    return [p for p in procesadas if p['tipo_comunicacion'] == tipo]

def fmt_fecha(s):
    """YYYY-MM-DD → DD/MM"""
    try:
        y,m,d = s.split('-'); return f"{d}/{m}"
    except: return s or '?'

dict_med = grupo('Notificación de Dictamen Médico')
if dict_med:
    L.append('\n✅ *DICTAMEN MÉDICO — plazo 3 hábiles p/ impugnar*')
    for p in dict_med:
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) — DICT MED notificado {fmt_fecha(p.get('fecha_notif'))} → vence impugnar {fmt_fecha(p['fecha_evento'])}")

const = grupo('Notificación de Constancia de Orden de Estudio')
const_intim = [p for p in const if p.get('subtipo') == 'intimacion_abogado']
const_estudio = [p for p in const if p.get('subtipo') == 'orden_estudio_cliente']
if const_intim:
    L.append('\n📝 *CONSTANCIA (INTIMACIÓN AL ABOGADO) — plazo 5 hábiles p/ contestar*')
    for p in const_intim:
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) — notificada {fmt_fecha(p.get('fecha_notif'))} → vence contestar {fmt_fecha(p['fecha_evento'])}")
if const_estudio:
    L.append('\n🏥 *ORDEN DE ESTUDIO AL CLIENTE — agendada + aviso WA*')
    for p in const_estudio:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) — notif {fmt_fecha(p.get('fecha_notif'))} → estudio {fmt_fecha(p['fecha_evento'])} {p.get('hora','')} {p.get('estudios','')[:50]}{mk}")

examen = grupo('Notificación de Citación')
if examen:
    L.append('\n🏥 *CITACIÓN EXAMEN FÍSICO — agendada + aviso WA*')
    for p in examen:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) — notif {fmt_fecha(p.get('fecha_notif'))} → examen {fmt_fecha(p['fecha_evento'])} {p.get('hora','')}{mk}")

clausuras = [p for p in procesadas if p['tipo_comunicacion'] == 'Notificación de Acto Administrativo' and 'Clausura' in (p.get('detalle') or '')]
if clausuras:
    L.append('\n🏛️ *CLAUSURAS SRT — agendadas en ✱ Vencimientos*')
    for p in clausuras:
        sub = p.get('subtipo','')
        plazos = '15+90d' if 'pcia' in sub else '15d'
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) — notif {fmt_fecha(p.get('fecha_notif'))} → {plazos}, vence {fmt_fecha(p['fecha_evento'])}")

homo = grupo('Notificación de Citación al Servicio de Homologación')
if homo:
    L.append('\n⚖️ *AUDIENCIA HOMOLOGACIÓN — agendada + aviso WA*')
    for p in homo:
        mk = '' if p.get('aviso_ok') else (' ⚠️sin grupo' if not p.get('grupo_cliente_wa') else ' 🔴aviso fallo')
        L.append(f"• {p['nombre_actor']} ({p['srt']}) — notif {fmt_fecha(p.get('fecha_notif'))} → audiencia {fmt_fecha(p['fecha_evento'])} {p.get('hora','')}{mk}")

prest_din = [p for p in procesadas if p.get('subtipo') == 'prest_dineraria']
if prest_din:
    L.append('\n💵 *NOTIFICACIÓN DE CÁLCULO DE PRESTACIÓN DINERARIA — revisar monto liquidado*')
    L.append('_(Informativo. Abrir el PDF en Mi Ventanilla y controlar el cálculo.)_')
    for p in prest_din:
        L.append(f"• {p['nombre_actor'] or '(sin nombre)'} ({p['srt']}) — notif {fmt_fecha(p.get('fecha_notif'))}")

if sin_grupo_citacion:
    L.append('\n📞 *CITACIONES SIN GRUPO WA DEL CLIENTE — copiar y pegar al cliente*')
    L.append('_(Mara: copiá el mensaje de cada uno y pegáselo al cliente por WA. Después matcheá el grupo en `casos_srt.wa_chat_id` para que la próxima salga sola.)_')
    for s in sin_grupo_citacion:
        L.append(f"\n———— *{s['nombre_actor']}* ({s['srt']}) ————")
        L.append(s['aviso_cliente'])

if errores:
    L.append('\n🔴 *ERRORES DE PROCESAMIENTO*')
    for e in errores:
        L.append(f"• {e.get('nombre_actor','?')} ({e['srt']}) {e['tipo_comunicacion']}: {e['error']}")

if not procesadas and not errores:
    L.append('\n✅ Sin comunicaciones nuevas hoy.')

open('/tmp/reporte.txt','w').write('\n'.join(L))
```

### Paso 6.5 — Post-check de sanity (detectar items salteados)

Después de generar el reporte, ejecutar una query adicional a Supabase para
detectar si **quedaron comunicaciones dentro de la ventana que NO se agendaron**
en esta corrida (indicaría que el agente se saltó items por sobrecarga, cadena
parcial, etc.). Si las hay, apendear un bloque **⚠️ ALERTA** al `/tmp/reporte.txt`
antes del INSERT del Paso 7.

```sql
-- Misma ventana + mismos tipos procesables del Paso 1, pero filtrando solo
-- los que quedaron sin agendar (candidatos huérfanos después del run actual)
SELECT m.srt_expediente_nro, m.tipo_comunicacion,
       (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date::text AS fecha_notif,
       c.nombre
FROM comunicaciones_miventanilla m
LEFT JOIN casos_srt c ON c.numero_srt = m.srt_expediente_nro
WHERE m.tipo_comunicacion IN (
    'Notificación de Dictamen Médico',
    'Notificación de Constancia de Orden de Estudio',
    'Notificación de Citación',
    'Notificación de Citación al Servicio de Homologación',
    'Notificación de Acto Administrativo',
    'Envío de Comunicación'
  )
  AND m.agendado_en_calendar_at IS NULL
  AND (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
      BETWEEN ((now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date - interval '2 days')::date
          AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
ORDER BY m.fecha_notificacion;
```

Si la query devuelve **0 filas**: todo OK, no tocar el reporte.

Si devuelve **> 0 filas**: son candidatos que el skill no agendó pero debería
haber intentado (salvo los que son `Envío de Comunicación` sin "prestación
dineraria" en el detalle — esos se filtran silenciosos; y los Acto Administrativo
sin "Clausura" en detalle). Apendear al reporte:

```python
# Filtrar los que sí deberían estar agendados (descartar "Envío de Comunicación"
# y "Acto Administrativo" que no matchean sub-tipos procesables)
import json
huerfanos = [h for h in huerfanos_query_result if not (
    (h['tipo_comunicacion'] == 'Envío de Comunicación' and 'prest' not in (h.get('detalle','') or '').lower())
    or (h['tipo_comunicacion'] == 'Notificación de Acto Administrativo' and 'Clausura' not in (h.get('detalle','') or ''))
)]
if huerfanos:
    with open('/tmp/reporte.txt','a') as f:
        f.write('\n\n⚠️ *ALERTA — QUEDARON COMUNICACIONES SIN AGENDAR EN ESTA CORRIDA*\n')
        f.write('_(Revisar manualmente. Puede ser que el agente se haya salteado items,'
                ' o que el scraper todavía no haya subido el texto del PDF.)_\n')
        for h in huerfanos:
            f.write(f"• {h.get('nombre') or '(sin caso)'} ({h['srt_expediente_nro']}) "
                    f"{h['tipo_comunicacion']} notif {h['fecha_notif']}\n")
```

El próximo run (mañana 9am o esta tarde 15:00 AR) los vuelve a intentar.

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
