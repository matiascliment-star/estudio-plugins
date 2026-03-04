---
name: subir-escrito-pjn
description: >
  Subir escritos y borradores al PJN (Poder Judicial de la Nación) via escritos.pjn.gov.ar.
  Convierte el escrito a PDF y lo guarda como borrador usando la tool MCP pjn_guardar_borrador.
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
2. **Convertir a PDF** usando Python + reportlab (o weasyprint si hay HTML complejo)
3. **Codificar el PDF en base64**
4. **Llamar a la tool MCP `pjn_guardar_borrador`** con los parámetros correctos
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

Si el usuario pasa un archivo PDF directamente, no hace falta convertir nada. Solo leer el archivo y codificarlo en base64.

## Llamada a la tool MCP

Una vez que tenés el PDF en base64, llamar a `pjn_guardar_borrador`:

```
Tool: pjn_guardar_borrador
Params:
  usuario: <PJN_USUARIO del .env>
  password: <PJN_PASSWORD del .env>
  numero_expediente: "CNT 6379/2024"  (o el que corresponda)
  tipo_escrito: "E"  (ver tabla de tipos abajo)
  pdf_base64: <el PDF codificado en base64>
  pdf_nombre: "escrito.pdf"  (nombre descriptivo)
  descripcion_adjunto: "IMPUGNA PERICIA"  (descripción del escrito)
```

La tool resuelve automáticamente el ID interno del expediente a partir del número.

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

## IMPORTANTE: Uso obligatorio de tools MCP

**NUNCA** intentar llamar a las APIs del PJN directamente via Node.js, curl, fetch, axios, o cualquier otro método HTTP directo. **SIEMPRE** usar las tools MCP provistas (`pjn_guardar_borrador`, `pjn_enviar_borrador`). Estas tools MCP ya están disponibles en tu entorno como herramientas que podés invocar directamente — no necesitás importar módulos, instalar paquetes, ni escribir código para hacer las llamadas HTTP. Simplemente invocá la tool MCP con los parámetros indicados.

Si al intentar usar la tool MCP recibís un error de que no existe o no está disponible, **informar al usuario** que el servidor MCP del scraper judicial no está conectado y que debe verificar su configuración. **No** intentar workarounds con Node.js o cualquier otro método.

## Instrucciones para el agente

1. Leer `.env` para obtener `PJN_USUARIO` y `PJN_PASSWORD`
2. Confirmar con el usuario: número de expediente, tipo de escrito, y contenido
3. Generar el PDF (instalar `pip install reportlab --break-system-packages` si hace falta)
4. Codificar en base64
5. Llamar a la **tool MCP** `pjn_guardar_borrador` (NO via Node.js, NO via curl — usar la tool MCP directamente)
6. Informar al usuario el resultado (éxito + ID del borrador)
7. Recordar al usuario que debe firmar digitalmente el borrador desde escritos.pjn.gov.ar

Si el usuario también quiere enviar el borrador al tribunal (acción IRREVERSIBLE), usar la **tool MCP** `pjn_enviar_borrador` con el `id_escrito` devuelto. Confirmar SIEMPRE antes de enviar porque no se puede deshacer.
