---
name: corrida-caducidad-diaria
description: >
  Corrida diaria automatizada de control de caducidad de instancia. Selecciona los
  20 expedientes CABA + 20 Provincia más urgentes, analiza cada uno con un subagente
  (lee movimientos, resumen_ia y reglas procesales), genera borradores DOCX para
  escritos de fórmula, los sube a OneDrive (CABA) y MEV (Pcia), y manda 4 mensajes de
  WhatsApp (uno por chica: Eliana, Mara, Kuki, Paula) + un mensaje resumen a Matías
  con los CRÍTICOS del día. Destinada a correr todos los días hábiles a las 7:00 AR
  para que las empleadas tengan todo listo al llegar a las 8.
  Triggers: "corrida caducidad", "control caducidad diario", "caducidad del día",
  "correr caducidad", "briefing caducidad", "revisar caducidades", "caducidad hoy".
---

# Skill: Corrida diaria de caducidad

## Objetivo

Reemplazar el trabajo manual diario de revisar la lista de caducidad ordenada por días sin movimiento. Todos los días hábiles a las 7:00 AR, el skill:

1. Arma la lista del día (top 20 CABA + top 20 Pcia).
2. Analiza cada expediente leyendo movimientos + resumen IA.
3. Sugiere el escrito de impulso que corresponde.
4. Para escritos **de fórmula** (pronto despacho, intimar pago, pedir audiencia, etc.): genera DOCX con formato del estudio y lo deja como borrador.
5. Para escritos **enjundiosos** (alegatos, recursos, impugnaciones con cálculo): solo sugerencia al WA para que la chica lo redacte.
6. Manda un WhatsApp por chica con su lista, bloque CRÍTICOS al tope, sugerencias y links a borradores.
7. Manda un WhatsApp adicional a Matías con resumen ejecutivo de todos los CRÍTICOS.

## Diferencia CABA vs Provincia — crítico de entender

- **CABA:** caducidad opera **automáticamente** a 6 meses 1ra / 3 meses Cámara. Si se pasa, se pierde la causa. MÁXIMA prioridad.
- **Provincia:** el juzgado intima a activar antes de declarar la caducidad. Los expedientes viejos sin intimación pendiente NO son críticos — solo los que tienen intimación reciente a activar.

Ver detalles en `reglas-procesales.md` (este archivo se inyecta en el prompt de cada subagente).

## Flujo completo

### Fase 1: Selección top 20+20

Supabase project `wdgdbbcwcrirpnfdmykh`. La query calcula `dr = plazo - (hoy - fecha_ref)` donde:
- `fecha_ref = MAX(ultimo_impulso_propio, último movimiento real)`
- `plazo = expedientes.plazo_caducidad` (si está), sino por default: Cámara=90, CABA 1ra=180, resto=90.

```sql
WITH ult_mov AS (
  SELECT expediente_id, MAX(fecha) AS fecha FROM movimientos_pjn GROUP BY expediente_id
  UNION ALL
  SELECT expediente_id, MAX(fecha) AS fecha FROM movimientos_judicial GROUP BY expediente_id
),
agg AS (SELECT expediente_id, MAX(fecha) AS fecha FROM ult_mov GROUP BY expediente_id),
base AS (
  SELECT
    e.id, e.numero, e.caratula, e.jurisdiccion,
    GREATEST(COALESCE(e.ultimo_impulso_propio, '1900-01-01'::date),
             COALESCE(a.fecha, '1900-01-01'::date)) AS fecha_ref,
    COALESCE(e.plazo_caducidad,
      CASE
        WHEN LOWER(COALESCE(e.instancia_actual,'')) IN ('camara','cámara','corte') THEN 90
        WHEN LOWER(COALESCE(e.juzgado,'')) LIKE '%sala %' OR LOWER(COALESCE(e.juzgado,'')) LIKE '%cámara%' THEN 90
        WHEN e.jurisdiccion = 'CABA' THEN 180 ELSE 90
      END) AS plazo,
    e.mev_idc, e.mev_ido, e.link_causa, e.estado, e.instancia_actual, e.resumen_ia,
    e.onedrive_id, e.onedrive_url
  FROM expedientes e
  LEFT JOIN agg a ON a.expediente_id = e.id
  WHERE COALESCE(e.excluido_caducidad, false) = false
    AND COALESCE(e.excluido_caducidad_temporal, false) = false
    AND e.estado IS DISTINCT FROM '80 Finalizado'
    AND e.acumulado_con IS NULL
    AND e.jurisdiccion IN ('CABA','Provincia')
),
ranked AS (
  SELECT *,
    (plazo - (CURRENT_DATE - fecha_ref)) AS dr,
    ROW_NUMBER() OVER (PARTITION BY jurisdiccion ORDER BY (plazo - (CURRENT_DATE - fecha_ref)) ASC, id ASC) AS rn
  FROM base
  WHERE fecha_ref > '1900-01-01'::date
)
SELECT id, numero, caratula, jurisdiccion, estado, instancia_actual,
       fecha_ref, plazo, (CURRENT_DATE - fecha_ref) AS diff_dias, dr,
       mev_idc, mev_ido, link_causa, resumen_ia, onedrive_id, onedrive_url
FROM ranked WHERE rn <= 20 ORDER BY jurisdiccion, rn;
```

**Dedup:** si dos filas tienen el mismo `numero`, quedarse con el primero. Si tras dedup hay <20 en alguna jurisdicción, traer los siguientes con otra query hasta completar.

### Fase 2: Lanzar 40 subagentes en tandas paralelas de 8

Cada subagente Sonnet recibe:
- Metadata del expediente (id, numero, caratula, jurisdiccion, estado, instancia, dr, plazo, fecha_ref).
- Link a PJN o mev_idc/mev_ido según corresponda.
- `resumen_ia` completo.
- El contenido de `reglas-procesales.md` inyectado en el prompt.
- Instrucción de devolver JSON estructurado.

**Prompt template del subagente** (ver `prompt-subagente.md`).

El subagente debe:
1. Leer últimos 15-20 movimientos de Supabase.
2. Si algún movimiento de tipo `FIRMA DESPACHO` tiene descripción ambigua, leer el `texto_documento` del PDF.
3. Aplicar las reglas procesales.
4. Decidir `tipo_impulso` + `urgencia_real` + `critico` (bool).
5. Si el tipo de impulso es "de fórmula" y tiene urgencia alta, generar el DOCX ahí mismo.
6. Devolver JSON con:
   - `contexto`: 2-3 oraciones contándole a la chica **qué pasó** en el expediente (último hito, fecha, por qué está frenado). Sirve para que la empleada entienda la lógica del caso sin leer movimientos.
   - `accion_sugerida`: una frase concreta de **qué hay que pedir** al juzgado.
   - `texto_sugerido`: párrafo tipo escrito judicial para copy-paste (~100-200 palabras).
   - `link_borrador_onedrive` / `link_borrador_mev`: si se generó.
   - `urgencia_real`, `critico`, `tipo_impulso`.

**Tipos de fórmula** (auto-generar DOCX):
- `pronto_despacho`
- `intimar_pago`
- `pedir_audiencia_testimonial`
- `pedir_traslado_amparo`
- `solicitar_autos_sentencia`
- `reiterar_giro`
- `evacuar_vista_perito`

**Tipos no-fórmula** (solo sugerencia):
- `alegar` / `alegato_bien_probado`
- `impugnar_liquidacion`
- `interponer_rex` / `interponer_ri` / `queja`
- `contestar_traslado_sustancial`

### Fase 3: Generación del DOCX

Los subagentes usan `scripts/generar_escrito.py` que:
1. Carga el modelo `modelos/{tipo_impulso}.md` (texto con placeholders).
2. Reemplaza `{{placeholders}}` con datos del caso.
3. Genera DOCX con **formato memoria** (Times 12, interlineado 1.5, márgenes 2/2/3/2, sangría 1.25cm, título en negrita+subrayado).
4. Guarda en `/tmp/caducidad/{fecha}/{numero_safe}_{tipo}.docx`.

### Fase 4: Distribución de borradores

**CABA (PJN no deja editar borradores):**
- Subir DOCX a OneDrive del expediente en carpeta `Borradores caducidad/{fecha}/`.
- Incluir link en el WhatsApp de la chica.
- Enviar el DOCX como adjunto con `wa_send_document` (preview en el celular).
- NO subir al PJN automáticamente.

**Provincia (MEV deja editar borradores):**
- Subir DOCX como borrador editable al MEV con `scripts/upload_mev_borrador.py` (del skill `subir-escrito-mev`).
- Copia en OneDrive del expediente.
- Incluir ambos links en el WA.

### Fase 5: Armado y envío de WhatsApp

**4 mensajes por chica + 1 mensaje ejecutivo a Matías.**

Estructura del mensaje por chica:

```
*CONTROL CADUCIDAD — {CHICA} ({JURISDICCION})*
_Corrida {fecha} · {N} expedientes_

🚨 *CRÍTICOS DEL DÍA* ({M} casos)
{Los críticos van primero, con el mismo detalle que los pendientes}

📋 *PENDIENTES*

*1.* {CARATULA_CORTA} — {NUMERO} · dr={dr}
{EMOJI} {tipo_impulso_legible}

📌 *Qué pasó:* {contexto — 2-3 oraciones explicando la lógica del expediente}

✏️ *Qué hay que pedir:* {accion_sugerida — frase concreta}

📎 Borrador: {link_onedrive | link_mev | "—"}
```

**Regla de oro:** que la chica pueda leer solo el bloque de un expediente y entender sin ambigüedad qué presentar y por qué, sin tener que abrir el expediente para averiguarlo.

Estructura del mensaje ejecutivo a Matías:

```
*RESUMEN EJECUTIVO CADUCIDAD — {fecha}*

🚨 CRÍTICOS: {total}
- Eliana: {n} ({listas muy cortas})
- Mara: {n}
- Kuki: {n}
- Paula: {n}

📝 Borradores generados: {n_caba_onedrive} CABA + {n_pcia_mev} Pcia

📊 Stats:
- CABA con dr < 0: {n}
- Pcia con intimación activar: {n}
- Excluidos del control sugeridos: {n}
```

**Durante fase de prueba, TODOS los WA van al `5491140439075` (Matías)** etiquetados con el nombre de la destinataria esperada. Cuando Matías apruebe la calidad, cambiar a los JIDs reales de cada chica.

### Fase 6: Logueo en Supabase

**Importante:** la tabla NO filtra. El skill toma siempre el top 20 por `dr` real — si un expediente sigue crítico porque nadie lo presentó, vuelve a aparecer mañana con un indicador de "repetido". Esto es a propósito: evita olvidar un crítico por bug de tracking y presiona sanamente a la chica sobre los casos arrastrados. La única salida real de la lista es presentar el escrito (cambia `ultimo_movimiento`) o excluirlo con `excluido_caducidad=true` en la app.

La tabla sirve para:
- Auditoría / métricas.
- Detectar repeticiones: antes de armar el WA, consultar cuántas corridas seguidas aparece cada expediente y agregar indicador al mensaje:
  - 1ra vez: sin indicador.
  - 2da vez seguida: `⚠️ Repetido (2 corridas)`.
  - 3ra+: `🔁 Recordatorio — aparece hace N días, sin presentar todavía`.

Tabla `caducidad_corridas` (crear si no existe):

```sql
CREATE TABLE IF NOT EXISTS caducidad_corridas (
  id BIGSERIAL PRIMARY KEY,
  fecha DATE NOT NULL,
  expediente_id BIGINT REFERENCES expedientes(id),
  responsable_asignada TEXT,  -- Eliana/Mara/Kuki/Paula
  tipo_impulso TEXT,
  urgencia TEXT,  -- alta/media/baja/no_requiere
  critico BOOLEAN DEFAULT FALSE,
  razon TEXT,
  borrador_onedrive_url TEXT,
  borrador_mev_id TEXT,
  presentado BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Cada subagente al finalizar inserta su fila. Así tenemos auditoría completa y podemos medir:
- Cuántos borradores terminan presentados (firmados por las chicas).
- Qué tipos de impulso son más frecuentes.
- Regresiones en la calidad de las sugerencias.

## Destinatarios WhatsApp

Durante prueba → todo al `5491140439075` (Matías).

Para producción (pedir mapeo a Matías cuando apruebe):
```
Eliana → 549XX...
Mara   → 549XX...
Kuki   → 549XX...
Paula  → 549XX...
```

Guardar en `reference_caducidad_asignaciones.md` en memoria.

**Instance WhatsApp activo:** consultar con `SELECT instance_id FROM wa_messages ORDER BY created_at DESC LIMIT 1` (suele rotar). Actualmente `inst_d9c22079`.

## Credenciales

Leer de `/Users/matiaschristiangarciacliment/.env`:
- `PJN_USUARIO`, `PJN_PASSWORD` (para eventual upload MEV, aunque MEV usa credencial distinta — ver skill `subir-escrito-mev`).
- `MSAL_CLIENT_ID`, etc. (para OneDrive — ver skill equivalente existente).

## Schedule

Trigger diario **7:00 AR** (= 10:00 UTC) de **lunes a viernes**. Crear con skill `schedule`.

## Resumen para el agente orquestador (Opus 4.7)

1. Leer `reglas-procesales.md` y cargarlo a memoria local.
2. Ejecutar query de Fase 1, deduplicar, obtener 40 filas.
3. Asignar por orden: top 1-10 CABA a Eliana, 11-20 CABA a Mara, 1-10 Pcia a Kuki, 11-20 Pcia a Paula.
4. Lanzar 40 subagentes en **tandas de 8 paralelos**. Cada subagente devuelve JSON.
5. Consolidar resultados. Identificar CRÍTICOS.
6. Generar 4 mensajes WA + 1 mensaje resumen Matías.
7. Enviar con `mcp__whatsapp__wa_send_text` + `mcp__whatsapp__wa_send_document` si hay adjunto.
8. Insertar filas en `caducidad_corridas`.
9. Reportar al usuario (o al scheduled trigger) el total procesado.

## Tiempo esperado

- Query Supabase: 2 seg
- 40 subagentes en tandas de 8 × ~75 seg promedio = ~6 min
- Generación DOCX + uploads: integrado en cada subagente
- 5 WA envíos paralelos: 5 seg
- **Total: 7-10 min end-to-end.**

Si algún subagente timeout (90 seg), reintentar 1 vez; si falla de nuevo, marcar en `caducidad_corridas.razon = "REVISAR MANUAL: subagente falló"` y seguir.
