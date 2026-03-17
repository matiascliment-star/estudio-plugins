---
name: subir-escrito-mev
description: >
  Subir escritos y borradores al MEV/SCBA (Provincia de Buenos Aires) via
  notificaciones.scba.gov.ar. Convierte escrito a HTML y guarda como borrador
  usando scba_guardar_borrador o el script de upload para adjuntos.
  Usar cuando el usuario pida: "subir escrito SCBA", "borrador provincia",
  "escrito MEV", "borrador MEV", "presentar escrito SCBA", "subir escrito provincia",
  "borrador notificaciones.scba", "subir al tribunal de provincia",
  "adjuntar documental SCBA", "subir PDF al MEV", o cualquier tarea de subir
  escritos/borradores en SCBA. También cuando dice "subir escrito" o "guardar
  borrador" en contexto de causas de Provincia de Buenos Aires.
  Triggers: "borrador SCBA", "escrito MEV", "borrador provincia",
  "subir escrito provincia", "adjunto SCBA", "notificaciones.scba".
---

# Skill: Subir Escrito / Borrador al MEV (SCBA - Provincia de Buenos Aires)

Este skill se encarga de convertir un escrito a HTML y subirlo como borrador al sistema de presentaciones electrónicas de la SCBA (notificaciones.scba.gov.ar). El borrador queda guardado para que el usuario lo firme digitalmente y lo presente desde el portal web.

A diferencia del PJN (que usa PDF), la SCBA trabaja con HTML — el contenido del escrito se renderiza en CKEditor dentro del portal. Si además hay documental (PDFs adjuntos), se usa el script helper para evitar problemas de tamaño con el base64.

## REGLA CRÍTICA: PRESERVAR EL FORMATO EXACTO DEL DOCUMENTO APROBADO

**NUNCA subir un documento con formato distinto al que el usuario aprobó.** El formato del escrito es tan importante como su contenido. Cuando el usuario entrega un Word (.docx) o un PDF ya formateado, el HTML que se suba al MEV debe reproducir EXACTAMENTE el mismo formato visual del original.

### Qué se debe preservar exactamente:
- **Negritas** → `<strong>` o `<b>`
- **Subrayados** → `<u>` (NO usar `<span style="text-decoration:underline">`, usar directamente `<u>`)
- **Cursivas** → `<em>` o `<i>`
- **Colores de texto** → `<span style="color: #XXXXXX">` (si el documento usa colores, mantenerlos)
- **Tablas** → `<table>`, `<tr>`, `<td>`, `<th>` con bordes y ancho de columnas
- **Alineación** → `style="text-align: justify/center/right"`
- **Listas** numeradas y con viñetas → `<ol>`, `<ul>`, `<li>`
- **Tamaño de fuente** si varía → `<span style="font-size: Xpx">`

### Cómo convertir según el formato de origen:

#### Si el usuario da un Word (.docx):
**USAR `python-docx` o `mammoth`** para extraer el HTML preservando formato:
```bash
pip install mammoth --break-system-packages
```
```python
import mammoth
with open("documento.docx", "rb") as f:
    result = mammoth.convert_to_html(f)
    html = result.value  # Preserva negritas, cursivas, subrayados, tablas, listas
```
`mammoth` convierte Word a HTML limpio preservando: negritas (`<strong>`), cursivas (`<em>`), subrayados, tablas, listas, links. Alternativa: `python-docx` para mayor control manual.

**NO usar la función simple `texto_a_html_scba()`** para convertir Word — esa función es solo para texto plano y pierde TODO el formato.

#### Si el usuario da un PDF:
Extraer el texto con formato. Si el PDF tiene formato complejo (tablas, colores), considerar usar `pdfplumber` o `pymupdf` para extraer preservando estructura, y reconstruir el HTML respetando el formato original.

#### Si el usuario da texto plano (sin archivo):
Ahí sí usar la función `texto_a_html_scba()` estándar. Pero si el usuario indica formato específico (ej: "poné tal parte en negrita", "subrayá el título"), respetarlo en el HTML generado.

### Regla de oro:
**Si el usuario aprobó un documento con determinado formato, lo que se sube al MEV debe verse EXACTAMENTE igual.** Si no podés preservar el formato, informar al usuario ANTES de subir — NUNCA subir algo con formato distinto sin avisar.

## Flujo completo

### Si el usuario da un Word (.docx) — sin adjuntos
1. **Leer el Word** y extraer HTML con `mammoth` preservando TODO el formato (negritas, subrayados, colores, tablas)
2. **NO usar la función `texto_a_html_scba()`** — pierde el formato del Word
3. **Obtener los IDs de la causa** (id_org e id_causa del MEV)
4. **Llamar a la tool MCP `scba_guardar_borrador`** con el HTML extraído
5. **Confirmar al usuario**

### Si el usuario da un Word (.docx) — con adjuntos
1. **Leer el Word** y extraer HTML con `mammoth` preservando formato
2. **Guardar el HTML** en archivo temporal
3. **Ejecutar el script `upload_scba_adjuntos.py`** con el HTML y los PDFs adjuntos
4. **Confirmar al usuario**

### Si el usuario da un PDF como escrito
1. **Extraer texto del PDF** preservando formato (negritas, tablas, estructura)
2. **Convertir a HTML** respetando el formato original del PDF
3. **Obtener los IDs de la causa** y subir como borrador
4. **Confirmar al usuario**

### Escrito solo texto plano (sin archivo, sin adjuntos)
1. **Obtener el texto del escrito**
2. **Convertir a HTML** con la función `texto_a_html_scba()` (formato judicial estándar)
3. **Obtener los IDs de la causa** (id_org e id_causa del MEV)
4. **Llamar a la tool MCP `scba_guardar_borrador`** (el HTML es texto pequeño, no hay problema)
5. **Confirmar al usuario**

### Escrito texto plano con documental (PDFs adjuntos)
1. **Obtener el texto del escrito + archivos PDF**
2. **Convertir texto a HTML** y guardar en archivo temporal
3. **Ejecutar el script `upload_scba_adjuntos.py`** que maneja los PDFs internamente
4. **Confirmar al usuario**

## Credenciales

Las credenciales de la SCBA están en el archivo `~/.env` (path absoluto: `/Users/matiaschristiangarciacliment/.env`):
- `MEV_USUARIO`: email de notificaciones SCBA (ej: `20313806198@notificaciones.scba.gov.ar`)
- `MEV_PASSWORD`: contraseña de notificaciones SCBA

**IMPORTANTE**: Siempre leer `~/.env` usando el path absoluto `/Users/matiaschristiangarciacliment/.env` (NO buscar `.env` en el directorio de trabajo actual, ya que puede variar). Si no hay credenciales en ese archivo, pedirlas al usuario.

## Conversión del escrito a HTML

El sistema SCBA espera HTML simple que se renderiza en CKEditor. No hace falta CSS sofisticado — solo tags HTML estándar.

### Conversión desde Word (.docx) — PRESERVAR FORMATO
```python
import mammoth
# mammoth preserva: negritas, cursivas, subrayados, tablas, listas, links
with open("documento.docx", "rb") as f:
    result = mammoth.convert_to_html(f)
    html = result.value
```
Instalar si no está: `pip install mammoth --break-system-packages`

**IMPORTANTE**: El HTML generado por mammoth ya viene con las tags correctas (`<strong>`, `<em>`, `<table>`, etc.) que CKEditor SCBA soporta. Usarlo directamente sin modificar el formato.

### Formato HTML judicial estándar (SOLO PARA TEXTO PLANO — NO usar para Word/PDF)

```python
def texto_a_html_scba(texto, titulo):
    """Convierte texto del escrito a HTML para SCBA."""

    # Título/sumario: centrado, negrita, subrayado
    html = f'<p style="text-align: center;"><strong><u>{titulo.upper()}</u></strong></p>\n'
    html += '<p>&nbsp;</p>\n'

    # Cuerpo del escrito
    parrafos = texto.split('\n\n')
    for p in parrafos:
        p = p.strip()
        if not p:
            continue
        # Convertir saltos simples a <br>
        p = p.replace('\n', '<br>')
        html += f'<p style="text-align: justify;">{p}</p>\n'

    return html
```

**IMPORTANTE sobre subrayado**: El título del escrito SIEMPRE debe llevar subrayado (`<u>` tag). CKEditor SCBA soporta `<u>` directamente. NO usar `style="text-decoration: underline"` con `<span>`, usar directamente la tag `<u>` que es más compatible.

### Si el input ya es HTML
Usarlo directamente. Solo verificar que no tenga tags que CKEditor no soporte (como `<script>`, `<style>`, etc.).

### Elementos HTML soportados por CKEditor SCBA
- `<p>`, `<br>`, `<strong>`, `<em>`, `<u>` — formatos básicos
- `<ul>`, `<ol>`, `<li>` — listas
- `<table>`, `<tr>`, `<td>`, `<th>` — tablas
- `style="text-align: justify/center/right"` — alineación
- `style="text-decoration: underline"` — subrayado

## Obtener IDs de la causa

Para guardar un borrador en SCBA necesitás dos IDs:
- **id_org**: ID del organismo (tribunal). Se obtiene del campo `ido` al listar causas del MEV.
- **id_causa**: ID de la causa. Se obtiene del campo `idc` al listar causas del MEV.

### Cómo obtener los IDs

**Opción 1**: Si el usuario ya sabe los IDs (porque los obtuvo antes), usarlos directamente.

**Opción 2**: Usar la tool MCP `mev_listar_causas` para obtener la lista de causas y buscar la correcta:
```
Tool: mev_listar_causas
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
```
Esto devuelve causas con campos `idc` e `ido`.

**Opción 3**: Si tenés el número de causa, buscar en la lista devuelta por `mev_listar_causas` la que coincida.

### Verificar info de la causa

Antes de guardar, podés consultar info con la tool MCP `scba_info_causa`:
```
Tool: scba_info_causa
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
  id_org: <ido de la causa>
  id_causa: <idc de la causa>
```
Esto confirma la carátula, organismo y si se puede guardar borrador.

## Guardar borrador SIN adjuntos (solo texto)

Para escritos sin adjuntos, usar la **tool MCP** `scba_guardar_borrador` directamente. El HTML es texto pequeño y no tiene problemas de tamaño:

```
Tool: scba_guardar_borrador
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
  id_org: <id del organismo>
  id_causa: <id de la causa>
  texto_html: "<p style='text-align: right;'><strong>PRONTO DESPACHO</strong></p>..."
  titulo: "PRONTO DESPACHO"
  tipo_presentacion: "1"
```

## Guardar borrador CON adjuntos (PDFs)

**IMPORTANTE**: Para escritos con PDFs adjuntos, NO intentar pasar el base64 de los PDFs como parámetro de la tool MCP. Los PDFs son demasiado grandes para el contexto del agente.

En su lugar, usar el script helper:

1. Guardar el HTML del escrito en un archivo temporal:
```bash
# Escribir el HTML a un archivo
```

2. Ejecutar el script:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/upload_scba_adjuntos.py \
  --usuario "user@notificaciones.scba.gov.ar" \
  --password "CONTRASEÑA" \
  --id-org 123 \
  --id-causa 456 \
  --titulo "ACOMPAÑA DOCUMENTAL" \
  --texto-html-file "/tmp/escrito_scba.html" \
  --adjuntos "/tmp/doc1.pdf" "/tmp/doc2.pdf" \
  --tipo-presentacion "1"
```

El script:
1. Lee el HTML del archivo
2. Lee cada PDF adjunto del disco
3. Codifica los PDFs en base64 internamente
4. Se conecta al MCP server por HTTP
5. Llama a `scba_guardar_borrador_adjuntos`
6. Imprime el resultado en stdout

### Parámetros del script

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--usuario` | Sí | Email MEV |
| `--password` | Sí | Password MEV |
| `--id-org` | Sí | ID del organismo |
| `--id-causa` | Sí | ID de la causa |
| `--titulo` | Sí | Título del escrito |
| `--texto-html` | Sí* | HTML inline del escrito |
| `--texto-html-file` | Sí* | Path a archivo con HTML (*alternativa a --texto-html) |
| `--adjuntos` | No | Paths a los PDFs adjuntos |
| `--tipo-presentacion` | No | Tipo (default: "1" = Escritos) |

## Tipos de presentación SCBA

| Código | Tipo |
|--------|------|
| 1 | Escritos (default — pronto despachos, impugnaciones, etc.) |
| 2 | Oficios |
| 3 | Cédulas |
| 4 | Mandamientos |

Si el usuario no especifica, usar "1" (Escritos) que es el más común.

## IMPORTANTE: Método de upload

**NUNCA** intentar:
- Pasar el base64 de PDFs adjuntos como parámetro de la tool MCP (es demasiado grande para el contexto del agente)
- Llamar a las APIs de la SCBA directamente via curl, fetch, axios u otro método HTTP
- Leer el base64 de un PDF con el Read tool (trunca líneas largas)

**Para escritos SIN adjuntos**: Usar la tool MCP `scba_guardar_borrador` directamente (el HTML es pequeño).

**Para escritos CON adjuntos**: Usar el script `upload_scba_adjuntos.py` que maneja los PDFs internamente.

Si el script o las tools MCP no están disponibles, informar al usuario que el servidor MCP no está conectado.

## Instrucciones para el agente

1. Leer `~/.env` (path absoluto: `/Users/matiaschristiangarciacliment/.env`) para obtener `MEV_USUARIO` y `MEV_PASSWORD`
2. Confirmar con el usuario: causa (número o carátula), tipo de presentación, y contenido
3. Obtener `id_org` e `id_causa` (si no los tenés, usar la **tool MCP** `mev_listar_causas`)
4. Convertir el escrito a HTML **preservando el formato exacto del original**:
   - **Word (.docx)** → Usar `mammoth` para extraer HTML con formato (negritas, subrayados, colores, tablas). **NUNCA usar `texto_a_html_scba()` para Word.**
   - **PDF** → Extraer texto preservando estructura y formato, reconstruir HTML fiel al original
   - **Texto plano** → Usar `texto_a_html_scba()` estándar
5. **Sin adjuntos**: Llamar a la tool MCP `scba_guardar_borrador` directamente
6. **Con adjuntos**: Guardar HTML en archivo temporal + ejecutar `${CLAUDE_PLUGIN_ROOT}/scripts/upload_scba_adjuntos.py`
7. Informar al usuario el resultado
8. Recordar que el borrador debe firmarse digitalmente desde notificaciones.scba.gov.ar
9. **NUNCA subir un documento con formato diferente al que el usuario aprobó**

El borrador NO se presenta automáticamente — siempre queda como borrador para firma digital manual. Esto es intencional y no se puede cambiar desde la API.
