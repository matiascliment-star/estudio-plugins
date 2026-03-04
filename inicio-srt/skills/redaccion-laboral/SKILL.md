---
name: redaccion-laboral
description: >
  Skill para redacción de demandas laborales por accidentes de trabajo. Usar cuando el usuario
  pida "generar relato", "redactar demanda", "hacer el relato del accidente", "manifiesta lesiones",
  "armar la demanda", "relato y lesiones", o cualquier tarea relacionada con la redacción de escritos
  para demandas por accidentes laborales o enfermedades profesionales en Argentina.
version: 0.1.0
---

# Redacción de Demandas Laborales - Accidentes de Trabajo

Skill especializado en generar los escritos legales para demandas laborales argentinas a partir de la ficha del cliente.

## Flujo de trabajo

1. **Leer la ficha del cliente** — puede venir como archivo .docx subido o como texto pegado en el chat
2. **Generar el relato "EL ACCIDENTE"** — siguiendo las reglas de `references/system-prompt-relato.md`
3. **Generar el "MANIFIESTA LESIONES"** — listado numerado de lesiones basado en las zonas lesionadas de la ficha
4. **Crear un PDF** con ambos textos + el "Hago saber" boilerplate + la firma del letrado
5. **Rellenar el Anexo I** de la SRT con los datos del cliente, siguiendo `references/anexo-i-campos.md`

## Estructura de la ficha del cliente

La ficha contiene estos datos (pueden variar en formato):

- **Nombre del trabajador**
- **Fecha del accidente**
- **Hora del accidente**
- **Tipo de accidente** (Laboral / In Itinere)
- **Jornada laboral** (horario y días)
- **Tareas** (puesto de trabajo)
- **Donde se atendió** (ART, hospital, etc.)
- **Diagnóstico**
- **Datos aportados por el trabajador** (relato crudo de la llamada telefónica)
- **Zonas principalmente lesionadas** (listado numerado)
- **Zonas secundariamente lesionadas** (opcional)

## Generación del relato

Leer las instrucciones completas en `references/system-prompt-relato.md`. Puntos clave:

- Usar vocabulario jurídico obligatorio ("mi instituyente", "cimbronazo", "entorsis", "tumefacción", etc.)
- Cada lesión del MANIFIESTA debe tener su mecanismo causal en el relato
- Las articulaciones se tuercen y traumatizan, nunca "se golpean" simplemente
- Seguir la estructura: APERTURA → DESARROLLO → CIERRE

## Generación del Manifiesta Lesiones

Formato del encabezado: `MANIFIESTA LESIONES – RECLAMA DAÑO FÍSICO Y PSÍQUICO.`

Reglas:
- Numerar cada lesión con `1.-`, `2.-`, etc.
- Transformar las zonas lesionadas de la ficha en terminología médico-legal
- Incluir siempre como últimos ítems (si corresponde):
  - Limitación funcional en las zonas afectadas
  - Daño psíquico
  - Cláusula de reserva: "Asimismo existe la posibilidad de nuevas patologías que puedan presentarse con el correr del tiempo y otras que puedan surgir de la prueba y de la peritación médica a efectuar en autos."

### Transformación de zonas lesionadas a terminología legal

| Zona de la ficha | Lesión en el Manifiesta |
|---|---|
| Rodilla | Traumatismo y esguince de rodilla [lado] |
| Hombro | Traumatismo y esguince de hombro [lado] |
| Tobillo | Traumatismo y esguince de tobillo [lado] |
| Muñeca | Traumatismo y esguince de muñeca [lado] |
| Mano / Dedos | Traumatismo de mano [lado] / Traumatismo de dedos [especificar] |
| Columna cervical | Traumatismo de columna cervical |
| Columna lumbar | Traumatismo de columna lumbosacra |
| Codo | Traumatismo y esguince de codo [lado] |
| Cadera | Traumatismo y esguince de cadera [lado] |
| Cabeza | Traumatismo de cráneo (TEC) |
| Ingle / hernia | Hernia inguinal [lado] |

## Formato del PDF de salida

El PDF tiene dos secciones:

### Página 1: Relato + Hago Saber
```
[NOMBRE DEL TRABAJADOR EN MAYÚSCULAS]

EL ACCIDENTE:

[Texto del relato generado]

Hago saber:

[Texto boilerplate — ver references/hago-saber-boilerplate.md]
```

### Página 2: Manifiesta Lesiones + Firma
```
MANIFIESTA LESIONES – RECLAMA DAÑO FÍSICO Y PSÍQUICO.

1.- [Lesión 1]
2.- [Lesión 2]
...

[Firma del letrado — ver references/firma-letrado.md]
```

## Generación del PDF

Usar Python con la librería `reportlab` para crear el PDF. Instalar con `pip install reportlab --break-system-packages`.

La firma se incluye como texto formateado al pie del manifiesta.

## Relleno del Anexo I

Leer `references/anexo-i-campos.md` para el mapeo completo de campos. Usar PyPDF2 para rellenar el formulario PDF.

## Referencias

- `references/system-prompt-relato.md` — Prompt completo con reglas de redacción, vocabulario, ejemplos
- `references/hago-saber-boilerplate.md` — Texto fijo del "Hago saber"
- `references/firma-letrado.md` — Datos de la firma del letrado
- `references/anexo-i-campos.md` — Mapeo de campos del Anexo I
- `references/manifiesta-ejemplos.md` — Ejemplos de manifiesta lesiones
