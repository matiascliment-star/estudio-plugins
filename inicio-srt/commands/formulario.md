---
description: Genera relato, manifiesta lesiones y Anexo I desde la ficha del cliente
allowed-tools: Read, Write, Edit, Bash(pip:*), Bash(python3:*), Bash(cp:*), Bash(sed:*), Glob
model: opus
---

Generar los escritos de demanda laboral a partir de la ficha del cliente.

## Paso 0: Cargar conocimiento

Leer los siguientes archivos de referencia del skill ANTES de generar cualquier texto:

- `${CLAUDE_PLUGIN_ROOT}/skills/redaccion-laboral/references/system-prompt-relato.md` — Reglas de redacción del relato
- `${CLAUDE_PLUGIN_ROOT}/skills/redaccion-laboral/references/hago-saber-boilerplate.md` — Texto fijo del Hago Saber
- `${CLAUDE_PLUGIN_ROOT}/skills/redaccion-laboral/references/firma-letrado.md` — Datos de firma
- `${CLAUDE_PLUGIN_ROOT}/skills/redaccion-laboral/references/manifiesta-ejemplos.md` — Ejemplos de manifiesta
- `${CLAUDE_PLUGIN_ROOT}/skills/redaccion-laboral/references/anexo-i-campos.md` — Mapeo de campos del Anexo I

## Paso 1: Obtener datos del cliente (ficha + documentación complementaria)

Buscar en la carpeta del usuario TODOS los archivos disponibles: la ficha (.docx), alta médica (imagen/pdf), recibos de sueldo (imagen/pdf), DNI (imagen), y cualquier otro documento. Leer TODOS los archivos, no solo la ficha.

### 1a. Ficha del cliente (.docx o texto pegado)
Extraer los datos del accidente: fecha, hora, tipo, jornada, tareas, dónde se atendió, diagnóstico, relato crudo, zonas lesionadas.

### 1b. Alta médica (imagen .jpg/.png o PDF)
Leer la imagen del alta médica para extraer datos que la ficha normalmente no tiene:
- **Nombre de la ART** (suele figurar como "Institución" o en el encabezado, ej: "FEDERACION PATRONAL", "PREVENCIÓN ART", etc.)
- **Fecha de atención / consulta** (puede servir como referencia temporal si no hay fecha de accidente)
- **Diagnóstico médico** (complementa el de la ficha)
- **Especialidad del médico** (traumatología, clínica, etc.)
- **Si tiene alta médica** (buscar "ALTA SI/NO")
- **Fecha de reingreso laboral** (si figura)

### 1c. Recibo de sueldo (imagen .jpg/.png)
Leer el recibo para extraer datos del empleador y del trabajador:
- **Razón social del empleador** (encabezado del recibo)
- **CUIT del empleador**
- **Dirección del establecimiento**
- **CUIL del trabajador**
- **Categoría / tarea desempeñada**
- **Fecha de ingreso**
- **Obra social**

### 1d. DNI (imagen .jpg/.png)
Leer frente y dorso del DNI para extraer:
- **DNI número**
- **Nombre completo**
- **Fecha de nacimiento**
- **Domicilio**

### 1e. Consolidar datos
Cruzar la información de TODAS las fuentes. La prioridad es:
1. Ficha del cliente (datos del accidente, relato, zonas lesionadas)
2. Recibo de sueldo (datos del empleador, CUIL, categoría)
3. Alta médica (datos de la ART, diagnóstico médico, alta)
4. DNI (datos personales, domicilio)

Si un dato aparece en varias fuentes, usar el más completo/preciso.

Mostrar al usuario los datos extraídos consolidados y confirmar antes de continuar.

## Paso 2: Generar el MANIFIESTA LESIONES

Usando las zonas lesionadas de la ficha y las reglas de `manifiesta-ejemplos.md`:

1. Transformar cada zona en terminología médico-legal
2. Numerar con formato "1.-", "2.-", etc.
3. SIEMPRE que haya traumatismos, incluir "Lesión en nervios periféricos." (agregar "lesión radicular con secuelas electromiográficas" SOLO si hay columna afectada)
4. Incluir "Limitación funcional" y "Daño psíquico"
5. Cerrar con la cláusula de reserva

Mostrar al usuario el manifiesta generado para revisión.

## Paso 3: Generar el RELATO "EL ACCIDENTE"

Usando las reglas completas de `system-prompt-relato.md`:

1. Tomar los datos de la ficha + el manifiesta lesiones ya generado
2. Redactar el relato asegurando que CADA lesión del manifiesta tenga su mecanismo causal
3. Seguir la estructura APERTURA → DESARROLLO → CIERRE
4. Usar el vocabulario obligatorio

Mostrar al usuario el relato generado para revisión.

## Paso 4: Generar el PDF del relato + manifiesta

Usar el script template en `${CLAUDE_PLUGIN_ROOT}/scripts/generar_relato_manifiesta_pdf.py`.

1. Copiar el script a la carpeta de trabajo temporal
2. Reemplazar las variables marcadas con `###`:
   - `###NOMBRE_TRABAJADOR###` → nombre en mayúsculas
   - `###RELATO_PARRAFOS###` → lista Python de strings con cada párrafo del relato
   - `###LESIONES###` → lista Python de strings con cada ítem numerado del manifiesta
   - `###OUTPUT_PATH###` → ruta de salida (usar `/sessions/*/mnt/outputs/[APELLIDO]_relato_manifiesta.pdf`)
   - `###FIRMA_PATH###` → `${CLAUDE_PLUGIN_ROOT}/templates/firma_letrado.jpg`
3. Ejecutar el script con `python3`

El script genera automáticamente un PDF de 2 páginas:
- Página 1: Nombre + Relato + Hago Saber
- Página 2: Manifiesta Lesiones + firma como imagen

## Paso 5: Rellenar el Anexo I

Usar el script template en `${CLAUDE_PLUGIN_ROOT}/scripts/rellenar_anexo_i.py`.

1. Copiar el script a la carpeta de trabajo temporal
2. Reemplazar las variables marcadas con `###`:
   - Datos del trabajador (nombre, CUIL)
   - Datos del empleador (razón social, CUIT, establecimiento, localidad, provincia)
   - Datos de la ART (denominación, CUIT)
   - Datos del accidente (fechas, detalle, diagnósticos, prueba médica)
   - Tipo de accidente: "trabajo", "itinere", o "enfermedad_profesional"
   - Booleanos de atención: ATENCION_ART, ALTA_MEDICA, ATENCION_OS, ESTUDIO_OS
   - PREEXISTENCIA: **SIEMPRE dejar en False** (no completar nunca)
   - Booleanos de fundamentos: FUNDAMENTO_DOMICILIO, FUNDAMENTO_PRESTACION, FUNDAMENTO_REPORTA
   - `###TEMPLATE_PATH###` → `${CLAUDE_PLUGIN_ROOT}/templates/ANEXO_I_RELLENABLE.pdf`
   - `###OUTPUT_PATH###` → ruta de salida (usar `/sessions/*/mnt/outputs/[APELLIDO]_ANEXO_I.pdf`)
3. Los campos que no tengan dato en la ficha se dejan como string vacío ""
4. Ejecutar el script con `python3`

## Paso 6: Entregar los archivos

Presentar al usuario ambos PDFs con links de descarga:
1. El PDF del relato + manifiesta
2. El Anexo I rellenado

Preguntar si quiere ajustes a alguno de los textos.
