---
name: match-wa-chats
description: >
  Corrida diaria (4:00 AR) que matchea `wa_chat_id` en `casos_srt` y en
  `expedientes` contra los grupos de WhatsApp del estudio (`wa_messages`),
  usando la función `fn_normalize_nombre` (Postgres unaccent + regex) y
  matching POSICIONAL estricto (apellido + nombre, en cualquier orden, con
  token 3 opcional para desambiguar homónimos). TODO en SQL — el agente no
  carga tablas al contexto, sólo cuenta filas y arma el reporte final.
  Idempotente: sólo procesa filas con `wa_chat_id IS NULL`. Reporta por
  WhatsApp al grupo "WA Claude SRT". Triggers: "match wa chats", "matchear
  whatsapp", "corrida wa_chat_id".
version: 2.2.0
---

# Match wa_chat_id en casos_srt + expedientes

## OBJETIVO

Todos los días a las 4:00 AR, completar `wa_chat_id` para todo caso/expediente
activo donde el algoritmo posicional encuentre un único grupo de WhatsApp
matcheado por nombre (token 1 + token 2 = apellido + primer nombre). Reportar
matcheados nuevos + ambiguos por WhatsApp.

## REGLAS DEL MATCHING (POSICIONAL)

- **Token 1** (apellido) + **token 2** (primer nombre) tienen que coincidir
  con los tokens 1 y 2 del `chat_name` (en ese orden, o invertido).
- Si **ambos** lado y grupo tienen **token 3**, también tiene que coincidir
  (protege homónimos: LOPEZ JORGE GASTON ≠ LOPEZ JORGE ANDRES).
- Si más de un grupo cumple → **AMBIGUO**, no actualizar.

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **Función SQL**: `fn_normalize_nombre(text)` ya creada en la DB
  (aplica `unaccent` + uppercase + regex de signos).
- **Tabla casos_srt**: columnas usadas → `id`, `nombre`, `wa_chat_id`,
  `wa_chat_matched_at`, `activo`.
- **Tabla expedientes**: columnas usadas → `id`, `caratula`,
  `caratula_actor_norm` (pre-calculada, ver Paso 0), `wa_chat_id`,
  `wa_chat_matched_at`, `estado`.
- **Tabla wa_messages**: columnas usadas → `chat_id`, `chat_name`,
  `is_group=true`.
- **WhatsApp grupo destino del reporte** "WA Claude SRT":
  chatId `120363407310742955@g.us`.
- **Edge function WhatsApp**:
  `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`.

## WORKFLOW

### Paso 0 — Repoblar `caratula_actor_norm` en expedientes nuevos

Los expedientes recién cargados no tienen la columna `caratula_actor_norm`.
La poblamos antes del match. Es idempotente (sólo toca `IS NULL`).

```sql
UPDATE expedientes
SET caratula_actor_norm = regexp_replace(
  fn_normalize_nombre(
    regexp_replace(
      regexp_replace(
        (regexp_match(caratula, '^(.+?)\s+[Cc]/'))[1],
        '\s+Y\s+OTRO/?A?\s*$', '', 'i'
      ),
      ',', ' ', 'g'
    )
  ),
  '\s+', ' ', 'g'
)
WHERE caratula IS NOT NULL
  AND caratula ~ '\s+[Cc]/'
  AND caratula_actor_norm IS NULL
  AND (estado IS NULL OR estado != '80 Finalizado');
```

### Paso 1A — UPDATE masivo en `casos_srt`

```sql
WITH cn AS (
  SELECT id, nombre,
    split_part(fn_normalize_nombre(nombre), ' ', 1) AS t1,
    split_part(fn_normalize_nombre(nombre), ' ', 2) AS t2,
    split_part(fn_normalize_nombre(nombre), ' ', 3) AS t3
  FROM casos_srt
  WHERE wa_chat_id IS NULL AND nombre IS NOT NULL AND activo = true
    AND array_length(string_to_array(trim(nombre), ' '), 1) >= 2
),
gn AS (
  SELECT DISTINCT chat_id, chat_name,
    split_part(fn_normalize_nombre(chat_name), ' ', 1) AS t1,
    split_part(fn_normalize_nombre(chat_name), ' ', 2) AS t2,
    split_part(fn_normalize_nombre(chat_name), ' ', 3) AS t3
  FROM wa_messages
  WHERE is_group = true AND chat_name IS NOT NULL AND chat_name <> ''
),
m AS (
  SELECT c.id AS caso_id, g.chat_id
  FROM cn c
  JOIN gn g ON ((c.t1 = g.t1 AND c.t2 = g.t2) OR (c.t1 = g.t2 AND c.t2 = g.t1))
  WHERE length(c.t1) >= 3 AND length(c.t2) >= 3
    AND g.chat_id NOT IN (SELECT chat_id FROM wa_chats_excluidos)
    AND (c.t3 = '' OR g.t3 = '' OR c.t3 = g.t3)
),
matches_unicos AS (
  SELECT caso_id, MIN(chat_id) AS chat_id
  FROM m
  GROUP BY caso_id
  HAVING COUNT(DISTINCT chat_id) = 1
)
UPDATE casos_srt c
SET wa_chat_id = mu.chat_id, wa_chat_matched_at = now()
FROM matches_unicos mu
WHERE c.id = mu.caso_id
RETURNING c.id, c.nombre, c.wa_chat_id;
```

Contá filas devueltas = `matcheados_casos`. Si ≤ 30, guardá la lista (nombre +
chat_name del grupo). Si más, sólo el conteo.

### Paso 1B — UPDATE masivo en `expedientes`

Usa `caratula_actor_norm` que ya está pre-calculada — equivale a aplicar
`fn_normalize_nombre` sobre el actor extraído.

```sql
WITH en AS (
  SELECT id, caratula,
    split_part(caratula_actor_norm, ' ', 1) AS t1,
    split_part(caratula_actor_norm, ' ', 2) AS t2,
    split_part(caratula_actor_norm, ' ', 3) AS t3
  FROM expedientes
  WHERE wa_chat_id IS NULL
    AND caratula_actor_norm IS NOT NULL
    AND (estado IS NULL OR estado != '80 Finalizado')
    AND array_length(string_to_array(trim(caratula_actor_norm), ' '), 1) >= 2
),
gn AS (
  SELECT DISTINCT chat_id, chat_name,
    split_part(fn_normalize_nombre(chat_name), ' ', 1) AS t1,
    split_part(fn_normalize_nombre(chat_name), ' ', 2) AS t2,
    split_part(fn_normalize_nombre(chat_name), ' ', 3) AS t3
  FROM wa_messages
  WHERE is_group = true AND chat_name IS NOT NULL AND chat_name <> ''
),
m AS (
  SELECT e.id AS exp_id, g.chat_id
  FROM en e
  JOIN gn g ON ((e.t1 = g.t1 AND e.t2 = g.t2) OR (e.t1 = g.t2 AND e.t2 = g.t1))
  WHERE length(e.t1) >= 3 AND length(e.t2) >= 3
    AND g.chat_id NOT IN (SELECT chat_id FROM wa_chats_excluidos)
    AND (e.t3 = '' OR g.t3 = '' OR e.t3 = g.t3)
),
matches_unicos AS (
  SELECT exp_id, MIN(chat_id) AS chat_id
  FROM m
  GROUP BY exp_id
  HAVING COUNT(DISTINCT chat_id) = 1
)
UPDATE expedientes e
SET wa_chat_id = mu.chat_id, wa_chat_matched_at = now()
FROM matches_unicos mu
WHERE e.id = mu.exp_id
RETURNING e.id, e.caratula, e.wa_chat_id;
```

Contá filas devueltas = `matcheados_expedientes`.

### Paso 1C — Vincular `expedientes.caso_srt_id` por `wa_chat_id` compartido

Cuando un expediente y un caso SRT activo comparten el mismo `wa_chat_id`,
podemos asumir que son del mismo cliente y vincularlos por FK. Sólo
auto-vinculamos si el cliente tiene **un único** caso SRT activo con ese
chat (sin ambigüedad por múltiples accidentes).

Esto alimenta el panel "Cliente 360°" del front sin requerir intervención
manual.

```sql
WITH cs_unicos AS (
  SELECT wa_chat_id, MIN(id) AS caso_id
  FROM casos_srt
  WHERE activo = true AND wa_chat_id IS NOT NULL
  GROUP BY wa_chat_id
  HAVING COUNT(*) = 1
)
UPDATE expedientes e
SET caso_srt_id = cs.caso_id
FROM cs_unicos cs
WHERE e.wa_chat_id = cs.wa_chat_id
  AND e.caso_srt_id IS NULL
  AND (e.estado IS NULL OR e.estado != '80 Finalizado')
RETURNING e.id, e.caratula, e.caso_srt_id;
```

Contá filas devueltas = `vinculados_fk_caso_srt`. Si <= 30 guardá lista
(carátula truncada + caso_srt_id), si más solo el conteo.

**Importante**: no tocar etapas en esta operación. La vinculación de FK
es para vista 360°; las transiciones de etapa las maneja el skill
`seguimiento-tratamiento-llm` u otros flujos.

### Paso 2 — Detectar ambiguos (para el reporte)

Mismo SQL que paso 1A/1B pero terminando con `HAVING COUNT(DISTINCT chat_id) > 1`
en lugar del UPDATE, y `LIMIT 10` por tabla. Esto te lista hasta 10 nombres
que tienen múltiples candidatos para que las chicas resuelvan a mano.

### Paso 3 — Totales actuales

```sql
SELECT
  (SELECT COUNT(*) FILTER (WHERE wa_chat_id IS NOT NULL)
   FROM casos_srt WHERE activo = true)                                AS casos_con_wa,
  (SELECT COUNT(*) FROM casos_srt WHERE activo = true)                AS casos_total,
  (SELECT COUNT(*) FILTER (WHERE wa_chat_id IS NOT NULL)
   FROM expedientes
   WHERE caratula_actor_norm IS NOT NULL
     AND (estado IS NULL OR estado != '80 Finalizado'))               AS exp_con_wa,
  (SELECT COUNT(*) FROM expedientes
   WHERE caratula_actor_norm IS NOT NULL
     AND (estado IS NULL OR estado != '80 Finalizado'))               AS exp_total,
  (SELECT COUNT(*) FILTER (WHERE caso_srt_id IS NOT NULL)
   FROM expedientes
   WHERE (estado IS NULL OR estado != '80 Finalizado'))               AS exp_con_caso_srt;
```

### Paso 4 — Enviar reporte por WhatsApp

Sólo si `matcheados_casos + matcheados_expedientes > 0` o hay ambiguos nuevos.
Si todo dio cero, **silencio total** (no enviar).

Formato del texto:

```
🧩 *MATCH WA_CHAT_ID* — DD/MM/YYYY HH24:MI
📋 casos_srt: matcheados hoy X | total con WA Y/Z | ambiguos N
📁 expedientes: matcheados hoy X | total con WA Y/Z | ambiguos N
🔗 expedientes ↔ caso_srt (FK 360°): vinculados hoy X | total V/W

✅ Matcheados hoy casos_srt (si ≤30):
• NOMBRE → chat_name_grupo
...

✅ Matcheados hoy expedientes (si ≤30):
• ACTOR → chat_name_grupo
...

⚠️ Ambiguos casos_srt:
• NOMBRE (id=X) → candidato1 | candidato2

⚠️ Ambiguos expedientes:
• ACTOR (id=X) → candidato1 | candidato2
```

Enviar con `pg_net`:

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object(
    'chatId', '120363407310742955@g.us',
    'text', <reporte>
  )
);
```

### Paso 5 — Output del agente

Reporte breve (≤200 palabras):

- Matcheados hoy: X casos / Y expedientes
- Con WA totales: A/B casos · C/D expedientes
- Ambiguos: N casos · M expedientes
- `request_id` de pg_net

Sin listas completas en el output del agente (las listas van sólo en el
WhatsApp).

## REGLAS

- Idempotente: nunca toca filas que ya tienen `wa_chat_id`.
- Los matches ambiguos quedan sin actualizar — las chicas los resuelven a
  mano vía el front (o el paso 2 LLM cuando esté implementado).
- Si una corrida no encuentra nada nuevo (matcheados + ambiguos = 0), no
  envía WhatsApp.
- El SQL corre en ~5 segundos sobre todo el dataset. No paralelizar ni
  partir en lotes.
