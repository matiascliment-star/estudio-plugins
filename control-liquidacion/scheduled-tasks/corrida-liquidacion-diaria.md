---
name: corrida-liquidacion-diaria
description: Corrida diaria de control de ejecución de sentencia por URGENCIA (L-V 18:00 AR). Selecciona 3 expedientes más urgentes por sub-estado 70–76 en CABA (= 21) + top de Provincia ordenados por días sin empuje DESC, analiza con subagentes, genera borradores DOCX, sube a OneDrive/MEV y manda WhatsApp por responsable + resumen ejecutivo a Matías. Inserta en liquidacion_corridas con tipo_corrida='urgencia'.
cron: "0 21 * * 1-5"
---

Leer el archivo `skills/corrida-liquidacion-diaria/SKILL.md` (dentro de este repo `estudio-plugins/control-liquidacion`) y ejecutar el workflow **variante URGENCIA** definido ahí.

**IMPORTANTE**: al insertar en `liquidacion_corridas`, setear `tipo_corrida='urgencia'`.

Al terminar, reportar: total expedientes analizados, CRÍTICOS detectados, borradores generados en OneDrive/MEV, WhatsApps enviados, y fallas (si las hubo).
