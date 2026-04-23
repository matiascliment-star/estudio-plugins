# Formato canónico para escritos judiciales DOCX

> **FUENTE DE VERDAD ÚNICA.** Este archivo describe el formato exacto que tienen
> que respetar **todos** los escritos judiciales generados por skills del Estudio
> García Climent. Si algún SKILL.md tiene un bloque de formato que contradice
> esta spec, gana esta spec.
>
> Implementación de referencia: `escritos-judiciales/scripts/formato_escrito.py`

## Por qué existe este archivo

Históricamente cada SKILL.md (redactar-escrito, hacer-alegato, recursos,
liquidaciones, corridas) duplicaba su propio bloque de python-docx con
parámetros levemente distintos. El resultado: el formato real de los escritos
nunca coincidía con el de los modelos del estudio. Ahora todos los skills
referencian este archivo + importan `formato_escrito.py`.

---

## Especificación

### Fuente y tamaño
- **Fuente:** Times New Roman
- **Tamaño:** 12 pt
- **Espacio después de párrafo:** 0

### Interlineado
- 1.5 en todo el cuerpo

### Márgenes de página
| Lado | cm |
|---|---|
| Superior | 2.0 |
| Inferior | 2.0 |
| Izquierdo | 3.0 |
| Derecho | 2.0 |

### Tipos de párrafo

| Tipo | Alineación | Sangría 1ra línea | Negrita | Subrayado | Notas |
|---|---|---|---|---|---|
| **Título principal** (objeto del escrito) | **JUSTIFICADO** | No | Sí | Sí | Ej: "INTERPONE RECURSO EXTRAORDINARIO FEDERAL" |
| **Encabezado al tribunal** | **IZQUIERDA** | No | No | No | Ej: "Sr. Juez:", "Excma. Corte:" |
| **Párrafo letrado** (presentación inicial) | Justificado | 1.5 cm | Solo nombre + carátula | No | Ver detalle abajo |
| **Título de sección** (I. OBJETO, II. HECHOS…) | Justificado | **1.25 cm** (igual que cuerpo) | Sí | Sí | Línea en blanco antes (space_before = 12 pt) |
| **Párrafo normal** | Justificado | 1.25 cm | No | No | |
| **Párrafo sin sangría** (items petitorio) | Justificado | 0 | No | No | Para "1. ...", "2. ..." |
| **Firma** | Centrado | 0 | Solo nombre | No | + "(Firmado electrónicamente)" en itálica |

### Párrafo letrado (intro) — detalle
Sangría primera línea **1.5 cm** (no 1.25). Estructura:

```
[NOMBRE EN NEGRITA], texto-pre-carátula, [CARÁTULA + EXPTE EN NEGRITA], texto-post-carátula
```

Ejemplo:

> **MATÍAS CHRISTIAN GARCÍA CLIMENT**, abogado, T° 97 F° 16 C.P.A.C.F., con
> domicilio electrónico constituido en 20-XXXXXXXX-X, en autos
> **VÁZQUEZ, MIGUEL ANGEL c/ SWISS MEDICAL ART s/ ACCIDENTE - LEY ESPECIAL
> Expte. N° 045419/2021**, a V.E. respetuosamente digo:

### Numeración de secciones
Romana: `I.`, `II.`, `III.`, `IV.`, … (no `1.`, `2.`).

### Espaciado entre secciones
Cada título de sección lleva **una línea en blanco antes** (implementado como
`space_before = Pt(12)` o párrafo vacío).

### Datos profesionales para firma
Por defecto:

```
MATÍAS CHRISTIAN GARCÍA CLIMENT
ABOGADO
T° 97 F° 16 C.P.A.C.F. / T° 46 F° 393 C.A.S.I.
(Firmado electrónicamente)
```

---

## Cómo usar desde un skill

### Opción A — Usar el helper (recomendado)
```python
import sys
from pathlib import Path

# Subir hasta el plugin escritos-judiciales y usar su scripts/
PLUGIN_ROOT = Path(__file__).resolve().parents[N]  # ajustar N según ubicación
sys.path.insert(0, str(PLUGIN_ROOT / "escritos-judiciales" / "scripts"))

from formato_escrito import (
    nuevo_documento, titulo_principal, encabezado_tribunal,
    parrafo_letrado, titulo_seccion, parrafo, firma,
)

doc = nuevo_documento()
titulo_principal(doc, "PRACTICA LIQUIDACIÓN")
encabezado_tribunal(doc, "Sr. Juez:")
parrafo_letrado(
    doc,
    "MATÍAS CHRISTIAN GARCÍA CLIMENT",
    ", abogado, T° 97 F° 16 C.P.A.C.F., en autos ",
    "GIMÉNEZ, JUAN c/ ART X s/ ACCIDENTE Expte. N° 12345/2023",
    ", a V.S. digo:",
)
titulo_seccion(doc, "I. OBJETO")
parrafo(doc, "Vengo a practicar liquidación...")
firma(doc)
doc.save("/tmp/escrito.docx")
```

### Opción B — Inline (si no se puede importar)
Replicar exactamente los parámetros de la spec arriba. **Antes** de inventar
algo distinto, asegurarse de que coincide con `formato_escrito.py`.

---

## Cambios futuros
Si el formato cambia, **editar este archivo y `formato_escrito.py`**. Nada más.
Los SKILL.md no necesitan tocarse porque referencian este doc.
