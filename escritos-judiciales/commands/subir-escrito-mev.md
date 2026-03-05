---
description: Subir escrito como borrador al MEV/SCBA (provincia)
allowed-tools: Read, Write, Bash, Grep, Glob
argument-hint: [numero-causa] [texto o archivo del escrito]
---

Subir un escrito como borrador al sistema de presentaciones electrónicas de la SCBA (notificaciones.scba.gov.ar).

Leer primero el skill en `${CLAUDE_PLUGIN_ROOT}/skills/subir-escrito-mev/SKILL.md` para obtener las instrucciones completas.

Argumentos del usuario: $ARGUMENTS

**IMPORTANTE:** Para escritos SIN adjuntos, usar la tool MCP `scba_guardar_borrador` directamente (el HTML es pequeño). Para escritos CON adjuntos (PDFs), usar el script `${CLAUDE_PLUGIN_ROOT}/scripts/upload_scba_adjuntos.py` que maneja la codificación base64 internamente. NUNCA intentar pasar base64 de PDFs como parámetro de una tool MCP.

Seguir estos pasos:

1. Leer el archivo `.env` de la carpeta del usuario para obtener `MEV_USUARIO` y `MEV_PASSWORD`. Si no existen, pedirlas.
2. Confirmar con el usuario la causa (número o carátula), el tipo de presentación, y el contenido del escrito.
3. Si el usuario pasó un archivo, leerlo. Si pasó texto, usarlo directamente.
4. Obtener `id_org` e `id_causa` de la causa. Si no los tiene, usar la **tool MCP** `mev_listar_causas`.
5. Convertir el escrito a HTML con formato judicial (ver skill para el formato exacto).
6. **Sin adjuntos**: Usar la tool MCP `scba_guardar_borrador` directamente.
7. **Con adjuntos**: Guardar HTML en `/tmp/escrito_scba.html` y ejecutar `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/upload_scba_adjuntos.py --usuario X --password Y --id-org Z --id-causa W --titulo "TITULO" --texto-html-file /tmp/escrito_scba.html --adjuntos /tmp/doc1.pdf`
8. Informar al usuario el resultado y recordarle que debe firmar el borrador desde notificaciones.scba.gov.ar.

Si el script o las tools MCP no están disponibles, informar al usuario que el servidor MCP no está conectado.
