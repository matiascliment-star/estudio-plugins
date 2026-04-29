# control-whatsapp

Automatización de la atención al cliente vía WhatsApp del estudio García Climent.

## Skills

### `revisar-whatsapp-diario`
Corrida diaria 8:00 AR (lun-vie). Detecta grupos de cliente con mensajes sin contestar, los clasifica con LLM (urgente / novedades / acción concreta / baja / cerrada), manda combo Sofía (audio + texto con datos del portal) a los que pidan novedades genéricas y aún no lo recibieron, y reporta al grupo TRABAJO con sub-reportes por chica.

Trigger Anthropic Cloud: `trig_014d19paikE3KzRpCkQYPsMd`.

### `recordatorio-turnos-diario`
Corrida diaria 7:00 AR (todos los días). Extrae turnos médicos / pericias de los mensajes del staff de los últimos 3 días con LLM (regex permisiva que solo requiere fecha+hora) e inserta en `wa_turnos`. Después manda recordatorios al cliente para los turnos de HOY y de MAÑANA que aún no fueron avisados.

Trigger Anthropic Cloud: `trig_01McoYgmtsE8MedSoDMWKmYm`.

## Tablas Supabase (proyecto `wdgdbbcwcrirpnfdmykh`)

- `wa_messages` — mensajes WhatsApp (alimentado por sincronizador externo)
- `wa_audio_enviado` — UNIQUE (chat_id, audio_tipo). Tracking del combo Sofía pregrabado.
- `wa_media_procesado` — transcripciones Whisper / OCR Claude vision (alimentada por Edge Function `process-wa-media`)
- `wa_turnos` — UNIQUE (chat_id, fecha_turno, hora_turno). Con flags `recordatorio_enviado` (día anterior) y `recordatorio_dia_enviado` (mismo día).

## Edge Function

`process-wa-media` — disparada por Postgres trigger en INSERT a `wa_messages` con `type IN ('audio','ptt','image')`. Transcribe audios (Whisper) o describe imágenes (Claude Sonnet 4.6) e inserta en `wa_media_procesado`.

## MCP requeridos

- Supabase (`c7abd1f3-f6e0-436f-a6b0-19698822a66b`)
- WhatsApp (`32eb8054-805a-478c-8692-ec5db255de92`) — `instanceId=inst_d9c22079`

## Reglas operativas

- **Pull, no push**: NUNCA mandar avisos proactivos sobre movimientos de expediente. El cliente entra al portal o pregunta cuando quiere.
- **No real-time clientes**: para clasificación / urgencias, alcanza el control diario.
- **Combo Sofía solo a "novedades genéricas"**: si pide algo concreto (turno, monto, doc) → respuesta humana, no audio.
