# Skill: Consulta MEV desde Supabase

Consulta expedientes y movimientos de MEV (Provincia de Buenos Aires) directamente desde Supabase. Los movimientos ya estan guardados porque el scraper corre automaticamente. Este skill es la forma predeterminada de buscar movimientos de expedientes de Provincia - es instantaneo y no necesita credenciales MEV.

**IMPORTANTE**: Este skill tiene PRIORIDAD sobre scrape-mev. Cuando el usuario pida ver movimientos, buscar un expediente, o consultar el estado de una causa de Provincia, usar SIEMPRE este skill primero. Solo usar `/scrape-mev` si el usuario lo pide expresamente.

Triggers: "fijate los movimientos de", "que paso con", "movimientos de", "como esta el expediente", "buscar causa", cualquier consulta de expediente de Provincia de Buenos Aires.

## Tool MCP

Solo se usa: `mcp__claude_ai_Supabase__execute_sql`

No se necesitan credenciales MEV. No se scrapea nada. No se guarda nada.

## Buscar un expediente

Si el usuario da un numero de causa, caratula, o nombre de parte:

```sql
SELECT e.id, e.numero_causa, e.caratula, e.jurisdiccion, e.mev_idc, e.mev_ido, e.monitoreo_diario
FROM expedientes e
WHERE e.jurisdiccion = 'Provincia'
  AND (
    e.numero_causa ILIKE '%{busqueda}%'
    OR e.caratula ILIKE '%{busqueda}%'
  )
ORDER BY e.numero_causa;
```

## Obtener movimientos de un expediente

Una vez identificado el expediente (por su `id`):

```sql
SELECT fecha, tipo, descripcion, url_proveido, texto_proveido
FROM movimientos_judicial
WHERE expediente_id = {id}
  AND fuente = 'MEV'
ORDER BY fecha DESC;
```

Para los ultimos N movimientos, agregar `LIMIT N`.

## Leer el contenido de un documento/proveido

La columna `texto_proveido` contiene el texto completo extraido del PDF del proveido. **NO es necesario usar el MCP Judicial (mev_leer_documentos) para leer documentos** — el contenido ya esta en Supabase.

Si necesitas leer un documento especifico:

```sql
SELECT fecha, tipo, descripcion, texto_proveido
FROM movimientos_judicial
WHERE expediente_id = {id}
  AND fuente = 'MEV'
  AND texto_proveido IS NOT NULL
ORDER BY fecha DESC;
```

Para buscar dentro del contenido de los proveidos:

```sql
SELECT fecha, tipo, descripcion, texto_proveido
FROM movimientos_judicial
WHERE expediente_id = {id}
  AND fuente = 'MEV'
  AND texto_proveido ILIKE '%{busqueda}%'
ORDER BY fecha DESC;
```

## Listar todos los expedientes Provincia

```sql
SELECT e.id, e.numero_causa, e.caratula, e.monitoreo_diario,
       (SELECT COUNT(*) FROM movimientos_judicial m WHERE m.expediente_id = e.id AND m.fuente = 'MEV') as total_movimientos,
       (SELECT MAX(fecha) FROM movimientos_judicial m WHERE m.expediente_id = e.id AND m.fuente = 'MEV') as ultimo_movimiento
FROM expedientes e
WHERE e.jurisdiccion = 'Provincia'
ORDER BY e.numero_causa;
```

## Buscar movimientos por tipo o contenido

```sql
SELECT e.numero_causa, e.caratula, m.fecha, m.tipo, m.descripcion
FROM movimientos_judicial m
JOIN expedientes e ON e.id = m.expediente_id
WHERE e.jurisdiccion = 'Provincia'
  AND m.fuente = 'MEV'
  AND (m.tipo ILIKE '%{busqueda}%' OR m.descripcion ILIKE '%{busqueda}%')
ORDER BY m.fecha DESC
LIMIT 20;
```

## Novedades recientes

```sql
SELECT e.numero_causa, e.caratula, m.fecha, m.tipo, m.descripcion
FROM movimientos_judicial m
JOIN expedientes e ON e.id = m.expediente_id
WHERE e.jurisdiccion = 'Provincia'
  AND m.fuente = 'MEV'
  AND m.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
ORDER BY m.fecha DESC;
```

## Tablas Supabase

### expedientes
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | int | PK |
| numero_causa | text | Numero de causa (ej: "42389-2023") |
| caratula | text | Caratula |
| jurisdiccion | text | 'Provincia' para MEV |
| mev_idc | text | ID causa en MEV |
| mev_ido | text | ID organismo en MEV |
| monitoreo_diario | bool | Si se monitorea diariamente |

### movimientos_judicial
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| expediente_id | int | FK a expedientes.id |
| fuente | text | 'MEV' |
| fecha | date | Fecha del movimiento |
| tipo | text | Tipo de actuacion |
| descripcion | text | Texto de la actuacion |
| url_proveido | text | URL al proveido/PDF |
| texto_proveido | text | Texto completo extraido del PDF del proveido |
| pdf_url | text | URL al PDF |
| procesado | bool | Si fue procesado |
| estado | text | Estado del movimiento |
| tarea | text | Tarea asignada |
| responsable | text | Responsable asignado |

## Instrucciones para el Agente

1. Identificar que expediente(s) pide el usuario (por numero, caratula, o nombre de parte)
2. Consultar Supabase con `execute_sql`
3. Mostrar los movimientos de forma clara y cronologica
4. Si el usuario pide "los ultimos movimientos", usar LIMIT
5. Si el usuario pide novedades de un periodo, filtrar por fecha
6. **Para leer el contenido de un proveido/documento, usar la columna `texto_proveido` de Supabase. NO usar mev_leer_documentos del MCP Judicial — el texto ya esta en Supabase.**
7. NO scrapear del MEV. Solo Supabase.
