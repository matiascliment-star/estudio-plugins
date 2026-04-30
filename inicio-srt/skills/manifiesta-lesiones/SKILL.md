---
name: manifiesta-lesiones
description: Genera SOLO el escrito MANIFIESTA LESIONES con su encabezado para presentar ante la Comisión Médica Jurisdiccional de la SRT. Lee los PDFs del expediente SRT del cliente (ITM, formulario inicio, expediente_XXXXX.pdf, alta médica, etc.) que están en la carpeta del caso, extrae nombre, DNI, CUIL, fecha y mecanismo del accidente, ART, número de expediente SRT, comisión médica jurisdiccional, diagnóstico y zonas lesionadas, y produce un PDF listo para subir a Mi Ventanilla SRT. NO genera relato del accidente, NO genera Anexo I, NO genera demanda — solo el manifiesta lesiones con su carátula. Usar cuando el usuario pida "hacer manifiesta", "armar manifiesta lesiones", "manifiesta para SRT", "manifiesta del expediente XXX", "generar manifiesta", "manifiesta solo", "PDF de manifiesta". Triggers: "manifiesta lesiones", "manifiesta SRT", "armar manifiesta", "hacer manifiesta", "PDF manifiesta", "manifiesta para comisión médica".
---

# Manifiesta Lesiones – Generador de PDF (solo manifiesta + encabezado)

Skill especializado para generar SOLAMENTE el escrito MANIFIESTA LESIONES + ENCABEZADO en PDF, listo para subir a Mi Ventanilla SRT como adjunto al trámite ante la Comisión Médica Jurisdiccional.

NO genera relato del accidente (eso es `redaccion-laboral`), NO rellena Anexo I, NO arma demanda judicial.

## Flujo

1. **Identificar la carpeta del caso** — el usuario suele estar parado en la carpeta del cliente (ej. `AA clientes activos/<APELLIDO> <NOMBRE> - SRT - <NUM>/`). Si no es claro, preguntar.

2. **Leer los PDFs del expediente** (en orden de utilidad):
   - `*ITM*.pdf` — Informe Técnico Médico: trae CUIL, fecha nac., fecha accidente, tipo, diagnóstico, mecanismo, ART, comisión médica jurisdiccional. Es el más rico.
   - `expediente_*.pdf` o el expediente SRT principal — formulario de inicio con domicilio, empleador, número de expediente, carátula.
   - `ALTA*.pdf` / `Alta médica*.pdf` — confirma diagnóstico y secuelas incapacitantes.
   - DDJJ B / aceptación de patrocinio — completan datos.

3. **Extraer datos clave**:
   - Apellido y Nombre del damnificado
   - DNI y CUIL
   - Fecha del accidente
   - Tipo de accidente (Laboral / In Itinere)
   - Mecanismo del accidente (descripción narrativa) → de acá se infieren las zonas lesionadas
   - ART (nombre + código SRT)
   - Número de expediente SRT (`XXXXXX/AA`)
   - Comisión Médica Jurisdiccional (número + delegación)
   - Diagnóstico médico (CIE-10 + descripción)
   - **Zonas lesionadas** — ítem central. Se infieren del diagnóstico + mecanismo + observaciones médicas.
   - Motivo de la presentación (Divergencia / Rechazo / Determinación de Incapacidad / etc.) → para armar la carátula

4. **Aplicar las reglas de transformación** de zonas lesionadas a terminología legal (ver `references/reglas-manifiesta.md`).

5. **MOSTRAR EL CONTENIDO AL USUARIO ANTES DE GENERAR EL PDF** — pegar el manifiesta completo (encabezado + ítems) en el chat para que pueda corregir antes de imprimir. Generar el PDF SOLO si el usuario pide explícitamente "hacelo en PDF" / "generá el PDF" / "guardalo en la carpeta" o equivalente. Esto respeta la regla "no subir borradores sin leer".

6. **Generar el PDF** con `scripts/generar_manifiesta_pdf.py` (template: reemplazar las variables marcadas con `###` antes de ejecutar). El PDF se guarda en la carpeta del caso con nombre `MANIFIESTA LESIONES - <APELLIDO>.pdf`.

## Reglas críticas

Las reglas completas están en `references/reglas-manifiesta.md`. Lo no negociable:

- **Encabezado va dirigido a "Comisión Médica Jurisdiccional N° X – Delegación YYYY:"**, NO a "Sr. Presidente". Las CM no tienen presidente.
- **"Pierna" sin más detalle → traumatismo y esguince de rodilla + tobillo del mismo lado** (dos ítems separados). La pierna es coloquial; los baremos miden articulaciones.
- **"Pie" → "dedos del pie [lado]"** salvo que la ficha liste pie y dedos por separado, en cuyo caso pie = tobillo.
- **Columna cervical/dorsal/lumbar nunca lleva "esguince"** — siempre "Traumatismo de columna [zona]".
- **Pelvis solo "traumatismo"**, nunca esguince ni torsión (estructura ósea, no articulación).
- **Sin impacto no hay traumatismo** — esfuerzos / torsiones sin golpe usan "esguince" o "[zona]algia", nunca "traumatismo".
- **Cimbronazo solo para choques o caídas que sacuden el cuerpo entero**, nunca para mecanismos cervicales aislados.
- **Si hay rodilla** → agregar ítem "Lesión meniscal y ligamentaria no operada con hipotrofia muscular (3) e hidrartrosis y bloqueo."
- **Si hay columna cervical** → agregar "Cervicobraquialgia y cervicalgia." + "Hernia y protrusión discal cervical."
- **Si hay columna lumbar/lumbosacra/dorsolumbar** → agregar "Lumbalgia y lumbociatalgia." + "Hernia y protrusión discal lumbar."
- **Siempre incluir** al final, en este orden:
  1. "Lesión en nervios periféricos[, lesión radicular con secuelas electromiográficas]" (la coletilla solo si hay columna).
  2. Limitación funcional (adaptada a las zonas afectadas).
  3. Daño psíquico.
  4. Cláusula de reserva (texto literal: ver reglas).
- **Si hay cirugía con osteosíntesis** (placa, tornillos, clavijas Kirschner): agregar ítem dedicado al material *in situ* + ítem dedicado a la cicatriz quirúrgica con secuela estética.
- **Datos del letrado** — siempre los del usuario (Matías Christian García Climent, T° 97 F° 16 CPACF, etc.). NO inventar.
- **NO inventar zonas lesionadas** que no estén en el ITM/ficha. Si el ITM dice solo "mano y pierna izquierda", trabajar SOLO con eso (aplicando las reglas de pierna→rodilla+tobillo).

## Encabezado tipo

```
Expediente SRT N° <NUM>/<AA>
"<APELLIDO NOMBRE> c/ <ART> S.A. s/ <MOTIVO PRESENTACIÓN>"
Comisión Médica Jurisdiccional N° <NUM> – Delegación <NOMBRE>
```

## Cuerpo

```
MANIFIESTA LESIONES – RECLAMA DAÑO FÍSICO Y PSÍQUICO.

Comisión Médica Jurisdiccional N° X – Delegación YYYY:

<NOMBRE LETRADO>, abogado, T° 97 F° 16 C.P.A.C.F., CUIT 20-31380619-8,
con domicilio legal constituido en Av. Ricardo Balbín N° 2401, Piso 1°,
Dpto. "A", C.A.B.A., y domicilio electrónico en
matiasgarciacliment@gmail.com, en mi carácter de letrado patrocinante
de <APELLIDO, NOMBRE>, DNI XX.XXX.XXX, CUIL XX-XXXXXXXX-X, en autos
caratulados "<CARÁTULA>", Expediente SRT N° <NUM>/<AA>, ante V.S. me
presento y respetuosamente digo:

Que vengo por el presente a manifestar las lesiones que como
consecuencia del accidente <laboral|in itinere> de fecha <DD de MMMM
de AAAA> padece mi instituyente, a saber:

1.- <Lesión 1>
2.- <Lesión 2>
...

Asimismo existe la posibilidad de nuevas patologías que puedan
presentarse con el correr del tiempo y otras que puedan surgir de la
prueba y de la peritación médica a efectuar en autos.

Proveer de conformidad,

SERÁ JUSTICIA.

[Firma]
Matías Christian García Climent
Abogado
T° 97 F° 16 C.P.A.C.F.
```

## Generación del PDF (scripts/generar_manifiesta_pdf.py)

El script vive en `inicio-srt/scripts/generar_manifiesta_pdf.py`. Mismo estilo que `generar_relato_manifiesta_pdf.py` (template con placeholders `###...###`). Pasos:

1. Copiar el script a `/tmp/generar_manifiesta_<APELLIDO>.py`.
2. Reemplazar TODAS las variables marcadas con `###`:
   - `EXPEDIENTE_SRT`, `CARATULA`, `COMISION_NUM`, `COMISION_DELEGACION`
   - `DAMNIFICADO_APELLIDO_NOMBRE`, `DAMNIFICADO_DNI`, `DAMNIFICADO_CUIL`
   - `TIPO_ACCIDENTE` ("in itinere" o "laboral"), `FECHA_ACCIDENTE_STR` ("15 de marzo de 2025")
   - `LESIONES` — lista Python de strings, cada uno una lesión SIN número (el script los numera). Ej: `["Fractura del 4° metacarpiano...", "Material de osteosíntesis...", ...]`
   - `OUTPUT_PATH` — ruta absoluta al PDF de salida en la carpeta del cliente
   - `FIRMA_PATH` — `/Users/matiaschristiangarciacliment/.claude/skills/redaccion-laboral/templates/firma_letrado.jpg` (si está disponible) o el path equivalente del plugin instalado
3. Ejecutar `python3 /tmp/generar_manifiesta_<APELLIDO>.py`.

El script ya inyecta automáticamente la cláusula de reserva, "SERÁ JUSTICIA", la firma y los datos del letrado.

## Lo que NO hace este skill

- NO hace el relato "EL ACCIDENTE" (eso es `redaccion-laboral`).
- NO rellena el Anexo I (eso es `redaccion-laboral` + `rellenar_anexo_i.py`).
- NO arma demanda judicial.
- NO sube el PDF a Mi Ventanilla SRT — solo lo deja en la carpeta para que el usuario o una empleada lo cargue manualmente.

## Referencias

- `references/reglas-manifiesta.md` — Reglas completas de transformación de zonas lesionadas, ítems automáticos por zona afectada, casos especiales por mecanismo y cierre del escrito.
