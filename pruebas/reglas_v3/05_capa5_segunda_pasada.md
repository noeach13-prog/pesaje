# Capa 5 — Segunda pasada residual (detector de falsos LIMPIO)

## Responsabilidad

Detectar sabores que pasaron como LIMPIO en Capa 3 pero contienen
errores compensados invisibles al screening individual.

---

## Input

- Dia completo resuelto (todos los sabores pasaron por Capas 1-4)
- Estadisticas historicas mensuales por sabor (media, std, N periodos)
- Perfil del dia: distribucion de ventas de todos los sabores

## Output

Por cada sabor LIMPIO:
- LIMPIO_CONFIRMADO → sin senales residuales
- LIMPIO_CON_NOTA → 1 senal, no reabrir
- REABRIR → >=2 senales de distinto tipo, vuelve a Capa 3/4

---

## Cuando se ejecuta

DESPUES de que TODOS los sabores del dia pasaron por Capas 1-4.
No es parte del expediente local. Es analisis transversal del dia.

---

## S5.1 — Senal R1: Desvio historico del sabor

```
z_score = (venta_final - media_sabor) / std_sabor
```

| z_score | Interpretacion |
|---------|---------------|
| abs(z) <= 1.5 | Normal. Sin senal. |
| 1.5 < abs(z) <= 1.8 | Leve. Solo contribuye si hay otra senal. |
| 1.8 < abs(z) <= 2.5 | Moderado. Candidato R1. |
| abs(z) > 2.5 | Fuerte. Candidato R1 con peso alto. |

Excepciones (no marcar como R1):
- Sabor con <5 periodos de historial
- Sabor con std >2000g (altamente variable)
- Dia con apertura confirmada que explica venta alta

---

## S5.2 — Senal R2: Rareza estructural debil

Senales que en Capa 3 no alcanzaron para escalar pero persisten:

| Sub-senal | Definicion |
|-----------|-----------|
| R2a | 2+ cerradas con diferencia 30-75g (zona ambigua) |
| R2b | Ab no cambio (±5g) en periodo con venta esperada >500g |
| R2c | Entrante sin genealogia |
| R2d | Cerrada con 1 solo sighting preservada en calculo |
| R2e | Matching de cerrada justo en borde del threshold (25-35g) |

Acumular >=2 sub-senales = 1 senal R2 fuerte.

---

## S5.3 — Senal R3: Perfil de dia anomalo

| Sub-senal | Definicion |
|-----------|-----------|
| R3a | >=2 sabores con desvios fuertes en direcciones opuestas |
| R3b | >=3 sabores simultaneamente >1.5 sigma |
| R3c | Total ventas del dia difiere >2 sigma del promedio diario |

R3 busca patrones invisibles sabor por sabor pero visibles a nivel dia.

---

## S5.4 — Regla de reapertura

```
Para cada sabor LIMPIO:
  senales = contar R1, R2, R3 presentes

  Si senales == 0 → LIMPIO_CONFIRMADO
  Si senales == 1 → LIMPIO_CON_NOTA (registrar, no reabrir)
  Si senales >= 2 → REABRIR
```

Condiciones de reapertura:
- Requiere >=2 senales de DISTINTO tipo (no 2 sub-senales R2)
- Maximo 5 reaperturas por dia
- Si >5 candidatos, priorizar por impacto potencial
- Sabor reabierto que vuelve LIMPIO de Capa 3 → LIMPIO_CONFIRMADO (no reabrir dos veces)

---

## S5.5 — Lo que esta capa NO hace

- No recalcula ventas
- No aplica correcciones
- No opera sobre ENGINE o ESCALADO (solo LIMPIO)
- No usa solo estadistica (combinacion estadistico-estructural)
- No reemplaza Capa 3 ni Capa 4

---

## Calibracion pendiente

Los thresholds (1.8 sigma, 30-75g, maximo 5 reaperturas) son propuestas iniciales.
Requieren calibracion empirica con dias validados para verificar:
1. Cuantos falsos LIMPIO reales existen
2. Si la regla >=2 senales los captura sin reabrir demasiados genuinos
3. Si el maximo de 5 es suficiente o demasiado conservador
