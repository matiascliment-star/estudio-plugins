---
name: corrida-liquidacion-diaria
description: Corrida diaria de control de ejecución de sentencia (L-V 7:30am AR, después de la corrida de caducidad). Selecciona 3 expedientes más urgentes por sub-estado 70–76 en CABA (= 21) + top de Provincia, analiza con subagentes, genera borradores DOCX, sube a OneDrive/MEV y manda WhatsApp por chica + resumen ejecutivo a Matías.
cron: "30 10 * * 1-5"
---

Leer el archivo `skills/corrida-liquidacion-diaria/SKILL.md` (dentro de este repo `estudio-plugins/control-liquidacion`) y ejecutar el workflow completo definido ahí.

Al terminar, reportar: total expedientes analizados, CRÍTICOS detectados, borradores generados en OneDrive/MEV, WhatsApps enviados, y fallas (si las hubo).
