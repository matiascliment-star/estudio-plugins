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

### Paso 2: Descargar TODAS las fotos

Usar el script `scripts/download_thumbs.py` con `--all` para descargar TODAS las fotos de cada propiedad (hasta 8 por aviso). Ejecutar:
```bash
python3 <skill-path>/scripts/download_thumbs.py <metadata.json> <output-dir> --all
```

Esto genera archivos como `0000_00.jpg`, `0000_01.jpg`, ..., `0000_07.jpg` para la propiedad 0, etc.
Con 25 workers en paralelo, ~5000 fotos se descargan en 1-2 minutos.

### Paso 3-4: Revisión visual por batches

**IMPORTANTE: Límite de 250 propiedades por batch.** Si hay más de 250 propiedades, dividir en batches y procesar cada uno por separado, seleccionando las mejores de cada batch. Al final, hacer una ronda final con todas las seleccionadas.

**Para cada batch:**

1. Armar un JSON parcial con las propiedades del batch (ej: propiedades 0-249, luego 250-499, etc.)
2. Armar grillas multi-foto del batch:
   ```bash
   python3 <skill-path>/scripts/make_grids.py <batch.json> <thumbs-dir> <output-dir> --multi
   ```
   Cada grilla tiene 20 propiedades (5 cols × 4 filas), cada celda con mosaico 4×2 de fotos. Un batch de 250 = ~13 grillas.
3. Recorrer TODAS las grillas del batch con Read. Seleccionar las ~30 mejores del batch.

**Ejemplo con 1000 propiedades:**
- Batch 1 (props 0-249): revisar 13 grillas → seleccionar ~30 mejores
- Batch 2 (props 250-499): revisar 13 grillas → seleccionar ~30 mejores
- Batch 3 (props 500-749): revisar 13 grillas → seleccionar ~30 mejores
- Batch 4 (props 750-999): revisar 13 grillas → seleccionar ~30 mejores
- **Ronda final**: con las ~120 seleccionadas, armar grillas y elegir las top 30

Si hay ≤ 250 propiedades, se hace un solo pase directo sin batches.

### Paso 5: Profundizar en las finalistas

Para las propiedades finalistas (~20-30):
1. Obtener sus datos completos del JSON de metadata, incluyendo el campo `imagenes` (array de URLs de todas las fotos)
2. Para cada candidata, armar las URLs en alta resolución: reemplazar `/360x266/` por `/730x532/` en cada URL del array `imagenes`
3. Ver 2-3 fotos en alta resolución con Read para evaluar detalles (terminaciones, humedad, red flags)
4. **Guardar TODAS las URLs hires** (no solo las que se vieron) — se usan en el Paso 7 para el HTML report

### Paso 6: Ranking final

Top 3, Top 10, Interesantes. Incluir links de ZonaProp.

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
