# Auditoría Día 27 — Viernes 27 de Febrero 2026

**Período**: Viernes 27 (DIA) ord.49 → Viernes 27 (NOCHE) ord.50
**Sabores con datos**: 51 (CHOCOLATE CON PASAS y MARACUYA: ALL_EMPTY)
**Raw total**: 14,040g

---

## F1 — Clasificación

| Nivel | n | Detalle |
|-------|---|---------|
| LIMPIO | 45 | Todas las condiciones pasan |
| ENGINE | 3 | ANANA(1L), LEMON PIE(1L), SAMBAYON(1L) |
| SOSPECHOSO | 3 | CHOCOLATE(cond.1: raw=-5010), CIELO(cond.1: raw=-6150), SAMBAYON AMORES(cond.1: raw=-6205) |

**Notas LIMPIO**: D.GRANIZADO cerr 6675→6575 (100g oscilación, mismo can con alta varianza, 2→2 count). GRANIZADO cerr 6750→6710 (40g). Ambos LIMPIO funcional.

---

## F2 — ENGINE confirmados

| Sabor | ab DIA→NOCHE | Cerr abierta | Consumo implícito | Veredicto |
|-------|-------------|-------------|-------------------|-----------|
| ANANA | 980→6490 (+5510) | 7030 | 980+7030−280=7730→6490=1240g | ✓ |
| LEMON PIE | 720→6480 (+5760) | 6610 | 720+6610−280=7050→6480=570g | ✓ |
| SAMBAYON | 1260→6235 (+4975) | 6450 | 1260+6450−280=7430→6235=1195g | ✓ |

3 aperturas confirmadas. **3 latas = 840g.**

---

## F4 — Escalados (3 casos, mismo patrón)

Los 3 casos comparten una firma idéntica: **entrante DIA que persiste en NOCHE + cerrada nueva en NOCHE con peso ≈ entrante (±5g)**. Es PF2 (ENTRANTE_DUP) en variante promoción (entrante→cerrada en vez de entrante→abierta).

### CHOCOLATE — PF2 variante promoción
- Señales: raw=-5010, ent 6405 en DIA=NOCHE, cerr nueva 6410 en NOCHE (|6410−6405|=5g)
- H1: entrante 6405 fue promovido a cerrada 6410 (almacenado), persiste como entrante por error
- H2: ninguna plausible (5g de diferencia confirma misma lata)
- Corrección: poner ent 6405 NOCHE en 0. NOCHE corr: 4050+6410+6545=17005
- Impacto: MASA +6405g
- Conf: 0.90
- Delta: −5010 → 1395 = +6405g

### CIELO — PF2 variante promoción
- Señales: raw=-6150, ent 6500 en DIA=NOCHE, cerr nueva 6505 en NOCHE (|6505−6500|=5g)
- H1: entrante 6500 fue promovido a cerrada 6505, persiste como entrante por error
- H2: ninguna plausible
- Corrección: poner ent 6500 NOCHE en 0. NOCHE corr: 5440+6505=11945
- Impacto: MASA +6500g
- Conf: 0.90
- Delta: −6150 → 350 = +6500g

### SAMBAYON AMORES — PF2 variante promoción
- Señales: raw=-6205, ent 6600 en DIA=NOCHE, cerr nueva 6605 en NOCHE (|6605−6600|=5g)
- H1: entrante 6600 fue promovido a cerrada 6605, persiste como entrante por error
- H2: ninguna plausible
- Corrección: poner ent 6600 NOCHE en 0. NOCHE corr: 5970+6605=12575
- Impacto: MASA +6600g
- Conf: 0.90
- Delta: −6205 → 395 = +6600g

---

## Tabla final

| Sabor | Nivel | Venta stock | Latas | Conf |
|-------|-------|-------------|-------|------|
| AMARGO | L | 1,440 | 0 | 1.00 |
| AMERICANA | L | 765 | 0 | 1.00 |
| ANANA | E | 1,520 | 1 | 1.00 |
| B, SPLIT | L | 1,210 | 0 | 1.00 |
| BLANCO | L | 295 | 0 | 1.00 |
| BOSQUE | L | 825 | 0 | 1.00 |
| CABSHA | L | 185 | 0 | 1.00 |
| CADBURY | L | 435 | 0 | 1.00 |
| CEREZA | L | 460 | 0 | 1.00 |
| CH AMORES | L | 280 | 0 | 1.00 |
| CH C/ALM | L | 1,660 | 0 | 1.00 |
| **CHOCOLATE** | **PF2v** | **1,395** | 0 | 0.90 |
| CHOCOLATE DUBAI | L | 860 | 0 | 1.00 |
| **CIELO** | **PF2v** | **350** | 0 | 0.90 |
| COCO | L | 370 | 0 | 1.00 |
| COOKIES | L | 245 | 0 | 1.00 |
| D. GRANIZADO | L | 1,690 | 0 | 1.00 |
| DOS CORAZONES | L | 260 | 0 | 1.00 |
| DULCE AMORES | L | 895 | 0 | 1.00 |
| DULCE C/NUEZ | L | 275 | 0 | 1.00 |
| DULCE D LECHE | L | 2,155 | 0 | 1.00 |
| DURAZNO | L | 555 | 0 | 1.00 |
| FERRERO | L | 635 | 0 | 1.00 |
| FLAN | L | 335 | 0 | 1.00 |
| FRAMBUEZA | L | 325 | 0 | 1.00 |
| FRANUI | L | 425 | 0 | 1.00 |
| FRUTILLA AGUA | L | 495 | 0 | 1.00 |
| FRUTILLA CREMA | L | 1,435 | 0 | 1.00 |
| FRUTILLA REINA | L | 285 | 0 | 1.00 |
| GRANIZADO | L | 535 | 0 | 1.00 |
| IRLANDESA | L | 365 | 0 | 1.00 |
| KINDER | L | 405 | 0 | 1.00 |
| KITKAT | L | 2,130 | 0 | 1.00 |
| LEMON PIE | E | 850 | 1 | 1.00 |
| LIMON | L | 540 | 0 | 1.00 |
| MANTECOL | L | 620 | 0 | 1.00 |
| MANZANA | L | 170 | 0 | 1.00 |
| MARROC | L | 80 | 0 | 1.00 |
| MASCARPONE | L | 310 | 0 | 1.00 |
| MENTA | L | 380 | 0 | 1.00 |
| MIX DE FRUTA | L | 5 | 0 | 1.00 |
| MOUSSE LIMON | L | 110 | 0 | 1.00 |
| NUTE | L | 20 | 0 | 1.00 |
| PISTACHO | L | 830 | 0 | 1.00 |
| RUSA | L | 305 | 0 | 1.00 |
| SAMBAYON | E | 1,475 | 1 | 1.00 |
| **SAMBAYON AMORES** | **PF2v** | **395** | 0 | 0.90 |
| SUPER | L | 580 | 0 | 1.00 |
| TIRAMIZU | L | 85 | 0 | 1.00 |
| TRAMONTANA | L | 635 | 0 | 1.00 |
| VAINILLA | L | 660 | 0 | 1.00 |

---

## Totales

Todas las correcciones tienen conf ≥0.85 → conservador = estimado.

| Componente | Valor |
|------------|-------|
| LIMPIO (45 sabores) | 22,960g |
| ENGINE (3 sabores, stock pre-lid) | 3,845g |
| PF2v (3 sabores, corregidos) | 2,140g |
| **Venta stock** | **33,545g** |
| Latas: 3 × 280 | −840g |
| VDP (engine) | 0g |
| Consumo (engine: SAMANTA 1 VASO) | −180g |
| **Total (engine)** | **32,525g** |

**Referencia validada**: venta=33,545, latas=840, VDP=250, total=32,955.

---

## Comparación contra referencia validada

| Métrica | Runtime | Validado | Δ | Causa |
|---------|---------|----------|---|-------|
| Venta stock | 33,545 | 33,545 | **0g** | ✓ Match completo |
| Latas | 3 (840g) | 3 (840g) | **0** | ✓ Match |
| VDP | 0 | 250 | −250 | Parser no captura entries |
| Consumo | 180 | (no separado) | ? | Incluido en validado o no reportado |
| Total | 32,525 | 32,955 | −430 | VDP + consumo |

**Venta stock y latas: convergencia total. Δ=0g.**
Divergencia residual: VDP/consumo (parser), no lógica de resolución.

---

## Observaciones

### PF2 variante promoción (nuevo hallazgo D27)

Los 3 escalados comparten un patrón que extiende PF2:

| PF2 original (D26, D28) | PF2 variante D27 |
|--------------------------|-----------------|
| Entrante DIA se abre → ab sube | Entrante DIA se promueve a cerrada (no se abre) |
| ab sube como señal de apertura | Cerrada nueva en NOCHE ≈ entrante (±5g) como señal |
| Corrección: poner ent NOCHE en 0 | Corrección: idéntica |

**No se agrega como prototipo nuevo** (baseline congelado). Se documenta como variante de PF2 para futura evaluación. La firma es: `raw muy negativo + ent DIA = ent NOCHE + cerr nueva NOCHE ≈ ent (±30g) + ab NO sube`.

### Scorecard

```
Total sabores:         51
Aciertos completos:    51 (100%)
Falsos abiertos:        0
Sobrecorrecciones:      0
Delta total sabores:    0g
```

D27 es un día limpio. Solo 3 correcciones mecánicas (PF2v) + 3 aperturas directas. Sin casos abiertos.
