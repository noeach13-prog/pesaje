# Auditoría Día 25 — Miércoles 25 de Febrero 2026 (v3)

**Método**: Arquitectura v3 por capas (04_sistema_de_escalado_v3_draft.md)
**Fuente única**: Febrero San Martin 2026 (1).xlsx — Hojas "Miércoles 25 (DIA)" y "Miércoles 25 (NOCHE)"
**Contexto temporal**: Hojas D22-D24, D26-D27 del mismo Excel para timeline
**Sabores con datos**: 51 activos (MARACUYA=vacío ambos turnos, CHOCOLATE CON PASAS=vacío ambos turnos → excluidos)

---

## CAPA 1 — PARSER: Datos crudos

51 sabores con datos. Sin celiaca registrada en ningún sabor.
MARACUYA DIA: ab=0, cerr=[], ent=[]. NOCHE: EMPTY. → Excluido (sin stock).
CHOCOLATE CON PASAS: EMPTY ambos. → Excluido.

**Observación de nombres**: DIA registra "TIRAMIZU", NOCHE registra "TIRAMIsU". Es el mismo sabor (confirmado por posición en planilla, turnos adyacentes usan "TIRAMIZU", nunca coexisten). Se combinan como un solo período.

VDP DIA: 0. VDP NOCHE: 0. Consumo interno DIA: "ANA — 3 MILKSHAKE" (sin peso numérico → 0g impacto en stock).

---

## CAPA 2 — CONTRATO CONTABLE: raw_sold

```
venta_stock = total_A + new_entrantes_B - total_B - ajuste_latas
total = abierta + celiaca + sum(cerradas) + sum(entrantes)
ajuste_latas = max(0, n_cerradas_A - n_cerradas_B) × 280
```

VDP = 0g. Consumo interno = 0g.

---

## CAPA 3 — MOTOR LOCAL: Screening + clasificación

### 3.1 Condiciones de screening

- C1: `raw_sold >= -50g` → si falla → SOSPECHOSO
- C2: `raw_sold < 5000g` o apertura confirmada → si falla → SOSPECHOSO
- C3: `ab_N <= ab_D + 20g` o apertura confirmada → si falla → SOSPECHOSO
- C4: Toda cerrada en solo 1 turno tiene match ±30g → si falla → SOSPECHOSO

### Sabores LIMPIO (43) — pasan todas las condiciones

| Sabor | ab DIA | ab NOCHE | cerr DIA | cerr NOCHE | raw_sold | Cerr match |
|-------|--------|----------|----------|------------|----------|------------|
| AMARGO | 6410 | 5890 | 6655 | 6665 | 510 | 10g ✓ |
| ANANA | 1650 | 1405 | 7030 | 7040 | 235 | 10g ✓ |
| B, SPLIT | 6060 | 5805 | 6405,6360 | 6395,6360 | 265 | 10g,0g ✓ |
| BLANCO | 5820 | 5800 | — | — | 20 | — |
| BOSQUE | 4045 | 3465 | 6580 | 6570 | 590 | 10g ✓ |
| CABSHA | 3805 | 3615 | — | — | 190 | — |
| CADBURY | 6365 | 6050 | 6355 | 6355 | 315 | 0g ✓ |
| CEREZA | 6205 | 5915 | — | — | 290 | — |
| CH AMORES | 5755 | 5415 | 6395 | 6390 | 345 | 5g ✓ |
| CH C/ALM | 5435 | 5210 | 6530,6445 | 6445,6525 | 230 | 5g,0g ✓ |
| CHOCOLATE DUBAI | 3445 | 2990 | 6355 | 6355 | 455 | 0g ✓ |
| CIELO | 6330 | 5950 | — | — | 380 | — |
| COCO | 5060 | 4985 | — | — | 75 | — |
| D. GRANIZADO | 4995 | 4245 | 6575,6605 | 6575,6610 | 745 | 0g,5g ✓ |
| DOS CORAZONES | 5800 | 5440 | — | — | 360 | — |
| DULCE C/NUEZ | 4390 | 4390 | — | — | 0 | — |
| DULCE D LECHE | 1905 | 1465 | 6690,6675 | 6690,6675 | 440 | 0g,0g ✓ |
| DURAZNO | 6595 | 6175 | — | — | 420 | — |
| FERRERO | 2300 | 2055 | 6365,6530 | 6530,6360 | 250 | 5g,0g ✓ |
| FLAN | 4190 | 3515 | — | — | 675 | — |
| FRAMBUEZA | 4585 | 4440 | — | — | 145 | — |
| FRANUI | 6090 | 6040 | — | — | 50 | — |
| FRUTILLA AGUA | 7425 | 6680 | — | — | 745 | — |
| FRUTILLA CREMA | 7035 | 5955 | 6565 | 6555 | 1,090 | 10g ✓ |
| FRUTILLA REINA | 5455 | 5070 | 6575 | 6575 | 385 | 0g ✓ |
| IRLANDESA | 4085 | 3235 | 6605 | 6605 | 850 | 0g ✓ |
| KINDER | 4480 | 4180 | — | — | 300 | — |
| KITKAT | 4630 | 4015 | 6400 | 6380 | 635 | 20g ✓ |
| LEMON PIE | 1335 | 1130 | 6645 | 6615 | 235 | 30g ✓ (límite) |
| LIMON | 4080 | 3185 | 6280 | 6265 | 910 | 15g ✓ |
| MANTECOL | 5265 | 4950 | — | — | 315 | — |
| MANZANA | 3590 | 3085 | — | — | 505 | — |
| MARROC | 5215 | 4965 | 6840 | 6830 | 260 | 10g ✓ |
| MASCARPONE | 2415 | 1855 | 6600 | 6600 | 560 | 0g ✓ |
| MENTA | 1470 | 1045 | 6460 | 6460 | 425 | 0g ✓ |
| MIX DE FRUTA | 5340 | 5340 | 6790 | 6785 | 5 | 5g ✓ |
| MOUSSE LIMON | 5000 | 4995 | 6485 | 6485 | 5 | 0g ✓ |
| NUTE | 1490 | 1420 | 6710 | 6695 | 85 | 15g ✓ |
| PISTACHO | 5775 | 5315 | 6350 | 6355 | 455 | 5g ✓ |
| RUSA | 4480 | 4475 | — | — | 5 | — |
| SAMBAYON | 2395 | 1720 | 6450 | 6450 | 675 | 0g ✓ |
| TRAMONTANA | 7055 | 6220 | 6790 | 6790 | 835 | 0g ✓ |
| VAINILLA | 5455 | 5190 | 6465 | 6460 | 270 | 5g ✓ |

**Subtotal LIMPIO**: 14,280g | 0 latas

---

### Sabores ENGINE — apertura confirmada (2)

Criterio v3 Plano 1: ab sube + desaparece fuente + rise coherente.

#### CHOCOLATE — ENGINE

| | DIA | NOCHE |
|--|-----|-------|
| ab | 1870 | 6415 |
| cerr | 5940 | — |
| total | 7810 | 6415 |

- ab sube +4545g ✓
- cerr 5940 desaparece ✓
- Rise coherente: 5940-280=5660 helado disponible. Rise 4545. 5660-4545=1115g venta IT. ✓

**Verificación historial cerr 5940**: D24 DIA: cerr=5940. D24 NOCHE: cerr=5940. D25 DIA: cerr=5940. 3 sightings consistentes. Es un valor inusualmente bajo para cerrada (rango típico 6200-6800) pero estable.

**Nota sobre D23→D24 transición**: La cerrada cambió de 6340 (D23) a 5940 (D24) sin transición documentada. Esto es una anomalía histórica, pero para D25 el valor 5940 lleva 3 sightings estables. Per v3: sin evidencia de digit error con ≥5 sightings al valor alternativo, usar valor observado.

**Resultado**: ENGINE_CONFIRMADO. Venta stock = 1,115g. 1 lata (-280g). Conf 1.00.

#### SAMBAYON AMORES — ENGINE

| | DIA | NOCHE |
|--|-----|-------|
| ab | 835 | 6450 |
| cerr | 6505 | — |
| total | 7340 | 6450 |

- ab sube +5615g ✓
- cerr 6505 desaparece ✓
- Rise coherente: 6505-280=6225 helado. Rise 5615. 6225-5615=610g venta IT. ✓

**Historial cerr**: D22-D24 cerr oscila 6430-6505 (1 can con varianza de pesaje normal).

**Resultado**: ENGINE_CONFIRMADO. Venta stock = 610g. 1 lata (-280g). Conf 1.00.

**Subtotal ENGINE**: 1,725g | 2 latas (-560g)

---

### Sabores OBSERVACIÓN (3) — 1 señal aislada, baja magnitud

| Sabor | ab D→N | cerr D→N | raw | Señal | Magnitud | Decisión |
|-------|--------|----------|-----|-------|----------|----------|
| DULCE AMORES | 3195→2730 | 6640↔6630(10g), 6700↔6740(40g) | 435 | C4: cerr diff 40g | 40g en cerr, raw normal | OBSERVACIÓN |
| SUPER | 4895→4680 | 6730↔6770(40g) | 175 | C4: cerr diff 40g | 40g en cerr, raw normal | OBSERVACIÓN |
| GRANIZADO | 6810→6465 | 6750↔6710(40g) | 385 | C4: cerr diff 40g | 40g en cerr, raw normal | OBSERVACIÓN |

Las 3 cerradas con diff=40g caen en zona 30-75g (varianza ampliada). El raw_sold es razonable en todos los casos. Per v3 Capa 3: "1 señal aislada, baja magnitud (<500g)" → OBSERVACIÓN. Usar raw.

**Subtotal OBSERVACIÓN**: 995g | 0 latas

---

### Sabores RESUELTO_PROTOTIPO (2)

#### TIRAMIZU / TIRAMIsU — PF8 NOMBRE_INCONSISTENTE

| | DIA ("TIRAMIZU") | NOCHE ("TIRAMIsU") |
|--|-------------------|---------------------|
| ab | 4345 | 4255 |
| cerr | 6560 | 6555 |
| total | 10905 | 10810 |

**Verificación PF8**:
- Par nunca coexiste: TIRAMIZU solo en DIA, TIRAMIsU solo en NOCHE ✓
- Pesos coherentes: ab 4345→4255 (-90g normal), cerr 6560↔6555 (5g) ✓
- Historial: D24 DIA/NOCHE, D26 DIA/NOCHE todos dicen "TIRAMIZU". Solo D25 NOCHE dice "TIRAMIsU" ✓
- Evidencia unívoca ✓

**Resultado**: RESUELTO_PROTOTIPO (PF8). Combinar como "TIRAMIZU". Venta = 95g. 0 latas. Conf 0.98.

#### COOKIES — PF1 DIGIT_TYPO

| | DIA | NOCHE |
|--|-----|-------|
| ab | 2870 | 2750 |
| cerr | 6715 | **5705** |
| total | 9585 | 8455 |
| raw | | 1,130 |

**Detección de dígito**: cerr 5705 en NOCHE. Offset +1000 → 6705. ¿Coincide con historial?

**Historial cerr COOKIES (12 turnos)**:

| Turno | Cerr |
|-------|------|
| D22 DIA | 6700 |
| D22 NOCHE | 6700 |
| D23 DIA | 6700 |
| D23 NOCHE | 6700 |
| D24 DIA | 6700 |
| D24 NOCHE | 6700 |
| D25 DIA | 6715 |
| **D25 NOCHE** | **5705** |
| D26 DIA | 6700 |
| D26 NOCHE | 6705 |
| D27 DIA | 6715 |
| D27 NOCHE | 6705 |

- 11 sightings en rango 6700-6715 (1 can estable)
- 1 sighting a 5705 (outlier único)
- 5705+1000 = 6705 → dentro del rango normal ✓

**Verificación PF1**:
- ≥5 sightings al valor de referencia: SÍ (11 sightings a ~6700-6715) ✓
- Offset exacto ±1000: SÍ (5705+1000=6705) ✓
- Turno prev/next normal: D25 DIA cerr=6715, D26 DIA cerr=6700 ✓
- Evidencia unívoca ✓

**Corrección**: cerr NOCHE = 6705 (en lugar de 5705).

| | DIA | NOCHE corregido |
|--|-----|-----------------|
| total | 9585 | 9455 |
| venta | | **130** |

**Resultado**: RESUELTO_PROTOTIPO (PF1). Venta = 130g. 0 latas. Conf 0.95 (11 sightings, offset exacto).
**Delta**: raw 1130 → corregido 130 = **-1,000g**.

**Subtotal PROTOTIPO**: 225g | 0 latas

---

### Sabores ESCALAR_A_CAPA_4 (1 caso)

| # | Sabor | raw_sold | Señales | Categoría v3 |
|---|-------|----------|---------|--------------|
| E1 | AMERICANA | -2,450 | C1: negativa + C3: ab sube +2460 sin fuente | SOSPECHA_COMPUESTA |

**Evaluación para escalado**: ¿Matchea PF7 (AB_IMP) directamente en Capa 3?

PF7 requiere: ab sube + cerradas intactas + forward confirma.
- ab sube: 1650→4110 (+2460g) ✓
- cerradas intactas: 6370↔6360 (10g) ✓
- forward confirma: D25 NOCHE ab=4110 → D26 DIA ab=4115 (+5g, estático) ✓

**¿Escalar a Capa 4?** PF7 criterio: "Forward ambiguo, o cerr parcialmente cambiadas" → NO aplica. Forward es claro.

**PERO**: la magnitud del error es grande (+2715g de corrección) y la determinación del valor correcto de ab tiene un rango. Per v3: "Corrección potencial cambia materialmente la masa del día (>2000g) y la evidencia no es unívoca" → la evidencia ES bastante unívoca (forward+backward convergen), pero la corrección > 2000g obliga a documentar con expediente.

**Decisión**: Escalar a Capa 4 para documentar con expediente ampliado pese a que PF7 aplica, porque la corrección es >2000g.

---

## CAPA 4 — EXPEDIENTE AMPLIADO (1 caso)

### E1 · AMERICANA — Expediente ampliado

**Contexto**: raw=-2450g. DIA: ab=1650, cerr=[6370]. NOCHE: ab=4110, cerr=[6360].
Señales: venta muy negativa + ab sube +2460g sin cerrada desaparecida.

#### Plano 1 — Serie temporal de abierta

| Turno | Ab | Transición | Clasificación |
|-------|----|-----------|---------------|
| D22 DIA | 960 | | |
| D22 NOCHE | 6245 | +5285 | APERTURA_SOPORTADA (cerr 6450 abierta) |
| D23 DIA | 6245 | 0 | ESTÁTICA |
| D23 NOCHE | 5795 | -450 | VENTA_PURA |
| D24 DIA | 5350 | -445 | VENTA_PURA |
| D24 NOCHE | 4365 | -985 | VENTA_PURA |
| **D25 DIA** | **1650** | **-2715** | **¿VENTA_EXTREMA?** |
| D25 NOCHE | 4110 | **+2460** | **AB_SUBE_SIN_FUENTE** |
| D26 DIA | 4115 | +5 | ESTÁTICA |
| D26 NOCHE | 3485 | -630 | VENTA_PURA |
| D27 DIA | 3485 | 0 | ESTÁTICA |
| D27 NOCHE | 2715 | -770 | VENTA_PURA |

**Patrón de ab post-apertura D22**: decrecimiento consistente ~450-985g por turno. Tasa promedio de consumo ≈ 600g/turno.

**Anomalía D25 DIA**: ab cae de 4365 (D24N) a 1650 (D25D) = -2715g en un solo turno. Luego sube a 4110 (D25N) = +2460g SIN que desaparezca ninguna cerrada.

- D24N→D25D: -2715g sería la mayor venta de abierta de TODA la serie (vs promedio ~600g). Posible pero muy improbable.
- D25D→D25N: +2460g con cerr intacta. **IMPOSIBILIDAD FÍSICA**: la ab no puede subir sin fuente. La cerr 6370 sigue presente (→6360, 10g varianza pesaje).

**Marca calidad**: DATO_NORMAL en turnos adyacentes. El error es puntual en D25 DIA.

**Conclusión P1**: ab=1650 es un **dato erróneo**. El valor real de ab en D25 DIA debió estar en el rango [4110, 4365], coherente con la tendencia pre y post.

#### Plano 2 — Multiconjunto de cerradas

**Vista 1 — Delta bruto**:
- cerr_A = {6370}
- cerr_B = {6360}
- No desaparece ninguna cerrada. Diff = 10g (varianza pesaje).

**Vista 2 — Equivalencias plausibles**:
| Cerr A | Cerr B | Dif | Plausibilidad |
|--------|--------|-----|---------------|
| 6370 | 6360 | 10g | exacta (conf 0.99) |

**Historial cerr AMERICANA**: cerr oscila entre 6350-6370 durante 12+ turnos. 1 solo can estable.

**Resolución cerradas**: 1 can, sin cambio. Plano 2 es neutro y estable. ✓

#### Plano 3 — Genealogía de entrantes
Sin entrantes en ningún turno de AMERICANA D25. Neutro.

#### Plano 4 — Celíacas / sublíneas
Sin sublíneas con vínculo operativo real.

#### Hipótesis

- **H1**: ab DIA=1650 es dato erróneo. El valor real era ~4365 (backward from D24 NOCHE, asumiendo venta mínima en apertura de local). Venta = (4365+6370)-(4110+6360) = 10735-10470 = **265g**, 0 latas.
  - P1: elimina AB_SUBE_SIN_FUENTE (imposibilidad física). La serie de ab queda coherente: ...4365→~4365→4110... ✓
  - P2: cerr intacta (1 can estable). ✓
  - P3: neutro.
  - Confianza alta. El valor exacto del ab DIA importa poco: cualquier valor entre 4110 y 4365 da venta entre 10g y 265g.

- **H2**: ab DIA=1650 es correcto. Hubo una venta masiva de 2715g en la apertura, y luego el balde fue rellenado por fuente desconocida.
  - P1: AB_SUBE_SIN_FUENTE → imposibilidad física. ✗
  - No hay mecanismo para que un balde abierto aumente de peso sin apertura de cerrada.
  - **H2 DESCARTADA por violación física.**

#### Convergencia
- H1: P1 (elimina imposibilidad física) + P2 (cerr estable confirma sin apertura) = 2 planos independientes.
- ¿Independientes? Sí: P1 mide abierta, P2 mide cerradas.
- Regla ≥2 planos independientes: **CUMPLE**.

#### Determinación del valor corregido

El valor exacto de ab DIA no se puede determinar con precisión. Pero el resultado final apenas varía:

| ab DIA supuesto | Venta DIA→NOCHE | Rango |
|-----------------|-----------------|-------|
| 4365 (backward = D24N) | 265g | máximo |
| 4237 (midpoint) | 137g | medio |
| 4110 (forward = D25N) | 10g | mínimo |

**Rango de incertidumbre**: 10g a 265g = 255g. **Inmaterial** (<300g).

**Valor elegido**: 4365 (backward reference, convención PF7: forward>backward usa D25N como confirmación, pero D24N como referencia para stock de apertura). Venta = **265g**.

#### Resolución
- **Corrección**: ab DIA = 4365 (backward reference de D24 NOCHE). total_A corregido = 4365+6370 = 10735.
- **Tipo**: RESUELTO_INDIVIDUAL (ab corregida) + RESUELTO_CONJUNTO (resultado robusto en rango 10-265g)
- **Conf**: 0.90 (certeza alta de que 1650 es error; incertidumbre solo en valor exacto, pero rango inmaterial)
- **Delta**: raw -2450 → corregido 265 = **+2,715g**
- **Impacto**: MASA: +2,715g en venta_stock, 0 latas

---

## CAPA 4 — Resumen

| Caso | Sabor | Tipo corrección | raw | Corregido | Δ | Latas | Conf | Tipo resolución |
|------|-------|----------------|-----|-----------|---|-------|------|----------------|
| E1 | AMERICANA | Ab imposible (PF7+expediente) | -2,450 | 265 | +2,715 | 0 | 0.90 | INDIVIDUAL+CONJUNTO |

---

## CAPA 5 — SEGUNDA PASADA RESIDUAL

Se ejecuta sobre los 43 sabores LIMPIO + 3 OBSERVACIÓN + 1 PF8.

### 5.1 Señal R1 — Desvío histórico del sabor
Sin historial mensual completo computado. **R1: NO EVALUABLE.**

### 5.2 Señal R2 — Rareza estructural débil

| Sabor | Sub-señal | Detalle |
|-------|-----------|---------|
| DULCE AMORES | R2e: match_en_límite | cerr 6700↔6740, diff=40g |
| SUPER | R2e: match_en_límite | cerr 6730↔6770, diff=40g |
| GRANIZADO | R2e: match_en_límite | cerr 6750↔6710, diff=40g |
| LEMON PIE | R2e: match_en_límite | cerr 6645↔6615, diff=30g (exacto en borde) |

4 sabores con R2e. Ninguno tiene segunda sub-señal.

### 5.3 Señal R3 — Perfil de día anómalo

Día miércoles, bajo tráfico. Ventas generalmente bajas. Sin patrón de compensaciones opuestas anómalas.
Nota: FRUTILLA CREMA raw=1090g es la más alta entre LIMPIOs. Cerr estable (6565↔6555, 10g). La alta venta viene de ab decayendo fuerte (7035→5955, -1080g). Plausible sin señal R2.

### 5.4 Resultado segunda pasada

| Sabor | Señales | Resultado |
|-------|---------|-----------|
| DULCE AMORES | 1 (R2e) | LIMPIO_CON_NOTA |
| SUPER | 1 (R2e) | LIMPIO_CON_NOTA |
| GRANIZADO | 1 (R2e) | LIMPIO_CON_NOTA |
| LEMON PIE | 1 (R2e) | LIMPIO_CON_NOTA |
| Resto (43) | 0 | LIMPIO_CONFIRMADO |

**Ningún sabor alcanza ≥2 señales de distinto tipo → 0 reaperturas.**

---

## TABLA FINAL POR SABOR

| Sabor | Capa | Tipo | Venta stock | Latas | Conf |
|-------|------|------|-------------|-------|------|
| **AMERICANA** | **4** | **RESUELTO_IND+CONJ** | **265** | **0** | **0.90** |
| AMARGO | L | LIMPIO_CONFIRMADO | 510 | 0 | 1.00 |
| ANANA | L | LIMPIO_CONFIRMADO | 235 | 0 | 1.00 |
| B, SPLIT | L | LIMPIO_CONFIRMADO | 265 | 0 | 1.00 |
| BLANCO | L | LIMPIO_CONFIRMADO | 20 | 0 | 1.00 |
| BOSQUE | L | LIMPIO_CONFIRMADO | 590 | 0 | 1.00 |
| CABSHA | L | LIMPIO_CONFIRMADO | 190 | 0 | 1.00 |
| CADBURY | L | LIMPIO_CONFIRMADO | 315 | 0 | 1.00 |
| CEREZA | L | LIMPIO_CONFIRMADO | 290 | 0 | 1.00 |
| CH AMORES | L | LIMPIO_CONFIRMADO | 345 | 0 | 1.00 |
| CH C/ALM | L | LIMPIO_CONFIRMADO | 230 | 0 | 1.00 |
| **CHOCOLATE** | **3-E** | **ENGINE_CONFIRMADO** | **1,115** | **1** | **1.00** |
| CHOCOLATE DUBAI | L | LIMPIO_CONFIRMADO | 455 | 0 | 1.00 |
| CIELO | L | LIMPIO_CONFIRMADO | 380 | 0 | 1.00 |
| COCO | L | LIMPIO_CONFIRMADO | 75 | 0 | 1.00 |
| **COOKIES** | **3-PF** | **PF1 DIGIT_TYPO** | **130** | **0** | **0.95** |
| D. GRANIZADO | L | LIMPIO_CONFIRMADO | 745 | 0 | 1.00 |
| DOS CORAZONES | L | LIMPIO_CONFIRMADO | 360 | 0 | 1.00 |
| DULCE AMORES | 3-O | LIMPIO_CON_NOTA | 435 | 0 | 1.00 |
| DULCE C/NUEZ | L | LIMPIO_CONFIRMADO | 0 | 0 | 1.00 |
| DULCE D LECHE | L | LIMPIO_CONFIRMADO | 440 | 0 | 1.00 |
| DURAZNO | L | LIMPIO_CONFIRMADO | 420 | 0 | 1.00 |
| FERRERO | L | LIMPIO_CONFIRMADO | 250 | 0 | 1.00 |
| FLAN | L | LIMPIO_CONFIRMADO | 675 | 0 | 1.00 |
| FRAMBUEZA | L | LIMPIO_CONFIRMADO | 145 | 0 | 1.00 |
| FRANUI | L | LIMPIO_CONFIRMADO | 50 | 0 | 1.00 |
| FRUTILLA AGUA | L | LIMPIO_CONFIRMADO | 745 | 0 | 1.00 |
| FRUTILLA CREMA | L | LIMPIO_CONFIRMADO | 1,090 | 0 | 1.00 |
| FRUTILLA REINA | L | LIMPIO_CONFIRMADO | 385 | 0 | 1.00 |
| GRANIZADO | 3-O | LIMPIO_CON_NOTA | 385 | 0 | 1.00 |
| IRLANDESA | L | LIMPIO_CONFIRMADO | 850 | 0 | 1.00 |
| KINDER | L | LIMPIO_CONFIRMADO | 300 | 0 | 1.00 |
| KITKAT | L | LIMPIO_CONFIRMADO | 635 | 0 | 1.00 |
| LEMON PIE | L | LIMPIO_CON_NOTA | 235 | 0 | 1.00 |
| LIMON | L | LIMPIO_CONFIRMADO | 910 | 0 | 1.00 |
| MANTECOL | L | LIMPIO_CONFIRMADO | 315 | 0 | 1.00 |
| MANZANA | L | LIMPIO_CONFIRMADO | 505 | 0 | 1.00 |
| MARROC | L | LIMPIO_CONFIRMADO | 260 | 0 | 1.00 |
| MASCARPONE | L | LIMPIO_CONFIRMADO | 560 | 0 | 1.00 |
| MENTA | L | LIMPIO_CONFIRMADO | 425 | 0 | 1.00 |
| MIX DE FRUTA | L | LIMPIO_CONFIRMADO | 5 | 0 | 1.00 |
| MOUSSE LIMON | L | LIMPIO_CONFIRMADO | 5 | 0 | 1.00 |
| NUTE | L | LIMPIO_CONFIRMADO | 85 | 0 | 1.00 |
| PISTACHO | L | LIMPIO_CONFIRMADO | 455 | 0 | 1.00 |
| RUSA | L | LIMPIO_CONFIRMADO | 5 | 0 | 1.00 |
| SAMBAYON | L | LIMPIO_CONFIRMADO | 675 | 0 | 1.00 |
| **SAMBAYON AMORES** | **3-E** | **ENGINE_CONFIRMADO** | **610** | **1** | **1.00** |
| SUPER | 3-O | LIMPIO_CON_NOTA | 175 | 0 | 1.00 |
| **TIRAMIZU** | **3-PF** | **PF8 NOMBRE_INCONS** | **95** | **0** | **0.98** |
| TRAMONTANA | L | LIMPIO_CONFIRMADO | 835 | 0 | 1.00 |
| VAINILLA | L | LIMPIO_CONFIRMADO | 270 | 0 | 1.00 |

---

## TOTALES

| Componente | Valor |
|------------|-------|
| LIMPIO (43 sabores) | 14,280g |
| OBSERVACIÓN (3 sabores) | 995g |
| PROTOTIPOS PF1+PF8 (2 sabores) | 225g |
| ENGINE (2 sabores) | 1,725g |
| CAPA 4 — AMERICANA | 265g |
| **Venta stock total** | **17,490g** |
| Latas: 1(CHOCOLATE) + 1(SAMBAYON AMORES) = **2** | **-560g** |
| VDP | **0g** |
| Consumo interno | 0g |
| **TOTAL** | **16,930g** |

---

## DETALLE DE CORRECCIONES APLICADAS

| Sabor | Tipo | raw | Corregido | Δ | Descripción |
|-------|------|-----|-----------|---|-------------|
| AMERICANA | Ab imposible (PF7) | -2,450 | 265 | +2,715 | ab DIA 1650 erróneo → corregido a 4365 (backward D24N) |
| COOKIES | Digit typo (PF1) | 1,130 | 130 | -1,000 | cerr NOCHE 5705 → 6705 (offset +1000, 11 sightings) |
| TIRAMIZU | Nombre incons. (PF8) | 95 | 95 | 0 | "TIRAMIsU" en NOCHE combinado como "TIRAMIZU" |
| **Neto correcciones** | | | | **+1,715** | |

Sin correcciones: raw total = 17,490 - 1,715 = 15,775g (con los errores originales).

---

## CASOS ABIERTOS

| Sabor | Tipo | Detalle | Impacto máx |
|-------|------|---------|-------------|
| AMERICANA | Rango residual | ab real en [4110, 4365]. Venta en [10, 265]. Rango = 255g. | 255g |
| CHOCOLATE | Cerr 5940 inusual | 5940 es bajo para cerrada pero lleva 3 sightings estables. Historia D23→D24 (6340→5940) sin explicación. No afecta D25. | 0g en D25 |

Incertidumbre total: ~255g por rango de AMERICANA. Resto del día resuelto con alta confianza.

---

## NOTAS METODOLÓGICAS v3

1. **AMERICANA**: escalada a Capa 4 pese a que PF7 aplicaba, por magnitud >2000g. El expediente confirmó la corrección con 2 planos independientes y documentó el rango de incertidumbre (255g inmaterial).

2. **COOKIES**: resuelta en Capa 3 con PF1. No necesitó Capa 4: 11 sightings + offset exacto +1000g = evidencia unívoca.

3. **TIRAMIZU/TIRAMIsU**: resuelta en Capa 3 con PF8. Caso trivial de misspelling. Sin impacto numérico.

4. **CHOCOLATE cerr 5940**: marcado como observación histórica. 3 sightings estables no alcanzan los ≥5 requeridos por PF1 para evaluar digit error. El valor 5940 se acepta como observado.

5. **Segunda pasada**: sin reaperturas. 4 sabores con R2e (cerr en zona 30-40g) pero sin segunda señal complementaria.

6. **Capa 5 limitada**: sin R1 (requiere historial mensual computado). La segunda pasada solo pudo evaluar R2 y R3.
