---
name: calcular-intereses
description: >
  Calculador de intereses moratorios judiciales usando el CPACF. Usar cuando el usuario pida
  "calcular intereses", "liquidación judicial", "intereses moratorios", "tasa activa BNA",
  "actualizar montos", "calcular con tasa pasiva", "liquidar honorarios", "intereses desde fecha X",
  o cualquier cálculo de intereses para causas judiciales argentinas.
version: 0.1.0
---

# Calculador de Intereses CPACF

Herramienta para calcular intereses moratorios judiciales usando el calculador oficial del
Colegio Público de Abogados de la Capital Federal (tasas.cpacf.org.ar).

## Herramientas MCP disponibles

### cpacf_calcular_intereses

Calcula intereses sobre un capital entre dos fechas usando tasas oficiales.

**Parámetros:**

- `capital` (str, requerido): Monto sin puntos de miles, con coma decimal. Ej: `81435196,75`
- `fecha_inicial` (str, requerido): Formato dd/mm/aaaa. Ej: `13/03/2025`
- `fecha_final` (str, requerido): Formato dd/mm/aaaa. Ej: `10/11/2025`
- `tasa` (enum, default "1"): ID de la tasa a usar (ver listado abajo)
- `capitalizacion` (enum, default "0"): Período de capitalización: 0=ninguna, 30=mensual, 90=trimestral, 180=semestral
- `multiplicador` (enum, default "1"): Multiplicador de tasa: 1, 1.5, 2, 2.5

### cpacf_listar_tasas

Lista las tasas disponibles. No requiere parámetros.

## Tasas disponibles

| ID | Tasa | Uso habitual |
|----|------|-------------|
| 1 | Tasa Activa BNA Efectiva mensual vencida | **Estándar CNAT** - Créditos laborales (Acordada 2357/02) |
| 2 | Tasa Activa Cartera general BNA | Créditos comerciales |
| 3 | Tasa Pasiva BNA | Algunos créditos civiles |
| 4 | Tasa Activa BPBA | Causas Prov. Buenos Aires |
| 5 | Tasa Pasiva BPBA | Causas Prov. Buenos Aires |
| 6 | Art. 37 Ley 11.683 | Intereses resarcitorios fiscales |
| 7 | Art. 52 Ley 11.683 | Intereses punitorios fiscales |
| 8 | Tasa Pasiva BCRA | Referencia general |
| 9 | CER | Ajuste por inflación |
| 10 | IPIM hasta 31/10/15 | Índice mayorista histórico |
| 11 | IPIM desde 01/01/16 | Índice mayorista actual |
| 12 | IPC/IPCNU hasta 31/10/15 | Índice consumidor histórico |

## Guía de uso

1. Para causas laborales (CNAT), usar tasa ID 1 (Activa BNA) sin capitalización y multiplicador 1x, salvo que la sentencia disponga otra cosa.
2. El capital se ingresa SIN puntos de miles. Usar coma como separador decimal. Ej: para $81.435.196,75 ingresar `81435196,75`.
3. Las fechas van en formato argentino: dd/mm/aaaa.
4. El resultado incluye: capital original, total intereses, total liquidación, tasa acumulada, y URL al PDF del cálculo.
5. Para liquidaciones con múltiples rubros (capital, honorarios, etc.), ejecutar un cálculo separado por cada rubro.
