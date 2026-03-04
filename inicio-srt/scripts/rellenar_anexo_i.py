"""
Script template para rellenar el Anexo I (formulario PDF de la SRT).
Claude debe reemplazar las variables marcadas con ### antes de ejecutar.
"""
import os
from datetime import date

# === VARIABLES A REEMPLAZAR POR CLAUDE ===
# Datos del trabajador
TRABAJADOR_NOMBRE = "###TRABAJADOR_NOMBRE###"
TRABAJADOR_CUIL = "###TRABAJADOR_CUIL###"  # Dejar "" si no se tiene

# Datos del empleador
EMPLEADOR_RAZON_SOCIAL = "###EMPLEADOR_RAZON_SOCIAL###"
EMPLEADOR_CUIT = "###EMPLEADOR_CUIT###"
EMPLEADOR_ESTABLECIMIENTO = "###EMPLEADOR_ESTABLECIMIENTO###"
EMPLEADOR_LOCALIDAD = "###EMPLEADOR_LOCALIDAD###"
EMPLEADOR_PROVINCIA = "###EMPLEADOR_PROVINCIA###"

# Datos de la ART
ART_DENOMINACION = "###ART_DENOMINACION###"
ART_CUIT = "###ART_CUIT###"

# Datos del accidente
FECHA_OCURRENCIA = "###FECHA_OCURRENCIA###"
FECHA_DENUNCIA = "###FECHA_DENUNCIA###"
FECHA_BAJA_LABORAL = "###FECHA_BAJA_LABORAL###"
DETALLE_ACCIDENTE = "Ver hoja adicional adjunta."

# Datos médicos
AFECCIONES_DIAGNOSTICOS = "Ver hoja adicional adjunta."
PRUEBA_MEDICA = "###PRUEBA_MEDICA###"
PRUEBA_JUDICIAL = "###PRUEBA_JUDICIAL###"

# Comisión médica
COMISION_MEDICA_NUM = "###COMISION_MEDICA_NUM###"
COMISION_MEDICA_JURISDICCION = "###COMISION_MEDICA_JURISDICCION###"

# Tipo de accidente: "trabajo", "itinere", o "enfermedad_profesional"
TIPO_ACCIDENTE = "###TIPO_ACCIDENTE###"

# Atención: True/False
ATENCION_ART = ###ATENCION_ART###
ALTA_MEDICA = ###ALTA_MEDICA###
ATENCION_OS = ###ATENCION_OS###
ESTUDIO_OS = ###ESTUDIO_OS###
PREEXISTENCIA = False  # NUNCA completar preexistencias

# Fundamentos (True/False)
FUNDAMENTO_DOMICILIO = ###FUNDAMENTO_DOMICILIO###
FUNDAMENTO_PRESTACION = ###FUNDAMENTO_PRESTACION###
FUNDAMENTO_REPORTA = ###FUNDAMENTO_REPORTA###

# Preexistencias - NO COMPLETAR
PREEX_PORCENTAJE = ""
PREEX_REGION_CUERPO = ""

# Paths
TEMPLATE_PATH = "###TEMPLATE_PATH###"
OUTPUT_PATH = "###OUTPUT_PATH###"
# === FIN VARIABLES ===

# Instalar dependencias si no están
try:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import NameObject
except ImportError:
    os.system("pip install PyPDF2 --break-system-packages -q")
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import NameObject

# Datos fijos del letrado
LETRADO_NOMBRE = "Matias Christian García Climent"
LETRADO_MATRICULA = "T°97 F°16 CPACF"
LETRADO_CUIT_DOMICILIO = "20313806198 matiasgarciacliment@gmail.com"

reader = PdfReader(TEMPLATE_PATH)
writer = PdfWriter()
writer.append(reader)

# Campos de texto
text_fields = {
    "trabajador_nombre": TRABAJADOR_NOMBRE,
    "trabajador_cuil": TRABAJADOR_CUIL,
    "empleador_razon_social": EMPLEADOR_RAZON_SOCIAL,
    "empleador_cuit": EMPLEADOR_CUIT,
    "empleador_establecimiento": EMPLEADOR_ESTABLECIMIENTO,
    "empleador_localidad": EMPLEADOR_LOCALIDAD,
    "empleador_provincia": EMPLEADOR_PROVINCIA,
    "art_denominacion": ART_DENOMINACION,
    "art_cuit": ART_CUIT,
    "fecha_ocurrencia": FECHA_OCURRENCIA,
    "fecha_denuncia": FECHA_DENUNCIA,
    "fecha_baja_laboral": FECHA_BAJA_LABORAL,
    "detalle_accidente": DETALLE_ACCIDENTE,
    "afecciones_diagnosticos": AFECCIONES_DIAGNOSTICOS,
    "prueba_medica": PRUEBA_MEDICA,
    "prueba_judicial": PRUEBA_JUDICIAL,
    "comision_medica_num": COMISION_MEDICA_NUM,
    "comision_medica_jurisdiccion": COMISION_MEDICA_JURISDICCION,
    "preex_porcentaje": PREEX_PORCENTAJE,
    "preex_region_cuerpo": PREEX_REGION_CUERPO,
    "letrado_nombre": LETRADO_NOMBRE,
    "letrado_cuit_domicilio": LETRADO_CUIT_DOMICILIO,
    "letrado_matricula": LETRADO_MATRICULA,
    "firma_letrado_aclaracion": LETRADO_NOMBRE,
    "firma_trabajador_aclaracion": TRABAJADOR_NOMBRE,
    "fecha_firma": date.today().strftime("%d/%m/%Y"),
}

# Rellenar campos de texto en todas las páginas
for page_num in range(len(writer.pages)):
    try:
        writer.update_page_form_field_values(writer.pages[page_num], text_fields)
    except Exception as e:
        print(f"Advertencia página {page_num}: {e}")

# Función para marcar checkboxes
def set_checkbox(writer, field_name, value=True):
    for page in writer.pages:
        if "/Annots" in page:
            for annot in page["/Annots"]:
                annot_obj = annot.get_object()
                if annot_obj.get("/T") == field_name:
                    if value:
                        annot_obj.update({
                            NameObject("/V"): NameObject("/Yes"),
                            NameObject("/AS"): NameObject("/Yes")
                        })
                    else:
                        annot_obj.update({
                            NameObject("/V"): NameObject("/Off"),
                            NameObject("/AS"): NameObject("/Off")
                        })

# Tipo de accidente
if TIPO_ACCIDENTE == "trabajo":
    set_checkbox(writer, "tipo_accidente_trabajo", True)
elif TIPO_ACCIDENTE == "itinere":
    set_checkbox(writer, "tipo_accidente_itinere", True)
elif TIPO_ACCIDENTE == "enfermedad_profesional":
    set_checkbox(writer, "tipo_enfermedad_profesional", True)

# Atención médica
set_checkbox(writer, "atencion_art_si", ATENCION_ART)
set_checkbox(writer, "atencion_art_no", not ATENCION_ART)
set_checkbox(writer, "alta_medica_si", ALTA_MEDICA)
set_checkbox(writer, "alta_medica_no", not ALTA_MEDICA)
set_checkbox(writer, "atencion_os_si", ATENCION_OS)
set_checkbox(writer, "atencion_os_no", not ATENCION_OS)
set_checkbox(writer, "estudio_os_si", ESTUDIO_OS)
set_checkbox(writer, "estudio_os_no", not ESTUDIO_OS)

# Preexistencias
set_checkbox(writer, "preexistencia_si", PREEXISTENCIA)
set_checkbox(writer, "preexistencia_no", not PREEXISTENCIA)

# Fundamentos
set_checkbox(writer, "fundamento_domicilio", FUNDAMENTO_DOMICILIO)
set_checkbox(writer, "fundamento_prestacion", FUNDAMENTO_PRESTACION)
set_checkbox(writer, "fundamento_reporta", FUNDAMENTO_REPORTA)

with open(OUTPUT_PATH, "wb") as f:
    writer.write(f)

print(f"Anexo I generado: {OUTPUT_PATH}")
