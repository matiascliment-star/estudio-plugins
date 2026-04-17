---
name: actualizar-liquidacion
description: Actualiza una liquidación judicial ya aprobada y practica una NUEVA liquidación para reclamar las diferencias devengadas desde la fecha de aprobación hasta la fecha actual (o la fecha del último pago). Calcula diferencias de capital (por actualización RIPTE / tasa activa / CER / IPC) y/o de honorarios (por valor UMA actual), descuenta los pagos parciales efectivamente percibidos, y genera el DOCX con tablas profesionales. Opcionalmente sube el borrador al PJN. Usar cuando el usuario pida "actualizar liquidación", "nueva liquidación", "reliquidación", "reclamar diferencias", "diferencias por actualización", "actualizar RIPTE", "actualizar UMA", "liquidar diferencias", "nueva liquidación de intereses", "practicar liquidación complementaria", "liquidar hasta hoy", "nueva liquidación a la fecha de pago". Triggers: "actualizar liquidación", "nueva liquidación", "reliquidación", "reclamar diferencias", "diferencias RIPTE", "diferencias UMA", "liquidación complementaria", "liquidar hasta hoy", "liquidar diferencias", "nueva liquidación de intereses".
---

# Skill: Actualizar Liquidación — Reclamar Diferencias

Practica una nueva liquidación para reclamar las diferencias devengadas desde una liquidación anterior aprobada. Distingue dos objetivos típicos (que pueden combinarse):

1. **Capital**: diferencias por actualización (RIPTE, tasa activa BNA capitalizable, IPC+tasa pura, CER, etc.) desde la fecha de la liquidación aprobada hasta la fecha del efectivo pago (o del último pago parcial).
2. **Honorarios**: diferencias por valor UMA actual (ley 27.423 art. 51) sobre los honorarios firmes, menos lo efectivamente percibido.

Diferencias clave con otras skills:
- **NO es `practicar-liquidacion`**: esa crea desde cero la primera liquidación post-sentencia. Esta parte del supuesto de que ya hay una liquidación aprobada.
- **NO es `controlar-liquidacion`**: esa critica una liquidación de la contraparte. Esta genera la propia del actor.

## Cuándo usar

- Hay una **liquidación aprobada previa** (propia del actor) y pasaron meses desde su aprobación.
- Hubo pagos parciales por parte de la demandada (o no).
- El índice de actualización (RIPTE, tasa, UMA) siguió corriendo.
- Hay que reclamar la diferencia acumulada + descontar lo efectivamente percibido.

## Flujo

1. **Consultar el expediente en Supabase** (`scrape-pjn-supabase`):
   - `expedientes` por `numero_causa` o carátula.
   - `movimientos_pjn` de los últimos 12 meses para detectar: (a) liquidación aprobada previa + su importe y fecha del índice; (b) depósitos/transferencias de la demandada (con fechas y montos discriminados); (c) giros librados al actor/letrado.
   - Usar la columna `texto_documento` — no scrapear PJN de nuevo.
2. **Identificar el método de actualización** de la sentencia (`expedientes.resumen_ia` y/o `sentencias.metodo_actualizacion`):
   - `RIPTE` (ley 27.348 accidentes laborales)
   - `Tasa activa BNA efectiva mensual vencida capitalizable` (CNAT Cámara moderna)
   - `IPC + tasa pura 6%` (civil nueva doctrina)
   - `RIPTE + tasa pura` (laboral mixto)
   - `CER` (deuda indexada)
3. **Identificar los valores UMA pertinentes** (si hay honorarios en UMAs):
   - UMA vigente al día de la fecha (https://new.cpacf.org.ar/noticia/5201/valores-uma-pjn-ley-27423).
   - UMA a la fecha del último pago parcial (si aplica).
4. **Leer la liquidación aprobada previa** para extraer el capital base y la fecha del índice usado.
5. **Leer los pagos efectivos** (montos, fechas, conceptos — NO confiar ciegamente en lo que dice la demandada en su escrito; **cruzar siempre con el comprobante bancario y el despacho del juzgado**). En particular:
   - Verificar que los honorarios NO se descuenten con montos imputados falsamente al capital.
   - Descomponer cada transferencia en honorarios + IVA cuando corresponda.
6. **Calcular las diferencias**:
   - Capital actualizado a la fecha de cobro / fecha actual menos pagos efectivos (nominal).
   - Honorarios al UMA actual menos pagos efectivos (con IVA descompuesto por 1,21).
7. **Generar DOCX** con el template `templates/generar_actualizacion.py`:
   - Copiar a `/tmp/` y adaptar el dict `CASO`.
   - Ejecutar.
   - El DOCX va a `~/Desktop/{caratula_short}_nueva_liquidacion.docx`.
8. **Preguntar si subir al PJN/MEV** como borrador.

## Formato (estándar del estudio, ver `feedback_formato_escritos.md`)

- Times New Roman 12pt, interlineado 1.5
- Márgenes sup/inf 2cm, izq 3cm, der 2cm
- Título principal: JUSTIFICADO, negrita + subrayado, sin sangría
- "Sr. Juez:" a la izquierda, negrita, sin sangría
- Primer párrafo: sangría 1.5 cm, nombre + carátula en negrita
- Secciones I.-, II.-: sangría 1.25 cm, negrita + subrayado, línea en blanco antes
- Cuerpo: justificado, sangría 1.25 cm
- Tablas: Times 11pt, bordes simples, headers en negrita

## Estructura del escrito (modelos fieles en `references/`)

Título típico:
```
PARTE ACTORA PRACTICA NUEVA LIQUIDACIÓN [DE CAPITAL Y HONORARIOS]. ACTUALIZA POR [RIPTE / TASA ACTIVA / IPC / CER] Y VALOR UMA VIGENTE. RECLAMA DIFERENCIAS. SE CORRA TRASLADO.-
```

1. **I.- PRACTICA NUEVA LIQUIDACIÓN.-**
   - Justifica por qué se practica (tiempo transcurrido, pagos parciales, método de actualización que sigue corriendo).
   - **A) CAPITAL** (si aplica): tabla con crédito original, factor de actualización, capital actualizado, pagos parciales descontados, saldo pendiente.
   - **B) HONORARIOS** (si aplica): dos escenarios si hay prorrateo pendiente (principal sin prorrateo + subsidiario con prorrateo). Tabla con UMAs reguladas, valor UMA actual, IVA 21%, lo pagado (discriminado), saldo adeudado. Dejar claro: el REX no se prorratea.
   - **C) RESUMEN — TOTAL ADEUDADO**: tabla final con capital + honorarios en ambos escenarios.
   - Reserva de actualización al efectivo pago + intereses moratorios (art. 900 CCCN).
2. **II.- SE CORRA TRASLADO.-** (texto estándar del modelo Valdez):
   - Traslado por 3 días, bajo apercibimiento de aprobarse.
   - Intimación: si quiere detener los intereses/actualización, debe practicar nueva liquidación a la fecha del efectivo pago.
3. **Cierre**: "Proveer de conformidad, / SERÁ JUSTICIA" centrado.

## Métodos de actualización

### RIPTE
- Fórmula: `capital_original × (RIPTE_mes_liquidación / RIPTE_mes_base)`
- Fuente valores: https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte
- Nota: publicación con retraso de ~2 meses. Usar el último publicado y reservar compensación por demora (fallo "BAREIRO c/ SWISS MEDICAL" Sala ?).

### Tasa Activa BNA efectiva mensual vencida capitalizable
- Fórmula: capitalización semestral (cada 6 meses agregar intereses acumulados al capital).
- Herramienta: CPACF (https://tasas.cpacf.org.ar/), tasa nº 1.
- Ver modelo Valdez (`references/modelo-valdez-tasa-activa.md`).

### UMA (honorarios)
- Fórmula: `UMAs_reguladas × UMA_vigente_a_la_fecha`
- Fuente valores: https://new.cpacf.org.ar/noticia/5201/valores-uma-pjn-ley-27423
- La cantidad de UMAs NO se modifica; solo su valor en pesos se actualiza mensualmente.
- Si hay prorrateo aprobado/pendiente, expresar las UMAs prorrateadas al valor UMA actual.

### IPC + tasa pura
- Actualizar capital por IPC hasta la fecha + tasa pura 6% anual sobre el capital actualizado.

### CER
- Multiplicar capital × (CER_final / CER_inicial).

## Precauciones

- **Descomponer honorarios + IVA** siempre (en tablas y en el texto).
- **Verificar los pagos** contra comprobantes bancarios y despachos del juzgado. No confiar en descripciones tramposas de la demandada que pretendan imputar capital pagado como si fuera honorarios (o viceversa).
- **Descontar los pagos al valor nominal** a la fecha en que se percibieron (criterio laboral ortodoxo: el capital se actualiza íntegro, los pagos parciales se descuentan al valor histórico).
- **Reserva de nueva liquidación al efectivo pago** + intereses por mora (art. 900 CCCN, art. 51 ley 27.423).
- **Fecha de liquidación**: si hay prorrateo pendiente, liquidar al UMA vigente pero aclarar que la cantidad de UMAs se determina al momento del cobro (en el caso Suárez, dic-2025).

## Referencias

- `references/modelo-valdez-tasa-activa.md`: liquidación por tasa activa BNA capitalizable (caso civil CNAT).
- `references/modelo-suarez-ripte-uma.md`: liquidación combinada RIPTE (capital) + UMA (honorarios) con dos escenarios de prorrateo.
- `templates/generar_actualizacion.py`: template Python parametrizable.

## Relación con otras skills

- Se suele presentar JUNTO con `pedir-giro-honorarios` (libramiento del giro de lo ya depositado) y/o con un escrito de notificación espontánea + oposición al prorrateo cuando hay cuestiones conexas.
- Si el juzgado ya desestimó una liquidación previa, el escrito debe citar el despacho y acompañar nueva liquidación acatando sus parámetros (ver modelo Valdez).
