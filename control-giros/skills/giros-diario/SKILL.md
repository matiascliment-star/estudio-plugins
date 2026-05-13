---
name: giros-diario
description: >
  Corrida diaria del control de facturación mensual de honorarios.
  Lee los giros nuevos desde DOS fuentes: (A) el grupo de WhatsApp
  "💰💷💸 giros/transferencias 💰💷💸" via la instancia personal de Mati
  (inst_29a52ca6) y (B) los movimientos nuevos scrapeados de
  movimientos_judicial (MEV) y movimientos_pjn (PJN). Clasifica cada giro
  como honorarios (facturable) o capital (del cliente), despeja honorarios
  netos / IVA / intereses, upserta en giros_honorarios / giros_capital con
  dedup_key, y manda un resumen del mes en curso vía WhatsApp personal con
  semáforo del tope de 50M netos. Triggers: "giros diario", "control giros",
  "revisar giros", "corrida giros", "facturación mes", "tope 50M",
  "novedades giros". Programado para correr todos los días hábiles a las
  18:30 AR (después de la corrida de liquidación).
version: 0.1.0
---

# Skill: Control de giros diario

Objetivo: que Mati pueda **decidir cada día qué giros pedir y cuáles retener** sin pasarse de los 50M netos facturables por mes. Todo el contenido es **privado** — las tablas tienen RLS lockdown solo para el UID de Mati, las empleadas no ven nada.

**Modelo LLM**: NO usar Anthropic API directa (es plata de bolsillo). La extracción/clasificación la hace el Claude que corre este skill (Opus 4.7 via Claude Code).

## Recursos

- **Proyecto Supabase**: `wdgdbbcwcrirpnfdmykh` (Estudio Jurídico)
- **Tablas**: `giros_honorarios` (lo que factura el estudio), `giros_capital` (del actor)
- **Vista**: `giros_honorarios_resumen_mensual` con `facturable_neto = hon_neto + intereses_hon`
- **Tope mensual**: 50.000.000 ARS de honorarios netos (sin IVA, sin reintegro IVA, sin capital)
- **Instancia WA personal**: `inst_29a52ca6` (NO confundir con la del estudio)
- **Grupo fuente** (de donde leemos los giros que pasa Noe): "💰💷💸 giros/transferencias 💰💷💸"
- **Grupo destino del resumen**: "Mati y Noe" — JID `120363026685801986@g.us` (instancia personal). Acá llega el resumen diario; lo ven Mati + Noe juntos.

## Workflow

### Paso 1 — Determinar ventana de lectura

```sql
SELECT GREATEST(
  COALESCE((SELECT MAX(wa_fecha) FROM giros_honorarios WHERE fuente='wa_noe'), '2000-01-01'::timestamptz),
  COALESCE((SELECT MAX(wa_fecha) FROM giros_capital   WHERE fuente='wa_noe'), '2000-01-01'::timestamptz)
) AS last_wa,
GREATEST(
  COALESCE((SELECT MAX(created_at) FROM giros_honorarios WHERE fuente IN ('proveido_mev','proveido_pjn')), '2000-01-01'::timestamptz),
  COALESCE((SELECT MAX(created_at) FROM giros_capital   WHERE fuente IN ('proveido_mev','proveido_pjn')), '2000-01-01'::timestamptz)
) AS last_mov;
```

Si las tablas están vacías, default = 14 días atrás.

### Paso 2 — Pasada A: WhatsApp de Noe

1. Identificar `chat_id` del grupo. Si no lo tenés guardado, listar mensajes recientes via `mcp__claude_ai_Whatsapp__wa_get_messages` con `instanceId=inst_29a52ca6` y filtrar por `chatName` que contenga "giros".
2. Traer mensajes posteriores a `last_wa`. Filtrar autor = "Noe" o "Abogados - Noe".
3. Pre-filter por anchors: `TRANSFERENCIA`, `transfiérase`, `transfiera`, `líbrese`, `libranza`, `transferencia electrónica`.
4. Para cada candidato: clasificar y extraer (ver "Reglas de clasificación" abajo). El LLM = vos (Claude en esta sesión).
5. INSERT con `ON CONFLICT (dedup_key) DO NOTHING`.
   - `fuente='wa_noe'`, `wa_message_id` = id del mensaje WA, `wa_fecha` = timestamp.

### Paso 3 — Pasada B: proveídos MEV + PJN

```sql
-- MEV
SELECT id, expediente_id, fecha_movimiento, descripcion, texto_completo
FROM movimientos_judicial
WHERE created_at > '<last_mov>'
  AND (texto_completo ILIKE '%transferencia%'
       OR texto_completo ILIKE '%transfi%'
       OR texto_completo ILIKE '%libr%giro%'
       OR texto_completo ILIKE '%libranza%')
ORDER BY created_at DESC;

-- PJN (mismo pattern)
SELECT id, expediente_id, fecha_movimiento, descripcion, texto_completo
FROM movimientos_pjn
WHERE created_at > '<last_mov>'
  AND (texto_completo ILIKE '%transferencia%'
       OR texto_completo ILIKE '%transfi%'
       OR texto_completo ILIKE '%libr%giro%'
       OR texto_completo ILIKE '%libranza%')
ORDER BY created_at DESC;
```

Procesar igual que pasada A. `fuente='proveido_mev'` o `'proveido_pjn'`, `movimiento_id` = id del movimiento. `wa_message_id` queda NULL.

### Paso 4 — Reglas de clasificación

Para cada giro detectado, decidir destino + despejar números:

| Concepto del texto | Tabla | Campos a poblar |
|---|---|---|
| "honorarios" / "honorarios e IVA" | `giros_honorarios` | `monto_honorarios_neto`, `monto_iva` |
| "reintegro IVA" / "reintegro de IVA" | `giros_honorarios` | `monto_reintegro_iva` (NO suma al tope) |
| "intereses sobre honorarios" | `giros_honorarios` | `monto_intereses_honorarios` |
| "capital" / "crédito laboral" / "no imponible" / "indemnización" | `giros_capital` | `monto_capital` |
| "intereses provenientes de crédito laboral" / "intereses sobre el capital" | `giros_capital` | `monto_intereses_capital` |

**Despeje numérico**:
- Desglose explícito → respetar números del texto.
- "Honorarios e IVA" sin desglose → `hon = total / 1.21`, `iva = total - hon`.
- 100% capital → `monto_capital = monto_total`.
- 100% reintegro IVA → `monto_reintegro_iva = monto_total`.
- Un proveído puede generar 1 fila o 2 (ej. capital al actor + honorarios al letrado en el mismo movimiento).

**Filtros**:
- Si el mensaje es charla, foto omitida, "hay que prestar caución", comentario, etc. → DESCARTAR.
- Mensajes válidos siempre tienen monto + concepto + (carátula o número de expediente).

**Montos en letras**: convertir a número. Ej "PESOS CUARENTA Y OCHO MILLONES..." → `48450996.02`.

**Fecha disponible / mes_imputacion**:
- Buscar "Agendado el: DD/MM/YYYY" o "Fecha de notificación por cédula ... DD/MM/YYYY".
- Si no hay esos marcadores, usar `wa_fecha` o `fecha_movimiento`.
- `mes_imputacion = primer día del mes de la fecha disponible` (YYYY-MM-01).

### Paso 5 — Vincular expediente_id (best-effort)

```sql
UPDATE giros_honorarios gh
SET expediente_id = e.id
FROM expedientes e
WHERE gh.expediente_id IS NULL
  AND gh.expediente_numero IS NOT NULL
  AND (
    REPLACE(e.numero, '/', '') = REPLACE(gh.expediente_numero, '/', '')
    OR e.numero = gh.expediente_numero
  );

-- Idem giros_capital
```

Si queda sin matchear, no es bloqueante — la fila queda con `expediente_id=NULL`.

### Paso 6 — Resumen mensual y semáforo

```sql
SELECT
  to_char(mes_imputacion,'YYYY-MM') AS mes,
  estado,
  COUNT(*) AS cant,
  SUM(monto_honorarios_neto + monto_intereses_honorarios) AS facturable_neto
FROM giros_honorarios
WHERE mes_imputacion >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
GROUP BY mes_imputacion, estado
ORDER BY mes_imputacion DESC, estado;
```

Semáforo del **mes en curso**:
- 🟢 < 70% del tope (< $35M)
- 🟡 70–95% ($35M–$47,5M)
- 🔴 ≥ 95% ($47,5M+) o ya pasado

### Paso 7 — Reporte WhatsApp al grupo "Mati y Noe"

Mandar **únicamente** al grupo "Mati y Noe" (JID `120363026685801986@g.us`) usando `instanceId=inst_29a52ca6`. Acá lo leen Mati y Noe juntos.

**NO mandar nunca**:
- Al individual de Noe (`5491170166033@s.whatsapp.net`) — solo al grupo.
- A la instancia del estudio — ese WhatsApp lo ven todas las empleadas y el contenido es privado.
- Al grupo TRABAJO del estudio (excepto en caso de error caído, sin montos).

Formato:

```
💰 GIROS — [fecha]

📥 Nuevos hoy:
   Honorarios: [N] filas, $[X] netos
   Capital: [M] filas, $[Y]
   Descartados: [K]

📊 MES EN CURSO [YYYY-MM]:
   Facturable neto: $[Z] / $50M  [SEMÁFORO]
   • Disponible: $[A] ([n] filas)
   • Girado: $[B] ([m] filas)
   • Retenido: $[C] ([k] filas)

[Si semáforo 🟡 o 🔴]
⚠️  Sugerencia: retener próximos $[diff] para no pasarte.

📅 Mes anterior cerró en $[prev] facturable.
```

### Paso 8 — Marcar run

Insertar registro en una tabla de runs (crear si no existe) con timestamp, candidatos procesados, filas insertadas, errores. Sirve para el health check.

## Notas operativas

- **NUNCA** usar la instancia del estudio para leer este grupo — ese grupo vive en el WA personal de Mati.
- **NUNCA** mandar mensajes operativos desde la instancia personal — solo el resumen a Mati.
- Si `wa_get_messages` falla (sesión caída), reportar al chat de TRABAJO del estudio (via instancia operativa) que el control de giros necesita re-vinculación de la instancia personal. NO mencionar montos ni detalles — solo "control giros caído, revisar".
- Para back-fill manual desde un archivo de chat exportado: usar `extract_from_chat_txt.py <path.txt>` para emitir candidatos JSON, después procesar y volcar a Supabase como hizo el subagente en el backfill inicial del 2026-05-13.
