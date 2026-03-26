# SISTEMA DE ESCALADO — Screening día por día (v2)

Basado en: `00_metodo_operativo.md` (método), `03_historias_por_sabor.json` (datos empíricos)
Actualizado con hallazgos de: D26 ground truth, D28 ground truth

---

## PRINCIPIO RECTOR

El sistema clasifica cada sabor en un nivel de escalado.
Cada nivel determina cuánto análisis recibe.

**No todo sabor necesita análisis multi-turno.**
La mayoría son limpios. El sistema existe para encontrar los pocos que no lo son.

**El razonamiento físico es primario.** Los thresholds existen como pre-filtros
para ahorrar tiempo, pero ningún threshold puede declarar un caso "resuelto"
si la secuencia física dice lo contrario.

---

## NIVELES DE ESCALADO

### NIVEL 0: LIMPIO

**Definición**: El sabor no presenta ninguna anomalía detectable.

**Criterios (TODOS deben cumplirse)**:

1. `engine_sold == raw_sold` (el engine no aplicó correcciones)
2. `raw_sold >= -50g` (la venta no es significativamente negativa)
3. `raw_sold < 5000g` O hay una apertura de cerrada documentada que la explique
4. La abierta no sube entre DIA→NOCHE (o sube ≤20g, que es varianza de pesaje)
5. No hay cerradas con 1 solo sighting que desaparezcan sin apertura

**Acción**: Usar raw_sold directamente. No requiere análisis posterior.

**Base empírica**: La varianza de pesaje de cerrada es media=3g, p99=30g.
La varianza cierre→apertura de abierta es mediana=0g, p90=5g.
Cualquier cosa dentro de estos rangos es ruido de medición.

---

### NIVEL 1: CORREGIDO POR ENGINE

**Definición**: El engine (tracker + inference) aplicó alguna corrección automática.

**Detección**: `engine_sold != raw_sold`

**Sub-tipos y verificación**:

#### 1a. Omission
El engine detectó que una cerrada con historial falta en un turno.

**Verificación física**:
- ¿El can tiene ≥3 sightings? → Sí: evidencia sólida de existencia
- ¿Aparece en el turno anterior Y posterior al faltante? → Sí: omisión bilateral
- ¿La abierta confirma que no hubo apertura? (cambio ≤150g)
- Si las 3 respuestas son sí → **Engine correcto** (confianza 0.92)
- Si falta el turno posterior → Verificar forward más amplio (±3 turnos)

#### 1b. Phantom
El engine marcó un valor como fantasma (sin match en ningún can tracked).

**Verificación física**:
- ¿Podría ser un entrante no documentado? (lata nueva que llegó sin registrar)
- ¿La abierta muestra salto grande? (→ alguien abrió algo, la phantom es una lata real)
- ¿El peso está en rango de cerrada (6000-7500g)?
- Si el peso es plausible como cerrada real y hay apertura → **Engine cuestionable**
- Si no hay explicación alternativa → **Engine correcto** (confianza 0.70-0.85)

#### 1c. Digit typo
El engine detectó un peso con offset ±1000-2000g del historial estable.

**Verificación física**:
- ¿El can tiene ≥5 sightings a peso estable (varianza ≤30g)?
- ¿El offset es exacto ±1000 o ±2000g?
- ¿Turno anterior y posterior muestran peso normal?
- Si todo sí → **Engine correcto** (confianza 0.92)

#### 1d. Doble omission / corrección compuesta
El engine aplicó más de una corrección al mismo sabor.

**Verificación**: Cada corrección individual se verifica por separado.
Confianza = mínimo de las confianzas individuales.

**Resultado de NIVEL 1**:
- Engine verificado → usar valor del engine, documentar verificación
- Engine cuestionable → escalar a NIVEL 2 para análisis multi-turno
- Engine incorrecto → escalar a NIVEL 2, marcar como "engine overridden"

---

### NIVEL 2: SOSPECHOSO

**Definición**: El engine no corrigió nada (o su corrección es cuestionable), pero
el valor crudo presenta una anomalía que viola la física o la estadística.

**Detección**: Cualquiera de estas condiciones dispara el escalado:

#### S1: Venta negativa significativa
`raw_sold < -200g`

No se usa un threshold menor porque la varianza de pesaje combinada
(abierta + cerradas) puede producir diferencias de hasta ±50g por medición,
y errores de redondeo hasta ±100g. Pero -200g ya está muy lejos del ruido.

**Sin embargo**: si la abierta sube sin explicación, el caso se escala
SIN IMPORTAR la magnitud (ver S2).

#### S2: Abierta sube sin fuente — IMPOSIBILIDAD FÍSICA
`abierta_NOCHE > abierta_DIA + 20g` Y no hay apertura de cerrada ni entrante.

**Este es el detector más importante del sistema.** No tiene threshold mínimo
porque cualquier subida sin fuente es físicamente imposible.

El "+20g" es margen de varianza de pesaje (empírico p90=5g, se usa 20g
como margen conservador). Todo lo que supere esto es anomalía.

**Verificación**:
- ¿Alguna cerrada desapareció entre DIA y NOCHE? → Si sí: es apertura legítima, no anomalía
- ¿Hay entrante nuevo en NOCHE? → Si sí: puede explicar la subida
- ¿La cerrada está intacta (varianza ≤30g)? → Si sí: confirma que no hubo apertura

**Base empírica**: De 1209 transiciones DIA→NOCHE observadas, 144 (11.9%) muestran
abierta subiendo. De esas 144, 83 tienen cerrada desaparecida (apertura legítima).
Las 43 restantes sin cerrada desaparecida se dividen en:
- 30 con delta >4000g: aperturas reales donde el matching falló (cerrada nueva reemplazó a la abierta)
- 8 con delta 1000-4000g: mezcla de aperturas y errores
- 5 con delta 150-1000g: probables errores de pesaje/registro

#### S3: Venta excesiva sin apertura
`raw_sold > 5000g` Y no hay apertura de cerrada documentada.

Una venta >5000g es físicamente posible solo si se abrió al menos una cerrada.
Si no hay apertura visible, probablemente hay una cerrada fantasma (1-sighting)
o un error de registro.

#### S4: Cerrada 1-sighting
Una cerrada aparece en un solo turno y desaparece sin apertura.

**Detección**:
- Cerrada presente en DIA pero no en NOCHE (o viceversa)
- La cerrada no tiene historial en el tracker (1 sighting)
- La abierta no muestra salto de apertura (cambio <3000g)

**Esto es una anomalía de stock, no de venta.** La cerrada existía físicamente
pero fue omitida. La venta cruda incluye su peso como "vendido" cuando en
realidad la lata sigue existiendo.

---

### NIVEL 3: SOSPECHOSO + DÍGITO

**Definición**: Un valor (cerrada o abierta) contiene un error de dígito no
detectado por el engine.

**Detección**:

#### D1: Dígito en cerrada
- La cerrada difiere ~1000 o ~2000g del peso histórico estable del can
- El can tiene ≥5 sightings con varianza ≤30g
- El turno anterior y posterior muestran el peso normal

**Señales típicas**:
- `5705` en vez de `6705` (offset -1000)
- `4385` en vez de `6385` (offset -2000)
- La diferencia es EXACTAMENTE ~1000 o ~2000, no un valor intermedio

#### D2: Dígito en abierta
- La abierta difiere ~1000g del valor esperado por la tendencia
- La secuencia forward confirma que el valor posterior es correcto
- La secuencia backward confirma que el valor anterior era coherente

**Diferencia con S2 (abierta imposible)**: En S2, la abierta SUBE sin fuente.
En D2, la abierta CAJA por error de dígito (ej: 6450 anotado como 5450).
D2 se detecta por la incoherencia con la tendencia, no por la dirección del cambio.

---

## DETECCIÓN DE ANOMALÍAS ESPECÍFICAS

### Anomalía física: abierta imposible (AB_IMP)

**Principio**: La masa de helado en una balde solo puede bajar (consumo) o
mantenerse (cierre→apertura). Subir requiere una fuente documentada.

**Protocolo de detección**:

```
1. Calcular delta = abierta_B - abierta_A
2. Si delta > 20g:
   a. ¿Desapareció alguna cerrada entre A y B?
      → Sí: apertura legítima, NO es anomalía
   b. ¿Hay entrante nuevo en B?
      → Sí: verificar si el entrante explica la subida
   c. ¿La cerrada está intacta (mismos pesos ±30g)?
      → Sí: confirma que no hubo apertura
   d. Si ninguna fuente explica la subida → AB_IMP confirmado
3. Determinar cuál valor es correcto:
   a. Verificar forward: ¿El turno siguiente es coherente con A o con B?
   b. Verificar backward: ¿El turno anterior es coherente con A?
   c. Aplicar principio RM-7: forward pesa más que backward
   d. Aplicar ancla cierre→apertura: diferencia entre turnos es ~0g
```

**No hay threshold de magnitud.** Una subida de 430g (SAMBAYON d26) es tan
imposible como una de 2715g (AMERICANA d25). La diferencia es la confianza
en la corrección, no en la detección.

### Cerrada fantasma (1-sighting)

**Principio**: Una cerrada que aparece 1 solo turno y desaparece sin ser
abierta probablemente fue omitida en el turno siguiente.

**Protocolo de detección**:

```
1. Cerrada presente en turno A pero no en turno B
2. Abierta de B no muestra salto (delta < 3000g)
3. El tracker no tiene historial del can (o tiene 1 solo sighting)
4. → La cerrada no fue vendida. Fue omitida o trasladada.
```

**Verificación forward**:
- ¿La cerrada reaparece en un turno posterior como entrante?
  → Sí: omisión confirmada (confianza media-alta)
  → No: podría ser omisión o traslado (confianza media)

**Verificación de apertura post-desaparición**:
- ¿En algún turno posterior la abierta salta sin cerrada visible?
  → Sí: la cerrada fue abierta sin registrar la apertura

### Error de dígito

**Principio**: Los empleados a veces omiten o cambian un dígito al anotar.
Los offsets típicos son ±1000 o ±2000.

**Protocolo de detección**:

```
1. Para cada cerrada en el turno:
   a. Buscar en el historial del tracker un can estable (≥5 sightings)
      cuyo peso difiera exactamente ~1000 o ~2000 del valor actual
   b. Verificar: |peso_actual - (peso_histórico ± N*1000)| ≤ 30g para N=1,2
   c. Si match: verificar turno anterior y posterior tienen peso normal
2. Para la abierta:
   a. Calcular valor esperado por tendencia (promedio de prev y next)
   b. Si |abierta - esperada| es ~1000g: candidato a dígito
   c. Verificar: forward confirma el valor corregido
```

**Clave**: El error de dígito se confirma por HISTORIAL ESTABLE, no por
magnitud del error. Un can con 11 sightings a ~6700g que aparece como 5700
es casi seguramente un error de dígito. Un can con 2 sightings no tiene
suficiente evidencia.

### Cerrada omitida en DIA (CERRADA_OMITIDA_EN_DIA) — *nuevo D28*

**Principio**: Una cerrada que existe físicamente en ambos turnos fue omitida
del registro DIA. Aparece solo en NOCHE, causando venta negativa o reducida.
Es el espejo de la omisión en NOCHE (ya conocida).

**Protocolo de detección**:

```
1. raw_sold muy negativo (< -200g)
2. Cerrada en NOCHE que NO tiene match en DIA (±30g)
3. La cerrada tiene historial previo (≥2 sightings en turnos anteriores)
4. La abierta baja normalmente (consumo coherente, no hay apertura)
5. → La cerrada existía en DIA pero fue omitida del registro
```

**Corrección**: agregar la cerrada faltante al total_DIA. Recalcular vendido.

**Diferencia con omisión en NOCHE**: la omisión en NOCHE infla la venta (falso
positivo de stock vendido). La omisión en DIA infla el stock NOCHE relativo,
causando venta negativa (falso negativo). Efecto opuesto, misma mecánica.

**Caso validado**: CHOCOLATE D28 — cerr 6545 existía (era entrante D27),
omitida de DIA. Raw=-3635 → corregido=2910. Confirmado por PDF.

**Firma clave**: venta muy negativa + cerrada NOCHE sin match en DIA +
cerrada con historial rastreable.

---

### Apertura única con phantom (APERTURA_UNICA_CON_PHANTOM) — *nuevo D28*

**Principio**: De N cerradas listadas en DIA, solo M<N existen realmente.
Las restantes son phantom. Las que existen pueden haber sido abiertas.
Sin detectar los phantoms, el engine sobreestima la venta y/o las latas.

**Protocolo de detección**:

```
1. Venta muy alta (>5000g) con múltiples cerradas desaparecidas
2. El salto de abierta es coherente con MENOS aperturas de las que
   sugiere el conteo bruto de cerradas desaparecidas
3. Para cada cerrada desaparecida, verificar:
   a. ¿Tiene historial previo (≥2 sightings)? → Probablemente real
   b. ¿Apareció solo este turno sin entrante? → Probablemente phantom
   c. ¿Fue abierta en un turno anterior? → Phantom seguro (RM-3)
4. Recalcular con solo las cerradas reales
```

**Corrección**: poner phantom en 0, ajustar conteo de latas.

**Caso validado**: CHOCOLATE DUBAI D28 — de 2 cerradas (6400, 6355), solo
6355 existía. 6400 phantom. Solo 1 lata abierta (no 2). Raw=8140 → corr=1740.
PISTACHO D28 — cerr 6350 phantom. 0 latas (no 1). Raw=7900 → corr=1550.
SAMBAYON D28 — cerr 6450 phantom (abierta D27). Raw=7105 → corr=655.

**Firma clave**: venta alta + ab sube menos de lo esperado para N aperturas +
cerrada sin historial o con historial de apertura previa.

---

### Nombre inconsistente

**Principio**: El mismo sabor físico aparece con nombres distintos en turnos
diferentes, típicamente por empleados distintos (DIA vs NOCHE).

**Protocolo de detección**:

```
1. Buscar pares de sabores que NUNCA coexisten en el mismo turno
2. Verificar que los pesos son coherentes:
   a. Abierta decae gradualmente entre el "cierre" de nombre A
      y la "apertura" de nombre B
   b. Cerradas tienen pesos similares (±30g)
3. Verificar que uno tiene muchos turnos y el otro tiene 1-2
4. Si todo se cumple: son el mismo sabor con nombre inconsistente
```

**Prototipos validados**: TIRAMIZU/TIRAMIsU (d25)

**Candidatos permanentes a verificar por hoja nueva**: KITKAT/KIT KAT/KIYKAT
(ya normalizado en CSV, pero verificar que la normalización fue correcta).

---

## CRITERIOS DE CONFIANZA

### Confianza ALTA (0.90-1.00): Corrección confirmada

La corrección está respaldada por:
- Evidencia bilateral (turno anterior + posterior coherentes)
- Historial estable del tracker (≥5 sightings)
- Prototipo validado contra PDF
- Imposibilidad física clara

**Ejemplos**:
- Dígito en cerrada con 11 sightings (COOKIES d25, KITKAT d26)
- Omisión con can de 9 sightings bilateral (CH C/ALM d26, SUPER d26)

### Confianza MEDIA (0.60-0.89): Corrección estimada

La corrección está respaldada por:
- Evidencia unilateral (solo forward O solo backward)
- Imposibilidad física clara pero sin valor exacto de reemplazo
- Historial del tracker con 3-4 sightings

**Ejemplos**:
- AB_IMP con forward coherente pero sin valor exacto (SAMBAYON d26: ~330g estimado)
- Cerrada 1-sighting con entrante posterior (BLANCO d26: forward sugiere continuidad)

### Confianza BAJA (0.40-0.59): Sospecha documentada

Hay indicios de error pero:
- Solo evidencia indirecta
- Sin prototipo validado
- Historial insuficiente (1-2 sightings)
- Múltiples explicaciones posibles

**Ejemplos**:
- Cerrada 1-sighting sin forward ni backward (DOS CORAZONES d26)
- Phantom que podría ser entrante no documentado (DULCE D LECHE d26)

### H0: Sin corrección

La evidencia es insuficiente para aplicar cualquier corrección.
Se mantiene el valor raw/engine.

**Cuándo aplica**:
- No hay prototipo validado que matchee
- La anomalía podría tener múltiples explicaciones equiprobables
- El impacto de una corrección incorrecta es mayor que el de no corregir

---

## CUÁNDO UNA CORRECCIÓN CAMBIA MASA vs INTERPRETACIÓN

### Correcciones que cambian MASA REAL del día

Estas correcciones modifican el total de gramos vendidos del día:

| Corrección | Efecto en masa | Ejemplo |
|-----------|----------------|---------|
| Dígito en cerrada | Cambia total_A o total_B | KITKAT 4385→6385: -2000g en venta |
| AB_IMP | Cambia abierta de A o B | AMERICANA 1650→4365: +2715g en total_A |
| Cerrada 1-sighting omitida | Quita cerrada del cálculo | BLANCO 6790→90: -6700g en venta |
| Phantom removido | Quita valor fantasma | DULCE D LECHE: +6635g si se restituye |

### Correcciones que cambian INTERPRETACIÓN pero no masa total del día

| Corrección | Efecto | Ejemplo |
|-----------|--------|---------|
| Nombre inconsistente | Redistribuye entre dos sabores | TIRAMISU/TIRAMIZU: neto 0g |
| Celiaca→Cerrada | Mueve peso entre columnas | DULCE AMORES d16: misma masa, distinto slot |

**Principio**: Las correcciones de masa se reportan como ajustes al total.
Las correcciones de interpretación se reportan como notas pero no cambian el total.

---

## CUÁNDO UN CASO QUEDA EN H0

Un caso queda en H0 (sin corregir) cuando se cumple CUALQUIERA de:

1. **Sin prototipo**: La anomalía no matchea ningún patrón validado contra PDF
2. **Evidencia insuficiente**: Solo 1 sighting, sin forward ni backward
3. **Múltiples explicaciones**: La anomalía podría ser error de pesaje, traslado,
   o dato legítimo con igual probabilidad
4. **Magnitud ambigua**: La subida/baja está en la zona gris donde podría ser
   varianza de pesaje extrema (150-300g para abierta)
5. **Engine ya corrigió razonablemente**: El engine aplicó una corrección plausible
   y no hay evidencia de que esté mal

**H0 no significa "el valor es correcto".** Significa "no tenemos evidencia
suficiente para cambiarlo". El caso queda documentado como sospechoso para
revisión futura o resolución con PDF.

---

## ORDEN DE DECISIÓN

El análisis de cada día sigue esta secuencia estricta.
Cada paso depende del anterior. No se puede saltar ni reordenar.

### Fase 0: Preparación
```
0.1  Identificar los turnos del día (DIA, NOCHE o UNICO)
0.2  Extraer todos los sabores con sus slots raw
0.3  Calcular raw_sold para cada sabor: total_A - total_B
0.4  Obtener engine_sold del motor de inferencia
```

### Fase 1: Clasificación inicial
```
Para cada sabor:
1.1  ¿engine_sold == raw_sold?
     → Sí: candidato a LIMPIO (verificar en 1.2)
     → No: marcar como CORREGIDO POR ENGINE (NIVEL 1)

1.2  Para candidatos LIMPIO, verificar:
     a. raw_sold >= -50g
     b. raw_sold < 5000g O hay apertura documentada
     c. abierta_B <= abierta_A + 20g (o hay apertura)
     d. No hay cerrada 1-sighting que desaparezca
     → Todo OK: NIVEL 0 (LIMPIO)
     → Alguno falla: NIVEL 2 (SOSPECHOSO)
```

### Fase 2: Verificación de correcciones del engine
```
Para cada sabor NIVEL 1:
2.1  Identificar tipo de corrección (omission/phantom/digit_typo/etc)
2.2  Aplicar protocolo de verificación según tipo
2.3  Resultado:
     → Engine correcto: mantener en NIVEL 1, usar valor engine
     → Engine cuestionable: escalar a NIVEL 2
     → Engine incorrecto: escalar a NIVEL 2, marcar "engine overridden"
```

### Fase 3: Screening de dígito
```
Para cada sabor NIVEL 2:
3.1  Comparar cada cerrada contra el historial del tracker
3.2  ¿Hay offset de ±1000 o ±2000 respecto a un can estable (≥5 sightings)?
     → Sí: escalar a NIVEL 3 (SOSPECHOSO + DÍGITO)
3.3  Comparar abierta contra tendencia prev/next
3.4  ¿Hay offset de ~1000g con forward coherente?
     → Sí: escalar a NIVEL 3
```

**El screening de dígito se hace ANTES del análisis multi-turno** porque un
dígito no detectado puede causar que el engine aplique correcciones incorrectas
(ej: COOKIES d25 — el engine creó omission porque no vio el typo).

### Fase 3.5: Precedencias de corrección — *nuevo v2*

**Problema que resuelve**: en D28, la auditoría sobrecorrigió SAMBAYON
(eliminó 2 cerradas cuando solo 1 era phantom) y CHOCOLATE DUBAI (contó
2 aperturas cuando solo 1 cerrada existía). Esto sucede por aplicar
correcciones sin un orden de prioridad que preserve el stock real mínimo.

**Regla maestra**: preservar la explicación más simple que sea coherente
con la física. No eliminar stock sin evidencia directa.

**Orden de precedencia (obligatorio)**:

```
P1. PRESERVAR recipientes reales mínimos
    - Toda cerrada se asume REAL salvo evidencia directa en contra.
    - "Sin historial previo" NO es suficiente para declarar phantom.
      Un entrante no documentado produce una cerrada sin historial
      que es perfectamente real.
    - Solo declarar phantom si:
      a. La lata fue abierta en turno anterior (RM-3: no puede resellarse), O
      b. Nota humana explícita dice "no existe", O
      c. La lata aparece en DIA y desaparece en NOCHE sin apertura
         Y ab no sube Y no reaparece en turnos posteriores
         Y no hay entrante que la explique.

P2. ELIMINAR phantoms explícitos
    - Solo los que cumplen P1.a, P1.b o P1.c.
    - Poner en 0 en el turno correspondiente.
    - Documentar la evidencia específica.

P3. COMPLETAR omisiones compatibles
    - Si una cerrada existe en NOCHE pero no en DIA (o viceversa),
      y tiene historial previo (≥2 sightings), agregarla al turno faltante.
    - Prioridad: omisiones con historial > omisiones sin historial.

P4. RECALCULAR aperturas y venta
    - Contar latas SOLO después de P1-P3.
    - Verificar cada apertura: ¿ab sube coherente con la cerrada desaparecida?
    - Si ab sube menos de lo esperado para N aperturas, considerar
      que alguna cerrada desaparecida es phantom (volver a P1).

P5. NO eliminar cerrada adicional salvo evidencia directa
    - Si después de P1-P4 queda una cerrada "extra" sin explicación,
      mantenerla como real y documentar la incertidumbre.
    - Ejemplo: SAMBAYON D28 cerr 6675 — sin historial pero el PDF
      la mantiene como real. No asumir phantom sin nota explícita.
```

**Anti-patrones que este orden previene**:
- ✗ Eliminar cerrada por "no tiene historial" → puede ser entrante no documentado
- ✗ Contar 2 latas cuando ab solo justifica 1 → la segunda cerrada era phantom
- ✗ Asumir omisión en NOCHE cuando el phantom está en DIA → invertir la corrección

---

### Fase 4: Análisis multi-turno
```
Para cada sabor NIVEL 2 o NIVEL 3:
4.1  Extraer timeline completa del sabor (todo el mes)
4.2  Aplicar detectores en este orden (respetando P1-P5 de Fase 3.5):

     a. DÍGITO (si NIVEL 3)
        - Confirmar offset con historial
        - Corregir valor
        - Recalcular raw con valor corregido

     b. PHANTOM (cerrada/entrante que no existe)
        - Aplicar criterios P1: solo eliminar con evidencia directa
        - Verificar RM-3 (abierta previa no puede reaparecer como cerrada)
        - Poner en 0 los phantoms confirmados

     c. CERRADA_OMITIDA (en DIA o en NOCHE)
        - Buscar cerradas que existen en un turno pero no en el otro
        - Verificar historial (≥2 sightings → omisión probable)
        - Agregar al turno faltante

     d. ENTRANTE_DUPLICADO
        - Entrante DIA que persiste en NOCHE tras ser abierto
        - Poner entrante NOCHE en 0

     e. AB_IMP (abierta imposible)
        - Verificar si abierta sube sin fuente
        - Determinar cuál valor es correcto (forward > backward)
        - Estimar valor corregido

     f. NOMBRE INCONSISTENTE
        - Verificar si hay par que nunca coexiste
        - Verificar coherencia de pesos
        - Combinar si confirmado

     g. APERTURA (recalcular latas)
        - Contar solo DESPUÉS de aplicar a-f
        - Verificar cada apertura contra salto de abierta

4.3  Asignar confianza según criterios (alta/media/baja/H0)
4.4  Registrar corrección o documentar como sospechoso sin resolver
```

**El orden dentro de 4.2 importa (actualizado v2)**:
- Dígito primero: puede invalidar correcciones del engine
- Phantom segundo: reducir stock ficticio antes de buscar omisiones
- Omisión tercero: completar stock real faltante
- Entrante dup cuarto: limpiar doble conteo
- AB_IMP quinto: depende de que cerradas ya estén limpias
- Nombre sexto: requiere visión de sabores "vecinos"
- Apertura último: se calcula sobre el stock ya corregido

### Fase 5: Cálculo del total
```
5.1  Para cada sabor, determinar venta_final:
     - LIMPIO: usar raw_sold
     - ENGINE CORRECTO: usar engine_sold
     - CORREGIDO MT: usar valor corregido multi-turno
     - H0: usar raw_sold o engine_sold según caso

5.2  Stock corregido = Σ(venta_final) de todos los sabores
5.3  Total = Stock corregido + VDP - lid_discount
5.4  Reportar total conservador (solo correcciones confirmadas)
     y total estimado (incluyendo correcciones media confianza)
```

### Fase 6: Registro
```
6.1  Tabla completa: sabor, engine, multi-turno, venta_final, tipo, confianza
6.2  Casos abiertos: sospechosos sin resolver con impacto potencial
6.3  Latas abiertas: detalle con can ID y turno
6.4  Rango de incertidumbre: [total_mínimo, total_máximo]
```

---

## RESUMEN VISUAL (v2)

```
                    ┌──────────────────┐
                    │  Todos los sabores │
                    │    del día (N~52)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Fase 1:          │
                    │  Clasificación    │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌────▼────┐  ┌──────▼──────┐
       │  NIVEL 0    │ │ NIVEL 1 │  │  NIVEL 2    │
       │  LIMPIO     │ │ ENGINE  │  │ SOSPECHOSO  │
       │  (~44/52)   │ │ (~4/52) │  │  (~4/52)    │
       └──────┬──────┘ └────┬────┘  └──────┬──────┘
              │              │              │
              │         ┌────▼────┐    ┌────▼────┐
              │         │ Fase 2: │    │ Fase 3: │
              │         │ Verif.  │    │ Dígito? │
              │         └────┬────┘    └────┬────┘
              │              │              │
              │         ┌────▼────┐    ┌────▼────┐
              │         │Correcto?│    │ NIVEL 3 │
              │         │  Sí/No  │    │ +DÍGITO │
              │         └────┬────┘    └────┬────┘
              │              │              │
              │              │    ┌─────────▼─────────┐
              │              │    │  Fase 3.5:         │
              │              │    │  PRECEDENCIAS P1-P5│
              │              │    │  (preservar→eliminar│
              │              │    │   →completar→contar)│
              │              │    └─────────┬─────────┘
              │              │              │
              │              │         ┌────▼─────┐
              │              │         │  Fase 4: │
              │              │         │  Multi-  │
              │              │         │  turno   │
              │              │         │  (a→g)   │
              │              │         └────┬─────┘
              │              │              │
              │              │    ┌─────────┼─────────┐
              │              │    │         │         │
              │              │ ┌──▼──┐  ┌───▼──┐  ┌──▼──┐
              │              │ │CONF.│  │EST.  │  │ H0  │
              │              │ │ALTA │  │MEDIA │  │     │
              │              │ └──┬──┘  └───┬──┘  └──┬──┘
              │              │    │         │        │
              └──────────────┴────┴─────────┴────────┘
                                  │
                         ┌────────▼────────┐
                         │  Fase 5: Total  │
                         │  del día        │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  Fase 6:        │
                         │  Registro +     │
                         │  Scorecard      │
                         └─────────────────┘
```

---

## DATOS EMPÍRICOS DE REFERENCIA

Extraídos de `03_historias_por_sabor.json` (Febrero 2026, 52 turnos):

| Métrica | Valor | Uso |
|---------|-------|-----|
| Varianza pesaje cerrada (p99) | 30g | Tolerance para matching de cans |
| Cierre→apertura abierta (mediana) | 0g | Ancla para verificar coherencia entre turnos |
| Cierre→apertura abierta (p95) | 10g | Margen normal |
| Cierre→apertura abierta (>150g) | 11.2% | Zona de sospecha |
| DIA→NOCHE abierta sube (total) | 144/1209 (11.9%) | Incluye aperturas legítimas |
| DIA→NOCHE abierta sube sin cerr gone | 43/1209 (3.6%) | Mezcla de aperturas no capturadas y errores |
| DIA→NOCHE abierta sube >4000g sin cerr gone | 30 casos | Casi todos son aperturas reales con matching fallido |
| DIA→NOCHE abierta sube 150-1000g sin cerr gone | 5 casos | Probables errores de registro |

---

## MÉTRICA DE EVALUACIÓN DE RESOLUCIONES — *nuevo v2*

Cada sabor resuelto se clasifica contra el ground truth (PDF humano)
en exactamente UNA de estas categorías:

### AC — Acierto completo

La corrección aplicada coincide con el ground truth en:
- Valor numérico final (±50g)
- Tipo de corrección (phantom, omisión, dígito, etc.)
- Dirección de la corrección (en qué turno se modifica el dato)

**Ejemplo**: MARACUYA D28 — auditoría dijo "entrante dup NOCHE, corr=555g",
GT dice lo mismo. AC.

### AN — Acierto numérico, interpretación errónea

El valor final coincide con el GT (±50g) pero la explicación es distinta.
El resultado fue correcto por razones parcialmente equivocadas.

**Ejemplo**: PISTACHO D28 — auditoría dijo "cerrada omitida en NOCHE" (agregar
6350 a NOCHE). GT dice "cerrada phantom en DIA" (poner 6350 en 0 en DIA).
Ambos dan venta=1550g pero la corrección real está en turno opuesto.

**Riesgo**: un AN puede acertar en un caso pero fallar en otro donde la
dirección importa. Requiere revisión del detector.

### FA — Falso abierto

El sistema dejó el caso como UNRESOLVED/H0 cuando el GT tiene resolución
explícita. El sistema tenía suficiente evidencia para resolver pero no lo hizo.

**Ejemplo**: CHOCOLATE D28 — auditoría lo dejó como UNRESOLVED (0g conservador),
GT muestra corrección clara (cerr 6545 omitida en DIA, corr=2910g).

**Causa típica**: el patrón existía (cerr sin match en DIA) pero el detector
no lo buscó porque solo buscaba omisiones en NOCHE.

### SC — Sobrecorrección

El sistema aplicó una corrección más agresiva que el GT. Eliminó stock real
o contó latas de más.

**Ejemplo**: CHOCOLATE DUBAI D28 — auditoría contó 2 latas (ambas cerradas
abiertas). GT dice 1 sola cerrada existía (6400 phantom), 1 lata. La
auditoría vendió 7580g vs GT 1740g. Sobrecorrección de +5840g.

**Ejemplo 2**: SAMBAYON D28 — auditoría (estimado) eliminó ambas cerradas DIA.
GT solo elimina 6450 (phantom confirmado), mantiene 6675 como real.

**Causa típica**: asumir que "sin historial = phantom" en vez de aplicar P1
("toda cerrada se asume real salvo evidencia directa").

### OP — Omisión de patrón

El sistema no detectó un patrón que el GT usa para corregir. El patrón
estaba fuera del catálogo de detectores.

**Ejemplo**: CERRADA_OMITIDA_EN_DIA no existía como prototipo antes de D28.
La auditoría buscó omisiones en NOCHE pero no en DIA.

**Acción**: agregar el prototipo al catálogo y re-evaluar casos previos.

---

### Tabla de evaluación por día

Formato para registrar resultados de cada auditoría contra su GT:

```
| Sabor          | Aud. venta | GT venta | Δ       | Clasif. | Nota                          |
|----------------|------------|----------|---------|---------|-------------------------------|
| EJEMPLO_1      | 555        | 555      | 0       | AC      | Match exacto                  |
| EJEMPLO_2      | 1550       | 1550     | 0       | AN      | Mismo valor, turno invertido  |
| EJEMPLO_3      | 0 (unres.) | 2910     | -2910   | FA      | Patrón no detectado           |
| EJEMPLO_4      | 7580       | 1740     | +5840   | SC      | Phantom no detectado          |
| EJEMPLO_5      | 555        | 655      | -100    | SC      | Sobre-eliminó cerr real       |
```

### Scorecard del día

```
Total sabores:        N
Aciertos completos:   AC  (objetivo: >90%)
Aciertos numéricos:   AN  (aceptable <5%)
Falsos abiertos:      FA  (objetivo: 0)
Sobrecorrecciones:    SC  (objetivo: 0)
Omisiones de patrón:  OP  (se reduce con cada día auditado)
Delta total:          Σ|Δ|  (objetivo: <1000g)
```

---

## SCORECARD D28 (retroactivo)

| Sabor | Aud. venta | GT venta | Δ | Clasif. | Nota |
|-------|-----------|---------|-------|---------|------|
| MARACUYA | 555 | 555 | 0 | **AC** | Entrante dup, match exacto |
| PISTACHO | 1,550 | 1,550 | 0 | **AN** | Mismo valor, auditoría dijo omisión NOCHE, GT dice phantom DIA |
| CHOCOLATE | 0 (unres.) | 2,910 | −2,910 | **FA** | No detectó CERRADA_OMITIDA_EN_DIA |
| CHOC DUBAI | 7,580 | 1,740 | +5,840 | **SC** | Asumió 2 latas, GT dice 1 (phantom 6400) |
| SAMBAYON | 555 (est.) | 655 | −100 | **SC** | Eliminó cerr 6675 real, GT solo elimina 6450 |
| *47 LIMPIOS* | *correctos* | *correctos* | 0 | **AC** | Sin corrección necesaria |

```
Total sabores:        52
Aciertos completos:   48 (92.3%)  [47 LIMPIO + MARACUYA]
Aciertos numéricos:    1 (1.9%)   [PISTACHO]
Falsos abiertos:       1 (1.9%)   [CHOCOLATE]
Sobrecorrecciones:     2 (3.8%)   [CHOC DUBAI, SAMBAYON]
Omisiones de patrón:   1          [CERRADA_OMITIDA_EN_DIA]
Delta total:          8,850g
```

**Lecciones incorporadas en v2**:
- Agregar detector CERRADA_OMITIDA_EN_DIA (previene FA)
- Agregar precedencia P1 "preservar recipientes reales" (previene SC)
- Agregar detector APERTURA_UNICA_CON_PHANTOM (previene SC en latas)
