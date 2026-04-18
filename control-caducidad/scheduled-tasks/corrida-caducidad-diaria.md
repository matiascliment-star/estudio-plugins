---
name: corrida-caducidad-diaria
description: Corrida diaria de caducidad de instancia (L-V 7am AR). Selecciona top 20 CABA + top 20 Pcia más urgentes, analiza con subagentes, genera borradores DOCX, sube a OneDrive y manda 4 WhatsApp por chica + 1 resumen ejecutivo a Matías.
cron: "0 10 * * 1-5"
---

Leer el archivo `skills/corrida-caducidad-diaria/SKILL.md` (dentro de este repo `estudio-plugins/control-caducidad`) y ejecutar el workflow completo definido ahí.

Al terminar, reportar: total expedientes analizados, CRÍTICOS detectados, borradores generados en OneDrive, WhatsApps enviados, y fallas (si las hubo).
