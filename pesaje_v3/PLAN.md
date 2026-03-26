# Plan: Reescribir pesaje_v3 desde cero

## Estado actual
El directorio `pesaje_v3/` tiene una implementación parcial:
- Capa 1-2: funcionales pero wrappers del parser v1
- Capa 3: solo screening (5 condiciones), **faltan prototipos PF1-PF7, marcas de calidad**
- Capa 4: motor de hipótesis básico, **falta detección de error de dígito, AB_IMP, genealogía de entrantes completa**
- Capa 5: **no existe**
- Exportador: **no existe**
- No hay test runner end-to-end

## Qué cambia en la reescritura
Reescribir TODO el contenido de `pesaje_v3/` siguiendo fielmente `reglas_v3/01-08`.
Reusar `parser.py` v1 como dependencia (no reescribir el parser).

## Arquitectura de archivos

```
pesaje_v3/
  __init__.py
  modelos.py          — Todos los dataclasses (capas 1-5 + output)
  capa1_parser.py     — Wrapper parser v1 → DatosDia
  capa2_contrato.py   — Fórmula inmutable → ContabilidadDia
  capa3_motor.py      — Screening + PF1-PF8 + marcas calidad → ResultadoC3
  capa4_expediente.py — 4 planos + hipótesis + convergencia + CONJUNTO → ResultadoC4
  capa5_residual.py   — Segunda pasada (R1/R2/R3) → ResultadoC5
  pipeline.py         — Orquestador CLI: Capa1→2→3→4→5→ResultadoDia
  exporter.py         — Genera Excel de salida con bandas y trazabilidad
```

## Fases de implementación

### Fase 1: modelos.py (dataclasses limpios)
- Reescribir todas las estructuras según la spec
- Capas 1-5, enums, ResultadoDia
- Sin lógica, solo datos

### Fase 2: capa1_parser.py
- Wrapper limpio sobre `parser.load_shifts()`
- Fix R1.4 (ab=0 explícito)
- `cargar_dia(path, dia_num)` → DatosDia
- `cargar_todos_los_dias(path)` → list[DatosDia]

### Fase 3: capa2_contrato.py
- Fórmula inmutable: `venta = total_A + new_ent_B - total_B - ajuste_latas`
- Matching entrantes greedy ±50g
- VDP text_to_grams
- SOLO_DIA / SOLO_NOCHE

### Fase 4: capa3_motor.py (la más grande)
- Screening C1-C5 (5 condiciones)
- Clasificación: LIMPIO / ENGINE / SENAL / COMPUESTO / SOLO_*
- **PF1**: Error de dígito (±1000/2000g, ≥5 sightings)
- **PF2**: Entrante duplicado (persiste post-apertura)
- **PF3**: Phantom RM-3 (can abierto reaparece)
- **PF4**: Cerrada omitida en NOCHE
- **PF5**: Cerrada omitida en DIA
- **PF6**: Apertura + phantom combinado
- **PF7**: Abierta imposible (AB_IMP)
- **PF8**: Nombre inconsistente (aliases)
- Marcas de calidad (DATO_NORMAL, COPIA_POSIBLE_LEVE/FUERTE)
- Criterios de escalado a Capa 4

### Fase 5: capa4_expediente.py
- PASO 1: Timeline (±3 turnos contexto)
- PASO 2: 4 planos (P1 abierta, P2 cerradas, P3 entrantes, P4 celiacas)
- PASO 3: Generar todas las hipótesis
- PASO 4: Evaluar contra planos (favor/neutro/contra)
- PASO 5: Seleccionar mejor (≥2 planos independientes)
- PASO 6: Asignar tipo A/B/C/D → banda CONFIRMADO/FORZADO/ESTIMADO
- PASO 7: Guardia post-corrección
- ESPECIAL: ENGINE con phantom oculto
- ESPECIAL: Análisis CONJUNTO cross-sabor

### Fase 6: capa5_residual.py
- R1: Desvío histórico (z-score)
- R2: Rareza estructural débil (R2a-R2e)
- R3: Perfil de día anómalo (R3a-R3c)
- Regla de reapertura: ≥2 señales distintas → REABRIR (max 5/día)

### Fase 7: pipeline.py + exporter.py
- Pipeline: Capa1→2→3→4→5→ResultadoDia con verbose output
- CLI: `python -m pesaje_v3.pipeline <excel> <dia>`
- CLI all: `python -m pesaje_v3.pipeline <excel> --all`
- Exporter: Excel con bandas, colores por confianza, trazabilidad

### Fase 8: Validación
- Correr contra D5, D25, D27, D28 (días con GT conocido)
- Comparar resultados con valores validados en MEMORY.md

## Dependencias externas
- `parser.py` (v1) — se usa tal cual, no se toca
- `models.py` (v1) — se importa ShiftData/FlavorShiftData para conversión en Capa 1
- `openpyxl` — ya instalado

## Orden de trabajo
Implementar fase por fase, testeando cada capa antes de avanzar.
Capa 3 es la más compleja (8 prototipos). Capa 4 es la más delicada (convergencia epistemológica).
