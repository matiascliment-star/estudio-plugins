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
  y manda resumen del mes con semáforo Confirmado/Proyectado vs tope 50M
  al grupo "Mati y Noe". Triggers: "giros diario", "control giros",
  "revisar giros", "corrida giros", "facturación mes", "tope 50M",
  "novedades giros". Programado L-V 18:30 AR (después de control-liquidacion).
version: 0.2.0
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
- **Grupo destino del resumen**: "Mati y Noe" → JID `120363026685801986@g.us` (instancia personal).
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

```sql
SELECT id, expediente_id, fecha_movimiento, descripcion, texto_completo
FROM movimientos_judicial
WHERE created_at > '<last_mov>'
  AND (texto_completo ILIKE '%transferencia%' OR texto_completo ILIKE '%libranza%'
       OR texto_completo ILIKE '%transfi%'    OR texto_completo ILIKE '%libr%giro%');

SELECT id, expediente_id, fecha_movimiento, descripcion, texto_completo
FROM movimientos_pjn
WHERE created_at > '<last_mov>'
  AND (texto_completo ILIKE '%transferencia%' OR texto_completo ILIKE '%libranza%'
       OR texto_completo ILIKE '%transfi%'    OR texto_completo ILIKE '%libr%giro%');
```

Procesar igual que pasada A. `fuente='proveido_mev'`/`'proveido_pjn'`, `movimiento_id`=id del mov.

### Paso 4 — Pasada C: mails Banco Ciudad (Hotmail)

**4a. Refresh access_token si vencido**

```sql
SELECT account_email, client_id, refresh_token, access_token, expires_at
FROM microsoft_oauth_mati
WHERE account_email='flirteador@hotmail.com';
```

Si `expires_at < NOW() + INTERVAL '2 min'`, refrescar:

```bash
curl -X POST "https://login.microsoftonline.com/common/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=0cb7d80d-72b7-41a8-b71e-c8fc68d9a986" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=<refresh_token>" \
  -d "scope=https://graph.microsoft.com/Mail.Read offline_access User.Read"
```

Update DB con nuevo `access_token`, `refresh_token` (Microsoft rota) y `expires_at = NOW() + (expires_in segundos)`.

**4b. Listar mails nuevos del banco**

```bash
curl -s "https://graph.microsoft.com/v1.0/me/messages?\$search=%22Aviso%20-%20%C3%9Altimos%20movimientos%22&\$top=20&\$select=id,subject,receivedDateTime" \
  -H "Authorization: Bearer <access_token>"
```

Filtrar `receivedDateTime > last_banco`.

**4c. Leer body de cada mail nuevo**

```bash
curl -s "https://graph.microsoft.com/v1.0/me/messages/<id>" \
  -H "Authorization: Bearer <access_token>" \
  -H 'Prefer: outlook.body-content-type="text"'
```

El body viene en texto plano. Formato típico:
```
Te informamos los movimientos al DD/MM de tu cuenta CA $ 000000260200356738
FECHA   DETALLE                                  IMPORTE
13/05   DEP JUDI - DEPOSITO JUDICIAL    $ 13.119.626,82 [arriba]
13/05   COMPRA PEDIDOSYA*PROPINA - CABA $ 750,00 [abajo]
```

`[arriba]` = crédito (entró plata), `[abajo]` = débito.

**4d. Parsear líneas (vos, el LLM)**

Para cada línea con formato `DD/MM   DETALLE   $ MONTO [arriba|abajo]`, extraer:
- `fecha` = DD/MM convertido a YYYY-MM-DD usando el año del mail.
- `detalle` = el texto del medio (trim).
- `importe` = monto numérico (sacar puntos miles, coma decimal).
- `signo` = `credito` si `[arriba]`, `debito` si `[abajo]`.

**4e. Upsert en `movimientos_banco`**

```sql
INSERT INTO movimientos_banco
  (banco, fecha, detalle, importe, signo, cuenta, email_message_id, email_fecha)
VALUES ('ciudad', ..., ..., ..., ..., ..., '<msg_id>', '<receivedDateTime>')
ON CONFLICT (email_message_id, fecha, importe, detalle) DO NOTHING;
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

```sql
UPDATE giros_honorarios gh
SET expediente_id = e.id
FROM expedientes e
WHERE gh.expediente_id IS NULL AND gh.expediente_numero IS NOT NULL
  AND (REPLACE(e.numero, '/', '') = REPLACE(gh.expediente_numero, '/', '')
       OR e.numero = gh.expediente_numero);

UPDATE giros_capital gc SET expediente_id = e.id FROM expedientes e
WHERE gc.expediente_id IS NULL AND gc.expediente_numero IS NOT NULL
  AND (REPLACE(e.numero, '/', '') = REPLACE(gc.expediente_numero, '/', '')
       OR e.numero = gc.expediente_numero);
```

Si queda sin matchear, no es bloqueante.

### Paso 7 — Match banco ↔ giros (autoset `fecha_girado`)

Para cada `movimientos_banco` con `signo='credito'`, `match_estado='sin_match'`, detalle LIKE `%DEP JUDI%` o `%DEPOSITO JUDICIAL%`:

```sql
SELECT id, expediente_numero, monto_total, monto_honorarios_neto, neto_esperado_caba
FROM giros_honorarios_match
WHERE estado='pendiente'
  AND jurisdiccion='caba'
  AND ABS(neto_esperado_caba - <importe_banco>) <= 5
  AND fecha_proyectada_cobro BETWEEN <fecha_banco> - INTERVAL '15 days' AND <fecha_banco> + INTERVAL '15 days';
```

**Decisión**:
- **0 matches** → `match_estado='sin_match'`, dejar `notas='Depósito DEP JUDI sin giro pendiente que matchee'`. Sospechoso: revisar manual.
- **1 match** →
  ```sql
  UPDATE giros_honorarios SET fecha_girado=<fecha_banco>, estado='girado' WHERE id=<match_id>;
  UPDATE movimientos_banco SET giro_honorario_id=<match_id>, match_estado='match_unico' WHERE id=<mov_id>;
  ```
  El trigger SQL recalcula `mes_imputacion` automáticamente.
- **2+ matches** → guardar candidatos en `match_candidatos` JSONB:
  ```sql
  UPDATE movimientos_banco
  SET match_estado='match_multiple',
      match_candidatos='[{"giro_id":X,"neto":Y,"diff":Z},...]'::jsonb
  WHERE id=<mov_id>;
  ```
  Mati resuelve en la app `giros-app`.

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

### Paso 9 — Reporte WhatsApp al grupo "Mati y Noe"

Mandar **solo** al grupo "Mati y Noe" (JID `120363026685801986@g.us`) usando `instanceId=inst_29a52ca6`.

**NO mandar**:
- Al individual de Noe.
- A la instancia del estudio (la ven las empleadas).
- Al grupo TRABAJO (salvo error caído, sin montos).

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

- **NUNCA** usar la instancia del estudio para leer el grupo de giros.
- **NUNCA** mandar mensajes operativos desde la instancia personal — solo el resumen al grupo "Mati y Noe".
- Si `wa_get_messages` falla, reportar al grupo TRABAJO sin montos: "control giros caído, revisar".
- Si Microsoft Graph devuelve 401 incluso tras refresh: el refresh_token caducó (Mati tiene que reconectar Hotmail en la giros-app). Reportar a TRABAJO sin detalles.
- **Back-fill** manual del chat exportado: usar `extract_from_chat_txt.py <path.txt>` para emitir candidatos JSON, después procesar como Pasada A (backfill inicial se hizo 2026-05-13 con 199 filas).
- El **modelo de consentimiento** está implementado a partir de 2026-05-15: `fecha_orden` (cuando ordenan), `fecha_proyectada_cobro` (calculada), `fecha_girado` (cuando entra). `mes_imputacion` se basa en `fecha_girado` si está, sino en `fecha_proyectada_cobro`. Los 199 históricos fueron re-imputados.
