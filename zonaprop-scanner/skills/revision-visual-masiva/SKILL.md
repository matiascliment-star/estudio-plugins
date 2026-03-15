---
name: revision-visual-masiva
description: >
  Revisión visual masiva de propiedades inmobiliarias desde Supabase. Usa el tool zonaprop_bulk_export
  para obtener TODAS las propiedades, descarga thumbnails, arma grillas de contacto para que Claude
  las recorra visualmente, y luego profundiza en las mejores con fotos en alta resolución.
  Usar siempre que el usuario pida: "revisar propiedades", "ver todas las fotos", "mostrame las propiedades",
  "cuáles son lindas", "buscar propiedades lindas", "analizar visualmente todas", "revisar las que bajé",
  "ver las de hoy", "cuáles me gustan", "filtrar por fotos", "revision masiva", o cualquier pedido de
  ver muchas propiedades a la vez para elegir las mejores visualmente.
---

# Revisión Visual Masiva de Propiedades

## Cuándo usar este skill

Cuando el usuario quiere revisar visualmente TODAS las propiedades de su base de datos (o un subconjunto grande) para encontrar las que se ven bien. No es un filtro por precio o m² — es una revisión visual real donde Claude mira las fotos y elige las lindas.

## Flujo completo

### Paso 1: Obtener datos con zonaprop_bulk_export

Llamar al tool MCP `zonaprop_bulk_export` para obtener TODAS las propiedades. Este tool:
- Pagina automáticamente en Supabase (de a 1000)
- Deduplica por link
- Devuelve JSON con todos los datos: id, link, imagen, imagenes, barrio, direccion, precio, moneda, m2, precio_m2, ambientes, dormitorios, banos, cochera, diff_vs_prom_general
- NO descarga fotos (solo URLs)
- No tiene límite de resultados

Parámetros opcionales de filtro: barrio, precio_min, precio_max, m2_min, m2_max, ambientes, solo_con_imagen.

Guardar el JSON resultado en un archivo temporal (ej: `/tmp/propiedades.json`).

### Paso 2: Descargar thumbnails

Usar el script `scripts/download_thumbs.py` para descargar en paralelo los thumbnails. Ejecutar:
```bash
python3 <skill-path>/scripts/download_thumbs.py <metadata.json> <output-dir>
```

### Paso 3: Armar montajes en grilla

Usar el script `scripts/make_grids.py` para crear imágenes de contacto (50 props por grilla). Ejecutar:
```bash
python3 <skill-path>/scripts/make_grids.py <metadata.json> <thumbs-dir> <output-dir>
```

### Paso 4: Revisión visual de grillas

Recorrer TODAS las grillas con Read. Ver TODAS, no saltear ninguna.

### Paso 5: Profundizar en las candidatas

Descargar fotos en mayor resolución (reemplazar /360x266/ por /730x532/).

### Paso 6: Ranking final

Top 3, Interesantes, Descartadas. Incluir links de ZonaProp.

## Notas importantes

- El tool zonaprop_bulk_export ya deduplica automáticamente.
- Los thumbnails de ~2KB son placeholders rotos, ignorarlos.
- La CDN de ZonaProp es imgar.zonapropcdn.com y no requiere autenticación.

## Dependencias

- Python 3 con Pillow
- Tool MCP zonaprop_bulk_export (del server zonaprop-scanner)
