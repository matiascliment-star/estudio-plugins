"""
Script template para generar el PDF de Relato + Manifiesta Lesiones.
Claude debe reemplazar las variables marcadas con ### antes de ejecutar.
"""
import sys
import os

# === VARIABLES A REEMPLAZAR POR CLAUDE ===
NOMBRE_TRABAJADOR = "###NOMBRE_TRABAJADOR###"  # Ej: "GONZALEZ ANDREA ROXANA"
RELATO_PARRAFOS = ###RELATO_PARRAFOS###  # Lista de strings, cada uno un párrafo del relato
LESIONES = ###LESIONES###  # Lista de strings, cada una un ítem numerado del manifiesta
OUTPUT_PATH = "###OUTPUT_PATH###"  # Ej: "/path/to/outputs/GONZALEZ_relato_manifiesta.pdf"
FIRMA_PATH = "###FIRMA_PATH###"  # Path al JPG de la firma del letrado
# === FIN VARIABLES ===

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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=A4,
    topMargin=2.5*cm,
    bottomMargin=2.5*cm,
    leftMargin=2.5*cm,
    rightMargin=2.5*cm
)

# Estilos
style_nombre = ParagraphStyle('Nombre', fontName='Times-Bold', fontSize=12, leading=14, alignment=TA_LEFT, spaceAfter=10)
style_titulo = ParagraphStyle('Titulo', fontName='Times-Bold', fontSize=11, leading=13, alignment=TA_LEFT, spaceAfter=6)
style_body = ParagraphStyle('Body', fontName='Times-Roman', fontSize=11, leading=11*1.25, alignment=TA_JUSTIFY, spaceAfter=6)

story = []

# === PÁGINA 1: NOMBRE + RELATO + HAGO SABER ===
story.append(Paragraph(NOMBRE_TRABAJADOR, style_nombre))
story.append(Paragraph("EL ACCIDENTE:", style_titulo))

for p in RELATO_PARRAFOS:
    story.append(Paragraph(p, style_body))

story.append(Spacer(1, 8))
story.append(Paragraph("Hago saber:", style_titulo))

HAGO_SABER = [
    "Sin perjuicio de lo denunciado y detallado en el presente formulario, se deja expresa constancia de que, atenta la proximidad temporal del accidente, así como la gravedad y el carácter traumático del hecho, existe la posibilidad de que algunas lesiones y/o patologías aún no se encuentren debidamente identificadas o descriptas al día de la fecha. Ello se debe a que, dada la etapa inicial del proceso, no se cuenta todavía con historia clínica ni estudios médicos suficientes que permitan determinar con precisión la totalidad de las lesiones sufridas por la parte damnificada.",
    "Asimismo, es necesario dejar constancia de que la parte accionante carece de los recursos económicos necesarios para costear la realización de una serie de estudios médicos que respalden lo denunciado, así como tampoco posee los conocimientos técnicos o médicos que le permitan diagnosticarse y determinar la totalidad de las lesiones que padece o podría estar padeciendo.",
    "Por todo lo expuesto, lo consignado en el presente formulario no implica ni excluye la posibilidad de que haya sufrido o se encuentre sufriendo otras lesiones o patologías como consecuencia directa del accidente aquí denunciado, ni que con posterioridad puedan manifestarse o desencadenarse nuevas afecciones derivadas del mismo."
]

for p in HAGO_SABER:
    story.append(Paragraph(p, style_body))

# === PÁGINA 2: MANIFIESTA LESIONES + FIRMA ===
story.append(PageBreak())
story.append(Paragraph("MANIFIESTA LESIONES – RECLAMA DAÑO FÍSICO Y PSÍQUICO.", style_titulo))
story.append(Spacer(1, 6))

for l in LESIONES:
    story.append(Paragraph(l, style_body))

# Firma como imagen
if os.path.exists(FIRMA_PATH):
    img = PILImage.open(FIRMA_PATH)
    img_w, img_h = img.size
    desired_w = 4 * cm
    scale = desired_w / img_w
    desired_h = img_h * scale
    story.append(Spacer(1, 30))
    firma_img = Image(FIRMA_PATH, width=desired_w, height=desired_h)
    firma_img.hAlign = 'CENTER'
    story.append(firma_img)
else:
    print(f"ADVERTENCIA: No se encontró la firma en {FIRMA_PATH}")

doc.build(story)
print(f"PDF generado: {OUTPUT_PATH}")
