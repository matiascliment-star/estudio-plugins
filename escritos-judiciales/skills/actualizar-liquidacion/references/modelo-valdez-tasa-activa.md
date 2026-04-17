# Modelo — Actualización con Tasa Activa BNA Capitalizable

Tomado del escrito de VALDEZ c/ LA SEGUNDA (CNT 23596/2022 - JNT 21). Caso típico: sentencia que manda tasa activa BNA efectiva mensual vencida capitalizable semestralmente (doctrina CNAT post-2022).

## Título

```
PARTE ACTORA PRACTICA NUEVA LIQUIDACIÓN DE INTERESES MORATORIOS - SE CORRA TRASLADO.-
```

## I.- PRACTICA NUEVA LIQUIDACIÓN

Párrafo introductorio (cuando hay una resolución anterior que desestimó la liquidación):

> En virtud de la resolución de fecha {FECHA_RESOLUCION}, mediante la cual se desestimó la liquidación oportunamente practicada por esta parte, se procede a presentar una nueva liquidación conforme a los parámetros allí establecidos.

Tabla principal — dos bloques (crédito laboral + honorarios):

### Bloque A) Crédito Laboral

| Concepto | Valor |
|---|---|
| Crédito laboral según liquidación de fecha {FECHA_LIQ_ANTERIOR} | ${CAPITAL_BASE} |
| Intereses desde el {F1} al {F2} (primer período) | ${INT_1} |
| (Cita CSJN "Para detener el curso de los intereses no basta...") | |
| (Link al cálculo CPACF, ej: https://tasas.cpacf.org.ar/calculo_XXX.pdf) | |
| **Total crédito laboral al {F2} — primera capitalización** | ${TOTAL_1} |
| Intereses desde el {F3} al {F4} (segundo período, sobre capital capitalizado) | ${INT_2} |
| (Link al cálculo CPACF) | |
| **Total adeudado al {F4}** | ${TOTAL_2} |
| Menos lo percibido en concepto de crédito laboral (art. 900 CCCN) | -${PERCIBIDO} |
| **Total adeudado al {FECHA_LIQ_ACTUAL}** | ${SALDO_CAP} |

### Bloque B) Honorarios (si aplica)

| Concepto | Valor |
|---|---|
| Honorarios sin IVA al {F_HON_BASE} | ${HON_BASE} |
| Intereses desde el {F1} al {F2} (primer período) | ${INT_H1} |
| (Link al cálculo CPACF) | |
| **Total honorarios al {F2} — primera capitalización** | ${TOTAL_H1} |
| Intereses desde el {F3} al {F4} (segundo período) | ${INT_H2} |
| (Link al cálculo CPACF) | |
| **Total adeudado al {F4}** | ${TOTAL_H2} |
| Menos lo percibido en concepto de honorarios (art. 900 CCCN) | -${PERC_HON} |
| **Total adeudado al {FECHA} sin IVA** | ${HON_SIN_IVA} |
| IVA 21% | ${IVA} |
| **Total adeudado al {FECHA} con IVA** | ${HON_CON_IVA} |

## II.- SE CORRA TRASLADO

Texto literal (copiar sin cambios):

> Solicito se ordene el traslado del presente escrito por tres días a la parte demandada a fin de que deposite el monto resultante de ésta liquidación en una cuenta del Banco Ciudad perteneciente a éstos a actuados o, en su caso, la impugne, practique la liquidación que estime corresponder y deposite el monto que arroje la misma en la cuenta indicada, todo ello bajo apercibimiento de que transcurrido el plazo sin que medie observación válida, quedará aprobada la liquidación efectuada por esta parte y se procederá a la ejecución.
>
> Asimismo, solicito a V.S que se le haga saber a la accionada que si su intención es detener el curso de los intereses deberá practicar nueva liquidación a la fecha del efectivo pago y acreditar el depósito de la cantidad resultante de ésta, tomando en consideración que se entenderá como fecha de efectivo pago aquella en la que la acreedora quede notificada automáticamente del auto que hace saber la dación en pago efectuada.

## Cierre (centrado)

```
Proveer de conformidad,
SERÁ JUSTICIA              ← en negrita
```

## Uso del CPACF para calcular intereses

Herramienta: MCP `mcp__claude_ai_cpacf__cpacf_calcular_intereses`.

Parámetros típicos:
- `capital`: el capital de esa etapa (en formato "81435196,75")
- `fecha_inicial`: primer día del período (DD/MM/AAAA)
- `fecha_final`: último día del período
- `tasa`: "1" = Tasa Activa BNA Efectiva Mensual Vencida
- `capitalizacion`: "0" = simple, o los meses de capitalización
- `multiplicador`: "1"

Para capitalización semestral: dividir el período en semestres y aplicar capitalización manual (o usar la fórmula de Cámara directamente).

El output incluye `total_intereses`, `total_liquidacion` y un link al PDF del cálculo: agregar ese link al escrito para respaldo.
