# Reglas de ejecución de sentencia (estados 70 a 76)

Este archivo se inyecta en el prompt de **cada subagente** que analiza un
expediente en ejecución. Sumar reglas cuando Matías detecte errores recurrentes.

## Regla cero — concepto de urgencia

A diferencia de Caducidad, en Ejecución **NO hay riesgo de perder la causa**
por inactividad procesal. La urgencia mide otra cosa:

- **Plata pendiente de cobro** que se erosiona por inflación.
- **Honorarios sin regular** que pierden valor con el tiempo.
- **Movimientos del juzgado** que requieren respuesta nuestra (traslado,
  intimación, etc.) y se vencen.

Por lo tanto el subagente **no debe** sugerir prontos despachos por simple
inactividad larga si no hay **acción concreta pendiente nuestra o del juzgado**.

## Reglas por sub-estado

### 70 Practicar liquidación

- Sentencia firme, hay que practicar la liquidación. NO es escrito de fórmula
  — requiere cálculo (skill `practicar-liquidacion`).
- Sugerir `tipo_accion = practicar_liquidacion`.
- Crítico si: pasaron > 60 días desde sentencia firme y no presentamos nada.

### 71 Liquidación practicada

Hay 3 sub-casos según los últimos movimientos:

1. **Esperando aprobación (ya hay traslado o no)**
   - Si pasaron > 30 días desde la liquidación sin proveído del juzgado →
     `tipo_accion = pronto_despacho_aprobacion`.
   - Crítico si > 60 días sin proveído.

2. **Liquidación aprobada y plazo vencido sin depósito de la demandada**
   - `tipo_accion = intimar_pago_deposito` (5 días bajo apercibimiento de
     embargo) o directamente `pedir_embargo` si ya hubo intimación previa.
   - Crítico si > 15 días desde aprobación firme sin depósito.

3. **Traslado de liquidación contraria pendiente**
   - `tipo_accion = impugnar_liquidacion` (NO fórmula — usar skill
     `controlar-liquidacion`).
   - Crítico si el plazo del traslado vence en ≤ 3 días.

### 72 Pedimos embargo

- Si ya hay traba efectiva → mover a 73/74 (pedir giro) en lugar de seguir en 72.
- Si > 30 días desde el pedido sin resolución → `tipo_accion = pronto_despacho_aprobacion`
  (variante "para que se trabe el embargo").
- Crítico si > 60 días sin traba.

### 73 Se ordenó giro actor

- Hay giro a favor del cliente ordenado pero no retirado (o transferencia no
  acreditada).
- `tipo_accion = reiterar_giro` para empujar al banco / juzgado.
- Crítico si > 15 días desde la orden.

### 74 Se ordenó giro nuestro

- Hay giro a favor del estudio ordenado pero no retirado.
- `tipo_accion = reiterar_giro` (variante para honorarios del estudio).
- Crítico si > 15 días desde la orden.

### 75 Intereses

- Cobramos capital, falta liquidar los intereses devengados desde el último
  cálculo. NO es escrito de fórmula — usar skill `actualizar-liquidacion`.
- `tipo_accion = liquidar_intereses`.
- Crítico si > 90 días desde el último cálculo.

### 76 Regulación honorarios

Dos sub-casos:

1. **Aún no pedimos regulación**
   - `tipo_accion = pedir_regulacion_honorarios`.
   - Crítico si pasaron > 60 días desde que se cobró el capital sin
     pedir regulación nuestra.

2. **Pedido de regulación sin resolver**
   - `tipo_accion = pronto_despacho_regulacion`.
   - Crítico si > 60 días desde el pedido sin resolución.

## Reglas comunes a todos los sub-estados

### Cuándo NO sugerir impulso

1. Causa con depósito de fondos en curso pero sin transferencia bancaria
   identificada todavía (esperar 5–10 días hábiles).
2. Causa con CSJN pendiente (vuelve después).
3. Cliente con datos de cuenta no actualizados → bloqueo administrativo
   (`obstaculo_actual = "cliente sin CBU actualizado"`).
4. Causa donde hubo conciliación posterior a la sentencia firme — debería
   estar en 77, marcarlo como `estado_procesal = "Posible conciliación, revisar manualmente"`.

### Provincia (MEV) — particularidades

- En Provincia los giros se piden con escrito + adjuntos al SCBA. El borrador
  va al MEV via skill `subir-escrito-mev`.
- En Provincia el plazo para pedir embargo es más laxo que en CABA.
  Los plazos críticos suben en ~50%.

### Lectura de movimientos

- `tipo='ESCRITO AGREGADO'` → escrito de parte.
- `tipo='FIRMA DESPACHO'` → providencia del juzgado.
- Si hay un movimiento `APRUEBA LIQUIDACIÓN` o `LIBRA GIRO`, contar los días
  desde ese movimiento.
- Si hay un movimiento `INTIMA DEPÓSITO BAJO APERCIBIMIENTO` y pasaron > 5
  días hábiles → directamente `pedir_embargo`.

## Criterios CRÍTICOS (bloque 🚨 al tope del WA)

Un expediente va al bloque CRÍTICOS cuando se da al menos una:

1. **Traslado vigente sin contestar** (impugnación de liquidación, etc.) — días
   restantes ≤ 3.
2. **Liquidación aprobada > 15 días sin depósito** (CABA) / > 25 días (Pcia).
3. **Embargo trabado > 30 días sin libramiento de giro**.
4. **Giro ordenado > 30 días sin retirar** (cliente o estudio).
5. **Pedido de regulación > 60 días sin resolución**.
6. **Sentencia firme > 60 días sin practicar liquidación**.

Caso típico NO crítico: estado 70 con sentencia firme reciente (< 30 días) — la
chica todavía está en plazo razonable para practicar.
