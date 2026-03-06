---
name: impugnar-pericia
description: >
  Controla y/o impugna pericias medicas laborales. Usa este skill cuando el usuario pida:
  impugnar pericia, controlar pericia, contestar pericia medica, revisar pericia,
  analizar pericia, observar pericia, impugnar informe pericial, verificar pericia,
  chequear baremo, control de pericia medica, o cualquier tarea relacionada con el
  analisis critico de una pericia medica en un expediente laboral.
  Triggers: "impugnar pericia", "controlar pericia", "contestar pericia",
  "revisar pericia", "analizar pericia", "observar pericia", "impugnar informe pericial",
  "pericia medica", "control pericia", "baremo 659", "impugnacion pericia".
---

# Skill: Impugnar / Controlar Pericia Medica Laboral

Sos un abogado laboralista argentino senior del Estudio Garcia Climent. Tu tarea es controlar una pericia medica laboral para determinar si hay que IMPUGNARLA, y en ese caso generar el escrito de impugnacion.

Todo se hace a traves de las **tools MCP** del server `judicial`. NO leer archivos de codigo fuente, NO instalar dependencias, NO escribir scripts. Solo invocar las tools y razonar sobre el contenido.

## Credenciales

Leer de `~/.env`:
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV/SCBA: `MEV_USUARIO` y `MEV_PASSWORD`

## Referencias

Antes de ejecutar el control, leer estos archivos de referencia:
- `skills/impugnar-pericia/references/baremo-659-96.md` — Tablas del Decreto 659/96
- `skills/impugnar-pericia/references/controles-pericia.md` — Checklist de controles
- `skills/impugnar-pericia/references/plantilla-impugnacion.md` — Template del escrito
- `skills/impugnar-pericia/references/argumentos-medico-legales.md` — Catalogo de argumentos legales
- `skills/impugnar-pericia/references/modelos-impugnacion.md` — **42+ modelos reales** de escritos del estudio, organizados por categoria (factores, rodilla, hernias, nervios, psiquica, causalidad, baremo, etc.). **CRITICO: estos modelos contienen los TEXTOS LITERALES que hay que usar. NO parafrasear. Copiar el texto tal cual del modelo que corresponda y solo reemplazar los datos del caso** (nombre del perito, porcentajes, fechas, expediente, partes, lateralidad, etc.)

## Flujo de 7 Fases

### FASE 1: Identificar expediente y jurisdiccion

Determinar:
- **Jurisdiccion**: PJN (nacional) o SCBA/MEV (provincia de Buenos Aires)
- **Numero de expediente**: el usuario puede darlo directamente o pedir que lo busques

Si el usuario dice un numero tipo "CNT 19429/2025" o similar → PJN.
Si el usuario dice un numero tipo "LP-12345-2024" o similar → SCBA/MEV.
Si no queda claro, preguntar.

### FASE 2: Leer documentos del expediente

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
   - **Numero de expediente SRT** (buscar "Expediente SRT", "SRT N°", "Comision Medica" en el texto)

2. **La PERICIA MEDICA** — El documento a controlar

3. **El EXPEDIENTE SRT** — Del expediente administrativo de la SRT lo que importa es:
   - **PRIMORDIAL: El DICTAMEN MEDICO** de Comision Medica — Retener:
     - Que incapacidad determino (puede ser 0%)
     - Que patologias reconocio/rechazo
     - Si aplico baremo y cual
     - La fecha del dictamen
   - **SECUNDARIO: La HISTORIA CLINICA** — Retener:
     - Diagnosticos y tratamientos realizados
     - Estudios medicos mencionados (RMN, EMG, radiografias)
     - Fecha de alta medica
     - Evolución del cuadro
   - Hay que buscar dentro del expediente SRT hasta encontrar el dictamen medico. El expediente SRT puede tener muchas fojas, pero el dictamen es lo esencial.

**Para PJN (CABA / Nacional):**
Usar `pjn_leer_documentos` con `max_documentos: 10` y `max_movimientos: 50`. Buscar la demanda y la pericia medica en los documentos leidos.

Si `pjn_leer_documentos` no trae ambos documentos, intentar con `max_movimientos: 100`.

Para obtener el expediente SRT con el dictamen medico:
- **El expediente SRT esta en el PRIMER DEO** (Despacho de Expedientes y Oficios). Buscar en los movimientos el primer despacho tipo "DEO" o "DOCUMENTAL DE INICIO" — ahi se adjunta el expediente administrativo de la SRT completo. Dentro de ese expediente, buscar hasta encontrar el dictamen medico de Comision Medica.
- Si no se encuentra en el DEO, buscar en el texto de la demanda el numero de expediente SRT (ej: "Expediente SRT 618936/23")
- Si no aparece, pedirle al usuario que lo pegue en el chat

**Para MEV/SCBA (Provincia de Buenos Aires):**
1. Usar `mev_listar_causas` para encontrar la causa y obtener `idc` e `ido`
2. Usar `mev_obtener_movimientos` con `idc` e `ido` para ver TODOS los movimientos de la causa
3. Identificar en los movimientos: demanda, pericia medica
4. **El expediente SRT con el dictamen medico se encuentra en una CONTESTACION DE OFICIO**. Buscar en los movimientos un tramite tipo "contestacion de oficio", "oficio contestado", "informe SRT", "oficio SRT" — generalmente viene adjunto como PDF. Dentro de ese PDF, buscar hasta encontrar el dictamen medico de Comision Medica.
5. Usar `mev_leer_documentos` con los movimientos relevantes identificados
6. Si no se encuentra la contestacion de oficio, o si el PDF no se puede leer (imagen escaneada), pedirle al usuario que lo pegue en el chat

**IMPORTANTE**: El dictamen SRT es clave porque:
- Si la SRT dio 0% y el perito da incapacidad → la pericia es favorable, tener cuidado al impugnar
- Si la SRT dio incapacidad y el perito da menos → argumento fuerte para impugnar
- Si es accion de revision (Ley 15057 en Provincia, Ley 27348 en Nacion), el dictamen SRT es el acto que se revisa
- Si la SRT dio 0%, NO hay incapacidad previa → Balthazar es improcedente (argumento clave contra 549/2025)

### FASE 3: Recopilar info complementaria

Solo preguntar al usuario lo que NO se pudo extraer de la demanda, la pericia y el dictamen SRT:
- Si no se encontro el dictamen SRT en los movimientos, pedirle al usuario que lo pegue o indique el numero
- Estudios medicos extra que quiera aportar (RMN, EMG, etc.)
- Datos que el usuario quiera destacar especialmente
- Si el actor es diestro o zurdo (relevante para miembro habil en miembros superiores)

**NO preguntar** lo que ya se extrajo de los documentos leidos (lesiones, mecanica, lateralidad, fecha, SRT si ya se leyo, etc.).

### FASE 4: Controlar la pericia

Aplicar TODOS los controles cruzando datos de la demanda contra la pericia. Leer `references/controles-pericia.md` para la checklist completa. Los controles son:

**SECCION 1 — Datos basicos del accidente:**
- 1.1 Fecha del accidente (demanda vs pericia vs SRT)
- 1.2 Mecanica del accidente
- 1.3 Zona lesionada — **CRITICO: verificar DERECHA/IZQUIERDA**
- 1.4 Alta medica

**SECCION 2 — Incapacidad fisica:**
- 2.1 Patologias constatadas vs reclamadas
- 2.2 Comparacion con SRT
- 2.3 Limitacion funcional (grados de movilidad vs baremo 659/96)
- 2.4 Acumulacion patologia + limitacion
- 2.5 Control especifico de rodilla (hidrartrosis, sinovitis, meniscal, meniscectomia)
- 2.6 Inestabilidad articular
- 2.7 Hernias
- 2.8 Cicatrices
- 2.9 Lesion de nervios perifericos / EMG
- 2.10 Miembro habil (solo miembros superiores: +5%)

**SECCION 3 — Incapacidad psiquica:**
- 3.1 Si el perito medico mensuro incapacidad psiquica
- 3.2 Grado de reaccion vivencial (I=0%, II=10%, III=20%, IV=30%)
- 3.3 Alteraciones cognitivas (memoria/concentracion → Grado III)

**SECCION 4 — Causalidad y permanencia:**
- 4.1 Relacion de causalidad fisica
- 4.2 Relacion de causalidad psiquica
- 4.3 Incapacidad permanente/irreversible
- 4.4 Causalidad negada (si el perito nego causalidad, evaluar si tiene fundamento)

**SECCION 5 — Baremo:**
- 5.1 Debe ser Decreto 659/96. Si uso otro (AMA, Altube) → IMPUGNAR
- 5.2 **CRITICO: Decreto 549/2025 aplicado retroactivamente** — Si el accidente es anterior a la vigencia del 549/2025 y el perito lo uso → ERROR GRAVE. Buscar en la pericia: "549/2025", "549/25", "nueva tabla", "tabla vigente que sustituye al 659/96". Consecuencias: (a) porcentajes reducidos, (b) capacidad restante generalizada indebida sobre incapacidades del mismo siniestro, (c) posible caida debajo de umbrales legales (50% o 66% T.O.)
- 5.3 Si se detecto 5.2 → Recalcular con 659/96 + suma aritmetica y verificar si supera umbral del 50% o 66% T.O.

**SECCION 6 — Factores de ponderacion:**
- 6.1 Si aplico factores
- 6.2 Factor edad: suma ARITMETICA directa (1% por ano sobre 30). NO porcentual
- 6.3 Dificultad para tareas: leve ≤10%, intermedia 11-15%, alta 16-20%
- 6.4 **Factores sobre psiquica**: dificultad y recalificacion TAMBIEN aplican sobre lo psiquico

**SECCION 7 — Calculo:**
- 7.1 Metodo de capacidad restante (Balthazar): bajo 659/96 SOLO si hay incapacidad previa de siniestro anterior. Si el perito la aplico a incapacidades del MISMO siniestro porque uso 549/2025 → ERROR (vincular con 5.2)
- 7.2 Suma aritmetica correcta

**SECCION 8 — Incapacidad integral:**
- Si hay preexistencias, evaluar Art. 45 inc c Ley 24.557

**REGLAS CRITICAS:**
- Si la pericia es FAVORABLE (alta incapacidad, buena causalidad, permanencia OK) → avisar al usuario que NO conviene impugnar, aunque haya errores menores
- Lateralidad: SIEMPRE verificar que DERECHA/IZQUIERDA coincida entre demanda y pericia
- Factores de ponderacion son el ERROR MAS COMUN de los peritos
- Signos objetivos de rodilla (hidrartrosis, atrofia, bloqueo) = objetivo = da incapacidad
- **Decreto 549/2025**: Desde su sancion, es cada vez mas frecuente que peritos apliquen este baremo retroactivamente. SIEMPRE verificar la fecha del accidente vs el baremo usado. Si aplico 549/2025 a accidente anterior → genera una OBSERVACION COMPUESTA (baremo + capacidad restante + recalculo + inconstitucionalidad subsidiaria). Usar modelo Barrientos en `modelos-impugnacion.md` como referencia

### FASE 5: Presentar resultado del control

Mostrar al usuario una tabla con TODOS los items controlados:

```
| # | Control | Resultado | Detalle |
|---|---------|-----------|---------|
| 1.1 | Fecha accidente | OK | Coincide: 15/03/2022 |
| 1.3 | Lateralidad | ERROR | Demanda: rodilla DERECHA / Pericia: rodilla IZQUIERDA |
| 2.3 | Limitacion funcional | WARNING | Flexion 0-120° = 5% segun baremo, perito asigno 2% |
| 5.2 | Decreto 549/2025 | ERROR | Perito uso 549/2025, accidente anterior a su vigencia |
| 6.2 | Factor edad | ERROR | Aplico porcentual (10% de 25% = 2.5%) en vez de aritmetico (10%) |
...
```

Al final, mostrar:
- **Datos SRT**: que determino la Comision Medica (% incapacidad o rechazo, patologias)
- **Resumen**: incapacidad fisica X%, psiquica X%, factores X%, total X% (segun perito vs segun nuestro calculo)
- **Veredicto**: HAY QUE IMPUGNAR / NO CONVIENE IMPUGNAR
- **Pronostico**: probabilidad de exito de la impugnacion

### FASE 5bis: Preguntar al usuario QUE impugnar

**CRITICO: NO generar el escrito automaticamente. Primero preguntar.**

Presentar al usuario la lista de items con ERROR o WARNING y preguntarle cuales quiere incluir en la impugnacion:

```
Errores detectados — ¿cuales queres impugnar?

1. [ERROR] Decreto 549/2025 aplicado retroactivamente (incluye: baremo, capacidad restante, recalculo, inconstitucionalidad subsidiaria)
2. [ERROR] Factor edad porcentual en vez de aritmetico
3. [WARNING] Dificultad "intermedia" pero asigno 10% (deberia ser 11-15%)
4. [WARNING] No aplico factores sobre psiquica

¿Queres agregar alguna observacion adicional que no haya detectado?
```

El usuario puede:
- Confirmar todos los errores
- Elegir solo algunos
- Descartar errores que no quiere impugnar (ej: si la pericia es favorable en general)
- Agregar observaciones propias que el control automatico no detecto
- Decir que no quiere impugnar nada

**Solo continuar a la Fase 6 cuando el usuario haya confirmado QUE observaciones incluir.**

### FASE 6: Generar escrito de impugnacion

Solo con las observaciones que el usuario confirmo en la Fase 5bis.

Leer `references/plantilla-impugnacion.md` para el formato y `references/argumentos-medico-legales.md` para los argumentos.

**REGLA FUNDAMENTAL: COPIAR TEXTOS LITERALES DE LOS MODELOS**

Para cada observacion que el usuario confirmo, buscar en `references/modelos-impugnacion.md` el modelo que corresponda a esa categoria de error. **Copiar el texto LITERAL del modelo**, reemplazando UNICAMENTE los datos especificos del caso:
- Nombre del perito (Dr. XXX)
- Porcentajes concretos (incapacidad, factores)
- Fechas (accidente, pericia, traslado)
- Datos del expediente (caratula, numero, partes)
- Lateralidad (derecha/izquierda)
- Edad del actor
- Tareas habituales
- Patologias especificas del caso

**NO reescribir, NO parafrasear, NO "mejorar" la redaccion de los modelos.** Los modelos son textos probados en la practica del estudio que fueron aprobados por los jueces. Mantener exactamente la misma estructura de frases, citas legales, y argumentacion. Si un modelo dice "La decision es erronea porque segun lo establecido en el Decreto 659/96..." usar esa misma frase, no inventar otra.

Si hay mas de un modelo aplicable para la misma categoria, elegir el que mas se ajuste al caso concreto.

Si NO hay modelo para una observacion especifica, recien ahi redactar siguiendo el estilo de los modelos existentes.

El escrito debe:
1. Tener encabezado con datos del expediente (usar modelo de "ESCRITO VACIO PERICIA MED IMPUGNA PERICIA" como estructura base)
2. Titulo "IMPUGNA PERICIA MEDICA" (o "OBSERVA PERICIA MEDICA" segun el caso)
3. Objeto: "Que vengo a impugnar la pericia medica presentada por el Dr. [nombre] de fecha [fecha]..."
4. Desarrollo: observaciones NUMERADAS, cada una **copiada del modelo correspondiente** con datos del caso reemplazados
5. Petitorio pidiendo:
   - Que se haga lugar a la impugnacion
   - Que el perito brinde explicaciones (art. 473 CPCCN / 474 CPCCBA)
   - Que se ordenen estudios complementarios si corresponde
   - Subsidiariamente, designacion de nuevo perito

**CASO ESPECIAL — Decreto 549/2025 aplicado retroactivamente:**
Cuando el error principal es la aplicacion retroactiva del 549/2025, el escrito tiene una estructura especial:
- **Observacion 1**: COMPUESTA con 3 sub-puntos:
  - 1.1 Baremo aplicable: Decreto 659/96 (irretroactividad, art. 7 CCyCN)
  - 1.2 Consecuencia: improcedencia de capacidad restante (659/96 solo para siniestros previos, no del mismo hecho)
  - 1.3 Recalculo: suma aritmetica con 659/96, verificar umbrales (50%, 66%)
- **Observacion 2**: INCONSTITUCIONALIDAD SUBSIDIARIA del 549/2025 (5 fundamentos: progresividad, porcentajes reducidos, exceso reglamentario, retroactividad, principio protectorio) + reserva caso federal
- **Demas observaciones**: otros errores detectados (factor edad, etc.)
- **Petitorio especifico**: incluir punto de inconstitucionalidad y reserva caso federal

Ver `references/plantilla-impugnacion.md` seccion "Decreto 549/2025". **Copiar los textos literales del modelo Barrientos en `references/modelos-impugnacion.md`**, reemplazando unicamente los datos del caso (nombre perito, porcentajes, fechas, patologias). NO parafrasear el modelo Barrientos.

**CITAS DE JURISPRUDENCIA:**
Algunos modelos tienen citas de jurisprudencia con la referencia del caso entre parentesis despues de la cita. Al generar el escrito, las citas de jurisprudencia deben ir ENTRE PARENTESIS inmediatamente despues del texto citado, tal como aparecen en los modelos. Ejemplo: "...es de 7.60%" (CNAT, SALA VII, "MIRANDA DARIO EDUARDO C/ GALENO...", Expte. 73939/2015, Sentencia del 28/03/2018). Copiar las citas TAL CUAL aparecen en el modelo (tribunal, sala, caratula, expediente, fecha). NO ponerlas como notas al pie.

**Formato segun jurisdiccion:**
- PJN: generar PDF (texto plano formateado)
- SCBA: generar HTML (para el campo texto_html del borrador)

### FASE 7: Mostrar escrito y esperar aprobacion

**STOP OBLIGATORIO — NO guardar como borrador automaticamente.**

Despues de generar el escrito en la Fase 6:
1. Mostrar el texto completo del escrito al usuario en el chat
2. Preguntarle: "¿Queres que lo guarde como borrador en [PJN/SCBA]? ¿Queres cambiar algo antes?"
3. **Esperar la respuesta del usuario**. NO llamar a ninguna tool de guardado hasta que el usuario diga expresamente que lo guarde.
4. El usuario puede pedir cambios, correcciones, agregar o quitar observaciones antes de guardar

Solo cuando el usuario confirme EXPRESAMENTE ("dale", "guardalo", "si", etc.), guardar:

**Para PJN:**
```
Tool: pjn_guardar_borrador
Parametros:
  - numero_expediente: "CNT XXXXX/YYYY"
  - tipo_escrito: "E" (ESCRITO)
  - pdf_base64: [el PDF generado en base64]
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

**PROHIBIDO:** Nunca usar `pjn_presentar_escrito` ni `pjn_enviar_borrador` sin confirmacion EXPLICITA del usuario. Nunca guardar borrador sin que el usuario haya visto el escrito y dicho que lo guarde.

## Instrucciones para generar el PDF

Para PJN necesitas generar un PDF en base64. Usa este metodo:

1. Generar el texto del escrito con formato limpio
2. Crear un HTML con el escrito formateado
3. Usar Bash para convertir a PDF: `echo '<html>...</html>' | python3 -c "import sys; ..."`

Alternativa mas simple: pedirle al usuario que copie el texto y lo pegue en un Word/PDF si la generacion automatica falla.

## Notas importantes

- Los peritos medicos cometen errores frecuentes en FACTORES DE PONDERACION (especialmente edad)
- La lateralidad (DERECHA/IZQUIERDA) es un error grave pero poco comun
- Si la pericia da alta incapacidad y buena causalidad, NO impugnar aunque tenga errores menores
- Los factores de ponderacion (dificultad, recalificacion) aplican a AMBAS incapacidades (fisica Y psiquica)
- El metodo de Balthazar (capacidad restante) bajo Decreto 659/96 SOLO se aplica cuando hay incapacidad previa de siniestro anterior
- Siempre consultar el baremo 659/96 para verificar porcentajes de limitacion funcional
- **Decreto 549/2025**: Desde su sancion, es CADA VEZ MAS FRECUENTE que los peritos lo apliquen retroactivamente a siniestros anteriores. Este error tiene doble impacto: (1) porcentajes reducidos, (2) capacidad restante generalizada que no corresponde bajo 659/96. SIEMPRE plantear la inconstitucionalidad como SUBSIDIARIA (para el caso de que el juez considere aplicable el 549/2025). SIEMPRE pedir al perito que haga el calculo alternativo con 659/96 + suma aritmetica para que el juez tenga ambas opciones al sentenciar
- Cuando el 549/2025 se aplica retroactivamente, verificar si el recalculo con 659/96 hace superar umbrales legales (50% T.O. = prestacion mensual complementaria, 66% T.O. = gran invalidez). Enfatizar esto en la observacion
