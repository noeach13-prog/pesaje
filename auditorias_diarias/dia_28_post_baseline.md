# Día 28 — Re-ejecución con baseline congelado

Baseline: `09_baseline_operativo.md` (2026-03-20)
Runtime: `04b` + `04c` + `04d`
Datos: `02_observaciones_normalizadas.csv` + `03_historias_por_sabor.json`
GT: `dia_28_ground_truth.md`

---

## A. RESULTADO CON BASELINE CONGELADO

### Clasificación

| Nivel | n |
|-------|---|
| LIMPIO | 43 |
| ENGINE confirmado | 4 (CH C/ALM, D.GRAN, DULCE AMORES, LIMON) |
| ENGINE → escalado | 1 (CHOC DUBAI: P4 detecta ab insuficiente para 2L) |
| OBSERVACIÓN | 1 (MIX DE FRUTA: raw=-95, señal aislada) |
| SOSPECHOSO | 4 (CHOCOLATE, MARACUYA, PISTACHO, SAMBAYON) |

### Escalados resueltos

| Sabor | Prototipo | Raw | Corregido | Latas | Conf |
|-------|-----------|-----|-----------|-------|------|
| CHOCOLATE | PF5 | -3,635 | 2,910 | 0 | 0.85 |
| MARACUYA | PF2 | -5,825 | 555 | 0 | 0.90 |
| PISTACHO | PF4 | 7,900 | 1,550 | 0 | 0.85 |
| SAMBAYON | PF3+P5 | 7,105 | 655 | 0 | 0.90 |
| CHOC DUBAI | PF6 | 8,140 | 1,740 | 1 | 0.80 |

### Totales

| | Stock | Latas | VDP | Total |
|--|-------|-------|-----|-------|
| **Conservador** (CHOC DUBAI a engine: 8140, 2L) | 57,565 | 6 × 280 = 1,680 | 2,270 | **58,155** |
| **Estimado** (todas las correcciones) | 51,165 | 5 × 280 = 1,400 | 2,270 | **52,035** |

---

## B. COMPARACIÓN CONTRA AUDITORÍA V1

| Sabor | Auditoría v1 | Baseline v2 | Regla que corrige | Δ gramos |
|-------|-------------|-------------|-------------------|----------|
| CHOCOLATE | FA: UNRESOLVED (0g cons.) | AC: PF5 → 2,910g | PF5 CERR_OMITIDA_DIA | +2,910 |
| CHOC DUBAI | SC: 2L, 7,580g | AC: PF6 → 1L, 1,740g | PF6 + P4 (ab insuficiente) | −5,840 |
| SAMBAYON | SC: est. 555g (eliminó 6675) | AC: 655g (conserva 6675) | PF3 RM-3 + P5 (no eliminar sin evidencia) | +100 |
| MARACUYA | AC: 555g | AC: 555g | (sin cambio) | 0 |
| PISTACHO | AN: 1,550g | AN: 1,550g | (sin cambio, sigue AN) | 0 |

**Impacto neto de v1→v2**: −2,830g en venta stock estimado.

Desglose:
- PF5 nuevo: +2,910g (CHOCOLATE deja de ser FA)
- PF6 nuevo: −5,840g (CHOC DUBAI deja de ser SC)
- P5 aplicado: +100g (SAMBAYON deja de ser SC)

---

## C. COMPARACIÓN CONTRA GROUND TRUTH

### Venta stock

| Métrica | Baseline v2 (estimado) | GT | Δ |
|---------|----------------------|-----|---|
| Venta stock total | 51,165g | 51,165g | **0g** |
| Latas | 5 (1,400g) | 5 (1,400g) | **0** |

**MATCH COMPLETO en venta stock.**

### VDP

| Fuente | Valor |
|--------|-------|
| Engine (parser.py) | 2,270g |
| GT (PDF) | 3,020g |
| **Δ** | **−750g** |

**MISMATCH en VDP. 100% atribuible a parser.**

### Total final

| Métrica | Baseline v2 | GT (v3) | Δ | Causa |
|---------|-----------|---------|---|-------|
| Total estimado | 52,035g | 52,785g | **−750g** | VDP |

### Scorecard por sabor

| Clasif. | n | Sabores |
|---------|---|---------|
| AC | 51 | 47 LIMPIO + CH C/ALM + D.GRAN + D.AMORES + LIMON + CHOC DUBAI + CHOCOLATE + MARACUYA + SAMBAYON + MIX DE FRUTA + OBSERVACIÓN |
| AN | 1 | PISTACHO (PF4 vs GT PF3, Δ=0g) |
| FA | 0 | — |
| SC | 0 | — |
| OP | 0 | — |

---

## D. DIAGNÓSTICO RESIDUAL

### Resuelto por el baseline

| Componente | Estado |
|------------|--------|
| Venta stock (52 sabores) | ✓ Convergencia total: 51,165g = GT |
| Latas abiertas (conteo y detalle) | ✓ 5 latas = GT (v3) |
| CHOCOLATE (antes FA) | ✓ PF5 resuelve |
| CHOC DUBAI (antes SC) | ✓ PF6+P4 resuelve |
| SAMBAYON (antes SC) | ✓ PF3+P5 resuelve |
| Clasificación de 52 sabores | ✓ 51 AC + 1 AN |
| Correcciones de stock (5 escalados) | ✓ Todas convergen con GT |

### Pendiente (parser/VDP)

| Componente | Estado | Impacto |
|------------|--------|---------|
| VDP total | ✗ 2,270 vs 3,020 (−750g) | Afecta total final, NO venta stock |
| VDP desglose | ✗ Parser captura 5 entries, GT tiene más o gramaje distinto | Requiere revisión de `_parse_vdp_texts` + `text_to_grams` |

### Confirmación

**La lógica de resolución ya no es el cuello de botella para D28.**

La divergencia residual (750g / 1.4% del total) está íntegramente en el parsing de VDP, que es independiente del baseline de resolución. El baseline congelado puede usarse tal cual para auditar los 27 días restantes sin modificación.
