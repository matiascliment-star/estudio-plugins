---
name: eliana-potenciales
description: >
  Skill recurrente (cada 90 min L-V 9-19 AR) que vigila por Eliana 2 cosas:
  (1) los chats individuales que entran a tu WhatsApp `+5491140439075`
  (instance `inst_d9c22079`) — clasifica mensajes recibidos para detectar
  potenciales clientes y alerta a Eliana con resumen; y (2) los Pre-SRT
  con `clasificacion_pre_srt='PENDIENTE_CONTACTO'`: revisa si Eliana ya
  escribió al cliente y si el cliente contestó / mencionó horario para
  llamado. Alerta a Eliana por su WhatsApp privado
  (`5491155681611@s.whatsapp.net`) con el resumen + acción sugerida.
  Idempotente vía `eliana_potenciales_alertas`. Triggers: "eliana revisar
  potenciales", "alertar eliana", "qué tiene eliana pendiente".
version: 1.0.0
---

# Eliana Potenciales

## OBJETIVO

Eliana atiende potenciales y necesita que el sistema le avise: (a) cuando
entran mensajes nuevos a tu WhatsApp privado que podrían ser cliente
potencial; y (b) cuando los Pre-SRT en `PENDIENTE_CONTACTO` tienen
señales para actuar (mencionaron horario, contestaron después de
silencio, etc.).

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **WhatsApp instance del estudio**: `inst_d9c22079` (número `+5491140439075`)
- **WhatsApp privado de Eliana** (destino de alertas):
  chatId `5491155681611@s.whatsapp.net`
- **Edge function WA send**:
  `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`
- **Tabla idempotencia**: `eliana_potenciales_alertas`
- **Staff name de Eliana**: `eliana` (en `wa_messages.staff_name`)

## WORKFLOW

### Paso 1 — Chats individuales nuevos (Parte 1)

Tomar mensajes recibidos en la instancia del estudio, en los últimos
90 min, en chats individuales (no grupos), donde el remitente NO sea
del staff y que NO hayan sido alertados aún:

```sql
SELECT m.id AS msg_id, m.chat_id, m.chat_name, m.sender_name,
       m.content, m.timestamp,
       to_timestamp(m.timestamp) AT TIME ZONE 'America/Argentina/Buenos_Aires' AS fecha_local
FROM wa_messages m
WHERE m.instance_id = 'inst_d9c22079'
  AND m.is_group = false
  AND m.is_from_me = false
  AND m.type = 'text'
  AND m.timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '90 minutes')
  AND NOT EXISTS (
    SELECT 1 FROM eliana_potenciales_alertas a
    WHERE a.tipo = 'individual_nuevo' AND a.message_id = m.id
  )
ORDER BY m.timestamp DESC;
```

Para cada mensaje:

1. **Verificar si ya hay respuesta nuestra después** (`is_from_me=true`
   en el mismo `chat_id` con `timestamp > m.timestamp`). Si ya
   contestamos → no alertar, registrar como `skipped` para no
   reevaluar.
2. **Sin respuesta nuestra** → LLM clasifica el mensaje en una de:
   - 🆕 **potencial_nuevo** — alguien que pregunta por consulta, accidente,
     ART, etc. (no es cliente actual conocido).
   - 🟢 **cliente_existente** — el sender_name o teléfono coincide con
     un caso_srt activo (cliente que ya está atendido).
   - 💬 **no_relevante** — personal, spam, publicidad, conversación
     informal con conocido (Eliana no necesita ver esto).
3. Solo alertar si es **potencial_nuevo**.
4. Armar resumen breve: "<Nombre/Tel>: <primera línea del mensaje, 80
   chars>".

### Paso 2 — Pendientes de contacto (Parte 2)

```sql
SELECT c.id, c.nombre, c.telefono, c.wa_chat_id, c.fecha_alta
FROM casos_srt c
WHERE c.activo = true
  AND c.etapa = 'POR_INICIAR'
  AND c.clasificacion_pre_srt = 'PENDIENTE_CONTACTO'
  AND c.wa_chat_id IS NOT NULL;
```

Por cada caso:

1. Bajar mensajes del chat de los últimos 7 días:

```sql
SELECT id, content, staff_name, is_from_me, timestamp
FROM wa_messages
WHERE chat_id = $1 AND type = 'text'
  AND timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
ORDER BY timestamp ASC;
```

2. LLM evalúa:
   - **Si Eliana NO escribió** (`staff_name='eliana'` ausente) Y el caso lleva
     >2 días con esa clasificación → alerta "PENDIENTE de contactar".
   - **Si Eliana escribió pero cliente NO respondió** desde hace >48h →
     alerta "sin respuesta".
   - **Si cliente contestó y mencionó HORARIO/FECHA disponible** para
     llamar ("podés llamar el martes a las 15", "después de las 18", etc.)
     → alerta "PUEDE SER LLAMADO: <horario detectado>".
   - **Si cliente contestó con algo relevante** (entregó documentos,
     consulta puntual) → alerta "RESPUESTA NUEVA: <resumen>".
   - Si todo OK / sin novedades → nada.

3. Idempotencia: usar `last_msg_id` del chat como `message_id` en
   `eliana_potenciales_alertas` para no repetir.

### Paso 3 — Enviar las alertas a Eliana

Una sola corrida = un solo mensaje agrupado (si hay <=15 items). Si son
más, mandar 2 mensajes (parte 1 y parte 2 por separado).

Formato:

```
🔔 *Eliana — potenciales y pendientes* — DD/MM HH24:MI

🆕 Mensajes nuevos en privado de Matías ({N1}):
• Juan Pérez (+54 9 11 1234-5678) — "Hola, me llamo Juan, tuve un accidente en..."
  → Abrir: https://wa.me/5491112345678
• ...

📞 Pendiente de contacto ({N2}):
• MARTINEZ MARIANO (#1296) — sin contactar hace 4 días → llamar
• PEREZ JUAN (#876) — pidió llamado *martes 15hs* → agendar
• LOPEZ MARÍA (#1023) — no contesta hace 3 días → reintentar
• ...
```

Si hay 0 items en ambas partes → silencio total (no enviar).

Enviar con pg_net:

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object(
    'chatId', '5491155681611@s.whatsapp.net',
    'text', <reporte>
  )
);
```

### Paso 4 — Registrar alertas para idempotencia

Por cada item alertado:

```sql
INSERT INTO eliana_potenciales_alertas (tipo, chat_id, message_id, caso_srt_id, resumen)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (tipo, chat_id, message_id) DO NOTHING;
```

### Paso 5 — Output del agente

≤150 palabras: N alertas parte 1, M parte 2, `request_id` del envío WA.
Si todo fue 0 decir "silencio total, sin alertas hoy" y terminar.

## REGLAS

- **No grupos**: parte 1 procesa solo `is_group = false`.
- **No ignorar contactos**: Matías pidió procesar TODO (sin lista de
  exclusión). El LLM decide qué es relevante.
- **Idempotencia**: cada `message_id` se alerta una sola vez. La tabla
  `eliana_potenciales_alertas` tiene UNIQUE (tipo, chat_id, message_id).
- **Eliana ya respondió**: si entre el mensaje del cliente y AHORA hay
  un `is_from_me=true` en el mismo chat, considerar respondido y NO
  alertar.
- Cliente actual = caso_srt activo con `wa_chat_id` coincidente con
  `m.chat_id`. NO alertar a Eliana en ese caso (Mara/Paula lo atienden).
