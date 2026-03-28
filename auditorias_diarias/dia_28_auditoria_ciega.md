# Auditoría Día 28 — Sábado 28 Feb 2026 (CIEGA)

**Método**: Solo datos congelados (CSV ord.49-52) + baseline (04b/04c/04d). Sin referencia validada.

## Clasificación: 42 LIMPIO, 1 ENGINE, 4 OBSERVACIÓN, 5 ESCALADO, 1 EMPTY

## Engine confirmados

| Sabor | Tipo | Venta bruta | Latas | Conf |
|-------|------|-------------|-------|------|
| D. GRANIZADO | Apertura cerr 6675 | 4725 | 1 | 1.00 |

Ab 1775→3720 (+1945). Cerr 6675 gone, cerr 6605≈6610 (5g). Apertura limpia.

## Observaciones (sin corrección)

| Sabor | Señal | Venta bruta | Nota |
|-------|-------|-------------|------|
| AMERICANA | cerr 6360→6290 (70g) | 525 | Varianza de pesaje. n_cerr igual. Sin impacto. |
| GRANIZADO | cerr 6750→6715 (35g) | 1070 | Varianza de pesaje. n_cerr igual. Sin impacto. |
| MIX DE FRUTA | ab sube 5245→5345 (+100g) | -95 | Impacto <200g. Ruido. H0. |
| VAINILLA | cerr 6465→6405 (60g) | 1075 | Varianza de pesaje. n_cerr igual. Sin impacto. |

## Escalados

### CHOCOLATE — PF5:CERR_OMITIDA_DIA
- Señales: raw=-3635, cerr 6545 en NOCHE sin match DIA, ab 4045→1535 (baja, no hay apertura)
- H1: cerr 6545 omitida del registro DIA. Evidencia: 6545 era entrante en D27 (ord.49-50), existe físicamente. Aparece como cerr NOCHE sin explicación de origen. Omisión de registro.
- H2: cerr 6545 llegó durante turno NOCHE sin documentar. Menos plausible: no hay entrante registrado.
- Corrección: agregar cerr 6545 a total_DIA
- Impacto: MASA: +6545g en venta_stock
- Conf: 0.85
- Delta: -3635 → 2910 = +6545g
- Nota: cerr 6655 DIA vs cerr 6255 NOCHE (diff 400g) queda sin resolver. P5 preserva ambas. Sin impacto en cálculo (n_cerr=2 ambos lados).

### MARACUYA — PF2:ENTRANTE_DUP
- Señales: raw=-5825, entrante 6380 idéntico DIA y NOCHE, ab 0→5825
- H1: entrante fue abierto (contenido al tarro), persiste en NOCHE por error de registro
- H2: ninguna plausible (ab=0→5825 confirma apertura, ent idéntico confirma persistencia)
- Corrección: poner entrante NOCHE en 0
- Impacto: MASA: +6380g en venta_stock
- Conf: 0.90
- Delta: -5825 → 555 = +6380g
- Nota: apertura de entrante no cuenta como "lata cambiada" en convención heladería (no es cerrada).

### PISTACHO — PF3:PHANTOM_CERR
- Señales: cerr 6350 en DIA sin match en NOCHE, ab 2705→1155 (baja, no hay apertura)
- H1: cerr 6350 phantom (registro duplicado de la misma lata 6355). Timeline: D27D cerr=[6350], D27N cerr=[6355], D28D cerr=[6350,6355], D28N cerr=[6355]. Una sola lata física pesada alternadamente 6350/6355 (5g varianza). En D28D se registraron ambos pesos por error.
- H2: cerr 6350 es real segunda lata, omitida en NOCHE. Poco plausible: ab baja sin apertura, y 6350/6355 son 5g de diferencia.
- Corrección: poner cerr 6350 en 0 en DIA
- Impacto: MASA: -6350g en venta_stock. Remueve 1 lata falsa (cerr gone sin apertura).
- Conf: 0.85 (P1.c: desaparece sin apertura + ab no sube + timeline confirma una sola lata)
- Delta: 7900 → 1550 = -6350g

### SAMBAYON — PF3:PHANTOM_CERR (RM-3)
- Señales: cerr 6450 DIA fue abierta en D27 (ab 1260→6235 con cerr 6450 gone), reaparece como cerr D28D
- H1: cerr 6450 phantom por RM-3. Timeline: ord.45-48 cerr 6450 estable (4 sightings). ord.49 (D27D): cerr=[6450], ent=[6575], ab=1260. ord.50 (D27N): ab=6235, no cerr. Cerr 6450 fue abierta en D27 (+4975g a ab). Imposible que reaparezca sellada en D28D.
- H2: error de peso (es otra lata pesando ~6450). Sin evidencia: no hay entrante ni nueva lata documentada.
- Corrección: poner cerr 6450 en 0 en DIA. Mantener cerr 6675 (P5).
- Impacto: MASA: -6450g en venta_stock. Remueve 1 lata falsa.
- Conf: 0.90 (RM-3 es violación estructural, evidencia directa)
- Delta: 7105 → 655 = -6450g
- Nota: cerr 6675 DIA vs cerr 6575 NOCHE (100g diff). Podrían ser la misma lata (ent 6575 de D27 promovida a cerr). P5 preserva.

### CHOCOLATE DUBAI — PF6:APERTURA_CON_PHANTOM
- Señales: 2 cerr DIA (6400, 6355), 0 cerr NOCHE, ab 1420→6035 (+4615)
- H1: cerr 6400 phantom (1-sighting, sin historial). Solo cerr 6355 fue abierta (1 lata). Timeline: cerr 6355 estable desde ord.45 (8 sightings). Cerr 6400 aparece solo en D28D. Ab sube +4615, consistente con 1 apertura de 6355: 6355-280=6075 de capacidad, venta=1460g razonable. Si 2 aperturas: venta=7580g, excesiva para CHOC DUBAI.
- H2: ambas reales, 2 aperturas. Poco plausible: ab sube solo 4615 vs ~12195 esperado con 0 venta.
- Corrección: poner cerr 6400 en 0, contar 1 lata (no 2)
- Impacto: MASA: -6400g en venta_stock, -1 lata
- Conf: 0.80 (PF6: ab consistente con M=1 no N=2, 6400 sin historial)
- Delta: 8140 → 1740 = -6400g

## Tabla final

| Sabor | Nivel | Venta bruta | Latas |
|-------|-------|-------------|-------|
| AMARGO | LIMPIO | 1345 | 0 |
| AMERICANA | OBS | 525 | 0 |
| ANANA | LIMPIO | 1115 | 0 |
| B, SPLIT | LIMPIO | 1765 | 0 |
| BLANCO | LIMPIO | 415 | 0 |
| BOSQUE | LIMPIO | 980 | 0 |
| CABSHA | LIMPIO | 660 | 0 |
| CADBURY | LIMPIO | 845 | 0 |
| CEREZA | LIMPIO | 1190 | 0 |
| CH AMORES | LIMPIO | 415 | 0 |
| CH C/ALM | LIMPIO | 2170 | 1 |
| CHOCOLATE | PF5 | 2910 | 0 |
| CHOCOLATE DUBAI | PF6 | 1740 | 1 |
| CIELO | LIMPIO | 835 | 0 |
| COCO | LIMPIO | 255 | 0 |
| COOKIES | LIMPIO | 420 | 0 |
| D. GRANIZADO | ENGINE | 4725 | 1 |
| DOS CORAZONES | LIMPIO | 705 | 0 |
| DULCE AMORES | LIMPIO | 1590 | 1 |
| DULCE C/NUEZ | LIMPIO | 100 | 0 |
| DULCE D LECHE | LIMPIO | 1620 | 0 |
| DURAZNO | LIMPIO | 145 | 0 |
| FERRERO | LIMPIO | 180 | 0 |
| FLAN | LIMPIO | 185 | 0 |
| FRAMBUEZA | LIMPIO | 530 | 0 |
| FRANUI | LIMPIO | 1445 | 0 |
| FRUTILLA AGUA | LIMPIO | 855 | 0 |
| FRUTILLA CREMA | LIMPIO | 2210 | 0 |
| FRUTILLA REINA | LIMPIO | 700 | 0 |
| GRANIZADO | OBS | 1070 | 0 |
| IRLANDESA | LIMPIO | 545 | 0 |
| KINDER | LIMPIO | 930 | 0 |
| KITKAT | LIMPIO | 595 | 0 |
| LEMON PIE | LIMPIO | 85 | 0 |
| LIMON | LIMPIO | 2925 | 1 |
| MANTECOL | LIMPIO | 860 | 0 |
| MANZANA | LIMPIO | 85 | 0 |
| MARACUYA | PF2 | 555 | 0 |
| MARROC | LIMPIO | 1220 | 0 |
| MASCARPONE | LIMPIO | 390 | 0 |
| MENTA | LIMPIO | 2190 | 0 |
| MIX DE FRUTA | OBS | -95 | 0 |
| MOUSSE LIMON | LIMPIO | 80 | 0 |
| NUTE | LIMPIO | 385 | 0 |
| PISTACHO | PF3 | 1550 | 0 |
| RUSA | LIMPIO | 65 | 0 |
| SAMBAYON | PF3/RM-3 | 655 | 0 |
| SAMBAYON AMORES | LIMPIO | 460 | 0 |
| SUPER | LIMPIO | 630 | 0 |
| TIRAMIZU | LIMPIO | 1010 | 0 |
| TRAMONTANA | LIMPIO | 1325 | 0 |
| VAINILLA | OBS | 1075 | 0 |

## Totales

| Métrica | Valor |
|---------|-------|
| venta_stock (bruta) | **51,165g** |
| latas | **5 (1,400g)** |
| VDP | pendiente (parser) |
| venta_stock - latas | 49,765g |

## Detalle de correcciones

| Sabor | Prototipo | Raw | Corregido | Delta |
|-------|-----------|-----|-----------|-------|
| CHOCOLATE | PF5 | -3635 | 2910 | +6545 |
| MARACUYA | PF2 | -5825 | 555 | +6380 |
| PISTACHO | PF3 | 7900 | 1550 | -6350 |
| SAMBAYON | PF3/RM-3 | 7105 | 655 | -6450 |
| CHOC DUBAI | PF6 | 8140 | 1740 | -6400 |
| **Σ deltas** | | | | **-6275** |

## Observaciones pendientes

1. **CHOCOLATE 6655/6255**: cerr DIA 6655 vs cerr NOCHE 6255 (400g diff). No es digit typo estándar (±1000). Sin historial suficiente para resolver. P5 preserva. Sin impacto en total (n_cerr=2 ambos lados).
2. **SAMBAYON 6675/6575**: cerr DIA 6675 vs cerr NOCHE 6575 (100g diff). Probablemente misma lata (ent 6575 de D27 promovida). P5 preserva.
3. **VDP**: no calculado en esta auditoría (parser pendiente).
