# Mapeo de Campos del Anexo I (SRT)

El Anexo I es un formulario PDF rellenable de la SRT (Superintendencia de Riesgos del Trabajo). El template está en `${CLAUDE_PLUGIN_ROOT}/templates/ANEXO_I_RELLENABLE.pdf`.

## Campos de texto (/Tx)

Los datos se extraen de múltiples fuentes: ficha del cliente, recibo de sueldo, alta médica y DNI. Se indica la fuente principal de cada dato.

### Datos del trabajador
| Campo PDF | Dato | Fuente principal |
|-----------|------|-----------------|
| `trabajador_nombre` | Nombre completo del trabajador | Ficha / DNI |
| `trabajador_cuil` | CUIL del trabajador | Recibo de sueldo |

### Datos del empleador
| Campo PDF | Dato | Fuente principal |
|-----------|------|-----------------|
| `empleador_razon_social` | Razón social del empleador | Recibo de sueldo |
| `empleador_cuit` | CUIT del empleador | Recibo de sueldo |
| `empleador_establecimiento` | Establecimiento / lugar de trabajo | Recibo de sueldo |
| `empleador_localidad` | Localidad del empleador | Recibo de sueldo |
| `empleador_provincia` | Provincia del empleador | Recibo de sueldo |

### Datos de la ART
| Campo PDF | Dato | Fuente principal |
|-----------|------|-----------------|
| `art_denominacion` | Nombre de la ART | Alta médica (campo "Institución" o encabezado) |
| `art_cuit` | CUIT de la ART | Alta médica (si figura) |

### Datos del accidente
| Campo PDF | Dato | Fuente principal |
|-----------|------|-----------------|
| `fecha_ocurrencia` | Fecha del accidente | Ficha |
| `fecha_denuncia` | Fecha de denuncia (si se conoce) | Ficha / Alta médica |
| `fecha_baja_laboral` | Fecha de baja laboral (si se conoce) | Ficha / Alta médica |
| `detalle_accidente` | Resumen breve del accidente | Ficha |

### Datos médicos
| Campo PDF | Dato | Fuente principal |
|-----------|------|-----------------|
| `afecciones_diagnosticos` | Diagnóstico / lesiones | Ficha + Alta médica |

### Datos del letrado
| Campo PDF | Dato |
|-----------|------|
| `letrado_nombre` | Matias Christian García Climent |
| `letrado_matricula` | T°97 F°16 CPACF |
| `letrado_cuit_domicilio` | (configurar) |
| `firma_letrado_aclaracion` | Matias Christian García Climent |

### Otros campos
| Campo PDF | Dato |
|-----------|------|
| `fecha_firma` | Fecha actual |
| `firma_trabajador_aclaracion` | Nombre del trabajador |

## Campos de checkbox (/Btn)

### Tipo de accidente
| Campo PDF | Cuándo activar |
|-----------|---------------|
| `tipo_accidente_trabajo` | Si el accidente es laboral |
| `tipo_accidente_itinere` | Si el accidente es in itinere |
| `tipo_enfermedad_profesional` | Si es enfermedad profesional |

### Atención médica
| Campo PDF | Cuándo activar |
|-----------|---------------|
| `atencion_art_si` | Si se atendió por ART |
| `atencion_art_no` | Si NO se atendió por ART |
| `atencion_os_si` | Si se atendió por obra social |
| `atencion_os_no` | Si NO se atendió por obra social |

### Preexistencias
| Campo PDF | Cuándo activar |
|-----------|---------------|
| `preexistencia_no` | **SIEMPRE** — nunca completar preexistencias |
| `preexistencia_si` | **NUNCA** — no marcar jamás |

## Instrucciones para rellenar

Usar PyPDF2 para rellenar el PDF:

```python
from PyPDF2 import PdfReader, PdfWriter

reader = PdfReader("ANEXO_I_RELLENABLE.pdf")
writer = PdfWriter()
writer.append(reader)

# Para campos de texto
writer.update_page_form_field_values(writer.pages[0], {
    "trabajador_nombre": "NOMBRE DEL TRABAJADOR",
    "fecha_ocurrencia": "15/01/2026",
    # ... etc
})

# Para checkboxes, usar el nombre del campo y valor "/Yes" o "/Off"

writer.write(open("ANEXO_I_COMPLETADO.pdf", "wb"))
```

Importante: Algunos campos pueden estar en diferentes páginas del PDF (es un formulario de 3-4 páginas). Verificar en qué página está cada campo al rellenar.
