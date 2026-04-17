"""
Template: generador de escrito de pedido de giro de honorarios (PJN/CABA).

USO:
  1. Copiar este archivo a /tmp/ y editarlo con los datos del caso concreto.
  2. Completar el dict CASO (ver abajo).
  3. Ejecutar: python3 /tmp/generar_giro.py
  4. El DOCX se guarda en ~/Desktop/{CARATULA_SHORT}_giro_honorarios.docx

REQUISITOS:
  - Las imágenes embebidas se toman de:
      ~/.claude/skills/pedir-giro-honorarios/assets/constancia_afip.png
      ~/.claude/skills/pedir-giro-honorarios/assets/constancia_cbu.png

CONVENCIÓN FORMATO (feedback_formato_escritos.md):
  - Times New Roman 12pt, interlineado 1.5
  - Márgenes: sup 2 / inf 2 / izq 3 / der 2 cm
  - Título principal justificado, negrita + subrayado, sin sangría
  - Sr. Juez: izquierda, negrita, sin sangría
  - 1er párrafo: sangría 1.5 cm
  - Secciones: sangría 1.25 cm, negrita + subrayado, una línea en blanco antes
  - Cuerpo: justificado, sangría 1.25 cm
"""

from docx import Document
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

# ======================================================================
# DATOS DEL CASO — EDITAR
# ======================================================================
CASO = {
    # Datos del expediente
    'caratula': 'APELLIDO, NOMBRE C/ DEMANDADA S/RECURSO LEY 27348',
    'numero_expte': 'CNT 000000/2025',
    'caratula_short': 'apellido',  # para nombre de archivo

    # Variante: 'A' (giro simple) o 'B' (traba embargo + giro)
    'variante': 'A',

    # Montos
    'honorarios': '1.000.000,00',  # capital sin IVA
    'iva': '210.000,00',            # 21%
    'monto_total': '1.210.000,00',  # honorarios + IVA

    # Fechas de depósitos (formato DD/MM/YYYY)
    # Variante A: usar FECHA_DEPOSITO y FECHA_EMBARGO (del proveído que ordenó embargo sobre la cuenta)
    # Variante B: usar FECHAS_DEPOSITOS (texto libre, ej: "07/11/2025 y 11/04/2026")
    'fecha_deposito': '23/10/2022',
    'fecha_embargo': '12/03/2026',
    'fechas_depositos': '07/11/2025 y 11/04/2026',

    # Contexto para variante B (recurso pendiente)
    'recurso_pendiente': 'queja ante la CSJN',

    # Datos fijos del suscripto (no tocar salvo que cambien)
    'letrado_nombre': 'MATÍAS CHRISTIAN GARCÍA CLIMENT',
    'letrado_tomo_folio': 'T° 97 F° 16 del C.P.A.C.F.',
    'letrado_cuit': '20-31380619-8',
    'letrado_dni': '31.380.619',
    'letrado_domicilio': 'Av. Ricardo Balbín 2368, CABA',
    'letrado_zona': '204',
    'letrado_email': 'matiasgarciacliment@gmail.com',
    'letrado_tel': '4-545-2488',
    'letrado_de': '2031306198',
    'banco': 'Banco de la Ciudad de Buenos Aires',
    'caja_ahorro': '000000260200356738',
    'cbu': '0290026110000003567389',
}

ASSETS_DIR = os.path.expanduser('~/.claude/skills/pedir-giro-honorarios/assets')

# ======================================================================
# CONSTRUCTOR DE DOCUMENTO
# ======================================================================
doc = Document()
for s in doc.sections:
    s.top_margin = Cm(2); s.bottom_margin = Cm(2)
    s.left_margin = Cm(3); s.right_margin = Cm(2)

st = doc.styles['Normal']
st.font.name = 'Times New Roman'; st.font.size = Pt(12)
pf = st.paragraph_format
pf.line_spacing = 1.5
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.first_line_indent = Cm(1.25)


def _run(p, t, bold=False, underline=False):
    r = p.add_run(t)
    r.font.name = 'Times New Roman'; r.font.size = Pt(12)
    r.bold = bold; r.underline = underline
    return r


def add_titulo(t):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = 1.5
    _run(p, t, bold=True, underline=True)


def add_encabezado(t):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = 1.5
    _run(p, t, bold=True)


def add_seccion(t):
    doc.add_paragraph()  # linea en blanco
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.line_spacing = 1.5
    _run(p, t, bold=True, underline=True)


def add_par(t, indent=1.25, bold=False, align='justify'):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = {'justify': WD_ALIGN_PARAGRAPH.JUSTIFY, 'center': WD_ALIGN_PARAGRAPH.CENTER, 'left': WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.first_line_indent = Cm(indent) if indent else Cm(0)
    p.paragraph_format.line_spacing = 1.5
    _run(p, t, bold=bold)


def add_par_mixto(segs, indent=1.25):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(indent)
    p.paragraph_format.line_spacing = 1.5
    for seg in segs:
        if len(seg) == 3:
            t, b, u = seg
        else:
            t, b = seg; u = False
        _run(p, t, bold=b, underline=u)


def add_constancia(titulo, imagen, width_inches):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(titulo); r.font.name = 'Times New Roman'; r.font.size = Pt(12); r.bold = True
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.add_run().add_picture(imagen, width=Inches(width_inches))


# ======================================================================
# TÍTULO
# ======================================================================
if CASO['variante'] == 'B':
    titulo = ('TRABA EMBARGO SOBRE FONDOS DEPOSITADOS. SE LIBRE GIRO ELECTRÓNICO '
              'EN CONCEPTO DE HONORARIOS. ADJUNTA DOCUMENTACIÓN. DECLARA BAJO '
              'JURAMENTO. HACE RESERVA.-')
else:
    titulo = ('SE LIBRE GIRO ELECTRÓNICO EN CONCEPTO DE HONORARIOS. ADJUNTA '
              'DOCUMENTACIÓN. DECLARA BAJO JURAMENTO. HACE RESERVA.-')
add_titulo(titulo)
doc.add_paragraph()
doc.add_paragraph()

# ======================================================================
# ENCABEZADO
# ======================================================================
add_encabezado('Sr. Juez:')

# ======================================================================
# PRIMER PÁRRAFO
# ======================================================================
add_par_mixto([
    ('', False, False),
    (CASO['letrado_nombre'], True, False),
    (f', abogado, inscripto en el {CASO["letrado_tomo_folio"]}, C.U.I.T N° {CASO["letrado_cuit"]}, '
     f'IVA responsable inscripto, ', False, False),
    ('POR DERECHO PROPIO', True, False),
    (f', manteniendo el domicilio procesal en la {CASO["letrado_domicilio"]} (zona de notificación '
     f'{CASO["letrado_zona"]}, e-mail: {CASO["letrado_email"]}, tel: {CASO["letrado_tel"]}) y '
     f'domicilio electrónico en {CASO["letrado_de"]}, en los autos caratulados ', False, False),
    (f'"{CASO["caratula"]}" Expte. N° {CASO["numero_expte"]}', True, False),
    (', a V.S. digo:', False, False),
], indent=1.5)

# ======================================================================
# I.- (depende de variante)
# ======================================================================
if CASO['variante'] == 'B':
    add_seccion('I.- TRABA EMBARGO SOBRE FONDOS DEPOSITADOS. SE LIBRE GIRO ELECTRÓNICO.-')
    add_par_mixto([
        ('', False, False),
        ('VISTO', True, False),
        (f' los depósitos efectuados por la demandada en fechas {CASO["fechas_depositos"]}, '
         f'que totalizan la suma de ${CASO["monto_total"]} (honorarios ${CASO["honorarios"]} + '
         f'IVA ${CASO["iva"]}) en la cuenta de autos —los que se encuentran dados en embargo '
         f'por la propia demandada con pretensión de inmovilización en plazo fijo hasta la '
         f'resolución de la {CASO["recurso_pendiente"]}—, y atento a que dicho trámite no '
         'suspende la ejecución ni la exigibilidad de los honorarios firmes (art. 285 CPCCN), ',
         False, False),
        ('SOLICITO', True, False),
        (' a V.S. que:', False, False),
    ])
    add_par(
        f'(a) Se TRABE EMBARGO a favor del suscripto, {CASO["letrado_nombre"]}, CUIT '
        f'{CASO["letrado_cuit"]}, sobre las sumas depositadas en la cuenta de autos por la '
        f'parte demandada, hasta cubrir la totalidad de ${CASO["monto_total"]} en concepto de '
        'honorarios profesionales, con más lo que corresponda por diferencias pendientes '
        'conforme las reservas oportunamente formuladas.'
    )
    add_par_mixto([
        ('(b) Se ', False, False),
        ('ORDENE TRANSFERIR', True, False),
        (' la suma de ', False, False),
        (f'${CASO["monto_total"]}', True, False),
        (' desde la cuenta de autos a la cuenta bancaria del suscripto, ', False, False),
        (CASO['letrado_nombre'], True, False),
        (f', DNI {CASO["letrado_dni"]}, CUIT {CASO["letrado_cuit"]}, abierta en el '
         f'{CASO["banco"]}, Caja de Ahorro $ N° {CASO["caja_ahorro"]}, CBU {CASO["cbu"]}, '
         'bajo estricta responsabilidad del profesional firmante.', False, False),
    ])
else:
    add_seccion('I.- SE ORDENE TRANSFERENCIA.-')
    add_par_mixto([
        ('', False, False),
        ('VISTO', True, False),
        (f' el depósito efectuado por la demandada en fecha {CASO["fecha_deposito"]} y el '
         f'embargo ordenado sobre la cuenta de autos en fecha {CASO["fecha_embargo"]}, ',
         False, False),
        ('SOLICITO', True, False),
        (' a S.S. que ', False, False),
        ('ORDENE TRANSFERIR', True, False),
        (' la suma de ', False, False),
        (f'${CASO["monto_total"]}', True, False),
        (' (honorarios ', False, False),
        (f'${CASO["honorarios"]}', True, False),
        (' + IVA ', False, False),
        (f'${CASO["iva"]}', True, False),
        (') desde la cuenta de autos a la cuenta bancaria del suscripto, ', False, False),
        (CASO['letrado_nombre'], True, False),
        (f', DNI {CASO["letrado_dni"]}, CUIT {CASO["letrado_cuit"]}, abierta en el '
         f'{CASO["banco"]}, Caja de Ahorro $ {CASO["caja_ahorro"]}, CBU {CASO["cbu"]}.',
         False, False),
    ])

# ======================================================================
# II.- ADJUNTA DOCUMENTACIÓN - DECLARA BAJO JURAMENTO
# ======================================================================
add_seccion('II.- ADJUNTA DOCUMENTACIÓN. DECLARA BAJO JURAMENTO.-')
add_par(
    'Adjunto constancia de inscripción y constancia de CBU de la cuenta bancaria del '
    'suscripto y declaro bajo juramento que ambas piezas son auténticas.'
)

# ======================================================================
# III.- PRESTA JURAMENTO
# ======================================================================
add_seccion('III.- PRESTA JURAMENTO.-')
add_par('Presto juramento de haber sido el único letrado actuante en los presentes autos.')

# ======================================================================
# IV.- HACE RESERVA
# ======================================================================
add_seccion('IV.- HACE RESERVA.-')
add_par(
    'Esta parte se reserva el derecho a reclamar los intereses devengados por la falta de '
    'pago en término, dejando expresa constancia que las sumas recibidas se imputarán en '
    'primer lugar a intereses y en segundo lugar a honorarios. En efecto, en los términos '
    'del artículo 900 del CCCN se deja constancia que el suscripto no presta su consentimiento '
    'a que la suma percibida se impute, en primer término, a la deuda principal de honorarios.'
)
add_par(
    'Asimismo, esta parte se reserva el derecho a reclamar la diferencia de honorarios que '
    'surja de aplicar lo dispuesto en el artículo 51 de la Ley 27.423 que dice:'
)
add_par_mixto([
    ('', False, False),
    ('"La regulación de honorarios deberá contener, bajo pena de nulidad, el monto expresado '
     'en moneda de curso legal y la cantidad de UMA que éste representa a la fecha de la '
     'resolución. El pago será definitivo y cancelatorio únicamente si se abona la cantidad '
     'de moneda de curso legal que resulte equivalente a la cantidad de UMA contenidas en la '
     'resolución regulatoria, ', False, False),
    ('según su valor vigente al momento del pago', False, True),
    ('".', False, False),
])
add_par('Solicito se tenga presente lo manifestado.')

# ======================================================================
# CIERRE
# ======================================================================
doc.add_paragraph()
add_par('Proveer de conformidad,', indent=0, align='center')
add_par('SERÁ JUSTICIA.-', indent=0, align='center', bold=True)

# ======================================================================
# ANEXOS (constancias embebidas)
# ======================================================================
add_constancia('CONSTANCIA DE INSCRIPCIÓN AFIP/ARCA',
               os.path.join(ASSETS_DIR, 'constancia_afip.png'), 6)
add_constancia('CONSTANCIA DE CBU - BANCO CIUDAD',
               os.path.join(ASSETS_DIR, 'constancia_cbu.png'), 5)

# ======================================================================
# GUARDAR
# ======================================================================
out = os.path.expanduser(f'~/Desktop/{CASO["caratula_short"]}_giro_honorarios.docx')
doc.save(out)
print(f'Guardado: {out}')
