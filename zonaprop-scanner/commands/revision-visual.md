# /zonaprop:revision-visual

Revisión visual masiva de propiedades inmobiliarias.

## Instrucciones

1. Obtener todas las propiedades activas de Supabase (paginar de a 1000, deduplicar por URL).
2. Descargar todos los thumbnails con `scripts/download_thumbs.py`.
3. Armar grillas de contacto (50 props por grilla) con `scripts/make_grids.py`.
4. Recorrer TODAS las grillas visualmente e identificar las propiedades más atractivas.
5. Profundizar en las candidatas con fotos en mayor resolución (730x532).
6. Armar ranking final: Top 3, Interesantes, Descartadas. Incluir links de ZonaProp.
