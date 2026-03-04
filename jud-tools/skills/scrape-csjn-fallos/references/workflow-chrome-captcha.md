# Workflow: Busqueda CSJN sentencias.html con captcha via Chrome

## Prerequisitos

- Claude in Chrome extension conectada
- Tab abierto en el navegador

## Paso 1: Navegar al formulario

Abrir `https://www.csjn.gov.ar/tribunales-federales-nacionales/sentencias.html` en Chrome.

## Paso 2: Completar el formulario

Usar JavaScript en Chrome para completar los campos:

```javascript
// Seleccionar tribunal (ejemplo: Camara del Trabajo = C_7)
document.querySelector('#camara_id').value = 'C_7';

// Setear palabra clave
document.querySelector('#firmantes').value = 'Guillermo Vera';

// Setear fechas - IMPORTANTE: usar nativeInputValueSetter para que React/jQuery detecte el cambio
const setNativeValue = (el, val) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
};

setNativeValue(document.querySelector('#fecha_fallo_desde'), '01/01/2025');
setNativeValue(document.querySelector('#fecha_fallo_hasta'), '31/12/2025');
```

**Nota sobre fechas:** A veces el campo de fecha no se actualiza correctamente via JavaScript. Si las fechas no persisten al enviar el formulario, usar triple-click + type directamente en el campo via Claude in Chrome computer tool.

## Paso 3: Captcha

El captcha es Securimage. La imagen esta en:
```
https://www.csjn.gov.ar/tribunales-federales-nacionales/scp/captcha/securimage_show.php
```

**No se puede resolver programaticamente.** Pedir al usuario que:
1. Mire la imagen captcha en el navegador
2. Escriba el codigo en el chat

Luego setear el valor:
```javascript
document.querySelector('#captcha_code').value = 'CODIGO_DEL_USUARIO';
```

**Importante:** El captcha expira rapido. Setear el captcha e inmediatamente enviar el formulario.

## Paso 4: Enviar formulario

```javascript
document.querySelector('#form_search_sentencias').submit();
// O alternativamente:
buscar(); // funcion global del sitio
```

Si el formulario necesita el campo `acc`:
```javascript
if (!document.querySelector('input[name="acc"]')) {
  const h = document.createElement('input');
  h.type = 'hidden'; h.name = 'acc'; h.value = 'searchFallos';
  document.querySelector('#form_search_sentencias').appendChild(h);
}
```

## Paso 5: Extraer UUIDs de PDFs

Una vez que aparecen los resultados, extraer los UUIDs:

```javascript
// Extraer UUIDs de la pagina actual
const links = document.querySelectorAll('a[href*="sentencia-SGU"]');
const uuids = [...links].map(a => {
  const m = a.href.match(/sentencia-SGU-([a-f0-9-]+)\.pdf/);
  return m ? m[1] : null;
}).filter(Boolean);
JSON.stringify(uuids);
```

## Paso 6: Paginar

Si hay mas de 20 resultados, hay paginacion:

```javascript
// Ver total de paginas
document.querySelector('.pagination') // inspeccionar
// Ir a pagina 2 (indice 1)
irPaginaF(1);
// Ir a pagina 3 (indice 2)
irPaginaF(2);
```

**Importante:** Despues de cada `irPaginaF()`, la pagina se recarga. Hay que volver a extraer los UUIDs en cada pagina.

## Paso 7: Construir URLs de PDFs

Con los UUIDs, armar las URLs:
```
https://www.csjn.gov.ar/tribunales-federales-nacionales/d/sentencia-SGU-{uuid}.pdf
```

## Paso 8: Analizar PDFs

Usar la tool `csjn_analizar_pdfs` pasando:
- `pdf_urls`: Array con todas las URLs construidas
- `termino`: El termino a buscar (ej: "Guillermo Vera")

La tool descarga cada PDF, extrae texto, busca el termino, y devuelve:
- Cuantos PDFs contienen el termino
- Contexto alrededor de cada match
- Si el termino aparece como "perito" (deteccion automatica)

## Valores conocidos de camara_id

| ID | Tribunal |
|----|----------|
| `C_7` | Cam. Nac. Apel. del Trabajo |
| `C_1` | Cam. Nac. Apel. en lo Civil |
| `C_2` | Cam. Nac. Apel. en lo Comercial |
| `C_3` | Cam. Nac. Apel. en lo Criminal y Correccional |
| `C_5` | Cam. Nac. Apel. en lo Contencioso Administrativo Federal |

Para obtener la lista completa, usar `csjn_listar_tribunales`.

## Troubleshooting

- **ERR_EMPTY_RESPONSE:** El sitio CSJN a veces crashea. Recargar la pagina y volver a intentar.
- **Fechas no persisten:** Usar triple-click + type en lugar de JavaScript para setear fechas.
- **Captcha expirado:** El captcha tiene vida corta. Pedir nuevo captcha justo antes de enviar.
- **Variables JS perdidas entre paginas:** `irPaginaF()` recarga la pagina, las variables se pierden. Extraer datos antes de paginar.
