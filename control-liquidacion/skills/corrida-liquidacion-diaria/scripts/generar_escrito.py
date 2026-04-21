#!/usr/bin/env python3
"""
Genera un DOCX de escrito judicial para la corrida diaria de caducidad.

Uso:
  python3 generar_escrito.py \
    --modelo pronto-despacho \
    --caratula "VALLEJOS, RAMIRO ALBERTO c/ SWISS MEDICAL ART S.A. s/DESPIDO" \
    --numero "CNT 000273/2024" \
    --placeholders '{"fecha_ultimo_hito":"07/07/2025","descripcion_ultimo_hito":"el Juzgado intimó al perito por remiso","estado_procesal":"paralizado en etapa probatoria","accion_especifica_a_pedir":"haga efectivo el apercibimiento al perito contador"}' \
    --output /tmp/pronto_VALLEJOS.docx

Aplica el formato del estudio (memoria feedback_formato_escritos.md):
- Times New Roman 12pt, interlineado 1.5, márgenes 2/2/3/2 cm
- Sangría 1.25 cm (1.5 para encabezado letrado)
- OBJETO: negrita + subrayado + MAYÚSCULAS + sangría 1.25
- "Sr. Juez:" izquierda sin sangría
- Nombre del letrado en negrita, carátula y expediente en negrita
"""

import argparse
import json
import re
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Formato del estudio
FUENTE = "Times New Roman"
TAM_PT = 12
INTERLINEADO = 1.5
MARGEN_SUP = MARGEN_INF = MARGEN_DER = Cm(2)
MARGEN_IZQ = Cm(3)
SANGRIA_CUERPO = Emu(450215)  # ~1.25 cm
SANGRIA_LETRADO = Emu(540385)  # ~1.5 cm


def aplicar_formato_doc(doc):
    """Aplica márgenes y formato base al documento."""
    for section in doc.sections:
        section.top_margin = MARGEN_SUP
        section.bottom_margin = MARGEN_INF
        section.left_margin = MARGEN_IZQ
        section.right_margin = MARGEN_DER


def set_style(run, negrita=False, subrayado=False):
    run.font.name = FUENTE
    run.font.size = Pt(TAM_PT)
    run.bold = negrita
    run.underline = subrayado


def agregar_parrafo(doc, texto, *, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
                    sangria=None, negrita=False, subrayado=False,
                    mayusculas=False, interlineado=INTERLINEADO,
                    space_before=0, space_after=0, bloques_negrita=None):
    """
    Agrega un párrafo con formato. Si `bloques_negrita` es una lista de
    substrings, esos tramos van en negrita (el resto normal).
    """
    p = doc.add_paragraph()
    p.alignment = alineacion
    pf = p.paragraph_format
    pf.line_spacing = interlineado
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if sangria is not None:
        pf.first_line_indent = sangria

    if mayusculas:
        texto = texto.upper()

    if bloques_negrita:
        # partir texto en tramos alternando normal/negrita
        pattern = "|".join(re.escape(b) for b in bloques_negrita)
        partes = re.split(f"({pattern})", texto)
        for parte in partes:
            if not parte:
                continue
            run = p.add_run(parte)
            es_negrita = parte in bloques_negrita or negrita
            set_style(run, negrita=es_negrita, subrayado=subrayado)
    else:
        run = p.add_run(texto)
        set_style(run, negrita=negrita, subrayado=subrayado)
    return p


def parsear_modelo(texto_modelo):
    """Parsea el .md del modelo y devuelve bloques lógicos."""
    # Los modelos tienen:
    # OBJETO: ...
    # (línea en blanco)
    # Sr. Juez:
    # (línea en blanco)
    # Primer párrafo (encabezado letrado)
    # (línea en blanco)
    # Cuerpo párrafos...
    # (línea en blanco)
    # Proveer de conformidad,
    # (línea en blanco)
    # SERÁ JUSTICIA.
    lineas = [l.rstrip() for l in texto_modelo.strip().split("\n")]
    # Agrupar en bloques separados por línea vacía
    bloques = []
    actual = []
    for l in lineas:
        if l.strip() == "":
            if actual:
                bloques.append("\n".join(actual).strip())
                actual = []
        else:
            actual.append(l)
    if actual:
        bloques.append("\n".join(actual).strip())
    return bloques


def reemplazar_placeholders(texto, placeholders):
    for k, v in placeholders.items():
        texto = texto.replace("{{" + k + "}}", str(v))
    # Detectar placeholders sin reemplazar (señal de error)
    sin_cubrir = re.findall(r"\{\{(\w+)\}\}", texto)
    if sin_cubrir:
        print(f"⚠️  Placeholders sin valor: {sin_cubrir}", file=sys.stderr)
    return texto


def generar(modelo_path, caratula, numero, placeholders, output_path):
    texto_modelo = Path(modelo_path).read_text(encoding="utf-8")

    # Sumar caratula y numero a los placeholders
    placeholders = {**placeholders, "caratula": caratula, "numero": numero}
    texto = reemplazar_placeholders(texto_modelo, placeholders)

    bloques = parsear_modelo(texto)

    doc = Document()
    aplicar_formato_doc(doc)

    for i, bloque in enumerate(bloques):
        # Primer bloque: OBJETO
        if i == 0 and bloque.upper().startswith("OBJETO"):
            agregar_parrafo(doc, bloque, sangria=SANGRIA_CUERPO,
                            negrita=True, subrayado=True, mayusculas=True,
                            space_after=6)
            continue

        # Encabezado al tribunal (ej "Sr. Juez:", "Excmo. Tribunal:")
        if bloque.endswith(":") and len(bloque) < 50 and "\n" not in bloque:
            agregar_parrafo(doc, bloque, alineacion=WD_ALIGN_PARAGRAPH.LEFT,
                            space_before=6, space_after=6)
            continue

        # Cierre "SERÁ JUSTICIA."
        if "JUSTICIA" in bloque.upper() and len(bloque) < 40:
            agregar_parrafo(doc, bloque, sangria=SANGRIA_CUERPO,
                            negrita=True, space_before=12)
            continue

        # "Proveer de conformidad,"
        if bloque.lower().startswith("proveer") or bloque.lower().startswith("provea"):
            agregar_parrafo(doc, bloque, sangria=SANGRIA_CUERPO, space_before=6)
            continue

        # Primer párrafo con datos del letrado (único con "GARCÍA CLIMENT" como actor)
        if "GARCÍA CLIMENT" in bloque and "T°" in bloque:
            bloques_negrita = re.findall(r"\*\*(.+?)\*\*", bloque, flags=re.DOTALL)
            texto_limpio = re.sub(r"\*\*(.+?)\*\*", r"\1", bloque, flags=re.DOTALL)
            agregar_parrafo(doc, texto_limpio, sangria=SANGRIA_LETRADO,
                            bloques_negrita=bloques_negrita, space_after=6)
            continue

        # Cuerpo normal
        bloques_negrita = re.findall(r"\*\*(.+?)\*\*", bloque, flags=re.DOTALL)
        texto_limpio = re.sub(r"\*\*(.+?)\*\*", r"\1", bloque, flags=re.DOTALL)
        agregar_parrafo(doc, texto_limpio, sangria=SANGRIA_CUERPO,
                        bloques_negrita=bloques_negrita, space_after=6)

    doc.save(output_path)
    print(f"✅ Guardado: {output_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True, help="Nombre del modelo (sin extensión), ej 'pronto-despacho'")
    ap.add_argument("--caratula", required=True)
    ap.add_argument("--numero", required=True)
    ap.add_argument("--placeholders", required=True, help="JSON con placeholders del modelo")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    modelo_path = skill_dir / "modelos" / f"{args.modelo}.md"
    if not modelo_path.exists():
        print(f"❌ Modelo no encontrado: {modelo_path}", file=sys.stderr)
        sys.exit(1)

    placeholders = json.loads(args.placeholders)
    generar(str(modelo_path), args.caratula, args.numero, placeholders, args.output)


if __name__ == "__main__":
    main()
