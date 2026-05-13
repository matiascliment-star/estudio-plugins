---
name: cargar-firmados-diario
description: >
  Corrida diaria (21:00 AR) que lee los mensajes de las últimas 24 hs del
  grupo de WhatsApp "FIRMÓ 🖋️📈" (chat_id 120363306095984248@g.us), parsea
  los avisos del estilo "*FIRMÓ* (+54...). Apellido Nombre c/ ART. Fecha del
  accidente: dd/mm/yyyy. [SIN ALTA MÉDICA | Con ALTA MÉDICA: ...]" y crea un
  caso en `casos_srt` por cada nuevo cliente firmado, con etapa TRATAMIENTO
  si sigue en tratamiento o POR_INICIAR si ya tiene alta médica. Registra
  cada mensaje procesado en `wa_firmo_procesados` para idempotencia y manda
  un reporte por WhatsApp al grupo "WA Claude SRT". Triggers: "cargar firmados",
  "procesar grupo firmó", "firmados de hoy".
version: 1.0.0
---

# Cargar Firmados Diario

## OBJETIVO

Todos los días a las 21:00 AR, leer los mensajes del grupo de WhatsApp "FIRMÓ
🖋️📈" de las últimas 24 hs, parsearlos, y crear un caso en `casos_srt` por
cada cliente que firmó. Etapa según ALTA MÉDICA. Reporte por WhatsApp.

## DATOS DE REFERENCIA

- **Supabase**: project_id `wdgdbbcwcrirpnfdmykh`
- **Grupo origen** "FIRMÓ 🖋️📈": chat_id `120363306095984248@g.us`
- **Grupo destino del reporte** "WA Claude SRT": chatId `120363407310742955@g.us`
- **Edge function WhatsApp**: `https://wdgdbbcwcrirpnfdmykh.supabase.co/functions/v1/wa-send`
- **Tabla de idempotencia**: `wa_firmo_procesados (message_id PK, caso_srt_id, resultado, motivo, procesado_at)`

## PATRÓN DEL MENSAJE

Variantes que escribe Axel G en el grupo:

```
*FIRMÓ* (+54 9 11 XXXX-XXXX). Apellido Nombre c/ ART. Fecha del accidente: dd/mm/yyyy. Sigue con tratamiento médico. SIN ALTA MÉDICA.
*FIRMÓ* (+54 9 11 XXXX-XXXX). Apellido Nombre c/ ART. Fecha del accidente: dd/mm/yyyy. Con ALTA MÉDICA: dd/mm/yyyy.
*FIRMÓ PRESENCIALMENTE* (+54 9 ...). Apellido Nombre c/ ART. Fecha del accidente: dd/mm/yyyy. Sigue con tratamiento. Sin alta médica.
*FIRMÓ* (+54 9 ...) Apellido Nombre c/ ART. Con alta médica: dd/mm/yyyy
```

Reglas:
- **Si el texto contiene "SIN ALTA MÉDICA" o "sigue con tratamiento" o "sigue en tratamiento" o "sin alta médica" (case-insensitive)** → `etapa = TRATAMIENTO`.
- **Si contiene "Con ALTA MÉDICA" / "con alta médica" / "ALTA MÉDICA:"** → `etapa = POR_INICIAR`.
- Si no se puede decidir, dejarlo en `POR_INICIAR` y dejar comentario en `notas`.

## WORKFLOW

### Paso 1 — Bajar mensajes nuevos de las últimas 26 horas

Damos 2 horas extra de margen para que no se nos escape ningún mensaje si
la corrida del día anterior corrió un poco tarde.

```sql
SELECT m.id, m.content, m.sender_name, m.timestamp,
       to_timestamp(m.timestamp) AT TIME ZONE 'America/Argentina/Buenos_Aires' AS fecha_local
FROM wa_messages m
LEFT JOIN wa_firmo_procesados p ON p.message_id = m.id
WHERE m.chat_id = '120363306095984248@g.us'
  AND m.type = 'text'
  AND m.content ILIKE '%FIRMÓ%'
  AND m.timestamp >= EXTRACT(EPOCH FROM NOW() - INTERVAL '26 hours')
  AND p.message_id IS NULL
ORDER BY m.timestamp ASC;
```

Si no hay filas → reporte "0 firmados hoy" y terminar.

### Paso 2 — Por cada mensaje, parsear con tu propio razonamiento

NO uses regex frágiles. Vos sos el LLM — leé el texto del mensaje y extraé:

- `nombre` (UPPER, sin coma): "Basaldua Balmori, María Librada" → `BASALDUA BALMORI MARIA LIBRADA`
- `art_demandada` (UPPER, sin punto final): "Berkley International A.R.T. S.A." → `BERKLEY INTERNATIONAL ART SA`
- `telefono` (formato libre tal como aparece): `+54 9 11 2049-8939`
- `fecha_accidente` (DATE o NULL): parsear `Fecha del accidente: 13/04/2026` → `'2026-04-13'`. Si no figura → NULL.
- `etapa` (`TRATAMIENTO` | `POR_INICIAR`): según la regla de ALTA MÉDICA.
- `lesion` (texto libre o NULL): si menciona patología explícita ("fractura de tobillo", "operado de rodilla"). Si no menciona → NULL.
- `observaciones` (texto libre o NULL): comentarios que valen la pena
  guardar ("TIENE UN BUEN SUELDO", "fue operado", "pidió documentación"). NULL si nada relevante.
- `firmado_por` = `sender_name` del mensaje
- `fecha_firma` = `fecha_local::date` del mensaje

Si el mensaje no se puede parsear (formato roto, falta nombre o ART), registrá
en `wa_firmo_procesados` con `resultado='no_parseable'` y `motivo='<razón>'` y seguí.

### Paso 3 — Chequear duplicado contra casos existentes

```sql
SELECT id, nombre, art_demandada, etapa, activo
FROM casos_srt
WHERE UPPER(REGEXP_REPLACE(nombre, '[^A-Za-z0-9 ]', '', 'g'))
    = UPPER(REGEXP_REPLACE($1, '[^A-Za-z0-9 ]', '', 'g'))
  AND activo = true
LIMIT 1;
```

Si hay match → `resultado='duplicado'`, `caso_srt_id=<id existente>`, motivo
con el nombre. NO crear nada nuevo.

### Paso 4 — Crear el caso

⚠️ **REGLA DURA**: `clasificacion_pre_srt` se setea SIEMPRE a `'PENDIENTE_CONTACTO'`
cuando `etapa = 'POR_INICIAR'`. Motivo: independientemente de si el cliente
firmó con alta médica o sin secuelas, siempre hay que llamarlo para tomarle
los datos del relato antes de iniciar el SRT. El skill NO debe inferir otras
clasificaciones (LISTA_SIN_SECUELAS, CON_PROBLEMAS, RECHAZO_PARA_INICIAR, etc.)
desde el mensaje de firmados — esas decisiones las toman las chicas después
de la llamada y se ajustan a mano en la solapa Pre-SRT.

Para `etapa = 'TRATAMIENTO'` dejar `clasificacion_pre_srt = NULL` (el seguimiento
LLM lo va a promover a POR_INICIAR + PENDIENTE_CONTACTO cuando detecte alta).

```sql
INSERT INTO casos_srt (
  nombre, art_demandada, etapa, estado, fecha_accidente,
  telefono, fecha_firma, firmado_por,
  lesion, notas, origen, activo, auto_creado,
  clasificacion_pre_srt,
  created_at, updated_at
)
VALUES (
  $1, $2, $3, 'INICIADO', $4,
  $5, $6, $7,
  $8,
  $9,   -- notas: incluir mensaje original completo
  'FIRMÓ_GRUPO_WA',
  true,
  true,
  CASE WHEN $3 = 'POR_INICIAR' THEN 'PENDIENTE_CONTACTO' ELSE NULL END,
  NOW(),
  NOW()
)
RETURNING id;
```

Donde `notas` arma así:
```
{observaciones si hay}

Mensaje original ({fecha_firma}):
{content tal cual}
```

### Paso 5 — Registrar en wa_firmo_procesados

```sql
INSERT INTO wa_firmo_procesados (message_id, caso_srt_id, resultado, motivo)
VALUES ($1, $2, 'creado', NULL);
```

Para `duplicado` o `no_parseable` también registrar (con `caso_srt_id=NULL` y motivo descriptivo).

### Paso 6 — Reporte por WhatsApp

Armar texto con este formato:

```
🖋️ *FIRMADOS HOY* — DD/MM/YYYY
Creados: X | Duplicados: Y | No parseables: Z

✅ Nuevos casos:
• NOMBRE — ART — TRATAMIENTO/POR_INICIAR (firmado por Axel G)
...

⚠️ Duplicados (ya existían):
• NOMBRE → caso #ID
...

❌ No parseables (revisar):
• <preview del mensaje truncado a 80 chars>
...
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

Si `creados + duplicados + no_parseables = 0`, no mandar reporte (silencio).

### Paso 7 — Output del agente

Reporte breve (≤200 palabras): cantidad creados, duplicados, no parseables, IDs
nuevos, `request_id` de pg_net.

## REGLAS

- Idempotencia: nunca procesar dos veces el mismo `message_id`.
- Si el parseo de un mensaje falla, registrar `no_parseable` y seguir con los otros — nunca abortar la corrida entera.
- `art_demandada` se guarda en UPPER y sin punto final, para que matchee bien.
- Si el caso queda con `fecha_accidente=NULL`, dejar nota en `observaciones` para que las chicas la completen.
- Solo casos con `etapa IN ('TRATAMIENTO', 'POR_INICIAR')` (la solapa Pre-SRT del front filtra por esa etapa).
- `clasificacion_pre_srt`: SIEMPRE `'PENDIENTE_CONTACTO'` para POR_INICIAR, NULL para TRATAMIENTO. Nunca inferir otras clasificaciones desde el mensaje — las chicas las ajustan a mano después de la llamada.
