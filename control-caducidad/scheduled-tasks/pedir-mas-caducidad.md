---
name: pedir-mas-caducidad
description: Procesa cola de pedidos on-demand de caducidad. Cron horario L-V 8-20hs AR (= 11-23 UTC) chequea `pedidos_caducidad_pendientes` en Supabase y si hay algo pendiente, lanza los subagentes para analizar los N expedientes ya pre-seleccionados por la edge function. Manda WhatsApp a la abogada destinataria + resumen ejecutivo a Matías.
cron: "7 11-23 * * 1-5"
---

Leer el archivo `skills/pedir-mas-caducidad/SKILL.md` (dentro del repo `estudio-plugins/control-caducidad`) y ejecutar el workflow.

Consumir el pedido más viejo de la cola `pedidos_caducidad_pendientes` (estado=`pendiente`). Si no hay ninguno, terminar en 2 seg reportando "sin pedidos pendientes" (comportamiento esperado el 90% de los runs).

Al terminar, reportar:
- `pedido_id` procesado (o "ninguno")
- cantidad de expedientes analizados OK
- cantidad de expedientes fallidos
- `numero_corrida` asignado
- abogada destinataria
- WhatsApp enviados (a quién y cuántos)
