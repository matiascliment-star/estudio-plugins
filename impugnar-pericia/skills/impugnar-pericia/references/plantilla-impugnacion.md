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

### Baremo incorrecto

```
7. UTILIZACION DE BAREMO INCORRECTO

El perito utilizo el baremo {BAREMO_USADO} para mensurar la incapacidad del actor, cuando corresponde utilizar exclusivamente la Tabla de Evaluacion de Incapacidades Laborales aprobada por Decreto 659/96 (y su modificatorio Decreto 49/14), conforme lo dispuesto por el art. 9 de la Ley 26.773 y el art. 8 de la Ley 24.557.

Se solicita al perito que re-mensure la incapacidad utilizando el baremo legalmente vigente (Decreto 659/96).
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
