---
description: Subir escrito como borrador al MEV/SCBA (provincia)
allowed-tools: Read, Write, Bash, Grep, Glob
argument-hint: [numero-causa] [texto o archivo del escrito]
---

Subir un escrito como borrador al sistema de presentaciones electrónicas de la SCBA (notificaciones.scba.gov.ar).

Leer primero el skill en `${CLAUDE_PLUGIN_ROOT}/skills/subir-escrito-mev/SKILL.md` para obtener las instrucciones completas.

Argumentos del usuario: $ARGUMENTS

**IMPORTANTE:** Para interactuar con la SCBA/MEV, usar SIEMPRE las tools MCP (`mev_listar_causas`, `scba_guardar_borrador`, `scba_guardar_borrador_adjuntos`). NUNCA intentar llamar a la API via Node.js, curl, fetch, ni ningún otro método HTTP directo. Las tools MCP ya están disponibles como herramientas invocables directamente.

Seguir estos pasos:

1. Leer el archivo `.env` de la carpeta del usuario para obtener `MEV_USUARIO` y `MEV_PASSWORD`. Si no existen, pedirlas.
2. Confirmar con el usuario la causa (número o carátula), el tipo de presentación, y el contenido del escrito.
3. Si el usuario pasó un archivo, leerlo. Si pasó texto, usarlo directamente.
4. Obtener `id_org` e `id_causa` de la causa. Si no los tiene, usar la **tool MCP** `mev_listar_causas` para buscar la causa correcta.
5. Convertir el escrito a HTML con formato judicial (ver skill para el formato exacto).
6. Si hay archivos PDF adjuntos (documental), codificarlos en base64 y usar la **tool MCP** `scba_guardar_borrador_adjuntos`. Si es solo texto, usar la **tool MCP** `scba_guardar_borrador`.
7. Informar al usuario el resultado y recordarle que debe firmar el borrador desde notificaciones.scba.gov.ar.

Si las tools MCP no están disponibles, informar al usuario que el servidor MCP del scraper no está conectado. No intentar alternativas.
