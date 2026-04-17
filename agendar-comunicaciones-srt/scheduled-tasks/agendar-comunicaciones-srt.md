---
name: agendar-comunicaciones-srt
description: Agendamiento diario de comunicaciones de Mi Ventanilla SRT (L-V 9am AR)
cron: "0 12 * * 1-5"
---

Leer el archivo `skills/agendar-comunicaciones-srt/SKILL.md` (dentro de este repo `estudio-plugins/agendar-comunicaciones-srt`) y ejecutar el workflow completo definido ahí.

Al terminar, reportar resumen ejecutivo: total procesadas, agendadas hoy con listado, errores, sin caso SRT en app, ID del run guardado en `agendar_comunicaciones_runs`, y status del envío de WhatsApp (pg_net jobid o NULL).
