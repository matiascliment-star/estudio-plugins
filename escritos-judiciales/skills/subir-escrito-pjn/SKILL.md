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

Este skill se encarga de convertir un escrito a PDF y subirlo como borrador al sistema de presentaciones electrónicas del PJN (escritos.pjn.gov.ar). El borrador queda en la bandeja MIS_BORRADORES para que el usuario lo firme digitalmente y lo presente desde el portal.

## Flujo completo

1. **Obtener el texto del escrito** (el usuario lo dicta, lo pega, o lo tenés de un paso previo)
2. **Convertir a PDF** usando Python + reportlab
3. **Guardar el PDF en un archivo temporal** (ej: `/tmp/escrito_pjn.pdf`)
4. **Ejecutar el script `upload_pjn_borrador.py`** que se encarga de codificar en base64 y llamar al MCP server
5. **Confirmar al usuario** que el borrador quedó guardado

## Credenciales

Las credenciales del PJN están en el archivo `.env` de la carpeta del usuario:
- `PJN_USUARIO`: CUIT sin guiones (ej: `20313806198`)
- `PJN_PASSWORD`: contraseña del PJN

Leer `.env` antes de hacer cualquier operación. Si no hay credenciales, pedirlas al usuario.

## Conversión del escrito a PDF

El PJN requiere que el escrito se suba como PDF. Hay dos caminos según el input:

### Si el escrito es texto plano o markdown

Usar Python con reportlab para generar el PDF. El estilo judicial estándar es:

```python
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT

def crear_pdf_escrito(texto, titulo, output_path):
    """Genera un PDF con formato judicial estándar."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=3*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Estilo para cuerpo del escrito
    estilo_cuerpo = ParagraphStyle(
        'CuerpoEscrito',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        fontName='Times-Roman'
    )

    # Estilo para título/sumario
    estilo_titulo = ParagraphStyle(
        'TituloEscrito',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        alignment=TA_RIGHT,
        spaceAfter=24,
        fontName='Times-Bold'
    )

    elementos = []

    # Título/sumario arriba a la derecha
    elementos.append(Paragraph(titulo.upper(), estilo_titulo))
    elementos.append(Spacer(1, 12))

    # Cuerpo del escrito
    parrafos = texto.split('\n\n')
    for p in parrafos:
        p = p.strip()
        if p:
            # Escapar caracteres especiales para reportlab
            p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            p = p.replace('\n', '<br/>')
            elementos.append(Paragraph(p, estilo_cuerpo))

    doc.build(elementos)
```

### Si el escrito es HTML

Usar weasyprint para convertir HTML a PDF:

```python
import weasyprint

def html_a_pdf(html_content, output_path):
    """Convierte HTML a PDF preservando formato."""
    css = weasyprint.CSS(string='''
        @page { size: A4; margin: 2cm 2cm 2cm 3cm; }
        body { font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.4; }
        p { text-align: justify; margin-bottom: 12pt; }
    ''')
    weasyprint.HTML(string=html_content).write_pdf(output_path, stylesheets=[css])
```

### Si el usuario ya tiene un PDF

Si el usuario pasa un archivo PDF directamente, no hace falta convertir nada. Usar el path del PDF directamente con el script de upload.

## Subida del borrador con el script helper

**IMPORTANTE**: NO intentar pasar el contenido base64 del PDF como parámetro de una tool MCP. Los PDFs son demasiado grandes para pasar como string en el contexto. En su lugar, usar el script helper que maneja todo internamente.

Una vez que tenés el PDF guardado en un archivo (ej: `/tmp/escrito_pjn.pdf`), ejecutar:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/upload_pjn_borrador.py \
  --usuario "20313806198" \
  --password "CONTRASEÑA" \
  --id-expediente 123456 \
  --tipo "E" \
  --pdf-path "/tmp/escrito_pjn.pdf" \
  --pdf-nombre "escrito.pdf" \
  --descripcion "IMPUGNA PERICIA"
```

El script:
1. Lee el PDF del disco
2. Lo codifica en base64 internamente
3. Se conecta al MCP server por HTTP
4. Llama a `pjn_guardar_borrador`
5. Imprime el resultado en stdout

### Parámetros del script

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--usuario` | Sí | CUIT del usuario PJN |
| `--password` | Sí | Password del PJN |
| `--id-expediente` | Sí | ID interno del expediente (número entero) |
| `--tipo` | Sí | Código tipo de escrito: M, E, C, I, H |
| `--pdf-path` | Sí | Path al archivo PDF en disco |
| `--pdf-nombre` | Sí | Nombre descriptivo del PDF |
| `--descripcion` | Sí | Descripción del escrito |
| `--id-oficina-destino` | No | ID oficina destino (opcional) |

### Obtener el ID del expediente

El script necesita el ID interno del expediente (no el número de causa). Para obtenerlo, usar la tool MCP `pjn_buscar_expediente` con el número de expediente (ej: "CNT 6379/2024"). La tool devuelve el `id` interno que se usa como `--id-expediente`.

## Tipos de escrito

| Código | Tipo | Cuándo usarlo |
|--------|------|---------------|
| M | MERO TRÁMITE | Pronto despachos, acuse recibo, solicitudes simples |
| E | ESCRITO | Escritos genéricos, impugnaciones, contestaciones de traslados |
| C | CONTESTACIÓN DEMANDA | Contestación de demanda específicamente |
| I | ESCRITO DEMANDA / DOCUMENTAL DE INICIO | Demanda inicial con documental |
| H | SOLICITUD HABILITACIÓN DÍA | Habilitación de día y hora |

Si el usuario no especifica el tipo, inferirlo del contenido. Por ejemplo, un "pronto despacho" es tipo M, una "impugnación de pericia" es tipo E.

## Formato del número de expediente

El formato es: `JURISDICCION NUMERO/AÑO`

Ejemplos:
- `CNT 6379/2024` (laboral nacional)
- `CIV 45231/2023` (civil nacional)
- `COM 12345/2024` (comercial)
- `CAF 8765/2023` (contencioso administrativo federal)

## IMPORTANTE: Método de upload

**NUNCA** intentar:
- Pasar el base64 del PDF como parámetro de la tool MCP `pjn_guardar_borrador` directamente (es demasiado grande para el contexto del agente)
- Llamar a las APIs del PJN directamente via curl, fetch, axios u otro método HTTP
- Leer el base64 del PDF con el Read tool (trunca líneas largas)

**SIEMPRE** usar el script `upload_pjn_borrador.py` que maneja todo internamente. El script lee el PDF del disco, lo codifica, y llama al MCP server — el base64 nunca pasa por el contexto del agente.

Si el script no está disponible o falla con error de conexión, informar al usuario que el servidor MCP no está conectado y que debe verificar su configuración.

## Instrucciones para el agente

1. Leer `.env` para obtener `PJN_USUARIO` y `PJN_PASSWORD`
2. Confirmar con el usuario: número de expediente, tipo de escrito, y contenido
3. Obtener el ID interno del expediente usando la tool MCP `pjn_buscar_expediente` (si solo tenés el número de causa)
4. Generar el PDF con Python + reportlab (instalar con `pip install reportlab --break-system-packages` si hace falta). Guardar en `/tmp/escrito_pjn.pdf`
5. Ejecutar el script `${CLAUDE_PLUGIN_ROOT}/scripts/upload_pjn_borrador.py` con los parámetros correctos
6. Informar al usuario el resultado (éxito + datos del borrador)
7. Recordar al usuario que debe firmar digitalmente el borrador desde escritos.pjn.gov.ar

Si el usuario también quiere enviar el borrador al tribunal (acción IRREVERSIBLE), usar la **tool MCP** `pjn_enviar_borrador` con el `id_escrito` devuelto. Confirmar SIEMPRE antes de enviar porque no se puede deshacer.
