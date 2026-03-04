---
name: subir-escrito-mev
description: >
  Subir escritos y borradores al MEV/SCBA (Provincia de Buenos Aires) via
  notificaciones.scba.gov.ar. Convierte escrito a HTML y guarda como borrador
  usando scba_guardar_borrador y scba_guardar_borrador_adjuntos.
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

A diferencia del PJN (que usa PDF), la SCBA trabaja con HTML — el contenido del escrito se renderiza en CKEditor dentro del portal. Si además hay documental (PDFs adjuntos), se usa la tool con adjuntos.

## Flujo completo

### Escrito solo texto (sin adjuntos)
1. **Obtener el texto del escrito**
2. **Convertir a HTML** con formato judicial
3. **Obtener los IDs de la causa** (id_org e id_causa del MEV)
4. **Llamar a `scba_guardar_borrador`**
5. **Confirmar al usuario**

### Escrito con documental (PDFs adjuntos)
1. **Obtener el texto del escrito + archivos PDF**
2. **Convertir texto a HTML**
3. **Codificar cada PDF adjunto en base64**
4. **Llamar a `scba_guardar_borrador_adjuntos`**
5. **Confirmar al usuario**

## Credenciales

Las credenciales de la SCBA están en el archivo `.env` de la carpeta del usuario:
- `MEV_USUARIO`: email de notificaciones SCBA (ej: `20313806198@notificaciones.scba.gov.ar`)
- `MEV_PASSWORD`: contraseña de notificaciones SCBA

Leer `.env` antes de hacer cualquier operación. Si no hay credenciales, pedirlas al usuario.

## Conversión del escrito a HTML

El sistema SCBA espera HTML simple que se renderiza en CKEditor. No hace falta CSS sofisticado — solo tags HTML estándar.

### Formato HTML judicial estándar

```python
def texto_a_html_scba(texto, titulo):
    """Convierte texto del escrito a HTML para SCBA."""

    # Título/sumario arriba a la derecha
    html = f'<p style="text-align: right;"><strong>{titulo.upper()}</strong></p>\n'
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

**Opción 2**: Usar la tool `mev_listar_causas` para obtener la lista de causas y buscar la correcta:
```
Tool: mev_listar_causas
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
```
Esto devuelve causas con campos `idc` e `ido`.

**Opción 3**: Si tenés el número de causa, buscar en la lista devuelta por `mev_listar_causas` la que coincida.

### Verificar info de la causa

Antes de guardar, podés consultar info con `scba_info_causa`:
```
Tool: scba_info_causa
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
  id_org: <ido de la causa>
  id_causa: <idc de la causa>
```
Esto confirma la carátula, organismo y si se puede guardar borrador.

## Llamada a las tools MCP

### Borrador solo texto

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

### Borrador con adjuntos (PDFs)

```
Tool: scba_guardar_borrador_adjuntos
Params:
  usuario: <MEV_USUARIO>
  password: <MEV_PASSWORD>
  id_org: <id del organismo>
  id_causa: <id de la causa>
  texto_html: "<p style='text-align: right;'><strong>ACOMPAÑA DOCUMENTAL</strong></p>..."
  titulo: "ACOMPAÑA DOCUMENTAL"
  adjuntos_base64: [
    { "base64": "<contenido PDF en base64>", "nombre": "documental.pdf", "mime": "application/pdf" }
  ]
  tipo_presentacion: "1"
```

Para codificar PDFs en base64:
```python
import base64
with open("archivo.pdf", "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode()
```

## Tipos de presentación SCBA

| Código | Tipo |
|--------|------|
| 1 | Escritos (default — pronto despachos, impugnaciones, etc.) |
| 2 | Oficios |
| 3 | Cédulas |
| 4 | Mandamientos |

Si el usuario no especifica, usar "1" (Escritos) que es el más común.

## IMPORTANTE: Uso obligatorio de tools MCP

**NUNCA** intentar llamar a las APIs de la SCBA/MEV directamente via Node.js, curl, fetch, axios, o cualquier otro método HTTP directo. **SIEMPRE** usar las tools MCP provistas (`mev_listar_causas`, `scba_info_causa`, `scba_guardar_borrador`, `scba_guardar_borrador_adjuntos`). Estas tools MCP ya están disponibles en tu entorno como herramientas que podés invocar directamente — no necesitás importar módulos, instalar paquetes, ni escribir código para hacer las llamadas HTTP. Simplemente invocá la tool MCP con los parámetros indicados.

Si al intentar usar la tool MCP recibís un error de que no existe o no está disponible, **informar al usuario** que el servidor MCP del scraper judicial no está conectado y que debe verificar su configuración. **No** intentar workarounds con Node.js o cualquier otro método.

## Instrucciones para el agente

1. Leer `.env` para obtener `MEV_USUARIO` y `MEV_PASSWORD`
2. Confirmar con el usuario: causa (número o carátula), tipo de presentación, y contenido
3. Obtener `id_org` e `id_causa` (si no los tenés, usar la **tool MCP** `mev_listar_causas` para buscar la correcta)
4. Convertir el escrito a HTML
5. Si hay adjuntos, codificar cada PDF en base64
6. Llamar a la **tool MCP** `scba_guardar_borrador` (sin adjuntos) o `scba_guardar_borrador_adjuntos` (con adjuntos) — NO via Node.js, NO via curl
7. Informar al usuario el resultado
8. Recordar que el borrador debe firmarse digitalmente desde notificaciones.scba.gov.ar

El borrador NO se presenta automáticamente — siempre queda como borrador para firma digital manual. Esto es intencional y no se puede cambiar desde la API.
