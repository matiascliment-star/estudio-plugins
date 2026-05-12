---
name: backfill-firmados-archivo
description: >
  Procesa un export de WhatsApp del grupo "FIRMÓ 🖋️📈" (archivo `_chat.txt`)
  y detecta qué firmados están cargados en `casos_srt` y cuáles se perdieron.
  Para los faltantes desde una fecha de corte (default 2026-01-01), reporta
  nombre, teléfono y alta médica detectada, y opcionalmente los crea
  automáticamente en `casos_srt`. Triggers: "procesar chat firmó archivo",
  "backfill firmados desde txt", "recuperar firmados perdidos".
version: 1.0.0
---

# Backfill Firmados desde Archivo

## OBJETIVO

Procesar un export de WhatsApp del grupo "FIRMÓ 🖋️📈" para encontrar
clientes que firmaron pero **nunca se cargaron** en `casos_srt`. Los compara
contra la base por nombre normalizado y teléfono, y reporta:

- ✅ **Encontrados**: firmados del chat que ya están en la base.
- ❌ **Faltantes**: firmados del chat que NO están en la base (estos son los
  que potencialmente perdimos).
- 🤔 **Ambiguos**: nombre coincide con varios casos (revisar manual).

## DATOS DE REFERENCIA

- **Supabase**: `project_id = wdgdbbcwcrirpnfdmykh`
- **Path típico del archivo** (en máquina de Matías):
  `/Users/matiaschristiangarciacliment/Library/Mobile Documents/com~apple~CloudDocs/Descargas/_chat.txt`
- **Fecha de corte recomendada**: `2026-01-01` (lo de 2024-2025 ya está
  procesado o pasó por otro flujo).
- **Variantes del marcador FIRMÓ** que el regex debe agarrar:
  - `*FIRMÓ*`, `*FIRMO*`, `*Firmó*`, `*Firmo*`, `FIRMÓ`, `FIRMO`

## ENTRADA / SALIDA

**Entrada**: path al archivo `.txt` (export de WhatsApp).

**Salida**: archivo `/tmp/firmados-backfill-report.json` con estructura:

```json
{
  "total_firmados_chat": 699,
  "desde_corte": 250,
  "encontrados": [{"nombre": "...", "telefono": "...", "fecha": "...", "caso_srt_id": 123}],
  "faltantes": [{"nombre": "...", "telefono": "...", "fecha": "...", "alta": true, "linea_chat": 42}],
  "ambiguos": [{"nombre": "...", "candidatos": [...]}]
}
```

## WORKFLOW

### Paso 1 — Verificar que el archivo existe

```bash
ls -la "$ARCHIVO"
wc -l "$ARCHIVO"
```

Si no existe, abortar. Si existe, mostrar tamaño y cantidad de líneas.

### Paso 2 — Ejecutar el parser Python embebido

Guardar este script como `/tmp/parse_firmados.py` y correrlo con:

```bash
python3 /tmp/parse_firmados.py "$ARCHIVO" 2026-01-01 > /tmp/firmados-parsed.json
```

**Script completo** (guardar tal cual):

```python
#!/usr/bin/env python3
"""Parsea un export de WhatsApp del grupo FIRMÓ y extrae firmados estructurados."""
import re
import json
import sys
from datetime import datetime

if len(sys.argv) < 3:
    print("Uso: parse_firmados.py <archivo.txt> <fecha_corte_YYYY-MM-DD>", file=sys.stderr)
    sys.exit(1)

archivo = sys.argv[1]
fecha_corte = datetime.strptime(sys.argv[2], "%Y-%m-%d")

# WhatsApp export usa formato [M/D/YY, HH:MM:SS] Autor: Mensaje
RX_LINEA = re.compile(r'^\[(\d{1,2})/(\d{1,2})/(\d{2}),\s*(\d{1,2}):(\d{2}):(\d{2})\]\s*([^:]+?):\s*(.*)$')

# FIRMÓ con muchas variantes
RX_FIRMO = re.compile(r'\*?(FIRM[ÓO]|Firm[oó])\*?', re.IGNORECASE)
RX_TELEFONO = re.compile(r'\(([\s\+\d\-]+)\)')
RX_FECHA_ACC = re.compile(r'[Ff]echa del accidente[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})')

# Nombre: buscar entre asteriscos o entre el ). y un punto final
RX_NOMBRE_AST = re.compile(r'\*([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s,]{4,80})\*')
RX_NOMBRE_PLAIN = re.compile(r'\)\s*\.?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s,]{4,80}?)(?:\.\s|$|,\s+Está|,\s+Con|,\s+En)', re.IGNORECASE)

def detectar_alta(texto):
    t = texto.lower()
    if 'sin alta' in t or 'no tiene alta' in t:
        return False
    if 'con alta' in t or 'ya tiene' in t or 'ya tenía' in t or 'alta médica' in t.replace('sin alta médica', ''):
        return True
    if 'tratamiento' in t and 'alta' not in t:
        return False
    return None  # indefinido

firmados = []
linea_actual = ''
fecha_actual = None
autor_actual = None
nro_linea = 0

with open(archivo, 'r', encoding='utf-8') as f:
    for n, raw in enumerate(f, 1):
        raw = raw.rstrip('\r\n').lstrip('\u200e')
        m = RX_LINEA.match(raw)
        if m:
            # nueva línea con timestamp → procesar la anterior si tenía FIRMÓ
            if linea_actual and RX_FIRMO.search(linea_actual) and fecha_actual >= fecha_corte:
                tel_m = RX_TELEFONO.search(linea_actual)
                nom_m = RX_NOMBRE_AST.search(linea_actual) or RX_NOMBRE_PLAIN.search(linea_actual)
                if tel_m or nom_m:
                    firmados.append({
                        'fecha': fecha_actual.strftime('%Y-%m-%d'),
                        'autor': autor_actual,
                        'telefono': tel_m.group(1).strip() if tel_m else None,
                        'nombre_raw': (nom_m.group(1).strip().rstrip(',.').strip() if nom_m else None),
                        'alta': detectar_alta(linea_actual),
                        'fecha_accidente': (RX_FECHA_ACC.search(linea_actual).group(1) if RX_FECHA_ACC.search(linea_actual) else None),
                        'linea_chat': nro_linea,
                        'contenido': linea_actual[:300]
                    })
            mes, dia, anio, h, mi, s, autor, contenido = m.groups()
            anio_int = int(anio) + (2000 if int(anio) < 50 else 1900)
            try:
                fecha_actual = datetime(anio_int, int(mes), int(dia), int(h), int(mi), int(s))
            except ValueError:
                fecha_actual = None
            autor_actual = autor.strip()
            linea_actual = contenido
            nro_linea = n
        else:
            # continuación de línea anterior
            linea_actual += ' ' + raw

# último mensaje
if linea_actual and RX_FIRMO.search(linea_actual) and fecha_actual and fecha_actual >= fecha_corte:
    tel_m = RX_TELEFONO.search(linea_actual)
    nom_m = RX_NOMBRE_AST.search(linea_actual) or RX_NOMBRE_PLAIN.search(linea_actual)
    if tel_m or nom_m:
        firmados.append({
            'fecha': fecha_actual.strftime('%Y-%m-%d'),
            'autor': autor_actual,
            'telefono': tel_m.group(1).strip() if tel_m else None,
            'nombre_raw': nom_m.group(1).strip().rstrip(',.').strip() if nom_m else None,
            'alta': detectar_alta(linea_actual),
            'fecha_accidente': (RX_FECHA_ACC.search(linea_actual).group(1) if RX_FECHA_ACC.search(linea_actual) else None),
            'linea_chat': nro_linea,
            'contenido': linea_actual[:300]
        })

print(json.dumps(firmados, ensure_ascii=False, indent=2))
print(f"\n# Total firmados desde {fecha_corte.date()}: {len(firmados)}", file=sys.stderr)
```

### Paso 3 — Cargar el JSON parseado a una tabla temporal de Supabase

```sql
CREATE TEMP TABLE IF NOT EXISTS _firmados_archivo (
  fecha DATE,
  autor TEXT,
  telefono TEXT,
  nombre_raw TEXT,
  alta BOOLEAN,
  fecha_accidente TEXT,
  linea_chat INT,
  contenido TEXT
);
-- INSERT bulk desde el JSON parseado (usar el cliente de Supabase con el JSON
-- cargado en /tmp/firmados-parsed.json)
```

### Paso 4 — Cruzar con casos_srt

```sql
WITH parsed AS (
  SELECT *,
    fn_normalize_nombre(nombre_raw) AS nn,
    regexp_replace(coalesce(telefono, ''), '[^0-9]', '', 'g') AS tel_norm
  FROM _firmados_archivo
),
casos AS (
  SELECT id, nombre, telefono, activo, etapa,
    fn_normalize_nombre(nombre) AS nn,
    regexp_replace(coalesce(telefono, ''), '[^0-9]', '', 'g') AS tel_norm
  FROM casos_srt
),
matches AS (
  SELECT p.*, c.id AS caso_id, c.activo, c.etapa,
    CASE
      WHEN p.tel_norm <> '' AND p.tel_norm = c.tel_norm THEN 'telefono'
      WHEN p.nn IS NOT NULL AND p.nn = c.nn THEN 'nombre_exacto'
      WHEN p.nn IS NOT NULL AND length(p.nn) >= 10
        AND (c.nn ILIKE '%' || split_part(p.nn, ' ', 1) || '%'
             AND c.nn ILIKE '%' || split_part(p.nn, ' ', 2) || '%') THEN 'nombre_fuzzy'
      ELSE NULL
    END AS tipo_match
  FROM parsed p
  LEFT JOIN casos c ON
    (p.tel_norm <> '' AND p.tel_norm = c.tel_norm)
    OR (p.nn IS NOT NULL AND p.nn = c.nn)
    OR (p.nn IS NOT NULL AND length(p.nn) >= 10
        AND c.nn ILIKE '%' || split_part(p.nn, ' ', 1) || '%'
        AND c.nn ILIKE '%' || split_part(p.nn, ' ', 2) || '%')
),
encontrados AS (
  SELECT DISTINCT ON (linea_chat) linea_chat, nombre_raw, telefono, fecha, caso_id, tipo_match
  FROM matches WHERE tipo_match IS NOT NULL
  ORDER BY linea_chat, CASE tipo_match
    WHEN 'telefono' THEN 1 WHEN 'nombre_exacto' THEN 2 WHEN 'nombre_fuzzy' THEN 3 END
),
faltantes AS (
  SELECT linea_chat, nombre_raw, telefono, fecha, alta, fecha_accidente, contenido
  FROM parsed
  WHERE linea_chat NOT IN (SELECT linea_chat FROM encontrados)
)
SELECT
  (SELECT COUNT(*) FROM parsed) AS total_chat,
  (SELECT COUNT(*) FROM encontrados) AS encontrados,
  (SELECT COUNT(*) FROM faltantes) AS faltantes;
```

### Paso 5 — Reporte

Generar dos secciones:

**A. Resumen ejecutivo**: total, encontrados, faltantes, ambiguos.

**B. Lista de faltantes** (los que efectivamente se perdieron):

```sql
SELECT fecha, nombre_raw, telefono, alta, contenido
FROM faltantes
ORDER BY fecha;
```

Mostrar todos. Si son >50, mostrar los 50 más recientes + total.

### Paso 6 — Opcional: crear los faltantes

Si Matías confirma, INSERT en `casos_srt` con `origen = 'BACKFILL_CHAT_TXT'`,
`auto_creado = true`, etapa según `alta` (TRUE → POR_INICIAR, FALSE/NULL →
TRATAMIENTO), `firmado_por = autor del mensaje`, `fecha_firma = fecha del
mensaje`.

NO ejecutar este paso sin confirmación humana — el dataset puede tener
errores de parsing.

## REGLAS

- No procesar antes de `fecha_corte` (default 2026-01-01).
- Los duplicados internos en el chat (cliente firmado 2 veces) se dedup
  por teléfono + nombre normalizado.
- Si nombre_raw aparece con coma ("Apellido, Nombre"), normalizar como
  "Apellido Nombre" antes de comparar.
- Detección de alta usa heurística simple — si dice "Con alta" → TRUE,
  si dice "En tratamiento" o "Sin alta" → FALSE, si no menciona nada →
  NULL (queda en TRATAMIENTO por default).

## OUTPUT FINAL

Reporte ejecutivo en stdout + archivo `/tmp/firmados-backfill-report.json`
con lista completa. Si Matías confirma, ejecutar Paso 6.
