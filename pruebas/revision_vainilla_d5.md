# Revisión puntual: VAINILLA — Día 5

---

## A. Evidencias reales usadas en VAINILLA

La clasificación actual (Tipo A, CONFIRMADO) se apoyó en:

1. **P1 (ab)**: abierta 5055 → 4970 (-85g). Descenso normal, sin salto.
2. **P2 (cerr)**: cerr 6445 aparece en NOCHE, persiste en D6D y D6N (3 sightings post).

Corrección aplicada: tratar cerr 6445 como new_entrante_B (+6445g).
raw = -6360 → corr = 85g.

---

## B. Evaluación de independencia

### P1 — ¿Qué dice realmente?

P1 dice que la abierta bajó 85g. Eso es consistente con venta mínima de la abierta. P1 NO dice nada sobre la cerrada 6445. P1 no confirma ni refuta que la cerrada sea un entrante no documentado. P1 solo dice "la abierta se comportó normalmente", lo cual es igualmente compatible con:

- H1: la cerrada es un entrante no documentado (corrección aplicada)
- H2: la cerrada fue omitida en DIA (PF5 cerr omitida)
- H3: la cerrada fue registrada por error en NOCHE (phantom)

P1 no discrimina entre estas hipótesis. Su valor es que descarta escenarios donde la abierta sería anómala, pero no apunta a una corrección específica.

### P2 — ¿Qué dice realmente?

P2 dice que cerr 6445 persiste en D6D y D6N (3 sightings posteriores). Eso confirma que el can es REAL (no es phantom en NOCHE). Esto descarta H3.

Pero P2 no distingue entre H1 (entrante no documentado) y H2 (cerrada omitida en DIA). En ambos casos la cerr 6445 sería real y persistente.

### P3 (genealogía) — AUSENTE

No hay entrante documentado para 6445 en ningún turno. La corrección asume que fue un entrante no registrado. La ausencia de genealogía es NEUTRAL por regla v3 (no confirma ni refuta). Pero tampoco hay evidencia de que fuera una cerrada previamente existente: D3 no tiene cerradas en VAINILLA, D5D tampoco.

### ¿Son P1 y P2 independientes?

Sí, miden cosas distintas (comportamiento de la abierta vs persistencia de la cerrada). No hay circularidad.

### ¿Convergen en la MISMA corrección?

No exactamente. Convergen en "el raw -6360 es imposible" y en "la cerr 6445 es real". Pero no convergen positivamente en "el valor correcto es exactamente +85g". El valor +85g depende de asumir que 6445 es un entrante nuevo (new_entrante_B). Si fuera una cerrada omitida en DIA (H2), la corrección sería la misma numéricamente (agregar 6445 al stock DIA produce el mismo delta), pero la naturaleza del error sería distinta.

Resultado: P1 y P2 convergen en que el raw es imposible y la cerr es real. El valor corregido resulta ser el mismo bajo H1 y H2. Pero la convergencia es parcialmente por reductio (raw imposible), no puramente por evidencia positiva del mecanismo.

---

## C. Decisión final

**VAINILLA no es Tipo A puro. Es híbrido A/B.**

La evidencia positiva (P1+P2) confirma:
- el raw es imposible (la cerr es real, no phantom)
- el delta correcto es +6445g (bajo H1 y H2 el resultado numérico es idéntico)

Pero el MECANISMO exacto (¿entrante no documentado? ¿cerrada omitida?) no está resuelto por convergencia positiva. Se resuelve porque ambas hipótesis producen el mismo número.

Esto es epistemológicamente más fuerte que CHOCOLATE (Tipo B puro, donde el mecanismo tiene incertidumbre de 100g en el valor exacto). En VAINILLA, la incertidumbre es sobre la causa, no sobre el número.

**Decisión: VAINILLA queda en CONFIRMADO, pero reclasificado como Tipo A- (A degradado).**

Justificación:
1. El delta (+6445) es idéntico bajo todas las hipótesis viables (H1 y H2). No hay ambigüedad numérica.
2. P1+P2 son independientes y ambos contribuyen (P1 descarta ab anómala, P2 confirma can real y descarta phantom).
3. La incertidumbre residual es sobre el mecanismo causal, no sobre el valor corregido.
4. Esto lo distingue de Tipo B donde la incertidumbre SÍ afecta al valor (CHOCOLATE: ¿855g exactos o podría ser otro número?).

No merece FORZADO porque el valor corregido no tiene la ambigüedad de CHOCOLATE.
No merece ESTIMADO porque la evidencia es fuerte (3 sightings, raw imposible).
No merece H0 porque hay resolución numérica clara.

**Tipo: A- (convergencia independiente con mecanismo causal ambiguo pero resultado numérico unívoco)**
**Banda: CONFIRMADO**

---

## D. Impacto si cambiara

Si VAINILLA bajara a FORZADO:

```
CONFIRMADO: +305 - 6445 = -6140g → RAW + (-6140) = 33,955g
FORZADO: -6630 + 6445 = -185g → 33,955 + (-185) = 33,770g
ESTIMADO: -60g → 33,770 + (-60) = 33,710g
```

El total final no cambia (33,710). Solo cambiaría el subtotal CONFIRMADO (40,400 → 33,955) y el FORZADO absorbería más delta. Pero esto sería incorrecto porque VAINILLA no tiene la misma incertidumbre sobre el VALOR que CHOCOLATE. Bajarla contaminaría la banda FORZADO con un caso que no pertenece ahí.

La ecuación final NO cambia. VAINILLA queda en CONFIRMADO.
