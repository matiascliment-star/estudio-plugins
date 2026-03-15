#!/usr/bin/env python3
"""
Crea montajes/grillas de contacto con thumbnails de propiedades.

Uso:
    python3 make_grids.py <metadata.json> <thumbs-dir> <output-dir>

Genera archivos page_00.jpg, page_01.jpg, etc. con 50 propiedades por grilla
(10 columnas x 5 filas). Cada celda tiene el thumbnail + label con datos.
"""
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow no instalado. Ejecutar: pip install Pillow --break-system-packages")
    sys.exit(1)

# Configuración visual
THUMB_W = 200
THUMB_H = 150
COLS = 10
LABEL_H = 36
CELL_H = THUMB_H + LABEL_H
PER_PAGE = 50  # 10 cols x 5 rows


def load_fonts():
    """Carga fuentes, con fallback a default."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return (
                    ImageFont.truetype(p, 10),
                    ImageFont.truetype(p, 9),
                )
            except Exception:
                continue
    default = ImageFont.load_default()
    return default, default


def make_grid(props, start_idx, thumbs_dir, font, font_small):
    """Crea una grilla de hasta PER_PAGE propiedades."""
    rows = (len(props) + COLS - 1) // COLS
    img_w = COLS * THUMB_W
    img_h = rows * CELL_H
    canvas = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(canvas)

    for i, p in enumerate(props):
        col = i % COLS
        row = i // COLS
        x = col * THUMB_W
        y = row * CELL_H
        idx = start_idx + i

        # Cargar thumbnail
        thumb_path = os.path.join(thumbs_dir, f"{idx:04d}.jpg")
        try:
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 100:
                thumb = Image.open(thumb_path)
                thumb = thumb.resize((THUMB_W, THUMB_H), Image.LANCZOS)
                canvas.paste(thumb, (x, y))
            else:
                draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill="#ddd")
                draw.text((x + 10, y + 60), "Sin foto", fill="gray", font=font)
        except Exception:
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill="#ddd")

        # Datos para el label
        precio = p.get("precio") or 0
        barrio = (p.get("barrio", "") or "")[:12]
        m2 = p.get("m2") or "?"
        amb = p.get("ambientes") or "?"
        diff = p.get("diff_vs_prom_general")

        label1 = f"#{idx} {barrio}"
        label2 = f"USD{precio / 1000:.0f}k {m2}m2 {amb}amb"
        diff_str = f"{diff:.0f}%" if diff is not None else ""

        # Dibujar label
        draw.rectangle(
            [x, y + THUMB_H, x + THUMB_W, y + CELL_H], fill="#f0f0f0"
        )
        draw.text((x + 2, y + THUMB_H + 2), label1, fill="black", font=font_small)
        draw.text(
            (x + 2, y + THUMB_H + 14), label2, fill="#333", font=font_small
        )
        if diff_str:
            color = "#d00" if diff and diff < -20 else "#666"
            draw.text(
                (x + 2, y + THUMB_H + 25), diff_str, fill=color, font=font_small
            )

    return canvas


def main():
    if len(sys.argv) < 4:
        print(f"Uso: {sys.argv[0]} <metadata.json> <thumbs-dir> <output-dir>")
        sys.exit(1)

    metadata_path = sys.argv[1]
    thumbs_dir = sys.argv[2]
    output_dir = sys.argv[3]
    os.makedirs(output_dir, exist_ok=True)

    with open(metadata_path) as f:
        props = json.load(f)

    font, font_small = load_fonts()

    page = 0
    for start in range(0, len(props), PER_PAGE):
        batch = props[start : start + PER_PAGE]
        canvas = make_grid(batch, start, thumbs_dir, font, font_small)
        fname = os.path.join(output_dir, f"page_{page:02d}.jpg")
        canvas.save(fname, quality=90)
        print(f"Grilla {page}: #{start}-{start + len(batch) - 1} -> {fname}")
        page += 1

    print(f"\nTotal: {page} grillas ({len(props)} propiedades)")


if __name__ == "__main__":
    main()
