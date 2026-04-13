# Skill: Consulta PJN desde Supabase

Consulta expedientes y movimientos de PJN (CABA) directamente desde Supabase. Los movimientos ya estan guardados porque el scraper corre automaticamente. Este skill es la forma predeterminada de buscar movimientos de expedientes CABA - es instantaneo y no necesita credenciales PJN.

**IMPORTANTE**: Este skill tiene PRIORIDAD sobre scrape-pjn. Cuando el usuario pida ver movimientos, buscar un expediente, o consultar el estado de una causa de CABA, usar SIEMPRE este skill primero. Solo usar `/scrape-pjn` si el usuario lo pide expresamente.

Triggers: "fijate los movimientos de", "que paso con", "movimientos de", "como esta el expediente", "buscar expediente", "CNT", "CIV", "COM", "CAF", cualquier consulta de expediente CABA.

## Tool MCP

Solo se usa: `mcp__claude_ai_Supabase__execute_sql`

No se necesitan credenciales PJN. No se scrapea nada. No se guarda nada.

## Buscar un expediente

Si el usuario da un numero de causa, caratula, o nombre de parte:

```sql
SELECT e.id, e.numero, e.numero_causa, e.caratula, e.jurisdiccion, e.monitoreo_diario
FROM expedientes e
WHERE e.jurisdiccion = 'CABA'
  AND (
    e.numero_causa ILIKE '%{busqueda}%'
    OR e.caratula ILIKE '%{busqueda}%'
    OR e.numero ILIKE '%{busqueda}%'
  )
ORDER BY e.numero_causa;
```

## Obtener movimientos de un expediente

Una vez identificado el expediente (por su `id`):

```sql
SELECT fecha, tipo, descripcion, fojas, oficina, url_documento, texto_documento
FROM movimientos_pjn
WHERE expediente_id = {id}
ORDER BY fecha DESC;
```

Para los ultimos N movimientos, agregar `LIMIT N`.

## Leer el contenido de un documento

La columna `texto_documento` contiene el texto completo extraido del PDF del movimiento. **NO es necesario usar el MCP Judicial (pjn_leer_documentos) para leer documentos** — el contenido ya esta en Supabase.

Si necesitas leer un documento especifico:

```sql
SELECT fecha, tipo, descripcion, texto_documento
FROM movimientos_pjn
WHERE expediente_id = {id}
  AND texto_documento IS NOT NULL
ORDER BY fecha DESC;
```

Para buscar dentro del contenido de los documentos:

```sql
SELECT fecha, tipo, descripcion, texto_documento
FROM movimientos_pjn
WHERE expediente_id = {id}
  AND texto_documento ILIKE '%{busqueda}%'
ORDER BY fecha DESC;
```

## Listar todos los expedientes CABA

```sql
SELECT e.id, e.numero, e.numero_causa, e.caratula, e.monitoreo_diario,
       (SELECT COUNT(*) FROM movimientos_pjn m WHERE m.expediente_id = e.id) as total_movimientos,
       (SELECT MAX(fecha) FROM movimientos_pjn m WHERE m.expediente_id = e.id) as ultimo_movimiento
FROM expedientes e
WHERE e.jurisdiccion = 'CABA'
ORDER BY e.numero_causa;
```

## Buscar movimientos por tipo o contenido

```sql
SELECT e.numero_causa, e.caratula, m.fecha, m.tipo, m.descripcion
FROM movimientos_pjn m
JOIN expedientes e ON e.id = m.expediente_id
WHERE e.jurisdiccion = 'CABA'
  AND (m.tipo ILIKE '%{busqueda}%' OR m.descripcion ILIKE '%{busqueda}%')
ORDER BY m.fecha DESC
LIMIT 20;
```

## Novedades recientes

```sql
SELECT e.numero_causa, e.caratula, m.fecha, m.tipo, m.descripcion
FROM movimientos_pjn m
JOIN expedientes e ON e.id = m.expediente_id
WHERE e.jurisdiccion = 'CABA'
  AND m.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
ORDER BY m.fecha DESC;
```

## Tablas Supabase

### expedientes
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | int | PK |
| numero | text | Numero completo SCW (ej: "CNT 019429/2025") |
| numero_causa | text | Numero normalizado (ej: "19429/2025") |
| caratula | text | Caratula del expediente |
| jurisdiccion | text | 'CABA' para PJN |
| monitoreo_diario | bool | Si se monitorea diariamente |

### movimientos_pjn
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| expediente_id | int | FK a expedientes.id |
| fecha | date | Fecha del movimiento |
| tipo | text | Tipo de actuacion |
| descripcion | text | Texto de la actuacion |
| fojas | text | Fojas |
| oficina | text | Oficina (ej: "T42") |
| url_documento | text | URL al documento PDF |
| texto_documento | text | Texto completo extraido del PDF del documento |
| pjn_cid | text | ID interno PJN |
| procesado | bool | Si fue procesado |

## Instrucciones para el Agente

1. Identificar que expediente(s) pide el usuario (por numero, caratula, o nombre de parte)
2. Consultar Supabase con `execute_sql`
3. Mostrar los movimientos de forma clara y cronologica
4. Si el usuario pide "los ultimos movimientos", usar LIMIT
5. Si el usuario pide novedades de un periodo, filtrar por fecha
6. **Para leer el contenido de un documento, usar la columna `texto_documento` de Supabase. NO usar pjn_leer_documentos del MCP Judicial — el texto ya esta en Supabase.**
7. NO scrapear del PJN. Solo Supabase.
