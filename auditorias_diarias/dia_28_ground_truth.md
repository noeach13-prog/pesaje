# Día 28 — Ground Truth operativo

**Fuente**: `Febrero San Martin 2026 - pesaje resuelto pao noche 28-2 (1).pdf`
**Versión alternativa (Desktop)**: `(3).pdf` — mismos VENDIDO, difiere solo en latas (1400 vs 1120).

---

## 1. TOTALES BRUTOS VISIBLES (Excel sin corrección)

| Componente | Valor |
|------------|-------|
| Suma raw VENDIDO (52 sabores) | 57,440g |
| Latas engine (n_cerr_A > n_cerr_B) | 8 × 280 = 2,240g |
| VDP DIA | 0g |
| VDP NOCHE | 3,020g |
| **Bruto sin corregir** | **57,440 − 2,240 + 3,020 = 58,220g** |

---

## 2. CORRECCIONES HUMANAS EXPLÍCITAS

5 sabores corregidos. Todas las correcciones modifican el dato bruto (ponen 0 o agregan cerrada) y recalculan VENDIDO.

### C1 · CHOCOLATE — Cerrada omitida en DIA

> *"La lata cerrada de chocolate 6545 que aparece en el turno noche y no en el turno dia existía de antes y se olvidaron de ponerla en el turno dia, por eso queda en negativo."*

| | DIA bruto | DIA corregido | NOCHE |
|--|-----------|---------------|-------|
| ab | 4045 | 4045 | 1535 |
| cerr | 6655 | 6655, **6545** | 6255, 6545 |
| total | 10,700 | **17,245** | 14,335 |

- **Acción**: agregar cerr 6545 a DIA.
- **Bruto**: −3,635g → **Corregido**: 2,910g. **Delta**: +6,545g.

### C2 · SAMBAYON — Phantom cerrada en DIA

> *"La lata sambayon 6450 cerrada que figura en el turno dia en realidad no existe porque se cambió el día anterior."*

| | DIA bruto | DIA corregido | NOCHE |
|--|-----------|---------------|-------|
| ab | 6235 | 6235 | 5680 |
| cerr | 6450, 6675 | **0**, 6675 | 6575 |
| total | 19,360 | **12,910** | 12,255 |

- **Acción**: poner cerr 6450 en 0 (phantom — ya fue abierta D27).
- **Bruto**: 7,105g → **Corregido**: 655g. **Delta**: −6,450g.
- **Nota**: la 6675 se mantiene como real pese a no tener historial previo.

### C3 · MARACUYA — Entrante duplicado NOCHE

> *"La lata maracuya entrante que figura en el turno noche de 6380 no debería figurar ahí porque esa lata entró en el turno dia y se abrió."*

| | DIA | NOCHE bruto | NOCHE corregido |
|--|-----|-------------|-----------------|
| ab | 0 | 5825 | 5825 |
| ent | 6380 | 6380 | **0** |
| total | 6,380 | 12,205 | **5,825** |

- **Acción**: poner entrante NOCHE en 0 (la lata ya se abrió y pasó a abierta).
- **Bruto**: −5,825g → **Corregido**: 555g. **Delta**: +6,380g.

### C4 · CHOCOLATE DUBAI — Phantom cerrada en DIA + apertura única

> *"La lata 6400 cerrada de Dubai del turno dia no existe y la cerrada 6355 se cambió y pasó a abierta."*

| | DIA bruto | DIA corregido | NOCHE |
|--|-----------|---------------|-------|
| ab | 1420 | 1420 | 6035 |
| cerr | 6400, 6355 | **0**, 6355 | — |
| total | 14,175 | **7,775** | 6,035 |

- **Acción**: poner cerr 6400 en 0 (phantom). Solo 1 cerrada existía (6355), que fue abierta.
- **Bruto**: 8,140g → **Corregido**: 1,740g. **Delta**: −6,400g.
- **Latas reales**: 1 (no 2 como sugería el engine).

### C5 · PISTACHO — Phantom cerrada en DIA

> *"La lata de pistacho 6350 no existe."*

| | DIA bruto | DIA corregido | NOCHE |
|--|-----------|---------------|-------|
| ab | 2705 | 2705 | 1155 |
| cerr | 6350, 6355 | **0**, 6355 | 6355 |
| total | 15,410 | **9,060** | 7,510 |

- **Acción**: poner cerr 6350 en 0 (phantom).
- **Bruto**: 7,900g → **Corregido**: 1,550g. **Delta**: −6,350g.
- **Latas reales**: 0 (ab bajó de 2705 a 1155, no hubo apertura).

---

## 3. EFECTO ESPERADO DE CADA CORRECCIÓN

| # | Sabor | Tipo | Acción sobre dato | Delta venta | Delta latas |
|---|-------|------|-------------------|-------------|-------------|
| C1 | CHOCOLATE | Cerr omitida DIA | +6545 a total_DIA | +6,545 | 0 |
| C2 | SAMBAYON | Phantom cerr DIA | −6450 de total_DIA | −6,450 | 0 (era 1→0) |
| C3 | MARACUYA | Entrante dup NOCHE | −6380 de total_NOCHE | +6,380 | 0* |
| C4 | CHOC DUBAI | Phantom cerr DIA | −6400 de total_DIA | −6,400 | −1 (de 2 a 1) |
| C5 | PISTACHO | Phantom cerr DIA | −6350 de total_DIA | −6,350 | −1 (de 1 a 0) |
| | **TOTAL** | | | **−6,275** | **−2** |

*MARACUYA: la apertura del entrante genera 1 lata conceptual, pero el PDF no la cuenta en LATAS CAMBIADAS.

---

## 4. TOTAL FINAL CORREGIDO

| Componente | Valor |
|------------|-------|
| TOTAL VENTA (suma VENDIDO corregidos) | **51,165g** |
| LATAS CAMBIADAS (v1) | 1,120g (4 latas) |
| VDP DIA | 0g |
| VDP NOCHE | 3,020g |
| **TOTAL** | **53,065g** |

### Latas abiertas contadas (4):

| Sabor | Cerr abierta | ab DIA→NOCHE |
|-------|-------------|-------------|
| CH C/ALM | 6445 | 2325→6605 |
| D. GRANIZADO | 6675 | 1775→3720 |
| DULCE AMORES | 6635 | 1145→6185 |
| LIMON | 6280 | 1960→5315 |

### Discrepancia v1 vs v3:

La versión (3) del PDF cuenta **5 latas** (1,400g) incluyendo CHOCOLATE DUBAI (6355 abierta). Esto cambia el total a **52,785g**. La apertura de DUBAI está documentada en la nota ("se cambió y pasó a abierta"), por lo que 5 latas parece el conteo correcto. v1 probablemente tiene un error de conteo.

---

## 5. DIFERENCIA ENTRE BRUTO Y CORREGIDO

| | Bruto | Corregido | Diferencia |
|--|-------|-----------|------------|
| Venta stock | 57,440 | 51,165 | **−6,275g** |
| Latas (engine bruto) | 8 × 280 = 2,240 | 4 × 280 = 1,120 | **−1,120g** |
| VDP | 3,020 | 3,020 | 0 |
| **Total** | **58,220** | **53,065** | **−5,155g** |

Las correcciones reducen la venta stock en 6,275g y las latas en 4 unidades (de 8 a 4). El efecto neto sobre el total es −5,155g (≈8.8% del bruto).

---

## 6. PROTOTIPOS QUE APORTA ESTE DÍA

### P1 · CERRADA_OMITIDA_EN_DIA (nuevo)
**Caso**: CHOCOLATE cerr 6545.
Una cerrada que existe físicamente en ambos turnos fue omitida del registro DIA. Aparece solo en NOCHE, causando venta negativa.
**Corrección**: agregar la cerrada a DIA.
**Firma**: venta muy negativa + cerrada en NOCHE sin match en DIA + cerrada tiene historial previo (era entrante D27).
**Diferencia con cerrada_omitida_en_NOCHE (D26 PISTACHO)**: la omisión es en el turno A, no en B. El efecto es inverso: infla NOCHE vs infla DIA.

### P2 · PHANTOM_CERRADA_DIA (refuerza D26)
**Casos**: SAMBAYON 6450, PISTACHO 6350, CHOCOLATE DUBAI 6400.
Tres instancias con causas distintas:
- **SAMBAYON 6450**: lata abierta D27 que reaparece como cerrada D28 DIA. Causa: dato viejo copiado.
- **PISTACHO 6350**: cerrada sin origen conocido. Nota: "no existe."
- **CHOC DUBAI 6400**: cerrada sin origen. Nota: "no existe."
**Firma común**: cerrada en DIA sin historial de entrante, que desaparece en NOCHE sin apertura (ab no sube).
**Variante SAMBAYON**: la lata SÍ tiene historial previo pero fue abierta en turno anterior → RM-3 (can sellada no puede resellarse).

### P3 · ENTRANTE_ABIERTO_PERSISTENTE (confirma D26)
**Caso**: MARACUYA ent 6380.
Idéntico al prototipo validado en D26 (CHOCOLATE ent 6405). Entrante DIA fue abierto pero persiste en registro NOCHE.

### P4 · APERTURA_UNICA_CON_PHANTOM (nuevo)
**Caso**: CHOCOLATE DUBAI.
De 2 cerradas listadas, solo 1 existía realmente (6355). Esa única cerrada fue abierta. Sin la corrección phantom, el engine cuenta 2 latas; el conteo real es 1.
**Firma**: ab sube menos de lo esperado para 2 aperturas. Con 1 sola: 1420+6355−280=7495 → ab=6035 → consumo=1460g. Coherente.

---

## RESUMEN DE CONCORDANCIA CON AUDITORÍA

| Sabor | Auditoría (05) | Ground truth | Match |
|-------|---------------|-------------|-------|
| CHOCOLATE | UNRESOLVED / est. 2510 | **2,910** (cerr omitida DIA) | ✗ Tipo correcto (cerr faltante) pero dirección invertida. Auditoría asumió ab-only; GT agrega cerr a DIA. |
| SAMBAYON | est. 555 | **655** | ≈ Auditoría dijo phantom pero eliminó ambas cerradas DIA. GT solo elimina 6450, conserva 6675. |
| MARACUYA | corr. 555 | **555** | ✓ Match exacto. |
| PISTACHO | corr. 1,550 | **1,550** | ✓ Match exacto (aunque auditoría dijo "omitida NOCHE" y GT dice "phantom DIA"; mismo resultado numérico). |
| CHOC DUBAI | 7,580 (2 latas) | **1,740** (1 lata) | ✗ Auditoría no detectó phantom 6400. |
| Latas | 7 | 4 (v1) / 5 (v3) | ✗ |
| TOTAL | est. 57,375 | **53,065** | ✗ Δ=4,310g |
