#!/usr/bin/env python3
"""
Extrae turnos médicos / pericias / citaciones de mensajes del staff y los guarda
en wa_turnos.

Estrategia:
1. Pre-filtrar mensajes del staff con regex (palabras clave: pericia, turno,
   citación, RMN, ecografía, electromiograma, psicodiagnóstico, etc.).
2. Para cada candidato, llamar Claude Haiku (rápido y barato) que devuelve JSON
   con los turnos detectados en el mensaje.
3. INSERT en wa_turnos (UNIQUE chat_id+fecha+hora evita duplicados).

Uso:
  python3 extract_turnos.py [--since YYYY-MM-DD] [--limit N]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

import requests

# ---------- env ----------
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
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

assert ANTHROPIC_KEY and SUPABASE_URL and SUPABASE_KEY

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ---------- regex pre-filter ----------
# Estrategia nueva: NO filtrar por keyword de procedimiento (demasiadas variantes:
# eco, audiometría, espirometría, doppler, holter, EEG, EMG, traumatólogo, etc).
# Solo filtramos por fecha + hora — si el mensaje del staff tiene los dos, va al LLM.
DATE_HINT = re.compile(
    r"(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo|"
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|"  # 28/04, 28/04/26
    r"\b\d{1,2}-\d{1,2}(?:-\d{2,4})?\b|"  # 28-04
    r"\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)|"
    r"\bel\s+d[ií]a\s+\d{1,2}\b|"  # "el día 28"
    r"\bpara\s+el\s+\d{1,2}\b)",  # "para el 28"
    re.IGNORECASE,
)
HOUR_HINT = re.compile(
    r"\b\d{1,2}[:\.]\d{2}\b|"  # 11:40, 9.30
    r"\b\d{1,2}\s*(hs|h\b|am|pm|horas)|"  # 11hs, 9h, 10am
    r"\ba las\s+\d{1,2}\b",  # "a las 11"
    re.IGNORECASE,
)


def es_candidato(content: str) -> bool:
    if not content or len(content) < 20:
        return False
    return bool(DATE_HINT.search(content)) and bool(HOUR_HINT.search(content))


# ---------- LLM extraction ----------
EXTRACTION_PROMPT = """Sos un asistente que extrae turnos médicos / pericias / citaciones de mensajes de WhatsApp de un estudio jurídico argentino.

Devolvé SOLO un JSON válido (sin markdown, sin explicación) con este schema:
{
  "turnos": [
    {
      "fecha": "YYYY-MM-DD",
      "hora": "HH:MM",
      "lugar": "dirección textual o nombre del lugar (max 200 chars)",
      "procedimiento": "qué le van a hacer (RMN, ecografía, junta médica, pericia psicológica, etc)"
    }
  ]
}

Si el mensaje NO menciona un turno con fecha+hora claras, devolvé {"turnos": []}.

REGLAS:
- Año actual: 2026. Si dice "29/04/26" interpretá 2026-04-29.
- Si solo dice "El día 6 Mayo" sin año, asumí año actual (2026) y mes según contexto.
- Si dice "videollamada" sin lugar físico, lugar = "Videollamada de WhatsApp".
- Si hay MÚLTIPLES turnos en el mismo mensaje (ej: ecografía 9:20 + RX 10:20), incluí cada uno.
- Si no podés determinar la hora con precisión (solo "tarde" o "mañana"), omitir el turno.
- procedimiento: usá las palabras clave del mensaje (RMN, RX, ECOGRAFÍA, ELECTROMIOGRAMA, PSICODIAGNÓSTICO, JUNTA MÉDICA, INTERCONSULTA, PERICIA MÉDICA, PERICIA PSICOLÓGICA).

Mensaje a analizar:"""


def extract_turnos_llm(content: str) -> list[dict]:
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 800,
            "messages": [
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + "\n\n" + content,
                }
            ],
        },
        timeout=60,
    )
    r.raise_for_status()
    res = r.json()
    text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text").strip()
    # Limpiar fences markdown si los hay
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data.get("turnos", [])
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON inválido: {e} — {text[:120]}", file=sys.stderr)
        return []


# ---------- supabase ----------
GRUPOS_INTERNOS = {
    "TRABAJO", "Lobos de Wall Street (2026)", "Cédulas y otras notificaciones",
    "Pericias y sentencias", "FIRMÓ 🖋️📈", "BANCO 🏦 (COBROS PRESENCIALES)",
    "Demandas (Registro) Provincia Bs.As.", "Control Dispos SRT", "Claude SRT",
    "Novedades - VETA CAPITAL", "Novedades PJN ", "Novedades Pcia ",
    "Control exptes/consultas", "INICIO - Nuevos formularios 2026",
    "DIARIO LA LEY 🗞️📰⚖️",
}


def fetch_staff_msgs(since: str, limit: int) -> list[dict]:
    """Trae mensajes del staff de los últimos N días, sólo en grupos de cliente."""
    msgs = []
    page_size = 1000
    offset = 0
    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/wa_messages"
            f"?select=id,chat_id,chat_name,content,created_at,staff_name"
            f"&staff_name=not.is.null"
            f"&content=not.is.null"
            f"&created_at=gte.{since}"
            f"&is_group=eq.true"
            f"&order=created_at.desc"
            f"&limit={page_size}&offset={offset}"
        )
        r = requests.get(url, headers=HEADERS_SB, timeout=30)
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        msgs.extend(chunk)
        if len(chunk) < page_size or len(msgs) >= limit * 2:
            break
        offset += page_size
    # Filtrar grupos internos
    msgs = [m for m in msgs if m.get("chat_name") not in GRUPOS_INTERNOS]
    return msgs[:limit]


def insert_turnos(rows: list[dict]):
    if not rows:
        return 0
    # Insert uno por uno para que un UNIQUE conflict no aborte el batch entero.
    # (PostgREST no maneja bien Prefer: resolution con UNIQUE compuesto si tiene NULLs.)
    insertados = 0
    for row in rows:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/wa_turnos",
            headers={**HEADERS_SB, "Prefer": "return=representation"},
            json=row,
            timeout=30,
        )
        if r.status_code == 201:
            insertados += 1
        elif r.status_code == 409:
            # Conflict por UNIQUE — esperado, ignorar
            pass
        else:
            print(f"⚠️  Error {r.status_code}: {r.text[:120]}", file=sys.stderr)
    return insertados


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="YYYY-MM-DD (default: 30 días atrás)")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--message-id", help="Procesar UN mensaje específico para test")
    args = ap.parse_args()

    if args.since is None:
        args.since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    if args.message_id:
        url = (
            f"{SUPABASE_URL}/rest/v1/wa_messages"
            f"?select=id,chat_id,chat_name,content,created_at,staff_name"
            f"&id=eq.{args.message_id}"
        )
        r = requests.get(url, headers=HEADERS_SB, timeout=30)
        r.raise_for_status()
        msgs = r.json()
    else:
        print(f"📥 Bajando mensajes del staff desde {args.since}...")
        msgs = fetch_staff_msgs(args.since, args.limit)
        print(f"   {len(msgs)} mensajes del staff")

    candidatos = [m for m in msgs if es_candidato(m.get("content", ""))]
    print(f"🎯 {len(candidatos)} candidatos a tener turno (post regex)")

    rows_total = []
    for i, m in enumerate(candidatos, 1):
        content = m["content"]
        chat_name = (m.get("chat_name") or "?")[:40]
        try:
            turnos = extract_turnos_llm(content)
        except Exception as e:
            print(f"  [{i}/{len(candidatos)}] {chat_name} ERROR LLM: {e}", file=sys.stderr)
            continue
        if not turnos:
            continue
        for t in turnos:
            try:
                fecha = datetime.strptime(t["fecha"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            hora = t.get("hora")
            if hora and re.match(r"^\d{1,2}:\d{2}$", hora):
                hora = hora if len(hora) == 5 else f"0{hora}"
            else:
                hora = None

            rows_total.append({
                "chat_id": m["chat_id"],
                "chat_name": m.get("chat_name"),
                "fecha_turno": fecha.isoformat(),
                "hora_turno": hora,
                "lugar": (t.get("lugar") or "")[:300] or None,
                "procedimiento": (t.get("procedimiento") or "")[:200] or None,
                "mensaje_origen_id": m["id"],
            })
        # Log progreso cada 20
        if i % 20 == 0:
            print(f"  [{i}/{len(candidatos)}] procesados — {len(rows_total)} turnos detectados hasta ahora")

    print(f"\n💾 Insertando {len(rows_total)} turnos en wa_turnos...")
    insertados = insert_turnos(rows_total)
    print(f"✅ {insertados} insertados (resto duplicados o conflictos UNIQUE)")


if __name__ == "__main__":
    main()
