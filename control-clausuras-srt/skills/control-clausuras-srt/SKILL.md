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

El script del Paso 3 **fetch automáticamente los feriados** del año actual y siguiente desde la API pública `https://api.argentinadatos.com/v1/feriados/{año}` (incluye feriados inamovibles, trasladables y puentes turísticos). Si la API falla, cae a un fallback hardcoded. No requiere mantenimiento manual.

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

### Paso 1b — Rellenar CM NULL con duplicados

Para cada clausura con `cm IS NULL`, buscar si existe otro registro en `casos_srt` con el mismo `nombre` y CM cargada:

```sql
SELECT comision_medica FROM casos_srt
WHERE nombre ILIKE $1 AND comision_medica IS NOT NULL
LIMIT 1;
```

Si se encuentra, actualizar el registro NULL:

```sql
UPDATE casos_srt SET comision_medica = $1
WHERE numero_srt = $2 AND comision_medica IS NULL;
```

### Paso 2 — Eventos de Calendar (con created)

**Crítico**: hay que bajar eventos de AMBOS calendarios con rango amplio. Muchos 15d están solo en el principal y los 90d en ✱ Vencimientos.

Listar eventos con `mcp__claude_ai_Google_Calendar__list_events` en cada calendario:

```
Calendarios:
  - flirteador84@gmail.com (principal)
  - f98t26v6l01v4ss922e069rid0@group.calendar.google.com (✱ Vencimientos)

Params:
  fullText: "VENCE APELAR CLAUSURA"
  pageSize: 250
  startTime: 2025-10-01T00:00:00-03:00   (o hoy-180d si sos conservador)
  endTime: hoy + 220 días (para cubrir 90d de clausuras recientes)
```

**Manejo de overflow**: si la respuesta excede el límite de tokens, queda guardada en un archivo `.txt` automáticamente. En ese caso usar `jq` para extraer solo lo necesario:

```bash
jq -c '.events[] | {summary, start_date: .start.date, created}' /path/to/output.txt
```

Si ambos calendars quedan en archivos separados, combinarlos con dedup por `summary+start_date`:

```bash
python3 <<'EOF'
import json, glob
seen = set()
events = []
for f in ['/tmp/venc.jl', '/tmp/princ.jl']:  # ajustar paths
    try:
        with open(f) as fp:
            for line in fp:
                if not line.strip(): continue
                ev = json.loads(line)
                key = (ev.get('summary',''), ev.get('start_date',''))
                if key in seen: continue
                seen.add(key)
                events.append(ev)
    except FileNotFoundError:
        pass
json.dump(events, open('/tmp/events.json','w'))
print(f'Eventos únicos: {len(events)}')
EOF
```

**Validación**: el archivo `/tmp/events.json` debería tener **al menos 200 eventos** si el rango cubre 6 meses de actividad. Si tiene muy pocos (<50), revisar: probablemente uno de los calendars no se bajó. En ese caso reintentar la query del calendar faltante antes de seguir.

### Paso 3 — Correr el analizador

Crear `/tmp/check.py` con este contenido EXACTO:

```python
import json, re, urllib.request
from datetime import date, datetime, timedelta

# Fallback hardcoded si la API no responde. Actualizar cuando salen nuevos feriados.
FERIADOS_FALLBACK = {
    '2025-12-08','2025-12-25',
    '2026-01-01','2026-02-16','2026-02-17',
    '2026-03-23','2026-03-24',
    '2026-04-02','2026-04-03',
    '2026-05-01','2026-05-25',
    '2026-06-15','2026-06-20',
    '2026-07-09','2026-07-10',
    '2026-08-17','2026-10-12','2026-11-23','2026-12-07','2026-12-08','2026-12-25',
}

def fetch_feriados(year, timeout=10):
    """Trae feriados desde api.argentinadatos.com. Incluye inamovibles, trasladables y puentes turísticos."""
    try:
        url = f'https://api.argentinadatos.com/v1/feriados/{year}'
        req = urllib.request.Request(url, headers={'User-Agent': 'control-clausuras-srt/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return {item['fecha'] for item in data if item.get('fecha')}
    except Exception as e:
        print(f'[WARN] Feriados API falló para {year}: {e}. Usando fallback.', flush=True)
        return None

_hoy = date.today()
FERIADOS_AR = set()
# Traer año anterior, actual y siguiente (plazos 90d cruzan años y dispos ventana 180d)
for y in (_hoy.year - 1, _hoy.year, _hoy.year + 1):
    feriados = fetch_feriados(y)
    if feriados:
        FERIADOS_AR |= feriados
if not FERIADOS_AR:
    FERIADOS_AR = FERIADOS_FALLBACK
    print('[WARN] Usando FERIADOS_FALLBACK', flush=True)
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

SRT_RE = re.compile(r'\b(\d{4,7}/\d{2})\b')
PLAZO_RE = re.compile(r'\((\d+)\s*D[IÍ]AS?\)', re.IGNORECASE)

clausuras = json.load(open('/tmp/clausuras.json'))
events = json.load(open('/tmp/events.json'))

by_srt = {}
for ev in events:
    s = (ev.get('summary') or '').upper()
    if 'CLAUSURA' not in s or 'VENCE' not in s: continue
    ms = SRT_RE.search(s)
    if not ms: continue
    mp = PLAZO_RE.search(s)
    if not mp: continue
    n = int(mp.group(1))
    t = '90d' if n == 90 else ('15d' if n in (15,16) else None)
    if not t: continue
    st = ev.get('start_date') or ev.get('start')
    if not st: continue
    by_srt.setdefault(ms.group(1), []).append({
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
    evs = by_srt.get(cl['srt'], [])
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

### Paso 4 — AUTO-AGENDAR faltantes

Para cada item en `to_create`, crear evento en Google Calendar:

- **calendarId**: `f98t26v6l01v4ss922e069rid0@group.calendar.google.com`
- **summary**: `{nombre} - {srt} - VENCE APELAR CLAUSURA ({15 DIAS|90 DÍAS}) {ciudad}`
  - 15d usa texto `15 DIAS`, 90d usa `90 DÍAS` (con acento)
- **allDay**: true
- **startTime**: `{fecha}T00:00:00`
- **endTime**: `{fecha+1d}T00:00:00`
- **colorId**: `'11'` para 15d, `'10'` para 90d
- **description**: `Fecha de dispo: DD/MM/YYYY — auto-agendado por control-clausuras-srt`
- **timeZone**: `America/Argentina/Buenos_Aires`

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

### Paso 7 — Confirmar

Reportar en la respuesta:
- Total clausuras analizadas
- Eventos agendados hoy (listado)
- Críticos detectados
- Vencidos sin evento
- Sin caso SRT en app
- Agendados la última semana (para control cruzado)
- Status del envío por WhatsApp
