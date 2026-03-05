#!/usr/bin/env python3
"""
Upload a PDF as a draft (borrador) to PJN via the MCP server HTTP endpoint.

Auto-reads credentials from .env files (plugin dir, ~/.env, or CLI args).

Usage:
  # Minimal (credentials auto-detected from .env):
  python3 upload_pjn_borrador.py \
    --numero-expediente "CNT 40454/2024" \
    --tipo E \
    --pdf-path /tmp/escrito.pdf \
    --pdf-nombre escrito.pdf \
    --descripcion "IMPUGNA PERICIA"

  # Explicit credentials:
  python3 upload_pjn_borrador.py \
    --usuario 20313806198 \
    --password SECRET \
    --numero-expediente "CNT 40454/2024" \
    ...
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


def load_env_file(path):
    """Read a .env file and return a dict of key=value pairs."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def find_credentials():
    """Auto-detect PJN credentials from .env files in multiple locations."""
    # Locations to search (in order of priority)
    search_paths = [
        # Plugin directory .env
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        # Home directory .env
        os.path.expanduser("~/.env"),
        # Real macOS home (in case ~ is sandboxed)
        "/Users/matiaschristiangarciacliment/.env",
    ]

    for path in search_paths:
        env = load_env_file(path)
        if env.get("PJN_USUARIO") and env.get("PJN_PASSWORD"):
            print(f"Credentials loaded from: {path}", file=sys.stderr)
            return env.get("PJN_USUARIO"), env.get("PJN_PASSWORD")

    return None, None


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
    # Auto-detect credentials
    auto_user, auto_pass = find_credentials()

    parser = argparse.ArgumentParser(description="Upload PDF as borrador to PJN via MCP")
    parser.add_argument("--usuario", default=auto_user, help="CUIT del usuario PJN (auto-detected from .env)")
    parser.add_argument("--password", default=auto_pass, help="Password del usuario PJN (auto-detected from .env)")

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

    if not args.usuario or not args.password:
        print("ERROR: No se encontraron credenciales PJN. Pasar --usuario y --password o crear ~/.env con PJN_USUARIO y PJN_PASSWORD", file=sys.stderr)
        sys.exit(1)

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
