---
name: scrape-mev
description: >
  MEV (Mesa de Entradas Virtual) y SCBA (Suprema Corte de Buenos Aires) -
  scraping, consultas, escritos, borradores y presentaciones electronicas.
  Usa este skill siempre que el usuario pida: scrapear, consultar, extraer o buscar
  causas o movimientos del MEV, Mesa de Entradas Virtual, SCBA, justicia de
  Provincia de Buenos Aires, o notificaciones judiciales provinciales.
  Tambien para subir escritos, presentar escritos, guardar borradores,
  borradores con adjuntos, presentaciones electronicas en SCBA/MEV,
  notificaciones.scba.gov.ar, o cualquier operacion sobre causas de Provincia.
  Triggers: "scrapear MEV", "movimientos MEV", "causas de provincia",
  "subir escrito SCBA", "borrador SCBA", "borrador provincia", "presentar escrito SCBA",
  "escrito MEV", "borrador MEV", "adjunto SCBA", "notificaciones.scba".
---

# Skill: Scraper MEV (Mesa de Entradas Virtual - Provincia de Buenos Aires)

Todo se hace a traves de las **tools MCP** del server `judicial`. NO leer archivos de codigo fuente, NO instalar dependencias, NO escribir scripts. Solo invocar las tools.

## Credenciales

Las credenciales se pasan como parametros a cada tool:
- `usuario`: Email del usuario MEV (leer de `~/.env` -> `MEV_USUARIO`)
- `password`: Password del usuario MEV (leer de `~/.env` -> `MEV_PASSWORD`)

## Tools MCP disponibles

### Consulta de causas y movimientos

| Tool | Descripcion | Parametros clave |
|------|-------------|------------------|
| `mev_listar_causas` | Lista todas las causas del usuario en MEV | `usuario`, `password` |
| `mev_obtener_movimientos` | Obtiene movimientos de una causa | `usuario`, `password`, `idc`, `ido` |
| `mev_scrape_masivo` | Scrape masivo de multiples causas con guardado en Supabase | `usuario`, `password`, `guardar_en_supabase` |

### Cedulas de notificacion

| Tool | Descripcion | Parametros clave |
|------|-------------|------------------|
| `scba_obtener_cedulas` | Obtiene cedulas de notificacion SCBA | `usuario`, `password` |

### Escritos y borradores SCBA

| Tool | Descripcion | Parametros clave |
|------|-------------|------------------|
| `scba_guardar_borrador` | Guarda borrador de escrito (solo texto HTML) | `usuario`, `password`, `id_org`, `id_causa`, `texto_html`, `titulo` |
| `scba_guardar_borrador_adjuntos` | Guarda borrador CON archivos adjuntos (PDFs) | `usuario`, `password`, `id_org`, `id_causa`, `texto_html`, `titulo`, `adjuntos_base64` |
| `scba_info_causa` | Consulta info de una causa para presentacion | `usuario`, `password`, `id_org`, `id_causa` |
| `scba_listar_presentaciones` | Lista borradores y presentaciones enviadas | `usuario`, `password`, `id_org`, `id_causa` |

## Estructura de datos

### Causa MEV
```json
{
  "numero": "42389-2023",
  "caratula": "GARCIA JUAN CARLOS C/ EMPRESA SA S/ PRETENSION INDEMNIZATORIA",
  "organismo": "TRIBUNAL DEL TRABAJO NRO 2 - SAN MARTIN",
  "idc": "abc123def456",
  "ido": "xyz789ghi012"
}
```

Los campos `idc` (ID causa) y `ido` (ID organismo) son necesarios para `mev_obtener_movimientos` y las tools de escritos SCBA.

### Movimiento MEV
```json
{
  "fecha": "2025-01-15",
  "tipo": "SENTENCIA",
  "descripcion": "Se dicta sentencia definitiva...",
  "url_proveido": "/InterfazBootstrap/VerProveido.aspx?id=XXXXX"
}
```

## Vinculacion MEV <-> SCBA Escritos

Los IDs de `mev_listar_causas` se mapean a las tools de escritos SCBA asi:
- `idc` del MEV -> `id_causa` de SCBA escritos
- `ido` del MEV -> `id_org` de SCBA escritos

## Tipos de presentacion SCBA

| Codigo | Tipo |
|--------|------|
| 1 | Escritos (default) |
| 2 | Oficios |
| 3 | Cedulas |
| 4 | Mandamientos |

## Flujo para guardar borrador SCBA

1. Obtener `idc` e `ido` de la causa con `mev_listar_causas`
2. Usar `scba_guardar_borrador` con `id_org` = `ido`, `id_causa` = `idc`, texto HTML y titulo
3. Si hay adjuntos PDF: usar `scba_guardar_borrador_adjuntos` en vez de `scba_guardar_borrador`
4. El borrador queda guardado para firmar digitalmente desde el portal web

### Ejemplo borrador con texto
```
Tool: scba_guardar_borrador
id_org: 301  (ej: TT1 La Plata - obtener de mev_listar_causas)
id_causa: 12345  (obtener de mev_listar_causas)
texto_html: "<p>SOLICITA SE LIBRE PRONTO DESPACHO...</p>"
titulo: "PRONTO DESPACHO"
tipo_presentacion: "1"
```

### Ejemplo borrador con adjunto PDF
```
Tool: scba_guardar_borrador_adjuntos
id_org: 301
id_causa: 12345
texto_html: "<p>ACOMPANA DOCUMENTAL...</p>"
titulo: "ACOMPANA DOCUMENTAL"
adjuntos_base64: [{ base64: "...", nombre: "documental.pdf", mime: "application/pdf" }]
```

## Instrucciones para el Agente

1. Leer `~/.env` para obtener `MEV_USUARIO` y `MEV_PASSWORD`
2. Usar las tools MCP directamente — NUNCA leer archivos de codigo, instalar dependencias ni escribir scripts
3. Para listar causas: `mev_listar_causas`
4. Para ver movimientos: `mev_obtener_movimientos` con `idc` e `ido` (obtenidos de `mev_listar_causas`)
5. Para scrape masivo: `mev_scrape_masivo`
6. Para borradores SCBA: primero `mev_listar_causas` para obtener IDs, luego `scba_guardar_borrador`
7. Para ver cedulas: `scba_obtener_cedulas`
