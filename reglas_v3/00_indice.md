# Sistema de Analisis v3 — Indice de reglas

Fecha: 2026-03-23
Estado: REGLAS DEFINIDAS, pendiente de implementacion

---

## Archivos de reglas

| # | Archivo | Capa | Contenido | Dependencias |
|---|---------|------|-----------|-------------|
| 01 | `01_capa1_parser.md` | 1 | Lectura del workbook, estructura de datos crudos | Ninguna |
| 02 | `02_capa2_contrato.md` | 2 | Formula de venta, componentes del total | Capa 1 |
| 03 | `03_capa3_motor.md` | 3 | Screening, flags, prototipos PF1-PF8, marcas de calidad | Capas 1-2 |
| 04 | `04_capa4_expediente.md` | 4 | 4 planos, convergencia, tipos de resolucion, CONJUNTO | Capas 1-3 |
| 05 | `05_capa5_segunda_pasada.md` | 5 | Senales R1-R3, reapertura de falsos LIMPIO | Capas 1-4 completas |
| 06 | `06_bandas_tipos_justificacion.md` | Transversal | Taxonomia A/B/C/D, 3 bandas, reglas de mapeo | Capas 3-4 |
| 07 | `07_reglas_madre.md` | Transversal | RM-1 a RM-10, principios fisicos P1-P6 | Todas |
| 08 | `08_numero_operativo.md` | Salida | Definicion del numero operativo, formato de reporte | Capas 1-5 + bandas |

---

## Orden de implementacion

```
Fase 1: Capas 1-2 (parser + formula)
  → Input: Excel
  → Output: datos crudos + venta raw por sabor
  → Test: comparar raw con valores conocidos de D5, D25, D28

Fase 2: Capa 3 (motor local)
  → Input: datos crudos
  → Output: clasificacion por sabor (LIMPIO/ENGINE/SENAL/COMPUESTO/SOLO_DIA)
  → Test: comparar clasificaciones con auditorias existentes

Fase 3: Capa 4 (expediente ampliado)
  → Input: sabores escalados + contexto temporal
  → Output: correcciones con tipo de resolucion
  → Nota: esta capa puede ser semi-automatica (Python genera el expediente, humano/LLM decide)

Fase 4: Capa 5 (segunda pasada)
  → Input: dia completo resuelto
  → Output: falsos LIMPIO reabiertos
  → Nota: requiere estadisticas mensuales por sabor

Fase 5: Bandas + numero operativo
  → Input: todas las correcciones clasificadas
  → Output: numero operativo del dia en formato estandar
```

---

## Relacion con archivos anteriores

Los archivos `04*_v3_draft.md` son los borradores de diseno.
Los archivos en `reglas_v3/` son la version limpia y modular para implementacion.
El baseline v2 (`09_baseline_operativo.md`) sigue vigente en produccion hasta que v3 se implemente.
