---
name: seguimiento-tratamiento-llm
description: >
  Corrida diaria (9:11 AR) que sigue a los clientes en etapa TRATAMIENTO.
  Para cada caso con `wa_chat_id` matcheado: lee los últimos 30 días del grupo
  de WhatsApp y, vía LLM, decide si el cliente ya tiene alta médica. Si la
  detecta con confianza, promueve automáticamente el caso a POR_INICIAR
  (etapa=POR_INICIAR, clasificacion_pre_srt='PENDIENTE_CONTACTO', fecha_alta
  si la extrajo). Si hace ≥7 días que el cliente no escribe, envía un ping
  proactivo preguntando cómo va el tratamiento (idempotente: no más de 1 ping
  por día por caso). Reporta al grupo "WA Claude SRT". Triggers:
  "seguimiento tratamiento", "detectar altas", "ping tratamiento".
version: 1.0.0
---

# Seguimiento de Tratamiento (LLM)

## OBJETIVO

Cerrar el loop del flujo Pre-SRT: cuando el cliente firma sin alta médica
queda en TRATAMIENTO. Nadie actualiza eso a mano cuando le dan el alta. Este
skill detecta automáticamente la transición leyendo el WhatsApp del cliente,
y mantiene contacto vivo con pings proactivos cuando hay silencio.

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **Tabla `casos_srt`** (campos usados): `id`, `nombre`, `etapa`, `wa_chat_id`,
  `fecha_alta`, `clasificacion_pre_srt`, `activo`.
- **Tabla `wa_messages`**: mensajes de WhatsApp (`chat_id`, `content`,
  `sender_name`, `is_from_me`, `timestamp`, `type`).
- **Tabla `seguimiento_pings`** (idempotencia):
  `caso_srt_id`, `enviado_at`, `mensaje`, `respondido_at`.
- **Edge function WhatsApp**:
  `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`.
- **Grupo destino del reporte** "WA Claude SRT":
  chatId `120363407310742955@g.us`.

## WORKFLOW

### Paso 1 — Levantar los casos elegibles

```sql
SELECT id, nombre, wa_chat_id
FROM casos_srt
WHERE activo = true
  AND etapa = 'TRATAMIENTO'
  AND wa_chat_id IS NOT NULL;
```

Si la query devuelve 0 → terminar (silencio).

### Paso 2 — Por cada caso, leer los últimos 30 días del chat

```sql
SELECT id, content, sender_name, is_from_me, timestamp,
       to_timestamp(timestamp) AT TIME ZONE 'America/Argentina/Buenos_Aires' AS fecha_local
FROM wa_messages
WHERE chat_id = $1
  AND type = 'text'
  AND timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days')
ORDER BY timestamp ASC;
```

### Paso 3 — Detectar último mensaje DEL CLIENTE

"Mensaje del cliente" = `is_from_me = false`. Tomá su `timestamp` más reciente
(= `ultimo_msg_cliente_ts`). Si no hay ninguno en los últimos 30 días, considerá
que el último mensaje del cliente es desconocido → pasa al ping (bloque B).

### Paso 4 — Bloque A · Detección de alta médica

Si hay al menos un mensaje del cliente en los últimos 30 días, leelos con tu
propio razonamiento (sos el LLM). Buscás:

**Alta clara** (confianza alta, AUTO-APLICAR):
- "ya me dieron el alta" / "me dieron el alta" / "alta médica" con o sin fecha
- "el alta médica fue el DD/MM" / "tengo el alta desde DD/MM"
- Forward de PDF / imagen de alta médica
- Cliente confirma fecha específica de alta

**Alta dudosa o futura** (NO aplicar, registrar en notas):
- "creo que el lunes me dan el alta"
- "le pedí al doctor el alta"
- "el doctor dice que falta poco"
- "esperando el alta"

**Sin señal** → no hacer nada en este bloque, pasar a Bloque B.

### Paso 5 — Aplicar la promoción (si alta clara)

```sql
UPDATE casos_srt
SET etapa = 'POR_INICIAR',
    clasificacion_pre_srt = 'PENDIENTE_CONTACTO',  -- siempre PENDIENTE_CONTACTO: hay que llamar al cliente para el relato antes de iniciar
    fecha_alta = COALESCE(fecha_alta, <fecha_extraida_o_NULL>),
    notas = COALESCE(notas, '') || E'\n\n--- ' || to_char(NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires', 'DD/MM/YYYY') || ' Promoción automática TRATAMIENTO→POR_INICIAR ---\n' ||
            'Evidencia WhatsApp: "<frase clave del mensaje del cliente>" (' || <fecha_msg> || ')',
    updated_at = NOW()
WHERE id = <caso_id>;
```

### Paso 6 — Bloque B · Ping proactivo si hay silencio

Para los casos donde el cliente NO mostró alta médica (o no escribió en
30 días), evaluá si corresponde mandar ping:

**Condiciones para enviar ping**:
1. `ultimo_msg_cliente_ts` fue hace ≥ 7 días (o no existe).
2. NO se envió ya un ping a este `caso_srt_id` en el día calendario AR de hoy:

```sql
SELECT 1 FROM seguimiento_pings
WHERE caso_srt_id = <caso_id>
  AND (enviado_at AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
      = (NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
LIMIT 1;
```

Si NO existe esa fila → enviar ping. Si existe → skip.

**Texto del ping** (reemplazar `{primer_nombre}` con el primer nombre del
cliente; si no se puede extraer, usar "Hola"):

```
Hola {primer_nombre}, ¿cómo estás? Te escribimos del estudio García Climent para saber cómo venís con el tratamiento médico. ¿Ya te dieron el alta?
```

Donde `{primer_nombre}` se extrae con: tomar `casos_srt.nombre`, partirlo
por espacios, tomar el primer token que NO sea apellido. Como aproximación
simple: si el nombre tiene formato "APELLIDO NOMBRE NOMBRE2", tomar el
segundo token (índice 1). Capitalizar.

**Envío del ping**:

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object(
    'chatId', '<wa_chat_id_del_caso>',
    'text', '<texto_del_ping>'
  )
);
```

**Registrar el envío**:

```sql
INSERT INTO seguimiento_pings (caso_srt_id, enviado_at, mensaje)
VALUES (<caso_id>, NOW(), '<texto_del_ping>');
```

### Paso 7 — Marcar pings respondidos (housekeeping)

Para cada ping previo sin `respondido_at`, si llegó un mensaje del cliente
en ese chat **después** del `enviado_at`, marcarlo como respondido:

```sql
UPDATE seguimiento_pings p
SET respondido_at = w.fecha_local
FROM casos_srt c,
     LATERAL (
       SELECT MIN(to_timestamp(timestamp) AT TIME ZONE 'America/Argentina/Buenos_Aires') AS fecha_local
       FROM wa_messages
       WHERE chat_id = c.wa_chat_id
         AND is_from_me = false
         AND timestamp >= EXTRACT(EPOCH FROM p.enviado_at)
     ) w
WHERE p.respondido_at IS NULL
  AND p.caso_srt_id = c.id
  AND w.fecha_local IS NOT NULL;
```

### Paso 8 — Reporte por WhatsApp al grupo "WA Claude SRT"

Sólo enviar si `promociones + pings_enviados + respondidos_hoy > 0`.

Formato:

```
🩺 *SEGUIMIENTO TRATAMIENTO* — DD/MM/YYYY HH24:MI
✅ Promociones a POR_INICIAR: X
📨 Pings enviados hoy: Y
↩️ Respondieron al ping anterior: Z

✅ Promovidos:
• NOMBRE (alta detectada en WA — DD/MM)
...

📨 Pings enviados:
• NOMBRE (último msg cliente: hace N días)
...
```

Enviar con `pg_net`:

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object(
    'chatId', '120363407310742955@g.us',
    'text', <reporte>
  )
);
```

### Paso 9 — Output del agente

Reporte breve (≤200 palabras): cantidad promovidas, pings, respondidos,
`request_id` del envío al grupo. Si todo 0, decirlo y terminar.

## REGLAS DURAS

- **AUTO en promociones**: si el LLM detecta alta médica con frase clara
  (no ambigua), promover sin pedir confirmación. Si las chicas se equivocan,
  lo arreglan a mano.
- **Idempotencia ping**: máximo 1 ping por caso por día calendario AR.
  Si el cliente nunca responde, se le sigue mandando 1 ping diario indefinidamente
  (es lo que pidió Matías).
- **No re-promover lo ya promovido**: el SQL del Paso 1 filtra por
  `etapa = 'TRATAMIENTO'`, así que casos ya en POR_INICIAR/ACTIVO no se vuelven
  a evaluar.
- **Casos sin `wa_chat_id`**: no se procesan (no hay forma de leer ni mandar
  ping). Quedan invisibles para el skill — el trigger 4am AR los va matcheando
  cuando aparecen.
- **No tocar `fecha_alta` si ya estaba poblada**: usar COALESCE.
- **Evidencia en notas**: cada promoción agrega una línea con la frase clave
  del mensaje, para auditoría futura.

## LIMITACIONES CONOCIDAS

- El skill no distingue grupos con MUCHO ruido (familia que escribe del
  cliente, varios participantes). El LLM tiene que filtrar mentalmente: el
  alta es del titular, no de un familiar.
- Si el cliente menciona alta de OTRO familiar/conocido en el chat, el LLM
  podría promover erróneamente. Bajo el principio "todo auto, las chicas
  arreglan" del usuario, este riesgo está aceptado.
