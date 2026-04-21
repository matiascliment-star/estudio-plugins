---
name: corrida-liquidacion-monto
description: Corrida diaria de control de ejecución por MONTO (L-V 18:30 AR, 30 min después de la de urgencia). Selecciona top 15-20 expedientes 7X ordenados por monto_pendiente_actor + monto_pendiente_honorarios DESC. Analiza con subagentes, genera borradores, sube a OneDrive/MEV y manda WhatsApp. Inserta en liquidacion_corridas con tipo_corrida='monto'. Complementa la corrida por urgencia: captura casos con plata grande aunque tengan movimiento reciente.
cron: "30 21 * * 1-5"
---

Leer el archivo `skills/corrida-liquidacion-diaria/SKILL.md` (dentro de este repo `estudio-plugins/control-liquidacion`) y ejecutar el workflow **variante MONTO** definido ahí.

**IMPORTANTE**: al insertar en `liquidacion_corridas`, setear `tipo_corrida='monto'`.

Al terminar, reportar: total expedientes analizados, CRÍTICOS detectados, monto total pendiente identificado, borradores generados en OneDrive/MEV, WhatsApps enviados, y fallas (si las hubo).
