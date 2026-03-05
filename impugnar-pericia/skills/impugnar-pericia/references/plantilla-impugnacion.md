# Plantilla de Escrito de Impugnacion de Pericia Medica

## Formato PJN (texto plano para PDF)

```
{NOMBRE_ACTOR}, por derecho propio, con el patrocinio letrado del Dr. {ABOGADO}, T° {TOMO} F° {FOLIO} CPACF, constituyendo domicilio electronico en CUIL {CUIL_ABOGADO}, en los autos caratulados "{CARATULA}" (Expte. N° {NUMERO_EXPEDIENTE}), ante V.S. me presento y respetuosamente digo:

                    I. OBJETO

Que vengo por el presente a impugnar la pericia medica presentada por el Dr. {NOMBRE_PERITO}, de fecha {FECHA_PERICIA}, obrante a fs. {FOJAS}, por los fundamentos de hecho y de derecho que a continuacion se exponen.

                    II. FUNDAMENTOS

{OBSERVACIONES_NUMERADAS}

                    III. PETITORIO

Por todo lo expuesto a V.S. solicito:

1) Se tenga por impugnada la pericia medica del Dr. {NOMBRE_PERITO}.

2) Se intime al perito a brindar las explicaciones solicitadas en el plazo que V.S. estime corresponder, conforme lo dispuesto por el art. 473 del CPCCN.

{PETITORIO_ESTUDIOS}

{PETITORIO_NUEVO_PERITO}

Proveer de conformidad que,
SERA JUSTICIA.
```

## Formato SCBA (HTML para texto_html del borrador)

```html
<p><strong>{NOMBRE_ACTOR}</strong>, por derecho propio, con el patrocinio letrado del Dr. {ABOGADO}, T&ordm; {TOMO} F&ordm; {FOLIO} CALP, constituyendo domicilio electr&oacute;nico en CUIL {CUIL_ABOGADO}, en los autos caratulados &quot;{CARATULA}&quot; (Causa N&ordm; {NUMERO_CAUSA}), ante V.S. me presento y respetuosamente digo:</p>

<p style="text-align: center;"><strong>I. OBJETO</strong></p>

<p>Que vengo por el presente a impugnar la pericia m&eacute;dica presentada por el Dr. {NOMBRE_PERITO}, de fecha {FECHA_PERICIA}, por los fundamentos de hecho y de derecho que a continuaci&oacute;n se exponen.</p>

<p style="text-align: center;"><strong>II. FUNDAMENTOS</strong></p>

{OBSERVACIONES_HTML}

<p style="text-align: center;"><strong>III. PETITORIO</strong></p>

<p>Por todo lo expuesto a V.S. solicito:</p>

<p>1) Se tenga por impugnada la pericia m&eacute;dica del Dr. {NOMBRE_PERITO}.</p>

<p>2) Se intime al perito a brindar las explicaciones solicitadas en el plazo que V.S. estime corresponder, conforme lo dispuesto por el art. 474 del CPCCBA.</p>

{PETITORIO_ESTUDIOS_HTML}

{PETITORIO_NUEVO_PERITO_HTML}

<p>Proveer de conformidad que,</p>
<p>SER&Aacute; JUSTICIA.</p>
```

## Estructura de las observaciones numeradas

Cada observacion sigue este formato:

### Formato texto plano (PJN)

```
{N}. {TITULO_OBSERVACION}

{DESCRIPCION_DEL_ERROR}

{FUNDAMENTACION_LEGAL_Y_TECNICA}

{LO_QUE_SE_SOLICITA}
```

### Formato HTML (SCBA)

```html
<p><strong>{N}. {TITULO_OBSERVACION}</strong></p>

<p>{DESCRIPCION_DEL_ERROR}</p>

<p>{FUNDAMENTACION_LEGAL_Y_TECNICA}</p>

<p><em>{LO_QUE_SE_SOLICITA}</em></p>
```

## Ejemplos de observaciones tipicas

### Error en lateralidad

```
1. ERROR EN LA ZONA EVALUADA (LATERALIDAD)

El perito Dr. {PERITO} evaluo la {ZONA} {LADO_PERITO} del actor, cuando en realidad la lesion reclamada en la demanda - y acreditada por los estudios medicos obrantes en autos - corresponde a la {ZONA} {LADO_DEMANDA}.

Este error resulta manifiesto toda vez que el accidente sufrido por el actor el dia {FECHA} afecto su {ZONA} {LADO_DEMANDA}, conforme surge de la demanda (fs. {FOJAS_DEMANDA}), del certificado medico de parte (fs. {FOJAS_CERTIFICADO}) y de los estudios de imagen practicados (fs. {FOJAS_ESTUDIOS}).

Se solicita al perito que rectifique su dictamen evaluando la zona correcta ({ZONA} {LADO_DEMANDA}), realizando nuevo examen fisico y nuevas mediciones.
```

### Error en factores de ponderacion (edad)

```
2. ERROR EN EL CALCULO DEL FACTOR EDAD

El perito aplico el factor de ponderacion por edad de manera PORCENTUAL, cuando conforme el Decreto 659/96, el factor edad debe sumarse de forma ARITMETICA DIRECTA.

El actor tenia {EDAD} anos al momento del accidente. Conforme el baremo, corresponde adicionar {FACTOR_CORRECTO} puntos porcentuales (edad - 30 = {CALCULO}), y no {FACTOR_PERITO} como calculo el perito.

El metodo correcto es: "se le adiciona a la incapacidad el 1% por cada ano que exceda los 30 anos de edad" (Decreto 659/96, Tabla de Factores de Ponderacion). Esto significa que se suman puntos porcentuales directamente, no un porcentaje de la incapacidad.

Se solicita al perito que recalcule la incapacidad total corrigiendo el factor edad, lo que elevaria la incapacidad de {TOTAL_PERITO}% a {TOTAL_CORRECTO}%.
```

### Factores no aplicados sobre psiquica

```
3. OMISION DE FACTORES DE PONDERACION SOBRE INCAPACIDAD PSIQUICA

El perito aplico los factores de ponderacion (dificultad para tareas habituales y recalificacion) unicamente sobre la incapacidad fisica ({FISICA}%), omitiendo aplicarlos sobre la incapacidad psiquica ({PSIQUICA}%).

Los factores de ponderacion del Decreto 659/96 deben aplicarse sobre la TOTALIDAD de la incapacidad (fisica + psiquica), no solo sobre un componente. La razon es que tanto la limitacion fisica como la psiquica dificultan las tareas habituales del trabajador y requieren su recalificacion laboral.

Se solicita al perito que aplique los factores de dificultad y recalificacion sobre ambas incapacidades (fisica y psiquica), lo que incrementaria el total en aproximadamente {DIFERENCIA}%.
```

### Limitacion funcional con grados incorrectos

```
4. DISCORDANCIA ENTRE GRADOS DE MOVILIDAD Y PORCENTAJE ASIGNADO

El perito informo que la {ARTICULACION} del actor presenta {MOVIMIENTO} de {GRADOS_PERITO}, y asigno un {PORCENTAJE_PERITO}% de incapacidad por limitacion funcional.

Sin embargo, conforme la Tabla de Evaluacion de Incapacidades Laborales (Decreto 659/96), una {MOVIMIENTO} de {GRADOS_PERITO} en {ARTICULACION} corresponde a un {PORCENTAJE_BAREMO}% de incapacidad.

Se solicita al perito que adecue el porcentaje de incapacidad por limitacion funcional de {ARTICULACION} al valor que corresponde segun el baremo vigente ({PORCENTAJE_BAREMO}%).
```

### Signos objetivos de rodilla no considerados

```
5. OMISION DE VALORAR SIGNOS OBJETIVOS EN RODILLA

De los estudios de imagen obrantes en autos ({TIPO_ESTUDIO}, fs. {FOJAS}) surge la presencia de {HALLAZGO} en la rodilla {LADO} del actor. Estos hallazgos constituyen signos OBJETIVOS de patologia articular que ameritan incapacidad independiente conforme el Decreto 659/96.

Puntualmente, la {PATOLOGIA} encontrada corresponde a una incapacidad de {PORCENTAJE_BAREMO}% segun el baremo, la cual no fue considerada por el perito en su dictamen.

Se solicita al perito que incluya la incapacidad correspondiente a {PATOLOGIA} ({PORCENTAJE_BAREMO}%) conforme el baremo vigente.
```

### Causalidad no establecida

```
6. OMISION DE ESTABLECER RELACION DE CAUSALIDAD

El perito omitio establecer expresamente la relacion de causalidad entre las lesiones constatadas y el accidente de trabajo sufrido por el actor el dia {FECHA}.

Conforme la doctrina y jurisprudencia pacifica, el perito medico debe pronunciarse expresamente sobre el nexo causal entre el infortunio laboral y las lesiones detectadas (CNAT, Sala VII, "Gonzalez c/ Mapfre ART SA", 30/06/2015).

Se solicita al perito que se expida expresamente sobre la relacion de causalidad, indicando si las lesiones constatadas guardan relacion causal directa con el accidente de trabajo del {FECHA}.
```

### Baremo incorrecto (general)

```
7. UTILIZACION DE BAREMO INCORRECTO

El perito utilizo el baremo {BAREMO_USADO} para mensurar la incapacidad del actor, cuando corresponde utilizar exclusivamente la Tabla de Evaluacion de Incapacidades Laborales aprobada por Decreto 659/96 (y su modificatorio Decreto 49/14), conforme lo dispuesto por el art. 9 de la Ley 26.773 y el art. 8 de la Ley 24.557.

Se solicita al perito que re-mensure la incapacidad utilizando el baremo legalmente vigente (Decreto 659/96).
```

### Decreto 549/2025 aplicado retroactivamente (OBSERVACION COMPUESTA)

**IMPORTANTE**: Cuando el perito usa el Decreto 549/2025 retroactivamente, se genera una OBSERVACION COMPUESTA con 3 sub-puntos (baremo, capacidad restante, recalculo) + una OBSERVACION SUBSIDIARIA (inconstitucionalidad). Modelo:

```
OBSERVACION N° {N}: Aplicacion del baremo del Decreto 659/96 vigente al momento de la contingencia. Improcedencia de la formula de capacidad restante. {SI_SUPERA_UMBRAL: "Incapacidad que supera el {UMBRAL}% de la T.O."}

{N}.1. Baremo aplicable: Decreto 659/96.

Observo la pericia en traslado en tanto el/la expert@ utilizo para la determinacion de la incapacidad el baremo previsto en el Decreto N° 549/2025, cuando el baremo aplicable a la presente contingencia es el previsto en el Decreto N° 659/96, vigente al momento en que se produjo el siniestro laboral del actor ({FECHA_ACCIDENTE}). Se explica:

Es criterio pacifico y reiterado de la jurisprudencia que el baremo aplicable para la determinacion de la incapacidad es aquel vigente al momento de la primera manifestacion invalidante, esto es, la fecha del accidente o la fecha de toma de conocimiento de la enfermedad profesional. En el caso de autos, la contingencia se produjo el {FECHA_ACCIDENTE}, fecha en la cual se encontraba vigente el Anexo I del Decreto N° 659/96 (y sus modificatorias). El Decreto N° 549/2025, utilizado por el/la perit@, fue dictado con posterioridad y no resulta aplicable a hechos anteriores a su entrada en vigencia, en virtud del principio de irretroactividad de la ley (art. 7 del Codigo Civil y Comercial de la Nacion).

{SI_PERITO_RECONOCE_USO_549: "Notese que el/la propi@ perit@ reconoce en su respuesta que aplica 'los factores de ponderacion conforme el Decreto 549/2025 (Tabla de Evaluacion de Incapacidades Laborales), normativa vigente que sustituye al Decreto 659/96 y al Decreto 49/2014'. Sin embargo, que la normativa sea 'vigente' al momento de la pericia no la hace aplicable al caso, toda vez que lo que determina el baremo aplicable es la fecha de la contingencia, y no la fecha de la pericia."}

{N}.2. Consecuencia directa: improcedencia de la formula de capacidad restante (Balthazard).

La aplicacion erronea del Decreto 549/2025 no solo afecta los porcentajes asignados a cada limitacion funcional, sino que -fundamentalmente- condujo al/a la expert@ a aplicar la formula de capacidad restante (metodo de Balthazard) para combinar las distintas incapacidades parciales, metodologia que el nuevo baremo impone de manera generalizada pero que resulta improcedente bajo el regimen del Decreto 659/96 vigente al momento del siniestro. Se explica:

{DETALLE_CALCULO_PERITO_CON_CR}

La formula de capacidad restante tiene por finalidad evitar que la sumatoria de incapacidades provenientes de distintos eventos danosos sucesivos supere el 100% de la capacidad obrera total. El Decreto 659/96 la preve exclusivamente para la combinacion de incapacidades derivadas de siniestros diferentes y previos, y no para la combinacion de las distintas manifestaciones funcionales de un unico traumatismo. El Decreto 549/2025, en cambio, introduce una aplicacion generalizada de esta formula a todas las incapacidades parciales, incluso las derivadas del mismo hecho.

En el caso de autos, todas las lesiones y secuelas que padece el actor provienen de un unico y mismo accidente ocurrido el {FECHA_ACCIDENTE} ({MECANICA_ACCIDENTE}). {ARGUMENTO_UNICO_HECHO_Y_CAUSALIDAD}.

{SI_COMISION_MEDICA_DIO_0: "Mas aun: la propia Comision Medica Jurisdiccional, en su Dictamen Medico, determino que el actor no presentaba secuelas generadoras de incapacidad laboral por este siniestro. Si la Comision Medica considero 0% de incapacidad previa -razon por la cual se inicio la presente accion de revision-, no existe capacidad residual inferior al 100% sobre la cual corresponda aplicar el metodo de Balthazard."}

En sintesis: bajo el Decreto 659/96 -unico baremo aplicable- las incapacidades parciales derivadas del mismo accidente deben sumarse aritmeticamente, sin aplicacion de la formula de capacidad restante.

{N}.3. Incapacidad recalculada{SI_SUPERA_UMBRAL: ": supera el {UMBRAL}% de la T.O."}.

Conforme los valores de incapacidad parcial determinados por el/la propi@ perit@ -que no se cuestionan en cuanto a las secuelas constatadas en el examen fisico-, pero aplicando la suma aritmetica que corresponde bajo el Decreto 659/96, la incapacidad total se discrimina de la siguiente manera:

Incapacidades parciales (suma aritmetica):
{LISTADO_INCAPACIDADES_PARCIALES}
Subtotal incapacidad = {SUBTOTAL}%

Factores de ponderacion (conforme Decreto 659/96):
{LISTADO_FACTORES}
Total factores = {TOTAL_FACTORES}%

INCAPACIDAD TOTAL = {SUBTOTAL}% + {TOTAL_FACTORES}% = {TOTAL_FINAL}% de la T.O.

{SI_SUPERA_UMBRAL: "La correcta aplicacion del Decreto 659/96 con suma aritmetica arroja una incapacidad total que supera el umbral del {UMBRAL}% de la T.O., con las significativas consecuencias que ello importa en el marco del sistema de la Ley 24.557 y sus modificatorias (art. 14 inc. 2 a, prestacion de pago mensual complementaria). La reduccion operada por la erronea aplicacion de la formula de capacidad restante del Decreto 549/2025 no solo perjudica cuantitativamente al trabajador, sino que lo coloca por debajo de un umbral legal con consecuencias cualitativas determinantes."}

Por lo expuesto, se solicita al/a la expert@ que recalcule la totalidad de las incapacidades parciales aplicando el baremo del Decreto 659/96 y utilizando la suma aritmetica directa, prescindiendo de la formula de capacidad restante que solo procede bajo el Decreto 549/2025. A todo evento, se le hace saber que, aun cuando en lo personal no comparta el criterio, igualmente realice el calculo subsidiario a fin de que sea el juez de la causa quien determine, al momento de dictar sentencia, cual es el baremo y el metodo de calculo aplicable.
```

### Inconstitucionalidad del Decreto 549/2025 (planteo subsidiario)

```
OBSERVACION N° {N}: Subsidiariamente, para el caso de que V.E. considere aplicable el Decreto 549/2025: inconstitucionalidad. Planteo y reserva.

Sin perjuicio de lo expuesto en la Observacion N° {N_ANTERIOR} respecto del baremo aplicable, y para el supuesto de que V.E. considere aplicable el Decreto 549/2025, se plantea en este acto su inconstitucionalidad. Los fundamentos son los siguientes:

a) Violacion del principio de progresividad y no regresividad. El Decreto 549/2025 constituye una modificacion estructural del sistema de valoracion del dano laboral que reduce sistematicamente los porcentajes de incapacidad reconocidos a los trabajadores, en franca violacion del principio de progresividad consagrado en el art. 2.1 del Pacto Internacional de Derechos Economicos, Sociales y Culturales, el art. 26 de la Convencion Americana sobre Derechos Humanos y el art. 1 del Protocolo de San Salvador. La reduccion opera a traves de multiples mecanismos convergentes: exclusion de patologias prevalentes, eliminacion del dolor como factor incapacitante, reduccion drastica de porcentajes, imposicion de metodologias de calculo restrictivas -como la aplicacion generalizada de la formula de capacidad restante- y establecimiento de topes arbitrarios.

b) Reduccion drastica e injustificada de porcentajes y aplicacion generalizada de la capacidad restante. La tabla del Decreto 549/2025 no solo asigna porcentajes sustancialmente inferiores a los del Decreto 659/96 para las mismas limitaciones funcionales, sino que -a diferencia del regimen anterior- impone la formula de capacidad restante para la combinacion de todas las incapacidades parciales, incluso las derivadas del mismo siniestro. Este mecanismo opera como un factor de reduccion adicional que carece de justificacion medica y obedece exclusivamente al proposito de reducir el costo de las prestaciones dinerarias. {CUANTIFICAR_DIFERENCIA_EN_CASO_CONCRETO}.

c) Exceso reglamentario y violacion del principio de legalidad. El art. 8° inc. 3 de la Ley 24.557 delego al Poder Ejecutivo la elaboracion de una tabla de evaluacion de incapacidades, facultad estrictamente tecnica y acotada. Dicha delegacion no incluyo facultades para excluir patologias reconocidas por la ciencia medica, suprimir la consideracion del dolor, imponer la formula de capacidad restante para incapacidades del mismo origen, ni reducir porcentajes sin justificacion medica. El Poder Ejecutivo ha excedido las facultades reglamentarias del art. 99 inc. 2 de la Constitucion Nacional e incurrido en delegacion legislativa prohibida por el art. 76.

d) Aplicacion retroactiva y afectacion de derechos adquiridos. El actor sufrio su siniestro laboral el {FECHA_ACCIDENTE}, bajo la vigencia del Decreto 659/96. Aplicar el Decreto 549/2025 -dictado con posterioridad- constituye una violacion flagrante del principio de irretroactividad de las normas perjudiciales (art. 7 del CCyCN y art. 17 de la CN). El trabajador tiene derecho adquirido a ser evaluado conforme al regimen vigente al momento del hecho danoso, derecho incorporado a su patrimonio desde el momento mismo del siniestro.

e) Violacion del principio protectorio y la garantia de reparacion integral. El art. 14 bis de la CN consagra el principio protectorio como base del derecho laboral. La CSJN, desde "Aquino" en adelante, ha establecido que este principio impide normas regresivas que desmejoren la situacion del trabajador. En "Ascua" senalo que el objetivo reparador no se cumple si las indemnizaciones no guardan relacion con el dano real. El nuevo baremo viola frontalmente estos principios al establecer un sistema que sistematicamente subvalora el dano real sufrido por los trabajadores.

En virtud de lo expuesto, el Decreto 549/2025 resulta violatorio de los arts. 14 bis, 16, 17, 18, 28, 75 inc. 22, 76 y 99 incs. 2 y 3 de la Constitucion Nacional; del art. 2.1 del Pacto Internacional de Derechos Economicos, Sociales y Culturales; del art. 26 de la Convencion Americana sobre Derechos Humanos; y del art. 1 del Protocolo de San Salvador. Se deja planteada la reserva del caso federal (art. 14, Ley 48).
```

## Petitorio - Clausulas opcionales

### Pedido de estudios complementarios

```
{N}) Se ordene la realizacion de {TIPO_ESTUDIO} a fin de determinar con precision {OBJETIVO_ESTUDIO}, con cargo a la parte demandada.
```

Estudios tipicos:
- RMN de {zona} con contraste
- Electromiograma (EMG) de miembros {superiores/inferiores}
- Evaluacion psicologica / psicodiagnostico
- Radiografias comparativas bilateral
- TAC de {zona}
- Potenciales evocados

### Pedido de nuevo perito (subsidiario)

```
{N}) Subsidiariamente, para el caso de que las explicaciones del perito no resulten satisfactorias, se designe nuevo perito medico conforme lo previsto por el art. 473 in fine del CPCCN, a fin de que se practique nueva pericia medica que contemple las observaciones aqui formuladas.
```

Para SCBA, reemplazar "art. 473 in fine del CPCCN" por "art. 474 del CPCCBA".

### Petitorio especifico cuando se impugna por Decreto 549/2025

Cuando la observacion principal es la aplicacion retroactiva del 549/2025, el petitorio debe incluir:

```
1) Se tenga por contestado en tiempo y forma el traslado de la pericia medica.
2) Se corra traslado al/a la perit@ de las observaciones formuladas.
3) Se haga lugar a las observaciones y se ordene al/a la expert@ que practique el calculo de incapacidad aplicando el baremo del Decreto 659/96, con suma aritmetica de las incapacidades parciales y adicion directa del factor edad.
4) Se tenga presente el planteo de inconstitucionalidad del Decreto 549/2025 y la reserva del caso federal (art. 14, Ley 48).
```

## Notas de formato

### Para PJN
- El escrito se genera como texto plano y se convierte a PDF
- Se sube via `pjn_guardar_borrador` con `tipo_escrito: "E"` (ESCRITO)
- Descripcion del adjunto: "Impugna pericia medica"
- Nombre del PDF: "impugnacion-pericia.pdf"

### Para SCBA
- El escrito se genera como HTML
- Se sube via `scba_guardar_borrador` con el HTML en `texto_html`
- Titulo: "IMPUGNA PERICIA MEDICA"
- Tipo presentacion: "1" (Escritos)
