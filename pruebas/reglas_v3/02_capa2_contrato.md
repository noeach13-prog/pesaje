# Capa 2 — Contrato contable

## Responsabilidad

Definir la formula de venta como regla global del sistema.
Esta formula es DEFINICION, no se modifica por historial ni inferencia.
Las correcciones de capas superiores modifican los INPUTS, no la formula.

---

## Input

Datos crudos de Capa 1: dos turnos (A = DIA, B = NOCHE) por sabor.

## Output

Por cada sabor:
```python
{
  'total_a': int,        # stock total en turno A
  'total_b': int,        # stock total en turno B
  'new_ent_b': int,      # entrantes nuevos en B (no estaban en A)
  'n_latas': int,        # latas abiertas en el periodo
  'ajuste_latas': int,   # n_latas * 280
  'venta_raw': int       # venta bruta calculada
}
```

---

## Formula de venta (inmutable)

```
venta_stock = total_A + new_entrantes_B - total_B - ajuste_latas
```

### Componentes

```
total = abierta + celiaca + sum(cerradas) + sum(entrantes)
```

Si abierta es None, se trata como 0 para el calculo (pero Capa 3 lo marca como dato faltante).

### Entrantes nuevos

```
new_entrantes_B = sum de entrantes en B que NO estaban en A
```

Un entrante de B se considera "ya estaba en A" si existe un entrante en A con |peso_B - peso_A| <= 50g.
El matching es greedy: cada entrante de A se usa una sola vez.

### Ajuste de latas

```
n_latas = max(0, n_cerradas_A - n_cerradas_B)
ajuste_latas = n_latas * 280
```

280g es el peso promedio de la tapa de lata que se descarta al abrir.
Solo se descuenta si el numero de cerradas BAJO (se abrio alguna).

### Composicion del total del dia

```
venta_stock_dia = sum(venta_stock de cada sabor)
VDP = ventas de postres en gramos (parseado de textos POSTRES)
lid_discount = sum(n_latas de cada sabor) * 280
TOTAL_DIA = venta_stock_dia + VDP - lid_discount
```

Nota: lid_discount ya esta incluido en venta_stock via ajuste_latas,
por lo que en la practica: TOTAL_DIA = sum(venta_raw) + VDP.
El lid_discount se reporta por separado para trazabilidad.

---

## VDP — Ventas de postres

### Parseo de textos VDP

Los textos crudos de la seccion POSTRES se convierten a gramos con tabla de equivalencias:

| Texto patron | Gramos |
|---|---|
| 1 KILO | 1000 |
| 1/2 KILO | 500 |
| 1/4 | 250 |
| 1 CUARTO | 250 |
| CUCURUCHO / CUCURUCHON | 245 |
| VASO 65 | 65 |
| VASO 110 | 110 |
| VASO 165 | 165 |
| BOCHA | 120 |

Prefijos numericos multiplican: "2 CUCURUCHO" = 490g, "4/1" = "4 x 1/4" = 1000g.

### VDP por turno

VDP_DIA y VDP_NOCHE se suman. El total VDP del dia = VDP_DIA + VDP_NOCHE.

---

## Sabores especiales

### SOLO_DIA
Sabor que aparece en DIA pero no en NOCHE (o NOCHE vacia).
No se calcula venta. Se registra con su stock DIA para trazabilidad.

### SOLO_NOCHE
Sabor que aparece en NOCHE pero no en DIA.
No se calcula venta. Caso raro, indica error de estructura.

### Nombre inconsistente
Si Capa 3 detecta que dos nombres son el mismo sabor (PF8),
Capa 2 recalcula tratandolos como uno solo.

---

## Test de validacion

Para D5:
- 49 sabores con ambos turnos → venta calculable
- 3 sabores SOLO_DIA (FRANUI, IRLANDESA, CHOC DUBAI)
- venta_raw total = 40,095g (antes de correcciones)
- VDP DIA = ~1,495g (2 vasos65 + 4/1 + 1 cucurucho)
- VDP NOCHE = 0g
