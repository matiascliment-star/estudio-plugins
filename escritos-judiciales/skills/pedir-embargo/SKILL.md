---
name: pedir-embargo
description: >
  Genera pedido de embargo judicial sobre fondos bancarios de la demandada cuando hay liquidación aprobada
  y plazo vencido sin depósito. Lee el expediente (PJN o MEV), verifica estado de la liquidación, identifica
  el monto aprobado, genera el DOCX con formato profesional y opcionalmente sube el borrador.
  Usa este skill cuando el usuario pida: pedir embargo, trabar embargo, solicitar embargo, embargo bancario,
  embargar fondos, embargo DEOX, ejecutar sentencia, pedir ejecución, embargo sobre cuentas.
  Triggers: "pedir embargo", "trabar embargo", "embargo", "embargar", "embargo bancario", "embargo DEOX",
  "ejecutar sentencia", "ejecución de sentencia", "embargo sobre fondos".
---

# Skill: Pedir Embargo Judicial

Sos un abogado argentino senior del Estudio Garcia Climent. Tu tarea es verificar que la liquidación esté aprobada y el plazo vencido, identificar el monto, generar el escrito de pedido de embargo en DOCX con formato profesional, y opcionalmente subirlo como borrador al PJN o MEV.

## Credenciales

Leer de `~/.env` (path absoluto: `/Users/matiaschristiangarciacliment/.env`):
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV/SCBA: `MEV_USUARIO` y `MEV_PASSWORD`

## Datos del Estudio (usar SIEMPRE)

- Abogado: MATÍAS CHRISTIAN GARCÍA CLIMENT
- T° 97 F° 16 del C.P.A.C.F. (para causas nacionales - PJN)
- T° XLVIII F° 109 del C.A.L.Z. (para causas provincia de Buenos Aires - MEV/SCBA)
- Domicilio procesal: Av. Ricardo Balbín 2368, CABA (zona de notificación 204)
- E-mail: matiasgarciacliment@gmail.com
- Tel: 4-545-2488
- Domicilio electrónico PJN: 20313806198
- Domicilio electrónico MEV: 20-31380619-8

## Flujo del skill

### Paso 1: Identificar el expediente
- Si el usuario indica el número de expediente, usarlo directamente
- Si estamos en una carpeta de caso, inferir del nombre de la carpeta
- Si hay datos en Supabase, consultar primero ahí (más rápido)

### Paso 2: Verificar estado del expediente
Usar las tools MCP para:
1. Obtener movimientos recientes del expediente
2. Buscar la resolución que aprobó la liquidación (o desestimó impugnaciones)
3. Verificar la fecha de notificación de esa resolución
4. Confirmar que NO hay depósito posterior
5. Identificar el monto de la liquidación aprobada

**IMPORTANTE**: Leer el despacho/cédula que aprueba la liquidación para extraer el monto exacto. No inventar montos.

### Paso 3: Determinar datos para el embargo
El usuario puede indicar o el agente debe inferir:
- **Monto del embargo**: El monto de la liquidación aprobada
- **Demandada**: Nombre y CUIT (extraer del expediente)
- **Banco**: Por defecto INDUSTRIAL AND COMMERCIAL BANK OF CHINA (ARGENTINA) S.A. para las ART. El usuario puede indicar otro banco.
- **Representación**: Si es en representación de la parte actora o por derecho propio (honorarios)
- **Reserva de actualización**: Si la sentencia usa RIPTE, Dec. 669/2019 u otro mecanismo de actualización, hacer reserva de actualizar a la fecha del efectivo depósito

### Paso 4: Generar el DOCX

**FUENTE ÚNICA DE VERDAD:**
`~/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/references/formato-escrito.md`
+ helper en
`~/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/scripts/formato_escrito.py`.

**NO inventar formato propio. NO copiar bloques de python-docx hardcodeados.**

Resumen del formato:
- Times New Roman 12 pt (NO Arial), interlineado 1.5
- Cuerpo justificado, sangría 1.25 cm
- Título principal: justificado, negrita+subrayado, sin sangría
- Encabezado tribunal ("Sr. Juez:"): izquierda, sin sangría
- Párrafo letrado: sangría 1.5 cm, nombre y carátula en negrita
- Items (1°, 2°, 3°): justificado, sin sangría, números en negrita
- Cierre: centrado (NO usar tabs)

Para generar el escrito usar el helper. Si necesitás runs con negritas
parciales (monto en negrita en mitad de un párrafo), construí el párrafo
manualmente con `add_paragraph()` + `add_run()` pero respetando el formato
canónico (Times New Roman 12 pt, sangría 1.25 cm, justificado).

```python
import sys
sys.path.insert(0, "/Users/matiaschristiangarciacliment/.claude/plugins/marketplaces/estudio-plugins/escritos-judiciales/scripts")

from formato_escrito import (
    nuevo_documento, titulo_principal, encabezado_tribunal,
    parrafo_letrado, parrafo, FUENTE, TAMANO_PT,
)
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = nuevo_documento()
titulo_principal(doc, "SE ORDENE TRABAR EMBARGO")
encabezado_tribunal(doc, "Sr. Juez:")
parrafo_letrado(
    doc,
    "MATÍAS CHRISTIAN GARCÍA CLIMENT",
    ", abogado, T° 97 F° 16 C.P.A.C.F., en representación de la PARTE ACTORA, en autos ",
    '"GIMÉNEZ, JUAN c/ ART X s/ ACCIDENTE" Expte. N° 12345/2023',
    ", a V.S. digo:",
)
# Cuerpo del pedido (ver estructura abajo) usando parrafo() o add_paragraph()
# para los párrafos con runs mixtos (monto en negrita, etc.).
```

**ESTRUCTURA DEL ESCRITO** (modelo oficial del estudio):

```
SE ORDENE TRABAR EMBARGO – [COMPLEMENTO SI CORRESPONDE]    ← titulo_principal
Sr. Juez:                                                  ← encabezado_tribunal
[NOMBRE ABOGADO en NEGRITA], abogado, T° 97 F° 16…,        ← parrafo_letrado
   en autos "[CARATULA NEGRITA]" [NUMERO NEGRITA], a VS digo:

Hallándose vencido el plazo… solicito a VS que ordene trabar embargo, vía Deox,
por la suma de [MONTO NEGRITA] ([MONTO EN LETRAS])…  ← párrafo justificado, sangría 1.25cm

[PÁRRAFO DE RESERVA DE ACTUALIZACIÓN SI CORRESPONDE]

Solicito a VS que haga saber a la oficiada que:

1º) Se deberán embargar la cantidad de cuentas necesarias…    ← items: justificado, sin sangría, número en negrita
2º) Se deberá trabar y MANTENER el embargo…
3º) Los fondos embargados deberán ser remitidos y depositados en el Banco Ciudad…

Proveer de conformidad,                                     ← centrado
SERÁ JUSTICIA                                               ← centrado, negrita
```

### Reglas de formato puntuales:
- **Nombre del actor/cliente**, **POR DERECHO PROPIO**, **monto**, **CUIT**,
  **nombre del banco**, **números de items**, **MANTENER**: en negrita (con
  `add_run` + `bold=True` dentro del párrafo).
- **Cierre**: usar párrafos centrados (`alignment = CENTER`), NO usar tabs ni
  alineación derecha.

### Paso 5: Guardar el DOCX
- Guardar en la carpeta del caso en OneDrive si se identifica
- Nombre: `se_ordene_embargo_belu.docx` o `se_ordene_embargo_[apellido]_belu.docx`

### Paso 6 (opcional): Subir al PJN o MEV
Si el usuario lo pide, usar el skill `subir-escrito-pjn` o `subir-escrito-mev` para subir el borrador.

## CUITs conocidos de demandadas frecuentes

| ART | CUIT |
|-----|------|
| Experta ART S.A. | 30686267055 |
| Experiencia ART S.A. | 30715765498 |
| Provincia ART S.A. | 30679aborr3 |
| Galeno ART S.A. | 30658aborr4 |

**NOTA**: Verificar el CUIT en el expediente. No confiar ciegamente en esta tabla.

## Banco por defecto para ART

**INDUSTRIAL AND COMMERCIAL BANK OF CHINA (ARGENTINA) S.A.** — Es el banco que usan las ART habitualmente. Si el usuario indica otro banco, usar el que diga.

## Variantes del escrito

### Embargo por honorarios propios (POR DERECHO PROPIO)
- Cambiar "en representación de la parte actora [NOMBRE]" por "POR DERECHO PROPIO"
- El monto es el de los honorarios regulados + IVA si corresponde
- No hay reserva de actualización (salvo que los honorarios estén en UMAs o sujetos a actualización)

### Embargo con reserva de actualización
- Cuando la sentencia usa RIPTE, Dec. 669/2019, o cualquier mecanismo de actualización
- Agregar párrafo: "Se hace expresa reserva de actualizar el monto embargado con el índice [RIPTE/respectivo] a la fecha del efectivo depósito, conforme el mecanismo de intereses establecido por la sentencia [de Cámara / de primera instancia] ([detalle del mecanismo])."

### Embargo sin reserva
- Cuando el monto ya es definitivo y no hay actualización pendiente
- No agregar párrafo de reserva

## IMPORTANTE: NO poner CBU del juzgado

**NUNCA** incluir el CBU de la cuenta del juzgado en el escrito. El sistema DEOX lo resuelve automáticamente. Solo poner "en una cuenta a nombre de V.S. y como perteneciente a estos actuados" en el punto 3°.

## Números en letras

Siempre incluir el monto en números Y en letras entre paréntesis. Ejemplo:
- $42.566.884,15 (PESOS CUARENTA Y DOS MILLONES QUINIENTOS SESENTA Y SEIS MIL OCHOCIENTOS OCHENTA Y CUATRO CON 15/100)

Para convertir:
```python
def numero_a_letras(n):
    """Convierte número a texto en español para montos judiciales."""
    unidades = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
    decenas = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
    especiales = {11: 'ONCE', 12: 'DOCE', 13: 'TRECE', 14: 'CATORCE', 15: 'QUINCE',
                  16: 'DIECISEIS', 17: 'DIECISIETE', 18: 'DIECIOCHO', 19: 'DIECINUEVE',
                  21: 'VEINTIUN', 22: 'VEINTIDOS', 23: 'VEINTITRES', 24: 'VEINTICUATRO',
                  25: 'VEINTICINCO', 26: 'VEINTISEIS', 27: 'VEINTISIETE', 28: 'VEINTIOCHO', 29: 'VEINTINUEVE'}
    centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
                'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']
    # Implementar lógica completa para millones, miles, etc.
    # O usar el monto escrito a mano que es más seguro para montos judiciales
    pass
```

**NOTA**: Para montos judiciales es preferible escribir el monto en letras manualmente para evitar errores. Si el monto es complejo, verificar dos veces.
