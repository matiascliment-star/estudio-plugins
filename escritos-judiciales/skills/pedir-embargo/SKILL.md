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

**FORMATO OBLIGATORIO** (replicar exactamente):
- Fuente: Arial 12pt
- Interlineado: 1.5
- Espaciado después de párrafo: ~5pt (Emu 63500)
- Alineación: Justificado en TODO el documento
- Márgenes: Superior 2cm, Inferior 2cm, Izquierdo 3cm, Derecho 2cm

**ESTRUCTURA DEL ESCRITO** (modelo oficial del estudio):

```
[Título en NEGRITA + SUBRAYADO, justificado]
SE ORDENE TRABAR EMBARGO – [COMPLEMENTO SI CORRESPONDE]

Sr. Juez:

[NOMBRE ABOGADO en NEGRITA], abogado, T° 97 F° 16 C.P.A.C.F, [en representación de / POR DERECHO PROPIO], manteniendo el domicilio procesal en la Av. Ricardo Balbín 2368, CABA (zona de notificación 204, e-mail: matiasgarciacliment@gmail.com, tel: 4-545-2488) y domicilio electrónico en 20313806198, en los autos caratulados: "[CARATULA en NEGRITA]" [NUMERO en NEGRITA], a VS digo:

Hallándose vencido el plazo [de fecha XX/XX/XXXX o "previsto en la sentencia de autos"] sin que obre en el sistema Lex 100 depósito alguno [—CONTEXTO ADICIONAL SI CORRESPONDE—], solicito a VS que ordene trabar embargo, vía Deox, por la suma de [MONTO en NEGRITA] ([MONTO EN LETRAS]), más lo que VS presupueste para responder a intereses y costas de la ejecución, sobre los fondos que [DEMANDADA Y CUIT en NEGRITA], posea al momento de la traba del presente o adquiera en el futuro en el [BANCO en NEGRITA], en cualquier cuenta corriente y/o caja de ahorros, fondo de inversión, plazo fijo u otra cuenta.

[PÁRRAFO DE RESERVA DE ACTUALIZACIÓN SI CORRESPONDE]

Solicito a VS que haga saber a la oficiada que:

[1º) en NEGRITA] Se deberán embargar la cantidad de cuentas necesarias para hacer efectiva la medida

[2º) en NEGRITA] Se deberá trabar y [MANTENER en NEGRITA] el embargo hasta el momento en que se retengan el 100% de los fondos

[3º) en NEGRITA] Los fondos embargados, deberán ser remitidos y depositados en el Banco Ciudad, dentro de los 5 días de su indisponibilidad, en una cuenta a nombre de V.S. y como perteneciente a estos actuados

[7 TABS] Proveer de conformidad,
[6 TABS + espacios] SERÁ JUSTICIA [en NEGRITA]
```

### Reglas de formato detalladas:
- **Título**: negrita + subrayado (underline=True)
- **Nombre del abogado**: negrita
- **Nombre del actor/cliente**: negrita (si es en representación)
- **"POR DERECHO PROPIO"**: negrita (si es por honorarios propios)
- **Carátula y número de expediente**: negrita
- **Monto**: negrita
- **Nombre y CUIT de la demandada**: negrita
- **Nombre del banco**: negrita
- **Números de items (1º, 2º, 3º)**: negrita
- **"MANTENER"**: negrita
- **"SERÁ JUSTICIA"**: negrita
- **Cierre**: con tabs (7 tabs para "Proveer de conformidad", 6 tabs + espacios para "SERÁ JUSTICIA"), NO usar alineación derecha — usar tabs como en el modelo

### Código Python para generar el DOCX:

```python
from docx import Document
from docx.shared import Pt, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2)

style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(12)

def add_run(p, text, bold=None, underline=None):
    r = p.add_run(text)
    r.font.name = 'Arial'
    if bold: r.bold = True
    if underline: r.underline = True
    return r

def make_para(alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, ls=1.5, sa=Emu(63500)):
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.line_spacing = ls
    p.paragraph_format.space_after = sa
    return p
```

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
