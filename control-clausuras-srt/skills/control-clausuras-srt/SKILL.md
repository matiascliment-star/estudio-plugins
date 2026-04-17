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
version: 1.0.0
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

### Paso 1 — Clausuras últimos 180 días

Supabase:

```sql
SELECT
  m.srt_expediente_nro AS srt,
  (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date::text AS fecha_dispo,
  c.nombre,
  c.comision_medica AS cm
FROM comunicaciones_miventanilla m
LEFT JOIN casos_srt c ON c.numero_srt = m.srt_expediente_nro
WHERE m.tipo_comunicacion = 'Notificación de Acto Administrativo'
  AND m.detalle ILIKE '%Clausura%'
  AND m.fecha_notificacion >= (now() - interval '180 days')
ORDER BY m.fecha_notificacion ASC;
```

→ guardar como JSON array en `/tmp/clausuras.json` con estructura `[{srt, fecha_dispo, nombre, cm}, ...]`.

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
# Si el output vino inline, escribir el JSON crudo con Write
# Si vino en archivo, usar la ruta que devolvió el tool

# Para cada fuente, normalizar a JSONL:
jq -c '.events[] | {id, summary, start_date: (.start.date // (.start.dateTime|.[0:10])), created}' <archivo_raw> >> /tmp/events_all.jsonl
```

Una vez procesados ambos calendarios, dedupear por `id` y convertir a JSON array:

```bash
python3 <<'EOF'
import json
seen = set()
events = []
with open('/tmp/events_all.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        ev = json.loads(line)
        eid = ev.get('id')
        if eid in seen: continue
        seen.add(eid)
        events.append({k: ev.get(k) for k in ('summary','start_date','created')})
json.dump(events, open('/tmp/events.json','w'))
print(f'Eventos únicos: {len(events)}')
EOF
```

**Validación**: `/tmp/events.json` debería tener **al menos 150 eventos** para un rango de 6+ meses. Si queda con menos de 80, reintentar el fetch del calendar que falló antes de seguir. No avanzar con datos parciales (generaría falsos "vencidos sin evento" y "0 críticos" porque no encuentra los eventos que sí existen).

### Paso 3 — Correr el analizador

Crear `/tmp/check.py` con este contenido EXACTO:

```python
import json, re
from datetime import date, datetime, timedelta

# Feriados bajados de la tabla feriados_ar en Paso 1.5 → /tmp/feriados.json
FERIADOS_AR = set(json.load(open('/tmp/feriados.json')))
if len(FERIADOS_AR) < 30:
    raise SystemExit(f'[ERROR] /tmp/feriados.json solo tiene {len(FERIADOS_AR)} feriados. Esperados >= 30 (3 años). Abortando.')
CM_CABA = {'CABA','CM 10L'}
CM_PCIA = ['LA PLATA','LOMAS','BAHIA','BAHÍA','TANDIL','SAN ISIDRO','ZARATE','ZÁRATE',
           'CAMPANA','MAR DEL PLATA','NECOCHEA','AZUL','LANUS','LANÚS','SAN MARTIN',
           'SAN MARTÍN','PILAR','MORON','MORÓN','QUILMES','MORENO','MATANZA','SAN MIGUEL',
           'AVELLANEDA']

def es_caba(cm):
    if cm is None: return None
    u = cm.upper().strip()
    if u in {c.upper() for c in CM_CABA}: return True
    if any(k in u for k in CM_PCIA): return False
    return None

def ciudad_pcia(cm):
    if cm is None: return 'PCIA'
    u = cm.upper()
    for k in CM_PCIA:
        if k in u: return k
    return cm.upper()

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
    """Extrae y normaliza el nro SRT a formato NNNN/YY desde variantes como
    '337272/25', '337272 / 25', '337272-25', '337272/2025'."""
    if not texto: return None
    m = SRT_RE.search(texto)
    if not m: return None
    num, yr = m.group(1), m.group(2)
    if len(yr) == 4: yr = yr[-2:]  # 2025 -> 25
    return f"{num}/{yr}"

clausuras = json.load(open('/tmp/clausuras.json'))
events = json.load(open('/tmp/events.json'))

by_srt = {}
for ev in events:
    s = (ev.get('summary') or '').upper()
    if 'CLAUSURA' not in s or 'VENCE' not in s: continue
    srt_norm = normalizar_srt(s)
    if not srt_norm: continue
    mp = PLAZO_RE.search(s)
    if not mp: continue
    n = int(mp.group(1))
    t = '90d' if n == 90 else ('15d' if n in (15,16) else None)
    if not t: continue
    st = ev.get('start_date') or ev.get('start')
    if not st: continue
    by_srt.setdefault(srt_norm, []).append({
        'tipo': t,
        'fecha': date.fromisoformat(st[:10]),
        'caba': 'CABA' in s,
        'created': ev.get('created'),
    })

hoy = date.today()
hace_7d = hoy - timedelta(days=7)

to_create = []
criticos = []
vencidos_sin_evento = []
sin_caso = []
agendados_ult_semana = []

for cl in clausuras:
    dispo = date.fromisoformat(cl['fecha_dispo'])
    cm = cl.get('cm')
    f15 = sumar_dh(dispo, 15)
    f90 = sumar_dh(dispo, 90)
    srt_norm = normalizar_srt(cl['srt']) or cl['srt']
    evs = by_srt.get(srt_norm, [])
    e15 = [e for e in evs if e['tipo']=='15d']
    e90 = [e for e in evs if e['tipo']=='90d']
    caba = es_caba(cm)
    if caba is None:
        if e15 and e15[0]['caba']: caba = True
        elif e90: caba = False
    if caba is None:
        sin_caso.append({'srt':cl['srt'],'nombre':cl['nombre'],'dispo':dispo.isoformat()})
        continue
    ciudad_ev = 'CABA' if caba else ciudad_pcia(cm)

    def check(tipo, esp, evl):
        if not evl:
            if esp >= hoy:
                to_create.append({'srt':cl['srt'],'nombre':cl['nombre'],'tipo':tipo,
                                  'fecha':esp.isoformat(),'ciudad':ciudad_ev,
                                  'dispo':dispo.isoformat()})
            else:
                vencidos_sin_evento.append({'srt':cl['srt'],'nombre':cl['nombre'],
                                            'tipo':tipo,'fecha':esp.isoformat()})
            return
        ev = evl[0]
        d = diff_dh(esp, ev['fecha'])
        if d > 0:
            criticos.append({'srt':cl['srt'],'nombre':cl['nombre'],'tipo':tipo,
                             'evento':ev['fecha'].isoformat(),'real':esp.isoformat(),'diff':d})
        if ev.get('created'):
            try:
                c_dt = datetime.fromisoformat(ev['created'].replace('Z','+00:00')).date()
                if c_dt >= hace_7d:
                    agendados_ult_semana.append({
                        'srt':cl['srt'],'nombre':cl['nombre'],'tipo':tipo,
                        'evento':ev['fecha'].isoformat(),'real':esp.isoformat(),
                        'diff':d,'ok': d <= 0,
                    })
            except Exception:
                pass

    if caba:
        check('15d CABA', f15, e15)
    else:
        check('90d Pcia', f90, e90)
        check('15d Pcia', f15, e15)

json.dump({
    'to_create':to_create,'criticos':criticos,
    'vencidos':vencidos_sin_evento,'sin_caso':sin_caso,
    'agendados_ult_semana':agendados_ult_semana,
}, open('/tmp/analisis.json','w'))
print(f'Total: {len(clausuras)} | Agendar: {len(to_create)} | Críticos: {len(criticos)} | Vencidos s/evento: {len(vencidos_sin_evento)} | Sin caso: {len(sin_caso)} | Agendados últ. semana: {len(agendados_ult_semana)}')
```

Correr: `python3 /tmp/check.py`

### Paso 4 — AUTO-AGENDAR faltantes (con verificación)

Para cada item en `to_create`, crear evento en Google Calendar con:

- **calendarId**: `f98t26v6l01v4ss922e069rid0@group.calendar.google.com`
- **summary**: `{nombre} - {srt} - VENCE APELAR CLAUSURA ({15 DIAS|90 DÍAS}) {ciudad}`
  - 15d usa texto `15 DIAS`, 90d usa `90 DÍAS` (con acento)
- **allDay**: true
- **startTime**: `{fecha}T00:00:00`
- **endTime**: `{fecha+1d}T00:00:00`
- **colorId**: `'11'` para 15d, `'10'` para 90d
- **description**: `Fecha de dispo: DD/MM/YYYY — auto-agendado por control-clausuras-srt`
- **timeZone**: `America/Argentina/Buenos_Aires`

**IMPORTANTE** — no asumir que el create funcionó. Chequear cada response:
- Si la respuesta trae `"status": "confirmed"` y un `"id"` → se creó OK, agregar a `/tmp/agendados_reales.json`
- Si trae error (401, 403, rate limit, etc.) → agregar a `/tmp/errores_agendar.json` con `{srt, nombre, tipo, fecha, error}`

Al final del paso, sobrescribir en `/tmp/analisis.json` el campo `to_create` con solo los agendados reales. Así el reporte y el log reflejan lo que efectivamente se creó, no lo que se intentó.

### Paso 5 — Generar reporte

```python
import json
from datetime import date
d = json.load(open('/tmp/analisis.json'))
hoy = date.today()
L = [f'📋 *CONTROL CLAUSURAS SRT* — {hoy.strftime("%d/%m/%Y")}']
L.append(f'Agendados hoy: {len(d["to_create"])} | Críticos: {len(d["criticos"])} | Vencidos s/evento: {len(d["vencidos"])} | Sin caso SRT: {len(d["sin_caso"])}')
if d['to_create']:
    L.append('\n✅ *AGENDADOS HOY*')
    for a in d['to_create']:
        L.append(f"• {a['nombre']} ({a['srt']}) {a['tipo']} → {a['fecha']}")
if d['criticos']:
    L.append('\n🔴 *CRÍTICOS — evento DESPUÉS del vencimiento real*')
    for c in d['criticos']:
        L.append(f"• {c['nombre']} ({c['srt']}) {c['tipo']}: evento {c['evento']} vs real {c['real']} (+{c['diff']}hdb)")
if d['vencidos']:
    L.append('\n⚠️ *VENCIDOS SIN EVENTO — verificar si se demandaron*')
    for v in d['vencidos']:
        L.append(f"• {v['nombre']} ({v['srt']}) {v['tipo']} venc {v['fecha']}")
if d['sin_caso']:
    L.append('\n🤷 *SIN CASO SRT CARGADO EN APP*')
    for s in d['sin_caso']:
        L.append(f"• {s['nombre']} ({s['srt']}) dispo {s['dispo']}")
if d['agendados_ult_semana']:
    L.append('\n📅 *AGENDADOS LA ÚLTIMA SEMANA — control cruzado*')
    for a in d['agendados_ult_semana']:
        mark = '✅' if a['ok'] else f"🔴 (+{a['diff']}hdb)"
        L.append(f"• {a['nombre']} ({a['srt']}) {a['tipo']}: {a['evento']} vs real {a['real']} {mark}")
if not d['to_create'] and not d['criticos'] and not d['vencidos'] and not d['sin_caso'] and not d['agendados_ult_semana']:
    L.append('\n✅ Todo en orden. Sin acciones pendientes.')
open('/tmp/reporte.txt','w').write('\n'.join(L))
print(open('/tmp/reporte.txt').read())
```

### Paso 6 — Enviar por WhatsApp

Usar el MCP de WhatsApp (`mcp__whatsapp__wa_send_text`):

- **instanceId**: `inst_d9c22079`
- **to**: `120363182236641964@g.us` (grupo "Control Dispos SRT")
- **text**: contenido de `/tmp/reporte.txt`

Si el MCP de WhatsApp no está disponible por alguna razón, fallback con curl a la edge function de Supabase:

```bash
REPORTE=$(cat /tmp/reporte.txt)
curl -sX POST "https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send" \
  -H "Content-Type: application/json" \
  --data "$(jq -n --arg text "$REPORTE" '{chatId:"120363182236641964@g.us", text:$text}')"
```

Verificar que el send devuelva `{status: "queued", jobId: ...}`. Si falla, reintentar 1 vez.

### Paso 7 — Guardar run en Supabase (historial)

Después de enviar por WhatsApp, guardar el run completo en la tabla `control_clausuras_runs` para tener histórico auditable:

```sql
INSERT INTO control_clausuras_runs (
  total_clausuras, agendados_hoy, criticos, vencidos_sin_evento,
  sin_caso_srt, agendados_ult_semana, whatsapp_jobid, errores, reporte_texto
) VALUES (
  $total,
  $agendados_hoy_jsonb,
  $criticos_jsonb,
  $vencidos_jsonb,
  $sin_caso_jsonb,
  $agendados_ult_semana_jsonb,
  $whatsapp_jobid,
  $errores_jsonb,
  $reporte_texto
)
RETURNING id, ejecutado_at;
```

Usar jsonb con los arrays del `/tmp/analisis.json`. El `reporte_texto` es el contenido completo del mensaje que se mandó por WhatsApp. `whatsapp_jobid` es el jobId devuelto por el MCP o la edge function (null si falló). `errores` captura cualquier problema de agendamiento del Paso 4.

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
