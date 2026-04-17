---
name: control-clausuras-srt
description: Control semanal de Disposiciones de Clausura SRT (lunes 10am AR)
cron: "0 13 * * 1"
---

Leer el archivo `skills/control-clausuras-srt/SKILL.md` (dentro de este repo `estudio-plugins/control-clausuras-srt`) y ejecutar el workflow completo definido ahí.

Al terminar, reportar: total clausuras analizadas, eventos agendados hoy, críticos, vencidos sin evento, sin caso SRT, agendados última semana, y status del envío por WhatsApp.
