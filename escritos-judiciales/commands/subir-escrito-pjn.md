---
description: Subir escrito como borrador al PJN (nación)
allowed-tools: Read, Write, Bash, Grep, Glob
argument-hint: [numero-expediente] [texto o archivo del escrito]
---

Subir un escrito como borrador al sistema de presentaciones electrónicas del PJN (escritos.pjn.gov.ar).

Leer primero el skill en `${CLAUDE_PLUGIN_ROOT}/skills/subir-escrito-pjn/SKILL.md` para obtener las instrucciones completas.

Argumentos del usuario: $ARGUMENTS

**IMPORTANTE:** Para subir el borrador, generar el PDF con reportlab, guardarlo en `/tmp/escrito_pjn.pdf`, y luego ejecutar el script `${CLAUDE_PLUGIN_ROOT}/scripts/upload_pjn_borrador.py` que se encarga de codificar el PDF en base64 y llamar al MCP server internamente. NUNCA intentar pasar el base64 del PDF como parámetro de una tool MCP (es demasiado grande para el contexto del agente).

Seguir estos pasos:

1. Leer el archivo `.env` de la carpeta del usuario para obtener `PJN_USUARIO` y `PJN_PASSWORD`. Si no existen, pedirlas.
2. Confirmar con el usuario el número de expediente (formato: "CNT 6379/2024"), el tipo de escrito, y el contenido.
3. Obtener el ID interno del expediente usando la tool MCP `pjn_buscar_expediente`.
4. Si el usuario pasó un archivo PDF, usarlo directamente. Si pasó texto, convertir a PDF con Python + reportlab (instalar con `pip install reportlab --break-system-packages` si hace falta).
5. Guardar el PDF en `/tmp/escrito_pjn.pdf`.
6. Ejecutar: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/upload_pjn_borrador.py --usuario X --password Y --id-expediente Z --tipo E --pdf-path /tmp/escrito_pjn.pdf --pdf-nombre escrito.pdf --descripcion "DESCRIPCION"`
7. Informar al usuario el resultado y recordarle que debe firmar el borrador desde escritos.pjn.gov.ar.

Si el script falla con error de conexión, informar al usuario que el servidor MCP no está conectado.
