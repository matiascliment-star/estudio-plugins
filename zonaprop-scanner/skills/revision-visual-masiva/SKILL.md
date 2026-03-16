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

Para las propiedades que pasaron el filtro visual (típicamente 20-30):
1. Obtener sus datos completos del JSON de metadata, incluyendo el campo `imagenes` (array de URLs de todas las fotos)
2. Para cada candidata, armar las URLs en alta resolución de TODAS sus fotos (hasta 8): reemplazar `/360x266/` por `/730x532/` en cada URL del array `imagenes`
3. Ver 2-3 fotos con Read para evaluar (estado, terminaciones, luminosidad, red flags)
4. **Guardar TODAS las URLs hires** (no solo las que se vieron) — se usan en el Paso 7 para el HTML report

### Paso 6: Ranking final

Top 3, Interesantes, Descartadas. Incluir links de ZonaProp.

### Paso 7: Generar HTML report

Después del ranking, generar un HTML interactivo con fotos embebidas usando `scripts/make_html_report.py`.

1. Armar un JSON con la estructura que espera el script:
   ```json
   {
     "stats": {
       "total_escaneadas": <total de propiedades revisadas>,
       "seleccionadas": <cantidad en el ranking>,
       "top_picks": <cantidad en top3>,
       "rango_precios": "USD XXk-XXXk"
     },
     "propiedades": [
       {
         "tier": "top3" | "top10" | "interesting",
         "rank": 1,
         "score": "9.5/10",
         "barrio": "...",
         "direccion": "...",
         "precio": 164000,
         "m2": 67,
         "ambientes": 2,
         "precio_m2": 2448,
         "diff_vs_prom": -31,
         "comentario": "Descripción de Claude...",
         "link": "https://www.zonaprop.com.ar/...",
         "fotos": ["https://imgar.zonapropcdn.com/avisos/1/00/58/53/68/28/730x532/foto1.jpg", "https://...foto2.jpg", "...hasta 8 fotos"]
       }
     ]
   }
   ```
2. Las fotos pueden ser URLs del CDN de ZonaProp (el script las descarga en paralelo) o paths locales. Incluir TODAS las fotos de cada propiedad (hasta 8), no solo las que Claude revisó visualmente. El script las embebe como base64 en el HTML.
3. Guardar el JSON como `report_input.json` y ejecutar:
   ```bash
   python3 <skill-path>/scripts/make_html_report.py report_input.json outputs/top_propiedades.html
   ```
4. Informar al usuario la ruta del HTML generado para que lo abra en el browser.

## Notas importantes

- El tool zonaprop_bulk_export ya deduplica automáticamente.
- Los thumbnails de ~2KB son placeholders rotos, ignorarlos.
- La CDN de ZonaProp es imgar.zonapropcdn.com y no requiere autenticación.

## Dependencias

- Python 3 con Pillow
- Tool MCP zonaprop_bulk_export (del server zonaprop-scanner)
