# Decisión metodológica: bandas de confianza v3 — aplicada al Día 5

---

## A. Problema metodológico detectado

La banda CONSERVADOR actual mezcla dos especies de justificación que no tienen el mismo peso epistemológico:

1. **Convergencia positiva**: DDL+DA tiene P1+P2 que apuntan independientemente al mismo hecho (la cerr 6555 fue mal asignada). Sabemos QUÉ pasó y POR QUÉ. La corrección tiene identidad propia.

2. **Reductio por imposibilidad**: CHOCOLATE entra al CONSERVADOR porque raw=7485g sin apertura es imposible. Sabemos que el RAW está MAL, pero la corrección específica (ent 6530~6630 = mismo can) descansa en un matching de 100g que duplica la tolerancia normal. No sabemos con la misma certeza cuál es el valor correcto exacto.

Meter ambas en la misma banda produce un CONSERVADOR que promete más de lo que puede cumplir. El usuario de la banda espera que todos los valores ahí dentro tengan el mismo tipo de respaldo. No lo tienen.

Problema secundario: el criterio de ">=2 planos" excluye correcciones como PISTACHO (digit error PF1, 3 sightings vs 1) que tienen evidencia interna fortísima dentro de un solo plano. Contar planos no captura la calidad de la justificación.

---

## B. Decisión metodológica

### 3 bandas. No 2.

Razón: la distinción entre "sé qué pasó" y "sé que el raw está roto pero mi fix es la mejor aproximación" es real y operativa. Colapsarla en una sola banda degrada la semántica del sistema. Separarla permite que el consumidor del resultado sepa exactamente qué tipo de confianza tiene cada número.

### Tipo de justificación manda. No cantidad de planos.

Razón: un solo plano con evidencia temporal masiva (ej: PF1 digit error con 3+ sightings vs 1) da más confianza que dos planos débiles que convergen por casualidad. El criterio ">=2 planos" es un proxy útil pero no es el fundamento. El fundamento es: ¿la corrección tiene anclaje suficiente para que, si apareciera evidencia nueva, sea más probable que confirme la corrección que la refute?

---

## C. Taxonomía de justificaciones

| Tipo | Nombre | Definición | Ejemplo |
|------|--------|-----------|---------|
| **A** | Convergencia independiente | >=2 planos apuntan al mismo hecho. La corrección tiene identidad causal clara. | DDL+DA: P1 (ab normales) + P2 (sightings 4v1) explican exactamente qué cerrada fue mal asignada. |
| **B** | Reductio / exclusión física | El raw es demostrativamente imposible. La corrección es el mecanismo más viable pero no el único concebible. | CHOCOLATE: sin apertura, 7485g es imposible. La corrección (ent matching 100g) es forzada. |
| **C** | Prototipo histórico fuerte | Un solo plano pero con patrón de error bien establecido y ratio de sightings alto (>=3:1). Equivalente a convergencia temporal dentro del plano. | PISTACHO: PF1 digit 6630->6330, ratio 3:1, patrón clásico de centena. |
| **D** | Ajuste plausible menor | Corrección de baja magnitud con evidencia parcial. Ni imposible ni confirmada. | CH C/ALM: pesaje variance 60g, solo P2, ambos valores (1400/1340) razonables. |

---

## D. Regla de mapeo a bandas

| Banda | Tipos que entran | Criterio operativo |
|-------|-----------------|-------------------|
| **CONFIRMADO** | A, C | La corrección tiene identidad causal o patrón histórico robusto. Si apareciera evidencia nueva, confirmaría antes que refutaría. El valor corregido tiene intervalo de confianza estrecho. |
| **FORZADO** | B | El raw es demostrativamente imposible. La corrección es la mejor explicación disponible pero tiene incertidumbre residual sobre el valor exacto. El intervalo de confianza es más ancho que en CONFIRMADO. |
| **ESTIMADO** | D, y cualquier B o C sin evidencia suficiente | Corrección plausible pero no anclada. Si se omitiera, el resultado final no se vuelve absurdo. |

### Excepciones

- Un Tipo C con ratio de sightings < 3:1 baja a ESTIMADO.
- Un Tipo B donde el mecanismo correctivo es unívoco (solo una explicación posible y es precisa) puede subir a CONFIRMADO. Esto no aplica al día 5.
- Un Tipo D con delta < 100g puede quedarse en ESTIMADO sin penalización adicional (no merece H0 por insignificancia).

---

## E. Aplicación al Día 5

### 1. DULCE D LECHE + DULCE AMORES

- **Tipo**: A (convergencia independiente)
- **Banda**: CONFIRMADO
- **Motivo**: P1 confirma que las abiertas de ambos sabores bajan normalmente (no hay anomalía en ab que requiera explicación alternativa). P2 muestra que cerr 6555 tiene 4 sightings en DDL y 1 en DA. La corrección bilateral (mover 6555 de DA a DDL en DIA) es la única explicación compatible con ambos planos. Identidad causal clara: misregistro de asignación de sabor.
- **¿Exige cambio de definición?** No. Este caso ya era CONSERVADOR con el método anterior. Sigue siéndolo.

### 2. VAINILLA

- **Tipo**: A (convergencia independiente)
- **Banda**: CONFIRMADO
- **Motivo**: P1 muestra ab 5055->4970 (descenso de 85g, normal). P2 muestra cerr 6445 persistiendo en D6D y D6N (can real, 3 sightings posteriores). La convergencia dice: la abierta no subió (no hubo error de registro en ab), el can es real (no es phantom), y no estaba antes (no hay sightings previos). Conclusión: entrante no documentado que llegó entre DIA y NOCHE. Corrección precisa: +6445 como new_entrante_B.
- **¿Exige cambio de definición?** No.

### 3. KITKAT

- **Tipo**: A (convergencia independiente)
- **Banda**: CONFIRMADO
- **Motivo**: P1 muestra declive lineal de ab (4905->4630->4400->4395->4060) con venta ~230g/turno. P2 muestra cerr 6400 con 0 sightings fuera de D5D. Los dos planos convergen: la abierta se comporta exactamente como si no hubiera cerrada (venta baja constante), y la cerrada es phantom (1-sighting aislado sin bilateral). Identidad causal: cerr 6400 fue registrada por error en KITKAT.
- **¿Exige cambio de definición?** No.

### 4. PISTACHO

- **Tipo**: C (prototipo histórico fuerte)
- **Banda**: CONFIRMADO
- **Motivo**: Cerr 6330 tiene 3 sightings (D3, D5N, D6D). Cerr 6630 tiene 1 sighting (D5D). Ratio 3:1. El patrón es PF1 digit error clásico: diferencia de 300g en la centena (63->66), error de lectura/transcripción conocido. Dentro del plano P2, los 3 sightings de 6330 constituyen convergencia temporal interna: tres observaciones independientes del mismo can en turnos distintos confirman que 6330 es la identidad real.
- **¿Exige cambio de definición?** SÍ. Con el método anterior (>=2 planos) quedaba en ESTIMADO. Con el nuevo criterio (tipo de justificación > conteo de planos), un PF1 con ratio 3:1 es CONFIRMADO. Esto es correcto: negar esta corrección requeriría asumir que tres pesajes distintos se equivocaron y el único pesaje que acertó fue D5D. Esa hipótesis alternativa es mucho más débil.
- **Delta**: -300g. Bajo impacto incluso si la clasificación fuera incorrecta.

### 5. CHOCOLATE

- **Tipo**: B (reductio / exclusión física)
- **Banda**: FORZADO
- **Motivo**: P2 prueba que no hubo apertura (cerr 6640 idéntica DIA/NOCHE, 0g diferencia). Sin apertura, raw=7485g requiere que se haya vendido más helado que el contenido total de la abierta, lo cual es físicamente imposible. El raw queda EXCLUIDO. La corrección (ent 6530~6630 = mismo can, venta=855g) es el único mecanismo disponible, pero descansa en un matching de 100g que duplica la tolerancia estándar de 50g. No hay segundo mecanismo viable; pero el mecanismo único tiene un gap inusual.
- **¿Exige cambio de definición?** SÍ. Este es exactamente el caso que motivó la separación en 3 bandas. Con 2 bandas, estaba forzado dentro de CONSERVADOR con una nota al pie incómoda. Con 3 bandas, tiene su lugar propio: FORZADO dice "el raw es imposible, el fix es el mejor disponible, pero la certeza sobre el valor exacto es menor que en CONFIRMADO."
- **Implicancia operativa**: Si el consumidor del resultado necesita un piso duro, puede usar CONFIRMADO solamente. Si acepta la mejor estimación disponible, incluye FORZADO. Esto es más honesto que meterlo en la misma bolsa que DDL+DA.

### 6. CH C/ALM

- **Tipo**: D (ajuste plausible menor)
- **Banda**: ESTIMADO
- **Motivo**: Cerr 6675->6615 (60g). Solo P2 soporta. P1 no discrimina (1400 y 1340 son ambos ventas razonables). El delta es 60g, el más bajo de todas las correcciones. Ni el raw ni el corregido generan contradicción. Es un ajuste fino plausible.
- **¿Exige cambio de definición?** No. Ya estaba en ESTIMADO y ahí debe quedarse.

---

## F. Conclusión operativa

### Decisiones tomadas

1. **3 bandas**: CONFIRMADO / FORZADO / ESTIMADO. La distinción entre evidencia positiva convergente y reductio por imposibilidad es real y operativa. Mantener 2 bandas obliga a hacer trampa con la semántica.

2. **Tipo de justificación manda sobre conteo de planos**. El criterio ">=2 planos" se mantiene como heurística interna de Tipo A, pero no es requisito universal. Tipo C (prototipo fuerte con ratio >=3:1) entra a CONFIRMADO con un solo plano dominante. El fundamento es la calidad de la evidencia, no la cantidad de fuentes.

3. **Regla de mapeo**:
   - Tipo A -> CONFIRMADO
   - Tipo B -> FORZADO (sube a CONFIRMADO solo si el mecanismo correctivo es unívoco Y preciso)
   - Tipo C -> CONFIRMADO si ratio >=3:1 y patrón PF conocido; ESTIMADO si ratio < 3:1
   - Tipo D -> ESTIMADO

### Resultado reclasificado del Día 5

| Sabor | Delta | Tipo | Banda |
|-------|-------|------|-------|
| DULCE D LECHE | +6555 | A | CONFIRMADO |
| DULCE AMORES | -6275 | A | CONFIRMADO |
| VAINILLA | +6445 | A | CONFIRMADO |
| KITKAT | -6120 | A | CONFIRMADO |
| PISTACHO | -300 | C | CONFIRMADO |
| CHOCOLATE | -6630 | B | FORZADO |
| CH C/ALM | -60 | D | ESTIMADO |

### Totales reclasificados — Ecuación final verificada

```
  40,095g  RAW
    +305g  CONFIRMADO  (DDL +6555, DA -6275, VAN +6445, KIT -6120, PIS -300)
  ------
  40,400g  PISO CONFIRMADO
  -6,630g  FORZADO     (CHOCOLATE -6630)
  ------
  33,770g  PISO CONFIRMADO+FORZADO
     -60g  ESTIMADO    (CH C/ALM -60)
  ------
  33,710g  TOTAL CORREGIDO
```

Con VDP (1,495g):

| Banda | Venta stock | + VDP | Total |
|-------|-------------|-------|-------|
| CONFIRMADO | 40,400g | 1,495g | 41,895g |
| CONFIRMADO+FORZADO | 33,770g | 1,495g | 35,265g |
| TOTAL (con ESTIMADO) | 33,710g | 1,495g | 35,205g |

Nota: CONFIRMADO > RAW (+305g) porque las correcciones de imposibles negativos (DDL +6555, VAN +6445) superan las de positivos falsos (KIT -6120). Esto es correcto: el RAW subestimaba el stock real porque no contaba la cerr omitida de DDL ni el entrante de VAINILLA.

### Qué cambia respecto del método anterior

1. PISTACHO sube de ESTIMADO a CONFIRMADO (Tipo C, PF1 con ratio 3:1).
2. CHOCOLATE sale de CONSERVADOR y entra en su propia banda FORZADO (Tipo B, reductio).
3. La semántica de cada banda es ahora unívoca:
   - CONFIRMADO = sabemos qué pasó
   - FORZADO = sabemos que el raw es imposible, el fix es el mejor disponible
   - ESTIMADO = ajuste plausible, prescindible

### Para aplicar a futuros días

- Clasificar cada corrección por tipo (A/B/C/D) ANTES de asignar banda.
- No usar ">=2 planos" como regla dura. Usarlo como indicador de Tipo A.
- Documentar el tipo en el expediente ampliado.
- Reportar las 3 bandas en el cierre de cada día.
