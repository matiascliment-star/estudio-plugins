#!/usr/bin/env python3
"""
Upload a PDF as a draft (borrador) to PJN via the MCP server HTTP endpoint.

This script handles the full MCP Streamable HTTP protocol:
  1. Initialize session
  2. Send initialized notification
  3. Call pjn_guardar_borrador tool with the PDF base64
  4. Print the result

Usage:
  python3 upload_pjn_borrador.py \
    --usuario 20313806198 \
    --password SECRET \
    --numero-expediente "CNT 40454/2024" \
    --tipo E \
    --pdf-path /tmp/escrito.pdf \
    --pdf-nombre escrito.pdf \
    --descripcion "IMPUGNA PERICIA" \
    [--mcp-url https://web-production-78135.up.railway.app/mcp] \
    [--api-key cpacf-mcp-railway-2024-secure-key] \
    [--id-oficina-destino 789]

Also accepts --id-expediente (numeric) as alternative to --numero-expediente.
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
        # Parse SSE response - extract JSON-RPC messages from events
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
        # Direct JSON response
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
            "clientInfo": {"name": "upload-pjn-script", "version": "1.0.0"}
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
    parser = argparse.ArgumentParser(description="Upload PDF as borrador to PJN via MCP")
    parser.add_argument("--usuario", required=True, help="CUIT del usuario PJN")
    parser.add_argument("--password", required=True, help="Password del usuario PJN")

    # Expediente: acepta numero O id interno
    exp_group = parser.add_mutually_exclusive_group(required=True)
    exp_group.add_argument("--numero-expediente", help="Numero de expediente (ej: 'CNT 40454/2024')")
    exp_group.add_argument("--id-expediente", type=int, help="ID interno numerico del expediente en PJN")

    parser.add_argument("--tipo", required=True, help="Tipo de escrito: M, E, C, I, H")
    parser.add_argument("--pdf-path", required=True, help="Path al archivo PDF")
    parser.add_argument("--pdf-nombre", required=True, help="Nombre del PDF (ej: escrito.pdf)")
    parser.add_argument("--descripcion", required=True, help="Descripcion del adjunto")
    parser.add_argument("--id-oficina-destino", type=int, default=None, help="ID oficina destino (opcional)")
    parser.add_argument("--mcp-url", default=MCP_URL_DEFAULT, help="URL del MCP server")
    parser.add_argument("--api-key", default=API_KEY_DEFAULT, help="API key del MCP server")
    args = parser.parse_args()

    # Read and encode PDF
    pdf_path = os.path.expanduser(args.pdf_path)
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    print(f"PDF loaded: {len(pdf_bytes)} bytes, base64: {len(pdf_base64)} chars", file=sys.stderr)

    # Initialize MCP session
    print("Initializing MCP session...", file=sys.stderr)
    session_id = initialize_session(args.mcp_url, args.api_key)
    print(f"Session ID: {session_id}", file=sys.stderr)

    # Build tool arguments
    tool_args = {
        "usuario": args.usuario,
        "password": args.password,
        "tipo_escrito": args.tipo,
        "pdf_base64": pdf_base64,
        "pdf_nombre": args.pdf_nombre,
        "descripcion_adjunto": args.descripcion,
    }

    # Usar numero_expediente o id_expediente segun lo que se paso
    if args.numero_expediente:
        tool_args["numero_expediente"] = args.numero_expediente
    else:
        tool_args["id_expediente"] = args.id_expediente

    if args.id_oficina_destino is not None:
        tool_args["id_oficina_destino"] = args.id_oficina_destino

    # Call the MCP tool
    print("Calling pjn_guardar_borrador...", file=sys.stderr)
    result = call_tool(args.mcp_url, args.api_key, session_id, "pjn_guardar_borrador", tool_args)

    # Output result
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
