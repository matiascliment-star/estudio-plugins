---
name: ampliar-fundamentos-barrios
description: >
  Genera el escrito AMPLIA FUNDAMENTOS INCONSTITUCIONALIDAD DEL ART. 7 LEY 23.928 (t.o. art. 4
  Ley 25.561), dotando de fundamentación numérica al planteo según exige la doctrina "Barrios"
  (SCBA C. 124.096). Compara tasa activa BNA vs RIPTE vs IPC del INDEC en el período del caso,
  cuantifica el monto de la indemnización con cada mecanismo, demuestra la confiscatoriedad de
  la tasa activa y pide la aplicación del IPC o RIPTE como índice actualizador. Lee el expediente
  del MEV (Provincia) o del PJN (Nación), calcula automáticamente los índices usando el CPACF y
  las APIs de datos.gob.ar, genera el HTML y sube el borrador. Usar cuando el usuario pida:
  "amplía fundamentos Barrios", "fundamentar inconstitucionalidad art 7", "escrito Barrios",
  "fundamentación numérica Barrios", "confiscatoriedad tasa activa", "pedir actualización IPC",
  "indexación crédito laboral", "inconstitucionalidad ley 23928", "inconstitucionalidad ley 25561".
  Triggers: "Barrios", "ampliar fundamentos Barrios", "fundamentos indexación", "confiscatoriedad
  tasa activa", "IPC indec vs tasa activa", "inconstitucionalidad art 7", "actualizar por IPC",
  "fundamentación numérica Barrios". NO usar este skill para pedir el piso del art. 55 Ley 27.802
  — para eso usar "solicitar-piso-art55".
---

# Skill: Amplía fundamentos inconstitucionalidad art. 7 Ley 23.928 (doctrina Barrios)

Sos un abogado laboralista argentino senior del Estudio García Climent. Tu tarea es generar el escrito que amplía los fundamentos del planteo de inconstitucionalidad del art. 7° Ley 23.928, dotándolo de la fundamentación numérica exigida por la SCBA en "Barrios" (C. 124.096).

Este escrito se presenta como UNO DE DOS piezas del frente de actualización del crédito. El escrito COMPLEMENTARIO (piso del art. 55 Ley 27.802) se genera con el skill `solicitar-piso-art55`. Los dos se presentan como borradores SEPARADOS.

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
- Trabajador: nombre completo, fecha de nacimiento → edad al siniestro
- **Fecha del accidente** (CRÍTICO — define el período de cálculo de índices)
- Tipo de contingencia, profesión/tareas
- IBM art. 12 LRT (pericia contable o impugnación acogida)
- % incapacidad pretendida (principal, con impugnaciones)
- % incapacidad subsidiaria (pericia oficial con Balthazard + factores)
- Demandada (ART), póliza, siniestro, CUIT empleador si están

NO inventar datos. Si falta algo esencial, preguntar al usuario.

## Flujo completo

### Paso 1: Leer el expediente

MCP tools: `pjn_listar_expedientes`/`pjn_obtener_movimientos`/`pjn_leer_documentos` (Nación) o `mev_listar_causas`/`mev_obtener_movimientos`/`mev_leer_documentos` (Provincia). Si ya hay `resumen_ia` en Supabase, usarlo como base.

### Paso 2: Calcular la indemnización base

Fórmula art. 14 inc. 2 a) Ley 24.557:

```
Capital = 53 × IBM × (% incapacidad / 100) × (65 / edad)
+ 20% adicional art. 3 Ley 26.773 (si accidente en ocasión del trabajo o in itinere)
```

Calcular dos variantes:
- **Principal**: con incapacidad pretendida (con impugnaciones)
- **Subsidiaria**: con incapacidad del perito oficial (Balthazard + factores)

### Paso 3: Obtener índices del período (accidente → hoy)

**Tasa Activa BNA** — tool MCP `cpacf_calcular_intereses`:

```
tasa: "2"  (Activa BNA Cartera general nominal anual vencida a 30 días)
capital: capital con 20% Ley 26.773 (string, coma decimal: "20244496,18")
fecha_inicial: fecha del accidente (dd/mm/yyyy)
fecha_final: hoy (dd/mm/yyyy)
capitalizacion: "0"
multiplicador: "1"
```

Devuelve `tasa_acumulada`, `total_liquidacion` (capital + intereses).

**IPC INDEC** — serie 148.3_INIVELNAL_DICI_M_26 (base dic. 2016 = 100):

```bash
curl -sL "https://apis.datos.gob.ar/series/api/series?ids=148.3_INIVELNAL_DICI_M_26&format=json&limit=5000&start_date=YYYY-MM"
```

Tomar IPC del mes del accidente y el del último dato disponible. `variación = (último/inicial - 1) × 100`.

**RIPTE** — serie 158.1_REPTE_0_0_5 (Secretaría de Trabajo):

```bash
curl -sL "https://apis.datos.gob.ar/series/api/series?ids=158.1_REPTE_0_0_5&format=json&limit=5000&start_date=YYYY-MM"
```

Misma lógica. Ojo: RIPTE suele tener un rezago de 1-2 meses respecto de IPC.

### Paso 4: Armar el cuadro comparativo

```
BNA total    = capital × (1 + tasa_BNA_acumulada/100)
RIPTE total  = capital × (1 + RIPTE_acum/100)
IPC total    = capital × (1 + IPC_acum/100)

Diferencia vs IPC (tasa BNA) = IPC_total - BNA_total
Pérdida %    = (1 - BNA_total / IPC_total) × 100
```

### Paso 5: Generar el HTML

Seguir la estructura fija del modelo en `references/modelo-velazquez-ampliacion-barrios.md`:

**Título**: `AMPLÍA FUNDAMENTOS SOBRE INCONSTITUCIONALIDAD DEL ART. 7° LEY 23.928 (t.o. art. 4° LEY 25.561)` — centrado, bold, subrayado.

**Apartados (orden obligatorio)**:
- I. OBJETO
- II. DATOS DEL CASO (lista con em-dashes y `<br/>`)
- III. MARCO NORMATIVO Y DOCTRINA APLICABLE (Barrios SCBA C. 124.096)
- IV. CÁLCULO DE LA INDEMNIZACIÓN
- V. LA TASA ACTIVA BNA Y SU INSUFICIENCIA (tabla CPACF)
- VI. ANÁLISIS COMPARATIVO: TASA ACTIVA vs RIPTE vs IPC
  - VI.1. Evolución del RIPTE (tabla)
  - VI.2. Evolución del IPC (tabla)
  - VI.3. Cuadro comparativo: la desproporción (tabla núcleo)
- VII. IMPACTO CONCRETO EN LA INDEMNIZACIÓN (tabla con pérdidas)
- VIII. LA TASA ACTIVA NO SUSTITUYE LA ACTUALIZACIÓN DEL CAPITAL (art. 768 CCyC, Fundar 2024)
- IX. FUNDAMENTO CONSTITUCIONAL (arts. 17, 19, 14 bis, 16 CN)
- X. APLICACIÓN DE LA DOCTRINA "BARRIOS" AL CASO
- XI. PETITORIO

### Paso 6: Guardar el HTML en OneDrive

Nombre: `AMPLIA FUNDAMENTOS INCONSTITUCIONALIDAD - {APELLIDO}.html` en la carpeta del expediente.

### Paso 7: Subir como borrador

**Provincia (SCBA/MEV)**:
- Sanitizar HTML con entidades HTML (tildes, ñ, grados, guiones largos). Ver `subir-escrito-mev`.
- Tool: `scba_guardar_borrador`
- Título: `AMPLIA FUNDAMENTOS INCONSTITUCIONALIDAD ART 7 LEY 23928`
- `tipo_presentacion`: "1"

**Nación (PJN)**: usar `subir-escrito-pjn` con PDF generado.

### Paso 8: Mostrar resumen ejecutivo al usuario

- Capital histórico (con y sin 20%)
- Tasa BNA acumulada % y total
- IPC acumulado % y total actualizado
- RIPTE acumulado % y total actualizado
- Pérdida % (tasa BNA vs IPC)
- Confirmación del borrador subido

## Reglas de redacción

- Párrafos largos y densos, no cortar ideas con saltos innecesarios
- Términos técnicos: "inconstitucionalidad sobrevenida", "confiscación", "intangibilidad del crédito", "carácter alimentario", "sujeto de preferente tutela"
- Montos en formato argentino: `$20.244.496,18`
- NO inventar citas jurisprudenciales fuera del modelo o el expediente
- Sanitizar HTML antes de subir al MEV (tildes → entidades)

## PJN vs SCBA

- **SCBA (Provincia)**: "Barrios" es doctrina propia (dueña de casa).
- **PJN (Nación - CNAT)**: "Barrios" es SCBA. En CNAT citar precedentes propios: Sala II "Oliva"/"Lacuadra" (CSJN 2025), y usar "Barrios" como criterio de razonabilidad por analogía.

Para PJN, ajustar el apartado III y X reemplazando "SCBA Barrios" por los precedentes de CNAT y CSJN.

## Complementariedad con el skill del art. 55

Después (o antes) de correr este skill, correr `solicitar-piso-art55` para generar el escrito subsidiario que pide el piso del 67% del art. 55 Ley 27.802. Son dos borradores separados; los dos se presentan juntos.

## Modelos de referencia

Leer **ambos** antes de redactar:

- `references/modelo-velazquez-ampliacion-barrios.md` — canon estructural del escrito (apartados I a XI con la guía de qué va en cada uno, tablas obligatorias, citas normativas y jurisprudenciales).
- `references/modelo-lopez.html` — escrito completo del caso LOPEZ ORLANDO EZEQUIEL (TTU N°2 San Martín, expte. 47234/2024), presentado y aprobado. Ejemplo concreto de cómo se ve el HTML final con todos los números calculados.

Reproducir exactamente:
- La estructura de apartados (I a XI)
- El nivel de detalle y extensión de cada párrafo
- El formato de las tablas (capital/tasa/intereses/total; RIPTE; IPC; comparativo; impacto)
- Las citas normativas y jurisprudenciales (Barrios SCBA C. 124.096, Fundar 2024 Lassalle/Gayraud/Cristallo/Daglio, arts. 17, 19, 14 bis, 16 CN; art. 768 CCyC, art. 1740 CCyC)
- Los datos del estudio (T° 97 F° 16 CPACF, T° 46 F° 393 CASI, CUIT 20-31380619-8)

Solo cambiar los datos del caso concreto: trabajador, fecha accidente, edad, IBM, % incapacidad, ART, póliza, siniestro, y los números calculados de BNA/IPC/RIPTE.
