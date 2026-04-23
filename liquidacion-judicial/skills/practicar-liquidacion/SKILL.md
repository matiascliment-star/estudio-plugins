---
name: practicar-liquidacion
description: >
  Práctica de liquidaciones judiciales art. 132 L.O. Genera el escrito completo en DOCX
  con tablas profesionales, constancia ARCA, y cálculo automático según el mecanismo que
  mande la sentencia: RIPTE, RIPTE + tasa pura, tasa activa BNA capitalizable, IPC + tasa pura,
  CER, o cualquier combinación. Usar cuando el usuario pida "practicar liquidación",
  "hacer liquidación", "armar liquidación", "liquidación art 132", "liquidar sentencia",
  "liquidación de sentencia firme", "liquidación RIPTE", "liquidación decreto 669",
  "liquidación con tasa activa", "liquidación IPC", "liquidación CER", "liquidación capitalizable",
  o cualquier tarea de crear una liquidación desde cero basada en una sentencia firme.
  Cubre casos laborales (CNAT), civiles y federales. Soporta 4 variantes: A) RIPTE puro,
  B) RIPTE + tasa pura, C) Tasa activa capitalizable semestral, D) IPC + tasa pura.
  Diferencia clave con controlar-liquidacion: este skill CREA la liquidación y genera el DOCX;
  controlar-liquidacion REVISA una ya existente.
version: 0.1.0
---

# Práctica de Liquidaciones Judiciales - Art. 132 L.O.

Sos un abogado litigante experto en liquidaciones judiciales argentinas. Tu trabajo es leer sentencias firmes, identificar los parámetros de condena, calcular el crédito actualizado, y generar un escrito formal en DOCX listo para presentar al juzgado.

## Workflow completo

### Paso 1: Obtener el expediente y las sentencias

1. Pedirle al usuario el número de expediente y jurisdicción (PJN, MEV, etc.)
2. Usar las credenciales del `.env` del usuario:
   - PJN: `PJN_USUARIO` y `PJN_PASSWORD`
   - MEV: `MEV_USUARIO` y `MEV_PASSWORD`
3. Obtener los movimientos con `pjn_obtener_movimientos` (o `mev_obtener_movimientos`)
4. Identificar las sentencias clave:
   - **Sentencia de 1ra instancia** (buscar "SENTENCIA DEFINITIVA" en oficina del juzgado)
   - **Sentencia de Cámara** (buscar "SENTENCIA DEFINITIVA COMPUTABLE" en oficina de Sala)
   - **Aclaratorias y revocatorias** (buscar "SENTENCIA INTERLOCUTORIA", "REVOCATORIA", "ACLARATORIA" — las aclaratorias generalmente son sentencias interlocutorias)
5. Leer los documentos con `pjn_leer_documentos` usando `filtro_descripcion`

### Paso 2: Analizar las sentencias y determinar qué quedó firme

Leer en orden cronológico: 1ra instancia → Cámara → aclaratoria/revocatoria.

Lo que importa es **lo último que quedó firme**. Si Cámara modificó algo, eso prevalece. Si hubo revocatoria in extremis rechazada, la sentencia de Cámara quedó firme tal cual.

Extraer con precisión:

#### Datos del caso
- Carátula, número de expediente, juzgado, sala
- Fecha del accidente/hecho generador
- Fecha de la sentencia firme

#### Parámetros de condena
- **Capital de condena**: monto fijo que surge de la fórmula o rubro condenado
- **Desglose**: indemnización base + adicionales (ej: art. 3 ley 26.773 = 20%)
- **IBM** (ingreso base mensual) si aplica
- **Incapacidad** si es caso de ART/accidente

#### Régimen de intereses/actualización
Determinar qué sistema manda la sentencia firme:

| Tipo | Cuándo aplica | Cómo calcular |
|------|--------------|---------------|
| **RIPTE** (decreto 669/19) | Cámara aplica dto. 669/19 | Ajustar capital × (RIPTE final ÷ RIPTE inicial) |
| **Tasa Activa BNA Cartera General** | Siempre que la sentencia diga "tasa activa" es la Cartera General (ID 2 en CPACF). Nunca usar la Efectiva (ID 1). | Usar CPACF tasa ID 2 |
| **Tasa Pasiva BNA** | Algunos civiles | Usar CPACF tasa ID 3 |
| **Mixto** | Distintos períodos con distintas tasas | Calcular cada período por separado |

#### Honorarios
Extraer los porcentajes regulados por Cámara (o por 1ra inst. si no hubo apelación):
- Actora: X% sobre monto total de condena
- Demandada: Y% sobre monto total de condena
- Perito médico/contador: Z% sobre monto total de condena
- Alzada: leer siempre lo que reguló la Cámara (puede ser 25%, 30%, 35%, un monto fijo en UMAs, etc. — NO asumir 30%)
- REF (recurso extraordinario federal): leer siempre lo que reguló la Cámara o la Corte (NO asumir 30%)
- Convertir a UMAs: honorarios_pesos ÷ valor_UMA = cantidad UMAs

#### Costas
- **Todas a cargo de demandada**: incluir línea de costas en la tabla + honorarios de todas las instancias
- **Alzada por su orden**: incluir honorarios de TODAS las instancias en la tabla pero NO poner ninguna línea detallando distribución de costas. Estrategia: que la contraparte se equivoque y pague todo.
- **Cada parte sus costas**: solo incluir honorarios propios

### Paso 3: Obtener datos para el cálculo

#### Si es RIPTE

**FUENTE OFICIAL PRIMARIA — PDF del Ministerio de Trabajo**:
- Portal: https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte
- **PDF con serie histórica completa** (desde julio 1994 hasta el último publicado): patrón `https://www.argentina.gob.ar/sites/default/files/ripte_[mes]_[año]-mdch.pdf` (ej: `ripte_febrero_2026-mdch.pdf`).
- Es la fuente oficial que se actualiza cada mes. **Usar siempre esta primero.** Contiene TODOS los índices históricos en un solo PDF.
- Columnas del PDF: `Período | Monto en $ | Variación % | Índice Base 07/94 = 100 | RIPTE - Índice No Decreciente Base 07/94 = 100 (uso exclusivo Riesgos del Trabajo)`.
- Para liquidaciones de accidentes de trabajo (Ley 24.557 / 27.348 / Decreto 669/19) **usar la 5ta columna** ("RIPTE - Índice No Decreciente") porque es la oficial de la SRT. En la práctica reciente es numéricamente idéntica a la 4ta; solo difieren cuando hubo deflación mensual histórica.
- **NO usar la columna "Monto en $"** — es la remuneración promedio en pesos, distinta escala.

**Procedimiento**:
1. Fetchear el PDF del Ministerio del mes actual. Si falla (404), probar meses anteriores (el último publicado tiene ~45 días de atraso).
2. Leer el PDF y extraer:
   - Índice RIPTE del mes del accidente/primera manifestación invalidante
   - Último índice RIPTE publicado (última fila del PDF)
   - Índice RIPTE del mes de mitigación (meses anteriores al accidente igual al retraso)
3. Calcular meses de retraso entre último RIPTE publicado y fecha de liquidación.

**Fuentes alternativas (si el PDF del Ministerio no está disponible)**:
- https://ripte.agjusneuquen.gob.ar/riptes (AGJ Neuquén — tarda 1-2 meses más)
- https://ikiwi.net.ar/indice-ripte/ (backup)

#### Si es Tasa Activa/Pasiva
1. Usar `cpacf_calcular_intereses` con los parámetros correspondientes
2. Capital en formato argentino: sin puntos de miles, coma decimal (ej: "503046,70")

#### Valor UMA vigente
Buscar en https://new.cpacf.org.ar/noticia/5201/valores-uma-pjn-ley-27423

### Paso 4: Generar el DOCX

Usar el script Python con python-docx. El documento tiene esta estructura:

```
1. Constancia de inscripción ARCA (imagen al inicio)
2. [línea en blanco]
3. TÍTULO (bold + subrayado): "PARTE ACTORA PRACTICA LIQUIDACIÓN - ..."
4. [línea en blanco]
5. Sr. Juez:
6. Encabezado con datos del abogado y carátula
7. [línea en blanco]
8. I. PRACTICA LIQUIDACIÓN (bold + subrayado)
9. [línea en blanco]
10. "Practico liquidación conforme..."
11. [línea en blanco]
12. TABLA 1: Liquidación según sentencia
13. [línea en blanco]
14. [línea en blanco]
15. II. SE ADOPTEN MEDIDAS... (bold + subrayado) — solo si RIPTE y Cámara no resolvió el retraso
16. [línea en blanco]
17. Párrafos pidiendo mitigación (con blank() entre cada uno)
18. [línea en blanco]
19. TABLA 2: Liquidación con mitigación
20. [línea en blanco]
21. [línea en blanco]
22. III. SE CORRA TRASLADO (bold + subrayado)
23. [línea en blanco]
24. Párrafos de traslado
25. [línea en blanco]
26. [línea en blanco]
27. IV. RESERVA DERECHOS (bold + subrayado)
28. [línea en blanco]
29. Párrafo de reserva
30. [línea en blanco]
31. [línea en blanco]
32. "Proveer de conformidad,"
33. [línea en blanco]
34. "SERÁ JUSTICIA" (bold)
```

#### Formato general

**FUENTE ÚNICA DE VERDAD:**
`~/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/references/formato-escrito.md`
+ helper en
`~/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/scripts/formato_escrito.py`.

Para la PARTE NARRATIVA del escrito (fuera de la tabla), usar el helper:
- Times New Roman 12 pt, interlineado 1.5, justificado, sangría 1.25 cm
- Márgenes 3 cm izq, 2 cm der/sup/inf
- Títulos de sección (I, II, III, IV) con `titulo_seccion()`
- Encabezado del tribunal con `encabezado_tribunal()`
- Párrafo letrado con `parrafo_letrado()`
- Firma final con `firma()`

```python
import sys
sys.path.insert(0, "/Users/matiaschristiangarciacliment/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/scripts")
from formato_escrito import (
    nuevo_documento, titulo_principal, encabezado_tribunal,
    parrafo_letrado, titulo_seccion, parrafo, firma,
)

doc = nuevo_documento()
titulo_principal(doc, "PRACTICA LIQUIDACIÓN")
encabezado_tribunal(doc, "Sr. Juez:")
parrafo_letrado(doc, "MATÍAS CHRISTIAN GARCÍA CLIMENT", ", abogado, ...", "carátula", ", a V.S. digo:")
titulo_seccion(doc, "I. PRACTICA LIQUIDACIÓN")
parrafo(doc, "Vengo a practicar liquidación...")
# acá insertar la TABLA con doc.add_table() respetando los estilos de tabla descritos abajo
firma(doc)
```

**Para la TABLA de liquidación**: respetar el formato propio de tablas descrito
en la sección "Formato de la tabla" (Calibri 9pt, colores, bordes). Las tablas
NO usan Times New Roman — son la única excepción al formato general.

#### Formato de la tabla
Tabla profesional con estilos:
- **Encabezados de sección** (1. Crédito laboral, 2. Honorarios, 3. Tasa de justicia): fondo azul oscuro (#2F5496), texto blanco, Calibri 10pt bold
- **Subtítulos** (Honorarios parte actora, etc.): fondo celeste claro (#D6E4F0), Calibri 9pt bold
- **Filas de total**: fondo verde claro (#E2EFDA), Calibri 9pt bold
- **Datos**: Calibri 9pt normal
- **Fórmula de cálculo**: Calibri 8pt cursiva
- **Bordes**: exteriores gruesos azul (#2F5496 sz=12), internos horizontales sutiles grises (#BFBFBF sz=4), sin líneas verticales internas
- **Filas vacías separadoras**: altura 0.15cm entre secciones
- **Columnas**: 6 columnas con anchos [6.35, 2.2, 1.42, 0.5, 2.79, 2.16] cm
- **Alineaciones**: col 0 izq, col 1-3 centro, col 4-5 derecha

#### Estructura de la tabla

```
[HEADER azul] 1) Crédito laboral
[vacía]
[data] a) Crédito laboral al | fecha_accidente | | | | $capital
[data] b) Índice R.I.P.T.E. | periodo_ini | al | | periodo_fin | $capital_ajustado
[calc cursiva] (Cálculo = último RIPTE publicado...)
[TOTAL verde] Total al fecha_liq | | | | | $capital_ajustado
[vacía]
[HEADER azul] 2) Honorarios
[vacía]
[SUBHEADER celeste] Honorarios representación letrada de la parte actora
[vacía]
[data] Honorarios 1° instancia | 18,00% = XX.XX | U.M.A. | * | $valor_uma | $monto
[data] I.V.A. sobre honorarios | 21,00% | de | | $base | $iva
[data] Honorarios 2° instancia | 30,00% | de | | $base | $monto_2da
[data] I.V.A. sobre honorarios | 21,00% | de | | $base_2da | $iva_2da
[TOTAL verde] Total al fecha_liq | | | | | $total_actora
[vacía]
[SUBHEADER celeste] Honorarios representación letrada de la parte demandada
[vacía]
[data] Honorarios 1° instancia | 18,00% = XX.XX | U.M.A. | * | $valor_uma | $monto
[data] Honorarios 2° instancia | 30,00% | de | | $base | $monto_2da
[TOTAL verde] Total al fecha_liq | | | | | $total_demandada
[vacía]
[SUBHEADER celeste] Honorarios de perito con especialidad médica
[vacía]
[data] Honorarios | XX.XX | U.M.A. | * | $valor_uma | $monto
[data] I.V.A. sobre honorarios | 21,00% | de | | $base | $iva
[TOTAL verde] Total al fecha_liq | | | | | $total_perito
[vacía]
[HEADER azul] 3) Tasa de justicia
[vacía]
[data] Tasa de justicia | 03,00% | de | | $capital_ajustado | $tasa
[TOTAL verde] Total al fecha_liq | | | | | $tasa
```

Si las costas de TODAS las instancias son a cargo de la demandada, agregar al final:
```
[data merge] Costas de 1° instancia: 100% a cargo de la parte demandada
[data merge] Costas de 2° instancia: 100% a cargo de la parte demandada
```

Si alguna instancia tiene costas por su orden: NO poner ninguna línea de costas.

### Paso 5: Lógica de mitigación RIPTE

Solo aplica cuando:
1. La sentencia manda RIPTE (decreto 669/19)
2. La Cámara NO resolvió sobre el retraso en la publicación del RIPTE en su sentencia ni en su aclaratoria

Cálculo de mitigación:
- `meses_retraso` = meses entre último RIPTE publicado y fecha de liquidación
- `ripte_mitigado` = RIPTE de (fecha_accidente - meses_retraso)
- Tabla 2 usa `ripte_mitigado` en vez del RIPTE de la fecha del accidente

Ejemplo: accidente 10/2019, último RIPTE publicado 01/2026, liquidación 03/2026
- Retraso: 2 meses
- RIPTE mitigado: 08/2019 (10/2019 - 2 meses)

#### Cita jurisprudencial OBLIGATORIA en la sección II (medidas mitigatorias)

**SIEMPRE** incluir como primer párrafo de la sección II la siguiente cita (en cursiva el nombre del fallo):

> Que resulta pertinente señalar que en diversos fallos —ver autos *"BAREIRO, EVER RAMON c/ SWISS MEDICAL ART S.A. s/RECURSO LEY 27348"* (Expte. N° 25349/2023), entre otros— la Excma. Cámara Nacional de Apelaciones del Trabajo ha establecido expresamente que corresponde al juez de la causa adoptar las medidas necesarias para mitigar los efectos adversos derivados del retraso en la publicación de los índices R.I.P.T.E., reconociendo así la facultad-deber del magistrado de primera instancia de implementar los mecanismos compensatorios que resulten apropiados para preservar la integridad del crédito laboral.

Seguido del párrafo que explica la problemática del retraso, el mecanismo compensatorio propuesto (tomar RIPTE de `fecha_accidente - meses_retraso`) y el fundamento constitucional (art. 17 CN, principios protectorios, progresividad).

Esta cita es **obligatoria** — sin ella la sección II pierde sustento jurídico y puede ser rechazada. Modelo completo en `templates/modelo_liquidacion_ripte.docx`.

### Paso 6: Variantes según tipo de interés/actualización

**REGLA FUNDAMENTAL: Siempre hacer lo que diga la sentencia firme.** Las variantes documentadas abajo son los casos más comunes, pero la sentencia puede mandar cualquier combinación de tasas, índices, períodos y mecanismos. Si la sentencia manda algo que no encaja exactamente en ninguna variante, adaptar la tabla al caso concreto siguiendo la lógica de la sentencia. Por ejemplo: tasa activa BNA simple sin capitalización, CER + tasa pura, RIPTE solo hasta cierta fecha y después otra cosa, dos períodos con tasas distintas, etc. El skill debe ser flexible y no encasillarse.

Variantes documentadas como referencia:

---

#### Variante A: RIPTE puro (Decreto 669/19)

Ya documentada arriba (Paso 4, estructura de tabla). Ejemplo: González c/ Provincia ART.

- Ajuste: capital × (RIPTE final ÷ RIPTE inicial)
- Tabla 1 según sentencia + Tabla 2 con mitigación (si aplica)
- Honorarios en UMAs

---

#### Variante B: RIPTE + tasa de interés pura (Decreto 669/19 con tasa pura)

Algunas sentencias mandan RIPTE + un porcentaje anual de interés puro (ej: 6% anual). Ejemplo: Castro c/ Prevención ART.

**Estructura de la tabla - Sección 1) Crédito laboral:**

```
[data] a) Crédito laboral al | fecha_accidente | | | | $capital
[data] b) Índice R.I.P.T.E. | periodo_ini | al | | periodo_fin | $capital_ajustado_ripte
[calc] (Cálculo = último RIPTE publicado...)
[data] c) Tasa de interés pura del XX,XX% anual | fecha_ini | al | | fecha_fin | $intereses_puros
[calc] (Cálculo = N días transcurridos entre fecha_ini y fecha_fin * XX,XX% / 365% * crédito laboral $capital_ajustado_ripte)
[TOTAL] Total al fecha_liq (b + c) | | | | | $capital_ajustado_ripte + $intereses_puros
```

**Cálculo del interés puro:**
```python
from datetime import datetime
dias = (fecha_fin - fecha_ini).days
interes_puro = capital_ajustado_ripte * (tasa_anual / 100) * dias / 365
```

**Honorarios**: se calculan sobre el total (RIPTE + interés puro), siempre expresados en UMAs.

---

#### Variante C: Tasa Activa BNA capitalizable cada 6 meses

La sentencia manda tasa activa BNA con capitalización semestral (art. 770 CCyCN). Ejemplo: Osuna c/ Federación Patronal.

**Estructura de la tabla - Sección 1) Crédito laboral:**

Se calcula por períodos semestrales. En cada período se capitalizan los intereses al capital. Usar `cpacf_calcular_intereses` con `capitalizacion="180"` para cada semestre.

```
[data] Crédito laboral al | fecha_accidente | | | $capital
[data] Intereses art. 11, Ley 27.348 | fecha_ini_1 | al | fecha_fin_1 | $intereses_1
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[TOTAL] Total al | fecha_fin_1 | | | $capital + $intereses_1
[data] Intereses art. 11, Ley 27.348 | fecha_ini_2 | al | fecha_fin_2 | $intereses_2
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[TOTAL] Total al | fecha_fin_2 | | | $total_anterior + $intereses_2
... (repetir por cada semestre hasta la fecha de liquidación)
[data] Menos lo percibido en el incidente N°X | | | | -$monto_percibido  (si aplica)
[TOTAL] Total al fecha_liq | | | | $total_final
```

**Procedimiento:**
1. Dividir el período total en semestres de 6 meses desde la fecha del accidente
2. Para cada semestre, llamar a `cpacf_calcular_intereses` con:
   - `capital`: el total acumulado del semestre anterior
   - `fecha_inicial`: inicio del semestre (día siguiente al fin del anterior)
   - `fecha_final`: fin del semestre (6 meses después)
   - `tasa`: "2" (Tasa Activa Cartera general BNA - SIEMPRE es esta para cartera general)
   - `capitalizacion`: "0" (no capitalizar dentro del semestre, solo entre semestres)
3. Sumar intereses al capital para el siguiente semestre
4. El último período va desde el inicio del semestre hasta la fecha de liquidación
5. Incluir el link PDF que devuelve el CPACF en cada cálculo
6. Si hay montos ya percibidos, restarlos al final

**Honorarios**: se calculan sobre el total final, siempre expresados en UMAs.
**Tabla**: usa 5 columnas [concepto, fecha_ini, conector, fecha_fin, monto].
**No hay mitigación RIPTE** ni sección II de medidas.

---

#### Variante D: IPC + tasa de interés pura

La sentencia manda ajuste por IPC (Índice de Precios al Consumidor) + una tasa de interés pura anual. Ejemplo: Aguilar.

**Estructura de la tabla - Sección 1) Crédito laboral:**

```
[data] a) Crédito laboral al | fecha_accidente | | | $capital
[data] b) I.P.C. | fecha_ini | al | fecha_fin | $capital_ajustado_ipc
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[data] c) Tasa de interés pura del XX,XX% anual | fecha_ini | al | fecha_fin | $intereses_puros
[calc] (Cálculo = N días transcurridos entre fecha_ini y fecha_fin * XX,XX% / 365% * crédito laboral $capital_ajustado_ipc)
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[TOTAL] Total al fecha_liq (b + c) | | | | $capital_ajustado_ipc + $intereses_puros
```

**Procedimiento:**
1. Calcular ajuste IPC con `cpacf_calcular_intereses`:
   - `capital`: monto original
   - `tasa`: "12" (IPC/IPCNU hasta 31/10/15) o consultar cuál usar según período
   - Incluir link PDF del CPACF
2. Calcular interés puro sobre el capital ajustado por IPC:
   ```python
   dias = (fecha_fin - fecha_ini).days
   interes_puro = capital_ajustado_ipc * (tasa_anual / 100) * dias / 365
   ```
3. Total = capital ajustado IPC + interés puro

**Honorarios**: siempre expresados en UMAs.
**Tabla**: usa 5 columnas.
**Reserva de derechos**: reservar reliquidar con IPC actualizado cuando se publique.
**No hay mitigación RIPTE** pero SÍ puede haber reserva por IPC pendiente de publicación.

---

---

#### Variante E: CER puro

La sentencia manda ajuste por CER (Coeficiente de Estabilización de Referencia). Ejemplo: Méndez Montenegro.

**Estructura de la tabla - Sección 1) Crédito laboral:**

```
[data] a) Crédito laboral al | fecha_accidente | | | | $capital
[data] b) C.E.R. | fecha_ini | al | | fecha_fin | $capital_ajustado_cer
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[TOTAL] Total al fecha_liq | | | | | $capital_ajustado_cer
```

**Procedimiento:**
1. Calcular con `cpacf_calcular_intereses`:
   - `capital`: monto original
   - `tasa`: "9" (CER)
   - `fecha_inicial` y `fecha_final` según sentencia
2. Incluir link PDF del CPACF
3. No hay interés puro adicional (solo CER)

**Honorarios**: siempre expresados en UMAs.

---

#### Variante F: CER + cambio de tasa por Acta CNAT

La sentencia manda CER hasta cierta fecha y luego otra tasa (ej: Acta CNAT 2.658) desde esa fecha en adelante. Ejemplo: Segundo. Esto pasa cuando un Acta de Cámara cambia el régimen de intereses a partir de una fecha.

**Estructura de la tabla - Sección 1) Crédito laboral:**

```
[data] a) Crédito laboral al | fecha_accidente | | | | $capital
[data] b) C.E.R. | fecha_ini | al | | fecha_corte_acta | $capital_ajustado_cer
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[data] Acta C.N.A.T. N° 2.658 | fecha_ini_acta | al | | fecha_liq | $intereses_acta
[link] https://tasas.cpacf.org.ar/calculo_XXXX.pdf
[TOTAL] Total al fecha_liq (b + c) | | | | | $total
```

**Procedimiento:**
1. Primer período (CER): `cpacf_calcular_intereses` con tasa "9" hasta la fecha de corte del acta
2. Segundo período (Acta): `cpacf_calcular_intereses` con la tasa que corresponda al Acta, desde la fecha de corte hasta la liquidación. El capital para este segundo cálculo es el resultado del primer período.
3. Total = resultado CER + intereses del segundo período
4. Incluir links PDF de ambos cálculos

**Nota**: la fecha de corte entre un régimen y otro depende de lo que diga la sentencia o el Acta de Cámara. Ej: Acta 2.658 rige desde 01/01/2024.

---

### Honorarios: SIEMPRE en UMAs

Los honorarios SIEMPRE se expresan en UMAs, sin importar si la sentencia los regula en porcentaje o en UMAs directamente.

**Si la sentencia reguló en porcentaje** (ej: "18% sobre el monto de condena"):
1. `honorarios_pesos = porcentaje × monto_total_condena`
2. `umas = honorarios_pesos ÷ valor_uma`
3. Se presenta como: `18,00% = XX.XX | U.M.A. | * | $valor_uma | $honorarios_pesos`
   - El porcentaje va explícito para que se vea de dónde sale, seguido de "=" y la cantidad de UMAs

**Si la sentencia reguló en UMAs directamente** (ej: "93 UMAs"):
1. Usar la cantidad de UMAs directamente
2. Se presenta como: `93,00 | U.M.A. | * | $valor_uma | $honorarios_pesos`
   - Sin porcentaje, solo la cantidad de UMAs

Buscar siempre el valor UMA vigente de PJN (ley 27.423).

### Links CPACF en la tabla

Cuando se usa `cpacf_calcular_intereses`, el resultado incluye un `pdf_url`. Incluir ese link en una fila debajo del cálculo correspondiente como respaldo verificable. Formato: fila merge con el URL completo en Calibri 8pt.

## Datos del abogado (hardcodeados)

```
Nombre: MATÍAS CHRISTIAN GARCÍA CLIMENT
Inscripción: T° 97 F° 16 del CPACF
CUIT: 20-31380619-8
IVA: Responsable inscripto
Domicilio procesal: Av. Ricardo Balbín 2368, CABA
Zona notificación: 204
Email: matiasgarciacliment@gmail.com
Tel: 4-545-2488
Domicilio electrónico: 2031306198
```

## Constancia de inscripción

Siempre incluir la constancia ARCA como primera página del documento. La imagen está en:
`~/.claude/skills/practicar-liquidacion/templates/constancia_arca.jpeg`

Insertarla centrada, ancho 16cm.

## Formato de montos

Siempre formato argentino: puntos de miles, coma decimal.
- Correcto: $17.313.687,19
- Incorrecto: $17,313,687.19

Función Python para formatear:
```python
def fmt(n):
    s = f"{n:,.2f}".replace(',','X').replace('.',',').replace('X','.')
    return f"${s}"
```

## Interacción con el usuario

Al inicio preguntar:
1. Número de expediente y jurisdicción
2. Si ya tiene los archivos o hay que scrapear
3. Fecha de corte de la liquidación (default: hoy)

NO preguntar cosas que se pueden deducir de la sentencia (tasa, capital, fechas). Leer la sentencia y deducir todo automáticamente. Solo preguntar al usuario si hay ambigüedad.

## Fuentes de datos RIPTE

**FUENTE OFICIAL PRIMARIA**: PDF del Ministerio de Trabajo con serie histórica completa.
- URL portal: https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte
- **URL PDF directo** (patrón): `https://www.argentina.gob.ar/sites/default/files/ripte_[mes]_[año]-mdch.pdf`
  - Ejemplos: `ripte_febrero_2026-mdch.pdf`, `ripte_enero_2026-mdch.pdf`, `ripte_diciembre_2025-mdch.pdf`
  - El mes en minúsculas en español sin tildes, el año con 4 dígitos.
- El PDF contiene TODOS los índices desde julio 1994. Columnas: Período | Monto $ | Var % | **Índice Base 07/94=100** | **RIPTE Índice No Decreciente** (esta última es la oficial SRT — usar esta).

**Alternativas si el PDF del Ministerio falla**:
- https://ripte.agjusneuquen.gob.ar/riptes (AGJ Neuquén — atraso 1-2 meses)
- https://ikiwi.net.ar/indice-ripte/ (backup histórico)
- https://calcularsueldo.com.ar/ripte (otro backup)

## Fuente de datos UMA

- https://new.cpacf.org.ar/noticia/5201/valores-uma-pjn-ley-27423 (usar WebFetch)
