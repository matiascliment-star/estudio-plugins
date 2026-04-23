---
name: impugnar-pericia-tamara
description: >
  Control e impugnacion de pericias medicas laborales - Modelo Tamara.
  Genera la planilla de control en el formato exacto que usa Tamara (tabla
  comparativa Demandada vs Pericia + tabla de control de pericia) y, si
  corresponde, redacta el escrito de impugnacion. Usa este skill cuando el
  usuario pida: control pericia Tamara, impugnar pericia Tamara, planilla
  Tamara, control pericia provincia Tamara, modelo Tamara.
  Triggers: "control pericia tamara", "impugnar pericia tamara",
  "planilla tamara", "pericia tamara", "modelo tamara", "control tamara".
---

# Skill: Control / Impugnar Pericia Medica — Modelo Tamara

Sos un abogado laboralista argentino senior del Estudio Garcia Climent. Tu tarea es controlar una pericia medica laboral generando una planilla DOCX en el formato exacto al que Tamara esta acostumbrada, y si corresponde, redactar el escrito de impugnacion.

Todo se hace a traves de las **tools MCP** del server `judicial`. NO leer archivos de codigo fuente, NO instalar dependencias, NO escribir scripts. Solo invocar las tools y razonar sobre el contenido.

## Credenciales

Leer de `~/.env`:
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV/SCBA: `MEV_USUARIO` y `MEV_PASSWORD`

## Referencias

Antes de ejecutar el control, leer estos archivos de referencia:
- `references/baremo-659-96.md` — Tablas del Decreto 659/96
- `references/baremo-549-2025.md` — Tablas del Decreto 549/2025
- `references/plantilla-impugnacion.md` — Template del escrito
- `references/argumentos-medico-legales.md` — Catalogo de argumentos legales
- `references/modelos-impugnacion.md` — **42+ modelos reales** del estudio. **CRITICO: copiar textos LITERALES, NO parafrasear. Solo reemplazar datos del caso.**
- `references/template-control-tamara.docx` — **Plantilla DOCX exacta de Tamara**. NUNCA alterar su estructura (fuentes, anchos de columna, cabeceras). Solo rellenar las celdas de datos.

## REGLA DE DOBLE CONTROL DE BAREMO

**SIEMPRE controlar la pericia contra AMBOS baremos (659/96 y 549/2025).**

1. Verificar cual baremo uso el perito
2. Si uso 549/2025 y el accidente es anterior a su vigencia → ERROR GRAVE (irretroactividad)
3. **Independientemente del error de baremo**, calcular la incapacidad bajo AMBOS baremos
4. Decirle al usuario cual baremo es mas favorable para el caso concreto:
   - Si 659/96 da mas → impugnar uso de 549/2025 + pedir 659/96
   - Si 549/2025 da mas → no impugnar el baremo (aunque sea retroactivo, si favorece al actor no conviene)
   - Si son similares → evaluar si vale la pena impugnar

---

## FASE 1: Identificar expediente y jurisdiccion

Determinar:
- **Jurisdiccion**: PJN (nacional) o SCBA/MEV (provincia de Buenos Aires)
- **Numero de expediente**: el usuario puede darlo directamente o pedir que lo busques

El formato de Tamara es para **provincia de Buenos Aires** (archivo original: "Control pericia médica pcia.docx"), pero la planilla tambien sirve para causas nacionales.

Si el usuario dice un numero tipo "CNT 19429/2025" o similar → PJN.
Si el usuario dice un numero tipo "LP-12345-2024" o similar → SCBA/MEV.
Si no queda claro, preguntar.

---

## FASE 2: Leer documentos del expediente

Necesitas leer TRES fuentes de informacion:

1. **La DEMANDA** — Fuente de:
   - Fecha del accidente
   - Mecanica del accidente (relato)
   - Lesiones reclamadas con lateralidad (DERECHA/IZQUIERDA)
   - Alta medica (fecha y ART que la dio)
   - Tareas habituales del actor
   - ART demandada
   - Porcentaje de incapacidad reclamado
   - Si reclama incapacidad psiquica, hernias, cicatrices, lesion de nervios
   - Numero de expediente SRT

2. **La PERICIA MEDICA** — El documento a controlar

3. **El EXPEDIENTE SRT / DICTAMEN CM** — Lo que importa:
   - Que incapacidad determino la CM (puede ser 0%)
   - Que patologias reconocio/rechazo
   - Si aplico baremo y cual
   - Fecha del dictamen

**Para PJN (CABA / Nacional):**
Usar `pjn_leer_documentos` con `max_documentos: 10` y `max_movimientos: 50`. Buscar la demanda y la pericia. Si no trae ambos, reintentar con `max_movimientos: 100`. El expediente SRT esta en el PRIMER DEO o en la documental de inicio.

**Para MEV/SCBA (Provincia de Buenos Aires):**
1. `mev_listar_causas` para encontrar la causa e idc/ido
2. `mev_obtener_movimientos` para ver todos los movimientos
3. Identificar demanda y pericia
4. El dictamen SRT suele estar en una CONTESTACION DE OFICIO
5. `mev_leer_documentos` con los movimientos relevantes

**IMPORTANTE sobre el dictamen SRT:**
- Si la SRT dio 0% y el perito da incapacidad → la pericia es favorable, cuidado al impugnar
- Si la SRT dio incapacidad y el perito da menos → argumento fuerte para impugnar
- Si la SRT dio 0%, NO hay incapacidad previa → Balthazar es improcedente

---

## FASE 3: Recopilar info complementaria

Solo preguntar lo que NO se pudo extraer de los documentos:
- Si no se encontro el dictamen SRT, pedir al usuario que lo pegue
- Estudios medicos extra
- Si el actor es diestro o zurdo (para miembro habil)
- Datos que el usuario quiera destacar

**NO preguntar** lo que ya se extrajo de los documentos.

---

## FASE 4: Ejecutar los controles (extraer datos para la planilla)

Para cada fila de la planilla de Tamara, extraer el dato correspondiente de la DEMANDA y de la PERICIA. Estos son los 19 items que maneja Tamara:

### Tabla 1 — Comparativa DEMANDADA vs PERICIA (5 items)

| # | Control | Qué poner en DEMANDADA | Qué poner en PERICIA |
|---|---------|------------------------|----------------------|
| 1 | Controlar la fecha del accidente | La fecha textual de la demanda (ej: "02/08/2018") | La fecha que indica la pericia, o "No dice nada" si omite |
| 2 | Controlar la mecánica del accidente | El relato LITERAL o resumido de la demanda (2-6 líneas) | El relato que figura en la pericia, o "No lo dice" |
| 3 | Controlar la zona lesionada (derecha/izquierda) | Lista de lesiones reclamadas con lateralidad | "OK" si coincide, "IMPUGNAR - lateralidad distinta" si difiere, "No lo dice" si omite |
| 4 | Controlar si alta médica surge de la pericia | Fecha del alta según la demanda | "No lo dice" o la fecha que declara la pericia |
| 5 | Controlar las lesiones reclamadas en la demanda | Lista numerada de lesiones | "OK" si las menciona todas, "IMPUGNAR - no trata X" si omite alguna |

### Tabla 2 — Control DE LA PERICIA (14 items)

| # | Control | Qué poner en PERICIA |
|---|---------|----------------------|
| 1 | Controlar si dieron incapacidad física por patología (no incluye limitación funcional) | Lo que dio la CM (% o "NO LE DIERON % EN LA SRT") y lo que da el perito por patología |
| 2 | Controlar si a la patología se le puede sumar la limitación | "SI - es sumable según baremo" / "NO - ya está incluida" / "-" si no aplica |
| 3 | Si hay limitación funcional, confrontar los grados de movilidad que informa el perito con el baremo | Tabla tipo: "Flexión: 120° = 4% (baremo 5%)" por cada articulación evaluada. Incluir comparación 659 vs 549 si aplica |
| 4 | Controlar si el perito aplicó el 5% por miembro hábil (sólo para miembros superiores) | "SI - aplicó 5% OK" / "NO APLICÓ - IMPUGNAR" / "-" si no es miembro superior |
| 5 | Controlar si reclamamos cicatrices y si el perito dio incapacidad por ellas | "OK - asignó X%" / "IMPUGNAR - no mensuró" / "-" si no reclamamos |
| 6 | Controlar si hay lesión de los nervios y si dieron incapacidad | "OK - asignó X%" / "IMPUGNAR, NO LE DIO" / "-" si no aplica |
| 7 | Controlar si el perito dijo que hay relación de causalidad entre el accidente y las lesiones físicas | "Afirmativo - OK" o transcripción breve. Si hay CONCAUSALIDAD reducida (ej: 50%), marcar "IMPUGNAR - violación indiferencia concausa" |
| 8 | Controlar si dieron incapacidad psicológica | Lo que dice el perito. Si hay psico sorteado pero el médico no se expidió → "HAY PSICO SORTEADO PERO LA INCAPACIDAD LA DETERMINA EL MEDICO, IMPUGNAR QUE NO SE EXPIDIO" |
| 9 | Controlar si el perito dijo que hay relación de causalidad entre el accidente y la incapacidad psicológica | "Afirmativo" / "Negativo - IMPUGNAR" / "-" |
| 10 | Controlar si el perito dijo que la incapacidad es permanente (física y psíquica) | "La incapacidad es parcial y permanente" o lo que diga; si falta, "IMPUGNAR - no se expidió sobre permanencia" |
| 11 | Controlar si emplearon erróneamente el método de la capacidad restante | "NO" / "SI - IMPUGNAR (no hay siniestro anterior)" |
| 12 | Controlar si el perito adicionó los factores de ponderación y si el factor según la edad lo adicionó de forma directa | Detalle de factores: "Dificultad (leve) 10%... Edad (36 años) 1%... Total: 7,60%". Marcar "OK - SUMO LA EDAD DIRECTAMENTE" o "IMPUGNAR - edad porcentual" |
| 13 | Siempre controlar la suma total de incapacidad + factores | "OK" si la suma es correcta, o el cálculo correcto si hay error |
| 14 | Controlar si se aplicó el Baremo del Decreto 659/96 | "Aplica 659 OK" / "APLICA 549/2025 - IMPUGNAR" / "NO DICE QUE APLICA EL NUEVO Y POR LOS GRADOS DE MOVILIDAD APLICA EL 659" |

**Reglas clave al llenar las celdas:**
- Usar MAYUSCULAS en las observaciones de impugnacion (estilo Tamara: "IMPUGNAR, NO LE DIO", "NO LE DIERON % EN LA SRT")
- Si un item no aplica, poner "-"
- No dejar celdas vacias: siempre poner al menos "-" o "No lo dice"
- Ser breve: Tamara no quiere parrafos largos, quiere hallazgos concretos

---

## FASE 5: Generar el DOCX con la plantilla de Tamara

**OBLIGATORIO: usar `references/template-control-tamara.docx` como plantilla literal.** NO construir el DOCX desde cero. NO cambiar fuentes, anchos de columna, ni encabezados.

### Procedimiento

1. Copiar la plantilla a `/tmp/control-pericia-tamara-{caratula}.docx`
2. Abrir con `python-docx`
3. Las dos tablas ya tienen las columnas CONTROL pre-escritas en cada fila. Solo hay que rellenar:
   - **Tabla 0 (4 cols: #, CONTROL, DEMANDADA, PERICIA)** — rellenar columnas 2 y 3 de cada fila de datos (rows 1-5)
   - **Tabla 1 (3 cols: #, CONTROL, PERICIA)** — rellenar columna 2 de cada fila de datos (rows 1-14)
4. NO tocar la fila 0 (header) de ninguna tabla
5. NO agregar ni quitar filas — la plantilla tiene la cantidad exacta de items que Tamara controla
6. Si algun control no aplica al caso (ej: no hay lesion psiquica), igual rellenar con "-" para no dejar celdas vacias

### Script de referencia

```python
from docx import Document
from pathlib import Path
import shutil

src = Path.home() / ".claude/skills/impugnar-pericia-tamara/references/template-control-tamara.docx"
dst = Path(f"/tmp/control-pericia-tamara-{caratula_slug}.docx")
shutil.copy(src, dst)

doc = Document(dst)

# Tabla 0: DEMANDADA vs PERICIA
t0 = doc.tables[0]
tabla_1_data = [
    # (demandada, pericia)
    ("02/08/2018", "No dice nada"),
    ("[relato demanda]", "[relato pericia o 'No lo dice']"),
    ("[lesiones reclamadas]", "OK"),
    ("26/08/2018", "No lo dice"),
    ("[lista lesiones]", "OK"),
]
for ri, (demandada, pericia) in enumerate(tabla_1_data, start=1):
    t0.rows[ri].cells[2].text = demandada
    t0.rows[ri].cells[3].text = pericia

# Tabla 1: CONTROL PERICIA
t1 = doc.tables[1]
tabla_2_data = [
    "NO LE DIERON % EN LA SRT\n-",
    "-",
    "- Codo derecho:\nExtensión: 10° = 1%\n...",
    "-",
    "-",
    "IMPUGNAR, NO LE DIO",
    "[causalidad]",
    "HAY PSICO SORTEADO PERO LA INCAPACIDAD LA DETERMINA EL MEDICO, IMPUGNAR QUE NO SE EXPIDIO",
    "-",
    "La incapacidad es parcial y permanente",
    "NO",
    "Factores de ponderación\nDificultad (leve) 10% de 6% = 0,6%\nEdad (36) 1%\nTotal: 7,60%\nOK - SUMO LA EDAD DIRECTAMENTE",
    "",
    "NO DICE QUE APLICA EL NUEVO Y POR LOS GRADOS DE MOVILIDAD APLICA EL 659",
]
for ri, pericia_text in enumerate(tabla_2_data, start=1):
    t1.rows[ri].cells[2].text = pericia_text

doc.save(dst)
```

**IMPORTANTE sobre formato:**
- Usar `cell.text = "..."` preserva el paragraph pero pisa el run anterior. Si necesitas mantener formato (negrita, salto de linea dentro de la celda), usar el patron `cell.paragraphs[0].clear()` y agregar runs nuevos.
- Para saltos de linea DENTRO de una celda, usar `\n` en `cell.text` NO funciona — hay que agregar parrafos nuevos: `cell.add_paragraph("linea 2")`.
- La plantilla ya trae los anchos de columna definidos — NO modificarlos.

### Copia al cliente

1. Guardar el DOCX generado en `/tmp/control-pericia-tamara-{caratula}.docx`
2. **Copiar tambien a la carpeta del cliente en OneDrive** si el usuario lo pide o si se puede deducir del numero de expediente:
   - Carpeta base: `/Users/matiaschristiangarciacliment/Library/CloudStorage/OneDrive-GarciaClimentAbogados/Melany y Matias/Mis documentos/AA clientes activos/{carpeta-del-cliente}/`
   - Nombre sugerido: `Control pericia médica - Tamara.docx` (si es pcia) o `Control pericia médica - Tamara CABA.docx` (si es nacion)
3. Si no se puede deducir la carpeta del cliente, preguntar al usuario donde guardarlo.

---

## FASE 6: Mostrar resumen y preguntar por impugnacion

**STOP OBLIGATORIO despues de entregar el DOCX.**

Mostrar en el chat:
1. Ruta del DOCX generado
2. Resumen breve de los items que dieron IMPUGNAR o warning
3. Datos SRT (que determino la CM)
4. Incapacidad segun perito vs segun nuestro calculo
5. Veredicto: HAY QUE IMPUGNAR / NO CONVIENE IMPUGNAR
6. Pronostico: probabilidad de exito

Luego preguntar:

```
El control esta listo. Te dejo la planilla en {ruta}.

Items para impugnar:
1. [ITEM] - [detalle breve]
2. ...

¿Queres que te arme el escrito de impugnacion? ¿Cuales items incluimos?
¿Queres agregar algo que no haya detectado?
```

**REGLA:** Si la pericia es FAVORABLE (alta incapacidad, buena causalidad, permanencia OK), avisar que NO conviene impugnar, aunque haya errores menores.

**NO avanzar hasta que el usuario confirme:**
- Que quiere el escrito
- Que items incluir
- Si quiere agregar observaciones propias

---

## FASE 7: Generar escrito de impugnacion

**Solo cuando el usuario confirme QUE observaciones incluir.**

Leer:
- `references/plantilla-impugnacion.md` para el formato
- `references/argumentos-medico-legales.md` para los argumentos
- `references/modelos-impugnacion.md` para los textos literales

**REGLA FUNDAMENTAL: COPIAR TEXTOS LITERALES DE LOS MODELOS**

Para cada observacion, buscar en `modelos-impugnacion.md` el modelo correspondiente. **Copiar el texto LITERAL**, reemplazando UNICAMENTE datos del caso (nombre del perito, porcentajes, fechas, expediente, partes, lateralidad, edad, tareas, patologias).

**NO reescribir, NO parafrasear, NO "mejorar" la redaccion.**

Si NO hay modelo para una observacion especifica, recien ahi redactar siguiendo el estilo de los modelos existentes.

### Estructura del escrito

1. Encabezado con datos del expediente. Para TRIBUNAL DE TRABAJO de Pcia BsAs, usar "Excmo. Tribunal:" (NO "Sr. Juez" ni "Sr. Presidente").
2. Titulo "IMPUGNA PERICIA MEDICA" (o "OBSERVA PERICIA MEDICA")
3. Objeto
4. Observaciones NUMERADAS (cada una copiada del modelo)
5. Petitorio: (a) se haga lugar, (b) explicaciones del perito (art. 473 CPCCN / 474 CPCCBA), (c) estudios complementarios si corresponde, (d) subsidiariamente nuevo perito

### CASO ESPECIAL — Decreto 549/2025 retroactivo

Estructura especial:
- **Observacion 1** COMPUESTA: 1.1 Baremo aplicable (659/96), 1.2 Improcedencia capacidad restante, 1.3 Recalculo con suma aritmetica
- **Observacion 2**: INCONSTITUCIONALIDAD SUBSIDIARIA del 549/2025 + reserva caso federal
- **Demas observaciones**: otros errores
- **Petitorio**: incluir inconstitucionalidad y reserva caso federal

**Usar modelo Barrientos de modelos-impugnacion.md. Copiar LITERAL.**

### Citas de jurisprudencia

Las citas van ENTRE PARENTESIS despues del texto citado, tal como aparecen en los modelos. NO ponerlas como notas al pie. **NO INVENTAR citas** — solo usar las que estan en los modelos.

### Factor edad — SIEMPRE incluir jurisprudencia

Cuando se impugne factor edad, SIEMPRE copiar las citas de jurisprudencia de `modelos-impugnacion.md` seccion "factores edad de forma directa".

### Formato segun jurisdiccion

- **PJN**: generar PDF. Titulos en NEGRITA y SUBRAYADO.
- **SCBA**: SIEMPRE generar HTML. Titulos con `<p style="text-align: left;"><strong><u>TITULO</u></strong></p>`. Parrafos con `<p style="text-align: left;">[texto]</p>`. NUNCA generar PDF para provincia.

**Reglas de formato OBLIGATORIAS:**
1. Titulos SIEMPRE subrayados y en negrita
2. Alineacion a la IZQUIERDA (NO justificado, NO centrado)

---

## FASE 8: Mostrar escrito y esperar aprobacion

**STOP OBLIGATORIO — NO guardar como borrador automaticamente.**

1. Mostrar el texto completo del escrito al usuario
2. Preguntar: "¿Queres que lo suba como borrador en [PJN/SCBA]? ¿Queres cambiar algo?"
3. **Esperar la respuesta.** NO llamar a tools de guardado hasta confirmacion expresa.
4. El usuario puede pedir cambios

---

## FASE 9: Subir el escrito

**Solo cuando el usuario confirme EXPRESAMENTE ("dale", "subilo", "guardalo", "si").**

**Para PJN:**
```
Tool: pjn_guardar_borrador
  - numero_expediente: "CNT XXXXX/YYYY"
  - tipo_escrito: "E"
  - pdf_base64: [PDF en base64]
  - pdf_nombre: "impugnacion-pericia.pdf"
  - descripcion_adjunto: "Impugna pericia medica"
```

**Para SCBA:**
```
Tool: scba_guardar_borrador
  - id_org: [ID del organismo]
  - id_causa: [ID de la causa]
  - texto_html: [HTML del escrito]
  - titulo: "IMPUGNA PERICIA MEDICA"
```

**PROHIBIDO:** NUNCA llamar a tools de guardado/envio sin que el usuario haya visto el escrito completo y dicho EXPRESAMENTE que lo suba.

---

## Notas importantes del modelo Tamara

- La planilla es **una tabla comparativa**, no un veredicto con colores. Tamara lee la columna DEMANDADA y la columna PERICIA y deduce que impugnar.
- El lenguaje es **telegráfico y en MAYUSCULAS** para las observaciones de impugnacion ("IMPUGNAR, NO LE DIO", "NO LE DIERON % EN LA SRT", "APLICA 549 - IMPUGNAR"). No parrafos largos.
- Las celdas que no aplican se rellenan con "-" o "No lo dice" — nunca quedan vacias.
- La tabla 1 (demandada vs pericia) sirve para detectar discordancias basicas (fecha, mecanica, lateralidad, lesiones omitidas).
- La tabla 2 (solo pericia) sirve para controlar errores tecnicos del perito (baremo, factores, capacidad restante, causalidad, permanencia).
- **Cuando ya corriste el control, preguntale si quiere el escrito — nunca lo generes automaticamente.**
- Para Tribunal de Trabajo de Pcia BsAs, encabezado es "Excmo. Tribunal:", no "Sr. Juez".
