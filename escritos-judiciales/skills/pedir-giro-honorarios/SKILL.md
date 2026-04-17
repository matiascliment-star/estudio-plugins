---
name: pedir-giro-honorarios
description: Genera escrito de pedido de giro electrónico (libramiento) de honorarios profesionales en causas de PJN (Justicia Nacional, CABA). Usar cuando el usuario pida "pedir giro", "pedir giro de honorarios", "libramiento de giro", "girar honorarios", "cobrar honorarios", "transferir honorarios", "giro electrónico", "pedir transferencia de honorarios", "pedir cobro", o cualquier pedido de libramiento de giro electrónico sobre fondos depositados en la cuenta de autos. También cuando haya que trabar embargo sobre fondos depositados por la demandada y pedir su transferencia a la cuenta del suscripto. Triggers: "pedir giro", "pedir giro honorarios", "libramiento", "girar honorarios", "giro electrónico", "transferir honorarios", "cobrar honorarios", "embargo y giro", "trabar embargo sobre fondos".
---

# Skill: Pedir Giro de Honorarios

Genera un escrito DOCX para pedir el libramiento de giro electrónico de honorarios profesionales ya depositados por la demandada en la cuenta de autos (causas PJN - Justicia Nacional / CABA). Sigue fielmente el modelo del estudio (ver `references/modelo-giro.md`), aplica el formato estándar de escritos (ver memoria `feedback_formato_escritos.md`) y adjunta las constancias del suscripto (AFIP y CBU) embebidas al final del escrito.

## Cuándo usar

- Hay fondos depositados en la cuenta de autos en concepto de honorarios profesionales del suscripto.
- Esos fondos están en embargo o en pago (indistinto), pero el juzgado todavía no giró al letrado.
- En causas PJN/CABA es OBLIGATORIO adjuntar la constancia de AFIP/ARCA y la constancia de CBU.
- Si además hay que trabar embargo sobre fondos que la demandada "dio en embargo" (no en pago), el escrito combina ambas cosas: "TRABA EMBARGO + SE LIBRE GIRO".

## Variantes

### A) Giro simple (fondos ya en pago)
Título: `SE LIBRE GIRO ELECTRÓNICO EN CONCEPTO DE HONORARIOS. ADJUNTA DOCUMENTACIÓN. DECLARA BAJO JURAMENTO. HACE RESERVA.-`

### B) Traba embargo + giro (fondos depositados en embargo por queja/recurso pendiente)
Título: `TRABA EMBARGO SOBRE FONDOS DEPOSITADOS. SE LIBRE GIRO ELECTRÓNICO EN CONCEPTO DE HONORARIOS. ADJUNTA DOCUMENTACIÓN. DECLARA BAJO JURAMENTO. HACE RESERVA.-`

El punto I.- en este caso dice primero "TRABE EMBARGO sobre las sumas depositadas a favor del suscripto" y en un segundo inciso "ORDENE TRANSFERIR" al CBU del letrado.

## Datos fijos del suscripto (García Climent)

- **Nombre:** MATÍAS CHRISTIAN GARCÍA CLIMENT
- **Matrícula:** T° 97 F° 16 CPACF
- **CUIT:** 20-31380619-8
- **DNI:** 31.380.619
- **Domicilio procesal:** Av. Ricardo Balbín 2368, CABA
- **Zona notificación:** 204
- **Email:** matiasgarciacliment@gmail.com
- **Tel:** 4-545-2488
- **Domicilio electrónico:** 2031306198
- **Banco:** Banco de la Ciudad de Buenos Aires
- **Caja de Ahorro $:** 000000260200356738
- **CBU:** 0290026110000003567389
- **Alias:** ROMERO.POROTO.CAMA

## Datos variables por caso

1. **Expediente**: carátula, número (ej: "CNT 033256/2022"), juzgado.
2. **Monto a girar**: capital (honorarios) + IVA (21%).
3. **Fechas de los depósitos** (ver movimientos PJN).
4. **Variante** (A o B): si los fondos están en pago o en embargo (por queja pendiente u otro motivo).

## Flujo

1. **Confirmar expediente** en Supabase (usar skill `scrape-pjn-supabase`) — tabla `expedientes`, buscar por número.
2. **Leer últimos movimientos PJN** (columna `texto_documento` en `movimientos_pjn`) para identificar:
   - Fechas y montos de los depósitos de la demandada.
   - Si se depositó "en pago" o "en embargo".
   - Si hay queja en CSJN o recurso pendiente (→ variante B).
3. **Calcular monto a girar**: suma de depósitos en concepto de honorarios del letrado + IVA.
4. **Generar DOCX** con el template `templates/generar_giro.py` (copiar a `/tmp/` y adaptar datos).
5. **Embebir constancias** desde `assets/constancia_afip.png` y `assets/constancia_cbu.png`.
6. **Guardar** en Desktop con nombre `{caratula_corta}_giro_honorarios.docx`.
7. **Preguntar si subir al PJN** como borrador usando skill `subir-escrito-pjn`.

## Formato

Seguir estrictamente `feedback_formato_escritos.md`:
- Times New Roman 12pt
- Interlineado 1.5
- Márgenes 3/2/2/2 (izq/sup/inf/der)
- Título principal: JUSTIFICADO, negrita + subrayado, sin sangría
- "Sr. Juez:" a la izquierda, sin sangría
- Primer párrafo: sangría 1.5 cm, nombre y carátula en negrita
- Secciones I.-, II.-, III.-, IV.-: sangría 1.25 cm, negrita + subrayado, UNA LÍNEA EN BLANCO antes de cada una
- Cuerpo: justificado, sangría 1.25 cm

## Estructura del escrito (4 secciones)

- **I.- SE ORDENE TRANSFERENCIA** (o `TRABA EMBARGO + SE LIBRE GIRO` si variante B): VISTO los depósitos, SOLICITO ordene transferir $X (honorarios + IVA) al CBU del suscripto.
- **II.- ADJUNTA DOCUMENTACIÓN. DECLARA BAJO JURAMENTO**: adjunta constancia AFIP + CBU, declara bajo juramento que son auténticas.
- **III.- PRESTA JURAMENTO**: único letrado actuante en autos.
- **IV.- HACE RESERVA**: (i) reserva de reclamar intereses por mora y aplicar art. 900 CCCN (imputación a intereses primero); (ii) reserva art. 51 ley 27.423 (diferencia por valor UMA al momento del pago).

## Cierre

- "Proveer de conformidad," centrado, sin negrita
- "SERÁ JUSTICIA.-" centrado, negrita

## Anexos (obligatorios en PJN/CABA)

Al final del DOCX, en hojas aparte (page breaks):
1. Constancia AFIP/ARCA del suscripto
2. Constancia CBU del Banco Ciudad

Insertar con `add_picture(width=Inches(6))` para la AFIP y `width=Inches(5))` para la CBU, en párrafos centrados.

## Referencias

- **Modelo fiel**: `references/modelo-giro.md` (basado en el escrito de MOLINA c/ SWISS)
- **Assets**: `assets/constancia_afip.png`, `assets/constancia_cbu.png`
- **Template Python**: `templates/generar_giro.py`
