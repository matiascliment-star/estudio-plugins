---
name: agendar-comunicaciones-srt
description: >
  Agendamiento automático diario (lunes a viernes 9am AR) de comunicaciones de
  Mi Ventanilla SRT que tienen plazo procesal. Fase 1 cubre Dictámenes Médicos
  e ITMs: para cada notificación nueva, crea un evento all-day en Google Calendar
  (principal) al día 3 hábil desde la fecha de notificación, con el formato del
  estudio ("NOMBRE-SRT- VENCE IMPUGNAR DICTAMEN MEDICO|ITM", colorId 6 naranja).
  Marca las comunicaciones como procesadas para no re-agendar. Manda reporte
  al grupo WhatsApp "Claude SRT" con lo agendado hoy. Triggers: "agendar
  comunicaciones SRT", "procesar dictámenes", "agendar ITMs", "revisar mi
  ventanilla".
version: 1.0.0
---

# Agendar Comunicaciones SRT

## OBJETIVO

Chequeo diario (L-V 9am AR) de comunicaciones nuevas de Mi Ventanilla con plazo procesal. Crea eventos de vencimiento en Google Calendar y reporta al grupo WhatsApp.

## REGLAS CLAVE

- **Día 1** = día hábil SIGUIENTE a la notificación (`fecha_notificacion`)
- **Feriados AR**: usar tabla `feriados_ar` en Supabase (ver Paso 0)
- **Nunca** re-agendar una comunicación ya procesada (columna `agendado_en_calendar_at IS NOT NULL`)
- **Fase 1 actual**: solo Dictamen Médico + ITM (3 días hábiles)
- **Fase 2 futura**: Citación (leer PDF + aviso WA cliente), Traslado Apelación y Agravios (leer PDF + solo si apeló ART)

## DATOS DE REFERENCIA

- **Supabase project_id**: `wdgdbbcwcrirpnfdmykh`
- **Calendario**: `flirteador84@gmail.com` (principal)
- **WhatsApp grupo**: "Claude SRT" = `120363407310742955@g.us`
- **Edge function**: `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send` (via pg_net trigger, no se llama directo)

## WORKFLOW

### Paso 0 — Bajar feriados AR

```sql
SELECT fecha::text FROM feriados_ar
WHERE fecha BETWEEN (now() - interval '30 days')::date AND (now() + interval '60 days')::date
ORDER BY fecha;
```

Guardar como `/tmp/feriados.json` → `["2026-01-01", ...]`.

### Paso 1 — Comunicaciones nuevas pendientes

```sql
SELECT m.id,
  m.srt_expediente_nro AS srt,
  (m.fecha_notificacion AT TIME ZONE 'America/Argentina/Buenos_Aires')::date::text AS fecha_notif,
  m.tipo_comunicacion,
  c.nombre
FROM comunicaciones_miventanilla m
LEFT JOIN casos_srt c ON c.numero_srt = m.srt_expediente_nro
WHERE m.tipo_comunicacion IN ('Notificación de Dictamen Médico', 'Notificación de ITM')
  AND m.agendado_en_calendar_at IS NULL
  AND m.fecha_notificacion >= (now() - interval '30 days')
ORDER BY m.fecha_notificacion ASC;
```

**Ventana 30 días**: si una comunicación llegó hace más y nunca se procesó, ya pasó el plazo de 3 hábiles (excepto edge cases con muchos feriados). Descartarla como "fuera de ventana" no tiene sentido reagendarla tardío. Si quedan NULL más viejos, el skill los ignora (se agendan manual).

Guardar como `/tmp/comunicaciones.json`.

### Paso 2 — Calcular fecha objetivo para cada una

Con Python usando los feriados de `/tmp/feriados.json`:

```python
import json
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

comunic = json.load(open('/tmp/comunicaciones.json'))
for c in comunic:
    notif = date.fromisoformat(c['fecha_notif'])
    c['fecha_vence'] = sumar_dh(notif, 3).isoformat()

json.dump(comunic, open('/tmp/comunicaciones_con_fecha.json','w'))
```

### Paso 3 — Crear evento en Google Calendar por cada una

Para cada item en `/tmp/comunicaciones_con_fecha.json`:

- **calendarId**: `flirteador84@gmail.com`
- **summary** (formato Mara, SIN prefix `(S)` que agrega Mara post-subida):
  - Dictamen Médico: `{NOMBRE}-{SRT}- VENCE IMPUGNAR DICTAMEN MEDICO`
  - ITM: `{NOMBRE}-{SRT}- VENCE IMPUGNAR ITM`
- **allDay**: true
- **startTime**: `{fecha_vence}T00:00:00`
- **endTime**: `{fecha_vence + 2 días}T00:00:00` (Mara usa 2 días visibles)
- **colorId**: `'6'` (Tangerine naranja)
- **description**: `Fecha de notif: DD/MM/YYYY — auto-agendado por agendar-comunicaciones-srt`
- **timeZone**: `America/Argentina/Buenos_Aires`

**Verificar** el response: si devuelve `status: confirmed` + `id`, el evento se creó. Si falla (401/403/rate limit), agregar a errores.

### Paso 4 — Marcar como agendado en Supabase

Para cada comunicación que se creó OK:

```sql
UPDATE comunicaciones_miventanilla
SET agendado_en_calendar_at = now(),
    agendado_por = 'claude',
    calendar_event_id = $event_id,
    calendar_event_fecha = $fecha_vence
WHERE id = $comunicacion_id;
```

Esto hace el skill **idempotente**: la próxima corrida diaria no vuelve a procesar las mismas.

### Paso 5 — Generar reporte

```python
import json
from datetime import date

agendados = [c for c in json.load(open('/tmp/comunicaciones_con_fecha.json')) if c.get('agendado_ok')]
errores = [c for c in json.load(open('/tmp/comunicaciones_con_fecha.json')) if c.get('error')]
sin_caso = [c for c in agendados if not c.get('nombre')]

hoy = date.today()
L = [f'📋 *AGENDAR COMUNICACIONES SRT* — {hoy.strftime("%d/%m/%Y")}']
L.append(f'Agendadas hoy: {len(agendados)} | Errores: {len(errores)} | Sin caso en app: {len(sin_caso)}')

if agendados:
    L.append('\n✅ *AGENDADAS HOY*')
    for a in agendados:
        tipo_corto = 'DICT MED' if 'Dictamen' in a['tipo_comunicacion'] else 'ITM'
        L.append(f"• {a['nombre'] or '(sin nombre)'} ({a['srt']}) {tipo_corto}: vence {a['fecha_vence']}")

if errores:
    L.append('\n🔴 *ERRORES*')
    for e in errores:
        L.append(f"• {e.get('nombre','?')} ({e['srt']}): {e['error']}")

if sin_caso:
    L.append('\n⚠️ *SIN CASO SRT CARGADO EN APP*')
    for s in sin_caso:
        L.append(f"• SRT {s['srt']} (notif {s['fecha_notif']}) — cargar caso en la app")

if not agendados and not errores and not sin_caso:
    L.append('\n✅ Sin comunicaciones nuevas hoy.')

open('/tmp/reporte.txt','w').write('\n'.join(L))
```

### Paso 6 — INSERT en runs table (dispara WA automáticamente)

```sql
INSERT INTO agendar_comunicaciones_runs (
  total_procesadas, agendados_hoy, errores, sin_caso_srt, reporte_texto
) VALUES (
  $total_procesadas,
  $agendados_jsonb,
  $errores_jsonb,
  $sin_caso_jsonb,
  $reporte_texto
)
RETURNING id, whatsapp_jobid;
```

El trigger `trg_agendar_comunicaciones_wa` dispara `pg_net` → edge function `wa-send` → grupo Claude SRT automáticamente.

### Paso 7 — Confirmar

Reportar resumen:
- Total comunicaciones procesadas
- Eventos creados OK (listado)
- Errores
- Sin caso SRT en app
- ID del run guardado
- Status WhatsApp (pg_net:N o NULL)

## NOTAS

- **Fase 2** (pendiente, requiere leer PDFs adjuntos): Citaciones con fecha de audiencia + aviso WA al cliente firmado como "Dra. Sofi Montes de Oca"; y Traslado Apelación y Agravios (solo si apeló ART).
- **Integración con la app del estudio**: Las columnas `agendado_en_calendar_at` y `agendado_por` permiten a la app mostrar qué fue procesado por Claude vs. pendiente manual. Mara puede filtrar "procesadas por Claude, solo revisar" vs. "pendientes reales".
