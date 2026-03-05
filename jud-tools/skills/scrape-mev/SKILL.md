---
name: scrape-mev
description: >
  MEV (Mesa de Entradas Virtual) y SCBA (Suprema Corte de Buenos Aires) -
  scraping y consultas de causas, movimientos y cedulas.
  Usa este skill siempre que el usuario pida: scrapear, consultar, extraer o buscar
  causas o movimientos del MEV, Mesa de Entradas Virtual, SCBA, justicia de
  Provincia de Buenos Aires, o notificaciones judiciales provinciales.
  Para SUBIR escritos o guardar borradores en SCBA/MEV, usar el skill
  "subir-escrito-mev" del plugin escritos-judiciales.
  Triggers: "scrapear MEV", "movimientos MEV", "causas de provincia",
  "consultar SCBA", "cedulas SCBA", "notificaciones provincia".
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
| `scba_guardar_borrador` | Guarda borrador de escrito (solo texto HTML, SIN adjuntos) | `usuario`, `password`, `id_org`, `id_causa`, `texto_html`, `titulo` |
| `scba_info_causa` | Consulta info de una causa para presentacion | `usuario`, `password`, `id_org`, `id_causa` |
| `scba_listar_presentaciones` | Lista borradores y presentaciones enviadas | `usuario`, `password`, `id_org`, `id_causa` |

**IMPORTANTE sobre borradores con adjuntos PDF:**
Para guardar borradores CON archivos PDF adjuntos, NO usar la tool MCP `scba_guardar_borrador_adjuntos` directamente (el PDF base64 es demasiado grande para pasar como parametro). En su lugar, usar el **script helper** del plugin `escritos-judiciales`:

```bash
python3 <plugin_escritos_root>/scripts/upload_scba_adjuntos.py \
  --usuario "user@notificaciones.scba.gov.ar" --password "PASS" \
  --id-org 123 --id-causa 456 \
  --titulo "ACOMPAÑA DOCUMENTAL" \
  --texto-html-file "/tmp/escrito.html" \
  --adjuntos "/tmp/doc1.pdf" "/tmp/doc2.pdf"
```

El script lee los PDFs del disco, los codifica en base64 internamente, y llama al MCP server por HTTP.

Para borradores **sin adjuntos** (solo texto HTML), se puede usar la tool MCP `scba_guardar_borrador` directamente ya que el HTML es pequeño.

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
2. **Sin adjuntos**: Usar `scba_guardar_borrador` con `id_org` = `ido`, `id_causa` = `idc`, texto HTML y titulo
3. **Con adjuntos PDF**: Usar el script `upload_scba_adjuntos.py` del plugin `escritos-judiciales` (NO pasar base64 como parametro de tool MCP)
4. El borrador queda guardado para firmar digitalmente desde el portal web

### Ejemplo borrador con texto (sin adjuntos)
```
Tool: scba_guardar_borrador
id_org: 301  (ej: TT1 La Plata - obtener de mev_listar_causas)
id_causa: 12345  (obtener de mev_listar_causas)
texto_html: "<p>SOLICITA SE LIBRE PRONTO DESPACHO...</p>"
titulo: "PRONTO DESPACHO"
tipo_presentacion: "1"
```

## Instrucciones para el Agente

1. Leer `~/.env` para obtener `MEV_USUARIO` y `MEV_PASSWORD`
2. Usar las tools MCP directamente — NUNCA leer archivos de codigo, instalar dependencias ni escribir scripts
3. Para listar causas: `mev_listar_causas`
4. Para ver movimientos: `mev_obtener_movimientos` con `idc` e `ido` (obtenidos de `mev_listar_causas`)
5. Para scrape masivo: `mev_scrape_masivo`
6. Para borradores sin adjuntos: `scba_guardar_borrador` directamente
7. Para borradores con adjuntos PDF: usar el script `upload_scba_adjuntos.py` del plugin `escritos-judiciales`
8. Para ver cedulas: `scba_obtener_cedulas`
