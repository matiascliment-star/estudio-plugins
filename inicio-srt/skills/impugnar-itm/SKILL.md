---
name: impugnar-itm
description: Genera el escrito IMPUGNA INFORME TÉCNICO MÉDICO para presentar ante la Comisión Médica Jurisdiccional de la SRT, fundándose en hasta tres causales modulares — A) que el ITM no convocó a examen físico, B) que no solicitó estudios complementarios indispensables (RMN, RX, ecografía, EMG, psicodiagnóstico), C) que no analizó la totalidad de las patologías reclamadas en el escrito de inicio o documentadas en la historia clínica. Lee los PDFs del expediente SRT del cliente (ITM, expediente_XXXXX.pdf, escrito de inicio, historia clínica, citación a examen físico, alta médica), detecta automáticamente qué bloques corresponden, redacta el escrito con el encabezado del manifiesta-lesiones y genera el PDF listo para subir a Mi Ventanilla SRT. NO sube el PDF — Matías debe leerlo y dar el OK explícito. Usar cuando el usuario pida "impugnar ITM", "impugnar informe técnico médico", "impugnar el ITM", "rebatir ITM", "objetar ITM", "contestar ITM", "pedir ampliación del ITM", "pedir estudios al ITM". Triggers: "impugnar ITM", "impugnar informe técnico médico", "rebatir ITM", "objetar ITM", "contestar ITM", "pedir RMN al ITM", "ampliar ITM".
---

# Impugnar ITM – Generador de PDF

Skill para generar el escrito IMPUGNA INFORME TÉCNICO MÉDICO + ENCABEZADO en PDF, listo para subir a Mi Ventanilla SRT.

NO genera manifiesta lesiones (eso es `manifiesta-lesiones`), NO genera demanda judicial.

## Cuándo se usa

Después de que la Comisión Médica emite el ITM (Informe Técnico Médico) en un trámite de divergencia / determinación de incapacidad / rechazo, cuando el ITM presenta uno o más de estos déficits:

- **A) No cita a examen físico** — el rubro "Requiere Audiencia / Examen Físico" del ITM está en NO. Sin examen físico no se puede determinar incapacidad bajo el Baremo del Decreto 659/96.
- **B) No solicita estudios complementarios** — el rubro "Indicaciones/Estudios Solicitados" dice "No se solicitan" o no incluye los estudios indispensables para diagnosticar las patologías denunciadas (RMN, RX, ecografía, EMG, psicodiagnóstico, etc.).
- **C) No analiza la totalidad de las patologías** — el "Análisis del Caso" del ITM circunscribe la evaluación a algunas zonas, omitiendo lesiones reclamadas en el escrito de inicio y/o documentadas en la historia clínica (con frecuencia: el daño psíquico, los dedos del pie, las lesiones tendinosas detectadas en ecografía, etc.).

Los tres bloques son **modulares**: se incluyen solo los que correspondan al caso. Si los tres aplican, mejor; si solo uno, también vale.

## Flujo

1. **Identificar la carpeta del caso** — el usuario suele estar parado en la carpeta del cliente (ej. `AA clientes activos/<APELLIDO> <NOMBRE> - <ART> - SRT - <NUM>/`). Si no es claro, preguntar.

2. **Leer TODOS los PDFs relevantes**:
   - `*ITM*.pdf` — **clave**: trae el rubro "Requiere Audiencia / Examen Físico" (SI/NO), el rubro "Indicaciones/Estudios Solicitados" y el "Análisis del Caso" con las zonas que la CM piensa evaluar. También trae fecha del ITM, firmante y matrícula.
   - `expediente_*.pdf` o expediente SRT principal — **clave**: contiene el escrito de inicio (manifiesta lesiones, ofrece prueba) que es la base contra la que comparar lo que el ITM analizó. Buscar el capítulo III "A raíz del accidente…" donde se reclaman daños físicos y psíquicos.
   - `*HC*.pdf`, `*historia clinica*.pdf`, `expediente*HC.pdf` — historia clínica del prestador de la ART. Buscar zonas/lesiones que el ITM pasó por alto. **Leerla siempre si está**.
   - `*ecografia*.pdf`, `*RMN*.pdf`, `*RX*.pdf`, `*estudio*.pdf` — estudios del cliente para citar en el bloque B.
   - `Citacion*.pdf`, `*examen*fisico*.pdf` — si existe esta citación, el bloque A NO aplica.
   - `ALTA*.pdf` — confirma diagnóstico aceptado por la ART.

3. **Detectar qué bloques corresponden**:
   - **Bloque A**: aplica si el ITM dice "Requiere Audiencia / Examen Físico: NO" Y no hay archivo `Citacion*` en la carpeta. Si existe la citación → A NO aplica.
   - **Bloque B**: aplica si "Indicaciones/Estudios Solicitados: No se solicitan" o si los estudios pedidos son insuficientes para el cuadro reclamado. Casi siempre aplica.
   - **Bloque C**: aplica si el "Análisis del Caso" del ITM enumera menos zonas que las reclamadas en el escrito de inicio, o si ignora el daño psíquico (que casi siempre se reclama y casi nunca se evalúa).

4. **Extraer datos para el encabezado y la presentación**:
   - Apellido y Nombre del damnificado (del ITM o expediente)
   - DNI y CUIL
   - ART y código SRT
   - Número de expediente SRT (`XXXXXX/AA`)
   - Comisión Médica Jurisdiccional (número + delegación)
   - Motivo de la presentación (Divergencia / Rechazo / Determinación de Incapacidad)
   - Fecha del ITM impugnado
   - Firmante del ITM (apellido, nombre, M.N.)
   - Patologías reclamadas en el escrito de inicio (lista)
   - Patologías que el ITM acota analizar (del "Análisis del Caso")
   - Estudios obrantes en autos (ecografía, RMN, etc.) para citarlos en B
   - Estudios faltantes que se piden en B

5. **MOSTRAR EL CONTENIDO COMPLETO AL USUARIO ANTES DE GENERAR EL PDF** — pegar el escrito en el chat para revisión. Generar el PDF SOLO si el usuario pide explícitamente "hacelo en PDF" / "dale" / "generá el PDF". Esto respeta la regla "no subir borradores sin leer".

6. **Generar el PDF** con `scripts/generar_impugna_itm_pdf.py`. Reemplazar las variables `###...###` antes de ejecutar. El PDF se guarda en la carpeta del caso con nombre `IMPUGNA ITM - <APELLIDO>.pdf`.

7. **NO subir a Mi Ventanilla SRT** — Matías debe leer el PDF y dar el OK explícito; recién entonces lo carga él (o una empleada).

## Reglas críticas

Las reglas completas están en `references/reglas-impugnacion.md`. Lo no negociable:

- **NO mencionar a la Comisión Médica Central** en el cuerpo de la impugnación. La CMC es órgano de **alzada**: solo aparece si una de las partes apela el dictamen de la CMJ. Para evaluar daño psíquico en primer grado se pide "interconsulta con psicólogo o médico psiquiatra" o "psicodiagnóstico".
- **El petitorio se dirige a la CMJ que tramita el expediente**, nunca a la CMC.
- **Encabezado**: "Comisión Médica Jurisdiccional N° X – Delegación YYYY:", NO "Sr. Presidente".
- **Datos del letrado fijos**: Matías Christian García Climent, T° 97 F° 16 C.P.A.C.F., CUIT 20-31380619-8, Av. Ricardo Balbín 2401 1° A, CABA, matiasgarciacliment@gmail.com. NO inventar.
- **Subrayado**: el título centrado y los headers (I.- OBJETO, II.- FUNDAMENTOS, A.-, B.-, C.-, III.- PETITORIO) van con `<u>...</u>` además del bold.
- **Reserva del caso federal SIEMPRE** al final del petitorio (art. 14 ley 48 + ley 27.348).
- **NO inventar patologías** que no estén en el escrito de inicio o en la historia clínica. Si el cliente solo reclamó tobillo y daño psíquico, no agregar columna ni hombro.
- **Bloque C — daño psíquico**: cuando se reclamó "reacción vivencial anormal neurótica grado III" (típico), el ITM casi siempre lo ignora. Es el ítem estrella del bloque C en casos chicos.

## Encabezado tipo

```
Expediente SRT N° <NUM>/<AA>
"<APELLIDO NOMBRE> c/ <ART> S.A. s/ <MOTIVO>"
Comisión Médica Jurisdiccional N° <NUM> – Delegación <NOMBRE>
```

## Título centrado

```
IMPUGNA INFORME TÉCNICO MÉDICO – SOLICITA <ALGUNA O VARIAS DE: AMPLIACIÓN
DE EXAMEN FÍSICO | ESTUDIOS COMPLEMENTARIOS | ANÁLISIS DE LA TOTALIDAD DE
LAS PATOLOGÍAS DENUNCIADAS>.
```

El título se construye dinámicamente con los bloques que apliquen.

## Estructura del cuerpo

Las secciones que SIEMPRE van:
- **Fórmula de presentación** (idéntica a manifiesta-lesiones).
- **I.- OBJETO** — qué se impugna y bajo qué causales (lista las que apliquen).
- **II.- FUNDAMENTOS** — bloques A, B, C (los que apliquen).
- **III.- PETITORIO** — pedidos numerados + reserva federal.
- **SERÁ JUSTICIA** + firma.

## Lo que NO hace este skill

- NO hace manifiesta lesiones (eso es `manifiesta-lesiones`).
- NO hace relato del accidente (eso es `redaccion-laboral`).
- NO hace demanda judicial.
- NO sube el PDF a Mi Ventanilla SRT — solo lo deja en la carpeta del caso para que Matías o una empleada lo carguen manualmente, previa lectura.

## Referencias

- `references/reglas-impugnacion.md` — Plantillas literales de cada bloque, lista de estudios sugeridos por zona afectada, jurisprudencia y normas a citar.
