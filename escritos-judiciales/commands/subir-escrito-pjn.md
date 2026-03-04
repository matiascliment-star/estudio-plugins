---
description: Subir escrito como borrador al PJN (nación)
allowed-tools: Read, Write, Bash, Grep, Glob
argument-hint: [numero-expediente] [texto o archivo del escrito]
---

Subir un escrito como borrador al sistema de presentaciones electrónicas del PJN (escritos.pjn.gov.ar).

Leer primero el skill en `${CLAUDE_PLUGIN_ROOT}/skills/subir-escrito-pjn/SKILL.md` para obtener las instrucciones completas.

Argumentos del usuario: $ARGUMENTS

**IMPORTANTE:** Para subir el borrador, usar SIEMPRE la tool MCP `pjn_guardar_borrador`. NUNCA intentar llamar a la API via Node.js, curl, fetch, ni ningún otro método HTTP directo. Las tools MCP ya están disponibles como herramientas invocables directamente.

Seguir estos pasos:

1. Leer el archivo `.env` de la carpeta del usuario para obtener `PJN_USUARIO` y `PJN_PASSWORD`. Si no existen, pedirlas.
2. Confirmar con el usuario el número de expediente (formato: "CNT 6379/2024"), el tipo de escrito, y el contenido.
3. Si el usuario pasó un archivo, leerlo. Si pasó texto, usarlo directamente.
4. Convertir el escrito a PDF usando Python + reportlab (instalar con `pip install reportlab --break-system-packages` si hace falta).
5. Codificar el PDF en base64.
6. Llamar a la **tool MCP** `pjn_guardar_borrador` con los parámetros correspondientes (NO usar Node.js, curl ni ningún otro workaround).
7. Informar al usuario el resultado y recordarle que debe firmar el borrador desde escritos.pjn.gov.ar.

Si la tool MCP no está disponible, informar al usuario que el servidor MCP del scraper no está conectado. No intentar alternativas.
