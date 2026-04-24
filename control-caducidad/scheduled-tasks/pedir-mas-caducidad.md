---
name: pedir-mas-caducidad
description: Procesa cola de pedidos on-demand de caducidad. Cada 2 min L-V 8-20hs AR chequea `pedidos_caducidad_pendientes` en Supabase y si hay algo pendiente, lanza los subagentes para analizar los N expedientes ya pre-seleccionados por la edge function.
cron: "*/2 11-23 * * 1-5"
---

Leer el archivo `skills/pedir-mas-caducidad/SKILL.md` (dentro del repo `estudio-plugins/control-caducidad`) y ejecutar el workflow.

Consumir el pedido más viejo de la cola `pedidos_caducidad_pendientes` (estado=`pendiente`). Si no hay ninguno, terminar en 2 seg reportando "sin pedidos pendientes" (comportamiento esperado el 90% de los runs).

Al terminar, reportar:
- `pedido_id` procesado (o "ninguno")
- cantidad de expedientes analizados OK
- cantidad de expedientes fallidos
- `numero_corrida` asignado
- abogada destinataria
