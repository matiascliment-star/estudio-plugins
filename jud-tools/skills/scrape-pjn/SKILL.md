---
name: scrape-pjn
description: >
  PJN (Poder Judicial de la Nacion) - scraping, consultas, escritos y borradores.
  Usa este skill siempre que el usuario pida: scrapear, consultar, extraer o buscar
  expedientes o movimientos del PJN, SCW, Poder Judicial de la Nacion, o causas
  de CABA/justicia nacional. Tambien para subir escritos, presentar escritos,
  guardar borradores, presentaciones electronicas en PJN, escritos.pjn.gov.ar,
  o cualquier operacion sobre expedientes nacionales.
  Triggers: "scrapear PJN", "movimientos PJN", "expedientes judiciales de nacion",
  "subir escrito", "subir borrador", "guardar borrador", "presentar escrito",
  "escrito PJN", "borrador PJN", "CNT", "CIV", "COM", "CAF", "escritos.pjn".
---

# Skill: Scraper PJN (Poder Judicial de la Nacion - SCW)

Todo se hace a traves de las **tools MCP** del server `judicial`. NO leer archivos de codigo fuente, NO instalar dependencias, NO escribir scripts. Solo invocar las tools.

## Credenciales

Las credenciales se pasan como parametros a cada tool:
- `usuario`: CUIT del usuario PJN (leer de `~/.env` -> `PJN_USUARIO`)
- `password`: Password del usuario PJN (leer de `~/.env` -> `PJN_PASSWORD`)

## Tools MCP disponibles

### Consulta de expedientes

| Tool | Descripcion | Parametros clave |
|------|-------------|------------------|
| `pjn_listar_expedientes` | Lista TODOS los expedientes del usuario | `usuario`, `password`, `todas_las_paginas` (bool) |
| `pjn_buscar_expediente` | Busca expediente por numero o filtros | `usuario`, `password`, `numero_expediente` o `filtros` |
| `pjn_obtener_movimientos` | Obtiene movimientos/actuaciones de un expediente | `usuario`, `password`, `numero_expediente` |
| `pjn_consulta_publica` | Busca en consulta publica (cualquier expediente) | `usuario`, `password`, `jurisdiccion`, `numero`, `anio` |
| `pjn_jurisdicciones` | Lista jurisdicciones disponibles | (sin parametros) |

### Documentos y cedulas

| Tool | Descripcion | Parametros clave |
|------|-------------|------------------|
| `pjn_leer_documentos` | Descarga y lee PDFs de un expediente | `usuario`, `password`, `numero_expediente` |
| `pjn_leer_documentos_lote` | Lee documentos de multiples expedientes | `usuario`, `password`, `expedientes` (array) |
| `pjn_obtener_cedulas` | Obtiene cedulas de notificacion PJN | `usuario`, `password` |

### Escritos y borradores

| Tool | Descripcion | Irreversible? |
|------|-------------|---------------|
| `pjn_info_escrito` | Consulta info del expediente para escritos | No |
| `pjn_guardar_borrador` | Guarda escrito como borrador | No |
| `pjn_enviar_borrador` | Envia borrador al tribunal | **SI** |
| `pjn_presentar_escrito` | Presenta escrito directo al tribunal | **SI** |

## Estructura de datos

### Expediente
```json
{
  "numero": "CNT 019429/2025",
  "dependencia": "JUZGADO NACIONAL DE 1RA INSTANCIA DEL TRABAJO NRO. 42",
  "caratula": "GARCIA, JUAN C/ EMPRESA SA S/ DESPIDO",
  "situacion": "En tramite",
  "ultimaActuacion": "15/01/2025"
}
```

### Movimiento
```json
{
  "fecha": "2025-01-15",
  "tipo": "SENTENCIA",
  "descripcion": "Se dicta sentencia definitiva...",
  "oficina": "T42",
  "fojas": "125/130",
  "url_documento": "https://scw.pjn.gov.ar/scw/viewer.seam?..."
}
```

## Jurisdicciones comunes

| Codigo | Jurisdiccion |
|--------|-------------|
| 0 | CSJ (Corte Suprema) |
| 1 | CIV (Civil) |
| 7 | CNT (Trabajo) |
| 10 | COM (Comercial) |
| 2 | CAF (Contencioso Administrativo Federal) |
| 8 | CFP (Criminal y Correccional Federal) |

## Distincion Principal vs Incidente

- **Principal**: `CNT 19429/2025` (numero/anio)
- **Incidente**: `CNT 19429/2025/1` (numero/anio/incidente)

## Tipos de escrito

| Codigo | Tipo |
|--------|------|
| M | MERO TRAMITE |
| E | ESCRITO |
| C | CONTESTACION DEMANDA |
| I | ESCRITO DEMANDA / DOCUMENTAL DE INICIO |
| H | SOLICITUD HABILITACION DIA |

## Flujo para guardar borrador con PDF

1. Usar `pjn_guardar_borrador` con `numero_expediente` directo (ej: `"CNT 6379/2024"`)
2. El PDF se pasa como `pdf_base64`
3. El ID interno se resuelve automaticamente
4. Para enviar al tribunal: usar `pjn_enviar_borrador` con el `id_escrito` devuelto (**IRREVERSIBLE**)

## Consulta publica

La tool `pjn_consulta_publica` busca cualquier expediente (no solo los del usuario). Requiere login para evitar captcha.

**IMPORTANTE sobre expedientes CSJN con sufijo /CA001:**
Los numeros con /CA001 refieren al recurso de apelacion ante la Camara, NO al expediente de primera instancia. Si la caratula no coincide, buscar por parte via Chrome.

**Busqueda por parte (solo via Chrome):**
La consulta publica por parte SOLO permite buscar por DEMANDADO. Requiere Claude in Chrome:
1. Navegar a `https://scw.pjn.gov.ar/scw/home.seam`
2. Activar tab "Por parte"
3. Completar formulario con `form_input`
4. Buscar y extraer resultados

## Instrucciones para el Agente

1. Leer `~/.env` para obtener `PJN_USUARIO` y `PJN_PASSWORD`
2. Usar las tools MCP directamente — NUNCA leer archivos de codigo, instalar dependencias ni escribir scripts
3. Para listar expedientes: `pjn_listar_expedientes`
4. Para buscar uno especifico: `pjn_buscar_expediente` con `numero_expediente`
5. Para ver movimientos: `pjn_obtener_movimientos` con `numero_expediente`
6. Para buscar expedientes ajenos: `pjn_consulta_publica` con jurisdiccion + numero + anio
7. Para escritos: `pjn_guardar_borrador` -> `pjn_enviar_borrador` (confirmar con usuario antes de enviar)
8. Si una busqueda por parte es necesaria, usar Chrome (no hay tool MCP para esto)
