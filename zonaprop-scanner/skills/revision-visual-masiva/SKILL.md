---
name: revision-visual-masiva
description: >
  Revisión visual masiva de propiedades inmobiliarias desde Supabase. Descarga todos los thumbnails,
  arma grillas/montajes de contacto para que Claude las recorra visualmente, y luego profundiza en
  las mejores con fotos en alta resolución. Usar siempre que el usuario pida: "revisar propiedades",
  "ver todas las fotos", "mostrame las propiedades", "cuáles son lindas", "buscar propiedades lindas",
  "analizar visualmente todas", "revisar las que bajé", "ver las de hoy", "cuáles me gustan",
  "filtrar por fotos", "revision masiva", o cualquier pedido de ver muchas propiedades a la vez
  para elegir las mejores visualmente. También cuando dice "ver las 700" o similar indicando que
  quiere una revisión exhaustiva, no solo un filtro por datos.
---

# Revisión Visual Masiva de Propiedades

## Cuándo usar este skill

Cuando el usuario quiere revisar visualmente TODAS las propiedades de su base de datos (o un subconjunto grande) para encontrar las que se ven bien. No es un filtro por precio o m² — es una revisión visual real donde Claude mira las fotos y elige las lindas.

## Flujo completo

### Paso 1: Obtener datos de Supabase

Consultar la tabla `propiedades` para obtener todas las propiedades activas. Paginar de a 1000 porque Supabase tiene ese límite por request. Deduplicar por URL base del link (ignorando query params).

```
SUPABASE_URL y SUPABASE_KEY vienen de las env vars del MCP server,
pero si las tools MCP fallan, Claude puede consultar Supabase directamente
via REST API usando las credenciales que el usuario proporcione.
```

Campos necesarios: `id, link, imagen, imagenes, barrio, direccion, precio, moneda, m2, precio_m2, ambientes, dormitorios, banos, cochera, diff_vs_prom_general`

### Paso 2: Descargar thumbnails

Usar el script `scripts/download_thumbs.py` para descargar en paralelo los thumbnails de todas las propiedades. El script:
- Usa ThreadPoolExecutor con 20 workers
- Guarda cada thumbnail como `{idx:04d}.jpg` en una carpeta `thumbs/`
- Usa las URLs tal cual vienen (360x266 del CDN de ZonaProp)
- Reporta progreso cada 100 descargas

Ejecutar así:
```bash
python3 <skill-path>/scripts/download_thumbs.py <metadata.json> <output-dir>
```

Donde `metadata.json` es el JSON con todas las propiedades (deduplicadas) y `output-dir` es donde guardar los thumbnails.

### Paso 3: Armar montajes en grilla

Usar el script `scripts/make_grids.py` para crear imágenes de contacto. Cada grilla tiene 50 propiedades (10 columnas x 5 filas) con:
- Thumbnail de 200x150px
- Label debajo con: número de índice, barrio, precio, m², ambientes, diff vs promedio
- El diff se muestra en rojo si es < -20% (oportunidad)

Ejecutar así:
```bash
python3 <skill-path>/scripts/make_grids.py <metadata.json> <thumbs-dir> <output-dir>
```

Esto genera archivos `page_00.jpg`, `page_01.jpg`, etc.

### Paso 4: Revisión visual de grillas

Recorrer TODAS las grillas con la tool Read. En cada grilla, identificar las propiedades que se ven visualmente atractivas: interiores luminosos, terminaciones modernas, buenos amenities (pileta, terraza), plantas/verde, cocinas de diseño, pisos de madera.

Anotar los índices (#) de las que llaman la atención. Tener en cuenta que los thumbnails son chicos, así que buscar señales claras: mucha luz, colores cálidos, espacios amplios, verde visible.

Es importante ver TODAS las grillas, no saltear ninguna. Si son 34 grillas, ver las 34. El usuario pidió una revisión exhaustiva.

### Paso 5: Profundizar en las candidatas

Para las propiedades que pasaron el filtro visual (típicamente 10-20):
1. Obtener sus datos completos del JSON de metadata
2. Descargar 2-3 fotos en mayor resolución (reemplazar `/360x266/` por `/730x532/` en la URL)
3. Ver cada foto con Read y evaluar:
   - Estado general y mantenimiento
   - Calidad de terminaciones (pisos, cocina, baños)
   - Luminosidad
   - Red flags (humedad, grietas, renders truchos vs fotos reales)
   - Si el precio parece acorde a lo que se ve

### Paso 6: Ranking final

Armar un ranking de las mejores propiedades, ordenadas por atractivo visual + relación precio/calidad. Para cada una incluir:
- Barrio, dirección, precio, m², ambientes
- Diff vs promedio del barrio
- Descripción breve de por qué es linda
- **Link de ZonaProp** (importante: el usuario quiere ir a verlas)

Separar en categorías:
- **Top 3**: Las que iría a ver ya
- **Interesantes**: Buenas pero con alguna reserva
- **Descartadas**: Se veían bien en el thumbnail pero no pasaron la inspección detallada

## Notas importantes

- Los m² en ZonaProp a veces están inflados (incluyen terraza, patio descubierto). Si el precio/m² es ridículamente bajo (< $10), probablemente los m² están mal cargados. Filtrar esos con `m2 > 20 AND m2 < 500 AND precio_m2 > 100`.
- Muchas propiedades aparecen duplicadas (misma propiedad con distintos query params en el link). Deduplicar siempre por `link.split('?')[0]`.
- Los thumbnails de ~2KB son placeholders rotos, ignorarlos.
- Si la primera foto de un aviso es un render 3D muy pulido, marcar como "render" — hay que desconfiar de la calidad real.
- La CDN de ZonaProp es `imgar.zonapropcdn.com` y no requiere autenticación.

## Dependencias

- Python 3 con `Pillow` (instalar con `pip install Pillow --break-system-packages` si no está)
- Acceso a Supabase (via MCP tools o directo via REST API)
