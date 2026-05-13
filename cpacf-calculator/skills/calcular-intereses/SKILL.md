---
name: calcular-intereses
description: >
  Calculador de intereses moratorios judiciales usando el CPACF. Usar cuando el usuario pida
  "calcular intereses", "liquidación de intereses", "liquidación complementaria", "intereses moratorios",
  "tasa activa BNA", "actualizar montos", "art 770", "capitalización semestral", "intereses post art 132",
  "intereses por mora", "imputación art 900 CCCN", "intereses sobre el remanente", "liquidar honorarios",
  o cualquier cálculo de intereses para causas judiciales argentinas — especialmente liquidaciones
  complementarias por mora en el depósito post-art. 132 L.O.
version: 1.0.0
---

# Calcular intereses judiciales (laboral CNAT + civil/comercial)

Skill para practicar liquidaciones de intereses moratorios usando el calculador oficial del CPACF
(`tasas.cpacf.org.ar`) vía MCP. Cubre liquidación inicial (art. 132 L.O.) y liquidación complementaria
(post-mora del depósito tardío).

## ⚠️ REGLA DE ORO

**LEE LA SENTENCIA ANTES DE CALCULAR.** La sentencia ordena la tasa y el mecanismo. No copies el
mecanismo de la liquidación anterior, no asumas. Encontrá en el fallo:

1. El **monto de condena** y la fecha a la que está expresado.
2. La **tasa de interés ordenada** y desde qué fecha corre.
3. Si hay **dos tasas** (una pre-art. 132 y otra post-mora) — frecuente en CNAT.
4. Si hay **capitalización** (art. 770 CCyCN) y desde cuándo.

Ej. caso Yrala (CNAT Sala VI, 28/10/2024, voto Craig–Vázquez): RIPTE+6% puro hasta liquidación
art. 132; tasa activa BNA cartera + cap. semestral art. 770 CCyCN desde la mora.

## Mecanismos típicos según sentencia (CNAT laboral)

| Sentencia ordena | Pre-art. 132 (hasta intimación de pago) | Post-art. 132 (en mora) |
|---|---|---|
| **RIPTE + 6% puro + art. 770 si mora** (Craig, Vázquez) | RIPTE sobre capital + 6% interés puro anual | Tasa activa BNA cartera general nominal anual 30 días + **cap. semestral** |
| **Tasa activa BNA pura + art. 770 si mora** (clásica Acta 2357/02 — 1ª instancia típica) | Tasa activa BNA (Acta 2357/02) | Tasa activa BNA + **cap. semestral** (770 CCyCN) |
| **Acta 2658** (Pose y Salas que la siguen) | Tasa efectiva anual (no nominal) | Igual + 770 CCyCN |
| **Actas 2783/2784** (laboral con composición) | Tasa específica del acta | Sólo si la sentencia lo dice |

**Mecanismo en provincia (SCBA):** habitualmente tasa pasiva BPBA o tasa pasiva digital. Verificar
sentencia. Pcia BsAs **no** suele capitalizar.

## Herramientas MCP disponibles

### `cpacf_calcular_intereses`

Calcula intereses sobre un capital entre dos fechas usando tasas oficiales.

**Parámetros:**

- `capital` (str): Monto sin puntos de miles, coma decimal. Ej: `138653657,55`
- `fecha_inicial` (str): `dd/mm/aaaa`
- `fecha_final` (str): `dd/mm/aaaa`
- `tasa` (enum, default `"1"`): ID de la tasa (ver tabla)
- `capitalizacion` (enum, default `"0"`): `0`=ninguna, `30`=mensual, `90`=trimestral, `180`=semestral
- `multiplicador` (enum, default `"1"`): `1`, `1.5`, `2`, `2.5`

**Devuelve:** capital_original, total_liquidacion, tasa_acumulada, tasa_utilizada, URL al PDF.

⚠️ **Importante:** el `total_liquidacion` que devuelve el CPACF es **CAPITAL + INTERESES**, NO
solo los intereses. Los intereses se calculan como `total_liquidacion - capital_original`.
Confundirlos es un error frecuente — ver "Errores que no debés repetir" abajo.

### `cpacf_listar_tasas`

Lista las tasas disponibles. Sin parámetros.

## Tasas disponibles

| ID | Tasa | Uso típico |
|----|------|-----------|
| 1 | **Activa BNA Efectiva mensual vencida** | Acta CNAT 2357/02 — laboral estándar antiguo |
| 2 | **Activa BNA Cartera general nominal anual 30 días** | Lo que dice la mayoría de las sentencias laborales modernas y comerciales |
| 3 | Pasiva BNA | Algunos civiles |
| 4 | Activa BPBA Restantes Operaciones | Pcia BsAs |
| 5 | Pasiva BPBA | Pcia BsAs |
| 6 | Art. 37 Ley 11.683 | Resarcitorios fiscales |
| 7 | Art. 52 Ley 11.683 | Punitorios fiscales |
| 8 | Pasiva BCRA | Referencia |
| 9 | CER | Ajuste inflación |
| 10–12 | IPIM / IPC históricos | Ajuste índices |

⚠️ Si la sentencia dice "tasa activa cartera general nominal anual vencida a 30 días BNA" → tasa ID **2**, no 1.

## Procedimiento — Liquidación complementaria post-mora (caso Yrala)

Aplica cuando: hay **liquidación aprobada (art. 132 L.O.)**, vencido el plazo de depósito, y la
demandada depositó tarde o sigue impaga. La demandada ya entró en mora → corresponde aplicar art.
770 CCyCN con capitalización semestral y la tasa que ordene la sentencia para esa etapa
(generalmente tasa activa BNA cartera).

### Paso 1 — Reunir los datos

| Dato | De dónde sale |
|---|---|
| Capital aprobado | Auto de aprobación de la liquidación art. 132 |
| Fecha de aprobación | Auto de aprobación |
| Fecha de notificación a demandada (cédula electrónica) | Lex100 / MEV |
| Plazo de depósito (5 días) | Vence al 5to día hábil desde notificación |
| Fecha del depósito tardío | Lex100 (boleta de depósito DEOX) |
| Fecha de notificación al actor del depósito | Lex100 (despacho "hágase saber") |
| Tasa que ordena la sentencia para la mora | Sentencia firme (de Cámara o única instancia si no se apeló) |

### Paso 2 — Tramo 1: desde aprobación hasta notificación del depósito

```
cpacf_calcular_intereses(
  capital = "<capital aprobado>",
  fecha_inicial = "<día siguiente a aprobación>",
  fecha_final = "<fecha notificación depósito>",
  tasa = "2",                    # o la que ordene la sentencia
  capitalizacion = "180"         # cap. semestral art. 770 CCyCN
)
```

Intereses tramo 1 = `total_liquidacion - capital_original`.

### Paso 3 — Imputación art. 900 CCCN al pago tardío

> *Art. 900 CCCN — "Si adeuda capital e intereses, el pago no puede imputarse a la deuda principal
> sin consentimiento del acreedor."*

```
Total adeudado al día de la notificación = capital + intereses tramo 1
Pago tardío recibido                      = capital aprobado (lo que depositó la ART)
Imputación art. 900:
  - Intereses tramo 1 → se cancelan (los pagó primero)
  - Sobrante (pago tardío - intereses tramo 1) → se imputa al capital
Remanente de capital impago = total adeudado - pago tardío = intereses tramo 1
```

Cita fallo CSJN Fallos 340:1671 para justificar que la mora corre hasta la notificación al
acreedor, no hasta el mero depósito:

> *"Para detener el curso de los intereses no basta con el solo depósito judicial del monto
> adeudado ya que ese depósito no extingue la obligación porque además de ser íntegro, debe ser
> comunicado al acreedor, por lo que el transcurso del tiempo y las consecuencias que se derivan
> de ello no deben pesar sobre quien no tenía conocimiento de que las sumas habían sido
> depositadas." (Fallos: 340:1671)*

### Paso 4 — Tramo 2: desde el día siguiente a la notificación hasta hoy

```
cpacf_calcular_intereses(
  capital = "<remanente impago = intereses tramo 1>",
  fecha_inicial = "<día siguiente a notificación>",
  fecha_final   = "<fecha de la liquidación>",
  tasa = "2",
  capitalizacion = "180"
)
```

### Paso 5 — Total adeudado y honorarios

```
Total adeudado = remanente impago + intereses tramo 2
```

**Honorarios:** repetir el mismo procedimiento sobre el monto de honorarios sin IVA aprobado, y al
final agregar 21% de IVA si corresponde. Los honorarios son crédito propio, devengan intereses por
separado.

### Paso 6 — Cláusula para detener intereses

Incluir siempre en el escrito:

> *"Asimismo, solicito a V.S. que se le haga saber a la accionada que si su intención es detener
> el curso de los intereses deberá practicar nueva liquidación a la fecha del efectivo pago y
> acreditar el depósito de la cantidad resultante de ésta, tomando en consideración que se
> entenderá como fecha de efectivo pago aquella en la que la acreedora quede notificada
> automáticamente del auto que hace saber la dación en pago efectuada."*

## Procedimiento — Liquidación inicial art. 132 L.O. (RIPTE + 6%)

Si la sentencia ordena RIPTE + 6% puro hasta la liquidación (caso típico de CNAT post-Oliva/Decreto
669/19), usar el skill **`practicar-liquidacion`** que ya tiene los Excel y mecanismos preparados.
Acá sólo el resumen:

1. Capital histórico × factor RIPTE (RIPTE fecha liquidación / RIPTE fecha siniestro) = capital
   actualizado.
2. Sobre el capital actualizado, 6% puro anual × (días corridos / 365) = intereses puros.
3. Total = capital actualizado + intereses puros.

⚠️ El 6% NUNCA se aplica con capitalización antes de la mora art. 132 — es interés puro.

## Errores que NO debés repetir (caso Yrala, mayo 2026)

Una empleada presentó una liquidación complementaria con varios errores que costaron $20M en
intereses no liquidados. Los errores que hay que evitar:

1. **Aplicar la tasa pre-art. 132 a la etapa post-art. 132.** La sentencia distinguía dos tasas
   (RIPTE+6% antes / tasa activa BNA + cap. semestral después) y se siguió usando 6% puro para los
   intereses post-mora. La tasa activa BNA en 2025 ronda 35-50% TNA — usar 6% puro deja afuera
   2/3 de los intereses devengados.

2. **Confundir "Total liquidación" con "Intereses".** El PDF del CPACF devuelve
   `capital_original`, `total_intereses` y `total_liquidacion = capital + intereses`. En el
   escrito hay que poner SOLO los intereses (`total_liquidacion - capital_original`), no el total.

3. **Ingresar capitales incorrectos al CPACF.** Verificar que el `capital_original` que devuelve
   el PDF coincida con el capital aprobado por el juzgado. Si no coincide, el cálculo está mal
   ingresado.

4. **Olvidarse de los honorarios.** Los honorarios profesionales son crédito propio del letrado,
   devengan sus propios intereses por mora. Si el Excel/plantilla los tiene como sección
   separada, completarla. No basta liquidar el capital.

5. **No aplicar capitalización semestral cuando la sentencia ordena art. 770 CCyCN.** El
   parámetro `capitalizacion = "180"` cambia sustancialmente el resultado en períodos largos.

6. **Tomar como fecha de detención el depósito y no la notificación al actor.** CSJN Fallos
   340:1671: la mora corre hasta la notificación. Citar el fallo siempre.

7. **No incluir la cláusula del Paso 6.** Sin ella, la ART deposita una suma fija y los intereses
   siguen corriendo silenciosamente — se evita teniendo la cláusula que obliga a re-liquidar al
   día del pago.

## Verificación cruzada

Antes de presentar:

- ✅ El `capital_original` que aparece en cada PDF CPACF coincide con el capital real (aprobado
  o remanente, según el tramo).
- ✅ La tasa utilizada (campo `tasa_utilizada` del PDF) coincide con la que ordena la sentencia.
- ✅ La capitalización corresponde a la mora art. 770 si así lo ordena la sentencia.
- ✅ Los intereses del escrito = `total_liquidacion - capital_original` del PDF.
- ✅ La imputación art. 900 CCCN se aplica correctamente: el pago tardío imputa primero a
  intereses, después al capital.
- ✅ Se incluyen los honorarios profesionales con sus propios intereses + IVA.
- ✅ Se cita Fallos 340:1671 (CSJN — depósito sin notificación no extingue).
- ✅ Se incluye la cláusula de detención de intereses ("acreditar el depósito de la cantidad
  resultante de ésta").

## Tips de formato del escrito

- Encabezado del estudio (Times New Roman 12, interlineado 1.5, márgenes 2/2/3/2 cm).
- Tabla con: rubro, fecha inicial, fecha final, monto.
- Pegar las URLs de los PDFs CPACF (`https://tasas.cpacf.org.ar/calculo_XXXXX.pdf`) como prueba
  del cálculo — el juzgado puede verificarlas.
- Las tablas separadas para capital y honorarios.
- Cierre con "SE CORRA TRASLADO" pidiendo 3 días bajo apercibimiento.

## Cuándo NO usar este skill

- Para **practicar la liquidación inicial** después de sentencia firme → `practicar-liquidacion`
  (tiene los modelos RIPTE/IPC/tasa activa).
- Para **controlar una liquidación de la contraparte** → `controlar-liquidacion`.
- Para **actualizar una liquidación ya aprobada** sumando diferencias por UMA/RIPTE actualizado
  → `actualizar-liquidacion`.
- Para **ampliar fundamentos de inconstitucionalidad** del art. 7 Ley 23.928 →
  `ampliar-fundamentos-barrios`.

Este skill es para el cálculo numérico puro de intereses, especialmente para liquidaciones
complementarias post-mora.
