#!/usr/bin/env python3
"""
Procesa audios e imágenes de wa_messages que no estén ya transcritos en
wa_media_procesado.

- Audios: Whisper (gpt-4o-mini-transcribe; fallback a whisper-1)
- Imágenes: Claude Sonnet 4.6 vision (extrae texto + descripción breve)

Uso:
  python3 process_media.py [--limit N] [--type audio|image|all] [--since YYYY-MM-DD]

Lee credenciales de ~/.env (OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY).
"""
import argparse
import os
import sys
import base64
import tempfile
import time
import json
from pathlib import Path

import requests

# ---------- carga de .env ----------
def load_env(path: str = None):
    path = path or os.path.expanduser("~/.env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

load_env()

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

assert OPENAI_KEY, "Falta OPENAI_API_KEY en ~/.env"
assert ANTHROPIC_KEY, "Falta ANTHROPIC_API_KEY en ~/.env"
assert SUPABASE_URL and SUPABASE_KEY, "Falta SUPABASE_URL/SUPABASE_KEY en ~/.env"

SUPABASE_URL = SUPABASE_URL.rstrip("/")
HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ---------- queries supabase ----------
def fetch_pending(media_type: str, since: str, limit: int):
    """Trae mensajes media sin procesar (LEFT JOIN wa_media_procesado IS NULL)."""
    sql = f"""
SELECT m.id, m.chat_id, m.chat_name, m.type, m.media_url, m.media_mimetype, m.created_at
FROM wa_messages m
LEFT JOIN wa_media_procesado p ON p.message_id = m.id
WHERE p.message_id IS NULL
  AND m.media_url IS NOT NULL
  AND m.created_at >= '{since}'::timestamp
"""
    if media_type == "audio":
        sql += "  AND m.type IN ('audio','ptt')\n"
    elif media_type == "image":
        sql += "  AND m.type = 'image'\n"
    else:
        sql += "  AND m.type IN ('audio','ptt','image')\n"
    sql += f"ORDER BY m.created_at DESC LIMIT {limit};"

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        headers=HEADERS_SB,
        json={"sql": sql},
        timeout=30,
    )
    if r.status_code == 404:
        # Fallback: PostgREST no expone exec_sql. Usar /rest/v1 con filtros directos.
        return fetch_pending_via_rest(media_type, since, limit)
    r.raise_for_status()
    return r.json()


def fetch_pending_via_rest(media_type: str, since: str, limit: int):
    """Fallback usando PostgREST estándar."""
    types = "(audio,ptt,image)" if media_type == "all" else (
        "(audio,ptt)" if media_type == "audio" else "(image)"
    )
    # 1. Bajar TODOS los message_id ya procesados (paginar de a 1000)
    procesados = set()
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/wa_media_procesado"
            f"?select=message_id&limit=1000&offset={offset}",
            headers=HEADERS_SB,
            timeout=30,
        )
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        procesados.update(x["message_id"] for x in chunk)
        if len(chunk) < 1000:
            break
        offset += 1000

    # 2. Bajar mensajes con media_url (paginar también; tomamos margen)
    msgs = []
    page_size = 1000
    offset = 0
    while len(msgs) < limit * 5:  # mucho margen
        url = (
            f"{SUPABASE_URL}/rest/v1/wa_messages"
            f"?select=id,chat_id,chat_name,type,media_url,media_mimetype,created_at"
            f"&type=in.{types}"
            f"&media_url=not.is.null"
            f"&created_at=gte.{since}"
            f"&order=created_at.desc"
            f"&limit={page_size}&offset={offset}"
        )
        r = requests.get(url, headers=HEADERS_SB, timeout=30)
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        msgs.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size

    # 3. Filtrar los procesados localmente
    pending = [m for m in msgs if m["id"] not in procesados]
    return pending[:limit]


def insert_procesado_one(row: dict) -> bool:
    """Insert una row sola. Retorna True si se insertó (o si ya existía)."""
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/wa_media_procesado",
        headers={**HEADERS_SB, "Prefer": "return=representation"},
        json=row,
        timeout=30,
    )
    if r.status_code in (201, 409):  # creado o ya existía
        return True
    print(f"⚠️  Error INSERT {r.status_code}: {r.text[:200]}", file=sys.stderr)
    return False


def insert_procesado(rows: list):
    """Insert por filas para evitar PGRST102 cuando hay schemas mixtos."""
    if not rows:
        return 0
    insertados = 0
    for row in rows:
        if insert_procesado_one(row):
            insertados += 1
    return insertados


# ---------- procesamiento ----------
def transcribe_audio(media_url: str, mime: str = None) -> dict:
    """Descarga el audio y lo manda a Whisper. Devuelve {transcripcion, modelo, costo_usd}."""
    audio_data = requests.get(media_url, timeout=60).content
    suffix = ".ogg" if "ogg" in (mime or "") else (".m4a" if "m4a" in (mime or "") else ".mp3")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_data)
        tmppath = f.name

    try:
        with open(tmppath, "rb") as audio_f:
            r = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                files={"file": (os.path.basename(tmppath), audio_f, "audio/ogg")},
                data={"model": "whisper-1", "language": "es"},
                timeout=120,
            )
        r.raise_for_status()
        text = r.json().get("text", "").strip()
        # Whisper-1 cobra $0.006/min. Estimamos por tamaño bytes (~16kB/s ogg-opus): muy aprox.
        size_kb = len(audio_data) / 1024
        est_min = max(0.05, size_kb / 480)  # ~30s mínimo
        costo = round(est_min * 0.006, 6)
        return {"transcripcion": text, "modelo": "whisper-1", "costo_usd": costo}
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass


def describe_image(media_url: str, mime: str = None) -> dict:
    """Manda imagen a Claude Sonnet 4.6 para extraer texto y descripción."""
    img_data = requests.get(media_url, timeout=60).content
    b64 = base64.b64encode(img_data).decode("ascii")
    media_type = mime or "image/jpeg"
    if not media_type.startswith("image/"):
        media_type = "image/jpeg"

    prompt = (
        "Analizá esta imagen que mandó un cliente por WhatsApp a un estudio jurídico. "
        "Devolvé en español, en MENOS de 80 palabras:\n"
        "1) Si tiene texto legible, transcribilo literal (DNI, certificados, alta médica, "
        "comprobantes de pago, recetas, etc.)\n"
        "2) Si es una foto de algo (cuerpo lesionado, accidente, lugar), describilo brevemente.\n"
        "3) Si no aporta info útil, decí 'sin info relevante'.\n"
        "No inventes datos."
    )

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 250,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    res = r.json()
    text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text").strip()
    # Aprox $0.003/img (sonnet 4.6 con imagen pequeña + 250 tokens out)
    return {"transcripcion": text, "modelo": "claude-sonnet-4-6", "costo_usd": 0.003}


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--type", choices=["audio", "image", "all"], default="all")
    ap.add_argument("--since", default=None, help="YYYY-MM-DD (default: 7 días atrás)")
    ap.add_argument("--message-id", help="Procesar UN message_id específico (ignora --type/--since/--limit)")
    args = ap.parse_args()

    if args.since is None:
        from datetime import datetime, timedelta
        args.since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Modo single message
    if args.message_id:
        url = (
            f"{SUPABASE_URL}/rest/v1/wa_messages"
            f"?select=id,chat_id,chat_name,type,media_url,media_mimetype,created_at"
            f"&id=eq.{args.message_id}"
        )
        r = requests.get(url, headers=HEADERS_SB, timeout=30)
        r.raise_for_status()
        pending = r.json()
    else:
        pending = fetch_pending_via_rest(args.type, args.since, args.limit)

    print(f"📥 {len(pending)} mensajes para procesar")

    # Checkpoint JSONL: si el INSERT falla, los datos quedan en disco.
    checkpoint_path = "/tmp/wa_media_checkpoint.jsonl"
    cp_f = open(checkpoint_path, "a")
    print(f"📝 Checkpoint a {checkpoint_path}")

    insertados = 0
    fallidos = 0
    total_costo = 0.0

    def normalize_row(d: dict) -> dict:
        """Garantiza schema uniforme (todas las keys siempre presentes)."""
        return {
            "message_id": d.get("message_id"),
            "chat_id": d.get("chat_id"),
            "chat_name": d.get("chat_name"),
            "type": d.get("type"),
            "media_url": d.get("media_url"),
            "transcripcion": d.get("transcripcion"),
            "modelo": d.get("modelo"),
            "costo_usd": d.get("costo_usd", 0) or 0,
            "error": d.get("error"),
        }

    for i, msg in enumerate(pending, 1):
        mtype = msg["type"]
        chat_name = msg.get("chat_name") or "?"
        print(f"  [{i}/{len(pending)}] {mtype} de {chat_name[:40]} … ", end="", flush=True)
        row = {
            "message_id": msg["id"],
            "chat_id": msg["chat_id"],
            "chat_name": chat_name,
            "type": mtype,
            "media_url": msg["media_url"],
        }
        try:
            if mtype in ("audio", "ptt"):
                res = transcribe_audio(msg["media_url"], msg.get("media_mimetype"))
            elif mtype == "image":
                res = describe_image(msg["media_url"], msg.get("media_mimetype"))
            else:
                print("skip (tipo no soportado)")
                continue
            row.update({
                "transcripcion": res["transcripcion"],
                "modelo": res["modelo"],
                "costo_usd": res["costo_usd"],
            })
            preview = (res["transcripcion"] or "")[:80].replace("\n", " ")
            print(f"OK — {preview}…")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            row["error"] = err[:300]
            print(f"ERROR — {err[:120]}")

        # Persist checkpoint LINE PER LINE inmediatamente
        row = normalize_row(row)
        cp_f.write(json.dumps(row, ensure_ascii=False) + "\n")
        cp_f.flush()

        # Insert one-by-one (robusto)
        if insert_procesado_one(row):
            insertados += 1
        else:
            fallidos += 1
        total_costo += row["costo_usd"] or 0

    cp_f.close()
    print(f"\n✅ {insertados} insertados, {fallidos} fallidos en INSERT — costo ~${total_costo:.4f}")
    print(f"📦 Checkpoint completo: {checkpoint_path}")


if __name__ == "__main__":
    main()
