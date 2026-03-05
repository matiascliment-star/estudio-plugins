---
name: subir-escrito-pjn
description: >
  Subir escritos y borradores al PJN (Poder Judicial de la Nación) via escritos.pjn.gov.ar.
  Convierte el escrito a PDF y lo guarda como borrador usando el script de upload.
  Usa este skill siempre que el usuario pida: "subir escrito PJN", "guardar borrador PJN",
  "presentar escrito PJN", "borrador PJN", "escrito PJN", "subir borrador nación",
  "cargar escrito en PJN", "presentar en nación", "subir PDF al PJN",
  "borrador escritos.pjn", "mandar escrito al juzgado nacional",
  o cualquier tarea relacionada con subir o guardar escritos en el sistema de
  presentaciones electrónicas del PJN (escritos.pjn.gov.ar).
  También cuando el usuario dice "subir escrito" o "guardar borrador" en contexto de
  causas nacionales (CNT, CIV, COM, CAF, etc.).
  Triggers: "subir escrito", "guardar borrador", "borrador PJN", "escrito PJN",
  "presentar escrito nación", "escritos.pjn", "subir al juzgado".
---

# Skill: Subir Escrito / Borrador al PJN

Este skill se encarga de subir un escrito como borrador al sistema de presentaciones electrónicas del PJN (escritos.pjn.gov.ar). El borrador queda en la bandeja MIS_BORRADORES para que el usuario lo firme digitalmente y lo presente desde el portal.

## REGLA PRINCIPAL: NO preguntar datos que se pueden inferir

**El agente NO debe preguntar al usuario datos que puede extraer del documento o inferir del contexto.** Específicamente:

- **Número de expediente**: Si el usuario sube un PDF o da un texto, LEER el contenido y extraer el número de expediente (buscar patrones como "Expte. Nº", "EXPTE.", "CNT", "CIV", "COM", "CAF" seguido de número/año).
- **Tipo de escrito**: Inferir del contenido. Impugnaciones, recursos, contestaciones de traslado = E. Pronto despachos, acuse recibo = M. Contestación de demanda = C. Demanda inicial = I.
- **Descripción del adjunto**: Generar automáticamente del título o sumario del escrito.

**Solo preguntar al usuario si el dato NO se puede extraer ni inferir** (ej: el PDF no menciona el expediente, o es ambiguo entre dos tipos).

## Flujo completo

### Si el usuario sube un PDF ya hecho:
1. **Leer el PDF** para extraer: número de expediente, título/sumario, tipo de escrito
2. **Copiar el PDF a /tmp** si no está ahí
3. **Leer `.env`** para credenciales PJN
4. **Ejecutar el script de upload** directamente con los datos extraídos
5. **Informar resultado** al usuario

### Si el usuario da texto para convertir a PDF:
1. **Extraer** del texto: número de expediente, título/sumario, tipo de escrito
2. **Generar PDF** con reportlab y guardar en `/tmp/escrito_pjn.pdf`
3. **Leer `.env`** para credenciales PJN
4. **Ejecutar el script de upload** con los datos extraídos
5. **Informar resultado** al usuario

## Credenciales

Las credenciales del PJN están en el archivo `.env` de la carpeta del usuario:
- `PJN_USUARIO`: CUIT sin guiones (ej: `20313806198`)
- `PJN_PASSWORD`: contraseña del PJN

Leer `.env` antes de hacer cualquier operación. Si no hay credenciales, pedirlas al usuario.

## Conversión del escrito a PDF (solo si el usuario da texto, NO si ya da un PDF)

```python
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT

def crear_pdf_escrito(texto, titulo, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=3*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    estilo_cuerpo = ParagraphStyle('CuerpoEscrito', parent=styles['Normal'], fontSize=12, leading=16, alignment=TA_JUSTIFY, spaceAfter=12, fontName='Times-Roman')
    estilo_titulo = ParagraphStyle('TituloEscrito', parent=styles['Normal'], fontSize=12, leading=16, alignment=TA_RIGHT, spaceAfter=24, fontName='Times-Bold')
    elementos = [Paragraph(titulo.upper(), estilo_titulo), Spacer(1, 12)]
    for p in texto.split('\n\n'):
        p = p.strip()
        if p:
            p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
            elementos.append(Paragraph(p, estilo_cuerpo))
    doc.build(elementos)
```

## Subida del borrador con el script helper

El script acepta **`--numero-expediente`** (ej: "CNT 40454/2024") O **`--id-expediente`** (numérico). Siempre preferir `--numero-expediente` porque no requiere buscar el ID interno.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/upload_pjn_borrador.py \
  --usuario "20313806198" \
  --password "CONTRASEÑA" \
  --numero-expediente "CNT 40454/2024" \
  --tipo "E" \
  --pdf-path "/tmp/escrito_pjn.pdf" \
  --pdf-nombre "recurso-error-sentencia.pdf" \
  --descripcion "PARTE ACTORA INTERPONE RECURSO"
```

### Parámetros del script

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--usuario` | Sí | CUIT del usuario PJN |
| `--password` | Sí | Password del PJN |
| `--numero-expediente` | Sí* | Número de expediente (ej: "CNT 40454/2024") |
| `--id-expediente` | Sí* | Alternativa: ID interno numérico (*uno de los dos) |
| `--tipo` | Sí | Código tipo de escrito: M, E, C, I, H |
| `--pdf-path` | Sí | Path al archivo PDF en disco |
| `--pdf-nombre` | Sí | Nombre descriptivo del PDF |
| `--descripcion` | Sí | Descripción del escrito |
| `--id-oficina-destino` | No | ID oficina destino (opcional) |

## Tipos de escrito

| Código | Tipo | Cuándo usarlo |
|--------|------|---------------|
| M | MERO TRÁMITE | Pronto despachos, acuse recibo, solicitudes simples |
| E | ESCRITO | Escritos genéricos, impugnaciones, recursos, contestaciones de traslados |
| C | CONTESTACIÓN DEMANDA | Contestación de demanda específicamente |
| I | ESCRITO DEMANDA / DOCUMENTAL DE INICIO | Demanda inicial con documental |
| H | SOLICITUD HABILITACIÓN DÍA | Habilitación de día y hora |

## Formato del número de expediente

El formato es: `JURISDICCION NUMERO/AÑO`. Ejemplos:
- `CNT 6379/2024` (laboral nacional)
- `CIV 45231/2023` (civil nacional)
- `COM 12345/2024` (comercial)
- `CAF 8765/2023` (contencioso administrativo federal)

**Cómo extraer del documento**: Buscar patrones como "Expte. Nº 40.454/2024" y combinar con la jurisdicción (si el documento menciona "Juzgado Nacional del Trabajo" → CNT, "Juzgado Civil" → CIV, etc.). El punto en "40.454" se saca: "CNT 40454/2024".

## IMPORTANTE: Método de upload

**NUNCA** intentar:
- Pasar el base64 del PDF como parámetro de la tool MCP directamente
- Llamar a las APIs del PJN directamente via curl, fetch, axios
- Leer el base64 del PDF con el Read tool

**SIEMPRE** usar el script `upload_pjn_borrador.py` con `--numero-expediente`.

## Instrucciones para el agente (resumen)

1. Leer `.env` → `PJN_USUARIO` y `PJN_PASSWORD`
2. Si el usuario sube un PDF → leerlo, extraer expediente + tipo. Si da texto → generar PDF con reportlab
3. **NO preguntar** lo que se puede extraer o inferir
4. Copiar/generar PDF en `/tmp/`
5. Ejecutar `upload_pjn_borrador.py` con `--numero-expediente` (NO hace falta buscar el ID interno)
6. Informar resultado + recordar que debe firmar desde escritos.pjn.gov.ar

Si el usuario quiere enviar el borrador al tribunal (IRREVERSIBLE), usar la tool MCP `pjn_enviar_borrador`. Confirmar SIEMPRE antes.
