---
name: recordatorio-turnos-diario
description: >
  Corrida diaria automatizada de recordatorios de turnos médicos / pericias /
  citaciones médicas. Lee la tabla `wa_turnos` en Supabase, detecta los turnos
  cuya fecha es MAÑANA y todavía no tienen `recordatorio_enviado=true`, y
  manda al cliente vía WhatsApp un mensaje formateado con día, hora, dirección
  y procedimiento. Marca cada turno como recordado para no duplicar. También
  reporta al grupo TRABAJO el resumen de qué cliente fue avisado y cuáles
  quedaron pendientes (turnos sin hora o sin lugar). Triggers: "recordatorio
  turnos", "recordar turnos", "turnos de mañana", "avisar turnos", "control
  turnos diario". Programado para correr todos los días hábiles a las 9:00 AR.
version: 0.1.0
---

# Skill: Recordatorio de turnos diario

Manda recordatorio automático al cliente 24hs antes de su turno (pericia, RMN, ecografía, junta médica, etc.) para reducir inasistencias. Cada inasistencia a pericia se considera desistimiento de la prueba y puede tirar el caso.

## Tabla `wa_turnos` (Supabase)

Esta skill consume datos producidos por `extract_turnos.py` (en el skill `revisar-whatsapp-diario`), que parsea los mensajes del staff y extrae turnos estructurados.

Schema:
```sql
wa_turnos (
  id, chat_id, chat_name,
  fecha_turno DATE, hora_turno TIME,
  lugar TEXT, procedimiento TEXT,
  mensaje_origen_id TEXT,
  recordatorio_enviado BOOLEAN DEFAULT false,
  recordatorio_msg_id TEXT,
  recordatorio_fecha TIMESTAMPTZ,
  asistio BOOLEAN, notas TEXT
)
```

**UNIQUE (chat_id, fecha_turno, hora_turno)** evita duplicados.

## Workflow

### Paso 1 — Asegurar datos actualizados

Antes de mandar recordatorios, refrescar la tabla. Correr:
```bash
python3 ~/.claude/skills/revisar-whatsapp-diario/extract_turnos.py --since $(date -v-3d +%Y-%m-%d)
```
Esto extrae turnos de mensajes del staff de los últimos 3 días que pueden haber agregado turnos para mañana.

### Paso 2 — Query de turnos de mañana sin recordatorio

```sql
SELECT id, chat_id, chat_name, fecha_turno, hora_turno, lugar, procedimiento
FROM wa_turnos
WHERE fecha_turno = (CURRENT_DATE + INTERVAL '1 day')::date
  AND recordatorio_enviado = false
  AND hora_turno IS NOT NULL
  AND lugar IS NOT NULL
ORDER BY hora_turno;
```

### Paso 3 — Enviar recordatorio por cliente

Para cada turno:

```
🩺 Hola! Te recordamos tu turno de mañana:

📅 [Día de la semana] [DD/MM/YY] a las [HH:MM]
📍 [Lugar]
🔬 Para: [Procedimiento]

Llevá DNI y avisanos por acá cuando llegues 🙏

⚠️ La inasistencia se considera desistimiento de la prueba.
```

Llamar `wa_send_text` con `instanceId=inst_d9c22079`, `to=chat_id`. Guardar el `messageId` retornado.

### Paso 4 — Marcar como enviado

```sql
UPDATE wa_turnos
SET recordatorio_enviado = true,
    recordatorio_msg_id = $1,
    recordatorio_fecha = NOW()
WHERE id = $2;
```

### Paso 5 — Reporte al grupo TRABAJO

JID `5491167156098-1395248421@g.us`. Formato:

```
🩺 RECORDATORIOS DE TURNOS — [fecha de mañana]

✅ Avisados ([N]):
- [Cliente] — [HH:MM] [procedimiento corto] @ [lugar corto]
- ...

⚠️ Sin avisar (faltan datos) ([N]):
- [Cliente] — [fecha mañana] — falta hora/lugar
- ...
```

## Edge cases

- **Turnos sin hora o sin lugar**: NO mandar recordatorio, listar en el bloque "sin avisar" para revisión manual.
- **Turnos en grupos internos** (no de cliente): el `extract_turnos.py` ya excluye grupos internos, pero verificar en la query.
- **Cliente que se fue del estudio**: si el grupo está marcado en `wa_audio_enviado` con audio_tipo `baja_cliente` (futuro) → no mandar recordatorio.
- **Mismo cliente con 2 turnos en el mismo día**: mandar 2 recordatorios separados (uno por turno) o uno consolidado. Por ahora hacer 1 mensaje por turno (más claro).
- **Si la instancia WA está caída**: avisar al grupo TRABAJO y abortar.
- **Turno en sábado/domingo/feriado**: igual mandar recordatorio el día previo (incluso si es feriado el recordatorio).

## Triggers manuales

- "recordatorio turnos"
- "recordar turnos"
- "turnos de mañana"
- "avisar turnos"
- "control turnos diario"

## Scheduled trigger

Configurar via `schedule` skill para correr **todos los días a las 9:00 AR**.

## Métricas a reportar

- Total turnos detectados para mañana
- Cuántos efectivamente avisados
- Cuántos quedaron sin avisar (incompletos)
- (Futuro) Tasa de asistencia: cuántos del recordatorio terminan asistiendo (campo `asistio` en wa_turnos)
