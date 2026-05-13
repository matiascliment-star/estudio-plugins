#!/usr/bin/env python3
"""
Lee el chat exportado del grupo '💰💷💸 giros/transferencias 💰💷💸' y
emite el JSON de candidatos esperado por parse_giros_llm.py.

Pre-filtro por keywords ancla:
  - "TRANSFERENCIA"  (formato Noe)
  - "transfiérase" / "transfiera" / "líbrese" / "libranza" / "libranse"
  - "transferencia electrónica"

Uso:
  python3 extract_from_chat_txt.py /path/al/chat.txt > candidatos.json
"""
import json
import re
import sys
from datetime import datetime


# Formato iOS: "[9/26/25, 12:20:11] Abogados - Noe: ..."
# Formato Android: "9/26/25, 12:20 - Abogados - Noe: ..."
MSG_RX = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}(?::\d{2})?)\]?\s+(?:-\s+)?(.+?):\s+(.*)$"
)

ANCHORS = re.compile(
    r"TRANSFERENCIA|transfiérase|transfiera|líbrese|libranza|libránse|transferencia electrónica",
    re.IGNORECASE,
)

NOISE_PHRASES = re.compile(
    r"(imagen omitida|video omitido|audio omitido|sticker omitido|GIF omitido|documento omitido)",
    re.IGNORECASE,
)


def parse_msg_id(timestamp_iso: str, autor: str) -> str:
    """ID estable derivado de fecha + autor (para dedup en wa_message_id)."""
    safe_autor = re.sub(r"[^a-zA-Z0-9]", "_", autor)[:20]
    return f"chat_{timestamp_iso}_{safe_autor}"


def normalizar_fecha(date_str: str, time_str: str) -> str:
    """'9/26/25 12:20:11' → '2025-09-26T12:20:11'."""
    parts = date_str.split("/")
    if len(parts) != 3:
        return None
    mes, dia, anio = parts
    anio = int(anio)
    if anio < 100:
        anio = 2000 + anio
    try:
        ts = time_str if time_str.count(":") == 2 else time_str + ":00"
        dt = datetime.strptime(f"{anio}-{int(mes):02d}-{int(dia):02d} {ts}", "%Y-%m-%d %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return None


def parse_chat(path: str):
    """Itera el chat. Maneja mensajes multi-línea uniendo hasta el próximo timestamp."""
    msgs = []
    current = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = MSG_RX.match(line)
            if m:
                if current:
                    msgs.append(current)
                date_str, time_str, autor, content = m.groups()
                fecha_iso = normalizar_fecha(date_str, time_str)
                if not fecha_iso:
                    current = None
                    continue
                # Sacar caracteres invisibles que iOS mete al principio
                content = content.lstrip("\u200e\u202c\ufeff ").strip()
                current = {
                    "id": parse_msg_id(fecha_iso, autor),
                    "fecha": fecha_iso,
                    "autor": autor.strip(),
                    "raw": content,
                }
            else:
                if current and line.strip():
                    current["raw"] += "\n" + line.strip()
    if current:
        msgs.append(current)
    return msgs


def es_candidato(m: dict) -> bool:
    raw = m.get("raw", "")
    if not raw or NOISE_PHRASES.search(raw):
        if not ANCHORS.search(raw):
            return False
    return bool(ANCHORS.search(raw))


def main():
    if len(sys.argv) < 2:
        print("uso: extract_from_chat_txt.py <chat.txt>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    msgs = parse_chat(path)
    print(f"📄 {len(msgs)} mensajes totales en chat", file=sys.stderr)

    candidatos = []
    for m in msgs:
        if not es_candidato(m):
            continue
        candidatos.append({
            "source": "wa_noe",
            "id": m["id"],
            "fecha": m["fecha"],
            "raw": m["raw"][:3000],
        })

    print(f"🎯 {len(candidatos)} candidatos con anchors", file=sys.stderr)
    json.dump(candidatos, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
