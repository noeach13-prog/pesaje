# Segunda pasada residual v3 — Detector de falsos LIMPIO (DRAFT)

---

## PROBLEMA QUE RESUELVE

Un sabor puede pasar todas las condiciones de LIMPIO en Capa 3 porque dos errores
se compensan. Ejemplos:
- Dígito +1000g en cerrada + omisión de otra cerrada de ~1000g → venta neta se ve razonable
- Error de pesaje en abierta +500g + cerrada cercana confundida -500g → cancela
- Entrante no documentado que compensa una cerrada phantom

Capa 3 no puede detectar esto porque evalúa cada señal por separado.
La segunda pasada opera sobre el **perfil completo del día ya resuelto**.

---

## CUÁNDO SE EJECUTA

Después de que TODOS los sabores del día pasaron por Capas 1-4.
No es parte del expediente local de un sabor. Es análisis transversal del día.

---

## SEÑALES RESIDUALES

La segunda pasada usa 3 tipos de señales. Ninguna por sí sola justifica reabrir.

### Señal R1 — Desvío histórico del sabor

Comparar venta_final del sabor contra su promedio histórico mensual.

```
z_score = (venta_final - media_sabor) / std_sabor
```

| z_score | Interpretación |
|---------|---------------|
| |z| ≤ 1.5 | Normal. Sin señal. |
| 1.5 < |z| ≤ 1.8 | Leve. Solo contribuye si hay otra señal. |
| 1.8 < |z| ≤ 2.5 | Moderado. Candidato R1. |
| |z| > 2.5 | Fuerte. Candidato R1 con peso alto. |

**Excepciones** (no marcar como R1):
- Sabor con <5 períodos de historial (distribución insuficiente)
- Sabor con std muy alta (>2000g): altamente variable por naturaleza
- Día con apertura confirmada que explica la venta alta

**No es solo ±2σ bruto.** Se filtra por calidad del historial y se combina con R2/R3.

### Señal R2 — Rareza estructural débil

Señales que en Capa 3 no fueron suficientes para escalar, pero que persisten:

| Sub-señal | Definición |
|-----------|-----------|
| R2a: cerr_cercanas | 2+ cerradas con diferencia 30-75g (zona ambigua de matching) |
| R2b: ab_plana_sospechosa | Ab no cambió (±5g) en período con venta >500g esperada |
| R2c: entrante_sin_genealogía | Entrante que aparece sin antecedente en turnos previos |
| R2d: cerr_1sighting_preservada | Cerrada con 1 solo sighting que quedó en el cálculo |
| R2e: match_en_límite | Matching de cerrada que cae justo en el borde del threshold (25-35g) |

Cada sub-señal cuenta como 1 señal R2. Acumular ≥2 sub-señales = 1 señal R2 fuerte.

### Señal R3 — Perfil de día anómalo

Análisis del perfil completo de ventas del día:

| Sub-señal | Definición |
|-----------|-----------|
| R3a: compensación_opuesta | ≥2 sabores con desvíos fuertes en direcciones opuestas (uno muy alto, otro muy bajo) que podrían compensarse |
| R3b: cluster_de_extremos | ≥3 sabores simultáneamente >1.5σ (improbable si son independientes) |
| R3c: total_día_vs_promedio | Total de ventas del día difiere >2σ del promedio diario |

R3 busca patrones que no son visibles sabor por sabor pero sí a nivel de día.

---

## REGLA DE REAPERTURA

```
Para cada sabor LIMPIO:
  Contar señales presentes: R1, R2, R3

  Si señales = 0     → LIMPIO_CONFIRMADO. No tocar.
  Si señales = 1     → LIMPIO_CON_NOTA. Registrar, no reabrir.
  Si señales ≥ 2     → REABRIR.
```

**REABRIR** significa:
- El sabor vuelve a entrar a Capa 3 como SOSPECHOSO.
- Si Capa 3 no resuelve con prototipo, escala a Capa 4.
- Documentar que fue reabierto por segunda pasada, con las señales que lo dispararon.

**Protección contra reapertura indiscriminada**:
- Solo sabores LIMPIO. Los que ya fueron ENGINE/ESCALADO no se reabren aquí.
- Requiere ≥2 señales de distinto tipo (no 2 sub-señales R2).
- Máximo de reaperturas por día: 5 sabores. Si >5 candidatos, priorizar por impacto potencial.
- Un sabor reabierto que vuelve a salir LIMPIO de Capa 3 queda como LIMPIO_CONFIRMADO.
  No se reabre dos veces.

---

## EJEMPLO DE FALSO LIMPIO DETECTABLE

Sabor EJEMPLO_X, Día 15:
- Capa 3: LIMPIO. raw_sold = 1200g. No hay señales.
- R1: media histórica de EJEMPLO_X = 450g, std = 180g. z = (1200-450)/180 = 4.17. **R1 fuerte.**
- R2: cerr 6380 y 6410 en DIA (dif=30g, justo en borde). **R2e presente.**
- R3: no hay señal de día.
- Señales = 2 (R1 + R2). → **REABRIR**.
- En Capa 3/4: se descubre que 6380 y 6410 son el mismo can (varianza pesaje),
  una fue contada doble. Corrección: -6400g de venta falsa. Venta real = -5200g → escalar.

---

## EJEMPLO DE LIMPIO GENUINO

Sabor EJEMPLO_Y, Día 15:
- Capa 3: LIMPIO. raw_sold = 800g.
- R1: media = 600g, std = 250g. z = 0.80. No es candidato R1.
- R2: ninguna sub-señal presente.
- R3: día normal.
- Señales = 0. → **LIMPIO_CONFIRMADO**.

---

## LO QUE ESTA PASADA NO HACE

- No recalcula ventas. Solo decide si reabrir.
- No aplica correcciones. Solo señala candidatos para re-análisis.
- No reemplaza Capa 3 ni Capa 4. Los sabores reabiertos pasan por el pipeline normal.
- No opera sobre sabores ya resueltos por engine o por prototipo. Solo sobre LIMPIO.
- No usa solo estadística. La combinación R1+R2+R3 es estadístico-estructural.

---

## CALIBRACIÓN PENDIENTE

Los thresholds (1.8σ, 30-75g, máximo 5 reaperturas) son propuestas iniciales.
Requieren calibración empírica con los días validados (D25, D26, D27, D28) para verificar:
1. ¿Cuántos falsos LIMPIO reales existen en esos días?
2. ¿La regla de ≥2 señales los captura sin reabrir demasiados LIMPIO genuinos?
3. ¿El máximo de 5 reaperturas es suficiente o demasiado conservador?

Hasta calibrar, los valores propuestos son heurísticas razonables, no verdades empíricas.
