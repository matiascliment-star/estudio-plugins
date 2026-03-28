---
name: briefing-expedientes
description: >
  Revisa expedientes judiciales con monitoreo_diario=true, detecta movimientos nuevos,
  actualiza los resumenes en Supabase, genera un reporte del dia y lo manda por mail
  a flirteador84@gmail.com. El briefing cubre: novedades del dia, casos sin movimiento
  hace mas de 30 dias, y saldo pendiente de cobro en ejecuciones.
  Usar cuando el usuario pida: "dame el briefing", "qué pasó hoy en los expedientes",
  "novedades judiciales", "revisar expedientes monitoreados", "briefing diario",
  "que hay de nuevo en los casos", "resumen del dia judicial", "chequear expedientes".
  Triggers: "briefing", "novedades expedientes", "que paso hoy", "revisar casos monitoreados".
  El scheduled task lo corre automaticamente cada dia habil a las 9am.
version: 0.1.0
---

# Skill: Briefing Diario de Expedientes

Revisa todos los expedientes con monitoreo activo, detecta novedades, actualiza resumenes y manda el reporte por mail.

## Credenciales

Leer de `~/.env`:
- PJN: `PJN_USUARIO` y `PJN_PASSWORD`
- MEV: `MEV_USUARIO` y `MEV_PASSWORD`
- Supabase: project_id `wdgdbbcwcrirpnfdmykh`
- Mail: enviar a `flirteador84@gmail.com` (misma casilla de origen)

## Formato de resumen

Los formatos de resumen_ia son los definidos en el skill `resumir-expediente` (ver `~/.claude/skills/resumir-expediente/SKILL.md`).
Cuando el briefing actualiza un resumen, SIEMPRE seguir esos mismos formatos.
Perspectiva: siempre desde NUESTRO ESTUDIO (parte actora). Distinguir NOSOTROS vs ELLOS.

## Workflow

### Paso 1: Obtener expedientes monitoreados

```sql
SELECT id, numero_causa, caratula, estado, jurisdiccion, juzgado,
       mev_idc, mev_ido, resumen_ia, ultima_revision_auto
FROM expedientes
WHERE monitoreo_diario = true
ORDER BY estado, caratula
```

Si no hay ninguno → informar y terminar.

### Paso 2: Detectar novedades por expediente

Para cada expediente, según jurisdiccion:
- **PJN**: `pjn_obtener_movimientos` con numero_causa, PJN_USUARIO, PJN_PASSWORD
- **MEV**: `mev_obtener_movimientos` con mev_idc, mev_ido, MEV_USUARIO, MEV_PASSWORD

Comparar: movimientos con fecha > `ultima_revision_auto` → hay novedad.

### Paso 3: Procesar novedades

#### Si hay movimiento nuevo:

1. Leer el documento si el movimiento es importante (sentencia, liquidacion, deposito, giro, embargo, intimacion, regulacion honorarios):
   - PJN: `pjn_leer_documentos` con filtro_descripcion y fecha_desde
   - MEV: `mev_leer_documentos` con filtro_descripcion y fecha_desde

2. Detectar CAMBIO DE ETAPA y leer documento completo si aplica:

   | Movimiento | Cambio | Qué extraer |
   |---|---|---|
   | "SENTENCIA DEFINITIVA", "HACER SABER SENTENCIA" | Prueba → Sentencia | Rubros, montos, tasa, costas |
   | "APROBAR LIQUIDACION" | Sentencia → Ejecución | Capital, intereses, total, honorarios |
   | "CONCEDER RECURSO", "ELEVAR A CAMARA" | 1ra → Cámara | Quién apeló, fecha |
   | "SENTENCIA DE CAMARA" | Cámara → Post | Confirmó/revocó, montos |
   | "DEPOSITO", "TRANSFERENCIA", "GIRO" | Cobro | Monto, concepto, quién |
   | "REGULACION DE HONORARIOS" | Regulación | A quién, cuánto, UMAs |

3. Agregar al resumen_ia existente (NO reemplazar, solo agregar al final):
   ```
   --- Revisión [fecha de hoy] ---
   Nuevo: [descripción de lo ocurrido, con montos y datos concretos]
   ```

4. Actualizar Supabase:
   ```sql
   UPDATE expedientes SET
     resumen_ia = '[resumen con el nuevo bloque agregado]',
     estado = '[nuevo estado si cambió de etapa]',
     ultima_revision_auto = now()
   WHERE id = [id];
   ```

#### Si NO hay movimiento nuevo:

Solo actualizar fecha:
```sql
UPDATE expedientes SET ultima_revision_auto = now() WHERE id = [id];
```

### Paso 4: Generar el briefing

#### Para la CONVERSACION (markdown bonito):

```markdown
# Briefing Judicial — DD/MM/YYYY

## 🔔 Con novedades

### [CARATULA] (`numero_causa`)
> [descripcion de lo que pasó, con montos si los hay]

**Acción:** [qué hay que hacer]

---

## ⏰ Sin movimiento +30 días

| Caso | Días | Acción sugerida |
|------|------|-----------------|
| [CARATULA] (`numero`) | [X] días | Pedir pronto despacho |

---

## ✅ Sin novedades
- [CARATULA] — última revisión [fecha]
- [CARATULA] — última revisión [fecha]

---

## 💰 Tablero de ejecuciones

| Caso | Total en juego | Cobrado | Pendiente | % |
|------|---------------|---------|-----------|---|
| [CARATULA] | $X | $Y | $Z | N% |
| **TOTAL** | **$X** | **$Y** | **$Z** | **N%** |
```

#### Para el MAIL (HTML con colores y formato):

Usar `contentType: "text/html"` en gmail_create_draft. Armar un HTML limpio con:
- Header azul oscuro (#1a365d) con "Briefing Judicial — DD/MM/YYYY"
- Sección verde (#48bb78 borde izquierdo) para novedades
- Sección naranja (#ed8936 borde izquierdo) para sin movimiento +30 días
- Sección gris (#e2e8f0 fondo) para sin novedades
- Tabla con bordes para el tablero de ejecuciones
- Fuente: Arial/sans-serif, tamaño legible
- Estilo limpio, profesional, fácil de leer en celular

### Paso 5: Mostrar en conversación Y crear borrador en Gmail

1. PRIMERO: mostrar el briefing completo al usuario en la conversación usando el formato markdown.
2. DESPUÉS: crear el draft con `gmail_create_draft`:
   - to: `flirteador84@gmail.com`
   - subject: `Briefing Judicial — DD/MM/YYYY`
   - contentType: `text/html`
   - body: el briefing en HTML con colores y formato profesional
3. Confirmar que el borrador quedó guardado en Gmail.

## Reglas

- NUNCA reemplazar el resumen_ia completo, solo agregar bloques nuevos al final.
- Usar FECHAS CONCRETAS, no relativas.
- Incluir MONTOS exactos cuando los hay.
- Si un expediente no tiene resumen_ia → marcarlo como "PENDIENTE DE RESUMEN" en el briefing y no intentar procesarlo.
- Si el scraping falla para un expediente → reportar el error y continuar con los demás.
- Calcular dias_sin_movimiento comparando la fecha del último movimiento con hoy.
- Priorizar en el briefing: cobros/depósitos > sentencias > intimaciones > despachos > resto.
