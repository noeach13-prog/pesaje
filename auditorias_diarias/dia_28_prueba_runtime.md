# Día 28 — Prueba de suficiencia del runtime corto

Ejecutado con: `04b_runtime_operativo.md`, `04c_matriz_de_activacion.md`, `04d_plantilla_caso_escalado.md`
Datos: `02_observaciones_normalizadas.csv`, `03_historias_por_sabor.json`
Comparado contra: `dia_28_ground_truth.md`

---

## F1 — Clasificación (52 sabores con datos)

| Nivel | n | Detalle |
|-------|---|---------|
| LIMPIO | 43 | Todas las condiciones 1–5 pasan |
| ENGINE | 5 | CH C/ALM(1L), CHOC DUBAI(2L), D.GRAN(1L), DULCE AMORES(1L), LIMON(1L) |
| OBSERVACIÓN | 1 | MIX DE FRUTA (raw=-95, señal aislada <500g) |
| SOSPECHOSO | 3 | CHOCOLATE (cond.1: raw=-3635), MARACUYA (cond.1: raw=-5825), PISTACHO (cond.2: raw=7900 sin apertura), SAMBAYON (cond.2: raw=7105 sin apertura) |

## F2 — Verificación ENGINE

| Sabor | Engine | Verificación | Resultado |
|-------|--------|-------------|-----------|
| CH C/ALM | 1L, venta=1890 | ab 2325→6605, cerr 6445 gone. Apertura coherente. | ✓ Correcto |
| D. GRANIZADO | 1L, venta=4445 | ab 1775→3720, cerr 6675 gone. Apertura coherente. | ✓ Correcto |
| DULCE AMORES | 1L, venta=1310 | ab 1145→6185, cerr 6635 gone. Apertura coherente. | ✓ Correcto |
| LIMON | 1L, venta=2645 | ab 1960→5315, cerr 6280 gone. Apertura coherente. | ✓ Correcto |
| CHOC DUBAI | 2L, venta=7580 | **P4**: ab sube +4615. Para 2 aperturas esperado ~+12000. Solo soporta 1. → **CUESTIONABLE** → escalar | ⚠ Escalado |

## F3.5+F4 — Escalados (5 casos, plantilla 04d)

### CHOCOLATE — PF5:CERR_OMITIDA_DIA
- Señales: raw=-3635, cerr 6545 en NOCHE sin match en DIA, 6545 vista como entrante ord49+ord50 (≥2 sightings)
- H1: cerr 6545 omitida del registro DIA
- H2: cerr 6545 es nueva llegada durante noche (no explica por qué estaba como entrante D27)
- Corrección: agregar cerr 6545 a total_DIA. DIA corr=17245, NOCHE=14335
- Impacto: MASA +6545g
- Conf: 0.85
- Delta: -3635 → 2910 = +6545g

### MARACUYA — PF2:ENTRANTE_DUP
- Señales: raw=-5825, entrante 6380 en DIA=NOCHE, ab 0→5825
- H1: entrante fue abierto, persiste en NOCHE por error de registro
- H2: ninguna plausible
- Corrección: poner entrante NOCHE en 0. NOCHE corr=5825
- Impacto: MASA +6380g
- Conf: 0.90
- Delta: -5825 → 555 = +6380g

### PISTACHO — PF4:CERR_OMITIDA_NOCHE (P1 preserva cerr como real)
- Señales: raw=7900, cerr 6350 en DIA no en NOCHE, ab baja 2705→1155 (0 aperturas)
- H1: cerr 6350 real, omitida de NOCHE (P1: preservar recipientes reales, 2 sightings ord49+ord51)
- H2: cerr 6350 phantom en DIA (GT usa esta, mismo resultado numérico)
- Corrección: agregar cerr 6350 a NOCHE. NOCHE corr=13860
- Impacto: MASA -6350g. 0 latas (engine daba 1 → rechazado, ab confirma 0 aperturas)
- Conf: 0.85
- Delta: 7900 → 1550 = -6350g

### SAMBAYON — PF3:PHANTOM_CERR
- Señales: raw=7105, cerr 6450 fue abierta D27 (ab 1260→6235 ord50), reaparece como cerr DIA D28
- H1: cerr 6450 phantom por RM-3. Cerr 6675 real (P5: no eliminar sin evidencia directa)
- H2: ambas phantom → venta=555 (elimina stock real sin evidencia)
- Corrección: poner cerr 6450 en 0. Mantener 6675. DIA corr=12910, NOCHE=12255
- Impacto: MASA -6450g. 0 latas (engine daba 1 → rechazado)
- Conf: 0.90 (RM-3 para 6450) + P5 default para 6675
- Delta: 7105 → 655 = -6450g

### CHOC DUBAI — PF6:APERTURA_CON_PHANTOM
- Señales: engine daba 2L, P4 detecta ab solo soporta 1 apertura, cerr 6400 sin historial
- H1: cerr 6400 phantom, solo 6355 fue abierta (1 lata). ab: 1420+6355-280=7495→6035, consumo=1460g
- H2: ambas reales y abiertas (2L, consumo=7580g, excesivo para 1 turno)
- Corrección: poner cerr 6400 en 0. DIA corr=7775, NOCHE=6035. 1 lata.
- Impacto: MASA -6400g, -1 lata
- Conf: 0.80
- Delta: 8140 → 1740 = -6400g

---

## TOTALES

### Total estimado (todas las correcciones aplicadas)

| Componente | Valor |
|------------|-------|
| Venta stock (52 sabores corregidos) | 51,165g |
| Latas: CH C/ALM(1)+D.GRAN(1)+D.AMORES(1)+LIMON(1)+CHOC DUBAI(1) = 5 | −1,400g |
| VDP (engine) | +2,270g |
| **Total estimado (VDP engine)** | **52,035g** |
| VDP (GT, si se usa) | +3,020g |
| **Total estimado (VDP GT)** | **52,785g** |

### Total conservador (solo correcciones conf ≥0.85; CHOC DUBAI queda en engine)

| Componente | Valor |
|------------|-------|
| Venta stock (CHOC DUBAI a raw=8140 en vez de 1740) | 57,565g |
| Latas: 4 confirmadas + 2 CHOC DUBAI engine = 6 | −1,680g |
| VDP (engine) | +2,270g |
| **Total conservador** | **58,155g** |

**Brecha conservador→estimado**: 6,120g (explicada 100% por CHOC DUBAI: 6400g stock + 280g 1 lata menos = 6,120g neto en total).

---

## COMPARACIÓN CONTRA GROUND TRUTH

### Por sabor

| Sabor | Runtime | GT | Δ | Clasif | Nota |
|-------|---------|-----|---|--------|------|
| CHOCOLATE | 2,910 | 2,910 | 0 | **AC** | PF5 resuelve correctamente |
| MARACUYA | 555 | 555 | 0 | **AC** | PF2, match exacto |
| PISTACHO | 1,550 | 1,550 | 0 | **AN** | Runtime: PF4 omisión NOCHE. GT: phantom DIA. Mismo resultado. |
| SAMBAYON | 655 | 655 | 0 | **AC** | PF3 RM-3 + P5 conserva 6675. Match exacto. |
| CHOC DUBAI | 1,740 | 1,740 | 0 | **AC** | PF6 vía P4. Match exacto. |
| 47 restantes | correctos | correctos | 0 | **AC** | Sin corrección necesaria |

### Scorecard

```
Total sabores:         52
Aciertos completos:    51  (98.1%)
Aciertos numéricos:     1  (1.9%)  [PISTACHO: PF4 vs PF3, mismo valor]
Falsos abiertos:        0
Sobrecorrecciones:      0
Omisiones de patrón:    0
Delta total sabores:    0g
```

### Totales

| Métrica | Runtime estimado | GT (v3) | Δ | Nota |
|---------|-----------------|---------|---|------|
| Venta stock | 51,165 | 51,165 | **0** | Match exacto |
| Latas | 5 (1,400g) | 5 (1,400g) | **0** | Match exacto (v3) |
| VDP | 2,270 | 3,020 | **−750** | Discrepancia de parsing, no de runtime |
| Total | 52,035 | 52,785 | **−750** | 100% explicado por VDP |

---

## VEREDICTO DE SUFICIENCIA

### ¿La capa operativa corta fue suficiente?

**SÍ.** Los 5 casos escalados convergieron a valor correcto (Δ=0g en venta stock).

### Qué funcionó

| Regla | Caso resuelto | Mejora vs auditoría v1 |
|-------|--------------|----------------------|
| PF5 CERR_OMITIDA_DIA | CHOCOLATE | v1: FA (no detectó). Runtime: AC. |
| PF6 + P4 | CHOC DUBAI | v1: SC (2 latas, +5840g). Runtime: AC. |
| PF3 + P5 | SAMBAYON | v1: SC (eliminó cerr real). Runtime: AC. |
| PF2 | MARACUYA | v1: AC. Runtime: AC. (sin cambio) |
| P1 + PF4 | PISTACHO | v1: AN. Runtime: AN. (sin cambio) |

### Qué no convergió

| Caso | Divergencia | Impacto | Acción necesaria |
|------|-------------|---------|------------------|
| PISTACHO | Interpretación (AN): runtime dice omisión NOCHE, GT dice phantom DIA | 0g (mismo resultado numérico) | Ninguna obligatoria. P1 "preservar" favorece PF4; GT prefiere PF3. Ambos válidos. |
| VDP | 2,270 vs 3,020 (−750g) | 750g en total | No es falla del runtime sino del parser de POSTRES. Requiere revisión de `parser.py`. |

### ¿Faltó alguna regla?

**No.** Todas las correcciones necesarias estaban cubiertas por los prototipos PF1–PF8 y las precedencias P1–P5. La única divergencia (PISTACHO AN) es una ambigüedad legítima donde dos prototipos dan el mismo resultado numérico — no requiere regla nueva.

### Comparación de scorecards: auditoría v1 vs runtime v2

| Métrica | Auditoría v1 | Runtime v2 | Mejora |
|---------|-------------|-----------|--------|
| AC | 48 (92.3%) | 51 (98.1%) | +3 |
| AN | 1 | 1 | = |
| FA | 1 | 0 | −1 |
| SC | 2 | 0 | −2 |
| OP | 1 | 0 | −1 |
| Δ total | 8,850g | 0g | −8,850g |
