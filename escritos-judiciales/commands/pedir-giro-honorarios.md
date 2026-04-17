---
description: Genera escrito de pedido de giro electrónico de honorarios (PJN/CABA) con constancias embebidas
allowed-tools: Read, Write, Bash, Grep, Glob
argument-hint: [numero-expediente] [variante A|B] [monto-honorarios]
---

Genera un escrito DOCX para pedir el libramiento de giro electrónico de honorarios profesionales en causas de PJN (Justicia Nacional / CABA), siguiendo el modelo del estudio.

Leer primero el skill en `${CLAUDE_PLUGIN_ROOT}/skills/pedir-giro-honorarios/SKILL.md` para obtener las instrucciones completas.

Argumentos del usuario: $ARGUMENTS

## Pasos

1. **Identificar el expediente** (número o carátula). Confirmar en Supabase con el skill `scrape-pjn-supabase` (jurisdicción CABA).
2. **Leer los últimos movimientos** (tabla `movimientos_pjn`, columna `texto_documento` en Supabase) para identificar:
   - Fechas y montos de los depósitos de la demandada.
   - Si se depositó "en pago" o "en embargo".
   - Si hay queja en CSJN u otro recurso pendiente → usar variante B (traba embargo + giro).
3. **Calcular el monto a girar**: suma de honorarios profesionales del letrado + IVA (21%).
4. **Generar el DOCX** a partir del template `${CLAUDE_PLUGIN_ROOT}/skills/pedir-giro-honorarios/templates/generar_giro.py`:
   - Copiar a `/tmp/generar_giro_<caso>.py`
   - Editar el dict `CASO` con los datos concretos
   - Ejecutar `python3 /tmp/generar_giro_<caso>.py`
   - El DOCX se guarda en `~/Desktop/<caratula_short>_giro_honorarios.docx` con las constancias AFIP y CBU embebidas al final.
5. **Formato**: se aplica automáticamente el estándar del estudio (Times 12, 1.5, márgenes 3/2/2/2, título justificado + negrita/subrayado, secciones con sangría 1.25 y espacio en blanco antes).
6. **Preguntar si subir al PJN** como borrador usando `/subir-escrito-pjn`.

## Variantes

- **A — Giro simple**: los fondos ya están a disposición del letrado (en pago). Título: `SE LIBRE GIRO ELECTRÓNICO EN CONCEPTO DE HONORARIOS...`.
- **B — Traba embargo + giro**: los fondos están "dados en embargo" por la demandada (ej: queja en CSJN pendiente). El punto I primero TRABA EMBARGO a favor del suscripto sobre las sumas depositadas, y luego pide ORDENE TRANSFERIR.

## Estructura del escrito (siempre 4 secciones fijas)

- **I.- SE ORDENE TRANSFERENCIA** (o `TRABA EMBARGO + SE LIBRE GIRO` en variante B)
- **II.- ADJUNTA DOCUMENTACIÓN. DECLARA BAJO JURAMENTO**
- **III.- PRESTA JURAMENTO** (único letrado actuante)
- **IV.- HACE RESERVA** (art. 900 CCCN + art. 51 ley 27.423)

## Anexos obligatorios (PJN/CABA)

Al final del DOCX, en hojas aparte:
- Constancia AFIP/ARCA del suscripto (desde `${CLAUDE_PLUGIN_ROOT}/skills/pedir-giro-honorarios/assets/constancia_afip.png`)
- Constancia CBU del Banco Ciudad (desde `${CLAUDE_PLUGIN_ROOT}/skills/pedir-giro-honorarios/assets/constancia_cbu.png`)
