---
name: agendar-comunicaciones-srt
description: Agendamiento de comunicaciones de Mi Ventanilla SRT (L-D 9am y 9pm AR)
cron: "0 0,12 * * *"
---

Corre todos los días (L-D) a las 9:00 AR (12:00 UTC) y a las 21:00 AR (00:00 UTC).
La de 9am agarra todo lo que el scraper SRT (que corre 1x/día) ingestó durante la
noche. La de 21:00 es backup: si la matutina falló o salteó items, la nocturna los
recupera (idempotente por `agendado_en_calendar_at IS NULL`). Sábado y domingo
también — a veces llegan notificaciones en fin de semana.

Leer el archivo `skills/agendar-comunicaciones-srt/SKILL.md` (dentro de este repo `estudio-plugins/agendar-comunicaciones-srt`) y ejecutar el workflow completo definido ahí.

Al terminar, reportar resumen ejecutivo: total procesadas, agendadas hoy con listado, errores, sin caso SRT en app, ID del run guardado en `agendar_comunicaciones_runs`, y status del envío de WhatsApp (pg_net jobid o NULL).
