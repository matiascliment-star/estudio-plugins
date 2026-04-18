# Reglas procesales — control de caducidad

Este archivo se inyecta en el prompt de **cada subagente** que analiza un expediente. Sumar reglas cuando Matías detecte errores recurrentes.

## Caducidad de instancia — diferencia clave CABA vs Provincia

⚠️ **CABA (Nación):** la caducidad opera **AUTOMÁTICAMENTE** a los 6 meses de inactividad (1ra instancia) / 3 meses (Cámara) sin necesidad de intimación previa. Si se pasa el plazo **se pierde la causa**. Por eso los expedientes CABA cerca de vencer son **CRÍTICOS** y la corrida debe priorizarlos.

✅ **Provincia de Buenos Aires (MEV):** la caducidad **NO opera automáticamente**. El juzgado primero **intima a la parte a activar** dentro de un plazo. Recién ante la falta de respuesta se declara la caducidad. Esto significa:
- Pcia con inactividad pero **sin intimación a activar pendiente** → NO crítico. La causa sigue viva.
- Pcia **con intimación a activar reciente en los últimos movimientos** → SÍ crítico. Plazo corriendo.

**Regla práctica para Pcia:** antes de sugerir urgencia alta, verificar en los últimos movimientos si hay `INTIMA A ACTIVAR`, `APERCIBIMIENTO CADUCIDAD`, o similar. Sin eso, bajar la urgencia a media/baja.

## CSJN

- No hay caducidad de instancia (art. 281 CPCCN). No proceden prontos despachos. Expedientes esperando sentencia → `NO REQUIERE IMPULSO`.

## Fuero penal (IPP)

- La caducidad de instancia es propia de procesos civiles/laborales. No aplica → `EXCLUIR DEL CONTROL`.

## Apelaciones laborales — efectos

- **Art. 110 LO:** apelación con **efecto diferido** hasta la sentencia. NO hay elevación inmediata a Cámara. NO sugerir "urgir elevación".
- **Art. 116 LO:** efecto suspensivo.

## Audiencias laborales

- **Audiencia art. 80 LO:** conciliación / saneamiento / apertura a prueba (etapa **preliminar**). NO es audiencia de alegatos.
- **Vista de causa:** etapa de recepción de prueba.

## Interpretación de movimientos

### SIEMPRE leer el texto completo

Cada fila de `movimientos_pjn` / `movimientos_judicial` tiene el contenido real del trámite o del escrito en el campo `texto_proveido` (Pcia/MEV) o `texto_documento` (PJN). **Nunca decidir solo con `descripcion` ni con `tipo`** — son etiquetas cortas; el contenido real está en el campo de texto.

**Limpieza del prefijo de UI (MEV):** los textos de Pcia arrancan con una cabecera de la UI del portal:

> `× Volver Informe × Resulta del proceso Aceptar × SI NO Texto del trámite Datos de la Causa …`

o

> `× Volver Informe × Resulta del proceso Aceptar × SI NO TEXTO Y DATOS DE LA NOTIFICACIÓN …`

Antes de analizar, partir el texto por la primera aparición de `"Texto del trámite"` o `"TEXTO Y DATOS DE LA NOTIFICACIÓN"` y quedarse con lo que viene después (ahí está el cuerpo real del despacho/escrito, con fechas, firmantes y contenido sustantivo).

### Tipos útiles vs ruido

- `tipo='ESCRITO AGREGADO'` (PJN) o tipos específicos en Pcia como `ESCRITO ELECTRONICO`, `IMPUGNA DICTAMEN PERICIAL`, `ALEGATO - PRESENTA`, `CONTESTA AGRAVIOS`, `MANIFESTACION - FORMULA`, `INTIMACION - SOLICITA`, etc. → escritos **de parte**. El `texto_proveido` trae el cuerpo real del escrito.
- `tipo='FIRMA DESPACHO'` (PJN) o en Pcia `DEMANDA - CONTESTADA / SE PROVEE`, `PRUEBA / SE PROVEE`, `AUTO DE APERTURA A PRUEBA`, `AGREGUESE Y TENGASE PRESENTE`, `SENTENCIA INTERLOCUTORIA`, `AUTOS PARA SENTENCIA`, etc. → providencias **del juzgado**.
- Tipos ruidosos que solo son acuses administrativos (no analizar contenido): `PRESENTACION - (RECIBIDA)`, `PRESENTACION - (PENDIENTE)`, `PRESENTACION - (DILIGENCIADA)`, `PRESENTACION - (OBSERVADA)` → son acuse del portal, no contienen el escrito real. El contenido propio aparece bajo OTRO tipo del mismo día o cercano.

### Si el texto del escrito no alcanza

Si después de leer `texto_proveido` completo sigue sin haber suficiente contexto para decidir qué acción corresponde, marcar `modelo_aplica=NINGUNO` y en `contexto` describir lo que sí se sabe + indicar "revisar escrito completo en MEV". Nunca forzar un modelo sin certeza.

## Estados internos del sistema

- `expedientes.estado` puede estar desactualizado. Siempre que el último movimiento real contradiga el estado, **priorizar los movimientos**.

## Qué escrito corresponde — método objetivo

**Paso 1 — Dos consultas a los movimientos:**
```sql
-- Último escrito nuestro agregado
SELECT MAX(fecha) AS f_escrito FROM movimientos_pjn
WHERE expediente_id = X AND tipo = 'ESCRITO AGREGADO';
-- (para Pcia usar movimientos_judicial)

-- Último proveído del tribunal
SELECT MAX(fecha) AS f_despacho FROM movimientos_pjn
WHERE expediente_id = X AND tipo = 'FIRMA DESPACHO';
```

**Paso 2 — Comparar fechas y decidir:**

### Caso A — `f_escrito > f_despacho` (nuestro último escrito es posterior al último despacho)
→ Hay escrito nuestro sin proveer → **`pronto-despacho`**.

### Caso B — `f_escrito <= f_despacho` (ya hay despacho posterior a nuestro último escrito)
→ Nuestro escrito ya fue proveído. Leer el contenido del último FIRMA DESPACHO:
- Si dice "BREVEDAD" / "téngase presente" / "autos en despacho" y el tribunal sigue sin cumplir lo sustantivo → **`reitera-pedido`**.
- Si dice "AUTOS PARA SENTENCIA" / "PASE AL ACUERDO" y ya pasó tiempo sin sentencia → **`solicita-sentencia`**.
- Si el despacho resolvió sustantivamente lo pedido → nada, el trámite avanzó.

### Caso C — No hay escritos nuestros previos
→ Si el tribunal por sí mismo llamó autos y está en mora → **`solicita-sentencia`**. Si no hay autos llamados tampoco → evaluar qué otro escrito procede.

**Regla de oro:** nunca sugerir `pronto-despacho` si `f_escrito <= f_despacho`. La comparación de fechas es binaria y objetiva.

## Encabezado, tratamiento y matrícula según fuero e instancia

Para placeholders `{{encabezado}}`, `{{tratamiento}}` y `{{matricula}}`:

| Fuero / Instancia | `{{encabezado}}` | `{{tratamiento}}` | `{{matricula}}` |
|---|---|---|---|
| CABA 1ra instancia | `Sr. Juez:` | `V.S.` | `T° 97 F° 16 C.P.A.C.F.` |
| CABA Cámara | `Excmo. Tribunal:` | `V.E.` | `T° 97 F° 16 C.P.A.C.F.` |
| Provincia 1ra instancia (TT) | `Excmo. Tribunal:` | `V.E.` | `T° 46 F° 393 C.A.S.I.` |
| Provincia Cámara / SCBA | `Excmo. Tribunal:` | `V.E.` | `T° 46 F° 393 C.A.S.I.` |

Los tribunales laborales de Provincia son colegiados (Tribunal del Trabajo), por eso "Excmo. Tribunal" y "V.E." desde primera instancia. La matrícula CABA es del CPACF (97/16), la de Provincia del CASI (46/393) — nunca mezclar.

## Cuándo NO sugerir impulso

1. Causa en CSJN esperando sentencia.
2. Causa archivada o con desistimiento homologado.
3. Causa con autos a sentencia y plazo no vencido.
4. Ejecución con el juzgado avanzando de oficio.
5. Fuero penal.
6. Pcia sin intimación a activar, aunque haya mucha inactividad.

## Criterios CRÍTICOS (bloque 🚨 destacado al tope del WA)

Un expediente va al bloque CRÍTICOS cuando se da al menos una:

1. **CABA con `dr` cercano a 0 o negativo** (caducidad inminente/operada — hay que actuar YA).
2. **Audiencia fijada con plazo corriendo o vencido.**
3. **Apercibimiento decretado sin cumplir.**
4. **Traslado corriendo sin contestar** (contraparte presentó algo).
5. **Liquidación de contraparte sin impugnar.**
6. **Intimación a activar en Pcia** (esos sí son urgentes).
7. **Audiencia 80 LO designada** (la actora debe comparecer).

Caso típico NO crítico: Pcia vieja sin intimación, CABA con dr > 30, ejecución con el juzgado trabajando solo.
