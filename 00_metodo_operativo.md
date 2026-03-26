# MÉTODO OPERATIVO DE RESOLUCIÓN POR DÍA

Extraído del documento "Resolución completa Día 26" como especificación reusable.

---

## SECUENCIA DE PASOS

```
PASO 1  Clasificación de los N sabores del día
PASO 2  Verificación de correcciones del engine
PASO 3  Análisis multi-turno de sospechosos
PASO 4  Tabla de ventas finales por sabor
PASO 5  Cálculo del total del día
PASO 6  Registro de casos abiertos
```

---

## PASO 1 — CLASIFICACIÓN

Para cada sabor del día, clasificar en exactamente una de estas categorías:

### 1.1 LIMPIO
- `engine == raw`
- Venta ≥ 0 (o negativa menor, típicamente ≥ -200g)
- El tracker no detectó anomalías
- Los slots de DIA y NOCHE son coherentes entre sí

### 1.2 CORREGIDO POR ENGINE
- `engine ≠ raw`
- El engine aplicó alguna corrección: omission, phantom, digit_typo, ghost, entrante_duplicate
- Requiere verificación en Paso 2

### 1.3 SOSPECHOSO
- `engine == raw` (el engine no corrigió nada)
- Pero el valor es anómalo:
  - Venta muy alta (> 5000g sin apertura de cerrada que la explique)
  - Venta negativa significativa (< -200g)
  - Abierta sube entre DIA→NOCHE sin apertura de cerrada
  - Cerrada aparece 1 solo turno y desaparece (1-sighting)
- Requiere análisis multi-turno en Paso 3

### 1.4 SOSPECHOSO + DÍGITO
- `engine == raw` (el engine no lo corrigió, o lo corrigió parcialmente)
- Contiene un typo de dígito no detectado: peso difiere ~1000-2000g del historial estable
- Se detecta en Paso 3 por historial del tracker

### Criterio de detección de sospechosos

Un sabor pasa a sospechoso si cumple CUALQUIERA de:
- `sold < -200`
- `sold > 5000` y no hay apertura de cerrada documentada
- Abierta NOCHE > abierta DIA (sin apertura)
- Cerrada con 1 solo sighting en el día
- `diff != 0` (engine modificó algo — va a "corregido", no "sospechoso")

---

## PASO 2 — VERIFICACIÓN DE CORRECCIONES DEL ENGINE

Para cada sabor clasificado como CORREGIDO POR ENGINE:

### 2.1 Obtener contexto
```
Datos requeridos:
- Slots raw de DIA y NOCHE (abierta, cerradas, entrantes)
- Total DIA, total NOCHE, raw sold
- Tipo de corrección aplicada (omission/phantom/digit_typo/etc)
- Can ID afectado, número de sightings, shifts donde aparece
```

### 2.2 Verificar por tipo de corrección

#### OMISSION (cerrada falta en un turno)
Verificar:
1. ¿El can tiene historial suficiente? (≥ 3 sightings)
2. ¿Aparece en el turno ANTERIOR y POSTERIOR al faltante?
3. ¿La abierta confirma que no hubo apertura? (baja poco, no salta)
4. Si TODO es sí → **engine correcto** ✓

#### PHANTOM (valor sin match en ningún can tracked)
Verificar:
1. ¿El valor tiene un can tracked que lo explique?
2. ¿Podría ser un entrante no documentado? (lata nueva sin registrar)
3. ¿La abierta muestra apertura? (salto grande = alguien abrió algo)
4. Si no hay explicación alternativa → **engine correcto** ✓
5. Si la lata podría ser real → **engine cuestionable**, anotar confianza

#### DIGIT_TYPO (peso con offset de ±1000-2000g respecto al historial)
Verificar:
1. ¿El can tiene ≥ 5 sightings estables?
2. ¿El offset es exacto ±1000 o ±2000?
3. ¿El turno anterior y posterior muestran el peso normal?
4. Si TODO es sí → **engine correcto** ✓

#### DOBLE OMISSION
Verificar:
1. Cada omisión individualmente (como arriba)
2. ¿Las omisiones se compensan parcialmente? (una en DIA, otra en NOCHE)
3. Anotar confianza menor (0.75) si hay ambigüedad

### 2.3 Resultado de verificación
Para cada corrección, anotar:
- **Engine correcto** ✓ — usar valor del engine
- **Engine aceptable** — usar valor del engine con confianza reducida
- **Engine incorrecto** ✗ — el engine se equivocó, requiere corrección manual en Paso 3

---

## PASO 3 — ANÁLISIS MULTI-TURNO

Para cada sabor SOSPECHOSO, SOSPECHOSO+DÍGITO, o con ENGINE INCORRECTO:

### 3.1 Extraer timeline completa
```
Ventana mínima: ±3 turnos alrededor del período analizado
Ventana ideal:  historia completa del sabor en todo el mes
Datos por turno: abierta, cerradas[], entrantes[], tracker cans
```

### 3.2 Aplicar razonamiento por tipo de anomalía

#### TIPO A: ERROR DE DÍGITO EN CERRADA
**Señales:**
- Cerrada con peso que difiere ~1000-2000g del historial estable del can
- El can tiene ≥ 5 sightings a un peso consistente (varianza ≤ 30g)
- Gap de exactamente ~1000g o ~2000g

**Verificación:**
- Turno anterior: peso normal del can
- Turno posterior: peso normal del can
- Abierta: baja poco (no hubo apertura, confirma que la cerrada sigue ahí)

**Corrección:**
- Reemplazar peso erróneo por peso promedio del can
- Recalcular: `venta = total_A_corregido - total_B` o `total_A - total_B_corregido`

**Ejemplo validado:** COOKIES d25 (5705→6705), KITKAT d26 (4385→6385)

#### TIPO B: ABIERTA IMPOSIBLE (AB_IMP)
**Señales — criterio por imposibilidad física, NO por threshold:**
- La abierta SUBE entre turnos SIN apertura de cerrada
- La cerrada está intacta (varianza ≤ 30g)
- No hay entrante que explique el aumento

**Verificación por secuencia:**
1. **Backward**: ¿Cuál era la tendencia de la abierta en turnos anteriores?
2. **Forward**: ¿Cuál es la abierta en el turno siguiente? ¿Es coherente con el valor sospechoso o con el valor esperado?
3. **Magnitud**: ¿Cuánto sube? (430g y 920g fueron los casos del d26)
4. **Continuidad**: ¿El valor posterior confirma cuál de los dos valores (DIA o NOCHE) es correcto?

**Determinación del valor correcto:**
- Si forward es coherente con el valor POSTERIOR → el posterior es correcto, el anterior es error
- Si forward es coherente con el valor ANTERIOR → el anterior es correcto, el posterior es error
- Usar cierre→apertura (~0g de diferencia) como ancla

**Corrección:**
- Reemplazar valor erróneo por el valor anclado (turno anterior o posterior)
- Si no hay valor exacto: usar el máximo físicamente posible (ej: abierta NOCHE ≤ abierta DIA si no hubo apertura)

**Ejemplo validado:** AMERICANA d25 (1650→4365), SAMBAYON AMORES d26 (5450→6450)

#### TIPO C: NOMBRE INCONSISTENTE
**Señales:**
- Dos sabores que nunca coexisten en el mismo turno
- Pesos coherentes entre ambos (abierta baja gradualmente, cerradas similares)
- Uno tiene muchos turnos, el otro tiene 1-2

**Corrección:**
- Combinar como un solo sabor
- Venta = suma de ambos (se compensan)

**Ejemplo validado:** TIRAMISU/TIRAMIZU d25

#### TIPO D: CERRADA 1-SIGHTING
**Señales:**
- Cerrada que aparece en un solo turno (solo DIA o solo NOCHE) y desaparece
- Sin historial previo en el tracker (1 sighting)
- La abierta confirma que no se abrió (baja poco)

**Razonamiento físico:**
- Si no se abrió → la cerrada sigue existiendo físicamente → fue omitida en el turno siguiente
- Venta real = solo consumo de abierta (no incluir la cerrada)
- La cerrada NO fue vendida

**Verificación forward:**
- ¿Reaparece como entrante en turno posterior? (ej: BLANCO 6700 → entrante 6770 en d27) → confianza media-alta
- ¿Desaparece completamente? (ej: DOS CORAZONES) → confianza media (la lata pudo ser trasladada)

**Corrección:**
- Venta = abierta_DIA - abierta_NOCHE (solo consumo de balde)
- No contar la cerrada como vendida

**Ejemplo validado:** BLANCO d26 (6790→90), DOS CORAZONES d26 (6690→160)

### 3.3 Clasificación del resultado

Cada corrección multi-turno se clasifica como:

| Clasificación | Criterio | Acción |
|---|---|---|
| **Confirmada** | Matchea prototipo validado con evidencia bilateral (turno anterior + posterior) | Aplicar corrección |
| **Estimada** | Evidencia física fuerte pero sin valor exacto de reemplazo | Aplicar con nota "(estimado)" |
| **H0** | Evidencia insuficiente, sin prototipo, ambigua | Mantener valor raw/engine |

**Criterio para "confirmada" vs "estimada":**
- CONFIRMADA: tengo el valor exacto correcto (ej: KITKAT 4385→6385, sé que es 6385 por 11 sightings)
- ESTIMADA: sé que el valor está mal pero no tengo el valor exacto (ej: SAMBAYON, sé que 2160 es imposible, estimo ~1400 por tendencia, pero podría ser 1300-1500)

---

## PASO 4 — TABLA DE VENTAS FINALES

Para cada sabor, registrar:

| # | Sabor | Engine | Multi-turno | Venta final | Tipo | Confianza |
|---|---|---|---|---|---|---|
| 1 | SABOR_X | 860 | — | 860 | Limpio | 1.00 |
| 2 | SABOR_Y | 1160 | — | 1160 | Engine correcto | 0.92 |
| 3 | SABOR_Z | 2185 | Dígito 4385→6385 | 185 | Corregido MT | 0.92 |
| 4 | SABOR_W | -425 | Estimado ~330 | ~330 | Estimado | 0.70 |
| 5 | SABOR_V | 6790 | Cerrada omitida | 90 | Corregido MT | 0.80 |

---

## PASO 5 — CÁLCULO DEL TOTAL DEL DÍA

### 5.1 Cálculo base
```
Stock engine = Σ(engine_sold) de todos los sabores
```

### 5.2 Ajustes multi-turno
```
Para cada corrección aplicada en Paso 3:
  delta = venta_corregida - venta_engine

Stock corregido = Stock engine + Σ(deltas)
```

### 5.3 Componentes adicionales
```
VDP = ventas de postres (parseadas de la sección POSTRES del Excel)
Lid discount = N_latas_abiertas × 280g
```

### 5.4 Total final
```
TOTAL DÍA = Stock corregido + VDP - Lid discount
```

### 5.5 Total conservador vs total estimado

Cuando hay correcciones ESTIMADAS (no confirmadas):

- **Total conservador**: usa solo correcciones CONFIRMADAS. Las estimadas se dejan en su valor engine/raw.
- **Total estimado**: aplica TODAS las correcciones, incluyendo estimadas. Se marca explícitamente como "(estimado)".

El total principal reportado es el **conservador**. El estimado se reporta como nota al pie.

---

## PASO 6 — REGISTRO DE CASOS ABIERTOS

Al final del análisis, listar explícitamente:

### 6.1 Sospechosos sin resolver
```
Sabor: BLANCO
  Valor engine: 6790g
  Problema: cerrada 1-sighting desaparece sin abrir
  Venta probable: 90g (solo consumo abierta)
  Confianza: media-alta (forward muestra entrante similar)
  Impacto si se corrige: -6700g al total
  Requiere: PDF resuelto o segunda fuente
```

### 6.2 Latas abiertas en el período
```
Sabor: DULCE D LECHE
  Can: 0b4c13d1 (6690g)
  Turno: NOCHE
  Evidencia: ab salta 1465→6780
```

### 6.3 Impacto potencial de resolución
```
Si se resolvieran los N casos abiertos, el total podría cambiar en ±Xg.
Rango: [total_mínimo, total_máximo]
```

---

## PRINCIPIOS FÍSICOS USADOS

### P1: Conservación de masa del helado
La masa de helado en una balde solo puede:
- **Bajar**: por consumo (venta, degustación, derretimiento)
- **Subir**: por apertura de una cerrada, por agregado de entrante, o por error
- **Mantenerse**: entre cierre y apertura del turno siguiente (varianza ≤ 15-20g)

### P2: Integridad de lata cerrada
Una lata cerrada pesa entre 6000-7900g. Su peso solo cambia por:
- Varianza de pesaje: ±15-30g entre mediciones
- Error de registro: ±1000-2000g (dígito equivocado)
- Si no se abre, debe aparecer en el turno siguiente con peso similar

### P3: Apertura de cerrada
Cuando se abre una cerrada:
- La abierta salta significativamente (típicamente +4000-6500g)
- La cerrada desaparece del listado
- El tracker marca el can como "opened"

### P4: Cierre→Apertura entre turnos
Entre el cierre de un turno (NOCHE) y la apertura del siguiente (DIA):
- La diferencia en abierta es ~0g (±0-150g por condensación, acomodamiento)
- Una diferencia > 300g sugiere error o evento no registrado

### P5: Imposibilidad de subida sin fuente
Si la abierta SUBE entre DIA→NOCHE y:
- No hay apertura de cerrada (cerrada intacta)
- No hay entrante
- No hay otra fuente documentada
→ **El valor es un error de registro**. No importa la magnitud.

### P6: Existencia física de lata no abierta
Si una cerrada aparece en DIA pero no en NOCHE, y:
- La abierta no muestra salto de apertura
→ **La lata sigue existiendo**. Fue omitida en el registro de NOCHE.

---

## THRESHOLDS RÍGIDOS vs RAZONAMIENTO FÍSICO

### Partes que usan thresholds rígidos

| Threshold | Valor | Dónde se usa |
|---|---|---|
| Tolerance del tracker | 30g (default), 45-105g (adaptativo) | Matching de cans entre turnos |
| Peso máximo de lata | 7900g | Detección de error T11 |
| Lid discount | 280g por lata | Cálculo de total |
| Varianza de pesaje | ±15-30g | Distinguir "misma lata" de "lata diferente" |
| Digit typo offset | ±1000 o ±2000 | Detección automática de typo |

Estos thresholds son **instrumentales** — sirven para que el tracker funcione. No definen la verdad.

### Partes que usan razonamiento físico (sin threshold)

| Decisión | Razonamiento |
|---|---|
| ¿Se abrió la cerrada? | Mirar si la abierta salta. No hay threshold: se ve en la secuencia. |
| ¿Es error de registro? | Si un valor viola conservación de masa → es error. La magnitud no importa. |
| ¿Cuál valor es correcto (DIA o NOCHE)? | Mirar forward y backward. El que es coherente con la secuencia es correcto. |
| ¿La cerrada fue omitida o trasladada? | Mirar forward: ¿reaparece? ¿Hay entrante similar? Sin forward → incertidumbre. |
| ¿El engine acertó? | Verificar si la corrección es coherente con la secuencia física completa. |

**Principio clave: Los thresholds son herramientas del tracker. El razonamiento final es SIEMPRE físico.** Si un threshold dice "no hay anomalía" pero la secuencia física muestra imposibilidad → la secuencia física gana. Si un threshold dice "anomalía" pero la secuencia física es coherente → la secuencia física gana.

---

## REGLAS MADRE DEL SISTEMA

### RM-1: La planilla es observación ruidosa, no verdad
Cada celda del Excel es lo que un empleado anotó. No es lo que realmente pesa la lata. Tratar todo dato como observación con ruido.

### RM-2: La física no se negocia
Si un valor viola conservación de masa (abierta sube sin fuente, cerrada desaparece sin apertura), el valor es un error. No importa que el threshold del engine no lo detecte. No importa la magnitud.

### RM-3: La corrección se aplica sobre el raw, no sobre el engine
El engine puede haber aplicado correcciones incorrectas causadas por el mismo error de datos subyacente (ej: COOKIES d25 — el engine creó omission porque no vio el typo). Siempre recalcular desde el raw corregido.

### RM-4: Separar stock observado de stock reconciliado
- **Observado (raw)**: lo que dice la planilla, sin modificar
- **Reconciliado (engine)**: lo que el tracker/inference corrigieron automáticamente
- **Corregido (multi-turno)**: lo que el análisis humano determinó con la secuencia completa
Cada nivel deja trazabilidad de qué cambió y por qué.

### RM-5: Si no sabés, decí que no sabés
Si la evidencia es insuficiente para corregir (1 sighting, sin forward, sin backward), clasificar como "sospechoso sin resolver" con el valor raw/engine. Nunca inventar una explicación para cerrar el caso.

### RM-6: La confianza es continua, no binaria
No existe "correcto" o "incorrecto" absoluto. Existe:
- Confirmado (evidencia bilateral fuerte, prototipo validado)
- Estimado (evidencia física clara, valor aproximado)
- Sospechoso (anomalía detectada, evidencia insuficiente)
- Limpio (sin anomalía)

### RM-7: Forward gana sobre backward
Cuando DIA y NOCHE tienen valores contradictorios:
- Si el valor de NOCHE es coherente con los turnos POSTERIORES → NOCHE es correcto, DIA es error
- Si el valor de DIA es coherente con los turnos ANTERIORES y NOCHE no es coherente con posteriores → DIA es correcto, NOCHE es error
- La secuencia forward tiene más peso porque está "fresca" (menos turnos de propagación de error)

### RM-8: Prototipos se validan con PDF, luego se generalizan
Un patrón de error (dígito, AB_IMP, nombre inconsistente) se convierte en prototipo solo después de ser validado contra un día con PDF resuelto. Una vez validado, se aplica a otros días sin necesidad de PDF.

Prototipos validados hasta ahora:
- **Dígito cerrada**: peso difiere ±1000-2000g del historial estable del can (5+ sightings). Validado en COOKIES d25, KITKAT d26.
- **AB_IMP**: abierta cae y sube sin apertura, con drop > 2000g y recovery > 1500g. Validado en AMERICANA d25.
- **Nombre inconsistente**: dos nombres nunca coexisten, pesos coherentes. Validado en TIRAMISU/TIRAMIZU d25.
- **Cerrada 1-sighting omitida**: cerrada aparece 1 turno sin abrir, omitida en NOCHE. Validado en BLANCO d26 (con forward), DOS CORAZONES d26 (sin forward).
- **Abierta sube sin fuente**: cualquier subida de abierta sin apertura de cerrada. Validado en SAMBAYON d26, SAMBAYON AMORES d26.

### RM-9: El total conservador es el que se reporta
El total oficial usa solo correcciones CONFIRMADAS. Las correcciones ESTIMADAS se reportan por separado con su impacto potencial. Esto permite que el usuario decida qué nivel de confianza acepta.

### RM-10: Cada día se resuelve completo antes de avanzar
No resolver "solo los sospechosos". Los 50+ sabores se clasifican, los corregidos se verifican, los sospechosos se analizan. El total se cierra. Recién entonces se pasa al día siguiente.
