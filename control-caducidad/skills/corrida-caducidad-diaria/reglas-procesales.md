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

- `tipo='ESCRITO AGREGADO'` → escrito **de parte**, NO providencia del juzgado. El título (ej. "AUTOS PARA ALEGAR") es lo que la parte pidió.
- `tipo='FIRMA DESPACHO'` → providencia del juzgado.
- Si `FIRMA DESPACHO` tiene descripción ambigua, leer `texto_documento` del PDF correspondiente antes de decidir.

## Estados internos del sistema

- `expedientes.estado` puede estar desactualizado. Siempre que el último movimiento real contradiga el estado, **priorizar los movimientos**.

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
