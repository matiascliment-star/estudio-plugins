"""
Script template para generar el PDF del escrito IMPUGNA ITM
para presentar ante la Comisión Médica Jurisdiccional de la SRT.

Claude debe reemplazar las variables marcadas con ### antes de ejecutar.

Bloques modulares: cualquiera de A, B, C puede valer False; el escrito se
arma con los que apliquen. El título se ajusta automáticamente.
"""
import os

# === VARIABLES A REEMPLAZAR POR CLAUDE ===
EXPEDIENTE_SRT = "###EXPEDIENTE_SRT###"  # Ej: "503338/25"
CARATULA = "###CARATULA###"  # Ej: 'NOLASCO ADAN CARLOS c/ EXPERTA ART S.A. s/ Divergencia en la Determinación de la Incapacidad'
COMISION_NUM = "###COMISION_NUM###"  # Ej: "10"
COMISION_DELEGACION = "###COMISION_DELEGACION###"  # Ej: "Villa Urquiza"
DAMNIFICADO_APELLIDO_NOMBRE = "###DAMNIFICADO_APELLIDO_NOMBRE###"  # Ej: "NOLASCO, ADAN CARLOS"
DAMNIFICADO_DNI = "###DAMNIFICADO_DNI###"  # Ej: "37.554.437"
DAMNIFICADO_CUIL = "###DAMNIFICADO_CUIL###"  # Ej: "20-37554437-8"
FECHA_ITM = "###FECHA_ITM###"  # Ej: "27/04/2026"
FIRMANTE_ITM = "###FIRMANTE_ITM###"  # Ej: "Juan Cruz Bertone"
MATRICULA_ITM = "###MATRICULA_ITM###"  # Ej: "146.480"

# Bloques que aplican (True/False)
BLOQUE_A_FALTA_EXAMEN = ###BLOQUE_A###  # True si el ITM no citó a examen físico
BLOQUE_B_FALTA_ESTUDIOS = ###BLOQUE_B###  # True si "No se solicitan" estudios
BLOQUE_C_FALTA_PATOLOGIAS = ###BLOQUE_C###  # True si el ITM ignoró patologías reclamadas

# Datos para Bloque A (solo si BLOQUE_A_FALTA_EXAMEN)
ZONAS_RECLAMADAS_PARA_A = "###ZONAS_RECLAMADAS_PARA_A###"  # Ej: "tobillo y pie derecho, columna lumbar"

# Datos para Bloque B (solo si BLOQUE_B_FALTA_ESTUDIOS)
# Texto puente describiendo los estudios ya obrantes (puede ser "" si no hay)
PARRAFO_ESTUDIOS_PREVIOS = "###PARRAFO_ESTUDIOS_PREVIOS###"
# Lista de estudios pedidos (cada elemento es un string en HTML, ya con <b>...</b>)
ESTUDIOS_PEDIDOS = ###ESTUDIOS_PEDIDOS###  # Lista Python de strings
# Lista corta para el petitorio (cada elemento label corto)
ESTUDIOS_PETITORIO = ###ESTUDIOS_PETITORIO###  # Lista Python de strings

# Datos para Bloque C (solo si BLOQUE_C_FALTA_PATOLOGIAS)
ZONAS_QUE_ITM_RECONOCIO = "###ZONAS_QUE_ITM_RECONOCIO###"  # Ej: '"TOBILLO Y PIE DERECHO"'
PATOLOGIAS_IGNORADAS_INTRO = "###PATOLOGIAS_IGNORADAS_INTRO###"  # Ej: 'una patología expresamente reclamada en el escrito de inicio: el <b>DAÑO PSÍQUICO</b> bajo la forma de reacción vivencial anormal neurótica de grado III. Asimismo, …'
FOJAS_INICIO = "###FOJAS_INICIO###"  # Ej: "12/14"
CITA_TEXTUAL_INICIO = "###CITA_TEXTUAL_INICIO###"  # Ej: "A raíz del accidente de marras el trabajador presenta daños físicos y psíquicos…"
PARRAFO_HALLAZGOS_HC = "###PARRAFO_HALLAZGOS_HC###"  # Texto opcional de hallazgos de HC ignorados; "" si no aplica
PATOLOGIAS_RECLAMADAS = ###PATOLOGIAS_RECLAMADAS###  # Lista Python de strings
ZONAS_IGNORADAS_PETITORIO = "###ZONAS_IGNORADAS_PETITORIO###"  # Ej: "el daño psíquico, las lesiones de los dedos del pie derecho…"

OUTPUT_PATH = "###OUTPUT_PATH###"  # Ej: "/path/cliente/IMPUGNA ITM - APELLIDO.pdf"
FIRMA_PATH = "###FIRMA_PATH###"  # Path al JPG de la firma
# === FIN VARIABLES ===

# Datos fijos del letrado
LETRADO_NOMBRE = "Matías Christian García Climent"
LETRADO_TOMO_FOLIO = "T° 97 F° 16 C.P.A.C.F."
LETRADO_CUIT = "20-31380619-8"
LETRADO_DOMICILIO = 'Av. Ricardo Balbín N° 2401, Piso 1°, Dpto. "A", C.A.B.A.'
LETRADO_EMAIL = "matiasgarciacliment@gmail.com"

# Instalar dependencias si faltan
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


# === ESTILOS ===
style_ref = ParagraphStyle("Ref", fontName="Times-Bold", fontSize=11, leading=14, alignment=TA_LEFT, spaceAfter=4)
style_titulo = ParagraphStyle("Titulo", fontName="Times-Bold", fontSize=12, leading=16, alignment=TA_CENTER, spaceBefore=10, spaceAfter=14)
style_body = ParagraphStyle("Body", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_JUSTIFY, firstLineIndent=1.25 * cm, spaceAfter=8)
style_body_noindent = ParagraphStyle("BodyNoIndent", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_JUSTIFY, spaceAfter=8)
style_seccion = ParagraphStyle("Seccion", fontName="Times-Bold", fontSize=11, leading=14, alignment=TA_LEFT, spaceBefore=10, spaceAfter=8)
style_item = ParagraphStyle("Item", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_JUSTIFY, leftIndent=0.6 * cm, spaceAfter=4)
style_subitem = ParagraphStyle("SubItem", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_JUSTIFY, leftIndent=1.2 * cm, spaceAfter=4)
style_sera = ParagraphStyle("Sera", fontName="Times-Bold", fontSize=12, leading=16, alignment=TA_CENTER, spaceBefore=14, spaceAfter=14)
style_firma = ParagraphStyle("Firma", fontName="Times-Roman", fontSize=11, leading=14, alignment=TA_CENTER)


# === CONSTRUCCIÓN DEL TÍTULO Y LISTADO DE CAUSALES ===
titulo_partes = ["IMPUGNA INFORME TÉCNICO MÉDICO"]
causales_obj = []
if BLOQUE_A_FALTA_EXAMEN:
    titulo_partes.append("SOLICITA CITACIÓN A EXAMEN FÍSICO")
    causales_obj.append("a) la omisión de citar a mi representado al examen físico indispensable")
if BLOQUE_B_FALTA_ESTUDIOS:
    titulo_partes.append("SOLICITA ESTUDIOS COMPLEMENTARIOS")
    causales_obj.append("b) la omisión de solicitar los estudios complementarios indispensables para diagnosticar y graduar la incapacidad")
if BLOQUE_C_FALTA_PATOLOGIAS:
    titulo_partes.append("RECLAMA ANÁLISIS DE LA TOTALIDAD DE LAS PATOLOGÍAS DENUNCIADAS")
    causales_obj.append("c) la omisión de analizar la totalidad de las patologías reclamadas en el escrito de inicio")
TITULO = " – ".join(titulo_partes) + "."
CAUSALES = "; ".join(causales_obj) + "."


# === DOCUMENTO ===
doc = SimpleDocTemplate(
    OUTPUT_PATH, pagesize=A4,
    topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    leftMargin=2.5 * cm, rightMargin=2.5 * cm,
)
story = []

# Encabezado
story.append(Paragraph(f"Expediente SRT N° {EXPEDIENTE_SRT}", style_ref))
story.append(Paragraph(f'"{CARATULA}"', style_ref))
story.append(Paragraph(f"Comisión Médica Jurisdiccional N° {COMISION_NUM} – Delegación {COMISION_DELEGACION}", style_ref))
story.append(Spacer(1, 14))

# Título centrado con subrayado
story.append(Paragraph(f"<u>{TITULO}</u>", style_titulo))

# Fórmula de presentación
story.append(Paragraph(f"<b>Comisión Médica Jurisdiccional N° {COMISION_NUM} – Delegación {COMISION_DELEGACION}:</b>", style_body_noindent))
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

# I.- OBJETO
story.append(Paragraph("<b><u>I.- OBJETO.</u></b>", style_seccion))
story.append(Paragraph(
    f"Que vengo en legal tiempo y forma a <b>IMPUGNAR</b> el Informe Técnico Médico de "
    f"fecha {FECHA_ITM}, suscripto por el Dr. {FIRMANTE_ITM}, M.N. {MATRICULA_ITM}, por "
    f"resultar incompleto, infundado e inhábil para servir de base al dictamen médico "
    f"que esta Comisión deba emitir.",
    style_body
))
story.append(Paragraph(
    f"La impugnación se funda en los siguientes déficits que, conjuntamente "
    f"considerados, vulneran la garantía de defensa de mi representado (art. 18 C.N.) "
    f"y la finalidad revisora del procedimiento de divergencia (Res. SRT N° 298/17): "
    f"{CAUSALES}",
    style_body
))

# II.- FUNDAMENTOS
story.append(Paragraph("<b><u>II.- FUNDAMENTOS DE LA IMPUGNACIÓN.</u></b>", style_seccion))

# Bloque A
if BLOQUE_A_FALTA_EXAMEN:
    story.append(Paragraph("<b><u>A.- AUSENCIA DE CITACIÓN A EXAMEN FÍSICO.</u></b>", style_seccion))
    story.append(Paragraph(
        "El ITM impugnado consigna en su evaluación médica que <b>NO</b> se requiere "
        "audiencia ni examen físico del damnificado, omitiendo así una etapa "
        "esencial del procedimiento.",
        style_body
    ))
    story.append(Paragraph(
        "La determinación de incapacidades laborales —objeto del presente trámite— "
        "exige inexorablemente la inspección directa del cuerpo del trabajador a fin "
        "de comprobar las maniobras semiológicas, las amplitudes de movimiento "
        "articular, la simetría muscular, la presencia de cicatrices, el dolor a la "
        "palpación y los signos clínicos compatibles con las patologías denunciadas. "
        "Sin examen físico, todo cálculo de incapacidad bajo el Baremo del Decreto "
        "659/96 deviene puramente conjetural.",
        style_body
    ))
    story.append(Paragraph(
        f"La omisión es particularmente grave en autos, donde se reclaman secuelas "
        f"en {ZONAS_RECLAMADAS_PARA_A} que no pueden valorarse sin contacto directo "
        f"con el damnificado.",
        style_body
    ))
    story.append(Paragraph(
        "Solicito, en consecuencia, que se cite a mi representado a examen físico "
        "interno por ante esta Comisión Médica, con la presencia del suscripto.",
        style_body
    ))

# Bloque B
if BLOQUE_B_FALTA_ESTUDIOS:
    story.append(Paragraph("<b><u>B.- OMISIÓN DE SOLICITAR ESTUDIOS COMPLEMENTARIOS INDISPENSABLES.</u></b>", style_seccion))
    story.append(Paragraph(
        'El ITM consigna textualmente en el rubro "Indicaciones/Estudios Solicitados": '
        '<b>"No se solicitan"</b>. La omisión es manifiestamente arbitraria y compromete '
        'la validez técnica del informe.',
        style_body
    ))
    if PARRAFO_ESTUDIOS_PREVIOS.strip():
        story.append(Paragraph(PARRAFO_ESTUDIOS_PREVIOS, style_body))
    story.append(Paragraph(
        "La determinación de incapacidad bajo el Baremo del Decreto 659/96 exige "
        "distinguir con precisión entre un esguince residual, una lesión "
        "ligamentaria estructural, una lesión condral asociada y una secuela "
        "tendinosa con limitación funcional —todas con porcentajes diferenciados—. "
        "Esa distinción es imposible sin estudios de mayor resolución. Resultan "
        "indispensables, en consecuencia:",
        style_body
    ))
    for est in ESTUDIOS_PEDIDOS:
        story.append(Paragraph(f"· {est}", style_subitem))
    story.append(Paragraph(
        "La omisión de estos estudios convierte al ITM en un acto formal sin "
        "sustento técnico-objetivo, en directa infracción a lo establecido en la "
        "Res. SRT N° 298/17 y al Baremo del Decreto 659/96, que requiere "
        "parámetros mensurables para fijar el porcentaje de incapacidad.",
        style_body
    ))

# Bloque C
if BLOQUE_C_FALTA_PATOLOGIAS:
    story.append(Paragraph("<b><u>C.- OMISIÓN DE ANALIZAR LA TOTALIDAD DE LAS PATOLOGÍAS DENUNCIADAS.</u></b>", style_seccion))
    story.append(Paragraph(
        f'El ITM circunscribe la futura evaluación a {ZONAS_QUE_ITM_RECONOCIO} '
        f'(ver "Análisis del Caso"), omitiendo lisa y llanamente '
        f'{PATOLOGIAS_IGNORADAS_INTRO}',
        style_body
    ))
    story.append(Paragraph(
        f'En la presentación inaugural de fojas {FOJAS_INICIO}, capítulo III, mi '
        f'representado denunció con toda claridad: "<i>{CITA_TEXTUAL_INICIO}</i>". '
        f'El ITM no formula una sola consideración al respecto, no propone '
        f'psicodiagnóstico ni dispone interconsulta con psicólogo o médico psiquiatra '
        f'que evalúe la patología denunciada.',
        style_body
    ))
    if PARRAFO_HALLAZGOS_HC.strip():
        story.append(Paragraph(PARRAFO_HALLAZGOS_HC, style_body))
    story.append(Paragraph(
        "Resulta improcedente que la Comisión Médica acote su examen al diagnóstico "
        "que la ART reconoció en el alta, pues ello vacía de contenido el trámite de "
        "divergencia, cuyo objeto es precisamente revisar —y, en su caso, ampliar— "
        "lo decidido por la aseguradora. Reitero, para que la Comisión las evalúe en "
        "su totalidad y el dictamen se pronuncie expresamente sobre cada una de "
        "ellas, las patologías reclamadas:",
        style_body
    ))
    for idx, pat in enumerate(PATOLOGIAS_RECLAMADAS, 1):
        story.append(Paragraph(f"<b>{idx}.-</b> {pat}", style_item))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "La omisión de cualquiera de estas patologías en el dictamen ulterior "
        "configurará vicio de motivación insanable, susceptible de revisión por la "
        "vía recursiva del art. 2 de la Ley 27.348 y, eventualmente, por las "
        "restantes vías de impugnación judicial.",
        style_body
    ))

# III.- PETITORIO
story.append(Paragraph("<b><u>III.- PETITORIO.</u></b>", style_seccion))
story.append(Paragraph("Por todo lo expuesto, solicito a V.S.:", style_body))

peticiones = []
peticiones.append(
    f"Tenga por <b>impugnado</b> el Informe Técnico Médico de fecha {FECHA_ITM} "
    f"en los términos del presente."
)
if BLOQUE_A_FALTA_EXAMEN:
    peticiones.append(
        "Disponga la <b>citación</b> de mi representado a examen físico interno "
        "por ante esta Comisión Médica, con notificación al suscripto."
    )
if BLOQUE_B_FALTA_ESTUDIOS:
    estudios_str = "; ".join(f"<b>{chr(96+i+1)})</b> {e}" for i, e in enumerate(ESTUDIOS_PETITORIO))
    peticiones.append(
        f"Ordene, previo al dictamen, la realización de los siguientes estudios "
        f"complementarios, con notificación al suscripto de la fecha, hora y lugar "
        f"de su producción: {estudios_str}."
    )
if BLOQUE_C_FALTA_PATOLOGIAS:
    peticiones.append(
        f"Disponga que la evaluación médica y el dictamen se extiendan a la "
        f"<b>totalidad</b> de las patologías denunciadas en este escrito y en el de "
        f"inicio, incluyendo —especialmente— {ZONAS_IGNORADAS_PETITORIO}."
    )
peticiones.append(
    "Producidas las medidas precedentes, se emita un nuevo Informe Técnico Médico "
    "que sirva de base válida al dictamen."
)
peticiones.append(
    "Tenga presente la <b>reserva del caso federal</b> (art. 14 ley 48) y de las "
    "vías de revisión judicial previstas en la ley 27.348 para el supuesto de que "
    "las medidas no se adopten."
)
for idx, p in enumerate(peticiones, 1):
    story.append(Paragraph(f"<b>{idx})</b> {p}", style_item))

story.append(Spacer(1, 10))
story.append(Paragraph("Proveer de conformidad,", style_body))
story.append(Paragraph("<b>SERÁ JUSTICIA.</b>", style_sera))

# Firma
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
