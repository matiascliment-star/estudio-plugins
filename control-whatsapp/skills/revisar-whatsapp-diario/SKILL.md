---
name: revisar-whatsapp-diario
description: >
  Corrida diaria automatizada de control de WhatsApp del estudio. Lee desde Supabase
  todos los grupos de cliente con mensajes sin contestar, lee el último día completo
  de cada conversación, los clasifica (urgente / novedades / acción concreta / baja /
  cerrada), manda automáticamente el combo (audio Sofía + texto con portal) a los
  que pidieron novedades genéricas y aún no lo recibieron, registra el envío en
  `wa_audio_enviado` para no duplicar, y genera un reporte estructurado al grupo
  TRABAJO con sub-reportes por chica (Paula, Mara, Eliana, Clara, Noe), bloque
  URGENTES al tope, escalaciones (clientes que recibieron Sofía y volvieron a
  insistir = requieren respuesta humana detallada), bajas detectadas y cruce con
  expedientes para flagear novedades reales. Triggers: "control whatsapp", "revisar
  whatsapp", "control chats", "novedades whatsapp", "briefing whatsapp", "corrida
  whatsapp", "atencion clientes whatsapp". Programado para correr todos los días
  hábiles a las 8:00, 12:00 y 16:00 AR. La corrida de las 8 es modo COMPLETO
  (todos los pendientes); las de 12 y 16 son INCREMENTAL (solo mensajes nuevos
  de las últimas 4 hs, reporte al grupo TRABAJO solo si hay urgentes/Sofía/bajas).
version: 0.2.0
---

# Skill: Control WhatsApp diario

Corrida automatizada de chats pendientes para que las chicas (Paula, Mara, Eliana, Clara, Noe) arranquen el día con la lista priorizada y contesten rápido. Auto-envía el combo de Sofía a los que sólo piden novedades genéricas, deja todo lo demás clasificado para acción humana.

## Decisiones operativas

- **Universo**: solo grupos de cliente (`is_group=true`), excluyendo grupos internos.
- **Pendiente**: último mensaje del grupo viene del cliente (`staff_name IS NULL`).
- **Contexto**: leer TODOS los mensajes del último día de actividad del grupo (no solo el último mensaje), para distinguir cierres genuinos de falsos cierres.
- **Audio Sofía sólo a "novedades genéricas"**: si pide algo concreto (monto, fecha, turno, expediente puntual) → NO mandar audio, va al reporte para respuesta humana.
- **No duplicar audio**: usar `wa_audio_enviado` (UNIQUE chat_id+audio_tipo) como cache.
- **Escalación automática**: cliente que ya recibió `sofia_novedades` y volvió a pedir novedades → 🔴 PRIORIDAD ALTA, requiere respuesta humana con info real del expediente.
- **Detección de bajas**: frases tipo "cambié de abogado", "ya tiene quien lo represente", "arranco con otro boga" → 🚪 BAJA.
- **Cross-check con expediente**: para los que reciben Sofía, intentar matchear nombre del grupo con `expedientes` en Supabase y leer últimos movimientos. Si hay movimiento reciente (≤3 días) → flag "📌 hay novedad real, mejor respuesta humana".

## Recursos clave

**Supabase proyecto**: `wdgdbbcwcrirpnfdmykh`
- Tabla `wa_messages` — mensajes WhatsApp
- Tabla `wa_audio_enviado` — tracking de audios pregrabados (UNIQUE por chat_id+audio_tipo)
- Tabla `wa_chats_cerrado` (PK `chat_id`) — chats cerrados detectados por IA o manual. Frontend filtra "Sin contestar" excluyendo `ultimo_ts_cerrado >= timestamp del último msg`. Reapertura automática si llega mensaje nuevo.
- Tabla `expedientes` — para cross-check de movimientos

**WhatsApp instance**: `inst_d9c22079`
**Grupo TRABAJO JID**: `5491167156098-1395248421@g.us`
**Audio Sofía URL**: `https://wdgdbbcwcrirpnfdmykh.supabase.co/storage/v1/object/public/wa-media/audio/3EB0B6A3610607D8F848AC.ogg`

**Grupos internos a excluir** (no son grupos de cliente):
```
TRABAJO, Lobos de Wall Street (2026), Cédulas y otras notificaciones,
Pericias y sentencias, FIRMÓ 🖋️📰⚖️, BANCO 🏦 (COBROS PRESENCIALES),
Demandas (Registro) Provincia Bs.As., Control Dispos SRT, Claude SRT,
Novedades - VETA CAPITAL, Novedades PJN, Novedades Pcia,
Control exptes/consultas, INICIO - Nuevos formularios 2026, DIARIO LA LEY 🗞️📰⚖️
```

## Modo según hora (LEER PRIMERO)

Determinar la hora actual en AR via Bash:
```bash
HORA=$(TZ=America/Argentina/Buenos_Aires date '+%H')
echo "Hora actual AR: $HORA"
```

- **HORA == 08 → MODO COMPLETO**: ejecutar el workflow tal como está descrito. Procesa todos los grupos pendientes del último día. Reporte completo al grupo TRABAJO con sub-bloques por chica.

- **HORA == 12 o HORA == 16 → MODO INCREMENTAL**: solo procesa grupos con mensajes NUEVOS en las últimas 4 hs escritos por el cliente. El subset se calcula así:
  ```sql
  SELECT DISTINCT m.chat_id, m.chat_name
  FROM wa_messages m
  WHERE m.is_group = true
    AND m.staff_name IS NULL
    AND m.created_at >= NOW() - INTERVAL '4 hours'
    AND m.chat_name NOT IN (<lista internos>);
  ```
  Resto del workflow idéntico (Paso 2 al 6) sobre ese subset.

  **Reporte al TRABAJO en INCREMENTAL**: SOLO si hay 🚨 URGENTE o 🔴 ESCALACIÓN nuevos, O se mandó al menos 1 combo Sofía, O se detectó 🚪 BAJA. Si nada de eso → silencio (Paso 3.5 y 4 igual se ejecutan).

  Formato reporte INCREMENTAL:
  ```
  ⚡ ACTUALIZACIÓN CHATS — [HH:MM]
  (últimas 4 hs)

  🤖 Audio Sofía enviado: [N]
  ✓ Cerradas automáticamente: [N]

  🚨 URGENTES NUEVOS ([N])
  🔴 ESCALACIÓN ([N])
  🚪 BAJAS ([N])
  ```
  Sin sub-bloques por chica en INCREMENTAL.

## Workflow

### Paso 1 — Identificar grupos pendientes

```sql
WITH grupos_cliente AS (
  SELECT DISTINCT chat_id, chat_name FROM wa_messages
  WHERE is_group = true AND chat_name NOT IN (<lista de internos>)
),
ultimo_por_grupo AS (
  SELECT DISTINCT ON (m.chat_id)
    m.chat_id, m.chat_name, m.staff_name, m.created_at::date AS ultima_fecha
  FROM wa_messages m
  JOIN grupos_cliente gc USING (chat_id)
  ORDER BY m.chat_id, m.created_at DESC
)
SELECT chat_id, chat_name, ultima_fecha
FROM ultimo_por_grupo
WHERE staff_name IS NULL;
```

### Paso 2 — Leer contexto completo

Para cada grupo pendiente, traer todos los mensajes de `ultima_fecha`. Esto da el hilo completo del último día de actividad para clasificar bien.

### Paso 3 — Clasificar con LLM

Buckets (mutuamente excluyentes):

| Bucket | Criterio |
|---|---|
| 🚨 URGENTE | Cliente enojado / amenaza irse / "armar quilombo" / "es urgente" / insiste varias veces sin respuesta |
| 🚪 BAJA | "Cambié de abogado", "ya tiene quien lo represente", "arranco con otro boga" |
| ✅ NOVEDADES | Pide estado genérico: "alguna novedad", "como va", "como sigue" — sin pregunta concreta |
| 🟡 ACCIÓN CONCRETA | Pide algo específico (monto, fecha cobro, turno, nro expediente, doc), mandó info, hizo consulta puntual |
| ✓ CERRADA | Cliente cerró con gracias/ok/reaction tras respuesta efectiva del staff |
| ⚫ AMBIGUO | Audio/imagen sin texto, requiere revisión humana |

Si un cliente entra en NOVEDADES y `chat_id` ya está en `wa_audio_enviado` con `audio_tipo='sofia_novedades'` → **reclasificar como 🔴 ESCALACIÓN** (Sofía no le bastó).

### Paso 3.5 — Persistir cierres detectados en `wa_chats_cerrado`

Para cada grupo clasificado como ✓ CERRADA, UPSERT en `wa_chats_cerrado` antes de seguir. El frontend de la app filtra la solapa "WA Grupos / Sin contestar" usando esta tabla: si el último mensaje del grupo tiene `timestamp <= ultimo_ts_cerrado`, no aparece. Si llega un mensaje nuevo del cliente (`timestamp > ultimo_ts_cerrado`), reaparece automáticamente sin DELETE.

```sql
INSERT INTO wa_chats_cerrado (chat_id, ultimo_ts_cerrado, motivo, cerrado_por, updated_at)
VALUES ($1, $2, $3, 'bot_ia', now())
ON CONFLICT (chat_id) DO UPDATE
  SET ultimo_ts_cerrado = EXCLUDED.ultimo_ts_cerrado,
      motivo = EXCLUDED.motivo,
      cerrado_por = 'bot_ia',
      updated_at = now();
```

Donde:
- `chat_id` = JID del grupo cerrado.
- `ultimo_ts_cerrado` = `MAX(timestamp)` de `wa_messages` para ese chat al momento del análisis (BIGINT, no `created_at`).
- `motivo` ≤80 chars (ej. "Cliente agradeció tras turno", "Consulta resuelta, OK del cliente").

Ejecutar todos los UPSERT antes del Paso 4 para que los cierres queden persistidos aunque el resto del workflow falle.

Las conversaciones ✓ CERRADA NO van al sub-reporte por chica — quedan archivadas y se cuentan en el contador "✓ Cerradas automáticamente".

### Paso 4 — Auto-envío del combo a los ✅ NOVEDADES nuevos

Para cada grupo en NOVEDADES que NO esté en `wa_audio_enviado`:

1. `wa_send_audio` con `ptt=true` y la URL del audio Sofía
2. `wa_send_text` con el bloque completo (5 bullets):
```
- Sofía por WhatsApp — asistente virtual que te responde al instante sobre tu expediente, 24 hs: +1 (555) 736-8693
- Portal de clientes — seguimiento de novedades en cualquier momento: portal-clientes.estudiogarciaclimentabogados.com
- Si querés hablar personalmente, atiendo los viernes en el estudio con turno previo:
calendly.com/estudiogarciaclimentabogados/consulta-sobre-el-caso
- Cuando necesites una respuesta humana más detallada, notás un error en el portal o en la atención de Sofía, completá la encuesta en el portal de clientes o escribinos a micaso@estudiogarciaclimentabogados.com.
- Si vos o alguien que conozcas tiene un caso nuevo para consultar, podés escribir al 11 4043-9075 — es la línea de admisión, separada de la atención de causas en curso.
```
3. INSERT en `wa_audio_enviado` con `audio_tipo='sofia_novedades'` y los `audio_msg_id` / `texto_msg_id` retornados.

### Paso 5 — Cross-check con expediente (best-effort)

Para los grupos que recibieron Sofía hoy, opcional: extraer nombre del cliente del título del grupo, hacer ILIKE contra `expedientes.cliente_nombre`. Si hay match con movimiento reciente (`max(movimiento.fecha) >= hoy - 3 días`), agregar al reporte:
```
📌 [Cliente] — Sofía enviada PERO hay novedad real en el expediente del [fecha].
   Conviene mandar mensaje personalizado con info concreta.
```

Si la query falla o no matchea, ignorar silenciosamente — no es bloqueante.

### Paso 6 — Asignar a chica

Para cada grupo pendiente, identificar la última chica que había estado contestando ese chat en los últimos 14 días:
```sql
SELECT DISTINCT ON (chat_id) staff_name
FROM wa_messages
WHERE chat_id = $1 AND staff_name IS NOT NULL
  AND created_at >= NOW() - INTERVAL '14 days'
ORDER BY chat_id, created_at DESC;
```
Si no hay coincidencia → asignar a "Sin asignar".

### Paso 7 — Generar y enviar reportes (solo MODO COMPLETO; en INCREMENTAL ver bloque "Modo según hora")

#### 7a — Reporte general al grupo TRABAJO

Estructura:
```
📋 CONTROL CHATS — [fecha]

🤖 Audio Sofía enviado automáticamente: [N]
✓ Cerradas automáticamente (UPSERT en wa_chats_cerrado): [N]

🚨 URGENTES — RESPONDER YA ([N])
1. [Cliente] (chica que venía contestando) — [resumen ≤40 palabras de qué pasó]
   ...

🔴 ESCALACIÓN — Sofía no les bastó, requieren info concreta del expediente ([N])
- [Cliente] (recibió Sofía el [fecha], hoy volvió a preguntar) — [pregunta actual]
   ...

🚪 BAJAS — Dar de baja del sistema ([N])
- [Cliente] — "[frase]"

🟡 ACCIÓN CONCRETA ([N]) — agrupada por tipo (turno / doc / monto / consulta / relato / etc.)

📌 NOVEDAD REAL DETECTADA ([N]) — Sofía enviada pero hay movimiento reciente del expediente. Conviene mensaje personalizado:
- [Cliente] — [tipo de movimiento] del [fecha]

⚫ AUDIOS/IMÁGENES SIN TEXTO ([N]) — Hay que escuchar/ver
- [Cliente]
```

#### 7b — Sub-reportes por chica (mensaje separado al grupo TRABAJO)

Un mensaje por chica con SUS chats pendientes:
```
👩 PAULA — [N] pendientes
🚨 [urgentes asignados]
🔴 [escalaciones]
🟡 [acciones concretas]
```

Repetir para Mara, Eliana, Clara, Noe. Si una chica tiene 0 pendientes, omitir su sección.

### Paso 8 — Logging

Imprimir en stdout (en cualquier modo):
- Modo (COMPLETO / INCREMENTAL) y hora detectada
- N total grupos procesados
- N audios Sofía enviados
- N cerradas automáticamente (UPSERT en `wa_chats_cerrado`)
- N escalaciones / urgentes / bajas
- N por chica (solo COMPLETO)
- jobIds de los mensajes enviados al TRABAJO (si hubo)

## Triggers manuales

- "control whatsapp"
- "revisar whatsapp"
- "control chats"
- "novedades whatsapp"
- "briefing whatsapp"
- "corrida whatsapp"
- "atencion clientes whatsapp"

## Scheduled trigger

Configurado para correr **lunes a viernes 8:00, 12:00 y 16:00 AR** vía Anthropic remote trigger (id `trig_014d19paikE3KzRpCkQYPsMd`, cron `0 11,15,19 * * 1-5` UTC). El prompt remoto invoca esta skill por nombre y el branching por hora se resuelve adentro de la skill (modo COMPLETO a las 8, INCREMENTAL en las otras dos).

## Edge cases

- **Instancia WA caída**: si `wa_send_*` retorna error de instancia, abortar inmediatamente y mandar alerta al grupo TRABAJO de que el bot no anduvo.
- **Audio URL caída**: verificar al inicio que la URL del audio Sofía responda 200. Si no, alertar y abortar el envío automático (el reporte sí se manda).
- **Grupo nuevo sin clasificar previamente**: tratar como grupo de cliente normal salvo que esté en la lista de internos.
- **Cliente cambió de número**: el `chat_id` cambia, pero el `chat_name` puede ser similar. No es problema mientras el `chat_id` sea distinto al de `wa_audio_enviado`. El audio se mandará una vez para cada `chat_id`.
- **Mensaje del staff sin `staff_name`**: a veces los msj del staff llegan con `staff_name=null` (bug del sincronizador). Para mitigar: si el último mensaje "del cliente" dice cosas tipo "Hola Cliente, soy Mati..." → tratarlo como staff. Detectar con regex / heurística.

## Mejoras futuras (no implementadas todavía)

1. **Audio diferenciado por etapa procesal**: 4-5 audios distintos según etapa del expediente (en pericia / en sentencia / en cámara / ejecución), cross-check con `resumen_ia`.
2. **Recordatorio de turnos automático**: detectar mensajes del staff con turnos médicos sin confirmación 1 día antes → recordatorio al cliente.
3. **Métricas semanales por chica**: tiempo promedio de respuesta, % chats cerrados, sobrecargas.
4. **Honorarios pendientes**: cruce con tabla de pagos para flag clientes que deben honorarios.
5. **Detección de fraude/spam**: clientes nuevos con discurso sospechoso o pedidos extraños.
6. **Auto-respuesta a saludos abiertos**: clientes que solo dicen "Hola buenas tardes" sin pregunta concreta → respuesta tipo "Hola! ¿En qué te podemos ayudar?" automática.
