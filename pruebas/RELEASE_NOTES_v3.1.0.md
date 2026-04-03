# Pesaje v3.1.0 — Enmienda INTRADUP + Threshold temporal + PFIT

Fecha: 2026-03-28

## Doctrina nueva: el turno como objeto de evidencia

Hasta v3.0.0 el sistema razonaba sabor por sabor, con acceso a contexto temporal
de *ese* sabor en turnos anteriores y posteriores. La unidad de razonamiento era
el sabor individual con su historia.

Esta versión introduce una fuente de evidencia nueva: **el turno completo como señal
colectiva**. Cuando muchos sabores de una misma planilla exhiben el mismo vicio de
carga, eso no es ruido por sabor — es información sobre cómo se escribió esa hoja.
El sistema ahora puede leer esa señal y usarla para cambiar el estatuto de evidencia
de hipótesis individuales que, aisladas, no llegarían a confirmarse.

La distinción que importa preservar:

> **INTRADUP_MASIVO_TURNO no corrige por contagio. Eleva sospechas individuales
> bajo patrón colectivo.**

Un sabor no queda corregido porque sus vecinos también tienen el problema. Queda
corregido porque tenía su propia señal (entrante DIA ≈ cerrada DIA) que antes
quedaba descartada por falta de soporte temporal individual. El patrón colectivo
no inventa evidencia; cambia el umbral para considerar suficiente la evidencia
que ya existía. La cadena de custodia permanece por sabor.

---

## Cambios técnicos

### 1. PFIT: hipótesis de doble registro intra-turno (`generadores_c3.py`)

Nuevo generador que detecta cuando un entrante DIA coincide (±100g) con una
cerrada DIA del mismo turno — el empleado cargó la misma lata en ambas columnas.

Jerarquía de confianza:
- **FUERTE (0.88)**: la cerrada existía en el turno previo (backward confirma identidad).
- **MEDIA (0.72)**: la cerrada persiste en el turno siguiente, previo ambiguo.
- **DÉBIL**: sin soporte temporal individual → no corrige (salvo INTRADUP_MASIVO, ver abajo).

Semánticamente distinto de PF2 (genealogía entrante→cerrada cross-turno). PFIT
detecta "registrado dos veces en la misma hoja"; PF2 detecta "transformación
legítima promovida al turno siguiente". Mezclarlos sería un error de categoría.

### 2. INTRADUP_MASIVO_TURNO: señal colectiva de planilla (`capa3_motor.py`)

`_detectar_intradup_masivo()` evalúa el turno completo con condición compuesta:
- N candidatos ≥ 8 sabores con patrón intra-turno
- Proporción ≥ 15% del total de sabores del turno
- Peso total duplicado ≥ 50,000g

Las tres condiciones deben cumplirse simultáneamente. El conteo solo no basta
(8/10 sabores es distinto de 8/60). La proporción sola no basta (15% con peso
mínimo bajo podría ser ruido). El peso solo no basta (una lata grande no hace un
patrón). La condición compuesta exige convergencia de señales.

Cuando el masivo se activa:
1. Cada sabor candidato recibe flag `INTRADUP` → forzado a SENAL aunque venta < threshold.
2. PFIT DÉBIL (sin backward ni forward) se eleva a MEDIA (0.72) con traza explícita:
   `ELEVADO_POR_INTRADUP_MASIVO_TURNO: patron colectivo de doble-registro en planilla`.
3. `ResultadoC3.warnings` registra el hallazgo a nivel de día.

### 3. Threshold mode-dependent (`constantes_c3.py`, `capa3_motor.py`)

El umbral de venta "sospechosamente alta" ahora depende de la unidad temporal real:
- `DIA_NOCHE` (medio día): 5,000g sospechoso — correcto, es un turno parcial.
- `TURNO_UNICO` (día completo): 8,000g — una lata entera (~6,700g) vendida en un
  día completo es normal. Usar 5,000g universal en TURNO_UNICO era una acusación
  sistemática, no prudencia.

### 4. Exporter: coherencia de columna para ESCALAR_C4 (`exporter_multi.py`)

Los sabores sin resolver (`⚪ Sin resolver`) ahora muestran `venta_raw` en la
columna "Venta (g)" en lugar de 0. La columna suma igual que el subtotal.
Etiqueta visual diferenciada: `⚪ Sin resolver` vs `✓ Sin cambios`.

---

## Validación

Prueba positiva — Triunvirato D13 (Viernes 13, planilla con doble-registro masivo):
- `INTRADUP_MASIVO=True`: 34 sabores candidatos, ~223kg duplicados.
- MOUSSE LIMON: DÉBIL elevado → `CORREGIDO_C3_BAJA_CONFIANZA`, delta=-6,320g.
- Sabores con backward propio resueltos independientemente (26 hipótesis FUERTE).

Prueba negativa — San Martín D5/D6/D8:
- D5: 4 candidatos aislados / 53 sabores → `masivo=False`. ✓
- D6, D8: 0 candidatos → `masivo=False`. ✓

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `constantes_c3.py` | `INTRADUP_MASIVO_*` (3 constantes), `PFIT_*` (4 constantes), threshold dual |
| `modelos.py` | `ObservacionC3.intradup_candidato`, `ResultadoC3.warnings` |
| `capa3_motor.py` | `_observar` detecta candidato; `_detectar_intradup_masivo` nuevo; `_screening` acepta masivo; `clasificar` pase doble |
| `generadores_c3.py` | `generar_hipotesis_pfit` completo; `generar_todas_hipotesis` pasa `turno_masivo` |
| `exporter_multi.py` | `venta_raw_fallback` para ESCALAR_C4; label `⚪ Sin resolver` |

---

## Pendientes heredados de v3.0.0

- VDP no capturado en algunos días.
- Capa 5 residual: solo diagnostica, no reabre casos.
- Multi-PFIT (sabor con 2+ entrantes duplicados): el árbitro escala conservadoramente.
  Candidato para v3.2.0: corrección compuesta acumulativa bajo INTRADUP_MASIVO.
