# Capa 1 — Parser / Estructura

## Responsabilidad

Leer el workbook Excel y entregar datos crudos sin interpretacion.
Ninguna inferencia, correccion ni interpretacion pertenece a esta capa.

---

## Input

Archivo Excel (.xlsx) con multiples hojas.
Cada hoja representa un turno (ej: "Jueves 5 (DIA)", "Jueves 5 (NOCHE)").

## Output

Por cada hoja valida, un diccionario:

```python
{
  'sabor': str,          # nombre tal cual aparece en col A
  'abierta': int | None, # col B. None = no registrado
  'celiaca': int | None, # col C. None = no hay celiaca
  'cerradas': list[int], # cols D-I, hasta 6 valores
  'entrantes': list[int] # cols J-K, hasta 2 valores
}
```

Mas la seccion POSTRES:
```python
{
  'vdp_textos': list[str],   # cols D-F, textos de ventas antes del pesaje
  'consumo_interno': list[str], # cols G-H
  'observaciones': list[str]    # col D debajo de POSTRES
}
```

---

## Reglas de lectura

### R1.1 — Hojas validas
Una hoja es valida si celda A1 == 'SABORES' (exacto, case-sensitive).
Hojas con A1 != 'SABORES' se saltan (ej: hojas "STOCK").
Hojas vacias (0 sabores parseados) se filtran con nota.

### R1.2 — Fin de sabores
La fila donde col A contiene 'POSTRES' marca el fin de la seccion de sabores.
Todo lo que esta arriba de esa fila (desde fila 2) son sabores.
Todo lo que esta en esa fila y debajo es seccion POSTRES.

### R1.3 — Columnas
| Col | Contenido | Tipo |
|-----|-----------|------|
| A | Nombre del sabor | str |
| B | Abierta (peso del balde abierto) | int o vacio |
| C | Celiaca | int o vacio |
| D-I | Cerradas (latas cerradas, hasta 6) | int o vacio |
| J-K | Entrantes (latas que llegaron, hasta 2) | int o vacio |

### R1.4 — Preservacion de valores nulos
Distinguir estrictamente:
- `None` → celda no registrada (dato faltante)
- `0` → cero explicito (balde vacio o sin abierta)
- `''` → celda vacia explicita

Estas distinciones se preservan para capas superiores. NO colapsar a 0.

### R1.5 — Nombres de sabor
Se entregan TAL CUAL aparecen en la planilla.
No normalizar, no corregir, no unificar variantes.
La correccion de nombres (ej: KIYKAT→KITKAT) pertenece a Capa 3.

### R1.6 — Orden de hojas
El orden fisico de las hojas en el workbook es el orden temporal de los turnos.
Respetar ese orden para la construccion de timelines.
Nota: puede haber hojas fuera de orden cronologico (ej: Viernes 13 NOCHE entre Martes 10 DIA y Martes 10 NOCHE en Febrero 2026).

### R1.7 — Seccion POSTRES
Dentro de la seccion POSTRES:
- Cols D-F: textos de VDP (ventas antes del pesaje)
- Cols G-H: consumo interno
- Col D (filas subsiguientes): observaciones libres

Los textos se entregan como strings sin parsear. El parseo de VDP a gramos pertenece a Capa 2.

---

## Implementacion existente

`parser.py` ya implementa la mayoria de estas reglas.
Referencia: `01_mapa_workbook.md` para estructura detallada del Excel.

## Test de validacion

Para D5 (Jueves 5):
- Hoja "Jueves 5 (DIA)": debe parsear 52 sabores
- Hoja "Jueves 5 (NOCHE)": debe parsear 49 sabores (FRANUI, IRLANDESA, CHOC DUBAI vacias)
- Hoja "Miercoles 4": debe filtrar como vacia (0 sabores)
