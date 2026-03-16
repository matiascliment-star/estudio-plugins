# /zonaprop:revision-visual

Revisión visual masiva de propiedades inmobiliarias.

## Instrucciones

1. Llamar a zonaprop_bulk_export para obtener TODAS las propiedades (sin límite, pagina automáticamente).
2. Guardar el JSON en /tmp/propiedades.json.
3. Descargar todos los thumbnails con scripts/download_thumbs.py.
4. Armar grillas de contacto (50 props por grilla) con scripts/make_grids.py.
5. Recorrer TODAS las grillas visualmente e identificar las propiedades más atractivas.
6. Profundizar en las candidatas con fotos en mayor resolución (730x532).
7. Armar ranking final: Top 3, Interesantes, Descartadas. Incluir links de ZonaProp.
8. Generar HTML interactivo con fotos embebidas usando `scripts/make_html_report.py`. El HTML se guarda en `outputs/`.
