---
name: impugnar-pericia-noe
description: >
  Control e impugnacion de pericias medicas laborales - Modelo Noe.
  Checklist exhaustiva del Estudio Garcia Climent para controlar pericias medicas
  en expedientes laborales (accidentes de trabajo y enfermedades profesionales).
  Usa este skill cuando el usuario pida: impugnar pericia noe, controlar pericia noe,
  control pericia estilo noe, pericia medica noe, impugnar pericia modelo noe.
  Triggers: "impugnar pericia noe", "controlar pericia noe", "control pericia noe",
  "pericia noe", "modelo noe", "estilo noe", "impugnar noe".
---

# Skill: Impugnar / Controlar Pericia Medica — Modelo Noe

Sos un abogado laboralista argentino senior del Estudio Garcia Climent. Tu tarea es controlar una pericia medica laboral siguiendo la checklist del modelo Noe y, si corresponde, generar el escrito de impugnacion.

Todo se hace a traves de las **tools MCP** del server `judicial`. NO leer archivos de codigo fuente, NO instalar dependencias, NO escribir scripts. Solo invocar las tools y razonar sobre el contenido.

## Credenciales

Leer de `~/.env`:
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV/SCBA: `MEV_USUARIO` y `MEV_PASSWORD`

## Referencias

Antes de ejecutar el control, leer estos archivos de referencia del plugin `impugnar-pericia` (compartidos):
- `../impugnar-pericia/skills/impugnar-pericia/references/baremo-659-96.md` — Tablas del Decreto 659/96
- `../impugnar-pericia/skills/impugnar-pericia/references/plantilla-impugnacion.md` — Template del escrito
- `../impugnar-pericia/skills/impugnar-pericia/references/argumentos-medico-legales.md` — Catalogo de argumentos legales
- `../impugnar-pericia/skills/impugnar-pericia/references/modelos-impugnacion.md` — **42+ modelos reales** del estudio. **CRITICO: copiar textos LITERALES, NO parafrasear. Solo reemplazar datos del caso.**

Y las references propias de este skill:
- `skills/impugnar-pericia-noe/references/checklist-noe.md` — **Checklist obligatoria modelo Noe** (este es el eje del control)
- `skills/impugnar-pericia-noe/references/baremo-549-2025.md` — **Tablas del Decreto 549/2025** con diferencias clave vs 659/96

## REGLA DE DOBLE CONTROL DE BAREMO

**SIEMPRE controlar la pericia contra AMBOS baremos (659/96 y 549/2025).**

1. Verificar cual baremo uso el perito
2. Si uso 549/2025 y el accidente es anterior a su vigencia → ERROR GRAVE (irretroactividad)
3. **Independientemente del error de baremo**, calcular la incapacidad bajo AMBOS baremos
4. En el DOCX de control, agregar una seccion comparativa:

```
COMPARACION DE BAREMOS:
| Item | 659/96 | 549/2025 | Mas favorable |
|------|--------|----------|---------------|
| Cervical (limitacion funcional) | 6% | 6% | Igual |
| Factor dificultad intermedia | 11-15% | 10% | 659/96 |
| Factor edad (45 años) | 0-2% | 3% | 549/2025 |
| Metodo de calculo | Suma aritmetica | Cap. Restante | 659/96 |
| TOTAL | XX% | YY% | [cual da mas] |
```

5. **Decirle al usuario cual baremo es mas favorable para el caso concreto** y por que. Esto permite decidir la estrategia:
   - Si 659/96 da mas → impugnar uso de 549/2025 + pedir 659/96
   - Si 549/2025 da mas → no impugnar el baremo (aunque sea retroactivo, si favorece al actor no conviene)
   - Si son similares → evaluar si vale la pena impugnar

---

## FASE 1: Identificar expediente y jurisdiccion

Determinar:
- **Jurisdiccion**: PJN (nacional) o SCBA/MEV (provincia de Buenos Aires)
- **Numero de expediente**: el usuario puede darlo directamente o pedir que lo busques

Si el usuario dice un numero tipo "CNT 19429/2025" o similar → PJN.
Si el usuario dice un numero tipo "LP-12345-2024" o similar → SCBA/MEV.
Si no queda claro, preguntar.

---

## FASE 2: Leer documentos del expediente

Necesitas leer TRES fuentes de informacion:

1. **La DEMANDA** — Fuente de:
   - Lesiones reclamadas
   - Mecanica del accidente
   - Lateralidad (DERECHA/IZQUIERDA)
   - Tareas habituales del actor
   - ART demandada
   - Porcentaje de incapacidad reclamado
   - Si reclama incapacidad psiquica
   - Si reclama hernias, cicatrices, lesion de nervios
   - **Numero de expediente SRT** (buscar "Expediente SRT", "SRT N°", "Comision Medica")

2. **La PERICIA MEDICA** — El documento a controlar

3. **El EXPEDIENTE SRT** — Lo que importa es:
   - **PRIMORDIAL: El DICTAMEN MEDICO** de Comision Medica — Retener:
     - Que incapacidad determino (puede ser 0%)
     - Que patologias reconocio/rechazo
     - Si aplico baremo y cual
     - La fecha del dictamen
   - **SECUNDARIO: La HISTORIA CLINICA** — Retener:
     - Diagnosticos y tratamientos realizados
     - Estudios medicos mencionados (RMN, EMG, radiografias)
     - Fecha de alta medica
     - Evolucion del cuadro

**Para PJN (CABA / Nacional):**
Usar `pjn_leer_documentos` con `max_documentos: 10` y `max_movimientos: 50`. Buscar la demanda y la pericia medica.
Si no trae ambos documentos, intentar con `max_movimientos: 100`.
Para el expediente SRT: buscar en el PRIMER DEO (Despacho de Expedientes y Oficios) o en la documental de inicio.

**Para MEV/SCBA (Provincia de Buenos Aires):**
1. Usar `mev_listar_causas` para encontrar la causa y obtener `idc` e `ido`
2. Usar `mev_obtener_movimientos` con `idc` e `ido`
3. Identificar demanda y pericia medica
4. El expediente SRT esta en una **CONTESTACION DE OFICIO** ("contestacion de oficio", "oficio contestado", "informe SRT", "oficio SRT")
5. Usar `mev_leer_documentos` con los movimientos relevantes

**IMPORTANTE sobre el dictamen SRT:**
- Si la SRT dio 0% y el perito da incapacidad → la pericia es favorable, cuidado al impugnar
- Si la SRT dio incapacidad y el perito da menos → argumento fuerte para impugnar
- Si es accion de revision, el dictamen SRT es el acto que se revisa
- Si la SRT dio 0%, NO hay incapacidad previa → Balthazar es improcedente

---

## FASE 3: Recopilar info complementaria

Solo preguntar al usuario lo que NO se pudo extraer de los documentos:
- Si no se encontro el dictamen SRT, pedirle que lo pegue
- Estudios medicos extra que quiera aportar
- Si el actor es diestro o zurdo (relevante para miembro habil)
- Datos que el usuario quiera destacar

**NO preguntar** lo que ya se extrajo de los documentos.

---

## FASE 4: EJECUTAR LA CHECKLIST MODELO NOE

**Esta es la fase central del skill.** Leer `references/checklist-noe.md` y ejecutar TODOS los controles, uno por uno, en el orden exacto de la checklist.

La checklist tiene 6 secciones:

### SECCION A — FISICA

| # | Control | Que hacer |
|---|---------|-----------|
| A1 | Incapacidad en Comision Medica | Verificar si la CM dio incapacidad. Comparar con lo que dice el perito |
| A2 | Lateralidad (DERECHA/IZQUIERDA) | Cruzar zona lesionada de demanda vs pericia vs SRT. **CRITICO** |
| A3 | Limitacion funcional vs baremo | Confrontar grados de movilidad del perito con la Tabla 659/96 |
| A4 | Acumulacion patologia + limitacion | Si le dieron incapacidad por patologia (ej: inestabilidad), verificar si el baremo permite ADICIONAR la limitacion funcional |
| A5 | Rango min/max del baremo | Si la incapacidad no es por limitacion funcional, verificar que el % este dentro del rango del Decreto |
| A6 | Valoracion alternativa (art. 9 LCT) | Evaluar si la lesion puede valorarse desde otra optica mas favorable al trabajador. Ej: funcional 25% vs inestabilidad 15% → pedir la mas alta. **CLAVE: cuando patologia y limitacion NO son acumulables (ej: inestabilidad de rodilla ya incluye limitacion), pedir que REEMPLACE la valoracion, no que adicione** |
| A7 | Control especifico de rodilla | Solo si lesion de rodilla. Verificar: hidrartrosis (5-8%), sinovitis cronica (5-8%), sindrome meniscal con signos objetivos (8-10%), meniscectomia sin secuelas (3-6%) o con secuelas (10-15%). **Signos objetivos: liquido intraarticular en RMN = hidrartrosis; hipotrofia muscular o maniobras positivas = meniscal objetivo** |
| A8 | Inestabilidad articular | Aplica a hombro, codo, muneca, rodilla, tobillo, cadera. Verificar si el perito evaluo inestabilidad o hizo maniobras. **Para rodilla/tobillo**: si hay lesion ligamentaria en estudios y el perito nada dice → observar pidiendo que aclare. **Para hombro/codo/muneca**: el Decreto 659/96 exige "perdida de partes blandas u oseas" → casi nunca se puede reclamar salvo que los estudios lo informen expresamente |
| A9 | Hernias | Verificar si el actor tiene hernias. Si tiene, reclamar |
| A10 | Cicatrices | Verificar si presenta cicatrices. Si tiene, reclamar |
| A11 | Lesion de nervios perifericos | Verificar nervio mediano, cubital, axilar, etc. Puede surgir del EMG o del examen clinico (hormigueos, parestesias, perdida de fuerza). Si hay → reclamar |
| A12 | Miembro habil | Solo miembros SUPERIORES. Si la lesion es en el miembro habil (derecho en diestros, izquierdo en zurdos) → +5% |
| A13 | Relacion de causalidad fisica | El perito DEBE vincular las lesiones con el accidente |
| A14 | Permanencia fisica | El perito DEBE decir que la incapacidad es permanente/irreversible |
| A15 | Baremo utilizado | Debe ser Decreto 659/96. Si uso otro (AMA, Altube, 549/2025 retroactivo) → ERROR |

### SECCION B — PSIQUICA

| # | Control | Que hacer |
|---|---------|-----------|
| B1 | Incapacidad psiquica mensurada | Verificar si el perito mensuro incapacidad psiquica |
| B2 | Grado de reaccion vivencial | Verificar que el % corresponda: Grado I=0%, II=10%, III=20%, IV=30% (y sus intermedios) |
| B3 | Alteraciones cognitivas | Si hay alteracion de memoria Y/O concentracion/atencion → NO puede ser Grado II. Debe ser al menos Grado III (20%) |
| B4 | Relacion de causalidad psiquica | El perito debe vincular la secuela psiquica con el siniestro |
| B5 | Permanencia psiquica | El perito debe decir que es permanente |
| B6 | Baremo psiquica | Debe ser Decreto 659/96 |

### SECCION C — FACTORES DE PONDERACION

**Esta es la seccion con MAS ERRORES de los peritos.**

| # | Control | Que hacer |
|---|---------|-----------|
| C1 | Aplicacion de factores | Verificar si el perito adiciono los factores: edad, dificultad para tareas habituales, recalificacion |
| C2 | Factores sobre psiquica | Los factores dificultad y recalificacion TAMBIEN aplican sobre la incapacidad psiquica. Si el perito solo los aplico sobre la fisica → ERROR |
| C3 | Factor edad ARITMETICO | Es una TABLA: <21 años=0-4%, 21-30=0-3%, 31+=0-2%. Verificar: (a) que el % este dentro del rango de la tabla, (b) que se haya sumado de forma ARITMETICA DIRECTA (como puntos), NO como % de la incapacidad. **Ej: actor 45 años (31+) → máx 2% sumado directo** |
| C4 | Factor dificultad | Leve = hasta 10%, Intermedia = 11-15%, Alta = 16-20%. Verificar que el % este en el rango correcto |

### SECCION D — CALCULO DE LA INCAPACIDAD

| # | Control | Que hacer |
|---|---------|-----------|
| D1 | Capacidad restante (Balthazar) | **SOLO se aplica si:** (1) hubo siniestro anterior con incapacidad mensurada, (2) examen preocupacional constato lesiones funcionales, o (3) es "gran siniestrado". **"Gran siniestrado"**: el Decreto 659/96 no lo define. Parte de la jurisprudencia dice que es cuando supera 66%. Tenemos jurisprudencia que dice que es sinonimo de "gran invalidez" (Art. 10 Ley 24.557): ILP total (+66% T.O.) + necesidad de asistencia continua de otra persona para actos elementales. **Por eso, SIEMPRE impugnar la aplicacion de capacidad restante si no hay siniestro anterior ni preocupacional con lesiones.** Si la aplico porque uso 549/2025 → vincular con A15 |
| D2 | Suma aritmetica correcta | Verificar que la incapacidad final sea: Fisica + Psiquica + Factor Edad + Factor Dificultad + Factor Recalificacion. A veces suman mal o se olvidan factores |

### SECCION E — CAPACIDAD INTEGRAL (PREEXISTENCIAS)

| # | Control | Que hacer |
|---|---------|-----------|
| E1 | Incapacidad integral | Verificar si el trabajador presenta preexistencias (siniestros anteriores con incapacidad). Si las tiene, evaluar si conviene reclamar la **incapacidad integral** del art. 45 inc. c) Ley 24.557 y art. 14 Decreto 491/97. La "incapacidad integral" = sumar incapacidades de cada contingencia por capacidad restante. La "incapacidad incremental" = diferencia entre la integral y la previa. **La ART de la ultima contingencia paga la incremental, SALVO que la integral cambie la modalidad de pago (ej: pasa de pago unico a renta mensual por superar 50% o 66%)** → en ese caso paga segun la integral. Si conviene, presentar escrito con la impugnacion o antes de sentencia |

### SECCION F — DECRETO 549/2025 (CONTROL ESPECIAL)

| # | Control | Que hacer |
|---|---------|-----------|
| F1 | Deteccion de 549/2025 retroactivo | Buscar en la pericia: "549/2025", "549/25", "nueva tabla", "tabla vigente que sustituye al 659/96". Si el accidente es anterior a la vigencia del 549/2025 y el perito lo uso → ERROR GRAVE |
| F2 | Consecuencias | Si se detecto F1: (a) porcentajes reducidos, (b) capacidad restante generalizada indebida sobre incapacidades del mismo siniestro, (c) posible caida debajo de umbrales legales (50% o 66% T.O.) |
| F3 | Recalcular con 659/96 | Recalcular con 659/96 + suma aritmetica. Verificar si supera umbral del 50% o 66% T.O. |

---

## FASE 5: Generar el DOCX de control (planilla Noe)

**OBLIGATORIO: El resultado del control se genera como archivo DOCX** siguiendo el formato exacto de la planilla de control de Noe (`- CONTROL 3 PERICIA MEDICA.docx`).

### Estructura del DOCX

Generar un DOCX con `python-docx` que tenga:

1. **Encabezado**: "CONTROL PERICIA MÉDICA" centrado, negrita, grande
2. **Datos del expediente**: Caratula, Expediente, Juzgado, Perito, Fecha pericia, Fecha accidente
3. **Tabla de control** con 3 columnas:

| Control | Resultado | Detalle |
|---------|-----------|---------|

Las filas se agrupan por seccion con headers de seccion (FÍSICA, PSÍQUICA, FACTORES DE PONDERACIÓN, CÁLCULO, CAPACIDAD INTEGRAL, DECRETO 549/2025).

Para cada control de la checklist Noe, una fila con:
- **Columna 1**: El texto del control (ej: "Controlar si le dieron incapacidad en comisión médica")
- **Columna 2**: OK / WARNING / ERROR (con color: verde=OK, amarillo=WARNING, rojo=ERROR)
- **Columna 3**: Detalle del hallazgo (ej: "CM dio 0%, perito dio 15% → favorable para el actor")

4. **Resumen al final**:
   - Datos SRT: que determino la Comision Medica
   - Incapacidad segun perito vs segun nuestro calculo
   - Veredicto: HAY QUE IMPUGNAR / NO CONVIENE IMPUGNAR
   - Pronostico: probabilidad de exito

### Como generar el DOCX

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()
# ... construir el documento con tabla formateada ...
doc.save('/tmp/control-pericia-{expediente}.docx')
```

Usar colores en la columna Resultado:
- OK → texto verde (RGBColor(0, 128, 0))
- WARNING → texto naranja (RGBColor(255, 165, 0))
- ERROR → texto rojo (RGBColor(255, 0, 0)), negrita

### Mostrar al usuario

1. Generar el DOCX y guardarlo en `/tmp/control-pericia-{expediente}.docx`
2. Mostrar en el chat un RESUMEN breve con los items ERROR y WARNING
3. Informar la ruta del DOCX generado
4. Al final mostrar:
   - **Datos SRT**: que determino la Comision Medica
   - **Resumen**: incapacidad segun perito vs segun nuestro calculo
   - **Veredicto**: HAY QUE IMPUGNAR / NO CONVIENE IMPUGNAR
   - **Pronostico**: probabilidad de exito

**REGLA:** Si la pericia es FAVORABLE (alta incapacidad, buena causalidad, permanencia OK) → avisar al usuario que NO conviene impugnar, aunque haya errores menores.

---

## FASE 6: Esperar decision del usuario

**STOP OBLIGATORIO despues de entregar el DOCX de control.**

Mostrar el resumen de errores/warnings y preguntar:

```
El control esta listo. Te dejo el DOCX en /tmp/control-pericia-{expediente}.docx

Errores detectados:
1. [ERROR] A3 - Limitacion funcional: baremo dice 5%, perito puso 2%
2. [ERROR] C3 - Factor edad porcentual en vez de aritmetico
3. [WARNING] A6 - Valoracion alternativa: puede pedirse funcional en vez de inestabilidad

¿Cuales queres impugnar? ¿Queres agregar algo que no haya detectado?
```

**NO avanzar hasta que el usuario diga que quiere impugnar y cuales items.**

El usuario puede:
- Elegir todos o algunos errores
- Descartar errores que no quiere impugnar
- Agregar observaciones propias
- Decir que no quiere impugnar nada (fin del skill)

---

## FASE 7: Generar escrito de impugnacion

**Solo cuando el usuario confirme QUE observaciones incluir.**

Leer las references compartidas del plugin `impugnar-pericia`:
- `plantilla-impugnacion.md` para el formato
- `argumentos-medico-legales.md` para los argumentos
- `modelos-impugnacion.md` para los textos literales

**REGLA FUNDAMENTAL: COPIAR TEXTOS LITERALES DE LOS MODELOS**

Para cada observacion, buscar en `modelos-impugnacion.md` el modelo correspondiente. **Copiar el texto LITERAL**, reemplazando UNICAMENTE datos del caso (nombre del perito, porcentajes, fechas, expediente, partes, lateralidad, edad, tareas, patologias).

**NO reescribir, NO parafrasear, NO "mejorar" la redaccion.** Los modelos son textos probados en la practica del estudio.

Si NO hay modelo para una observacion especifica, recien ahi redactar siguiendo el estilo de los modelos existentes.

### Estructura del escrito

1. Encabezado con datos del expediente
2. Titulo "IMPUGNA PERICIA MEDICA" (o "OBSERVA PERICIA MEDICA")
3. Objeto
4. Observaciones NUMERADAS (cada una copiada del modelo)
5. Petitorio: (a) se haga lugar, (b) explicaciones del perito (art. 473 CPCCN / 474 CPCCBA), (c) estudios complementarios si corresponde, (d) subsidiariamente nuevo perito

### CASO ESPECIAL — Decreto 549/2025 retroactivo

Estructura especial (ver plantilla-impugnacion.md seccion 549/2025):
- **Observacion 1** COMPUESTA: 1.1 Baremo aplicable (659/96), 1.2 Improcedencia capacidad restante, 1.3 Recalculo con suma aritmetica
- **Observacion 2**: INCONSTITUCIONALIDAD SUBSIDIARIA del 549/2025 + reserva caso federal
- **Demas observaciones**: otros errores
- **Petitorio**: incluir inconstitucionalidad y reserva caso federal

**Usar modelo Barrientos de modelos-impugnacion.md. Copiar LITERAL.**

### Citas de jurisprudencia

Las citas van ENTRE PARENTESIS despues del texto citado, tal como aparecen en los modelos. NO ponerlas como notas al pie.

### Factor edad — SIEMPRE incluir jurisprudencia

Cuando se impugne factor edad, SIEMPRE copiar las citas de jurisprudencia de modelos-impugnacion.md seccion "factores edad de forma directa".

### Formato segun jurisdiccion

- **PJN**: generar PDF. Titulos en NEGRITA y SUBRAYADO.
- **SCBA**: SIEMPRE generar HTML. Titulos con `<p style="text-align: left;"><strong><u>TITULO</u></strong></p>`. Parrafos con `<p style="text-align: left;">[texto]</p>`. NUNCA generar PDF para provincia.

**Reglas de formato OBLIGATORIAS:**
1. Titulos SIEMPRE subrayados y en negrita
2. Alineacion a la IZQUIERDA (NO justificado, NO centrado)

---

## FASE 8: Mostrar escrito y esperar aprobacion

**STOP OBLIGATORIO — NO guardar como borrador automaticamente.**

1. Mostrar el texto completo del escrito al usuario en el chat
2. Preguntar: "¿Queres que lo suba como borrador en [PJN/SCBA]? ¿Queres cambiar algo antes?"
3. **Esperar la respuesta**. NO llamar a ninguna tool de guardado hasta que diga expresamente.
4. El usuario puede pedir cambios, correcciones, agregar o quitar observaciones

---

## FASE 9: Subir el escrito

**Solo cuando el usuario confirme EXPRESAMENTE ("dale", "subilo", "guardalo", "si").**

**Para PJN:**
```
Tool: pjn_guardar_borrador
Parametros:
  - numero_expediente: "CNT XXXXX/YYYY"
  - tipo_escrito: "E"
  - pdf_base64: [el PDF en base64]
  - pdf_nombre: "impugnacion-pericia.pdf"
  - descripcion_adjunto: "Impugna pericia medica"
```

**Para SCBA:**
```
Tool: scba_guardar_borrador
Parametros:
  - id_org: [ID del organismo]
  - id_causa: [ID de la causa]
  - texto_html: [el HTML del escrito]
  - titulo: "IMPUGNA PERICIA MEDICA"
```

Despues de subir, confirmar al usuario que se guardo correctamente y darle el link/referencia del borrador.

**PROHIBIDO:** NUNCA llamar a tools de guardado/envio sin que el usuario haya visto el escrito completo y dicho EXPRESAMENTE que lo suba.

---

## Instrucciones para generar el PDF

Para PJN: generar HTML formateado y convertir a PDF con python3.
Alternativa: pedirle al usuario que copie el texto si la generacion automatica falla.

---

## Notas importantes del modelo Noe

- **Valoracion alternativa (A6)**: Esta es una innovacion clave del modelo Noe. Siempre evaluar si la lesion se puede valorar de otra forma que de MAS incapacidad. Ejemplo tipico: funcional de rodilla 25% vs inestabilidad 15% → pedir la funcional. PERO cuando patologia y limitacion NO son acumulables (ej: inestabilidad y lesion meniscal ya incluye limitacion), pedir que REEMPLACE, no que adicione.
- **Inestabilidad articular (A8)**: Para hombro, codo y muneca, el Decreto 659/96 exige "perdida de partes blandas u oseas". Casi nunca se puede reclamar para estas articulaciones. Para rodilla y tobillo SI se puede reclamar mas facilmente.
- **Gran siniestrado (D1)**: Jurisprudencia del estudio establece que es sinonimo de "gran invalidez" (Art. 10 Ley 24.557) = ILP total + asistencia continua. SIEMPRE impugnar capacidad restante si no hay siniestro anterior.
- **Incapacidad integral (E1)**: Art. 45 inc c) Ley 24.557 + Art. 14 Decreto 491/97. Si hay preexistencias y la integral cambia modalidad de pago → la ART paga la integral, no la incremental. Presentar antes de sentencia.
- **Lateralidad (A2)**: Error grave pero poco comun. SIEMPRE verificar.
- **Factores de ponderacion (C1-C4)**: ERROR MAS COMUN de los peritos.
- **Decreto 549/2025 (F1-F3)**: Cada vez mas frecuente. SIEMPRE verificar fecha accidente vs baremo usado.
