#!/usr/bin/env python3
"""
Upload a borrador with PDF adjuntos to SCBA/MEV via the MCP server HTTP endpoint.

This script handles the full MCP Streamable HTTP protocol:
  1. Initialize session
  2. Send initialized notification
  3. Call scba_guardar_borrador_adjuntos tool with HTML + PDF base64 adjuntos
  4. Print the result

Usage:
  python3 upload_scba_adjuntos.py \
    --usuario user@notificaciones.scba.gov.ar \
    --password SECRET \
    --id-org 123 \
    --id-causa 456 \
    --titulo "ACOMPAÑA DOCUMENTAL" \
    --texto-html "<p>...</p>" \
    --texto-html-file /tmp/escrito.html \
    --adjuntos /tmp/doc1.pdf /tmp/doc2.pdf \
    [--tipo-presentacion 1] \
    [--mcp-url https://web-production-78135.up.railway.app/mcp] \
    [--api-key cpacf-mcp-railway-2024-secure-key]

For borrador WITHOUT adjuntos (text only), this script also supports:
  python3 upload_scba_adjuntos.py \
    --usuario ... --password ... \
    --id-org 123 --id-causa 456 \
    --titulo "PRONTO DESPACHO" \
    --texto-html "<p>...</p>" \
    --sin-adjuntos
"""

import argparse
import base64
import json
import os
import sys

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "--break-system-packages", "-q"])
    import requests


MCP_URL_DEFAULT = "https://web-production-78135.up.railway.app/mcp"
API_KEY_DEFAULT = "cpacf-mcp-railway-2024-secure-key"


def mcp_request(url, api_key, body, session_id=None):
    """Send a JSON-RPC request to the MCP server and return parsed response."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-API-Key": api_key,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    resp = requests.post(url, json=body, headers=headers, timeout=120)

    content_type = resp.headers.get("Content-Type", "")
    new_session_id = resp.headers.get("Mcp-Session-Id") or session_id

    if "text/event-stream" in content_type:
        result = None
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                data = line[6:].strip()
                if data:
                    try:
                        result = json.loads(data)
                    except json.JSONDecodeError:
                        pass
        return result, new_session_id
    else:
        if resp.status_code == 202:
            return None, new_session_id
        try:
            return resp.json(), new_session_id
        except Exception:
            return None, new_session_id


def initialize_session(url, api_key):
    """Initialize MCP session and return session ID."""
    init_body = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "upload-scba-script", "version": "1.0.0"}
        },
        "id": 1
    }

    result, session_id = mcp_request(url, api_key, init_body)

    if not session_id:
        raise RuntimeError("No session ID returned from initialize request")

    if result and "error" in result:
        raise RuntimeError(f"Initialize error: {result['error']}")

    notif_body = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    mcp_request(url, api_key, notif_body, session_id)

    return session_id


def call_tool(url, api_key, session_id, tool_name, arguments):
    """Call an MCP tool and return the result."""
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 2
    }

    result, _ = mcp_request(url, api_key, body, session_id)

    if not result:
        raise RuntimeError("No response from tool call")

    if "error" in result:
        raise RuntimeError(f"Tool error: {result['error']}")

    return result.get("result", result)


def main():
    parser = argparse.ArgumentParser(description="Upload borrador to SCBA/MEV via MCP")
    parser.add_argument("--usuario", required=True, help="Email MEV")
    parser.add_argument("--password", required=True, help="Password MEV")
    parser.add_argument("--id-org", required=True, type=int, help="ID del organismo (ido)")
    parser.add_argument("--id-causa", required=True, type=int, help="ID de la causa (idc)")
    parser.add_argument("--titulo", required=True, help="Titulo del escrito")
    parser.add_argument("--texto-html", default=None, help="HTML del escrito (inline)")
    parser.add_argument("--texto-html-file", default=None, help="Path a archivo con HTML del escrito")
    parser.add_argument("--adjuntos", nargs="*", default=[], help="Paths a PDFs adjuntos")
    parser.add_argument("--sin-adjuntos", action="store_true", help="Guardar sin adjuntos (solo texto)")
    parser.add_argument("--tipo-presentacion", default="1", help="Tipo: 1=Escritos, 2=Oficios, 3=Cedulas, 4=Mandamientos")
    parser.add_argument("--mcp-url", default=MCP_URL_DEFAULT, help="URL del MCP server")
    parser.add_argument("--api-key", default=API_KEY_DEFAULT, help="API key del MCP server")
    args = parser.parse_args()

    # Get HTML content
    texto_html = args.texto_html
    if args.texto_html_file:
        html_path = os.path.expanduser(args.texto_html_file)
        if not os.path.exists(html_path):
            print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
            sys.exit(1)
        with open(html_path, "r", encoding="utf-8") as f:
            texto_html = f.read()

    if not texto_html:
        print("ERROR: Must provide --texto-html or --texto-html-file", file=sys.stderr)
        sys.exit(1)

    # Initialize MCP session
    print("Initializing MCP session...", file=sys.stderr)
    session_id = initialize_session(args.mcp_url, args.api_key)
    print(f"Session ID: {session_id}", file=sys.stderr)

    if args.sin_adjuntos or not args.adjuntos:
        # Borrador sin adjuntos
        tool_name = "scba_guardar_borrador"
        tool_args = {
            "usuario": args.usuario,
            "password": args.password,
            "id_org": args.id_org,
            "id_causa": args.id_causa,
            "texto_html": texto_html,
            "titulo": args.titulo,
            "tipo_presentacion": args.tipo_presentacion,
        }
    else:
        # Borrador con adjuntos
        adjuntos_b64 = []
        for pdf_path in args.adjuntos:
            pdf_path = os.path.expanduser(pdf_path)
            if not os.path.exists(pdf_path):
                print(f"ERROR: Adjunto not found: {pdf_path}", file=sys.stderr)
                sys.exit(1)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            nombre = os.path.basename(pdf_path)
            b64 = base64.b64encode(pdf_bytes).decode("ascii")
            adjuntos_b64.append({
                "base64": b64,
                "nombre": nombre,
                "mime": "application/pdf"
            })
            print(f"Adjunto: {nombre} ({len(pdf_bytes)} bytes)", file=sys.stderr)

        tool_name = "scba_guardar_borrador_adjuntos"
        tool_args = {
            "usuario": args.usuario,
            "password": args.password,
            "id_org": args.id_org,
            "id_causa": args.id_causa,
            "texto_html": texto_html,
            "titulo": args.titulo,
            "adjuntos_base64": adjuntos_b64,
            "tipo_presentacion": args.tipo_presentacion,
        }

    # Call the MCP tool
    print(f"Calling {tool_name}...", file=sys.stderr)
    result = call_tool(args.mcp_url, args.api_key, session_id, tool_name, tool_args)

    # Output result
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
