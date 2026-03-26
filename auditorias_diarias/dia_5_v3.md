# Auditoría Día 5 — Jueves 5 de Febrero 2026 (v3)

**Período**: Jueves 5 (DIA) ord.3 → Jueves 5 (NOCHE) ord.4
**Contexto temporal**: Martes 3 (ord.2) → [Miércoles 4 VACÍO] → D5D → D5N → Viernes 6D (ord.5) → Viernes 6N (ord.6)
**Sabores con datos**: 52 (3 SOLO_DIA: CHOCOLATE DUBAI, FRANUI, IRLANDESA)

---

## 1. CAPA 1 — Datos crudos extraídos

Fuente: `Febrero San Martin 2026 (1).xlsx`, hojas "Jueves 5 (DIA)" y "Jueves 5 (NOCHE)".

**Notas de parseo**:
- NOCHE registra "KIYKAT" → corregido a KITKAT (PF8 nombre inconsistente)
- CHOCOLATE DUBAI, FRANUI, IRLANDESA: presentes en DIA pero EMPTY en NOCHE → SOLO_DIA
- COCO: no aparece en grilla principal DIA, pero sí en sección POSTRES/observaciones (ab=4505)

---

## 2. CAPA 2 — Contrato contable (screening)

| Nivel | n | Sabores |
|-------|---|---------|
| LIMPIO | 36 | AMARGO, ANANA, B.SPLIT, BLANCO, BOSQUE, CABSHA, CEREZA, CIELO, COCO, D.GRANIZADO, DOS CORAZONES, DULCE C/NUEZ, DURAZNO, FERRERO, FLAN, FRAMBUEZA, FRUTILLA AGUA, FRUTILLA CREMA, FRUTILLA REINA, GRANIZADO, KINDER, LEMON PIE, LIMON, MANTECOL, MANZANA, MARACUYA, MARROC, MASCARPONE, MIX DE FRUTA, MOUSSE LIMON, NUTE, RUSA, SUPER, TIRAMIZU, TRAMONTANA, CH AMORES |
| ENGINE (apertura) | 4 | AMERICANA, COOKIES, MENTA, SAMBAYON AMORES |
| COMPUESTO | 8 | CADBURY, CH C/ALM, DULCE AMORES, DULCE D LECHE, KITKAT, PISTACHO, SAMBAYON, VAINILLA |
| SEÑAL | 1 | CHOCOLATE |
| SOLO_DIA | 3 | CHOCOLATE DUBAI, FRANUI, IRLANDESA |

---

## 3. CAPA 3 — Motor local

### 3.1 ENGINE — Aperturas confirmadas

| Sabor | ab DIA→NOCHE | Cerr abierta | Latas | Venta (neta) |
|-------|-------------|--------------|-------|-------------|
| AMERICANA | 760→6805 (+6045) | 6700 | 1 | 375 |
| COOKIES | 775→6900 (+6125) | 6630 | 1 | 225 |
| MENTA | 1695→7050 (+5355) | 6610 | 1 | 975 |
| SAMBAYON AMORES | 1030→6255 (+5225) | 6255 | 1 | 750 |
| **Subtotal** | | | **4** | **2,325** |

Todas confirman P1 (salto de abierta coherente con peso de cerrada abierta).

### 3.2 Reclasificación T3 → LIMPIO

| Sabor | Cerr DIA | Cerr NOCHE | Diff | Raw | Decisión |
|-------|----------|------------|------|-----|----------|
| CADBURY | 6360 | 6410 | 50g | 1,320 | T3 pesaje variance. Timeline: D3 cerr=6410, D6D cerr=6360. Oscila ±50g. LIMPIO |
| CH C/ALM | 6675 | 6615 | 60g | 1,400 | T3 pesaje variance. Timeline: D3 cerr=6615. Oscila ±60g. LIMPIO |
| SAMBAYON | 6365 | 6315 | 50g | 900 | T3 pesaje variance. LIMPIO |

**LIMPIO reclasificado**: 36 + 3 = **39 sabores, 27,430g**

### 3.3 Casos escalados a Capa 4

| # | Sabor | Raw | Flag | Prototipo candidato |
|---|-------|-----|------|-------------------|
| E1 | DULCE D LECHE | -6,315 | NEG, CERR+1N | PF5 cerr omitida DIA |
| E2 | VAINILLA | -6,360 | NEG, CERR+1N | PF5 cerr omitida DIA |
| E3 | DULCE AMORES | 7,235 | HIGH, 1 lata | PF3 phantom cerrada DIA |
| E4 | KITKAT | 6,350 | HIGH, 1 lata | PF3 phantom cerrada DIA |
| E5 | PISTACHO | 1,945 | C4d:6630, C4n:6330 | PF1 error pesaje cerrada |
| E6 | CHOCOLATE | 7,485 | HIGH, ent mismatch | PF1 error pesaje entrante NOCHE |

---

## 4. CAPA 4 — Expedientes ampliados

### E1 · DULCE D LECHE — cerr_omitida_DIA (PF5)

**Datos**:
- DIA: ab=1705, cerr=[6685]
- NOCHE: ab=1470, cerr=[6680, 6555]

**P1 — Serie temporal abierta**:
ab baja 1705→1470 (-235g). Consumo normal. Sin apertura.

**P2 — Multiconjunto cerradas**:
DIA registra 1 cerrada (6685≈6680). NOCHE registra 2 cerradas (6680, 6555). La 6555 aparece en NOCHE sin origen.

**P3 — Genealogía / Timeline**:
- D3: cerr=[6680, 6555] ← ambas cerradas presentes
- D5D: cerr=[6685] ← solo una registrada (6685≈6680, diff 5g)
- D5N: cerr=[6680, 6555] ← ambas cerradas de vuelta
- D6D: cerr=[6680, 6555] ← ambas cerradas presentes
- D6N: cerr=[6555] ← 6680 desaparece (apertura D6)

La cerrada 6555 estuvo presente en D3, D5N, D6D — timeline continuo. Fue **omitida del registro DIA**.

**Hipótesis**:
- H1 (PF5 cerr omitida DIA): 6555 estaba físicamente presente pero no registrada. **Conf: 0.95**
- H2 (entrante nuevo): 6555 llegó durante el turno. Contradice D3 (ya presente). **Conf: 0.05**

**Convergencia**: P1 (consumo normal, sin apertura ↔ coherente) + P2 (mismatch conteo) + P3 (timeline confirma presencia). 3 planos convergentes.

**Corrección**: Añadir 6555 a DIA.
- Stock DIA corregido = 1705 + 6685 + 6555 = 14,945
- Stock NOCHE = 1470 + 6680 + 6555 = 14,705
- Venta corregida = 14,945 - 14,705 = **240g**, 0 latas
- Delta: +6,555g (de -6,315 a 240)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.95**.

---

### E2 · VAINILLA — cerr_omitida_DIA (PF5)

**Datos**:
- DIA: ab=5055, cerr=[]
- NOCHE: ab=4970, cerr=[6445]

**P1 — Serie temporal abierta**:
ab baja 5055→4970 (-85g). Consumo mínimo. Sin apertura.

**P2 — Multiconjunto cerradas**:
DIA registra 0 cerradas. NOCHE registra 1 cerrada (6445). Apareció de la nada.

**P3 — Genealogía / Timeline**:
- D3: cerr=[] ← sin cerradas (pero Vainilla es sabor con poco historial de cerradas en este punto)
- D5D: cerr=[] ← sin cerradas
- D5N: cerr=[6445] ← aparece
- D6D: cerr=[6445] ← persiste
- D6N: cerr=[6445] ← persiste

La cerrada 6445 aparece en D5N y persiste D6D y D6N → stock real. El punto de entrada más probable es entre D3 y D5D (entrante no registrado que ya estaba ahí como cerrada). Fue **omitida del registro DIA**.

**Hipótesis**:
- H1 (PF5 cerr omitida DIA): 6445 estaba presente pero no registrada en D5D. **Conf: 0.88**
- H2 (entrante intra-turno): llegó durante el turno DIA y fue registrada en cierre. Posible pero sin entrante documentado. **Conf: 0.12**

**Convergencia**: P1 (ab normal) + P2 (mismatch) + P3 (persistencia posterior confirma stock real). 3 planos.

**Corrección**: Añadir 6445 a DIA.
- Stock DIA corregido = 5055 + 6445 = 11,500
- Stock NOCHE = 4970 + 6445 = 11,415
- Venta corregida = 11,500 - 11,415 = **85g**, 0 latas
- Delta: +6,445g (de -6,360 a 85)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.88**.

---

### E3 · DULCE AMORES — phantom_cerrada_DIA (PF3)

**Datos**:
- DIA: ab=2475, cerr=[6700, 6555], ent=[6795]
- NOCHE: ab=1515, cerr=[6700], ent=[6795]

**P1 — Serie temporal abierta**:
ab baja 2475→1515 (-960g). Consumo normal. **No hay apertura** (ab NO sube). Si cerr 6555 fue abierta, ab debería saltar a ~6555-280≈6275 → ab subiría. No sucedió. P1 **rechaza** apertura.

**P2 — Multiconjunto cerradas**:
DIA tiene 2 cerradas, NOCHE tiene 1. La 6700 persiste. La 6555 desaparece. Raw asume apertura (1 lata).

**P3 — Genealogía / Timeline**:
- D3: cerr=[6700] ← solo 6700
- D5D: cerr=[6700, 6555] ← 6555 aparece sin entrante documentado (T9)
- D5N: cerr=[6700] ← 6555 desaparece
- D6D: cerr=[6700] ← solo 6700

La 6555 es **1-sighting** (solo en D5D). No tiene genealogía previa ni posterior. El entrante 6795 ya está contabilizado como entrante — no puede ser la fuente de 6555 (peso difiere 240g).

**Hipótesis**:
- H1 (PF3 phantom): 6555 fue registrada por error en DIA (confusión de sabor, error de grilla). **Conf: 0.88**
- H2 (apertura real): 6555 era real y fue abierta. P1 rechaza: ab no sube. **Conf: 0.08**
- H3 (omisión NOCHE): 6555 sigue presente pero omitida en NOCHE. Contradice D6D (no está). **Conf: 0.04**

**Convergencia**: P1 (ab baja, imposible apertura) + P2 (1-sighting) + P3 (sin genealogía). 3 planos convergentes en phantom.

**Corrección**: Remover 6555 de DIA.
- Stock DIA corregido = 2475 + 6700 + 6795 = 15,970
- Stock NOCHE = 1515 + 6700 + 6795 = 15,010
- Venta corregida = 15,970 - 15,010 = **960g**, 0 latas
- Delta: -6,275g (de 7,235 a 960)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.88**.

---

### E4 · KITKAT — phantom_cerrada_DIA (PF3)

**Datos**:
- DIA: ab=4630, cerr=[6400]
- NOCHE: ab=4400, cerr=[] (hoja NOCHE dice "KIYKAT", PF8 nombre corregido)

**P1 — Serie temporal abierta**:
ab baja 4630→4400 (-230g). Consumo mínimo. **No hay apertura** (ab baja). Si cerr 6400 fue abierta, ab subiría a ~6120g. No sucedió.

**P2 — Multiconjunto cerradas**:
DIA tiene 1 cerrada, NOCHE tiene 0. Raw asume apertura (1 lata, venta 6350g).

**P3 — Genealogía / Timeline**:
- D3: cerr=[] ← sin cerradas
- D5D: cerr=[6400] ← aparece
- D5N: cerr=[] ← desaparece
- D6D: cerr=[] ← sin cerradas
- D6N: cerr=[] ← sin cerradas

La 6400 es **1-sighting** (solo en D5D). KITKAT nunca tuvo cerradas en D3, D6D, D6N.

**Hipótesis**:
- H1 (PF3 phantom): 6400 fue registrada por error en DIA. **Conf: 0.90**
- H2 (apertura real): P1 rechaza categóricamente (ab baja). **Conf: 0.05**
- H3 (cerrada real que se fue): entró y salió el mismo día. Extremadamente raro. **Conf: 0.05**

**Convergencia**: P1 (ab baja) + P2 (1-sighting) + P3 (sin genealogía). 3 planos.

**Corrección**: Remover 6400 de DIA.
- Stock DIA corregido = 4630
- Stock NOCHE = 4400
- Venta corregida = 4630 - 4400 = **230g**, 0 latas
- Delta: -6,120g (de 6,350 a 230)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.90**.

---

### E5 · PISTACHO — error_pesaje_cerrada (PF1)

**Datos**:
- DIA: ab=3140, cerr=[6630]
- NOCHE: ab=1495, cerr=[6330]

**P1 — Serie temporal abierta**:
ab baja 3140→1495 (-1645g). Consumo alto pero dentro de rango (sabor popular).

**P2 — Multiconjunto cerradas**:
1 cerrada en DIA (6630), 1 en NOCHE (6330). Diff = 300g → fuera de tolerancia 30g. No matchean como misma lata a nivel C4.

**P3 — Genealogía / Timeline**:
- D3: cerr=[6330]
- D5D: cerr=[6630] ← ¡300g más que D3!
- D5N: cerr=[6330] ← vuelve a 6330
- D6D: cerr=[6330] ← 6330 estable
- D6N: cerr=[] ← desaparece (apertura D6)

El peso estable de esta cerrada es **6330g** (D3, D5N, D6D = 3 sightings). D5D registra 6630, que es exactamente **+300g**. Error de pesaje o transcripción (posible inversión de dígitos 33→63 en centenas).

**Hipótesis**:
- H1 (PF1 error pesaje): DIA registró 6630 pero el peso real es 6330. **Conf: 0.92**
- H2 (cerradas distintas): 6630 y 6330 son latas diferentes. Contradice continuidad: 6330 no desaparece y 6630 solo 1-sighting. **Conf: 0.08**

**Convergencia**: P2 (misma posición) + P3 (peso estable 6330 en 3 turnos flanqueantes). 2 planos independientes.

**Corrección**: DIA cerr 6630 → 6330.
- Stock DIA corregido = 3140 + 6330 = 9,470
- Stock NOCHE = 1495 + 6330 = 7,825
- Venta corregida = 9,470 - 7,825 = **1,645g**, 0 latas
- Delta: -300g (de 1,945 a 1,645)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.92**.

---

### E6 · CHOCOLATE — error_pesaje_entrante (PF1)

**Datos**:
- DIA: ab=1980, cerr=[6640], ent=[6530, 6475]
- NOCHE: ab=1025, cerr=[6640], ent=[6630, 6475]

**P1 — Serie temporal abierta**:
ab baja 1980→1025 (-955g). Consumo normal.

**P2 — Multiconjunto cerradas**:
Cerrada 6640 matchea perfectamente (0g diff). Sin problemas.

**P2b — Entrantes**:
- Ent 6475 matchea perfectamente (0g).
- Ent DIA 6530 vs ent NOCHE 6630: diff = 100g (fuera de tolerancia 50g).
- Raw trata 6630 como **nuevo entrante** → agrega 6,630g al stock de apertura → infla venta a 7,485g.

**P3 — Genealogía / Timeline**:
- D3: cerr=[6640], ent=[] ← sin entrantes
- D5D: cerr=[6640], ent=[6530, 6475] ← 2 entrantes nuevos
- D5N: cerr=[6640], ent=[6630, 6475] ← el "6630" ocupa la posición del 6530
- D6D: cerr=[**6530**, 6640, 6475], ent=[] ← entrantes promovidos a cerradas. **Peso es 6530, NO 6630**.
- D6N: cerr=[6475, 6530], ent=[] ← 6530 persiste

**Evidencia decisiva**: En D6D, el entrante fue promovido a cerrada con peso **6530g**. Esto confirma que el peso real del entrante es 6530g. El registro de 6630 en D5N es un error de pesaje (+100g).

**Hipótesis**:
- H1 (PF1 error pesaje): NOCHE registró 6630 pero el peso real es 6530. **Conf: 0.93**
- H2 (entrantes distintos): 6530 se fue y 6630 llegó. Contradice D6D (cerrada=6530, no 6630). **Conf: 0.07**

**Convergencia**: P2b (posición ent) + P3 (D6D confirma peso=6530 como cerrada). 2 planos.

**Corrección**: NOCHE ent 6630 → 6530. Esto matchea con DIA, new_ent_B = 0.
- Stock DIA = 1980 + 6640 + 6530 + 6475 = 21,625
- Stock NOCHE corregido = 1025 + 6640 + 6530 + 6475 = 20,670
- Venta corregida = 21,625 - 20,670 = **955g**, 0 latas
- Delta: -6,530g (de 7,485 a 955)

**Resolución**: RESUELTO_INDIVIDUAL. Conf: **0.93**.

---

## 5. CAPA 5 — Segunda pasada residual

### 5.1 Revisión SOLO_DIA

| Sabor | DIA | Decisión |
|-------|-----|----------|
| CHOCOLATE DUBAI | ab=0, cerr=[], ent=[] | ALL_EMPTY. Slot vacío. 0g. |
| FRANUI | ab=1095, cerr=[], ent=[] | Solo abierta. Sin NOCHE para comparar. No se puede calcular venta. Registrar como **pendiente**. |
| IRLANDESA | ab=775, cerr=[], ent=[] | Solo abierta. Sin NOCHE. Registrar como **pendiente**. |

Nota: FRANUI e IRLANDESA tienen stock activo en DIA pero desaparecen en NOCHE. Sin dato de cierre no se puede calcular venta. Se excluyen del total (0g contribución).

### 5.2 Señales residuales

- **MANZANA**: venta = -5g. Ruido de pesaje (ab 765→770, +5g). Dentro de tolerancia. LIMPIO.
- **MIX DE FRUTA**: venta = 210g con ab 6710→6500 (-210g). Normal.
- **CH AMORES**: cerr 6675→6665 (10g diff). T3. LIMPIO.

No se detectan falsos LIMPIO que requieran reapertura. Sin señales R1/R2/R3 convergentes.

---

## 6. TABLA FINAL POR SABOR

| # | Sabor | Nivel | Venta | Latas | Conf |
|---|-------|-------|-------|-------|------|
| 1 | AMARGO | L | 1,455 | 0 | 1.00 |
| 2 | AMERICANA | E | 375 | 1 | 1.00 |
| 3 | ANANA | L | 710 | 0 | 1.00 |
| 4 | B, SPLIT | L | 870 | 0 | 1.00 |
| 5 | BLANCO | L | 410 | 0 | 1.00 |
| 6 | BOSQUE | L | 860 | 0 | 1.00 |
| 7 | CABSHA | L | 245 | 0 | 1.00 |
| 8 | CADBURY | L(T3) | 1,320 | 0 | 1.00 |
| 9 | CEREZA | L | 3,030 | 0 | 1.00 |
| 10 | CH AMORES | L | 1,175 | 0 | 1.00 |
| 11 | CH C/ALM | L(T3) | 1,400 | 0 | 1.00 |
| 12 | CHOCOLATE | **E6** | **955** | **0** | **0.93** |
| 13 | CHOCOLATE DUBAI | SOLO_DIA | 0 | 0 | — |
| 14 | CIELO | L | 295 | 0 | 1.00 |
| 15 | COCO | L | 425 | 0 | 1.00 |
| 16 | COOKIES | E | 225 | 1 | 1.00 |
| 17 | D. GRANIZADO | L | 1,490 | 0 | 1.00 |
| 18 | DOS CORAZONES | L | 280 | 0 | 1.00 |
| 19 | DULCE AMORES | **E3** | **960** | **0** | **0.88** |
| 20 | DULCE C/NUEZ | L | 55 | 0 | 1.00 |
| 21 | DULCE D LECHE | **E1** | **240** | **0** | **0.95** |
| 22 | DURAZNO | L | 105 | 0 | 1.00 |
| 23 | FERRERO | L | 480 | 0 | 1.00 |
| 24 | FLAN | L | 90 | 0 | 1.00 |
| 25 | FRAMBUEZA | L | 215 | 0 | 1.00 |
| 26 | FRANUI | SOLO_DIA | 0 | 0 | — |
| 27 | FRUTILLA AGUA | L | 420 | 0 | 1.00 |
| 28 | FRUTILLA CREMA | L | 1,055 | 0 | 1.00 |
| 29 | FRUTILLA REINA | L | 325 | 0 | 1.00 |
| 30 | GRANIZADO | L | 635 | 0 | 1.00 |
| 31 | IRLANDESA | SOLO_DIA | 0 | 0 | — |
| 32 | KINDER | L | 455 | 0 | 1.00 |
| 33 | KITKAT | **E4** | **230** | **0** | **0.90** |
| 34 | LEMON PIE | L | 870 | 0 | 1.00 |
| 35 | LIMON | L | 2,190 | 0 | 1.00 |
| 36 | MANTECOL | L | 125 | 0 | 1.00 |
| 37 | MANZANA | L | -5 | 0 | 1.00 |
| 38 | MARACUYA | L | 440 | 0 | 1.00 |
| 39 | MARROC | L | 255 | 0 | 1.00 |
| 40 | MASCARPONE | L | 985 | 0 | 1.00 |
| 41 | MENTA | E | 975 | 1 | 1.00 |
| 42 | MIX DE FRUTA | L | 210 | 0 | 1.00 |
| 43 | MOUSSE LIMON | L | 685 | 0 | 1.00 |
| 44 | NUTE | L | 195 | 0 | 1.00 |
| 45 | PISTACHO | **E5** | **1,645** | **0** | **0.92** |
| 46 | RUSA | L | 360 | 0 | 1.00 |
| 47 | SAMBAYON | L(T3) | 900 | 0 | 1.00 |
| 48 | SAMBAYON AMORES | E | 750 | 1 | 1.00 |
| 49 | SUPER | L | 435 | 0 | 1.00 |
| 50 | TIRAMIZU | L | 615 | 0 | 1.00 |
| 51 | TRAMONTANA | L | 1,370 | 0 | 1.00 |
| 52 | VAINILLA | **E2** | **85** | **0** | **0.88** |

---

## 7. TOTALES

| Componente | Venta | Latas |
|------------|-------|-------|
| LIMPIO (39 sabores) | 27,430g | 0 |
| ENGINE (4 sabores) | 2,325g | 4 |
| E1 DDL (PF5 cerr omitida) | 240g | 0 |
| E2 VAINILLA (PF5 cerr omitida) | 85g | 0 |
| E3 DULCE AMORES (PF3 phantom) | 960g | 0 |
| E4 KITKAT (PF3 phantom) | 230g | 0 |
| E5 PISTACHO (PF1 error pesaje) | 1,645g | 0 |
| E6 CHOCOLATE (PF1 error pesaje ent) | 955g | 0 |
| **Venta stock corregida** | **33,870g** | **4** |
| Ajuste latas (4 × 280g) | (ya incluido) | |
| VDP DIA: 2 VASO 65 + 4/1 + 1 CUCURUCHON | **+1,375g** | |
| VDP NOCHE | 0g | |
| Consumo interno | 0g | |
| **TOTAL DÍA 5** | **35,245g** | |

**Comparación RAW vs CORREGIDO**:
- Venta stock RAW: 40,095g (6 latas)
- Venta stock CORREGIDA: 33,870g (4 latas)
- Delta total: **-6,225g** (eliminación de phantoms, omisiones recuperadas, errores de pesaje)

---

## 8. RESUMEN DE CORRECCIONES

| # | Sabor | Tipo | De (raw) | A (corr) | Delta | Conf |
|---|-------|------|----------|----------|-------|------|
| E1 | DULCE D LECHE | PF5 cerr omitida DIA | -6,315 | 240 | +6,555 | 0.95 |
| E2 | VAINILLA | PF5 cerr omitida DIA | -6,360 | 85 | +6,445 | 0.88 |
| E3 | DULCE AMORES | PF3 phantom cerrada DIA | 7,235 | 960 | -6,275 | 0.88 |
| E4 | KITKAT | PF3 phantom cerrada DIA | 6,350 | 230 | -6,120 | 0.90 |
| E5 | PISTACHO | PF1 error pesaje cerr | 1,945 | 1,645 | -300 | 0.92 |
| E6 | CHOCOLATE | PF1 error pesaje ent | 7,485 | 955 | -6,530 | 0.93 |

Nota: Las correcciones E1/E2 (omisiones) y E3/E4 (phantoms) se compensan parcialmente en el total (+12,000 vs -12,395), pero no son interdependientes — cada una se resuelve con evidencia independiente de 3 planos.

---

## 9. CASOS ABIERTOS

### FRANUI / IRLANDESA (SOLO_DIA)
Ambos sabores tienen stock activo en DIA (ab=1095 / ab=775) pero desaparecen completamente en NOCHE. Sin dato de cierre no se puede calcular venta. Impacto potencial: hasta ~1,870g de venta no contabilizada.

**No hay casos UNRESOLVED ni H0 en este día.** Todas las anomalías detectadas se resuelven con confianza ≥0.88.
