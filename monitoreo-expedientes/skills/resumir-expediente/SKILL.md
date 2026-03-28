---
name: resumir-expediente
description: >
  Genera un resumen inteligente (resumen_ia) de un expediente judicial y lo guarda en Supabase.
  Lee movimientos, sentencias, liquidaciones y proveidos clave del expediente, y produce un
  resumen narrativo estructurado que permite entender el estado del caso sin releer todo.
  Sirve para cualquier etapa: prueba, sentencia, ejecucion, camara, etc.
  Tambien activa monitoreo_diario=true para que el briefing diario lo incluya.
  Usar cuando el usuario pida: "resumir expediente", "hacer resumen del caso", "cargar resumen",
  "activar monitoreo", "agregar al briefing", "resumir caso", "resumen IA del expediente",
  "quiero seguir este caso", "monitorear expediente", "agregar expediente al seguimiento".
  Triggers: "resumir expediente", "resumen caso", "cargar resumen", "activar monitoreo",
  "agregar al briefing", "quiero seguir este caso", "monitorear".
version: 0.2.0
---

# Skill: Resumen IA de Expediente Judicial

Genera un resumen narrativo completo de un expediente y lo guarda en Supabase para que el briefing diario pueda usarlo sin releer todo el expediente.

## Credenciales

Leer de `~/.env`:
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV: `MEV_USUARIO` y `MEV_PASSWORD`
- Supabase: usar el MCP de Supabase con project_id `wdgdbbcwcrirpnfdmykh`

## Workflow

### Paso 1: Identificar el expediente

1. El usuario dice cual expediente quiere resumir (por nombre, numero, o criterio)
2. Buscar en Supabase:
   ```sql
   SELECT id, numero_causa, caratula, estado, jurisdiccion, juzgado, resumen_ia,
          mev_idc, mev_ido
   FROM expedientes
   WHERE caratula ILIKE '%texto%' OR numero_causa ILIKE '%texto%'
   ```
3. Si ya tiene `resumen_ia`, preguntar si quiere regenerarlo o actualizarlo

### Paso 2: Leer el expediente

Dependiendo de la jurisdiccion:

**PJN (nacional):**
- `pjn_obtener_movimientos` → lista completa de actuaciones
- `pjn_leer_documentos` con `leer_todos=true` → lee sentencias, liquidaciones, despachos
- Si hay mucho, priorizar: sentencia > liquidacion > despachos de ejecucion > escritos propios

**MEV (provincia):**
- `mev_obtener_movimientos` → lista completa
- `mev_leer_documentos` con filtros segun etapa:
  - Ejecucion: filtro "SENTENCIA", "LIQUIDACION", "DEPOSITO", "GIRO", "TRANSFERENCIA", "EMBARGO", "REGULACION"
  - Prueba: filtro "DEMANDA", "APERTURA", "PERICIA", "TESTIMONIAL", "INFORME"
  - Camara: filtro "SENTENCIA", "AUTOS", "LLAMAMIENTO", "MEMORIAL", "AGRAVIOS"

### Paso 3: Generar el resumen

El resumen debe ser NARRATIVO y ESTRUCTURADO. Adaptarlo a la etapa del caso.
PERSPECTIVA: siempre desde el punto de vista de NUESTRO ESTUDIO (somos la parte actora).
Distinguir siempre "NOSOTROS" (actor) vs "ELLOS" (demandado/a).

#### Para casos en EJECUCION (estados 70-77):
```
[CARATULA] - [NUMERO_CAUSA] - [JUZGADO]

SENTENCIA ([fecha]): [quién condena a quién, rubros, montos, tasa de interés, costas]
Demandados: [nombre de cada demandado condenado, solidariamente o no]

APELACIONES (si hubo):
  Nosotros apelamos: [qué, fecha, resultado]
  Ellos apelaron: [qué, fecha, resultado]
  Sentencia Cámara ([fecha]): [confirmó/modificó/revocó, qué cambió]

LIQUIDACIONES:
  Nuestra liquidación ([fecha]): capital $[X] + intereses $[Y] = TOTAL $[Z]
  Liquidación contraria ([fecha]): capital $[X] + intereses $[Y] = TOTAL $[Z]
  Liquidación aprobada ([fecha]): capital $[X] + intereses $[Y] = TOTAL $[Z]
  Diferencia con la nuestra: [monto y motivo si lo hay]
  Plazo para pagar: [X días desde [fecha de intimación]]
  Vencimiento del plazo: [fecha concreta]

MONTOS:
  Capital de condena: $[monto] (a valores [fecha])
  Intereses acta/mecanismo: [tasa aplicable, ej: Acta 2601, Acta 2764, tasa activa BNA]
  Honorarios regulados:
    - Dr. [nombre] (letrado actor): $[monto] / [X] UMAs — [cobrado/pendiente]
    - Dr. [nombre] (letrado demandado): $[monto] / [X] UMAs — [cobrado/pendiente]
    - [perito médico]: $[monto] / [X] UMAs — [cobrado/pendiente]
    - [perito contador]: $[monto] / [X] UMAs — [cobrado/pendiente]
    - [otros peritos/profesionales]: $[monto] — [cobrado/pendiente]
  Regulación por etapa de ejecución: [pedida/pendiente/regulada, monto si hay]
  Aportes ley 23.187 / CASSABA: [si corresponde, monto]
  Tasa de justicia: [pagada/pendiente, monto si se sabe]
  TOTAL ESTIMADO EN JUEGO: $[suma de todo lo que hay que cobrar/pagar]

COBROS Y PAGOS (con fechas exactas para control de intereses):
  - [fecha depósito]: [quién depositó] $[monto] en concepto de [capital/honorarios/intereses]
  - [fecha intimación al pago]: se intimó por [X] días
  - [fecha vencimiento plazo]: venció el plazo
  - [fecha embargo]: se trabó embargo sobre [qué]
  - [fecha pedido de giro]: pedimos giro/transferencia
  - [fecha giro ordenado]: se ordenó giro
  - [fecha transferencia efectiva]: se transfirió $[monto] a [destinatario]
  Días entre vencimiento e/ plazo y depósito: [X] días → [hay/no hay lugar a intereses moratorios]
  Total cobrado: $[X] de $[Y] ([porcentaje]%)

PENDIENTE:
  - [qué falta cobrar: capital restante, honorarios de quién, intereses complementarios]
  - [gestiones pendientes: intimar, embargar, pedir giro, pedir regulación ejecución, etc.]
  Saldo pendiente estimado: $[monto]

ULTIMO MOVIMIENTO: [fecha] - [descripcion]
```

IMPORTANTE para ejecución:
- Si la liquidación tiene desglose de rubros (indemnización, vacaciones, SAC, art. 2, etc.), listar cada rubro con su monto.
- Si hay más de un demandado, indicar quién pagó qué y quién debe.
- Si hay honorarios regulados en UMAs, poner tanto el monto en pesos como las UMAs.
- Si hay intereses complementarios (por diferencia de tasas, periodo posterior a liquidación), incluirlos.
- El "TOTAL ESTIMADO EN JUEGO" es la suma de todo: capital + intereses + honorarios propios + costas.
- SIEMPRE anotar NUESTRA liquidación vs la del OTRO. No confundirlas.
- SIEMPRE anotar fechas de depósitos, intimaciones y vencimientos para evaluar intereses moratorios.

#### Para casos en PRUEBA (estados 10-23):
```
[CARATULA] - [NUMERO_CAUSA] - [JUZGADO]

DEMANDA ([fecha presentación]):
  Rubros reclamados: [listar rubros y montos si los hay]
  Hechos clave: [resumen breve del reclamo]

CONTESTACION ([fecha]): [si contestaron, excepciones opuestas, posición sobre los hechos]

APERTURA A PRUEBA ([fecha]):

PRUEBA OFRECIDA POR NOSOTROS:
  - Pericia médica: [ofrecida/ordenada/producida/pendiente]
  - Pericia contable: [ofrecida/ordenada/producida/pendiente]
  - Pericia psicológica: [ofrecida/ordenada/producida/pendiente]
  - Testimonial: [ofrecida/ordenada/producida/pendiente] — testigos: [nombres si se sabe]
  - Informativa: [a quién, ofrecida/ordenada/contestada/pendiente]
  - Documental: [agregada/reconocida/pendiente de reconocimiento]
  - [otras pruebas ofrecidas]

PRUEBA OFRECIDA POR ELLOS:
  - [listar lo relevante que hayan ofrecido]

PRUEBA PRODUCIDA (resumen de resultados):
  - Pericia médica ([fecha], perito [nombre]): [conclusión principal, % incapacidad]
  - Pericia contable ([fecha]): [conclusión principal]
  - Testimonial ([fecha], testigo [nombre]): [qué declaró relevante]
  - [otras]

PRUEBA PENDIENTE DE PRODUCIR:
  - [listar cada prueba que falta y su estado: perito sorteado/intimado/pendiente aceptación, etc.]

PROXIMO PASO: [qué hay que impulsar]
ULTIMO MOVIMIENTO: [fecha] - [descripcion]
```

IMPORTANTE para prueba:
- Leer la demanda para saber qué rubros se reclamaron y qué prueba se ofreció.
- Leer la apertura a prueba para saber qué prueba fue ordenada (no toda la ofrecida se ordena).
- Distinguir entre ofrecida, ordenada, producida y pendiente.
- Si hay pericia presentada, anotar la conclusión principal (% de incapacidad, monto, etc.).

#### Para casos en CAMARA/CSJN (estados 50-64):
```
[CARATULA] - [NUMERO_CAUSA] - [SALA/CAMARA]

SENTENCIA 1RA INSTANCIA ([fecha]): [resultado, rubros, montos, tasa, costas]
  Capital de condena: $[monto] (a valores [fecha])
  Honorarios 1ra instancia: [letrado actor $X, peritos $Y, etc.]

APELACIONES:
  Nosotros apelamos: [qué puntos, fecha del memorial]
  Ellos apelaron: [qué puntos, fecha del memorial]
  Contestación de agravios: [nuestra fecha, la de ellos]

ESTADO EN CAMARA: [si hay llamamiento de autos, dictamen fiscal, si hay sentencia]

SENTENCIA CAMARA ([fecha]): [si hay: confirmó/revocó/modificó, qué puntos, nuevos montos]
  Honorarios 2da instancia: [si fueron regulados]
  Costas de alzada: [a quién]

ESTIMACION MONTO TOTAL: $[estimación de lo que vale el caso si se confirma]
ULTIMO MOVIMIENTO: [fecha] - [descripcion]
```

#### Para cualquier otra etapa:
```
[CARATULA] - [NUMERO_CAUSA] - [JUZGADO]

ESTADO ACTUAL: [descripcion del estado procesal]
RESUMEN: [qué pasó en el caso hasta ahora, lo relevante]
PROXIMO PASO: [qué hay que hacer]
ULTIMO MOVIMIENTO: [fecha] - [descripcion]
```

### Paso 4: Guardar en Supabase

```sql
UPDATE expedientes SET
  resumen_ia = '[el resumen generado]',
  monitoreo_diario = true,
  ultima_revision_auto = now()
WHERE id = [expediente_id];
```

### Paso 5: Confirmar al usuario

Mostrar el resumen generado y confirmar que se guardó. Preguntar si quiere ajustar algo.

## Reglas importantes

- El resumen debe ser CONCISO pero COMPLETO. Entre 300-800 palabras segun complejidad.
- Usar FECHAS CONCRETAS, no relativas ("15/03/2024", no "hace un año").
- Incluir MONTOS exactos cuando los hay.
- Incluir NOMBRES de peritos, letrados contrarios, ART/aseguradoras.
- SIEMPRE distinguir NOSOTROS (actor) vs ELLOS (demandado). Nuestra liquidación vs la de ellos. Nuestras apelaciones vs las de ellos.
- No inventar datos. Si no pudiste leer un documento, indicarlo: "[No se pudo leer la sentencia]"
- Si el expediente tiene muchos movimientos, priorizar los ultimos 2 años.
- El resumen se lee como si fuera la "ficha mental" que un abogado tiene del caso.
- Las fechas de depósitos, intimaciones y pagos son CRITICAS para evaluar intereses moratorios.

## Ejemplo de uso

Usuario: "resumir el caso Jimenez"
1. Busco en Supabase → encuentro CNT 7758/2020
2. Leo movimientos y documentos via MCP
3. Genero resumen estructurado
4. Guardo en Supabase con monitoreo_diario=true
5. Muestro al usuario para validar
