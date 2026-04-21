---
name: control-clausuras-srt
description: >
  Chequeo semanal (lunes 10am AR) de Disposiciones de Clausura de la SRT.
  Verifica que cada clausura tenga agendado sus vencimientos en Google Calendar
  con fecha correcta (15 d.h. CABA, 15 + 90 d.h. Pcia), rellena CM NULL con
  duplicados del mismo nombre, auto-agenda los faltantes con plazo vigente,
  y manda reporte por WhatsApp al grupo "Control Dispos SRT". Usar cuando el
  usuario pida: "control clausuras", "revisar dispos SRT", "chequear vencimientos
  clausura", "briefing clausuras". Triggers: "control clausuras", "dispos SRT",
  "vencimientos clausura", "clausuras srt".
version: 2.0.0
---

# Control de Clausuras SRT

## OBJETIVO

Chequeo semanal (lunes 10:00 AR): verificar que toda Disposición de Clausura tenga sus eventos de vencimiento en Google Calendar con fechas correctas, agendar los faltantes, y mandar reporte por WhatsApp al grupo "Control Dispos SRT".

## REGLAS CLAVE

- **Día 1** = día hábil SIGUIENTE a la notificación (`fecha_notificacion`)
- **CABA** (CM = "CABA" o "CM 10L"): 1 evento a 15 días hábiles
- **Pcia BsAs** (CM con ciudad bonaerense): 2 eventos — 15 d.h. + 90 d.h. (el 90d es el principal/crítico)
- **Crítico** solo si el evento está DESPUÉS del vencimiento real. Si está antes o igual, OK (el estudio presenta temprano, no pierde plazo).
- Solo auto-agendar si el plazo está vigente y el CM es conocido.
- **Nunca modificar ni borrar** eventos existentes.

## DATOS DE REFERENCIA

- **Supabase**: project_id `wdgdbbcwcrirpnfdmykh`
- **Calendarios** a inspeccionar:
  - Principal: `flirteador84@gmail.com`
  - `✱ Vencimientos`: `f98t26v6l01v4ss922e069rid0@group.calendar.google.com`
- **WhatsApp grupo** "Control Dispos SRT": chatId `120363182236641964@g.us`
- **Edge function para enviar WA**: `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`

### CM conocidas

- **CABA**: `CABA`, `CM 10L`
- **Pcia BsAs**: cualquier CM que contenga `LA PLATA`, `LOMAS`, `BAHIA`/`BAHÍA`, `TANDIL`, `SAN ISIDRO`, `ZARATE`/`ZÁRATE`, `CAMPANA`, `MAR DEL PLATA`, `NECOCHEA`, `AZUL`, `LANUS`/`LANÚS`, `SAN MARTIN`/`SAN MARTÍN`, `PILAR`, `MORON`/`MORÓN`, `QUILMES`, `MORENO`, `MATANZA`, `SAN MIGUEL`, `AVELLANEDA`.

### Feriados AR

Los feriados están en la tabla **`feriados_ar`** de Supabase (project `wdgdbbcwcrirpnfdmykh`). Incluye feriados inamovibles, trasladables y puentes turísticos. Paso 1.5 los baja a `/tmp/feriados.json`. **Mantenimiento**: cada diciembre hacer INSERT del próximo año con datos de `https://api.argentinadatos.com/v1/feriados/{año}`.

## WORKFLOW

### Paso 1 — Clausuras últimos 180 días (+ texto del PDF truncado)

Supabase. Texto limitado a 6000 chars: suficiente para detectar CM emisora y
frase de acuerdo (ambos aparecen en los primeros considerandos).

```sql
SELECT
  m.srt_expediente_nro AS srt,
  (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date::text AS fecha_dispo,
  c.nombre,
  c.comision_medica AS cm,
  a.texto_extraido AS texto_clausura,
  -- fallback si el PDF de la clausura aún no tiene texto extraído
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
WHERE m.tipo_comunicacion = 'Notificación de Acto Administrativo'
  AND m.detalle ILIKE '%Clausura%'
  AND m.fecha_notificacion >= (now() - interval '180 days')
ORDER BY m.fecha_notificacion ASC;
```

→ guardar como JSON array en `/tmp/clausuras.json` con estructura
`[{srt, fecha_dispo, nombre, cm, texto_clausura, texto_dictamen_previo}, ...]`.

El texto sirve para clasificar cada clausura en 3 variantes:
1. **Con acuerdo** (homologación del acuerdo) → 5 d.h. contestar intimación, color amarillo
2. **Rechazo CABA** (CM 10/10L firma) → 15 d.h. apelar, color rojo
3. **Rechazo Pcia** (cualquier otra CM firma) → 15 + 90 d.h. apelar, color verde

### Paso 1b — Rellenar CM NULL con duplicados (UPDATE bulk)

Ejecutar una sola query que actualiza en masa los CM NULL con CMs encontradas en duplicados del mismo `nombre`:

```sql
UPDATE casos_srt AS c SET comision_medica = dup.cm
FROM (
    SELECT DISTINCT ON (nombre) nombre, comision_medica AS cm
    FROM casos_srt WHERE comision_medica IS NOT NULL
    ORDER BY nombre, updated_at DESC NULLS LAST
) dup
WHERE c.comision_medica IS NULL
  AND c.nombre = dup.nombre
  AND c.numero_srt IN (
    SELECT srt_expediente_nro FROM comunicaciones_miventanilla
    WHERE tipo_comunicacion = 'Notificación de Acto Administrativo'
      AND detalle ILIKE '%Clausura%'
      AND fecha_notificacion >= (now() - interval '180 days')
  )
RETURNING c.numero_srt, c.nombre, c.comision_medica;
```

**IMPORTANTE**: después de correr este UPDATE, **re-ejecutar el query del Paso 1** para obtener `clausuras.json` con los CMs actualizados. Sin este refresh, los casos rellenados quedarían como NULL en el análisis.

### Paso 1.5 — Bajar feriados AR

Query a Supabase para traer los feriados nacionales + días no laborables:

```sql
SELECT fecha::text FROM feriados_ar
WHERE fecha BETWEEN (now() - interval '1 year')::date AND (now() + interval '1 year')::date
ORDER BY fecha;
```

Guardar el resultado como `/tmp/feriados.json` con estructura `["2026-01-01", "2026-02-16", ...]` (array de strings YYYY-MM-DD).

### Paso 2 — Eventos de Calendar (con created)

**Crítico**: hay que bajar eventos de AMBOS calendarios con rango amplio. Muchos 15d están solo en el principal y los 90d en ✱ Vencimientos. El rango tiene que cubrir clausuras de hasta **180 días atrás** (sus eventos 15d pudieron ser agendados recientemente pero los 90d están a 6 meses vista).

Llamar `mcp__claude_ai_Google_Calendar__list_events` en cada calendario con estos params:

```
calendarId: <uno de los dos>
fullText: "VENCE APELAR CLAUSURA"
pageSize: 250
startTime: hoy - 200 días, en ISO con timezone -03:00
endTime:   hoy + 220 días, en ISO con timezone -03:00
```

**Manejo del output**: para CADA calendario, la respuesta viene inline O en un archivo `.txt` (si excede tokens). Guardar ambos como JSONL y combinar después:

```bash
# Para cada fuente, normalizar a JSONL incluyendo colorId y description.
# Antes del jq, AGREGAR manualmente el campo "calendar_origin" con 'principal' o 'vencimientos'
# según qué calendario se estaba procesando (el MCP no devuelve el calendarId en cada event).

# Ejemplo (calendar vencimientos):
jq -c '.events[] | {
  id, summary, colorId,
  start_date: (.start.date // (.start.dateTime|.[0:10])),
  created, description,
  calendar_origin: "vencimientos"
}' <archivo_raw_venc> >> /tmp/events_all.jsonl

# Y para el principal:
jq -c '.events[] | {
  id, summary, colorId,
  start_date: (.start.date // (.start.dateTime|.[0:10])),
  created, description,
  calendar_origin: "principal"
}' <archivo_raw_princ> >> /tmp/events_all.jsonl
```

Una vez procesados ambos calendarios, CONSERVAR todos los eventos (no dedupear por id
porque un mismo plazo puede tener 2 eventos — uno en principal + uno en vencimientos —
y necesitamos detectar duplicados faltantes):

```bash
python3 <<'EOF'
import json
events = []
with open('/tmp/events_all.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        events.append(json.loads(line))
json.dump(events, open('/tmp/events.json','w'))
print(f'Eventos totales (sin dedup): {len(events)}')
EOF
```

**Validación**: `/tmp/events.json` debería tener **al menos 150 eventos** para un rango de 6+ meses. Si queda con menos de 80, reintentar el fetch del calendar que falló antes de seguir. No avanzar con datos parciales (generaría falsos "vencidos sin evento" y "0 críticos" porque no encuentra los eventos que sí existen).

### Paso 3 — Correr el analizador

Crear `/tmp/check.py` con este contenido EXACTO:

```python
import json, re
from datetime import date, datetime, timedelta

FERIADOS_AR = set(json.load(open('/tmp/feriados.json')))
if len(FERIADOS_AR) < 30:
    raise SystemExit(f'[ERROR] /tmp/feriados.json tiene {len(FERIADOS_AR)} feriados. Abortando.')

CAL_VENC_ID = 'f98t26v6l01v4ss922e069rid0@group.calendar.google.com'
CAL_PRINC_ID = 'flirteador84@gmail.com'

# Color mapping esperado por variante (según convenciones del estudio)
COLOR_ACUERDO = '5'   # amarillo
COLOR_CABA    = '11'  # rojo
COLOR_PCIA    = '10'  # verde

# ═══════ Helpers de parseo PDF (idénticos a agendar-comunicaciones-srt) ═══════

def detectar_cm_emisora(texto):
    """Extrae el código de la CM que firma (no la ciudad de emisión).
    Ej: 'DIAPA-2026-7647-APN-SHC10#SRT' → '10' (CABA)
        'Comisión Medica N° 37 de la localidad de QUILMES' → '37' (Pcia)
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
        if m: return m.group(1).strip().upper()
    return None

def cm_es_caba(codigo):
    if not codigo: return None
    return bool(re.fullmatch(r'10[A-Z]*', codigo.strip().upper()))

def es_clausura_con_acuerdo(texto):
    if not texto: return False
    tl = texto.lower()
    return ('resolvieron celebrar el acuerdo acompañado' in tl
            or 'resolvieron celebrar el acuerdo acompanado' in tl
            or 'homológase el acuerdo celebrado' in tl
            or 'homologase el acuerdo celebrado' in tl)

# ═══════ Helpers de fechas ═══════

def sumar_dh(fi, n):
    d = fi; c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() >= 5: continue
        if d.isoformat() in FERIADOS_AR: continue
        c += 1
    return d

def diff_dh(d1, d2):
    if d1 == d2: return 0
    sign = 1 if d2 > d1 else -1
    a, b = (d1, d2) if d2 > d1 else (d2, d1)
    c = 0
    while a < b:
        a += timedelta(days=1)
        if a.weekday() >= 5: continue
        if a.isoformat() in FERIADOS_AR: continue
        c += 1
    return sign * c

SRT_RE = re.compile(r'\b(\d{3,7})\s*[/\-]\s*(\d{2,4})\b')
PLAZO_RE = re.compile(r'\((\d+)\s*D[IÍ]AS?\)', re.IGNORECASE)

def normalizar_srt(texto):
    if not texto: return None
    m = SRT_RE.search(texto)
    if not m: return None
    num, yr = m.group(1), m.group(2)
    if len(yr) == 4: yr = yr[-2:]
    return f"{num}/{yr}"

# ═══════ Análisis ═══════

clausuras = json.load(open('/tmp/clausuras.json'))
events = json.load(open('/tmp/events.json'))

# Indexar eventos: (srt_norm, tipo_plazo) → [eventos en principal, eventos en vencimientos]
by_srt = {}
for ev in events:
    s = (ev.get('summary') or '').upper()
    if 'CLAUSURA' not in s or 'VENCE' not in s: continue
    srt_norm = normalizar_srt(s)
    if not srt_norm: continue
    mp = PLAZO_RE.search(s)
    n = int(mp.group(1)) if mp else None
    # Tipo: 5d (acuerdo/contestar), 15d (apelar), 90d (apelar Pcia)
    if 'CONTESTAR' in s and 'ACUERDO' in s: t = '5d'
    elif n == 90: t = '90d'
    elif n in (15, 16, 5): t = '15d' if n in (15,16) else '5d'
    else: t = None
    if not t: continue
    st = ev.get('start_date')
    if not st: continue
    by_srt.setdefault(srt_norm, []).append({
        'id': ev.get('id'), 'tipo': t,
        'fecha': date.fromisoformat(st[:10]),
        'colorId': ev.get('colorId'),
        'calendar_origin': ev.get('calendar_origin'),
        'summary': ev.get('summary'),
        'description': ev.get('description') or '',
        'caba_txt': 'CABA' in s,
        'created': ev.get('created'),
    })

hoy = date.today()
hace_7d = hoy - timedelta(days=7)

to_create = []          # clausuras con evento faltante → agendar nuevo
criticos = []           # evento agendado DESPUÉS del vencimiento real
vencidos_sin_evento = []
sin_caso = []
agendados_ult_semana = []
color_mal = []          # evento con colorId distinto al esperado
jurisdiccion_mal = []   # evento dice "CABA" pero PDF dice Pcia o viceversa
duplicado_faltante = [] # clausura que debería estar en los 2 calendarios pero solo está en 1
acuerdo_mal_agendado = []  # clausura con acuerdo que tiene evento de 15d/90d en vez de 5d

def clasificar_variante(cl):
    """Devuelve: ('acuerdo', 5, amarillo) o ('rechazo_caba', 15, rojo) o ('rechazo_pcia', 15+90, verde) o None."""
    texto = cl.get('texto_clausura') or ''
    if es_clausura_con_acuerdo(texto):
        return {'variante': 'acuerdo', 'plazos': [5], 'color': COLOR_ACUERDO, 'tipos': ['5d']}
    # Es rechazo → detectar jurisdicción por CM emisora del PDF
    codigo = detectar_cm_emisora(texto) or detectar_cm_emisora(cl.get('texto_dictamen_previo'))
    is_caba = None
    if codigo:
        is_caba = cm_es_caba(codigo)
    else:
        # Fallback al campo manual casos_srt.comision_medica
        cm = (cl.get('cm') or '').upper()
        if cm in ('CABA','CM 10','CM 10L'): is_caba = True
        elif cm: is_caba = False
    if is_caba is None:
        return None  # no se puede clasificar
    if is_caba:
        return {'variante': 'rechazo_caba', 'plazos': [15], 'color': COLOR_CABA, 'tipos': ['15d']}
    else:
        return {'variante': 'rechazo_pcia', 'plazos': [15, 90], 'color': COLOR_PCIA, 'tipos': ['15d', '90d']}

for cl in clausuras:
    dispo = date.fromisoformat(cl['fecha_dispo'])
    srt = cl['srt']
    srt_norm = normalizar_srt(srt) or srt
    nombre = cl['nombre'] or '(SIN NOMBRE)'
    evs = by_srt.get(srt_norm, [])

    clasif = clasificar_variante(cl)
    if clasif is None:
        sin_caso.append({'srt':srt,'nombre':nombre,'dispo':dispo.isoformat(),
                         'razon':'no hay texto PDF ni cm en casos_srt'})
        continue

    # Fechas esperadas por plazo
    fechas_esp = {f'{n}d': sumar_dh(dispo, n) for n in clasif['plazos']}
    color_esp = clasif['color']
    variante = clasif['variante']

    # Detectar "acuerdo mal agendado": clausura es acuerdo pero hay evento 15d/90d
    if variante == 'acuerdo':
        mal = [e for e in evs if e['tipo'] in ('15d','90d')]
        if mal:
            for e in mal:
                acuerdo_mal_agendado.append({
                    'srt':srt,'nombre':nombre,
                    'evento_id':e['id'],'evento_tipo':e['tipo'],
                    'fecha':e['fecha'].isoformat(),
                    'calendar':e['calendar_origin'],
                    'nota':'clausura es CON ACUERDO (5d contestar), no rechazo'
                })

    for tipo in clasif['tipos']:
        esp = fechas_esp[tipo]
        evs_tipo = [e for e in evs if e['tipo'] == tipo]

        if not evs_tipo:
            if esp >= hoy:
                to_create.append({'srt':srt,'nombre':nombre,'tipo':f'{tipo} {variante}',
                                  'fecha':esp.isoformat(),'variante':variante,
                                  'color':color_esp,'dispo':dispo.isoformat()})
            else:
                vencidos_sin_evento.append({'srt':srt,'nombre':nombre,'tipo':tipo,
                                            'fecha':esp.isoformat()})
            continue

        # Verificar cada evento encontrado (puede haber 2: uno en principal, uno en vencimientos)
        origenes = {e['calendar_origin'] for e in evs_tipo}

        # Check duplicado faltante: para TODAS las variantes debería haber evento en los 2 calendarios
        if 'principal' not in origenes:
            evs_venc = [e for e in evs_tipo if e['calendar_origin']=='vencimientos']
            for e in evs_venc:
                duplicado_faltante.append({
                    'srt':srt,'nombre':nombre,'tipo':tipo,
                    'falta_en':'principal','evento_id':e['id'],
                    'fecha':e['fecha'].isoformat(),'color':e.get('colorId'),
                    'description':e.get('description',''),
                })
        if 'vencimientos' not in origenes:
            evs_pr = [e for e in evs_tipo if e['calendar_origin']=='principal']
            for e in evs_pr:
                duplicado_faltante.append({
                    'srt':srt,'nombre':nombre,'tipo':tipo,
                    'falta_en':'vencimientos','evento_id':e['id'],
                    'fecha':e['fecha'].isoformat(),'color':e.get('colorId'),
                    'description':e.get('description',''),
                })

        for e in evs_tipo:
            d = diff_dh(esp, e['fecha'])

            # Check fecha: crítico si evento está DESPUÉS del vencimiento
            if d > 0:
                criticos.append({'srt':srt,'nombre':nombre,'tipo':tipo,
                                 'evento':e['fecha'].isoformat(),'real':esp.isoformat(),
                                 'diff':d,'evento_id':e['id'],'calendar':e['calendar_origin']})

            # Check color
            color_actual = e.get('colorId')
            if color_actual and color_actual != color_esp:
                auto_fix = 'auto-agendado' in (e.get('description') or '').lower()
                color_mal.append({
                    'srt':srt,'nombre':nombre,'tipo':tipo,
                    'evento_id':e['id'],'calendar':e['calendar_origin'],
                    'color_actual':color_actual,'color_esp':color_esp,
                    'variante':variante,'auto_fix':auto_fix,
                })

            # Check jurisdicción: el summary del evento dice CABA o PCIA
            if variante in ('rechazo_caba','rechazo_pcia'):
                summary_caba = e['caba_txt']
                esperado_caba = (variante == 'rechazo_caba')
                if summary_caba != esperado_caba:
                    jurisdiccion_mal.append({
                        'srt':srt,'nombre':nombre,'tipo':tipo,
                        'evento_id':e['id'],'calendar':e['calendar_origin'],
                        'summary':e['summary'],
                        'variante_real':variante,
                        'nota':'el summary del evento y la jurisdicción según PDF no coinciden',
                    })

            # Registro de agendados última semana
            if e.get('created'):
                try:
                    c_dt = datetime.fromisoformat(e['created'].replace('Z','+00:00')).date()
                    if c_dt >= hace_7d:
                        agendados_ult_semana.append({
                            'srt':srt,'nombre':nombre,'tipo':tipo,
                            'evento':e['fecha'].isoformat(),'real':esp.isoformat(),
                            'diff':d,'ok': d <= 0,
                            'calendar':e['calendar_origin'],
                        })
                except Exception:
                    pass

json.dump({
    'to_create':to_create,
    'criticos':criticos,
    'vencidos':vencidos_sin_evento,
    'sin_caso':sin_caso,
    'agendados_ult_semana':agendados_ult_semana,
    'color_mal':color_mal,
    'jurisdiccion_mal':jurisdiccion_mal,
    'duplicado_faltante':duplicado_faltante,
    'acuerdo_mal_agendado':acuerdo_mal_agendado,
}, open('/tmp/analisis.json','w'))
print(f'Total: {len(clausuras)} | Agendar: {len(to_create)} | Críticos fecha: {len(criticos)} | '
      f'Color mal: {len(color_mal)} | Jurisdicción mal: {len(jurisdiccion_mal)} | '
      f'Duplicado faltante: {len(duplicado_faltante)} | Acuerdo mal agendado: {len(acuerdo_mal_agendado)} | '
      f'Vencidos: {len(vencidos_sin_evento)} | Sin caso: {len(sin_caso)}')
```

Correr: `python3 /tmp/check.py`

### Paso 4 — AUTO-AGENDAR faltantes (con verificación)

Para cada item en `to_create` del análisis, crear eventos en los **2 calendarios**
(principal + ✱ Vencimientos) con el formato verificado:

```
create_event(
    calendarId = <principal o vencimientos>,
    summary = <ver abajo>,
    startTime = "{fecha}T00:00:00Z",
    endTime   = "{fecha + 1 día}T00:00:00Z",   # end-exclusive → 1 solo día
    allDay = True,
    timeZone = "America/Argentina/Buenos_Aires",
    colorId = <item.color>,
    description = "Fecha de dispo: DD/MM/YYYY — auto-agendado por control-clausuras-srt",
)
```

**Summary y colorId según variante**:

| Variante | Plazo | colorId | Summary |
|----------|-------|---------|---------|
| `acuerdo` | 5d | `5` (amarillo) | `{nombre} - {srt} - VENCE CONTESTAR INTIMACION CLAUSURA (ACUERDO)` |
| `rechazo_caba` | 15d | `11` (rojo) | `{nombre} - {srt} - VENCE APELAR CLAUSURA (15 DIAS) CABA` |
| `rechazo_pcia` | 15d + 90d | `10` (verde) | `{nombre} - {srt} - VENCE APELAR CLAUSURA ({15 DIAS\|90 DÍAS}) {ciudad}` |

15d usa texto `15 DIAS`, 90d usa `90 DÍAS` (con acento).

**IMPORTANTE**: cada clausura genera 2 eventos (uno por calendario). Agregar a
`/tmp/agendados_reales.json` con `{srt, nombre, tipo, fecha, calendar, event_id}`.
Si alguna respuesta trae error, agregar a `/tmp/errores_agendar.json`.

### Paso 4b — AUTO-CORREGIR colores (solo eventos de Claude)

Para cada item en `color_mal` del análisis con `auto_fix: true` (description tiene
"auto-agendado"):

```
update_event(
    calendarId = <item.calendar> (principal o vencimientos según su origen),
    eventId = <item.evento_id>,
    colorId = <item.color_esp>,
)
```

Si `auto_fix: false` (lo creó un humano) → NO tocar, dejar solo en el reporte.

Registrar en `/tmp/colores_corregidos.json` los que se corrigieron OK.

### Paso 4c — DUPLICAR en calendar faltante (solo eventos de Claude)

Para cada item en `duplicado_faltante` cuya description contenga "auto-agendado":

```
create_event(
    calendarId = <item.falta_en>,      # el calendar donde NO estaba
    summary    = <igual al evento original>,
    startTime  = "{item.fecha}T00:00:00Z",
    endTime    = "{item.fecha + 1 día}T00:00:00Z",
    allDay     = True,
    timeZone   = "America/Argentina/Buenos_Aires",
    colorId    = <item.color si es válido, sino recalcular según variante>,
    description = <igual al original>,
)
```

Si el original NO tiene "auto-agendado" en description → NO crear, solo reportar
(fue un humano el que agendó en 1 solo calendar, no pisamos su criterio).

Registrar en `/tmp/duplicados_creados.json`.

### Paso 4d — Reportar eventos de acuerdo mal agendados

Los items en `acuerdo_mal_agendado` (clausuras con acuerdo que tienen evento 15d/90d)
**solo se reportan**, no se auto-corrigen. La decisión de borrar los eventos viejos
la toma un humano porque puede ser intencional (ej: por si apelan el acuerdo).

### Paso 5 — Generar reporte

```python
import json, os
from datetime import date

d = json.load(open('/tmp/analisis.json'))
hoy = date.today()

# Cargar listas de correcciones ejecutadas en Paso 4
agendados_reales   = json.load(open('/tmp/agendados_reales.json'))   if os.path.exists('/tmp/agendados_reales.json')   else []
colores_corregidos = json.load(open('/tmp/colores_corregidos.json')) if os.path.exists('/tmp/colores_corregidos.json') else []
duplicados_creados = json.load(open('/tmp/duplicados_creados.json')) if os.path.exists('/tmp/duplicados_creados.json') else []

L = [f'📋 *CONTROL CLAUSURAS SRT* — {hoy.strftime("%d/%m/%Y")}']

resumen = (f'Agendados: {len(agendados_reales)} | Colores corregidos: {len(colores_corregidos)} | '
           f'Duplicados creados: {len(duplicados_creados)} | Críticos fecha: {len(d["criticos"])} | '
           f'Color mal: {len(d["color_mal"])} | Jurisdicción mal: {len(d["jurisdiccion_mal"])} | '
           f'Duplicado faltante: {len(d["duplicado_faltante"])} | Acuerdo mal: {len(d["acuerdo_mal_agendado"])} | '
           f'Vencidos s/evento: {len(d["vencidos"])} | Sin caso: {len(d["sin_caso"])}')
L.append(resumen)

if agendados_reales:
    L.append('\n✅ *AGENDADOS HOY*')
    for a in agendados_reales:
        L.append(f"• {a['nombre']} ({a['srt']}) {a['tipo']} → {a['fecha']} [{a.get('calendar','')}]")

if colores_corregidos:
    L.append('\n🎨 *COLORES CORREGIDOS (auto)*')
    for c in colores_corregidos:
        L.append(f"• {c['nombre']} ({c['srt']}) {c['tipo']}: {c.get('color_actual')} → {c.get('color_esp')}")

if duplicados_creados:
    L.append('\n🔁 *DUPLICADOS CREADOS (auto, en calendar faltante)*')
    for dup in duplicados_creados:
        L.append(f"• {dup['nombre']} ({dup['srt']}) {dup['tipo']} en {dup['falta_en']}")

if d['criticos']:
    L.append('\n🔴 *CRÍTICOS — evento DESPUÉS del vencimiento real*')
    for c in d['criticos']:
        L.append(f"• {c['nombre']} ({c['srt']}) {c['tipo']}: evento {c['evento']} vs real {c['real']} (+{c['diff']}hdb)")

if d['color_mal']:
    pendientes = [c for c in d['color_mal'] if not c.get('auto_fix')]
    if pendientes:
        L.append('\n🎨 *COLOR MAL — agendado por humano, revisar manualmente*')
        for c in pendientes:
            L.append(f"• {c['nombre']} ({c['srt']}) {c['tipo']}: color {c['color_actual']} (esperado {c['color_esp']} {c['variante']}) [{c['calendar']}]")

if d['jurisdiccion_mal']:
    L.append('\n🧭 *JURISDICCIÓN MAL — summary dice CABA/Pcia distinto al PDF*')
    for j in d['jurisdiccion_mal']:
        L.append(f"• {j['nombre']} ({j['srt']}) {j['tipo']}: {j['summary'][:60]} → PDF dice {j['variante_real']}")

if d['duplicado_faltante']:
    pendientes = [x for x in d['duplicado_faltante'] if 'auto-agendado' not in (x.get('description') or '').lower()]
    if pendientes:
        L.append('\n🔁 *DUPLICADO FALTANTE — agendado por humano solo en 1 calendar*')
        for x in pendientes:
            L.append(f"• {x['nombre']} ({x['srt']}) {x['tipo']} falta en {x['falta_en']} (fecha {x['fecha']})")

if d['acuerdo_mal_agendado']:
    L.append('\n⚠️ *ACUERDO MAL AGENDADO — clausura con acuerdo tiene evento de apelación (15d/90d)*')
    for a in d['acuerdo_mal_agendado']:
        L.append(f"• {a['nombre']} ({a['srt']}): evento {a['evento_tipo']} fecha {a['fecha']} — revisar manual")

if d['vencidos']:
    L.append('\n⚠️ *VENCIDOS SIN EVENTO — verificar si se demandaron*')
    for v in d['vencidos']:
        L.append(f"• {v['nombre']} ({v['srt']}) {v['tipo']} venc {v['fecha']}")

if d['sin_caso']:
    L.append('\n🤷 *SIN CASO SRT / SIN DATOS DE JURISDICCIÓN*')
    for s in d['sin_caso']:
        L.append(f"• {s['nombre']} ({s['srt']}) dispo {s['dispo']}")

if d['agendados_ult_semana']:
    L.append('\n📅 *AGENDADOS LA ÚLTIMA SEMANA — control cruzado*')
    for a in d['agendados_ult_semana']:
        mark = '✅' if a['ok'] else f"🔴 (+{a['diff']}hdb)"
        L.append(f"• {a['nombre']} ({a['srt']}) {a['tipo']}: {a['evento']} vs real {a['real']} {mark}")

nada_que_reportar = not any([
    agendados_reales, colores_corregidos, duplicados_creados,
    d['criticos'], d['color_mal'], d['jurisdiccion_mal'],
    d['duplicado_faltante'], d['acuerdo_mal_agendado'],
    d['vencidos'], d['sin_caso'], d['agendados_ult_semana'],
])
if nada_que_reportar:
    L.append('\n✅ Todo en orden. Sin acciones pendientes.')

open('/tmp/reporte.txt','w').write('\n'.join(L))
print(open('/tmp/reporte.txt').read())
```

### Paso 6 — (sin paso manual de envío)

**El envío por WhatsApp es automático** al hacer el INSERT del Paso 7. La tabla `control_clausuras_runs` tiene un trigger (`trg_control_clausuras_wa`) que al insertar un run llama a `pg_net.http_post` → edge function `wa-send` → MCP WhatsApp → grupo "Control Dispos SRT".

Esto evita el sandbox egress de Anthropic: toda la cadena de envío corre del lado de Supabase.

El skill solo tiene que **generar el reporte y meterlo en el INSERT del Paso 7**.

### Paso 7 — Guardar run en Supabase (dispara WhatsApp automáticamente)

⚠️ **IMPORTANTE**: NO hacer el INSERT vía MCP `execute_sql` — el payload de 20KB+
entra al contexto del modelo y puede causar timeout idle > 10 min entre generar
SQL y llamar el tool. En su lugar, hacer **POST directo al REST API de Supabase
desde Python**, así el payload nunca toca el contexto del modelo.

```python
import json, os, urllib.request

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://wdgdbbcwcrirpnfdmykh.supabase.co')
SUPABASE_KEY = os.environ['SUPABASE_KEY']  # service_role, configurado en el entorno

d = json.load(open('/tmp/analisis.json'))
agendados_reales   = json.load(open('/tmp/agendados_reales.json'))   if os.path.exists('/tmp/agendados_reales.json')   else []
colores_corregidos = json.load(open('/tmp/colores_corregidos.json')) if os.path.exists('/tmp/colores_corregidos.json') else []
duplicados_creados = json.load(open('/tmp/duplicados_creados.json')) if os.path.exists('/tmp/duplicados_creados.json') else []
reporte = open('/tmp/reporte.txt').read()
clausuras = json.load(open('/tmp/clausuras.json'))

criticos_consolidado = {
    'fecha': d['criticos'],
    'color_mal': d['color_mal'],
    'jurisdiccion_mal': d['jurisdiccion_mal'],
    'duplicado_faltante': d['duplicado_faltante'],
    'acuerdo_mal_agendado': d['acuerdo_mal_agendado'],
    'colores_corregidos': colores_corregidos,
    'duplicados_creados': duplicados_creados,
}

payload = {
    'total_clausuras': len(clausuras),
    'agendados_hoy': agendados_reales,
    'criticos': criticos_consolidado,
    'vencidos_sin_evento': d['vencidos'],
    'sin_caso_srt': d['sin_caso'],
    'agendados_ult_semana': d['agendados_ult_semana'],
    'errores': [],
    'reporte_texto': reporte,
}

req = urllib.request.Request(
    f'{SUPABASE_URL}/rest/v1/control_clausuras_runs',
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=60) as resp:
    body = resp.read().decode()
    row = json.loads(body)[0]
    print(f"RUN ID: {row['id']} | ejecutado_at: {row['ejecutado_at']} | wa_jobid: {row.get('whatsapp_jobid')}")
```

Correr con `SUPABASE_KEY=... python3 /tmp/insert.py`. El script imprime el ID
del run + el jobid de WhatsApp. Eso es lo único que ve el agente en el contexto.

El trigger de Supabase (`trg_control_clausuras_wa`) detecta el INSERT, lee
`reporte_texto` y lo manda por WhatsApp via pg_net + edge function `wa-send`
al grupo "Control Dispos SRT" (`wa_chat_id` default `120363182236641964@g.us`).

### Paso 7.5 — Fallback si pg_net falla

Si el `whatsapp_jobid` es NULL (el trigger DB no disparó o la edge function falló),
el agente debe mandar el reporte **directamente** via MCP WhatsApp:

```
wa_send_text(chat_id="120363182236641964@g.us", text=<contenido de /tmp/reporte.txt>)
```

Esto garantiza que el reporte llegue aunque la cadena pg_net → edge function se caiga.

Después del INSERT, el campo `whatsapp_jobid` queda como `pg_net:<N>`. Para confirmar que el envío salió OK:

```sql
SELECT id, status_code, error_msg FROM net._http_response ORDER BY id DESC LIMIT 1;
```

Un `status_code=200` con `error_msg=null` significa que WA ack. Si es distinto, ver `content` para diagnóstico.

### Paso 8 — Confirmar

Reportar en la respuesta:
- Total clausuras analizadas
- Eventos agendados hoy (listado real, no planeado)
- Errores de agendamiento (si los hubo)
- Críticos detectados
- Vencidos sin evento
- Sin caso SRT en app
- Agendados la última semana
- Status del envío por WhatsApp (jobId o error)
- ID del run guardado en `control_clausuras_runs`
