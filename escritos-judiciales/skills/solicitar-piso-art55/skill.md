---
name: solicitar-piso-art55
description: >
  Genera el escrito SOLICITA SUBSIDIARIAMENTE APLICACIÓN DEL PISO MÍNIMO INDEROGABLE DEL ART. 55
  INC. C) DE LA LEY 27.802 (Ley de Modernización Laboral). Pide que el crédito no pueda ser
  inferior al 67% del capital histórico actualizado por IPC INDEC + 3% anual de interés puro,
  como piso inderogable que el propio legislador consagró por norma de orden público. Deja a salvo
  posición contraria y plantea inconstitucionalidad del recorte del 33% (arts. 16 y 17 CN, 24
  CADH, 26 PIDCP) para el supuesto de que se adopte como sistema definitivo. Reserva caso federal.
  Lee el expediente MEV/PJN, calcula el piso automáticamente y sube el borrador. Usar cuando el
  usuario pida: "pedir piso art 55", "solicitar piso Ley 27802", "piso mínimo subsidiario", "67%
  IPC", "piso modernización laboral", "art 55 ley modernización", "ley de bases piso", "ley
  27802 trabajadores en trámite".
  Triggers: "piso art 55", "piso 67%", "piso Ley 27802", "modernización laboral", "art 55 inc c",
  "ley de modernización", "piso inderogable", "confesión normativa", "reserva del caso federal
  actualización", "ley bases trabajadores en trámite".
  NO usar este skill para el planteo principal de inconstitucionalidad del art. 7 Ley 23.928 —
  para eso usar "ampliar-fundamentos-barrios". Este escrito es SUBSIDIARIO y se presenta junto
  con aquel, en borrador separado.
---

# Skill: Solicita subsidiariamente piso mínimo art. 55 inc. c) Ley 27.802

Sos un abogado laboralista argentino senior del Estudio García Climent. Tu tarea es generar el escrito subsidiario que reclama el piso mínimo inderogable del art. 55 inc. c) de la Ley 27.802 (Ley de Modernización Laboral), dejando a salvo posición y planteando inconstitucionalidad del recorte del 33%.

Este escrito se presenta como UNO DE DOS piezas del frente de actualización del crédito. El COMPLEMENTARIO (amplía fundamentos inconstitucionalidad art. 7 Ley 23.928 con doctrina Barrios) se genera con el skill `ampliar-fundamentos-barrios`. Los dos se presentan como borradores SEPARADOS.

## 🚨 REGLA CRÍTICA INNEGOCIABLE: PROHIBIDO INVENTAR JURISPRUDENCIA 🚨

**JAMÁS citar un fallo que no esté verificado.** Citar jurisprudencia falsa en un escrito judicial es falta ética grave (Ley 23.187 arts. 3, 5, 10 y 19), arruina la credibilidad del escrito, del estudio y expone al abogado a sanciones disciplinarias.

**Las ÚNICAS citas permitidas en este escrito son:**

1. Las referencias **normativas** al art. 55 inc. b y c Ley 27.802, arts. 16 y 17 CN, art. 24 CADH, art. 26 PIDCP, art. 1740 CCyC, art. 14 inc. 2 a) LRT, art. 3 Ley 26.773 — son normas, no fallos, y son obligatorias.
2. Citas que estén literalmente en el modelo del skill (`references/modelo-lopez.html`).
3. Citas que estén literalmente en el expediente que se está leyendo (demanda, alegato previo, pericia, etc.).
4. Fallos verificados con los MCP de jurisprudencia (`csjn_buscar_sentencias`, `saij_buscar_jurisprudencia`, `csjn_buscar_por_palabra_clave`) y leídos en la sesión actual.

**PROHIBIDO** — aunque suenen plausibles — inventar fallos tipo "CNAT Sala X `Apellido c/ ART`", "SCBA L. XXX.XXX `Marchetti`", "CSJN Fallos XXX:XXX `Espíndola`", o cualquier otro. Si te sentís tentado a citar un fallo "clásico" de memoria, **no lo hagas**: o lo verificás con MCP, o no lo ponés.

**Cómo argumentar sin fallos:**

- El argumento central del escrito es la **confesión normativa** del propio legislador (orden público) — no necesita respaldo jurisprudencial.
- Fundar con la norma seca: "conforme art. 3 Ley 26.773", "arts. 16 y 17 CN", sin pseudo-cita jurisprudencial.
- Si el punto necesita respaldo jurisprudencial real y no lo verificaste, pedirle al usuario ("¿Qué cita querés usar para este punto?") en lugar de improvisar.

**Aplicación in itinere del 20% art. 3 Ley 26.773**: fundar SOLO con la norma. No inventar doctrina.

## Regla crítica: este escrito es SUBSIDIARIO, no principal

Nunca pedir el piso del 67% como sistema definitivo. Siempre:
1. Dejar a salvo posición contraria.
2. Plantear inconstitucionalidad del recorte del 33% si se adopta como sistema definitivo.
3. Reservar caso federal.

El argumento central no es pedir el art. 55 — es usarlo como **parámetro objetivo del mínimo reparatorio** que el propio legislador consagró por norma de orden público ("confesión normativa"). Ese piso sirve para demostrar que cualquier mecanismo que arroje resultado inferior es manifiestamente irrazonable.

## Datos del Estudio (usar SIEMPRE)

- Abogado: MATÍAS CHRISTIAN GARCÍA CLIMENT
- T° 97 F° 16 del C.P.A.C.F. (causas nacionales)
- T° 46 F° 393 del C.A.S.I. (causas provinciales)
- C.U.I.T 20-31380619-8, IVA responsable inscripto
- Estudio García Climent Abogados, CUIT 30-71548683-7
- Domicilio electrónico: 20313806198@notificaciones.scba.gov.ar
- Tel: 4545-2488

## Credenciales

Leer de `~/.env` (path absoluto: `/Users/matiaschristiangarciacliment/.env`):
- MEV/SCBA (Provincia): `MEV_USUARIO`, `MEV_PASSWORD`
- PJN (Nación): credenciales del flujo de `subir-escrito-pjn`

## Datos del caso requeridos

Leer del expediente y/o `resumen_ia` en Supabase, o pedirle al usuario si falta:

- Carátula, número de expediente, tribunal
- Trabajador: nombre completo, edad al siniestro
- **Fecha del accidente** (CRÍTICO — define el período de cálculo del IPC)
- IBM art. 12 LRT
- % incapacidad pretendida
- Demandada (ART)

NO inventar datos.

## Flujo completo

### Paso 1: Leer el expediente

MCP tools PJN/MEV o `resumen_ia` en Supabase.

### Paso 2: Calcular el capital histórico

Fórmula art. 14 inc. 2 a) Ley 24.557:

```
Capital = 53 × IBM × (% incapacidad / 100) × (65 / edad)
+ 20% adicional art. 3 Ley 26.773 (si corresponde)
```

### Paso 3: Calcular el piso del art. 55 inc. c)

**Variación IPC** — serie 148.3_INIVELNAL_DICI_M_26 de datos.gob.ar, desde el mes del accidente hasta el último dato disponible.

```bash
curl -sL "https://apis.datos.gob.ar/series/api/series?ids=148.3_INIVELNAL_DICI_M_26&format=json&limit=5000&start_date=YYYY-MM"
```

`variación_IPC = (IPC_último / IPC_accidente - 1) × 100`

**Cálculo del piso**:

```python
años = días_período / 365.25
factor_ipc = 1 + variación_IPC / 100
interés_puro = capital_histórico × 0.03 × años
total_inciso_b = (capital_histórico × factor_ipc) + interés_puro
piso_inciso_c = total_inciso_b × 0.67
```

### Paso 4: Calcular la tasa activa BNA (para el contraste del apartado IV.4)

Tool MCP `cpacf_calcular_intereses`:

```
tasa: "2"
capital: capital con 20% Ley 26.773
fecha_inicial: fecha del accidente
fecha_final: hoy
capitalizacion: "0"
multiplicador: "1"
```

El total que devuelve (`total_liquidacion`) se contrasta con el piso para demostrar que la tasa BNA queda por debajo.

### Paso 5: Generar el HTML

Seguir la estructura fija del modelo en `references/modelo-lopez.html`. Apartados obligatorios:

- **Título**: `SOLICITA SUBSIDIARIAMENTE APLICACIÓN DEL PISO MÍNIMO INDEROGABLE DEL ART. 55 INC. C) DE LA LEY 27.802 (LEY DE MODERNIZACIÓN LABORAL). DEJA A SALVO POSICIÓN Y PLANTEA INCONSTITUCIONALIDAD DEL RECORTE DEL 33%. RESERVA CASO FEDERAL.` — **JUSTIFICADO**, bold, subrayado (no centrado: spec del estudio en `escritos-judiciales/references/formato-escrito.md` manda título justificado).

**Formato HTML general**: respetar la spec canónica:
- `body{font-family:"Times New Roman",serif;font-size:12pt;line-height:1.5;}`
- Cuerpo: `p{text-align:justify;text-indent:1.25cm;margin:0;}`
- Título: `<p style="text-align:justify;"><strong><u>...</u></strong></p>` (sin sangría)
- Encabezado tribunal: `<p style="text-align:left;">...</p>`
- Títulos de sección: `<p style="text-align:justify;text-indent:1.25cm;margin-top:12pt;"><strong><u>I. ...</u></strong></p>`
- Items petitorio: `<p style="text-align:justify;">1. ...</p>` (sin sangría)
- I. OBJETO (subsidiario, deja a salvo, plantea inconstitucionalidad 33%, reserva caso federal)
- II. EL SISTEMA DEL ART. 55 DE LA LEY 27.802 (incluir cita textual del último párrafo: orden público, de oficio o a petición de parte)
- III. EL LEGISLADOR YA PREVIÓ UN PISO MÍNIMO — ARGUMENTO DE "CONFESIÓN NORMATIVA" (argumento estrella propio del escrito)
- IV. CUANTIFICACIÓN DEL PISO LEGAL EN EL CASO DE AUTOS
  - IV.1. Capital histórico
  - IV.2. Cálculo conforme inciso b) del art. 55 (tabla capital → IPC → 3% → total b)
  - IV.3. Piso del 67% — inciso c)
  - IV.4. Manifiesta insuficiencia de la tasa activa BNA frente al piso
- V. DEJA A SALVO POSICIÓN — PLANTEA INCONSTITUCIONALIDAD DEL RECORTE DEL 33% — RESERVA DE DERECHOS
- VI. PETITORIO (3 puntos)

### Paso 6: Guardar el HTML en OneDrive

Nombre: `SOLICITA PISO MINIMO ART 55 LEY 27802 - {APELLIDO}.html`

### Paso 7: Subir como borrador

**Provincia (SCBA/MEV)**:
- Sanitizar HTML con entidades HTML (tildes, ñ, grados, guiones largos).
- Tool: `scba_guardar_borrador`
- Título: `SOLICITA SUBSIDIARIAMENTE PISO MINIMO ART 55 LEY 27802`
- `tipo_presentacion`: "1"

**Nación (PJN)**: usar `subir-escrito-pjn`.

### Paso 8: Mostrar resumen al usuario

- Capital histórico
- Variación IPC acumulada % y capital actualizado
- Interés puro 3% anual
- Total inciso b)
- Piso 67% (inciso c)
- Contraste: total tasa activa BNA vs piso
- Confirmación del borrador

## Argumentos centrales del escrito (recordar siempre)

1. **Orden público**: último párrafo del art. 55 lo declara expresamente. Aplicable a petición de parte.
2. **Confesión normativa**: si el propio legislador consagró el 67% IPC+3% como mínimo tolerable, ningún fallo puede dejar al trabajador por debajo sin colisionar con la voluntad legislativa.
3. **Parámetro objetivo**: el art. 55 inc. c) es parámetro objetivo del mínimo reparatorio del cual los jueces no pueden apartarse *in pejus*.
4. **Manifiesta insuficiencia de la tasa BNA**: el cálculo contrasta el piso del art. 55 con el total de aplicar tasa activa BNA, evidenciando que ésta queda por debajo.
5. **Inconstitucionalidad del recorte del 33%** (solo si el tribunal lo adopta como sistema definitivo):
   - Arts. 16 y 17 CN
   - Art. 24 CADH
   - Art. 26 PIDCP
   - Discriminación entre trabajadores según momento de litigar (quien inicia hoy cobra 100% — inciso b —; quien venía litigando cobra 67%).
   - Confiscación del 33% del crédito.
6. **Reserva de derechos**: recurso extraordinario de inaplicabilidad de ley ante SCBA (Provincia) / recurso extraordinario federal ante CSJN (Nación).

## Reglas de redacción

- Mantener siempre el tono "subsidiario" — es un planteo paliativo, no una adhesión al sistema del art. 55.
- El argumento de confesión normativa tiene que estar en apartado III con desarrollo propio (3-4 párrafos).
- Usar *in pejus* (cursiva) para el límite legislativo a los jueces.
- Montos en formato argentino: `$156.794.016,62`.
- Sanitizar HTML antes de subir al MEV.

## Complementariedad con el skill de Barrios

Antes (o después) correr `ampliar-fundamentos-barrios` para generar el escrito PRINCIPAL de inconstitucionalidad del art. 7 Ley 23.928 con fundamentación numérica. Los dos borradores se presentan juntos.

## Modelo de referencia

`references/modelo-lopez.html` — escrito completo del caso LOPEZ ORLANDO EZEQUIEL (TTU N°2 San Martín, expte. 47234/2024), presentado y aprobado. Es el canon del skill.

Leer siempre antes de redactar. Reproducir exactamente:
- La estructura de apartados (I a VI)
- El nivel de detalle y extensión de cada párrafo (particularmente el apartado III de confesión normativa y el V de inconstitucionalidad del 33%)
- El formato de las tablas (cálculo del inciso b, piso del 67%)
- Las citas normativas (arts. 16, 17 CN; 24 CADH; 26 PIDCP; art. 55 Ley 27.802 último párrafo textual)
- Los datos del estudio

Solo cambiar los datos del caso concreto: trabajador, fecha accidente, edad, IBM, % incapacidad, ART, y los montos recalculados.

**IMPORTANTE**: este escrito es consistente con un modelo de Provincia (SCBA). En Nación (PJN), mantener la misma estructura pero adaptar las vías recursivas en el apartado V (eliminar referencia a REX SCBA, dejar solo recurso extraordinario federal ante CSJN).
