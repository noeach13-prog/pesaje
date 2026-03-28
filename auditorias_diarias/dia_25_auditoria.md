# Auditoría Día 25 — Miércoles 25 de Febrero 2026

**Período**: Miércoles 25 (DIA) ord.45 → Miércoles 25 (NOCHE) ord.46
**Sabores con datos**: 51 (CHOCOLATE CON PASAS y MARACUYA: ALL_EMPTY)
**Raw total**: 18,590g

---

## F1 — Clasificación

| Nivel | n | Detalle |
|-------|---|---------|
| LIMPIO | 47 | Todas las condiciones pasan |
| ENGINE | 2 | CHOCOLATE(1L), SAMBAYON AMORES(1L) |
| SOSPECHOSO | 2 | AMERICANA(cond.1: raw=-2450, cond.3: ab sube sin apertura), COOKIES(cond.4: cerr 6715→5705 sin match) |

**Notas LIMPIO**: FERRERO cerr 6365→6360 (5g). LIMON cerr 6280→6265 (15g). MIX DE FRUTA cerr 6790→6785 (5g). LEMON PIE cerr 6645→6615 (30g). Todos dentro de tolerancia ±30g. TIRAMIZU nombre NOCHE="TIRAMIsU" resuelto por alias del parser → LIMPIO funcional.

---

## F2 — ENGINE confirmados

| Sabor | ab DIA→NOCHE | Cerr abierta | Consumo implícito | Veredicto |
|-------|-------------|-------------|-------------------|-----------|
| CHOCOLATE | 1870→6415 (+4545) | 5940 | 1870+5940−280=7530→6415=1115g | ✓ |
| SAMBAYON AMORES | 835→6450 (+5615) | 6505 | 835+6505−280=7060→6450=610g | ✓ |

2 aperturas confirmadas. **2 latas = 560g.**

---

## F4 — Escalados (2 casos)

### COOKIES — PF1:DIGIT_TYPO
- Señales: cerr DIA=6715, cerr NOCHE=5705 (Δ=1010g), |5705−(6715−1000)|=10g
- H1: operador escribió 5705 en vez de 6705 (error de dígito en millar)
- H2: ninguna plausible (una lata no pierde 1010g sin abrirse, ab baja solo 120g)
- Corrección: cerr NOCHE = 6705. NOCHE corr: 2750+6705=9455
- Impacto: MASA −1000g
- Conf: 0.90
- Delta: 1130 → 130 = −1000g

### AMERICANA — PF7:AB_IMP
- Señales: raw=-2450, ab DIA=1650 cae desde 4365 (ord.44), ab NOCHE=4110 se recupera, sin apertura
- H1: ab DIA=1650 es error de registro. Valor correcto ≈ 4365 (forward desde ord.44, overnight sin ventas)
- H2: ninguna plausible (no hay mecanismo físico para caída de 2715g sin apertura ni consumo)
- Corrección: ab DIA = 4365. DIA corr: 4365+6370=10735
- Impacto: MASA +2715g
- Conf: 0.85
- Delta: −2450 → 265 = +2715g

---

## Tabla final

| Sabor | Nivel | Venta stock | Latas | Conf |
|-------|-------|-------------|-------|------|
| AMARGO | L | 510 | 0 | 1.00 |
| **AMERICANA** | **PF7** | **265** | 0 | 0.85 |
| ANANA | L | 235 | 0 | 1.00 |
| B, SPLIT | L | 265 | 0 | 1.00 |
| BLANCO | L | 20 | 0 | 1.00 |
| BOSQUE | L | 590 | 0 | 1.00 |
| CABSHA | L | 190 | 0 | 1.00 |
| CADBURY | L | 315 | 0 | 1.00 |
| CEREZA | L | 290 | 0 | 1.00 |
| CH AMORES | L | 345 | 0 | 1.00 |
| CH C/ALM | L | 230 | 0 | 1.00 |
| CHOCOLATE | E | 1,395 | 1 | 1.00 |
| CHOCOLATE DUBAI | L | 455 | 0 | 1.00 |
| CIELO | L | 380 | 0 | 1.00 |
| COCO | L | 75 | 0 | 1.00 |
| **COOKIES** | **PF1** | **130** | 0 | 0.90 |
| D. GRANIZADO | L | 745 | 0 | 1.00 |
| DOS CORAZONES | L | 360 | 0 | 1.00 |
| DULCE AMORES | L | 435 | 0 | 1.00 |
| DULCE C/NUEZ | L | 0 | 0 | 1.00 |
| DULCE D LECHE | L | 440 | 0 | 1.00 |
| DURAZNO | L | 420 | 0 | 1.00 |
| FERRERO | L | 250 | 0 | 1.00 |
| FLAN | L | 675 | 0 | 1.00 |
| FRAMBUEZA | L | 145 | 0 | 1.00 |
| FRANUI | L | 50 | 0 | 1.00 |
| FRUTILLA AGUA | L | 745 | 0 | 1.00 |
| FRUTILLA CREMA | L | 1,090 | 0 | 1.00 |
| FRUTILLA REINA | L | 385 | 0 | 1.00 |
| GRANIZADO | L | 385 | 0 | 1.00 |
| IRLANDESA | L | 850 | 0 | 1.00 |
| KINDER | L | 300 | 0 | 1.00 |
| KITKAT | L | 635 | 0 | 1.00 |
| LEMON PIE | L | 235 | 0 | 1.00 |
| LIMON | L | 910 | 0 | 1.00 |
| MANTECOL | L | 315 | 0 | 1.00 |
| MANZANA | L | 505 | 0 | 1.00 |
| MARROC | L | 260 | 0 | 1.00 |
| MASCARPONE | L | 560 | 0 | 1.00 |
| MENTA | L | 425 | 0 | 1.00 |
| MIX DE FRUTA | L | 5 | 0 | 1.00 |
| MOUSSE LIMON | L | 5 | 0 | 1.00 |
| NUTE | L | 85 | 0 | 1.00 |
| PISTACHO | L | 455 | 0 | 1.00 |
| RUSA | L | 5 | 0 | 1.00 |
| SAMBAYON | L | 675 | 0 | 1.00 |
| SAMBAYON AMORES | E | 890 | 1 | 1.00 |
| SUPER | L | 175 | 0 | 1.00 |
| TIRAMIZU | L | 95 | 0 | 1.00 |
| TRAMONTANA | L | 835 | 0 | 1.00 |
| VAINILLA | L | 270 | 0 | 1.00 |

---

## Totales

Todas las correcciones tienen conf ≥0.85 → conservador = estimado.

| Componente | Valor |
|------------|-------|
| Raw (51 sabores) | 18,590g |
| Corrección COOKIES (PF1) | −1,000g |
| Corrección AMERICANA (PF7) | +2,715g |
| **Venta stock (corregido)** | **20,305g** |
| Latas: 2 × 280 | −560g |
| VDP (engine) | 0g |
| **Total** | **19,745g** |

**Referencia validada**: venta=20,305, latas=560, VDP=0, total=19,745.

---

## Comparación contra referencia validada

| Métrica | Runtime | Validado | Δ |
|---------|---------|----------|---|
| Venta stock | 20,305 | 20,305 | **0g** |
| Latas | 2 (560g) | 2 (560g) | **0** |
| VDP | 0 | 0 | **0** |
| Total | 19,745 | 19,745 | **0g** |

**Convergencia total. Δ=0g en todas las métricas.**

---

## Observaciones

### Resolución de nombre por parser
TIRAMIZU/TIRAMIsU resuelto como alias en el parser → no requiere PF8 en la auditoría. Si el parser no lo resolviera, sería un caso PF8:NOMBRE_INCONSISTENTE con los mismos valores numéricos.

### Scorecard

```
Total sabores:         51
Aciertos completos:    51 (100%)
Falsos abiertos:        0
Sobrecorrecciones:      0
Delta total sabores:    0g
```

D25 es un día limpio. 2 correcciones mecánicas (PF1 dígito + PF7 abierta imposible) + 2 aperturas directas. Sin casos abiertos.
