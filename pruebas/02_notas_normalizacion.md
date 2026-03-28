# NOTAS DE NORMALIZACIÓN — 02_observaciones_normalizadas.csv

Generado a partir de: `Febrero San Martin 2026 (1).xlsx`
Filas: 2757 (57 sabores × ~52 turnos, menos ausencias)
Columnas: fecha, turno, orden_temporal, sabor_original, sabor_normalizado, abierta, celiaca, cerradas, entrantes, total_observado, hoja_origen, fila_origen, notas_lectura

---

## 1. DECISIONES DE NORMALIZACIÓN

### 1.1 Nombres de sabor → strip()
Todos los nombres se procesaron con `.strip()`. Esto resolvió trailing spaces sistemáticos en 6 sabores (AMARGO, BOSQUE, CHOCOLATE, FLAN, LIMON, MENTA — siempre con espacio al final) y esporádicos en FRANUI (1 hoja).

### 1.2 Rango de columnas

| Zona | Columnas leídas | Justificación |
|------|-----------------|---------------|
| Abierta | B (2) | Estándar |
| Celiaca | C (3) | Estándar. Rara vez usada (ver 1.4) |
| Cerradas | D-I (4-9) | 6 slots máximo |
| Entrantes | J-L (10-12) | Extendido a col L. B,SPLIT en Viernes 6 usa 3 entrantes (J+K+L) |
| Total | O (15) | Fórmula de suma del Excel |

**Decisión col L**: El estándar es J-K (2 slots de entrante). Sin embargo, `B, SPLIT` en `Viernes 6 (Día)` y `Viernes 6 (Noche)` tiene un 3er entrante en col L (6475g). Esta es la ÚNICA ocurrencia de datos en col L en todo el workbook. Se incluyó col L para no perder este valor.

### 1.3 Valores vacíos

- Celda `None` → campo vacío en CSV (string vacío)
- Celda con valor `0` o `0.0` → se registra como `0`
- Toda la fila sin datos numéricos → nota `ALL_EMPTY` (131 filas, concentradas en Miércoles 4 que está completamente vacío + sabores individuales sin stock como MARACUYA)

### 1.4 Celiaca como cerrada

En `Lunes 16 (NOCHE)`:
- DULCE AMORES tiene C(3) = 6620 → peso de cerrada, no celiaca
- BOSQUE tiene C(3) = 6470 → peso de cerrada, no celiaca

**Decisión**: Valores en col C mayores a 5000g se reclasifican automáticamente como cerrada adicional. Se mueven a la lista de cerradas y se vacía el campo celiaca. Nota `CELIACA_ES_CERRADA:{peso}` documenta la decisión.

**Justificación**: La celiaca (celíaca/sin TACC) es un peso alternativo de balde abierta, nunca superior a ~3000g. Un valor de 6000+ es inequívocamente una lata cerrada colocada en la columna equivocada.

### 1.5 Hojas filtradas

- **Hojas STOCK** (idx 1, 13, 28, 43, 56): excluidas. Contienen inventario de insumos, no pesos de helado.
- **Miércoles 4** (idx 4): incluida pero sus 53 filas tienen nota `ALL_EMPTY`. Tiene nombres de sabores sin ningún dato numérico.

### 1.6 Orden temporal

El campo `orden_temporal` asigna un número secuencial (1-52) a cada turno en orden cronológico real, NO en orden de pestaña del Excel. La hoja `Viernes 13 (NOCHE)` (idx 17 en el libro) recibe orden 22 (después de Viernes 13 DIA, orden 21).

### 1.7 Turno para hojas sin marcador DIA/NOCHE

| Hoja | Turno asignado | Justificación |
|------|----------------|---------------|
| Domingo 1 | UNICO | No tiene par NOCHE |
| Lunes 2 | UNICO | No tiene par NOCHE |
| Martes 3 | UNICO | No tiene par NOCHE |
| Miércoles 4 | UNICO | No tiene par NOCHE (además está vacía) |
| Miércoles 11 | DIA | Tiene par `Miércoles 11 (NOCHE)` → es DIA implícito |

---

## 2. ALIAS TENTATIVOS

| Nombre original | Nombre normalizado | Hojas | Confianza | Evidencia |
|-----------------|-------------------|-------|-----------|-----------|
| `KIT KAT` | `KITKAT` | Lunes 9 DIA, Miércoles 11, Sábado 21 DIA (3) | Alta | Mismo sabor, solo espacio |
| `KIYKAT` | `KITKAT` | Jueves 5 NOCHE (1) | Alta | Typo evidente (Y→T) |
| `TIRAMIsU` | `TIRAMIZU` | Miércoles 25 NOCHE (1) | Alta | Mismo sabor, casing + U/Z |

**Nota**: Estos alias están **aplicados** en el CSV (el campo `sabor_normalizado` tiene el nombre canónico). El campo `sabor_original` preserva el nombre tal como estaba en la hoja. La columna `notas_lectura` marca cada aplicación con `ALIAS:original->normalizado`.

### Alias NO aplicados (requieren decisión humana)

| Candidato A | Candidato B | Evidencia | Por qué no se aplicó |
|------------|-------------|-----------|---------------------|
| BANANITA | CHOCOLATE CON PASAS | BANANITA desaparece en d12, CH.CON PASAS aparece en d12 | Son sabores DISTINTOS (BANANITA = banana, CH.CON PASAS = chocolate). La coincidencia temporal es por cambio de carta, no alias. |
| FRAMBUEZA | FRAMORE | Similitud fonética parcial | FRAMORE existe solo en 3 hojas DIA (d6-d8). Son sabores diferentes. |

---

## 3. FILAS DUDOSAS

### 3.1 Total mismatch: BOSQUE en Viernes 6 (Noche)
```
Hoja: Viernes 6 (Noche), row 28
Datos: ab=6450, cerr=[], ent=[], total_observado=980
Computed: 6450 (solo abierta)
Observado: 980
Diff: +5470
```
**Causa raíz**: La fórmula del Excel en O28 es `=B27+C28+D28+...+N28`. Toma B de la fila 27 (FRUTILLA AGUA, un sabor diferente) en vez de la fila 28. Es un error de fórmula en la planilla original. El total 980 es basura — el valor correcto es 6450 (solo abierta, sin cerradas ni entrantes).

**Decisión**: Se registra el total tal como está en el Excel (980) pero se marca con `TOTAL_MISMATCH`. El análisis posterior debe usar los valores de columnas individuales (abierta + cerradas + entrantes), NO el total de col O.

### 3.2 Total mismatch: FRUTILLA CREMA en Viernes 13 (NOCHE)
```
Hoja: Viernes 13 (NOCHE), row 24
Datos: ab=3275, cerr=[], ent=[6695, 6550], total_observado=17000
Computed: 16520
Observado: 17000
Diff: -480
```
**Causa posible**: El total 17000 podría incluir un valor no visible en las columnas estándar, o ser un total manualmente ingresado con redondeo. La diferencia de 480g no se explica por ningún campo visible.

**Decisión**: Registrado como `TOTAL_MISMATCH`. Usar valores de columnas individuales.

### 3.3 Celiaca reclasificada: Lunes 16 (NOCHE)
```
DULCE AMORES: C(3)=6620 → movido a cerradas. Nota: CELIACA_ES_CERRADA:6620
BOSQUE: C(3)=6470 → movido a cerradas. Nota: CELIACA_ES_CERRADA:6470
```
**Riesgo**: Si algún sabor tuviera un peso celiaca legítimo de >5000g, se reclasificaría erróneamente. Sin embargo, en todo el workbook solo estas 2 filas tienen celiaca >5000, y ambos valores son típicos de lata cerrada (6400-6700g).

### 3.4 Hoja completamente vacía: Miércoles 4
53 filas de sabores, todos los campos numéricos vacíos. Todas las filas marcadas como `ALL_EMPTY`. Esta hoja NO debe usarse como turno en la timeline — no aporta observación alguna.

### 3.5 B, SPLIT con 3er entrante en col L
```
Viernes 6 (Día), row 5: ab=4800, ent=[6450, 6350, 6475], total=24075
Viernes 6 (Noche), row 5: ab=3555, ent=[6450, 6350, 6475], total=22830
```
Única ocurrencia de datos en col L (12). Los 3 entrantes son reales — el total del Excel los incluye y cuadra.

---

## 4. CAMPOS QUE REQUIEREN REVISIÓN HUMANA

### 4.1 Total de col O: NO usar como fuente de verdad
El total de col O es una fórmula del Excel que en al menos 2 casos tiene errores (BOSQUE Viernes 6 Noche, FRUTILLA CREMA Viernes 13 Noche). **Recomendación: recalcular total siempre desde abierta + cerradas + entrantes.**

### 4.2 Celiaca como cerrada: verificar con el local
La reclasificación automática de celiaca > 5000g es una heurística. Si el local confirma que DULCE AMORES y BOSQUE tenían cerradas en Lunes 16 NOCHE, la decisión es correcta. Si tenían baldes celíacos grandes, hay que revertir.

### 4.3 Sabores temporales: ¿son reales?
- **D. PATAGONICO** (5 hojas, d4-d8 solo DIA): ¿Sabor real? ¿Error de carga? Todos los campos ALL_EMPTY en Miércoles 4 (pero esa hoja completa está vacía).
- **FRAMORE** (3 hojas, d6-d8 solo DIA): ¿Sabor real? Solo 3 apariciones.
- **YOGURT** (6 hojas, d5-d10): ¿Sabor que dejaron de hacer?
- **MARACUYA** (52 hojas, siempre ALL_EMPTY): Sabor fantasma. Presente en la lista pero nunca tuvo stock.

### 4.4 Viernes 13 NOCHE fuera de orden
La pestaña `Viernes 13 (NOCHE)` está en posición idx 17 del libro (entre Martes 10 DIA y Martes 10 NOCHE). El `orden_temporal` asignado es 22. Si algún proceso lee las pestañas en orden del libro sin reordenar, se obtiene una secuencia temporal incorrecta.

### 4.5 Hojas con A1 anómalo
- `SABADO 7 (NOCHE)`: A1=None (falta "SABORES")
- ` Martes 10 (NOCHE)`: A1='/' (carácter slash)
- `Domingo 15 (DIA)`: A1=4.0 (número)

Ninguna de estas anomalías afecta la extracción de datos (los sabores empiezan en row 2 normalmente), pero un parser que filtre por `A1 == 'SABORES'` las perdería.

---

## 5. ESTADÍSTICAS DEL CSV

| Métrica | Valor |
|---------|-------|
| Total filas | 2757 |
| Sabores únicos (normalizado) | 57 |
| Turnos con datos | 51 (excluye Miércoles 4 vacío) |
| Filas ALL_EMPTY | 131 |
| Alias aplicados | 5 filas |
| Celiaca reclasificada | 2 filas |
| Total mismatches | 2 filas |
| Sabores permanentes (52 turnos) | 49 |
| Sabores parciales | 8 (BANANITA, CHOCOLATE CON PASAS, COCO, D.PATAGONICO, FRAMORE, FRANUI, KITKAT, YOGURT) |
