---
name: vincular-srt-demanda-diaria
description: >
  Corrida diaria (8:55 AR) que detecta casos SRT activos cuya demanda ya
  fue presentada (apareció un expediente MEV/PJN con el mismo cliente y
  ART compatible), los marca como `DEMANDA_PRESENTADA`, copia los datos
  del expediente (carátula, juzgado, jurisdicción, fecha) y los vincula
  vía `expedientes.caso_srt_id`. Lo hace solo cuando hay UN único
  expediente match — si hay ambigüedad (homónimos, multi-accidente) deja
  el caso activo y alerta al grupo "WA Claude SRT". Triggers: "vincular
  SRT demanda", "marcar demanda presentada auto", "promover SRT a
  expediente".
version: 1.0.0
---

# Vincular SRT → Demanda Presentada (auto)

## OBJETIVO

Cerrar el loop entre `casos_srt` (etapa = ACTIVO, ya iniciado en SRT) y
`expedientes` (causa judicial real). Hoy ese pase a `DEMANDA_PRESENTADA`
se hace 100% a mano: cuando aparece la causa en el MEV/PJN, una chica
tiene que entrar al detalle del caso SRT y apretar "📝 Marcar demanda
presentada". Este skill lo hace solo cuando el match es inequívoco.

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **Grupo destino del reporte** "WA Claude SRT":
  chatId `120363407310742955@g.us`
- **Edge function WhatsApp**:
  `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`

## REGLAS DE MATCHING

### Nombre

Normalizar ambos lados (caso SRT y carátula del expediente):

1. Quitar acentos (`Á→A`, `Ñ→N`, etc.).
2. UPPER.
3. Quitar todo lo que no sea letra/dígito/espacio.
4. Colapsar espacios múltiples.
5. La parte cliente de la carátula se extrae del prefijo **antes** del
   primer ` C/ `, ` c/ `, `C/`, `S/`, ` Y OTRO`, ` Y OTROS`. Si no hay
   separador, descartar el expediente (no es accidente típico).

**Match nombre** = el `nombre` normalizado del caso SRT es igual al
cliente normalizado de la carátula, o uno contiene al otro como token
completo (ej. "GOMEZ JUAN" ⊂ "GOMEZ JUAN CARLOS" cuenta como match — el
expediente puede tener un nombre más completo que la carga rápida del
SRT).

### ART

Normalizar ambos lados eliminando estas stopwords:
`ART`, `SA`, `S.A.`, `S.A`, `INTERNATIONAL`, `SEGUROS`, `CIA`, `CÍA`,
`ARGENTINA`, `DE`, `LA`, `EL`, `LAS`, `LOS`. Quitar puntos.

**Match ART** = al menos UN token significativo (≥3 chars) coincide
entre el `art_demandada` del SRT y la parte demandada de la carátula
(extraída entre ` C/ ` y ` S/ `).

Ejemplos:
- SRT `BERKLEY INTERNATIONAL ART SA` → token `BERKLEY`
  Carátula `... C/ BERKLEY ART S.A. S/ACCIDENTE` → token `BERKLEY`
  → ✅ match
- SRT `PROVINCIA` vs carátula `... C/ PROVINCIA ART S.A. S/...`
  → tokens `PROVINCIA` vs `PROVINCIA` → ✅
- SRT `EXPERTA` vs carátula `... C/ ASOCIART...`
  → `EXPERTA` vs `ASOCIART` → ❌
- SRT con `art_demandada IS NULL` o `""` → no se chequea ART, solo nombre.
  Pero loguear en notas que la promoción fue **solo por nombre**.

### Carátula sin "C/" parseable

Si la carátula no tiene patrón cliente C/ demandada (ej. carátula
escrita raro, juicio ejecutivo, etc.) → descartar ese expediente como
candidato, NO promover en base a él.

## WORKFLOW

### Paso 1 — Levantar casos SRT activos elegibles

```sql
SELECT id, nombre, art_demandada, telefono, fecha_firma, fecha_alta,
       wa_chat_id, notas, onedrive_id
FROM casos_srt
WHERE activo = true
  AND etapa = 'ACTIVO'
  AND demanda_presentada_at IS NULL;
```

Si 0 filas → reporte "0 candidatos hoy" y terminar.

### Paso 2 — Levantar expedientes candidatos

```sql
SELECT id, numero, caratula, juzgado, jurisdiccion, fecha_inicio,
       caso_srt_id, onedrive_id
FROM expedientes
WHERE caratula IS NOT NULL
  AND COALESCE(caso_srt_id, 0) = 0;
```

Filtra expedientes que YA están vinculados a otro caso SRT.

### Paso 3 — Match per-caso

Para cada caso SRT del paso 1:

1. Calcular `nombre_norm` del caso (ver "REGLAS DE MATCHING").
2. Por cada expediente del paso 2:
   - Parsear cliente y demandada de la carátula.
   - Si no se puede parsear → siguiente expediente.
   - Si `cliente_norm` matchea con `nombre_norm` (igualdad o uno contenido en el otro como tokens) → candidato del caso.
   - Si caso tiene `art_demandada` no vacío, también validar ART. Si no comparte ningún token significativo → descartar candidato.
3. Resultado por caso:
   - **0 candidatos** → no se promueve. Sigue activo.
   - **1 candidato** → promover (Paso 4).
   - **2+ candidatos** → no se promueve. Alertar (Paso 5).

### Paso 4 — Promover caso SRT a DEMANDA_PRESENTADA

```sql
UPDATE casos_srt
SET etapa = 'DEMANDA_PRESENTADA',
    activo = false,
    demanda_presentada_at = NOW(),
    demanda_caratula = $expediente.caratula,
    demanda_juzgado = $expediente.juzgado,
    demanda_jurisdiccion = $expediente.jurisdiccion,
    demanda_fecha = $expediente.fecha_inicio,
    notas = COALESCE(notas,'') || E'\n\n--- ' || to_char(NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires', 'DD/MM/YYYY')
            || ' Auto-vinculado a expediente #' || $expediente.id || ' (' || $expediente.numero || ')'
            || $solo_nombre_flag || ' ---',
    updated_at = NOW()
WHERE id = $caso.id;

UPDATE expedientes
SET caso_srt_id = $caso.id
WHERE id = $expediente.id;
```

Donde `$solo_nombre_flag` = `' — promovido SOLO por nombre (SRT sin ART)'`
si el caso tenía art_demandada NULL/empty, sino cadena vacía.

NO renombra carpeta OneDrive (eso requiere MSAL desde el front). Las
chicas lo verán en la solapa "Demanda Presentada" y pueden renombrar
manualmente si hace falta.

### Paso 5 — Alertas por ambigüedad

Cuando hay 2+ candidatos, armar fila para el reporte:

```
⚠️ {nombre} (caso SRT #{id}) — {N} expedientes posibles:
   • {num1} — {caratula1[:60]}
   • {num2} — {caratula2[:60]}
   → revisar a mano
```

### Paso 6 — Reporte al grupo "WA Claude SRT"

Solo enviar si `promovidos + ambiguos > 0`. Formato:

```
🔗 *AUTO-VINCULACIÓN SRT → DEMANDA* — DD/MM HH24:MI

✅ Promovidos a Demanda Presentada ({N}):
• NOMBRE (#caso) → exp #expid (numero) — JUZGADO
• ...

⚠️ Ambiguos (revisar a mano, {M}):
• NOMBRE (#caso) — {n_matches} expedientes posibles
• ...
```

Enviar con pg_net:

```sql
SELECT net.http_post(
  url := 'https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send',
  headers := '{"Content-Type": "application/json"}'::jsonb,
  body := jsonb_build_object('chatId', '120363407310742955@g.us', 'text', <reporte>)
);
```

Si `promovidos + ambiguos = 0` → silencio.

### Paso 7 — Output del agente

Reporte breve (≤200 palabras):
- N candidatos evaluados, M promovidos automáticos, K ambiguos.
- IDs de los casos promovidos.
- `request_id` del envío WA (si hubo).

## REGLAS DURAS

- **Solo etapa ACTIVO**: nunca toca POR_INICIAR/TRATAMIENTO/DEMANDA_PRESENTADA/cualquier otro.
- **Solo expedientes sin caso_srt_id**: nunca vincula un expediente que ya tiene caso.
- **1 expediente = 1 caso**: si dos casos SRT matchean al MISMO expediente, ese expediente queda sin asignar y ambos casos van a "ambiguos".
- **Idempotencia natural**: cuando un caso queda en `DEMANDA_PRESENTADA` con `activo=false`, ya no aparece en el filtro del Paso 1.
- **Nunca renombrar OneDrive**: el skill solo toca Supabase. La carpeta la renombra la chica si quiere.
- **Sin LLM**: todo determinístico por regex y normalización. Si hace falta razonar (ambigüedad), se deja para humano.

## EDGE CASES

- **Cliente con homónimo real**: el caso queda en ambiguos. Las chicas vinculan a mano.
- **ART null en SRT pero presente en carátula**: promueve solo por nombre, deja flag en notas.
- **ART distinta pero misma persona** (cambió de ART entre SRT y demanda): no se promueve, alerta en ambiguos. Las chicas evalúan.
- **Expediente con carátula sin "C/"**: descartado como candidato (no es accidente típico).
- **Caso SRT con nombre incompleto** (ej. solo `RAMOS TOBIAS`) y expediente `RAMOS TOBIAS NICOLAS C/ X S/Y`: match porque "RAMOS TOBIAS" está contenido como tokens en el más largo.
