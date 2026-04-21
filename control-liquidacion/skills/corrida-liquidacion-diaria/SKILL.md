---
name: corrida-liquidacion-diaria
description: >
  Corrida diaria automatizada de control de ejecución de sentencia (estados 70 a 76).
  Selecciona los 3 expedientes más urgentes por sub-estado en CABA (= 21) + top de
  Provincia, analiza cada uno con un subagente (lee movimientos, resumen_ia, monto
  pendiente y reglas de ejecución), genera borradores DOCX para escritos de fórmula,
  los sube a OneDrive (CABA) y MEV (Pcia), y manda mensajes de WhatsApp por chica +
  un resumen ejecutivo a Matías con los CRÍTICOS del día. Destinada a correr todos
  los días hábiles a las 7:30 AR (después de la corrida de caducidad).
  Triggers: "corrida liquidación", "control liquidación diario", "liquidación del día",
  "correr liquidación", "briefing liquidación", "revisar ejecuciones", "liquidación hoy",
  "corrida ejecución", "ejecución del día".
---

# Skill: Corrida diaria de liquidación (ejecución de sentencia)

## Objetivo

Espejar la corrida de caducidad pero para los expedientes en **etapa de ejecución
de sentencia** (estados 70 a 76). Cada día hábil a las 7:30 AR el skill:

1. Arma la lista del día: 3 más urgentes por cada sub-estado en CABA (= 21) + top
   5–7 de Provincia.
2. Analiza cada expediente leyendo movimientos + `resumen_ia` + reglas de ejecución.
3. Sugiere la acción de impulso que corresponde (practicar liquidación, intimar
   depósito, pedir embargo, reiterar giro, pedir regulación, etc.).
4. Para escritos **de fórmula** (pronto despacho de aprobación, intimar pago,
   reiterar giro, pedir regulación, etc.): genera DOCX con formato del estudio
   y lo deja como borrador.
5. Para escritos **enjundiosos** (practicar liquidación, liquidar intereses,
   impugnar liquidación contraria): solo sugerencia + invocación al skill
   correspondiente (`practicar-liquidacion`, `actualizar-liquidacion`,
   `controlar-liquidacion`).
6. Manda WhatsApp por chica + un mensaje resumen a Matías con los CRÍTICOS.
7. Persiste cada decisión en `liquidacion_corridas` (alimenta la solapa
   "Liquidación IA" del frontend).

## Universo

`expedientes` con `estado` cuyo prefijo de 2 dígitos esté entre **70 y 76**:

| Cód. | Sub-estado |
|------|------------|
| 70 | Practicar liquidación |
| 71 | Liquidación practicada |
| 72 | Pedimos embargo |
| 73 | Se ordenó giro actor |
| 74 | Se ordenó giro nuestro |
| 75 | Intereses |
| 76 | Regulación honorarios |

Excluidos: `77` (Conciliado), `80–84` (Finalizados), `90+` (Especiales).

## Diferencia conceptual con Caducidad

- En Caducidad la urgencia es **plazo legal** (perder la causa por inactividad
  procesal).
- En Liquidación la urgencia es **plata sobre la mesa** que no estamos
  cobrando: liquidación sin practicar, sentencia sin aprobar, depósito sin
  retirar, intereses sin reclamar, regulación sin pedir.
- No hay caducidad de instancia en ejecución — pero hay **prescripción del
  ejecutado** y, sobre todo, oportunidad económica que se erosiona con la
  inflación.

## Flujo completo

### Fase 1: Selección de candidatos

Supabase project `wdgdbbcwcrirpnfdmykh`.

**CABA — 3 por sub-estado, ordenados por días sin empuje DESC:**

Regla de validez del click (paridad con Caducidad):
- Click con `escrito_id` vinculado → cuenta como impulso válido siempre.
- Click sin `escrito_id` dentro de los últimos 15 días → cuenta (grace period).
- Click sin `escrito_id` con > 15 días → **se ignora** (el expediente vuelve al radar).

```sql
WITH ult_mov AS (
  SELECT expediente_id, MAX(fecha) AS fecha FROM movimientos_pjn GROUP BY expediente_id
  UNION ALL
  SELECT expediente_id, MAX(fecha) AS fecha FROM movimientos_judicial GROUP BY expediente_id
),
agg_mov AS (SELECT expediente_id, MAX(fecha) AS fecha_mov FROM ult_mov GROUP BY expediente_id),
ult_imp AS (
  SELECT expediente_id, MAX(fecha_click) AS fecha_imp
  FROM impulsos_caducidad
  WHERE escrito_id IS NOT NULL
     OR fecha_click >= (CURRENT_DATE - INTERVAL '15 days')
  GROUP BY expediente_id
),
ult_esc AS (
  SELECT expediente_id, MAX(fecha) AS fecha_esc
  FROM escritos_expediente
  GROUP BY expediente_id
),
base AS (
  SELECT
    e.id, e.numero, e.caratula, e.jurisdiccion, e.estado,
    LEFT(e.estado, 2) AS sub_estado,
    e.mev_idc, e.mev_ido, e.link_causa, e.resumen_ia,
    e.onedrive_id, e.onedrive_url,
    e.monto_pendiente_actor, e.monto_pendiente_honorarios, e.monto_capital_sentencia, e.moneda,
    GREATEST(
      COALESCE(am.fecha_mov, '1900-01-01'::date),
      COALESCE(ui.fecha_imp, '1900-01-01'::date),
      COALESCE(ue.fecha_esc, '1900-01-01'::date)
    ) AS fecha_ref
  FROM expedientes e
  LEFT JOIN agg_mov am ON am.expediente_id = e.id
  LEFT JOIN ult_imp ui ON ui.expediente_id = e.id
  LEFT JOIN ult_esc ue ON ue.expediente_id = e.id
  WHERE LEFT(e.estado, 2) IN ('70','71','72','73','74','75','76')
    AND e.acumulado_con IS NULL
    AND e.jurisdiccion IN ('CABA','Provincia')
),
ranked AS (
  SELECT *,
    (CURRENT_DATE - fecha_ref) AS dias_sin_empuje,
    ROW_NUMBER() OVER (
      PARTITION BY jurisdiccion, sub_estado
      ORDER BY (CURRENT_DATE - fecha_ref) DESC, id ASC
    ) AS rn
  FROM base
)
SELECT id, numero, caratula, jurisdiccion, estado, sub_estado,
       fecha_ref, dias_sin_empuje,
       mev_idc, mev_ido, link_causa, resumen_ia, onedrive_id, onedrive_url,
       monto_pendiente_actor, monto_pendiente_honorarios, monto_capital_sentencia, moneda
FROM ranked
WHERE (jurisdiccion = 'CABA' AND rn <= 3)
   OR (jurisdiccion = 'Provincia' AND rn <= 2)
ORDER BY jurisdiccion, sub_estado, rn;
```

**Provincia** tiene tan pocos expedientes en 7X (~26) que con `rn <= 2` por
sub-estado alcanza para cubrir todos en pocos días de rotación. Si en algún
sub-estado no hay candidatos, se omite (no se rellena con otro sub-estado).

**Dedup**: si un expediente cae en dos sub-estados (no debería), priorizar el
sub-estado más avanzado.

### Fase 2: Asignación de responsables

La liquidación la hacen **solo Matías y Noe** (a diferencia de Caducidad que
reparte entre Eliana, Mara, Kuki, Paula). Split: **Matías (10) + Noe (11)**
del total de ~21 CABA.

**Asignación por sub-estado:**

- **Matías** (cálculos fuertes + honorarios propios) — **10 expedientes**:
  - Todo 70 Practicar liquidación (3)
  - Todo 75 Intereses (3)
  - Todo 76 Regulación honorarios (3)
  - 1 del sub-estado 71 (el más urgente) — para llegar a 10

- **Noe** (seguimiento operativo) — **11 expedientes**:
  - 2 restantes de 71 Liquidación practicada
  - Todo 72 Pedimos embargo (3)
  - Todo 73 Giro actor ordenado (3)
  - Todo 74 Giro nuestro ordenado (3)

**Provincia**: mismo criterio semántico (70/75/76 → Matías; 71/72/73/74 → Noe).

**Teléfonos WhatsApp** (producción):
- Matías → `16393940416`
- Noe → `5491131586965`

Durante prueba todos los WA van a Matías etiquetados con el nombre de la
destinataria esperada. Cuando Matías apruebe, usar los JIDs reales arriba.

### Fase 3: Lanzar subagentes en tandas paralelas de 8

Cada subagente Sonnet recibe:

- Metadata: id, numero, caratula, jurisdiccion, estado, sub_estado, dias_sin_empuje, fecha_ref.
- Link a PJN o mev_idc/mev_ido según corresponda.
- `resumen_ia` completo.
- Snapshots de `monto_pendiente_cobro` y `monto_capital_sentencia` (si están).
- El contenido de `reglas-ejecucion.md` inyectado en el prompt.
- Instrucción de devolver JSON estructurado.

El subagente debe:

1. Leer últimos 10–15 movimientos de Supabase.
2. Si algún movimiento de tipo `FIRMA DESPACHO` tiene descripción ambigua, leer
   el `texto_documento` del PDF correspondiente.
3. Aplicar las reglas de ejecución (`reglas-ejecucion.md`).
4. Decidir `tipo_accion` + `urgencia` + `critico` (bool).
5. Si el tipo es "de fórmula" y la urgencia es alta, generar el DOCX con
   `scripts/generar_escrito.py`.
6. Devolver JSON con:
   - `estado_procesal`: una frase describiendo en qué estado real está el expediente.
   - `pagos_recibidos`: array de pagos efectivizados (snapshot del histórico).
   - `pagos_pendientes`: array de giros ordenados sin retirar / saldos.
   - `obstaculo_actual`: cuál es el bloqueo (ej "demandada no depositó", "perito no aceptó", "TOA pendiente", etc.).
   - `estrategia_sugerida`: array de 1-3 pasos a corto plazo.
   - `accion_inmediata`: una frase concreta de qué hacer hoy.
   - `tipo_accion`: ver tabla más abajo.
   - `urgencia`: `critico` | `alto` | `medio` | `bajo`.
   - `critico`: bool.
   - `texto_sugerido`: párrafo tipo escrito (~100-200 palabras) si aplica.
   - `borrador_onedrive_url` / `borrador_mev_id`: si se generó DOCX.
   - `monto_pendiente_cobro` (re-extraído del resumen si está más actualizado).
   - `numero_expediente_destino`, `mev_idc_destino`, `mev_ido_destino`,
     `oficina_destino_label`: por si la presentación va a otro expediente
     (ej. incidente).

### Tipos de acción

**De fórmula** (auto-generar DOCX):

| `tipo_accion` | Sub-estado típico | Modelo |
|---------------|-------------------|--------|
| `pronto_despacho_aprobacion` | 71 | `pronto-despacho-aprobacion.md` |
| `intimar_pago_deposito`      | 71 | `intimar-pago-deposito.md` |
| `pedir_embargo`              | 71/72 | `pedir-embargo.md` |
| `reiterar_giro`              | 73/74 | `reiterar-giro.md` |
| `pedir_regulacion_honorarios`| 76 | `pedir-regulacion-honorarios.md` |
| `pronto_despacho_regulacion` | 76 | `pronto-despacho-regulacion.md` |

**No fórmula** (solo sugerencia + invocar skill):

| `tipo_accion` | Sub-estado | Skill a sugerir |
|---------------|------------|-----------------|
| `practicar_liquidacion`  | 70 | `practicar-liquidacion` |
| `liquidar_intereses`     | 75 | `actualizar-liquidacion` |
| `impugnar_liquidacion`   | 71 (contraparte) | `controlar-liquidacion` |
| `pedir_giro_honorarios`  | 73/74 | `pedir-giro-honorarios` |

### Fase 4: Generación del DOCX

Idéntico a caducidad: usa `scripts/generar_escrito.py` con el modelo
correspondiente. Guarda en `/tmp/liquidacion/{fecha}/{numero_safe}_{tipo}.docx`.

### Fase 5: Distribución de borradores

**CABA:**
- Subir a OneDrive del expediente en carpeta `Borradores liquidación/{fecha}/`.
- Link al WA + adjunto en el mensaje de la chica.
- NO subir a PJN (no edita).

**Provincia:**
- Subir como borrador editable al MEV (skill `subir-escrito-mev`).
- Copia en OneDrive.
- Ambos links al WA.

### Fase 6: Mensaje WhatsApp por chica

```
*CONTROL LIQUIDACIÓN — {CHICA} ({JURISDICCION})*
_Corrida {fecha} · {N} expedientes_

🚨 *CRÍTICOS DEL DÍA* ({M} casos)
{Idem detalle de pendientes}

📋 *PENDIENTES POR SUB-ESTADO*

▸ *70 Practicar liquidación*

*1.* {CARATULA_CORTA} — {NUMERO} · sin empuje hace {dias_sin_empuje}d
💰 Monto pendiente: {monto o "no cargado"}

📌 *Estado:* {estado_procesal}
✏️ *Acción:* {accion_inmediata}
📎 Borrador: {link | "—"}
```

**Regla de oro:** que la chica entienda sin ambigüedad qué presentar y por qué,
sin abrir el expediente.

### Fase 7: Mensaje ejecutivo a Matías

```
*RESUMEN EJECUTIVO LIQUIDACIÓN — {fecha}*

🚨 CRÍTICOS: {total}
- Matías (70/75/76 + 1 del 71): {n}
- Noe (resto 71, 72, 73, 74): {n}

💰 Monto pendiente identificado en críticos: {SUMA}

📊 Por sub-estado:
- 70 Practicar liq.: {n}
- 71 Liq practicada: {n}
- 72 Embargo: {n}
- 73 Giro actor: {n}
- 74 Giro nuestro: {n}
- 75 Intereses: {n}
- 76 Regulación: {n}

📝 Borradores generados: {n_caba_onedrive} CABA + {n_pcia_mev} Pcia
🔁 Repetidos (≥3 corridas): {n} (revisar manualmente)
```

Durante prueba, todos los WA van al `16393940416` (Matías) etiquetados con
el nombre de la destinataria (Noe si corresponde).

### Fase 8: Logueo en Supabase

Insertar fila por cada expediente en `liquidacion_corridas`:

```sql
INSERT INTO liquidacion_corridas (
  fecha, expediente_id, responsable_asignada, jurisdiccion,
  sub_estado, sub_estado_label, dias_sin_empuje,
  monto_pendiente_cobro, monto_capital_sentencia, moneda,
  urgencia, critico, tipo_accion, accion_sugerida, texto_sugerido, contexto,
  estado_procesal, pagos_recibidos, pagos_pendientes,
  obstaculo_actual, estrategia_sugerida, accion_inmediata,
  numero_expediente_destino, mev_idc_destino, mev_ido_destino, oficina_destino_label,
  borrador_onedrive_url, borrador_mev_id
) VALUES (...);
```

Igual que Caducidad, **la tabla NO filtra**. El skill toma siempre el top por
días sin empuje. Si un expediente sigue urgente porque nadie actuó, vuelve a
aparecer mañana con un indicador de "repetido". La única salida real es
presentar el escrito (cambia `ultimo_movimiento`) o cambiar el `estado` a 80
Finalizado / 77 Conciliado en la app.

Indicadores en el WA:
- 1ra vez: sin indicador.
- 2da vez seguida: `⚠️ Repetido (2 corridas)`.
- 3ra+: `🔁 Recordatorio — aparece hace N días, sin presentar todavía`.

Consultar repeticiones desde `liquidacion_corridas_repeticiones` (vista creada
en la migración).

## Schedule

Trigger diario **7:30 AR** (= 10:30 UTC) de **lunes a viernes**, después de la
corrida de caducidad. Crear con skill `schedule`.

## Resumen para el agente orquestador (Opus 4.7)

1. Cargar `reglas-ejecucion.md` a memoria.
2. Ejecutar query de Fase 1 → ~21 CABA + ~14 Pcia (variable).
3. Asignar responsables según tabla de Fase 2.
4. Lanzar N subagentes en tandas de 8 paralelos.
5. Consolidar JSON. Identificar CRÍTICOS.
6. Generar mensajes WA + resumen Matías.
7. Enviar con `mcp__whatsapp__wa_send_text` + `wa_send_document`.
8. Insertar filas en `liquidacion_corridas`.
9. Reportar al usuario / al scheduled trigger.

## Tiempo esperado

- Query: 2 seg
- ~25 subagentes en tandas de 8 × ~75 seg = ~4 min
- Generación DOCX + uploads: integrado en cada subagente
- WA envíos paralelos: 5 seg
- **Total: 5–7 min end-to-end.**

Si algún subagente timeout (90 seg), reintentar 1 vez; si falla de nuevo,
marcar `obstaculo_actual = "REVISAR MANUAL: subagente falló"` y seguir.
