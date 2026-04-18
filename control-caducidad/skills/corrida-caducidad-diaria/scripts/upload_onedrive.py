#!/usr/bin/env python3
"""
Sube un archivo (típicamente DOCX) a OneDrive del estudio, dentro de la carpeta
de un expediente.

Flujo:
  1. Lee refresh_token de Supabase tabla cloud_tokens (provider='microsoft').
     Lo obtiene vía REST API con el SERVICE_ROLE_KEY que el trigger tenga en env.
  2. Cambia refresh_token por access_token en login.microsoftonline.com.
  3. PUT a Microsoft Graph: /drives/{SHARED_DRIVE_ID}/items/{onedrive_id}:/{ruta_rel}:/content
     con el archivo como body.
  4. Devuelve (stdout) JSON con {webUrl, id} del archivo subido.

Uso:
  python3 upload_onedrive.py \
    --onedrive-id {onedrive_id_del_expediente} \
    --subpath "Borradores caducidad/2026-04-18/pronto_VALLEJOS.docx" \
    --file /tmp/caducidad/2026-04-18/pronto_VALLEJOS.docx

Env vars requeridas (las carga del entorno):
  SUPABASE_URL           — https://wdgdbbcwcrirpnfdmykh.supabase.co
  SUPABASE_SERVICE_KEY   — service_role key (para leer cloud_tokens)
  MS_CLIENT_ID           — 97970b5b-262c-45c4-a5e0-f91e40860d60
  MS_TENANT_ID           — 563aed0f-51a2-4fad-98be-73054f96624a
  SHARED_DRIVE_ID        — b!DWGMY6sEh0OcgPK7dDTJDpqdri_ncgZNi1uyttHXWPcrleCPn4_oRbaw9dJBhhVM
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def http_post_form(url, form_data):
    data = urllib.parse.urlencode(form_data).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def http_get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def http_put_binary(url, data, headers):
    req = urllib.request.Request(url, data=data, method="PUT", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def http_patch_json(url, body, headers):
    data = json.dumps(body).encode()
    h = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method="PATCH", headers=h)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_refresh_token():
    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    url = f"{supabase_url}/rest/v1/cloud_tokens?provider=eq.microsoft&select=refresh_token"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    rows = http_get_json(url, headers)
    if not rows or not rows[0].get("refresh_token"):
        raise RuntimeError("No hay refresh_token para provider=microsoft en cloud_tokens")
    return rows[0]["refresh_token"]


def refresh_access_token(refresh_token):
    tenant = os.environ["MS_TENANT_ID"]
    client_id = os.environ["MS_CLIENT_ID"]
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    resp = http_post_form(url, {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "Files.ReadWrite.All Sites.Read.All offline_access",
    })
    if "access_token" not in resp:
        raise RuntimeError(f"No se pudo refrescar: {resp}")
    return resp["access_token"], resp.get("refresh_token")


def actualizar_refresh_si_cambia(nuevo_refresh):
    if not nuevo_refresh:
        return
    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    url = f"{supabase_url}/rest/v1/cloud_tokens?provider=eq.microsoft"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "return=minimal",
    }
    http_patch_json(url, {"refresh_token": nuevo_refresh}, headers)


def subir(file_path, onedrive_id, subpath, access_token):
    shared = os.environ["SHARED_DRIVE_ID"]
    # Encode subpath con slashes literales pero escapar caracteres raros
    subpath_enc = urllib.parse.quote(subpath, safe="/")
    url = f"https://graph.microsoft.com/v1.0/drives/{shared}/items/{onedrive_id}:/{subpath_enc}:/content"
    with open(file_path, "rb") as f:
        data = f.read()
    # Para archivos <4MB basta PUT directo. Los DOCX del skill son <1MB.
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }
    return http_put_binary(url, data, headers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onedrive-id", required=True, help="onedrive_id del expediente (item padre)")
    ap.add_argument("--subpath", required=True, help="ruta relativa dentro de la carpeta del exp")
    ap.add_argument("--file", required=True, help="path local del archivo a subir")
    ap.add_argument("--refresh-token", help="refresh_token directo (si no viene, se busca en Supabase con SUPABASE_SERVICE_KEY)")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ Archivo no existe: {args.file}", file=sys.stderr)
        sys.exit(1)

    refresh = args.refresh_token or get_refresh_token()
    access, nuevo_refresh = refresh_access_token(refresh)
    if not args.refresh_token:
        actualizar_refresh_si_cambia(nuevo_refresh)

    result = subir(args.file, args.onedrive_id, args.subpath, access)
    out = {"webUrl": result.get("webUrl"), "id": result.get("id"), "name": result.get("name")}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
