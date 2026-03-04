---
name: scrape-csjn-fallos
description: >
  Scraper de fallos de la CSJN (Corte Suprema de Justicia de la Nacion) - Tribunales Federales y Nacionales.
  Usa este skill siempre que el usuario pida "buscar fallos CSJN", "buscar sentencias en CSJN",
  "scrape CSJN", "analizar PDFs de fallos", "buscar perito en fallos", "descargar fallos de sentencias",
  "buscar en Tribunales Federales", o cualquier consulta sobre fallos del sitio csjn.gov.ar.
  Cubre busqueda por palabra clave, busqueda filtrada por tribunal/fecha con captcha via Chrome,
  descarga de PDFs y analisis de texto dentro de los PDFs.
version: 0.1.0
---

# Scraper CSJN - Tribunales Federales y Nacionales

El sitio de la CSJN (https://www.csjn.gov.ar/tribunales-federales-nacionales/) tiene dos buscadores de fallos con mecanismos distintos.

## Herramientas MCP disponibles

El plugin jud-tools incluye estas tools para CSJN:

| Tool | Descripcion |
|------|-------------|
| `csjn_listar_jurisdicciones` | Lista jurisdicciones disponibles (CABA, Provincias) |
| `csjn_listar_tribunales` | Lista tribunales de una jurisdiccion |
| `csjn_buscar_por_palabra_clave` | Busca texto dentro de fallos (buscador-de-fallos.html, sin captcha) |
| `csjn_buscar_sentencias` | Busca por caratula/expediente/firmante (sentencias.html, requiere captcha) |
| `csjn_descargar_fallo` | Descarga un PDF individual y extrae texto |
| `csjn_analizar_pdfs` | Descarga multiples PDFs y busca un termino en todos |

## Buscador 1: Palabra clave (sin captcha)

URL: `buscador-de-fallos.html`

Busca texto full-text dentro del contenido de los fallos. No requiere captcha.
Funciona completamente via la tool `csjn_buscar_por_palabra_clave`.

**Limitacion:** Solo contiene datos historicos (hasta ~2014). No tiene datos recientes.

Los PDFs de este buscador se descargan con `flid` (ID numerico) via `showFile.php`.

## Buscador 2: Sentencias filtradas (requiere captcha)

URL: `sentencias.html`

Busca por caratula, expediente, firmante (que en la UI se llama "Palabra clave"), tribunal, y rango de fechas. Contiene datos actuales.

**Requiere captcha Securimage.** Por esto, la busqueda filtrada necesita Claude in Chrome para:
1. Navegar al formulario
2. Completar los campos
3. Pedirle al usuario que ingrese el captcha
4. Extraer los resultados

### Workflow completo para busqueda con captcha

Leer `references/workflow-chrome-captcha.md` para el procedimiento paso a paso.

### Resumen rapido del workflow

1. Abrir `https://www.csjn.gov.ar/tribunales-federales-nacionales/sentencias.html` en Chrome
2. Completar formulario (camara, fechas, palabra clave)
3. Pedir captcha al usuario
4. Buscar y extraer UUIDs de los PDFs de cada pagina
5. Usar `csjn_analizar_pdfs` para descargar y analizar todos los PDFs

## Analisis masivo de PDFs

La tool `csjn_analizar_pdfs` permite:
- Descargar N PDFs en lote
- Buscar un termino dentro de cada PDF
- Detectar automaticamente si el termino aparece como "perito" (cerca de la palabra "perito")
- Devolver contexto alrededor de cada match

Parametros:
- `pdf_urls`: Array de URLs de PDFs (formato `https://www.csjn.gov.ar/.../sentencia-SGU-{uuid}.pdf`)
- `termino`: Texto a buscar (ej: "Guillermo Vera")
- `contexto`: Caracteres de contexto (default: 120)
- `max_contextos`: Max fragmentos por PDF (default: 5)

## Formato de URLs de PDFs

Los PDFs de sentencias.html siguen el patron:
```
https://www.csjn.gov.ar/tribunales-federales-nacionales/d/sentencia-SGU-{uuid}.pdf
```

Los UUIDs se extraen del HTML de resultados con:
```javascript
document.querySelectorAll('a[href*="sentencia-SGU"]')
```

## Campos del formulario sentencias.html

| Campo HTML | Descripcion | Ejemplo |
|------------|-------------|---------|
| `camara_id` | Tribunal (select) | `C_7` = Cam. Nac. Apel. Trabajo |
| `firmantes` | Palabra clave (texto libre) | `Guillermo Vera` |
| `fecha_fallo_desde` | Fecha desde (DD/MM/YYYY) | `01/01/2025` |
| `fecha_fallo_hasta` | Fecha hasta (DD/MM/YYYY) | `31/12/2025` |
| `captcha_code` | Codigo captcha Securimage | (lo ingresa el usuario) |

La paginacion se maneja con `irPaginaF(indice)` donde indice es 0-based.
