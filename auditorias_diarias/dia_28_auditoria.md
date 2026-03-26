# Auditoría Día 28 — Sábado 28 de Febrero 2026

**Período**: Sábado 28 (DIA) ord.51 → Sábado 28 (NOCHE) ord.52
**Sabores con datos**: 52 (CHOCOLATE CON PASAS excluido: ALL_EMPTY)
**Raw total**: 57,440g

---

## 1. CLASIFICACIÓN INICIAL

| Nivel | n | Sabores |
|-------|---|---------|
| LIMPIO | 43 | AMARGO, AMERICANA, ANANA, B.SPLIT, BLANCO, BOSQUE, CABSHA, CADBURY, CEREZA, CH AMORES, CIELO, COCO, COOKIES, DOS CORAZONES, DULCE C/NUEZ, DULCE D LECHE, DURAZNO, FERRERO, FLAN, FRAMBUEZA, FRANUI, FRUTILLA AGUA, FRUTILLA CREMA, FRUTILLA REINA, GRANIZADO, IRLANDESA, KINDER, KITKAT, LEMON PIE, MANTECOL, MANZANA, MARROC, MASCARPONE, MENTA, MIX DE FRUTA, MOUSSE LIMON, NUTE, RUSA, SAMBAYON AMORES, SUPER, TIRAMIZU, TRAMONTANA, VAINILLA |
| ENGINE (apertura) | 5 | CH C/ALM, CHOCOLATE DUBAI, D. GRANIZADO, DULCE AMORES, LIMON |
| ESCALADO | 4 | CHOCOLATE, MARACUYA, PISTACHO, SAMBAYON |

**Notas rápidas LIMPIO**: MIX DE FRUTA tiene raw=-95g (ab sube +100g), dentro de ruido de pesaje. COOKIES/VAINILLA/FRUTILLA REINA/AMERICANA presentan T3 (diff cerrada 30-70g) sin impacto material.

---

## 2. CORRECCIONES ENGINE — Aperturas confirmadas

| Sabor | ab DIA→NOCHE | Cerr desaparecida | Latas | Venta stock | Venta neta |
|-------|-------------|-------------------|-------|-------------|------------|
| CH C/ALM | 2325→6605 (+4280) | 6445 | 1 | 2,170 | 1,890 |
| CHOCOLATE DUBAI | 1420→6035 (+4615) | 6400 + 6355 | 2 | 8,140 | 7,580 |
| D. GRANIZADO | 1775→3720 (+1945) | 6675 | 1 | 4,725 | 4,445 |
| DULCE AMORES | 1145→6185 (+5040) | 6635 | 1 | 1,590 | 1,310 |
| LIMON | 1960→5315 (+3355) | 6280 | 1 | 2,925 | 2,645 |
| **Subtotal** | | | **6** | **19,550** | **17,870** |

Todas confirmadas por salto de abierta coherente con apertura de cerrada (P1).

---

## 3. CASOS ESCALADOS

| # | Sabor | Raw | Flag principal | Prototipo |
|---|-------|-----|----------------|-----------|
| E1 | MARACUYA | -5,825 | Entrante duplicado DIA→NOCHE + apertura entrante | entrante_duplicate (validado D26) |
| E2 | PISTACHO | 7,900 | Cerrada 6350 omitida de NOCHE, ab baja | cerrada_omitida |
| E3 | CHOCOLATE | -3,635 | 2 cerradas nuevas en NOCHE sin fuente documentada | cerradas_caóticas |
| E4 | SAMBAYON | 7,105 | 2 cerradas DIA son phantom (6450 ya abierta D27) | phantom_cerrada |

---

## 4. ANÁLISIS PROFUNDO — Escalados

### E1 · MARACUYA — entrante_duplicate (conf: 0.90)

MARACUYA estuvo VACÍO desde ord42 hasta ord50. En DIA aparece solo entrante 6380 (ab=0). En NOCHE aparece ab=5825 con el mismo entrante 6380 listado.
**Diagnóstico**: el entrante fue abierto (6380-280=6100 ice cream disponible → ab=5825 tras consumo de 275g). El entrante persiste en NOCHE por error de registro.
**Corrección**: remover entrante 6380 de NOCHE. NOCHE corregido = 5825. Venta stock = 6380-5825 = 555g. 1 lata (entrante→abierta). Venta neta = 555-280 = 275g.
Prototipo validado en D26 (CHOCOLATE entrante 6405).

### E2 · PISTACHO — cerrada_omitida (conf: 0.85)

DIA: ab=2705, cerr=[6350, 6355]. NOCHE: ab=1155, cerr=[6355]. La cerrada 6350 desaparece pero ab BAJA 2705→1155 (-1550g). NO hubo apertura (P1 violado si se asume apertura: ab debería subir ~6000g).
**Diagnóstico**: cerrada 6350 fue omitida del registro NOCHE. Sigue físicamente presente.
**Corrección**: NOCHE corregido = 1155+6355+6350 = 13860. Venta stock = 15410-13860 = 1550g. 0 latas. Venta neta = 1550g.
Engine asignaba 1 lata (7620g) → rechazado por evidencia ab.

### E3 · CHOCOLATE — cerradas_caóticas (conf: 0.45)

DIA: ab=4045, cerr=[6655]. NOCHE: ab=1535, cerr=[6255, 6545]. Timeline: cerradas cambian cada turno (ord49 ent=[6545,6405], ord50 cerr=[6410], ord51 cerr=[6655], ord52 cerr=[6255,6545]). La 6255 no tiene historia previa. La 6545 era entrante D27. La identidad de cerradas es irreconciliable.
**Consumo ab confirmado**: 4045-1535 = 2510g (directo, confiable).
**Cerradas**: stock neto +1 cerrada en NOCHE sin documentar → imposible determinar venta real.
**Conservador**: UNRESOLVED, usar raw = -3,635g. **Estimado**: 2,510g (solo ab).

### E4 · SAMBAYON — phantom_cerrada (conf: 0.65)

DIA: ab=6235, cerr=[6450, 6675]. NOCHE: ab=5680, cerr=[6575].
**Evidencia fuerte**: la cerrada 6450 fue abierta en D27 (ab 1260→6235 en ord50). Una lata abierta NO puede reaparecer como cerrada. La 6675 no tiene historia previa. El entrante 6575 de D27 aparece como cerrada en NOCHE (promoción legítima).
**Diagnóstico**: DIA tiene cerradas phantom. Stock real DIA = ab(6235) + cerr_real(6575) = 12810. NOCHE = 5680+6575 = 12255. Venta stock = 555g. 0 latas.
ab baja 6235→5680 (555g consumo) confirma: sin apertura.
**Conservador**: usar raw (7105, 1 lata). **Estimado**: 555g, 0 latas.

---

## 5. TABLA FINAL POR SABOR

| Sabor | Nivel | Venta stock | Latas | Venta neta | Conf |
|-------|-------|-------------|-------|------------|------|
| AMARGO | L | 1,345 | 0 | 1,345 | 1.00 |
| AMERICANA | L | 525 | 0 | 525 | 1.00 |
| ANANA | L | 1,115 | 0 | 1,115 | 1.00 |
| B, SPLIT | L | 1,765 | 0 | 1,765 | 1.00 |
| BLANCO | L | 415 | 0 | 415 | 1.00 |
| BOSQUE | L | 980 | 0 | 980 | 1.00 |
| CABSHA | L | 660 | 0 | 660 | 1.00 |
| CADBURY | L | 845 | 0 | 845 | 1.00 |
| CEREZA | L | 1,190 | 0 | 1,190 | 1.00 |
| CH AMORES | L | 415 | 0 | 415 | 1.00 |
| CH C/ALM | E | 2,170 | 1 | 1,890 | 1.00 |
| CHOCOLATE | **E3** | **-3,635 / 2,510** | 0 | **-3,635 / 2,510** | **0.45** |
| CHOCOLATE DUBAI | E | 8,140 | 2 | 7,580 | 1.00 |
| CIELO | L | 835 | 0 | 835 | 1.00 |
| COCO | L | 255 | 0 | 255 | 1.00 |
| COOKIES | L | 420 | 0 | 420 | 1.00 |
| D. GRANIZADO | E | 4,725 | 1 | 4,445 | 1.00 |
| DOS CORAZONES | L | 705 | 0 | 705 | 1.00 |
| DULCE AMORES | E | 1,590 | 1 | 1,310 | 1.00 |
| DULCE C/NUEZ | L | 100 | 0 | 100 | 1.00 |
| DULCE D LECHE | L | 1,620 | 0 | 1,620 | 1.00 |
| DURAZNO | L | 145 | 0 | 145 | 1.00 |
| FERRERO | L | 180 | 0 | 180 | 1.00 |
| FLAN | L | 185 | 0 | 185 | 1.00 |
| FRAMBUEZA | L | 530 | 0 | 530 | 1.00 |
| FRANUI | L | 1,445 | 0 | 1,445 | 1.00 |
| FRUTILLA AGUA | L | 855 | 0 | 855 | 1.00 |
| FRUTILLA CREMA | L | 2,210 | 0 | 2,210 | 1.00 |
| FRUTILLA REINA | L | 700 | 0 | 700 | 1.00 |
| GRANIZADO | L | 1,070 | 0 | 1,070 | 1.00 |
| IRLANDESA | L | 545 | 0 | 545 | 1.00 |
| KINDER | L | 930 | 0 | 930 | 1.00 |
| KITKAT | L | 595 | 0 | 595 | 1.00 |
| LEMON PIE | L | 85 | 0 | 85 | 1.00 |
| LIMON | E | 2,925 | 1 | 2,645 | 1.00 |
| MANTECOL | L | 860 | 0 | 860 | 1.00 |
| MANZANA | L | 85 | 0 | 85 | 1.00 |
| MARACUYA | **E1** | **555** | **1** | **275** | **0.90** |
| MARROC | L | 1,220 | 0 | 1,220 | 1.00 |
| MASCARPONE | L | 390 | 0 | 390 | 1.00 |
| MENTA | L | 2,190 | 0 | 2,190 | 1.00 |
| MIX DE FRUTA | L | -95 | 0 | -95 | 1.00 |
| MOUSSE LIMON | L | 80 | 0 | 80 | 1.00 |
| NUTE | L | 385 | 0 | 385 | 1.00 |
| PISTACHO | **E2** | **1,550** | **0** | **1,550** | **0.85** |
| RUSA | L | 65 | 0 | 65 | 1.00 |
| SAMBAYON | **E4** | **7,105 / 555** | **1 / 0** | **6,825 / 555** | **0.65** |
| SAMBAYON AMORES | L | 460 | 0 | 460 | 1.00 |
| SUPER | L | 630 | 0 | 630 | 1.00 |
| TIRAMIZU | L | 1,010 | 0 | 1,010 | 1.00 |
| TRAMONTANA | L | 1,325 | 0 | 1,325 | 1.00 |
| VAINILLA | L | 1,075 | 0 | 1,075 | 1.00 |

*Nota: CHOCOLATE y SAMBAYON muestran valor conservador / estimado.*

---

## 6. TOTAL CONSERVADOR

Usa raw para casos sin resolver (CHOCOLATE, SAMBAYON). Solo aplica correcciones con confianza ≥0.85.

| Componente | Valor |
|------------|-------|
| LIMPIO (43 sabores) | 32,345g |
| ENGINE aperturas (5 sabores, stock) | 19,550g |
| E1 MARACUYA corregido (stock) | 555g |
| E2 PISTACHO corregido (stock) | 1,550g |
| E3 CHOCOLATE (raw, UNRESOLVED) | -3,635g |
| E4 SAMBAYON (raw, UNRESOLVED) | 7,105g |
| **Venta stock bruta** | **57,470g** |
| Latas abiertas: 6(ENGINE) + 1(MARACUYA) + 1(SAMBAYON raw) = **8** | **-2,240g** |
| VDP (5 entries NOCHE: 1KILO+1/4x2+2CUCUR+2BOCHAS+2CUCUR) | **+2,270g** |
| Consumo interno | 0g |
| **TOTAL CONSERVADOR** | **57,500g** |

⚠️ El conservador hereda error conocido de CHOCOLATE (-3,635g, venta negativa imposible) y posible inflación de SAMBAYON (+6,825g por cerradas phantom).

---

## 7. TOTAL ESTIMADO

Aplica correcciones estimadas para CHOCOLATE (ab consumption) y SAMBAYON (phantom).

| Componente | Valor |
|------------|-------|
| LIMPIO (43 sabores) | 32,345g |
| ENGINE aperturas (5 sabores, stock) | 19,550g |
| E1 MARACUYA corregido | 555g |
| E2 PISTACHO corregido | 1,550g |
| E3 CHOCOLATE estimado (ab only) | 2,510g |
| E4 SAMBAYON estimado (phantom) | 555g |
| **Venta stock bruta** | **57,065g** |
| Latas abiertas: 6(ENGINE) + 1(MARACUYA) = **7** | **-1,960g** |
| VDP | **+2,270g** |
| Consumo interno | 0g |
| **TOTAL ESTIMADO** | **57,375g** |

**Rango total**: 57,375g (est.) — 57,500g (cons.)

---

## 8. CASOS ABIERTOS

### E3 · CHOCOLATE (impacto: -3,635 a +2,510g)
- Las cerradas cambian de identidad cada turno. Sin tracker resuelto es imposible saber si el stock realmente creció o si es error de registro.
- **Resolución posible**: verificar planilla física de NOCHE para confirmar si cerr 6255 y 6545 realmente estaban presentes.
- **Impacto en total**: ±6,145g de rango.

### E4 · SAMBAYON (impacto: 555 a 6,825g)
- Evidencia fuerte de phantom (la 6450 fue abierta D27, RM-3 impide reaparición). La 6675 es huérfana sin entrante.
- **Resolución posible**: confirmar con D27 que cerr 6450 fue efectivamente abierta (ab 1260→6235 la confirma).
- **Impacto en total**: ±6,270g de rango.

**Incertidumbre total combinada**: ~12,400g de rango entre peor y mejor caso por estos 2 sabores.
