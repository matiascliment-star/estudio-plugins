---
name: health-check-diario
description: >
  Corrida diaria (8:53 AR) que chequea si todos los skills programados
  corrieron en su frecuencia esperada, además de reportar pendientes
  operativos del estudio (Pre-SRT con alta sin relato, etc.). Lee la
  tabla `health_check_config` para saber qué skills monitorear (cada uno
  con su SQL de "última corrida" y frecuencia en horas). Reporta al
  grupo "WA Claude SRT". Triggers: "health check", "chequear skills",
  "qué corrió hoy", "que falto correr".
version: 1.0.0
---

# Health Check Diario

## OBJETIVO

Detectar antes que las chicas: (a) si algún skill cron no corrió cuando
debía y (b) si hay tareas pendientes que se están acumulando en el
estudio (clientes con alta detectada sin llamar, firmados sin cargar,
etc).

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **Tabla config**: `health_check_config` (PK: `skill`)
- **Grupo destino del reporte** "WA Claude SRT":
  chatId `120363407310742955@g.us`
- **Edge function WhatsApp**:
  `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`

## WORKFLOW

### Paso 1 — Bajar configuración de skills

```sql
SELECT skill, descripcion, ultima_corrida_sql, frecuencia_horas, cron_expression, cuenta
FROM health_check_config
WHERE enabled = true
ORDER BY cuenta NULLS LAST, skill;
```

Si la query devuelve 0 → terminar (no hay nada configurado).

### Paso 2 — Para cada skill, ejecutar su SQL de última corrida

Por cada fila de `health_check_config`, ejecutar `ultima_corrida_sql`.
Devuelve un único timestamp (o NULL). Comparar con
`NOW() - (frecuencia_horas || ' hours')::interval`:

- Si `ultima > NOW() - frecuencia_horas` → ✅ OK
- Si `ultima IS NULL` → ❓ nunca corrió (skip si recién se creó)
- Si `ultima < NOW() - frecuencia_horas` → ⚠️ ATRASADO

Calcular `horas_atraso = EXTRACT(EPOCH FROM (NOW() - ultima))/3600`.

### Paso 3 — Pendientes operativos

Además del health check, reportar contadores útiles para que las chicas
no acumulen trabajo:

```sql
SELECT
  -- Pre-SRT con alta detectada sin relato → hay que llamar
  (SELECT COUNT(*) FROM casos_srt
    WHERE activo = true AND etapa = 'POR_INICIAR' AND fecha_alta IS NOT NULL
      AND relato_hecho = false) AS por_iniciar_sin_relato,

  -- POR_INICIAR con relato hecho pendientes >7d
  (SELECT COUNT(*) FROM casos_srt
    WHERE activo = true AND etapa = 'POR_INICIAR' AND relato_hecho = true
      AND relato_hecho_at < NOW() - INTERVAL '7 days') AS listos_para_srt_atrasados,

  -- TRATAMIENTO sin actividad cliente >14d (recordar que tienen ping diario)
  (SELECT COUNT(*) FROM casos_srt c
    WHERE c.activo = true AND c.etapa = 'TRATAMIENTO' AND c.wa_chat_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM wa_messages w
        WHERE w.chat_id = c.wa_chat_id AND w.is_from_me = false
          AND w.timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '14 days')
      )) AS tratamiento_sin_msg_cliente_14d,

  -- Firmados del chat FIRMÓ sin procesar (rezagados del cron firmados)
  (SELECT COUNT(*) FROM wa_messages w
    WHERE w.chat_id = '120363306095984248@g.us' AND w.type = 'text'
      AND w.content ILIKE '%FIRMÓ%'
      AND NOT EXISTS (SELECT 1 FROM wa_firmo_procesados p WHERE p.message_id = w.id))
    AS firmados_sin_procesar,

  -- Pendientes SRT activos sin caso_srt_id
  (SELECT COUNT(*) FROM causas_pendientes_srt
    WHERE rechazado = false AND caso_srt_id IS NULL) AS pendientes_srt_sin_caso;
```

### Paso 4 — Armar reporte

Plantilla:

```
🩺 *HEALTH CHECK* — DD/MM/YYYY HH24:MI

✅ Skills OK ({N}):
• {skill}: corrió hace {h}h
• ...

⚠️ Skills atrasados ({M}):
• {skill}: hace {h}h sin correr (esperado cada {frec}h) — cuenta {cuenta_o_NULL}
• ...

📋 Pendientes operativos:
• {por_iniciar_sin_relato} con alta detectada → llamar para relato
• {listos_para_srt_atrasados} listos para iniciar en SRT (>7d desde relato)
• {tratamiento_sin_msg_cliente_14d} en tratamiento sin msg del cliente >14d
• {firmados_sin_procesar} mensajes FIRMÓ sin procesar
• {pendientes_srt_sin_caso} pendientes SRT sin caso vinculado
```

Si NO hay skills atrasados Y todos los pendientes están en 0 → enviar
versión corta tipo "Todo OK ✓" pero igual mandar (el silencio total no
sirve acá: el reporte mismo es la garantía de que el health check funciona).

### Paso 5 — Enviar al grupo

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

### Paso 6 — Output del agente

Reporte breve (≤150 palabras):
- Skills OK / atrasados (números).
- Pendientes operativos (números).
- `request_id` del envío WhatsApp.

## REGLAS

- **Siempre enviar** (incluso "todo OK") — el reporte es la prueba de
  que el health check funciona.
- Cada skill se ejecuta de forma aislada: si el SQL de uno tira error,
  ese skill se marca como "❌ Error al chequear" pero los demás siguen.
- Para skills semanales (control-clausuras-srt, frecuencia_horas=168),
  no marcar atrasado si pasó <168h.
- La columna `cuenta` es informativa: ayuda a saber dónde corregir si
  algo falla. No bloquea el chequeo.

## EXTENSIÓN

Para agregar un nuevo skill al monitoreo:

```sql
INSERT INTO health_check_config (skill, descripcion, ultima_corrida_sql, frecuencia_horas, cron_expression, cuenta)
VALUES ('nuevo-skill', 'Descripción corta',
  'SELECT MAX(timestamp_field) FROM tabla_runs',
  24, 'cron expression', 'cuenta_1');
```

El skill `health-check-diario` lo va a chequear automáticamente al
siguiente run.
