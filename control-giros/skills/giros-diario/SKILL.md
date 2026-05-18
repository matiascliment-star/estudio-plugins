---
name: giros-diario
description: >
  Corrida diaria del control de facturación mensual de honorarios.
  Lee giros nuevos desde TRES fuentes: (A) el grupo WhatsApp
  "💰💷💸 giros/transferencias 💰💷💸" via la instancia personal de Mati
  (inst_29a52ca6), (B) movimientos nuevos de movimientos_judicial (MEV) y
  movimientos_pjn (PJN), (C) mails "Aviso - Últimos movimientos" del Banco
  Ciudad leídos vía Microsoft Graph desde flirteador@hotmail.com.
  Clasifica cada giro como honorarios (facturable) o capital (del cliente),
  proyecta fecha de cobro según día de orden y jurisdicción, matchea
  depósitos del banco contra giros pendientes (descuenta retenciones IVA
  14% + Ganancias 2% s/excedente $67.170), marca girados con fecha real,
  manda resumen del mes con semáforo Confirmado/Proyectado vs tope 50M
  al grupo "Mati y Noe", y avisa al grupo "ejecución-giros" qué clientes
  van a cobrar capital en los próximos 7 días (sin mencionar honorarios).
  Triggers: "giros diario", "control giros", "revisar giros", "corrida
  giros", "facturación mes", "tope 50M", "novedades giros". Programado
  L-V 18:30 AR (después de control-liquidacion).
version: 0.3.0
---

# Skill: Control de giros diario

Objetivo: Mati decide cada día qué giros pedir y cuáles retener sin pasarse de **50M netos facturables por mes**. Privado: tablas RLS-locked solo a su UID, empleadas no ven nada.

**Modelo LLM**: el parseo y clasificación lo hace **este Claude** (Opus 4.7 via Claude Code). NO usar Anthropic API directa.

## Recursos

- **Supabase**: project `wdgdbbcwcrirpnfdmykh` (Estudio Jurídico). RLS lockdown solo UID `dfd103c5-3d6f-4ced-ad6f-b0b180d463a8`.
- **Tablas**:
  - `giros_honorarios` — lo que factura el estudio. Campos clave:
    - `fuente` (`wa_noe`/`proveido_mev`/`proveido_pjn`/`manual`)
    - `jurisdiccion` (`caba`/`provincia`)
    - `fecha_orden` — cuándo el juzgado ordenó la transferencia.
    - `fecha_proyectada_cobro` — calculada por trigger según día de orden.
    - `fecha_girado` — cuándo entró la plata (la setea el match con el banco).
    - `estado` (`pendiente`/`girado`/`retenido`).
    - `mes_imputacion` — calculado por trigger: `mes(fecha_girado ?? fecha_proyectada_cobro)`.
    - Montos: `monto_total`, `monto_honorarios_neto`, `monto_iva`, `monto_intereses_honorarios`, `monto_reintegro_iva`.
  - `giros_capital` — del actor, info-only (NO suma al tope).
  - `movimientos_banco` — cache de mails parseados del Banco Ciudad.
  - `microsoft_oauth_mati` — tokens OAuth para Hotmail.
- **Vista**: `giros_honorarios_match` con columna `neto_esperado_caba` (calc_neto_caba aplicado).
- **Tope mensual**: 50.000.000 ARS de honorarios netos + intereses (sin IVA, sin reintegro, sin capital).
- **Instancia WA personal**: `inst_29a52ca6` (NO la del estudio).
- **Grupo fuente WA**: "💰💷💸 giros/transferencias 💰💷💸".
- **Grupo destino del resumen privado**: "Mati y Noe" → JID `120363026685801986@g.us` (instancia personal).
- **Grupo destino del aviso de capital a ejecución**: "ejecución-giros" (instancia personal `inst_29a52ca6`, igual que "Mati y Noe"). El JID se resuelve dinámicamente en runtime (ver Paso 8b).
- **Microsoft Graph**:
  - client_id: `0cb7d80d-72b7-41a8-b71e-c8fc68d9a986`
  - tenant: `common`
  - cuenta: `flirteador@hotmail.com`

## Reglas de proyección de cobro (CABA)

`fecha_proyectada_cobro` la calcula el trigger SQL `calc_fecha_proyectada_cobro` según el día de la orden. Para referencia:

| Día orden | Día de nota | Día transferencia | Días corridos |
|---|---|---|---|
| Lunes | Martes | Lunes siguiente | +7 |
| Martes | Viernes | Jueves siguiente | +9 |
| Miércoles | Viernes | Jueves siguiente | +8 |
| Jueves | Viernes | Jueves siguiente | +7 |
| Viernes | Martes (sig) | Lunes (sig al martes) | +10 |

**Provincia**: `+3 días` corridos (provisorio hasta que el banco confirme). El banco corrige `fecha_girado` cuando se acredita realmente.

## Retenciones (CABA — Banco Ciudad)

Para matchear depósitos del banco contra giros pendientes, el neto esperado es:

```
neto_acreditado = monto_total
                − (monto_honorarios_neto × 0.14)            # IVA retenido
                − (max(0, hon_neto − 67170) × 0.02)         # Ganancias lineal
```

Función SQL `calc_neto_caba(monto_total, hon_neto)` ya hace este cálculo. Vista `giros_honorarios_match` la expone como `neto_esperado_caba`.

Provincia: agregar `− 3.5%×hon_neto` (IIBB) y `− 10%×hon_neto` (Caja Abogados). No implementado todavía.

## Workflow

### Paso 1 — Ventanas de lectura

```sql
SELECT
  COALESCE((SELECT MAX(wa_fecha) FROM giros_honorarios WHERE fuente='wa_noe'), NOW() - INTERVAL '14 days') AS last_wa,
  COALESCE((SELECT MAX(created_at) FROM giros_honorarios WHERE fuente IN ('proveido_mev','proveido_pjn')), NOW() - INTERVAL '14 days') AS last_mov,
  COALESCE((SELECT MAX(email_fecha) FROM movimientos_banco), NOW() - INTERVAL '14 days') AS last_banco;
```

### Paso 2 — Pasada A: WhatsApp de Noe

1. Identificar `chat_id` del grupo via `mcp__claude_ai_Whatsapp__wa_get_messages` con `instanceId=inst_29a52ca6`, filtrar `chatName` que contenga "giros".
2. Traer mensajes posteriores a `last_wa`, autor "Noe"/"Abogados - Noe".
3. Pre-filter por anchors: `TRANSFERENCIA`, `transfiérase`, `transfiera`, `líbrese`, `libranza`.
4. Para cada candidato: clasificar (ver "Reglas de clasificación") y emitir filas.
5. INSERT con `ON CONFLICT (dedup_key) DO NOTHING`. `fuente='wa_noe'`, `wa_message_id`, `wa_fecha`.

### Paso 3 — Pasada B: proveídos MEV + PJN

**Filtro mínimo**: solo proveídos que tengan **monto explícito en formato dinero** (`$X.XXX,XX`). En la ventana diaria son ~10-50 candidatos, manejable para que el LLM clasifique todo. NO filtrar por "líbrese giro electrónico" ni por destinatario — el LLM decide si es honorarios, capital o descartar.

Columnas reales: `texto_proveido` (MEV) y `texto_documento` (PJN). NO `texto_completo`.

```sql
-- MEV
SELECT id, expediente_id, fecha, descripcion, texto_proveido
FROM movimientos_judicial
WHERE fecha > '<last_mov_date>'
  AND texto_proveido ~* '\$\s*[\d.]+,\d{2}'
  AND NOT EXISTS (SELECT 1 FROM giros_honorarios gh WHERE gh.movimiento_id = movimientos_judicial.id::TEXT)
  AND NOT EXISTS (SELECT 1 FROM giros_capital gc WHERE gc.movimiento_id = movimientos_judicial.id::TEXT);

-- PJN
SELECT id, expediente_id, fecha, descripcion, texto_documento
FROM movimientos_pjn
WHERE fecha > '<last_mov_date>'
  AND texto_documento ~* '\$\s*[\d.]+,\d{2}'
  AND NOT EXISTS (SELECT 1 FROM giros_honorarios gh WHERE gh.movimiento_id = movimientos_pjn.id::TEXT)
  AND NOT EXISTS (SELECT 1 FROM giros_capital gc WHERE gc.movimiento_id = movimientos_pjn.id::TEXT);
```

**Clasificación (vos, el LLM)**:
Para cada candidato, leer el texto y decidir:
- **Honorarios al estudio** → `giros_honorarios`. Señales: "líbrese giro electrónico" a favor de "GARCIA CLIMENT" / "MATIAS CHRISTIAN".
- **Capital al actor** → `giros_capital`. Señales: "líbrese giro" / "transfiérase" al ACTOR (nombre que aparece en la carátula), en concepto de "capital", "crédito laboral", "indemnización", "no imponible".
- **Descartar**: giro a perito, dación en pago sin orden de giro al letrado, inversión a plazo fijo, oficios entre cuentas, escritos del estudio pidiendo cosas (no son proveídos del juez), cualquier cosa sin orden de transferencia firme.

**Filtro recomendado para back-fill o búsqueda exhaustiva**:

El filtro "descripción empieza con ORDENA/LIBRA/etc." es **demasiado estricto** — pierde proveídos con prefijos del secretario (`KB-`, `MBM-`, `RR-`) o variantes (`SE APRUEBA...`, `DA EN PAGO...`).

El filtro "texto contiene GARCIA CLIMENT + transfiérase" es **demasiado estricto** — pierde proveídos donde el monto a Mati aparece en otra parte del texto.

**Filtro robusto**: buscar proveídos cuyo `texto_documento` contenga la frase **"a favor de [Dr.] MAT[IÍ]AS"** o variantes (`Dr. MATIAS CHRISTIAN`, `orden del Dr. MATIAS`, `nombre del Dr. MATIAS`):

```sql
m.texto_documento ~* '(a\s+favor\s+del?\s+(Dr\.?\s+)?MAT[IÍ]AS|Dr\.?\s+MAT[IÍ]AS\s+CHRISTIAN|orden\s+del\s+(Dr\.?\s+)?MAT[IÍ]AS|nombre\s+del\s+(Dr\.?\s+)?MAT[IÍ]AS)'
```

Esto captura los proveídos donde el juez te designa explícitamente como beneficiario, **independientemente del prefijo de descripción o el orden de las palabras**.

Procesar como Pasada A. `fuente='proveido_mev'`/`'proveido_pjn'`, `movimiento_id`=id del mov.

**Match cruzado WA ↔ proveído** (importante):
Antes de insertar un giro nuevo (sea de honorarios o capital), chequear si ya existe uno `wa_noe` con:
- Mismo `expediente_numero` normalizado (sin "CNT ", sin "/CA001" final).
- `ABS(monto_total - existente.monto_total) <= 10`.

Si encuentra match → **UPDATE** del giro `wa_noe` existente: setear `movimiento_id` con el id del proveído, opcionalmente actualizar `concepto_texto` si el proveído tiene más detalle. NO insertar fila nueva. Mantiene trazabilidad cruzada entre las 2 fuentes.

### Paso 4 — Pasada C: mails Banco Ciudad (Hotmail) — vía pg_net + Edge Function

**IMPORTANTE**: El sandbox del cron bloquea outbound a hosts externos (`graph.microsoft.com`, `*.supabase.co/functions`, etc) tanto desde `curl` como desde `WebFetch`. La salida es ir **por Postgres**: hay funciones SQL que el LLM llama via MCP `execute_sql` (que sí funciona), que internamente usan `pg_net` para invocar la Edge Function `bank-mail-fetch`, y devuelven el JSON con los mails crudos. El LLM parsea los bodies como siempre.

**4a. Disparar request a la Edge Function**

```sql
SELECT bank_mails_request('<ISO8601 desde, ej 2026-05-13T00:00:00Z>', 20);
```

Devuelve `request_id` (bigint). Guardalo.

**4b. Esperar 3 segundos** (con `Bash` `sleep 3`). pg_net trabaja async y necesita el delay para que la respuesta esté disponible.

**4c. Recuperar la respuesta**

```sql
SELECT bank_mails_response(<request_id>);
```

Devuelve jsonb:
```json
{
  "status": "ok",
  "data": {
    "since": "...",
    "total_listed": 5,
    "returned": 2,
    "mails": [
      { "id": "...", "subject": "Aviso - Últimos movimientos", "receivedDateTime": "...", "body": "<texto plano>" }
    ]
  }
}
```

Si `status='pending'` (todavía no llegó): esperar 2-3 segundos más y reintentar `bank_mails_response`. Hasta 3 reintentos. Si después de 15 segundos sigue pending, considerar como error.

Si `status='error'`: registrar en `giros_runs.errores`, en el resumen agregar "⚠️ Pasada C falló (banco)" y continuar con las demás pasadas. **NO mandar nada a TRABAJO**.

**4b. Parsear cada `body` (vos, el LLM)**

El body viene en texto plano. Formato típico:
```
Te informamos los movimientos al DD/MM de tu cuenta CA $ 000000260200356738
FECHA   DETALLE                                  IMPORTE
13/05   DEP JUDI - DEPOSITO JUDICIAL    $ 13.119.626,82 [arriba]
13/05   COMPRA PEDIDOSYA*PROPINA - CABA $ 750,00 [abajo]
```

Para cada línea con formato `DD/MM   DETALLE   $ MONTO [arriba|abajo]`, extraer:
- `fecha` = DD/MM convertido a YYYY-MM-DD usando el año del mail (`receivedDateTime`).
- `detalle` = el texto del medio (trim).
- `importe` = monto numérico (sacar puntos miles, coma decimal). Ej. `13.119.626,82` → `13119626.82`.
- `signo` = `credito` si `[arriba]`, `debito` si `[abajo]`.

**4c. Upsert en `movimientos_banco`**

El UNIQUE es `(banco, fecha, importe, detalle)` — un mismo movimiento aparece en múltiples mails consecutivos pero solo se inserta una vez.

```sql
INSERT INTO movimientos_banco
  (banco, fecha, detalle, importe, signo, cuenta, email_message_id, email_fecha)
VALUES ('ciudad', ..., ..., ..., ..., ..., '<msg_id>', '<receivedDateTime>')
ON CONFLICT (banco, fecha, importe, detalle) DO NOTHING;
```

### Paso 5 — Reglas de clasificación de giros (texto/proveído)

Para cada candidato de Paso 2 o 3, decidir destino + despejar números:

| Concepto del texto | Tabla | Campos a poblar |
|---|---|---|
| "honorarios" / "honorarios e IVA" | `giros_honorarios` | `monto_honorarios_neto`, `monto_iva` |
| "reintegro IVA" / "reintegro de IVA" | `giros_honorarios` | `monto_reintegro_iva` (NO suma al tope) |
| "intereses sobre honorarios" | `giros_honorarios` | `monto_intereses_honorarios` |
| "capital" / "crédito laboral" / "no imponible" / "indemnización" | `giros_capital` | `monto_capital` |
| "intereses provenientes de crédito laboral" | `giros_capital` | `monto_intereses_capital` |

**Despeje**:
- Desglose explícito → respetar números.
- "Honorarios e IVA" sin desglose → `hon = total/1.21`, `iva = total − hon`.
- Un proveído puede generar 1 o 2 filas (capital al actor + honorarios al letrado).

**Filtros**:
- Descartar charla, fotos, "hay que prestar caución", comentarios.
- Mensajes válidos siempre tienen monto + concepto + (carátula o número).

**Montos en letras**: convertir. Ej "PESOS CUARENTA Y OCHO MILLONES..." → `48450996.02`.

**`fecha_orden`**: buscar "Agendado el: DD/MM/YYYY" o "Fecha de notificación por cédula ... DD/MM/YYYY". Fallback: `wa_fecha`/`fecha_movimiento`. El trigger calcula `fecha_proyectada_cobro` y `mes_imputacion` automáticamente.

### Paso 6 — Vincular `expediente_id` (best-effort)

**Importante**: `expedientes.numero` tiene **padding de ceros** (`CNT 026777/2024`) pero `giros.expediente_numero` típicamente no (`CNT 26777/2024`). Hay que normalizar quitando prefijo no numérico y ceros leading antes de comparar.

**6a. Match por número de expediente (primer intento)**:

```sql
WITH normalized AS (
  SELECT gh.id AS giro_id, e.id AS exp_id
  FROM giros_honorarios gh
  CROSS JOIN expedientes e
  WHERE gh.expediente_id IS NULL AND gh.expediente_numero IS NOT NULL
    AND regexp_replace(gh.expediente_numero, '^[^0-9]*0*', '') = regexp_replace(e.numero, '^[^0-9]*0*', '')
)
UPDATE giros_honorarios gh SET expediente_id = n.exp_id
FROM normalized n WHERE gh.id = n.giro_id;

-- Idem giros_capital (mismo patrón, cambiando tabla).
```

**6b. Fallback por actor (carátula) con dedup y normalización**:

Muchos giros (especialmente los de WA de Noe) traen carátula pero no número o el número viene mal parseado. Después del 6a, intentar match por el actor (parte antes de `c/`) contra `expedientes.caratula`, con:
1. Strip de prefijos `"Incidente Nº 1 - "` y `"ACTOR: "`.
2. Normalización de tildes (Á→A, É→E, etc.) en ambos lados.
3. Dedup por número normalizado (`regexp_replace(numero, '^[^0-9]*0*', '')`) para colapsar expedientes duplicados como `024987/2023` y `CNT 024987/2023` que son el mismo caso con distinto formato — se elige el canónico (numero más largo, típicamente con prefijo CNT y padding).

**Sólo aplicar si después de la dedup queda 1 match único**. Los que quedan con 2+ expedientes distintos son casos reales de elección que Mati resuelve en la app.

```sql
-- giros_honorarios
WITH pendientes AS (
  SELECT id, TRIM(translate(upper(
    regexp_replace(
      regexp_replace(caratula, '^Incidente N[º°o\.]\s*\d+\s*-\s*', '', 'i'),
      '^ACTOR:\s*', '', 'i'
    )
  ),'ÁÉÍÓÚÑ','AEIOUN')) AS car_norm
  FROM giros_honorarios
  WHERE expediente_id IS NULL AND caratula IS NOT NULL AND caratula <> ''
),
actores AS (
  SELECT id, TRIM(split_part(car_norm, ' C/', 1)) AS actor FROM pendientes
),
candidatos AS (
  SELECT a.id AS giro_id, e.id AS exp_id, e.numero AS exp_numero,
         regexp_replace(e.numero, '^[^0-9]*0*', '') AS num_norm
  FROM actores a
  JOIN expedientes e ON translate(upper(e.caratula),'ÁÉÍÓÚÑ','AEIOUN') LIKE a.actor || '%'
  WHERE LENGTH(a.actor) >= 5
),
canonico AS (
  -- Dedup por num_norm: si un actor matchea 024987/2023 y CNT 024987/2023, ambos
  -- normalizan a 24987/2023 y queda 1 sola fila — la del numero mas largo.
  SELECT DISTINCT ON (giro_id, num_norm) giro_id, exp_id, num_norm
  FROM candidatos
  ORDER BY giro_id, num_norm, LENGTH(exp_numero) DESC, exp_id ASC
),
unicos AS (
  SELECT giro_id, MIN(exp_id) AS exp_id
  FROM canonico
  GROUP BY giro_id
  HAVING COUNT(*) = 1
)
UPDATE giros_honorarios gh
SET expediente_id = u.exp_id, updated_at = NOW()
FROM unicos u WHERE gh.id = u.giro_id;

-- Idem giros_capital (mismo patron, cambiando tabla).
```

**Casos que NO se auto-resuelven** (necesitan elección manual en la app):
- 2+ expedientes realmente distintos para el mismo actor (ej: KRESTA tiene `CNT 32596/2024` y `CNT 026173/2024`, son 2 casos distintos).
- Actores con apellido muy corto (<5 chars) — evitamos espurios.
- Carátulas tipo `"AVALOS, JUAN Y OTRO c/..."` cuando hay otra carátula con `"AVALOS, JUAN"` solo — puede dar falso positivo. Si esto pasa, agregar a la blacklist.

Si queda sin matchear después de 6a y 6b, no es bloqueante.

### Paso 7 — Match banco ↔ giros (autoset `fecha_girado`)

**7a. Marcar como `ignorado` el ruido**

Antes del match, marcar como `match_estado='ignorado'` todos los movimientos que NO son giros judiciales (débitos, compras, transferencias propias, devoluciones). Así no aparecen en el contador de pendientes.

```sql
UPDATE movimientos_banco
SET match_estado = 'ignorado',
    notas = COALESCE(notas, '') || ' [auto-ignorado: ruido no judicial]'
WHERE match_estado = 'sin_match'
  AND (
    signo = 'debito'
    OR (signo = 'credito'
        AND detalle NOT ILIKE '%DEP JUDI%'
        AND detalle NOT ILIKE '%DEPOSITO JUDICIAL%')
  );
```

**7a-bis. Refresh de match_multiple stale**

Antes de procesar los `sin_match` nuevos, revalidar los `match_multiple` existentes. Los candidatos almacenados en el snapshot `match_candidatos` (JSONB) pueden quedar inválidos cuando esos giros fueron asignados a otro mov en una corrida posterior. Si quedan 0 candidatos pendientes en ventana ±30 días → marcar como `sin_match` y vaciar el snapshot. Si queda 1 → auto-asignar como `asignado_manual`.

```sql
WITH multis AS (
  SELECT id, fecha, importe FROM movimientos_banco WHERE match_estado = 'match_multiple'
),
candidatos AS (
  SELECT m.id AS mov_id, m.fecha, m.importe,
         jsonb_agg(
           jsonb_build_object(
             'giro_id', gh.id, 'expediente', gh.expediente_numero, 'caratula', gh.caratula,
             'neto_esperado', calc_neto_caba(gh.monto_total, gh.monto_honorarios_neto),
             'diff', ABS(calc_neto_caba(gh.monto_total, gh.monto_honorarios_neto) - m.importe)
           ) ORDER BY ABS(calc_neto_caba(gh.monto_total, gh.monto_honorarios_neto) - m.importe)
         ) AS candidatos_validos,
         COUNT(*) AS n
  FROM multis m
  JOIN giros_honorarios gh
    ON gh.estado = 'pendiente' AND gh.jurisdiccion = 'caba'
   AND ABS(calc_neto_caba(gh.monto_total, gh.monto_honorarios_neto) - m.importe) <= 100000
   AND ABS(gh.fecha_orden - m.fecha) <= 30
  GROUP BY m.id, m.fecha, m.importe
)
-- Actualizar snapshots o marcar como sin_match segun corresponda
-- (luego aplicar 7b a los que quedaron con 1 candidato unico, igual que match nuevo)
```

Luego aplicar la lógica de tolerancia escalonada del 7b sobre cada caso refrescado.

**7b. Match contra giros pendientes — tolerancia escalonada**

**Importante**: este paso procesa **TODOS** los `movimientos_banco` con `match_estado='sin_match'`, no solo los nuevos. Esto permite que cuando se carga un giro retroactivo (por back-fill o por carga manual), el match se haga automáticamente sin intervención.

**REGLA TEMPORAL DURA**: nunca auto-asignar un mov a un giro cuyo `fecha_orden` esté a **más de 30 días** del `mov.fecha` (en cualquier dirección). Esos casos quedan como `sin_match` esperando que aparezca un giro nuevo más cercano en tiempo. Antes esto causaba falsos positivos donde el cron asignaba depósitos nuevos a giros viejos de hace 4-6 meses por ser "único candidato $100k".

**Realidad operativa**: el banco a veces erra el monto hasta **$100.000** (errores de retención mal calculada, diferencias UMA, intereses no contabilizados). Por eso usamos tolerancia escalonada:

| Tolerancia (|diff|) | Tratamiento |
|---|---|
| ≤ $5 | **Match seguro** automático **— pero solo si `ABS(mov.fecha − giro.fecha_orden) ≤ 30 días`** |
| $5 – $100.000 | **Match dudoso**: solo aplicar si hay UN único giro pendiente en esa ventana **Y** `ABS(mov.fecha − giro.fecha_orden) ≤ 30 días`. Si hay 2+, marcar `match_multiple`. |
| > $100.000 | NO matchear automático. Marcar `sin_match`. |

**Si un candidato es matemáticamente compatible pero temporalmente lejano (>30 días)**: NO asignar automático. Dejar `sin_match`. Mati lo revisa manualmente en la app si corresponde.

Para cada `movimientos_banco` con `signo='credito'`, `match_estado='sin_match'`, detalle LIKE `%DEP JUDI%` o `%DEPOSITO JUDICIAL%`:

```sql
-- Primero buscar matches exactos (≤ $5)
SELECT id, neto_esperado_caba, ABS(neto_esperado_caba - <importe>) AS diff
FROM giros_honorarios_match
WHERE estado='pendiente' AND jurisdiccion='caba'
  AND ABS(neto_esperado_caba - <importe>) <= 5;

-- Si no hay matches exactos, ampliar a tolerancia $100k
SELECT id, neto_esperado_caba, ABS(neto_esperado_caba - <importe>) AS diff
FROM giros_honorarios_match
WHERE estado='pendiente' AND jurisdiccion='caba'
  AND ABS(neto_esperado_caba - <importe>) <= 100000
ORDER BY diff;
```

**Decisión** (en este orden):

1. **1 match con diff ≤ $5** → `match_estado='match_unico'`, auto-aplicar.
2. **2+ matches con diff ≤ $5** → `match_estado='match_multiple'`, guardar candidatos. Mati elige en la app.
3. **0 matches con diff ≤ $5, pero 1 con diff $5-$100k** → `match_estado='asignado_manual'` automático (el banco erró pero hay un único candidato). Agregar nota: `'Match con diff $X – banco erró el monto'`.
4. **0 con diff ≤ $5, pero 2+ con diff $5-$100k** → `match_estado='match_multiple'`, guardar todos los candidatos en JSONB con su diff. Mati elige.
5. **0 matches con diff ≤ $100k** → `match_estado='sin_match'`, nota `'Depósito sin giro pendiente que matchee dentro de $100k'`. Sospechoso: probable giro de Provincia (MEV) o cesión no cargada.

```sql
-- caso match único (cualquier tolerancia):
UPDATE giros_honorarios SET fecha_girado=<fecha_banco>, estado='girado' WHERE id=<match_id>;
UPDATE movimientos_banco
SET giro_honorario_id=<match_id>,
    match_estado = CASE WHEN <diff> <= 5 THEN 'match_unico' ELSE 'asignado_manual' END,
    notas = CASE WHEN <diff> <= 5 THEN NULL ELSE 'Banco erró el monto, diff $' || <diff>::text END
WHERE id=<mov_id>;
```

### Paso 8 — Resumen mensual y semáforo

```sql
SELECT
  to_char(mes_imputacion,'YYYY-MM') AS mes,
  COUNT(*) FILTER (WHERE estado='girado')    AS girados,
  COUNT(*) FILTER (WHERE estado='pendiente') AS pendientes,
  COUNT(*) FILTER (WHERE estado='retenido')  AS retenidos,
  SUM(CASE WHEN estado='girado'    THEN monto_honorarios_neto+monto_intereses_honorarios ELSE 0 END)::numeric(14,2) AS confirmado,
  SUM(CASE WHEN estado='pendiente' THEN monto_honorarios_neto+monto_intereses_honorarios ELSE 0 END)::numeric(14,2) AS proyectado
FROM giros_honorarios
WHERE mes_imputacion >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
GROUP BY mes_imputacion ORDER BY mes_imputacion DESC;
```

Semáforo del **mes en curso** sobre `confirmado` (lo que ya entró):
- 🟢 < 70% del tope (< $35M)
- 🟡 70–95% ($35M–$47,5M)
- 🔴 ≥ 95% ($47,5M+)

### Paso 8b — Aviso de capital al grupo "ejecución-giros" (próximos 7 días)

Antes del resumen privado a Mati y Noe, avisar al equipo de ejecución qué clientes van a cobrar capital en los próximos 7 días, para que tengan a mano los expedientes y puedan avisar al cliente si corresponde.

**Importante**: este mensaje sale desde la instancia personal `inst_29a52ca6` al grupo "ejecución-giros" (también de la personal). Nunca incluir honorarios, IVA, ni totales del tope mensual — solo capital del cliente.

**8b.1 Query**: capital pendiente a cobrarse entre HOY y HOY+7 (inclusive).

```sql
SELECT
  gc.id,
  gc.expediente_numero,
  gc.caratula,
  gc.fecha_proyectada_cobro,
  (COALESCE(gc.monto_capital,0) + COALESCE(gc.monto_intereses_capital,0))::numeric(14,2) AS total
FROM giros_capital gc
WHERE gc.estado = 'pendiente'
  AND gc.fecha_proyectada_cobro BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY gc.fecha_proyectada_cobro ASC, gc.expediente_numero ASC;
```

Si la query devuelve 0 filas → **no mandar nada** (silencio absoluto, no mandar "no hay nada esta semana"). Pasar directo al Paso 9.

**8b.2 Resolver JID del grupo "ejecución-giros"** (instancia personal `inst_29a52ca6`):

Usar `wa_get_messages` con `instanceId=inst_29a52ca6`, filtrar por `chatName` que contenga "ejecución" Y "giros" (probar también sin tilde: "ejecucion"). Guardar el JID resultante. Si no se encuentra:
- Registrar error en `giros_runs.errores`: `'no se encontró grupo ejecución-giros en inst_29a52ca6'`.
- En el resumen a Mati y Noe (Paso 9), agregar línea: `⚠️ No se pudo avisar a ejecución-giros (grupo no encontrado)`.
- NO buscar fallbacks en otros grupos ni en otra instancia. Continuar con Paso 9.

**8b.3 Formato del mensaje**:

```
📅 PRÓXIMOS COBROS — [DD/MM al DD/MM]

Estos clientes van a cobrar capital esta semana:

• [DD/MM] — ACTOR (Carátula corta) — Exp [NÚMERO] — $[total]
• [DD/MM] — ACTOR2 (Carátula corta) — Exp [NÚMERO] — $[total]
...

Total estimado de la semana: $[suma]
```

Reglas de formato:
- Mostrar el ACTOR (primer apellido o nombre que figure en la carátula, antes del "c/" o "vs"). Si no se puede extraer, usar carátula completa truncada a 50 chars.
- Fecha en formato `DD/MM` (sin año).
- Montos con separador de miles `.` y decimal `,`. Ej `$1.234.567,89`.
- Ordenar por `fecha_proyectada_cobro` ASC.
- Si hay más de 20 filas, listar las primeras 20 y agregar línea `... y [N] más`.

**8b.4 Enviar**:

Usar `wa_send_text` con `instanceId=inst_29a52ca6` y `chatId` = JID resuelto en 8b.2. Si el envío falla:
- Registrar en `giros_runs.errores`.
- Línea en el resumen a Mati y Noe: `⚠️ Falló envío a ejecución-giros: [motivo]`.
- NO reintentar a ningún otro grupo (ni TRABAJO ni la instancia del estudio).

### Paso 9 — Reporte WhatsApp al grupo "Mati y Noe"

Mandar **siempre y únicamente** al grupo "Mati y Noe" (JID `120363026685801986@g.us`) usando `instanceId=inst_29a52ca6`.

**REGLAS DURAS — NO HAY EXCEPCIONES**:
- ❌ NUNCA mandar al individual de Noe (`5491170166033@s.whatsapp.net`).
- ❌ NUNCA mandar desde la instancia del estudio (ni siquiera el aviso de capital — el grupo "ejecución-giros" está en la instancia personal).
- ❌ NUNCA mandar al grupo TRABAJO del estudio bajo NINGUNA circunstancia (ni siquiera para reportar errores). Las empleadas leen TRABAJO y no deben saber que existe el sistema de giros.
- ❌ NUNCA mandar honorarios, IVA, ni el tope de 50M a ningún grupo que no sea "Mati y Noe".
- ✅ Resumen privado completo (honorarios + capital + semáforo) → grupo "Mati y Noe" (JID `120363026685801986@g.us`) desde `inst_29a52ca6`.
- ✅ Aviso de capital próximos 7 días → grupo "ejecución-giros" desde `inst_29a52ca6`. Solo capital del cliente, sin info del estudio.

Si la corrida falla entera (no se puede mandar a "Mati y Noe" por sesión WA caída), NO usar TRABAJO como fallback — solo registrar en `giros_runs.errores` y terminar silencioso. Mati va a ver el run faltante en la app.

Formato:

```
💰 GIROS — [DD/MM]

📥 Hoy detectados:
  Honorarios: [N] nuevos · $[X] netos
  Capital: [M] nuevos · $[Y]
  Mails banco procesados: [K]
  Depósitos matcheados: [J] de [K_creditos] (auto)

📊 MES EN CURSO [YYYY-MM]:
  Confirmado (girado): $[C] / $50M  [SEMÁFORO]
  Proyectado (pendiente): $[P]
  Total potencial: $[C+P]
  • Girados: [n] filas
  • Pendientes: [m] filas
  • Retenidos: [k] filas

[Si confirmado ≥ 70% del tope]
⚠️  Cerca del tope. Próximos $[diff] retenibles.

[Si hay depósitos sin matchear]
🔍 [N] depósitos sin asignar → revisar en la app.

📅 Mes anterior: confirmado $[prev]
```

### Paso 10 — Marcar run

(Opcional) Insertar registro en una tabla `giros_corridas` (crear si no existe) con timestamp, candidatos procesados, filas insertadas, matches automáticos, errores. Sirve para health check.

## Notas operativas

- **NUNCA** usar la instancia del estudio para nada en este skill (ni para leer ni para escribir).
- Desde `inst_29a52ca6` solo se escribe a 2 destinos: "Mati y Noe" (resumen privado) y "ejecución-giros" (aviso capital 7 días). A ningún otro chat.
- **NUNCA** mandar al grupo TRABAJO bajo ninguna circunstancia. Si todo falla, registrar en `giros_runs.errores` y terminar silencioso.
- Si Microsoft Graph devuelve 401 incluso tras refresh: el refresh_token caducó. Registrar en `giros_runs.errores`, en el resumen a "Mati y Noe" agregar "⚠️ Reconectar Hotmail en la app". NO ir a TRABAJO.
- **Back-fill** manual del chat exportado: usar `extract_from_chat_txt.py <path.txt>` para emitir candidatos JSON, después procesar como Pasada A (backfill inicial se hizo 2026-05-13 con 199 filas).
- El **modelo de consentimiento** está implementado a partir de 2026-05-15: `fecha_orden` (cuando ordenan), `fecha_proyectada_cobro` (calculada), `fecha_girado` (cuando entra). `mes_imputacion` se basa en `fecha_girado` si está, sino en `fecha_proyectada_cobro`. Los 199 históricos fueron re-imputados.
