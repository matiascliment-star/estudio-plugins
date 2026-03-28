---
name: ver-resumen
description: >
  Muestra el resumen IA (resumen_ia) de un expediente guardado en Supabase.
  NO scrapea ni lee documentos, solo va directo a la base de datos y muestra
  el resumen ya generado. Es instantáneo y no consume tokens leyendo expedientes.
  Usar cuando el usuario pida: "mostrame el resumen de", "ver resumen de",
  "qué tenemos de", "cómo está el caso", "estado del expediente", "ficha del caso",
  "qué dice el resumen de", "mostrar resumen".
  Triggers: "ver resumen", "mostrar resumen", "como esta el caso", "ficha del caso",
  "que tenemos de", "estado del expediente", "mostrame el resumen".
version: 0.1.0
---

# Skill: Ver Resumen de Expediente

Muestra el resumen IA guardado en Supabase. No scrapea nada, va directo a la base.

## Supabase
Project ID: `wdgdbbcwcrirpnfdmykh`

## Workflow

### Paso 1: Buscar el expediente

```sql
SELECT id, numero_causa, caratula, estado, jurisdiccion, juzgado,
       resumen_ia, monitoreo_diario, ultima_revision_auto
FROM expedientes
WHERE caratula ILIKE '%texto%' OR numero_causa ILIKE '%texto%'
```

Si hay varios resultados, mostrar lista y preguntar cuál.

### Paso 2: Mostrar el resumen

Si tiene `resumen_ia`:
- Mostrar el resumen completo tal como está guardado
- Mostrar al final: "Última revisión automática: [fecha]" y si tiene monitoreo activo o no

Si NO tiene `resumen_ia`:
- Informar que este expediente no tiene resumen cargado
- Sugerir: "Usá `/resumir-expediente` para generar el resumen de este caso"

### Paso 3 (opcional): Si el usuario pide varios

Si el usuario dice "mostrame los resúmenes de ejecución" o "todos los monitoreados":

```sql
SELECT id, numero_causa, caratula, estado, resumen_ia, ultima_revision_auto
FROM expedientes
WHERE monitoreo_diario = true
  AND resumen_ia IS NOT NULL
ORDER BY estado, caratula
```

Mostrar cada uno con un separador visual.

## Reglas

- NUNCA scrapear ni leer documentos. Este skill solo lee de Supabase.
- Si el resumen parece desactualizado (ultima_revision_auto > 7 días), avisar al usuario.
- Mostrar el resumen tal cual está, no reformatearlo ni resumirlo.
