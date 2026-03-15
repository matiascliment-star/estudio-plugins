#!/usr/bin/env python3
"""
Descarga thumbnails de propiedades en paralelo.

Uso:
    python3 download_thumbs.py <metadata.json> <output-dir>

metadata.json: JSON array de propiedades con campo '_thumb' (URL del thumbnail)
output-dir: carpeta donde guardar los thumbnails como 0000.jpg, 0001.jpg, etc.
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_thumb_url(prop):
    """Extrae la URL del primer thumbnail de una propiedad."""
    # Si ya tiene _thumb precalculado
    if prop.get("_thumb"):
        return prop["_thumb"]
    # Intentar imagenes (array jsonb)
    imgs = prop.get("imagenes")
    if imgs and isinstance(imgs, list) and len(imgs) > 0:
        return imgs[0]
    # Fallback: campo imagen
    img = prop.get("imagen", "")
    return img if img and img.startswith("http") else ""


def download_one(idx, url, output_dir):
    """Descarga un thumbnail. Retorna (idx, success)."""
    fname = os.path.join(output_dir, f"{idx:04d}.jpg")
    if os.path.exists(fname) and os.path.getsize(fname) > 100:
        return idx, True
    if not url or not url.startswith("http"):
        return idx, False
    try:
        urllib.request.urlretrieve(url, fname)
        return idx, True
    except Exception:
        return idx, False


def main():
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <metadata.json> <output-dir>")
        sys.exit(1)

    metadata_path = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    with open(metadata_path) as f:
        props = json.load(f)

    # Precalcular URLs
    items = []
    for i, p in enumerate(props):
        url = get_thumb_url(p)
        items.append((i, url))

    total = len(items)
    print(f"Descargando {total} thumbnails a {output_dir}...")

    success = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(download_one, idx, url, output_dir): idx
            for idx, url in items
        }
        for future in as_completed(futures):
            idx, ok = future.result()
            if ok:
                success += 1
            else:
                fail += 1
            done = success + fail
            if done % 100 == 0 or done == total:
                print(f"  Progreso: {done}/{total} ({success} ok, {fail} fail)")

    print(f"\nFinal: {success} descargados, {fail} fallidos de {total}")


if __name__ == "__main__":
    main()
