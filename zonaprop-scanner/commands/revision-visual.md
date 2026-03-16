# /zonaprop:revision-visual

Revisión visual masiva de propiedades inmobiliarias.

## Instrucciones

1. Llamar a zonaprop_bulk_export para obtener TODAS las propiedades (sin límite, pagina automáticamente).
2. Guardar el JSON en /tmp/propiedades.json.
3. Descargar TODAS las fotos con `scripts/download_thumbs.py --all` (hasta 8 por propiedad).
4. Armar grillas multi-foto (20 props por grilla, mosaico 4x2 por celda) con `scripts/make_grids.py --multi`.
5. Recorrer TODAS las grillas visualmente (cada celda muestra todas las fotos de la propiedad).
6. Profundizar en las candidatas con fotos en mayor resolución (730x532).
7. Armar ranking final: Top 3, Interesantes, Descartadas. Incluir links de ZonaProp.
8. Generar HTML interactivo con fotos embebidas usando `scripts/make_html_report.py`. El HTML se guarda en `outputs/`.
