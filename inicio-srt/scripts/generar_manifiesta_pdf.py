"""
Script template para generar el PDF de SOLO Manifiesta Lesiones + Encabezado
para presentar ante la Comisión Médica Jurisdiccional de la SRT.
Claude debe reemplazar las variables marcadas con ### antes de ejecutar.
"""
import sys
import os

# === VARIABLES A REEMPLAZAR POR CLAUDE ===
EXPEDIENTE_SRT = "###EXPEDIENTE_SRT###"  # Ej: "404829/25"
CARATULA = "###CARATULA###"  # Ej: 'CISNEROS NANDO EMANUEL c/ PROVINCIA ART S.A. s/ Divergencia en la Determinación de la Incapacidad'
COMISION_NUM = "###COMISION_NUM###"  # Ej: "10"
COMISION_DELEGACION = "###COMISION_DELEGACION###"  # Ej: "Villa Urquiza"
DAMNIFICADO_APELLIDO_NOMBRE = "###DAMNIFICADO_APELLIDO_NOMBRE###"  # Ej: "CISNEROS, Nando Emanuel"
DAMNIFICADO_DNI = "###DAMNIFICADO_DNI###"  # Ej: "39.311.100"
DAMNIFICADO_CUIL = "###DAMNIFICADO_CUIL###"  # Ej: "20-39311100-4"
TIPO_ACCIDENTE = "###TIPO_ACCIDENTE###"  # "in itinere" | "laboral"
FECHA_ACCIDENTE_STR = "###FECHA_ACCIDENTE_STR###"  # Ej: "15 de marzo de 2025"
LESIONES = ###LESIONES###  # Lista de strings, cada uno un ítem (ya con su numeración "1.- ...", "2.- ..."), o solo el texto sin número y el script numera
OUTPUT_PATH = "###OUTPUT_PATH###"  # Ej: "/path/cliente/MANIFIESTA LESIONES - APELLIDO.pdf"
FIRMA_PATH = "###FIRMA_PATH###"  # Path al JPG de la firma del letrado
# === FIN VARIABLES ===

# Datos fijos del letrado
LETRADO_NOMBRE = "Matías Christian García Climent"
LETRADO_TOMO_FOLIO = "T° 97 F° 16 C.P.A.C.F."
LETRADO_CUIT = "20-31380619-8"
LETRADO_DOMICILIO = 'Av. Ricardo Balbín N° 2401, Piso 1°, Dpto. "A", C.A.B.A.'
LETRADO_EMAIL = "matiasgarciacliment@gmail.com"

CLAUSULA_RESERVA = (
    "Asimismo existe la posibilidad de nuevas patologías que puedan presentarse con el "
    "correr del tiempo y otras que puedan surgir de la prueba y de la peritación médica "
    "a efectuar en autos."
)

# Instalar dependencias si no están
try:
    from reportlab.lib.pagesizes import A4
except ImportError:
    os.system("pip install reportlab --break-system-packages -q")
    from reportlab.lib.pagesizes import A4

try:
    from PIL import Image as PILImage
except ImportError:
    os.system("pip install Pillow --break-system-packages -q")
    from PIL import Image as PILImage

from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=A4,
    topMargin=2.5 * cm,
    bottomMargin=2.5 * cm,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
)

# Estilos
style_ref = ParagraphStyle(
    "Ref", fontName="Times-Bold", fontSize=11, leading=14,
    alignment=TA_LEFT, spaceAfter=4
)
style_titulo_centro = ParagraphStyle(
    "TituloCentro", fontName="Times-Bold", fontSize=12, leading=16,
    alignment=TA_CENTER, spaceBefore=10, spaceAfter=14
)
style_body = ParagraphStyle(
    "Body", fontName="Times-Roman", fontSize=11, leading=14,
    alignment=TA_JUSTIFY, firstLineIndent=1.25 * cm, spaceAfter=8
)
style_body_noindent = ParagraphStyle(
    "BodyNoIndent", fontName="Times-Roman", fontSize=11, leading=14,
    alignment=TA_JUSTIFY, spaceAfter=8
)
style_item = ParagraphStyle(
    "Item", fontName="Times-Roman", fontSize=11, leading=14,
    alignment=TA_JUSTIFY, leftIndent=0.6 * cm, spaceAfter=6
)
style_sera = ParagraphStyle(
    "Sera", fontName="Times-Bold", fontSize=12, leading=16,
    alignment=TA_CENTER, spaceBefore=14, spaceAfter=14
)
style_firma = ParagraphStyle(
    "Firma", fontName="Times-Roman", fontSize=11, leading=14,
    alignment=TA_CENTER
)

story = []

# === REFERENCIA DEL EXPEDIENTE ===
story.append(Paragraph(f"Expediente SRT N° {EXPEDIENTE_SRT}", style_ref))
story.append(Paragraph(f'"{CARATULA}"', style_ref))
story.append(Paragraph(
    f"Comisión Médica Jurisdiccional N° {COMISION_NUM} – Delegación {COMISION_DELEGACION}",
    style_ref
))
story.append(Spacer(1, 14))

# === TÍTULO CENTRADO ===
story.append(Paragraph(
    "MANIFIESTA LESIONES – RECLAMA DAÑO FÍSICO Y PSÍQUICO.",
    style_titulo_centro
))

# === FÓRMULA DE PRESENTACIÓN ===
story.append(Paragraph(
    f"<b>Comisión Médica Jurisdiccional N° {COMISION_NUM} – Delegación {COMISION_DELEGACION}:</b>",
    style_body_noindent
))
story.append(Spacer(1, 6))

presentacion = (
    f"<b>{LETRADO_NOMBRE}</b>, abogado, {LETRADO_TOMO_FOLIO}, "
    f"CUIT {LETRADO_CUIT}, con domicilio legal constituido en {LETRADO_DOMICILIO}, "
    f"y domicilio electrónico en <i>{LETRADO_EMAIL}</i>, en mi carácter de letrado "
    f"patrocinante de <b>{DAMNIFICADO_APELLIDO_NOMBRE}</b>, DNI {DAMNIFICADO_DNI}, "
    f"CUIL {DAMNIFICADO_CUIL}, en autos caratulados <b>\"{CARATULA}\"</b>, "
    f"Expediente SRT N° <b>{EXPEDIENTE_SRT}</b>, ante V.S. me presento y "
    f"respetuosamente digo:"
)
story.append(Paragraph(presentacion, style_body))

# === INTRODUCCIÓN AL MANIFIESTA ===
intro = (
    f"Que vengo por el presente a manifestar las lesiones que como consecuencia "
    f"del accidente <i>{TIPO_ACCIDENTE}</i> de fecha {FECHA_ACCIDENTE_STR} padece "
    f"mi instituyente, a saber:"
)
story.append(Paragraph(intro, style_body))
story.append(Spacer(1, 6))

# === ÍTEMS NUMERADOS ===
for idx, lesion in enumerate(LESIONES, start=1):
    # si la lesión ya viene con el "N.- " adelante, respetamos; si no, lo numeramos
    if lesion.lstrip().startswith(tuple(f"{n}.-" for n in range(1, 100))):
        story.append(Paragraph(lesion, style_item))
    else:
        story.append(Paragraph(f"<b>{idx}.-</b> {lesion}", style_item))

# === CLÁUSULA DE RESERVA ===
story.append(Spacer(1, 8))
story.append(Paragraph(CLAUSULA_RESERVA, style_body))

# === CIERRE ===
story.append(Paragraph("Proveer de conformidad,", style_body))
story.append(Paragraph("<b>SERÁ JUSTICIA.</b>", style_sera))

# === FIRMA ===
if FIRMA_PATH and os.path.exists(FIRMA_PATH):
    img = PILImage.open(FIRMA_PATH)
    img_w, img_h = img.size
    desired_w = 4 * cm
    scale = desired_w / img_w
    desired_h = img_h * scale
    story.append(Spacer(1, 24))
    firma_img = Image(FIRMA_PATH, width=desired_w, height=desired_h)
    firma_img.hAlign = "CENTER"
    story.append(firma_img)
else:
    story.append(Spacer(1, 36))

story.append(Paragraph(LETRADO_NOMBRE, style_firma))
story.append(Paragraph("Abogado", style_firma))
story.append(Paragraph(LETRADO_TOMO_FOLIO, style_firma))

doc.build(story)
print(f"PDF generado: {OUTPUT_PATH}")
