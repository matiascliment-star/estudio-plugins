# Workflow: Consulta Publica SCW via Chrome

## Caso de uso

Buscar expedientes que no pertenecen al usuario logueado, especialmente:
- Expedientes de CSJN con sufijo /CA001 donde el numero no coincide en primera instancia
- Expedientes donde se necesita buscar por nombre de parte
- Descarga de documentos de actuaciones (pericias, escritos, etc.)

## Prerequisitos

- Claude in Chrome extension conectada
- Usuario logueado en SCW (para evitar captcha)

## Workflow 1: Busqueda por numero

### Paso 1: Navegar
```
navigate to https://scw.pjn.gov.ar/scw/home.seam
```

### Paso 2: Completar formulario "Por expediente"
```javascript
document.querySelector('#formPublica\\:camaraNumAni').value = '7'; // CNT
document.querySelector('#formPublica\\:numero').value = '83800';
document.querySelector('#formPublica\\:anio').value = '2016';
document.querySelector('#formPublica\\:buscarPorNumeroButton').click();
```

### Paso 3: Verificar caratula
SIEMPRE verificar que la caratula del expediente encontrado coincida con la esperada.
Si no coincide, el numero de CSJN /CA001 no mapea al expediente de primera instancia.

## Workflow 2: Busqueda por parte (demandado)

### Paso 1: Navegar y activar tab "Por parte"
```
navigate to https://scw.pjn.gov.ar/scw/home.seam
wait 2 seconds
```

### Paso 2: Activar tab RichFaces
```javascript
document.querySelector('#formPublica\\:porParte\\:header\\:inactive').click();
```
Esperar 2 segundos.

### Paso 3: Verificar que el formulario este cargado
```javascript
const ok = document.querySelector('#formPublica\\:camaraPartes') &&
           document.querySelector('#formPublica\\:tipo') &&
           document.querySelector('#formPublica\\:nomIntervParte');
```

### Paso 4: Completar con form_input (NO JavaScript directo)
Usar las herramientas `form_input` de Claude in Chrome:
1. Jurisdiccion select -> value "7" (CNT)
2. Tipo select -> value "DEMANDADO" (UNICO permitido)
3. Parte input -> nombre del demandado (minimo 6 caracteres)

**IMPORTANTE:** No usar `element.value = ...` para los selects JSF.
Usar `form_input` que dispara eventos correctamente.

### Paso 5: Buscar
Click en el boton Consultar del formulario "Por parte" (`formPublica:buscarPorParteButton`).

### Paso 6: Revisar resultados
La pagina `consultaParte.seam` muestra la lista de expedientes.
Buscar el que coincida con la caratula esperada.

## Workflow 3: Descargar documento de actuacion

### Paso 1: Filtrar por Despachos/Escritos
```javascript
// Marcar checkbox Despachos/Escritos
const cb = document.querySelector('#expediente\\:checkBoxDespachosYEscritosId');
if (cb && !cb.checked) cb.click();
// Click Aplicar
document.querySelector('input[value="Aplicar"]').click();
```

### Paso 2: Buscar la actuacion deseada
Navegar por las paginas buscando texto como "PERICIA MEDIC" o "PRESENTA PERICIA".

### Paso 3: Paginacion
Hay DOS conjuntos de paginacion en el expediente:
- **j_idt217**: seccion "Ver Todos" (sin filtro)
- **j_idt256**: seccion filtrada (Despachos/Escritos)

Usar el correcto segun el filtro activo. Hacer click en el numero de pagina.

### Paso 4: Descargar
- **Descargar PDF**: click en `expediente:action-table:{row}:j_idt162`
- **Ver en visor**: click en `expediente:action-table:{row}:j_idt168`

El PDF se descarga en una nueva pestana del navegador.

## Notas importantes

1. **Login requerido**: Sin login, la consulta publica pide captcha Securimage
2. **Solo DEMANDADO**: La busqueda por parte solo acepta DEMANDADO
3. **Minimo 6 chars**: El campo Parte requiere minimo 6 caracteres
4. **Expedientes /CA001**: Los numeros con /CA001 de CSJN no coinciden en primera instancia del SCW
5. **RichFaces tabs**: Usar `#formPublica:porParte:header:inactive` para activar el tab (no click visual)
6. **form_input obligatorio**: Los selects JSF no respetan `element.value`, usar form_input de Chrome
