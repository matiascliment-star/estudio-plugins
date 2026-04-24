---
name: pedir-mas-caducidad
description: >
  Procesa pedidos on-demand de más casos de caducidad cuando una abogada (o Matías/Noe) pide más
  expedientes para impulsar después de terminar los del día. Lee la cola `pedidos_caducidad_pendientes`
  de Supabase, toma el pedido más viejo en estado `pendiente`, analiza los N expedientes
  que ya seleccionó la edge function `pedir-mas-caducidad`, genera los DOCX de fórmula,
  los sube a OneDrive, y hace UPDATE sobre las filas stub que la edge function dejó
  pre-creadas en `caducidad_corridas`. Al finalizar manda 2 mensajes de WhatsApp: uno a la
  abogada (o a Matías si es Kuki/Paula) con el detalle de los casos pedidos, y un resumen
  ejecutivo a Matías. Disparado por trigger remoto Anthropic con cron horario L-V 8-20hs AR
  (o disparado on-demand desde la edge function cuando se aprieta el botón en la app).
  Triggers: "pedir mas caducidad", "procesar cola caducidad", "pedido on-demand caducidad".
---

# Skill: Pedir más casos de caducidad (on-demand)

## Objetivo

Complementar la corrida diaria `corrida-caducidad-diaria`. Cuando una abogada termina los 10 casos que le tocaron a las 7am y necesita más, desde la app aprieta un botón que:

1. Corre la query de selección (en la edge function Supabase), toma los N siguientes más urgentes de `jurisdiccion` excluyendo los ya asignados hoy, inserta filas **stub** en `caducidad_corridas` con `analisis_pendiente=true`, y encola un pedido en `pedidos_caducidad_pendientes`.
2. Este skill, disparado cada 2 minutos por el scheduled task, consume la cola: analiza los expedientes, genera los DOCX y hace `UPDATE` sobre las filas stub llenando `estado_procesal`, `prueba_producida/pendiente`, `obstaculo_actual`, `estrategia_sugerida`, `accion_inmediata`, `tipo_impulso`, `urgencia`, `borrador_onedrive_url`.
3. Setea `analisis_pendiente=false` en cada fila → la app (que está en polling) renderiza los detalles inmediatamente.
4. Marca el pedido como `completado` en la cola.

La app muestra "⏳ Analizando IA…" mientras `analisis_pendiente=true` y luego renderiza el análisis + el link al borrador cuando pasa a `false`.

## Diferencias con `corrida-caducidad-diaria`

| Aspecto | Corrida 7am | Pedir más |
|---|---|---|
| Disparador | Cron diario 7am L-V | Scheduled cada 2 min L-V 8-20hs + cola |
| Selección de expedientes | La skill hace la query Fase 1 | La edge function ya seleccionó y creó stubs |
| Cantidad | 40 fijos (10 × 4 abogadas) | N variable (1-30, default 10) |
| Inserción en `caducidad_corridas` | `INSERT` | `UPDATE` (filas stub ya existen) |
| WhatsApp | Sí (4 abogadas + resumen a Matías) | Sí (1 abogada destinataria + resumen a Matías) |
| Tandas de subagentes | 4 tandas de 10 paralelos | 1 tanda de N paralelos (máx 30) |
| `numero_corrida` | 1 (o 2 si se corrió manual antes) | `max(hoy)+1` (la edge function lo asigna) |

Todo lo demás (scripts, modelos, reglas procesales, formato DOCX, oficina destino, reglas duras sobre `borrador_onedrive_url`) es **idéntico** — se referencia a `corrida-caducidad-diaria` para evitar duplicación.

## Flujo completo

### Fase 1: Consumir la cola

Supabase project `wdgdbbcwcrirpnfdmykh`. La cola vive en `pedidos_caducidad_pendientes`:

```sql
CREATE TABLE IF NOT EXISTS pedidos_caducidad_pendientes (
  id BIGSERIAL PRIMARY KEY,
  creado_at TIMESTAMPTZ DEFAULT NOW(),
  abogada TEXT NOT NULL,                -- Eliana/Mara/Kuki/Paula
  jurisdiccion TEXT NOT NULL,            -- CABA/Provincia
  n INT NOT NULL,                        -- cantidad pedida (1-30)
  expediente_ids BIGINT[] NOT NULL,      -- IDs ya seleccionados por la edge function
  numero_corrida INT NOT NULL,           -- max(hoy)+1 asignado por la edge function
  estado TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | en_proceso | completado | error
  procesado_at TIMESTAMPTZ,
  error_msg TEXT,
  pedido_por TEXT                        -- opcional: quien apretó el botón (vos/Noe/la abogada)
);
```

**Al iniciar la skill:**

```sql
-- Tomar el pedido pendiente más viejo y marcarlo en proceso
UPDATE pedidos_caducidad_pendientes
SET estado = 'en_proceso', procesado_at = now()
WHERE id = (
  SELECT id FROM pedidos_caducidad_pendientes
  WHERE estado = 'pendiente'
  ORDER BY creado_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING id, abogada, jurisdiccion, n, expediente_ids, numero_corrida;
```

Si no devuelve filas → no hay nada que hacer, terminar reportando "sin pedidos pendientes".

Si devuelve una fila, guardar `pedido_id`, `abogada`, `jurisdiccion`, `n`, `expediente_ids[]`, `numero_corrida`.

### Fase 2: Análisis paralelo (1 tanda de N subagentes)

Traer los datos necesarios de los N expedientes:

```sql
SELECT e.id, e.numero, e.caratula, e.jurisdiccion, e.estado, e.instancia_actual,
       e.mev_idc, e.mev_ido, e.link_causa, e.resumen_ia, e.onedrive_id, e.onedrive_url,
       c.dr, c.fecha
FROM expedientes e
JOIN caducidad_corridas c ON c.expediente_id = e.id AND c.fecha = CURRENT_DATE
WHERE e.id = ANY($expediente_ids)
  AND c.analisis_pendiente = true;
```

Lanzar **N subagentes Opus 4.7 en una sola tanda paralela** (máximo 30 según el tope del formulario). Cada subagente recibe exactamente lo mismo que en `corrida-caducidad-diaria` (Fase 2 de ese skill):

- Metadata del expediente (id, numero, caratula, etc.)
- `resumen_ia`
- Contenido completo de `../corrida-caducidad-diaria/reglas-procesales.md`
- Instrucción de devolver el mismo JSON estructurado

Cada subagente:
1. Lee últimos 30 movimientos de Supabase con `texto_proveido/texto_documento` completo.
2. Aplica el método `f_escrito` vs `f_despacho` para clasificar.
3. Genera el DOCX si corresponde (tipo de fórmula) usando `../corrida-caducidad-diaria/scripts/generar_escrito.py`.
4. Sube el DOCX a OneDrive usando `../corrida-caducidad-diaria/scripts/upload_onedrive.py`.
5. Actualiza `resumen_ia` en `expedientes` (siguiendo el mismo template de `resumir-supabase` — idéntico a la corrida diaria).

### Fase 3: UPDATE (no INSERT) en `caducidad_corridas`

Cada subagente al finalizar hace **UPDATE** sobre su fila stub:

```sql
UPDATE caducidad_corridas
SET tipo_impulso            = $tipo_impulso,
    urgencia                = $urgencia,
    critico                 = $critico,
    accion_sugerida         = $accion_sugerida,
    texto_sugerido          = $texto_sugerido_corto,
    borrador_onedrive_url   = $borrador_onedrive_url,
    -- análisis estructurado
    estado_procesal         = $estado_procesal,
    prueba_producida        = $prueba_producida,
    prueba_pendiente        = $prueba_pendiente,
    obstaculo_actual        = $obstaculo_actual,
    estrategia_sugerida     = $estrategia_sugerida,
    accion_inmediata        = $accion_inmediata,
    -- oficina destino
    numero_expediente_destino = $numero_expediente_destino,
    mev_idc_destino         = $mev_idc_destino,
    mev_ido_destino         = $mev_ido_destino,
    oficina_destino_label   = $oficina_destino_label,
    -- flag de polling
    analisis_pendiente      = false
WHERE fecha = CURRENT_DATE
  AND expediente_id = $expediente_id
  AND analisis_pendiente = true;  -- safety: no pisar una corrida de 7am ya analizada
```

### Fase 4: WhatsApp — abogada destinataria + resumen ejecutivo a Matías

Cuando los N subagentes terminaron, mandar **2 mensajes** (NO mandar mientras se procesa, solo al final):

#### 4.a) WhatsApp a la abogada (1 mensaje, partible)

Usa la **misma tabla de destinatarios y reglas duras** que `corrida-caducidad-diaria` (ver Fase 5 de aquel SKILL.md):

| Destinataria | Número WhatsApp |
|---|---|
| Eliana | `5491155681611` (su celular — directo) |
| Mara | `5491150547137` (su celular — directo) |
| Kuki | `5491140439075` (Matías, con prefijo `*[Para: Kuki]*`) |
| Paula | `5491140439075` (Matías, con prefijo `*[Para: Paula]*`) |

Estructura del mensaje (la abogada del pedido recibe SOLO los N casos del pedido — no los 10 originales del 7am):

```
*PEDIDO EXTRA — {ABOGADA} ({JURISDICCION})*
_Pedido {fecha_HH:MM} · {N} expedientes · pedido por {pedido_por o "ella misma"}_

*1.* {CARATULA_CORTA} — {NUMERO} · dr={dr}
{EMOJI} {tipo_impulso_legible}

📌 *Estado:* {estado_procesal}
🔬 *Prueba producida:* {prueba_producida}
⏳ *Prueba pendiente:* {prueba_pendiente}
🎯 *Obstáculo:* {obstaculo_actual}
🧭 *Estrategia:* {estrategia_sugerida}
✏️ *Hoy:* {accion_inmediata}

📎 Borrador: {link_onedrive | "—"}

*2.* ...
```

**Reglas anti idle-timeout (heredadas de la corrida diaria):**

1. **Nunca escribir helpers Python** — usar las MCP tools `mcp__whatsapp__wa_send_text` directo.
2. **Particionar mensajes >3500 chars** en 2-3 mensajes consecutivos prefijados `[Parte 1/3] PEDIDO EXTRA`, etc.
3. Para la abogada que recibe en su celular (Eliana, Mara): **NO** prefijar con `*[Para: NOMBRE]*`. Para Kuki/Paula que va a Matías: SÍ prefijar.

#### 4.b) Resumen ejecutivo a Matías — SOLO cuando soy el último pedido de mi corrida

⚠️ **REGLA CRÍTICA:** varios pedidos pueden compartir el mismo `numero_corrida` (cuando desde la app se selecciona multi-abogada, ej. "Pedir 5 para Eliana+Mara" crea 2 pedidos con el mismo numero_corrida). En ese caso, Matías debe recibir **UN SOLO resumen ejecutivo consolidado** al final de la corrida — NO uno por pedido.

**Algoritmo del resumen unificado:**

1. Después de marcar mi pedido como `completado`, chequear si quedan otros pedidos del mismo numero_corrida+fecha sin completar:

```sql
SELECT COUNT(*)::INT AS n_pendientes
FROM pedidos_caducidad_pendientes
WHERE numero_corrida = $mi_numero_corrida
  AND DATE(creado_at AT TIME ZONE 'America/Argentina/Buenos_Aires') = CURRENT_DATE
  AND estado NOT IN ('completado','error')
  AND id <> $mi_pedido_id;
```

2. Si `n_pendientes > 0`: **NO mandar** el resumen a Matías. Skippear. Otra routine que procese otro pedido de la misma corrida va a mandarlo cuando sea la última.

3. Si `n_pendientes = 0` (soy la última en terminar): armar el resumen consolidado con info de TODOS los pedidos de esta corrida:

```sql
-- Traer info de todos los pedidos de la corrida
SELECT id, abogada, jurisdiccion, n, expediente_ids, estado, error_msg, pedido_por
FROM pedidos_caducidad_pendientes
WHERE numero_corrida = $numero_corrida
  AND DATE(creado_at AT TIME ZONE 'America/Argentina/Buenos_Aires') = CURRENT_DATE;

-- Traer info de todos los expedientes procesados (para críticos)
SELECT expediente_id, responsable_asignada, tipo_impulso, urgencia, critico,
       estado_procesal, accion_inmediata, borrador_onedrive_url
FROM caducidad_corridas
WHERE fecha = CURRENT_DATE AND numero_corrida = $numero_corrida;
```

Formato del resumen consolidado (va al `5491140439075`):

```
*RESUMEN CORRIDA EXTRA — {fecha_HH:MM} (corrida #{numero_corrida})*
_Pedida por: {pedido_por o "las abogadas"}_

👩‍💼 *Abogadas de la corrida:* {lista, ej: Eliana + Mara}
📋 *Total expedientes:* {total} ({n por abogada, ej: 5+5})
✅ *Procesados OK:* {n_ok}
❌ *Fallaron:* {n_fail}

🚨 *Críticos detectados:* {total_criticos}
- Eliana: {n_criticos_eliana} {(lista corta de carátulas si hay)}
- Mara: {n_criticos_mara} {(lista corta si hay)}
{...otras abogadas que participaron}

📝 *Borradores generados:* {n_con_borrador}/{total}
🔗 *pedido_ids:* {[id1, id2, ...]} · numero_corrida: {numero_corrida}
```

Si solo hay UNA abogada en la corrida (pedido individual clásico), el formato funciona igual — solo aparece esa abogada en la lista.

**Cómo evitar race condition:** los N pedidos de la corrida son procesados en paralelo por N routines. Si dos terminan "al mismo tiempo", ambas ven `n_pendientes=0` al chequear y ambas mandan resumen. Para evitarlo, usar un lock optimista en la query:

```sql
-- Claim el "slot" de mandar el resumen via UPDATE atómico
UPDATE pedidos_caducidad_pendientes
SET estado = 'completado_y_resumido'
WHERE id = $mi_pedido_id
  AND estado = 'completado'
  AND NOT EXISTS (
    SELECT 1 FROM pedidos_caducidad_pendientes
    WHERE numero_corrida = $mi_numero_corrida
      AND DATE(creado_at AT TIME ZONE 'America/Argentina/Buenos_Aires') = CURRENT_DATE
      AND estado NOT IN ('completado','completado_y_resumido','error')
      AND id <> $mi_pedido_id
  )
RETURNING id;
```

Si el UPDATE afecta 0 filas → alguien más ya mandó el resumen, skippeo. Si afecta 1 fila → soy yo el que manda.

Nota: `completado_y_resumido` es un estado nuevo que representa "completado y además mandé el resumen ejecutivo". El CHECK de la tabla `pedidos_caducidad_pendientes` permite este valor — si no está en el CHECK, agregar con ALTER TABLE antes del primer run.

### Fase 5: Marcar el pedido como completado

Cuando los N subagentes terminaron Y los WhatsApp ya salieron:

```sql
UPDATE pedidos_caducidad_pendientes
SET estado = 'completado'
WHERE id = $pedido_id;
```

Si algún subagente falló:

```sql
UPDATE pedidos_caducidad_pendientes
SET estado = 'error',
    error_msg = $resumen_error
WHERE id = $pedido_id;
```

Las filas stub de los que sí anduvieron quedan actualizadas. Las que fallaron permanecen con `analisis_pendiente=true` — el próximo run del cron no las toma (porque el pedido ya no está `pendiente`), así que quedan como "huérfanas" hasta que un humano las atribuya manualmente o las borre.

## Compartido con `corrida-caducidad-diaria`

**Por referencia, no copia:**
- Script Python de generación: `../corrida-caducidad-diaria/scripts/generar_escrito.py`
- Modelos de escritos: `../corrida-caducidad-diaria/modelos/*.md`
- Reglas procesales: `../corrida-caducidad-diaria/reglas-procesales.md`

## Subida a OneDrive — GitHub relay (IDÉNTICO a corrida 7am)

**NO usar el script `upload_onedrive.py` directo** — ese requiere env vars (`SUPABASE_SERVICE_KEY`, `MS_TENANT_ID`, etc.) que el runtime remoto de Anthropic NO tiene configuradas. En la corrida 2026-04-24 esto rompió el upload y los DOCX quedaron en `/tmp` del subagente, se perdieron al terminar la sesión.

**Usar el mismo patrón que `corrida-caducidad-diaria`:**

1. El trigger remoto clona 2 repos: `estudio-plugins` + `caducidad-borradores`.
2. Cada subagente genera el DOCX con `scripts/generar_escrito.py` **guardando en el working copy de `caducidad-borradores`**:
   ```
   caducidad-borradores/YYYY-MM-DD/{tipo}-{APELLIDO}.docx
   ```
3. Al terminar TODOS los subagentes del pedido, el orquestador hace:
   ```bash
   cd caducidad-borradores && git add -A && git commit -m 'Pedir mas caducidad YYYY-MM-DD pedido X' && git push
   ```
   (El clone del trigger remoto viene con credenciales de push para este repo — es un repo dedicado al relay.)
4. Para cada DOCX, llamar la edge function `upload-to-onedrive` vía `pg_net.http_post`:
   ```sql
   SELECT net.http_post(
     url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/upload-to-onedrive',
     headers := '{"Content-Type":"application/json"}'::jsonb,
     body := jsonb_build_object(
       'onedrive_id', '<onedrive_id del expediente>',
       'subpath', 'Borradores caducidad/YYYY-MM-DD/{tipo}-{APELLIDO}.docx',
       'github_path', 'YYYY-MM-DD/{tipo}-{APELLIDO}.docx'
     )
   );
   ```
5. La edge function hace fetch del raw del repo `caducidad-borradores` con el PAT ya configurado en sus secrets, y PUT a Microsoft Graph. Devuelve `webUrl` del SharePoint. Se usa `refresh-microsoft-token` internamente para mantener el token vivo.
6. Polear `net._http_response` por el `id` del request; extraer `webUrl` del body JSON; `UPDATE caducidad_corridas SET borrador_onedrive_url = $webUrl WHERE id = ...`.

**⚠️ NUNCA usar `content_base64` ni curl directo desde el subagente** — ambos caminos fallaron en corridas previas (límite MCP SQL + sandbox allowlist).

**Reglas duras para `borrador_onedrive_url`:**
- Solo URLs https del tenant del estudio (`abogadosgc-my.sharepoint.com/...`). Nunca paths locales (`/tmp/...`).
- Si no hay `onedrive_id` en el expediente: no generar DOCX, dejar `borrador_onedrive_url = NULL` y anotar en `texto_sugerido` "⚠️ Sin carpeta OneDrive para este expediente".
- Si la edge function devuelve error (poll del `net._http_response` con `status_code != 200`): dejar `borrador_onedrive_url = NULL`, anotar en `texto_sugerido` "⚠️ Upload OneDrive falló: {error corto}".
- Oficina destino: igual regla que corrida 7am (default `NULL`, override solo en incidentes / alzadas / conexos).

## Credenciales y entorno

Iguales a la corrida diaria: el runtime de Anthropic ya tiene los MCPs configurados (Supabase, Judicial, OneDrive via env vars del script).

Leer de `/Users/matiaschristiangarciacliment/.env` si corresponde:
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `MS_TENANT_ID`, `MS_CLIENT_ID` (para OneDrive — el script `upload_onedrive.py` los usa)

## Schedule

**Trigger remoto Anthropic** con cron horario L-V (mínimo soportado por triggers Anthropic = 1h):

```
cron: "7 11-23 * * 1-5"   # cada hora 8:07 a 20:07 AR (= 11:07 a 23:07 UTC)
```

**Latencia esperada:** hasta 1h desde que se aprieta el botón hasta que arranca el procesamiento. Promedio ~30 min. Aceptable porque la abogada apenas pide sigue laburando los originales.

**Disparo on-demand (mejor latencia):** la edge function `pedir-mas-caducidad` puede llamar adicionalmente al endpoint `POST /v1/code/triggers/{id}/run` para disparar el trigger inmediatamente después de encolar el pedido. Eso baja la latencia a ~30 segundos. Requiere OAuth token de claude.ai en Supabase secrets — implementación pendiente.

Fuera del horario hábil (noche, fin de semana) el cron no corre — si alguien pide a las 21hs, queda en la cola hasta las 8am del día hábil siguiente.

## Tiempo esperado

- Consumir cola + fetch expedientes: 3 seg
- N subagentes Opus en 1 tanda paralela × ~120 seg = **~2 min**
- UPDATE filas + cerrar pedido: 2 seg
- **Total: 2-3 min end-to-end.**

## Resumen para el agente orquestador (Opus 4.7)

1. Consumir cola con UPDATE + FOR UPDATE SKIP LOCKED. Si no hay pendientes, salir.
2. Traer datos de los N expedientes (los IDs ya vienen en el pedido).
3. Cargar `../corrida-caducidad-diaria/reglas-procesales.md` a memoria local.
4. Lanzar **N subagentes Opus 4.7 en 1 tanda paralela** (N ≤ 30).
5. Cada subagente: analiza, genera DOCX, sube a OneDrive, hace UPDATE en `caducidad_corridas`.
6. Esperar a que terminen todos (con timeout 180 seg por subagente, 1 reintento).
7. **Mandar WhatsApp a la abogada destinataria** (Fase 4.a) — con los N casos analizados, siguiendo tabla de destinatarios. SIEMPRE. Usar MCP tools `mcp__whatsapp__wa_send_text`, NUNCA helpers Python.
8. Marcar pedido como `completado` (o `error` si todos fallaron).
9. **Chequear si soy el último pedido de mi corrida** (Fase 4.b): query a `pedidos_caducidad_pendientes` por `numero_corrida` + fecha. Si hay otros pedidos aún en `pendiente`/`en_proceso`/`completado` (no `completado_y_resumido` ni `error`) → SKIPPEAR el resumen ejecutivo. Si soy la última → armar el resumen **consolidado** con info de TODOS los pedidos de la corrida (puede ser 1 solo si fue pedido individual) y mandarlo a Matías (`5491140439075`). Usar el UPDATE atómico con `NOT EXISTS` para claim el slot sin race.
10. Reportar al scheduled trigger: cantidad procesada + cantidad fallida + si mandé resumen o no.

Si algún subagente timeout, la fila queda con `analisis_pendiente=true` — el orquestador la deja así y lo registra en `error_msg`.

## Idempotencia

Si el cron se dispara dos veces seguidas, `FOR UPDATE SKIP LOCKED` asegura que solo un worker tome cada pedido. Si un worker falla a mitad (ej. crashea), el pedido queda en `en_proceso` sin `estado = completado`. **No hay auto-recovery** — un humano tiene que intervenir. Esto es a propósito para evitar doble-análisis accidental. Si pasa seguido, agregar:

```sql
-- Resetear pedidos colgados >15 min
UPDATE pedidos_caducidad_pendientes
SET estado = 'pendiente', procesado_at = NULL
WHERE estado = 'en_proceso' AND procesado_at < now() - INTERVAL '15 minutes';
```
