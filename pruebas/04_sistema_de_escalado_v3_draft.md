# SISTEMA DE ESCALADO v3 — Arquitectura por capas (DRAFT)

Basado en: v2 vigente (congelada 2026-03-20)
Propuesta: rama de diseño paralela. NO reemplaza el baseline operativo.

---

## CAMBIO FUNDAMENTAL RESPECTO DE v2

v2 trata el análisis como un pipeline lineal: clasificar → verificar → corregir → contar.
v3 separa el sistema en **5 capas con responsabilidades estrictas** y agrega:
- expediente ampliado de 4 planos solo para casos realmente escalados
- resolución por coherencia conjunta, no por señal única
- segunda pasada residual para falsos LIMPIO
- manejo honesto de ambigüedad (conjunto vs individual vs diferida)
- marcas de calidad del dato (estática sospechosa)

**Lo que NO cambia**: la fórmula de venta, los prototipos validados (PF1-PF8),
las precedencias P1-P5, el scorecard AC/AN/FA/SC/OP.

---

## ARQUITECTURA DE 5 CAPAS

### Capa 1 — Parser / Estructura

**Responsabilidad**: leer el workbook y entregar datos crudos sin interpretación.

Pertenece a esta capa:
- Detección de hojas válidas (A1='SABORES')
- Lectura de columnas: A=sabor, B=abierta, C=celiaca, D-I=cerradas, J-K=entrantes
- Detección de fila POSTRES y sección posterior
- Manejo de variantes de estructura: columna G irrelevante, POSTRES variable
- Lectura literal de ab=None / ab='' / ab=0 **sin colapsar prematuramente**
  - `ab=None` → no se registró (dato faltante)
  - `ab=''` → celda vacía explícita (posible intención de 0)
  - `ab=0` → cero explícito (balde vacío o no hay abierta)
  Estas distinciones se preservan para que capas superiores decidan.
- Filtrado de hojas vacías (0 sabores)

**NO pertenece a esta capa**: ninguna inferencia, corrección ni interpretación.

---

### Capa 2 — Contrato contable

**Responsabilidad**: definir la fórmula de venta como regla global del sistema.

```
venta_stock_bruta = total_A + new_entrantes_B - total_B - ajuste_latas
total = abierta + celiaca + sum(cerradas) + sum(entrantes)
new_entrantes_B = entrantes en B que NO estaban en A (dentro de 50g)
ajuste_latas = max(0, n_cerradas_A - n_cerradas_B) * 280
```

Esta fórmula es **definición global**. No se resuelve por historial, expediente ni inferencia.
Cualquier corrección en capas superiores modifica los inputs (totales), no la fórmula.

También pertenece aquí:
- Separación de VDP (ventas de postres) como componente aparte
- Separación de lid_discount como componente aparte
- El total final = venta_stock ± correcciones + VDP - lid_discount

---

### Capa 3 — Motor local (screening + señales + prototipos)

**Responsabilidad**: clasificar cada sabor, detectar señales, aplicar prototipos fuertes,
y marcar calidad del dato. Es el motor que resuelve ~95% de los casos.

#### 3.1 Clasificación (idéntica a v2)

| # | Condición | Si falla → |
|---|-----------|------------|
| 1 | `raw_sold >= -50g` | SOSPECHOSO |
| 2 | `raw_sold < 5000g` o hay apertura confirmada | SOSPECHOSO |
| 3 | `ab_NOCHE <= ab_DIA + 20g` o hay apertura confirmada | SOSPECHOSO |
| 4 | No hay cerrada en un solo turno sin match (±30g) | SOSPECHOSO |
| 5 | `engine_sold == raw_sold` | ENGINE |
| todas pasan | | LIMPIO |

#### 3.2 Verificación de engine (idéntica a v2)

Para ENGINE: verificar tipo (omission/phantom/digit/compuesta).
Si correcto: mantener. Si cuestionable: escalar.

#### 3.3 Screening de dígito (idéntico a v2)

Offset ±1000/±2000 vs historial ≥5 sightings estables.

#### 3.4 Prototipos fuertes (PF1-PF8, idénticos a v2)

Se aplican **solo** si:
1. El caso matchea exactamente 1 prototipo fuerte.
2. La evidencia es unívoca (no hay hipótesis alternativa plausible).
3. La confianza del prototipo es ≥0.85.

#### 3.5 Precedencias P1-P5 (idénticas a v2)

P1 preservar → P2 eliminar phantoms → P3 completar omisiones → P4 recontar → P5 no eliminar extra.

#### 3.6 NUEVO — Marcas de calidad del dato

Para cada dato que participa en una resolución, evaluar calidad:

**Abierta estática (Riesgo E)**:

| Marca | Condición | Efecto |
|-------|-----------|--------|
| DATO_NORMAL | Variación normal entre turnos | Sin efecto |
| COPIA_POSIBLE_LEVE | 2 turnos con peso idéntico exacto (±0g) en contexto improbable (venta esperada >200g) | Nota informativa |
| COPIA_POSIBLE_FUERTE | ≥3 turnos con peso idéntico exacto (±0g) | Baja confianza de cualquier resolución que dependa de esa estática en -0.15 |

"Contexto improbable" = el sabor tiene historial de venta >200g/período y la abierta no se mueve.

Estas marcas **no corrigen nada por sí mismas**. Solo degradan la confianza de resoluciones
que dependen del dato marcado.

#### 3.7 Resultado de Capa 3

Cada sabor sale con exactamente uno de:
- **LIMPIO** → Capa 5 lo revisará en segunda pasada (pero no se toca aquí)
- **ENGINE_CONFIRMADO** → valor engine aceptado
- **RESUELTO_PROTOTIPO** → 1 prototipo fuerte aplicado
- **OBSERVACIÓN** → 1 señal aislada, baja magnitud, sin corregir
- **ESCALAR_A_CAPA_4** → requiere expediente ampliado

**Criterios para ESCALAR_A_CAPA_4** (Corrección 1):
- SOSPECHA COMPUESTA (≥2 señales simultáneas)
- VIOLACIÓN ESTRUCTURAL que no cierra con prototipo fuerte
- Conflicto real entre hipótesis plausibles (≥2 prototipos compiten con resultados distintos)
- Corrección potencial cambia materialmente la masa del día (>2000g) y la evidencia no es unívoca

**Criterio explícito de NO escalado**:
- LIMPIO nunca se escala aquí (va a Capa 5)
- ENGINE simple confirmado nunca se escala
- Prototipo fuerte con evidencia unívoca nunca se escala

---

### Capa 4 — Resolución de hipótesis compuestas (expediente ampliado)

**Responsabilidad**: resolver los casos que Capa 3 no pudo, usando coherencia conjunta
de 4 planos de evidencia.

#### 4.1 Principio rector (Corrección 2)

La resolución NO sale de una señal única tipo "RM-3 → PF3 → listo".
Sale de la **coherencia conjunta** de 4 planos independientes.

#### 4.2 Plano 1 — Serie temporal de abierta

**Qué reporta**: clasificación de cada transición de abierta entre turnos consecutivos.

| Clasificación | Definición |
|--------------|------------|
| VENTA_PURA | ab baja, sin cerradas desaparecidas ni entrantes nuevos |
| APERTURA_SOPORTADA | ab sube + desaparece una fuente (cerrada o entrante) + rise coherente con esa fuente menos venta intra-turno razonable |
| APERTURA_PLAUSIBLE_NO_CONFIRMADA | ab sube + desaparece una fuente + pero el rise NO es coherente (difiere >30% de lo esperado) |
| AB_SUBE_SIN_FUENTE | ab sube + no desaparece ninguna fuente → imposibilidad física |
| ESTÁTICA | ab no cambia (±20g) en un período con venta esperada baja |
| ESTÁTICA_SOSPECHOSA | ab no cambia (±0g exactos) en ≥3 turnos consecutivos O en 2 turnos con venta esperada >200g |

**Definición de APERTURA (Corrección 2 — sin umbral fijo)**:

APERTURA no se define por "ab sube >3000g". Se define como señal compuesta:
1. ab sube significativamente (más allá de varianza de pesaje, >20g)
2. desaparece una fuente plausible (cerrada o entrante) en el mismo período
3. el rise es coherente con esa fuente dentro de un margen razonable:
   `rise ≈ peso_fuente - venta_intra_turno_estimada` (±15% o ±500g, lo que sea mayor)

Si falta cualquiera de estas tres patas, NO clasificar como APERTURA confirmada.
Queda como APERTURA_PLAUSIBLE_NO_CONFIRMADA o AB_SUBE_SIN_FUENTE según corresponda.

#### 4.3 Plano 2 — Multiconjunto de cerradas

**Qué reporta**: DOS vistas, no un matching greedy individual.

**Vista 1 — Delta bruto del multiconjunto**:
```
cerradas_A = {6545, 6400, 6355}   # multiset de pesos en turno A
cerradas_B = {6545, 6355}         # multiset de pesos en turno B
delta_bruto = cerradas_A - cerradas_B = {6400}  # desapareció una de ~6400g
```
Esto es un hecho observable. No requiere matching individual.

**Vista 2 — Equivalencias plausibles NO VINCULANTES**:
```
Posibles identidades bajo ruido de pesaje (±30g):
- 6545_A ↔ 6545_B (exacto, conf 0.99)
- 6355_A ↔ 6355_B (exacto, conf 0.99)
- 6400_A → sin match en B (desapareció)
Alternativa: 6400_A ↔ 6355_B? No: dif=45g, >30g threshold.
```

**Reglas estrictas del Plano 2**:
- No forzar identidad individual cuando la diferencia está en zona ambigua (30-75g)
- No colapsar dos cerradas cercanas como si fueran una sola sin evidencia adicional
- No usar matching oculto como si resolviera R2/R8
- Permitir resolución a nivel de conjunto cuando la identidad individual no afecta el resultado

**Resolución por conjunto (Corrección 4)**:
Si hay cerradas cercanas donde la identidad individual es ambigua pero el resultado numérico
no depende de cuál es cuál:
```
Ejemplo: cerr_A = {6400, 6410}, cerr_B = {6405, 6415}
Individualmente ambiguo (¿6400↔6405 y 6410↔6415? ¿o cruzado?)
A nivel conjunto: delta_A = 12810, delta_B = 12820. Diferencia = 10g.
→ Resolución: CONJUNTO, identity_ambiguous, venta no depende de identidad.
```

#### 4.4 Plano 3 — Genealogía de entrantes

**Qué reporta**: ciclo de vida observado de cada entrante.

```
Ciclo de vida posible:
aparece → persiste (N turnos) → se promueve a cerrada → se abre → desaparece
```

Cada entrante se clasifica en:
- CICLO_COMPLETO: toda la genealogía es visible
- CICLO_PARCIAL: aparece y desaparece, con algún gap
- SIN_GENEALOGÍA: aparece sin antecedente rastreable
- HUÉRFANO: desaparece sin explicación

**Regla epistemológica (Corrección 3)**:
"Sin genealogía" es evidencia **NEUTRA**, no evidencia contra una cerrada.
La ausencia de genealogía no puede incriminar a una cerrada por sí sola.
Un entrante sin genealogía puede ser simplemente un entrante no documentado en turnos anteriores.

#### 4.5 Plano 4 — Celíacas / sublíneas relacionadas

**Cuándo incluir**: SOLO si tienen vínculo operativo real con el caso.

Vínculos operativos reales:
- Celiaca del mismo sabor comparte balde con la abierta
- Sublínea es variante del mismo producto (ej: DULCE DE LECHE / DULCE D LECHE CELIACO)
- Celiaca participa en el cálculo de total del sabor afectado

**No incluir por reflejo** solo por compartir nombre. Si la celiaca no afecta
el total ni la resolución del caso, se omite del expediente.

#### 4.6 Resolución por coherencia conjunta (Correcciones 2 y 3)

**Regla epistemológica fuerte**: para aplicar cualquier corrección material
(phantom, omisión, apertura parcial, etc.) se requieren **≥2 planos convergentes
y suficientemente independientes**.

"Suficientemente independientes" significa que no repiten la misma evidencia:
- Plano 1 (abierta) + Plano 2 (cerradas) = independientes ✓
- Plano 2 (cerrada desaparece) + Plano 3 (entrante sin genealogía) = parcialmente independientes
  (la genealogía del entrante puede referirse a la misma cerrada)
- Plano 2 (cerrada desaparece) + Plano 2 (otra cerrada cercana) = **NO independientes** ✗

**Tabla de convergencia mínima**:

| Corrección | Planos mínimos requeridos | Ejemplo |
|-----------|--------------------------|---------|
| Phantom (P1.a, RM-3) | P1 + P2 (ab no sube + cerrada desaparece) | SAMBAYON D28 |
| Phantom (P1.c) | P1 + P2 + (P3 o P4) | Cerr desaparece + ab no sube + sin entrante |
| Omisión bilateral | P2 + historial tracker (≥3 sightings) | CH C/ALM D26 |
| Error de dígito | P2 + historial tracker (≥5 sightings) | COOKIES D25 |
| AB_IMP | P1 + P2 (ab sube + cerradas intactas) | AMERICANA D25 |
| Apertura parcial | P1 + P2 + P3 (ab sube parcial + fuente + genealogía) | Necesita 3 planos |

**Si solo hay 1 plano**: → H0 / UNRESOLVED. No corregir.

#### 4.7 R2/R8 — La abierta como testigo (Corrección 4)

En riesgos de cerradas muy cercanas o tolerancias ambiguas:

1. Si una cerrada supuestamente se abrió → la abierta debe comportarse de forma compatible
   (rise coherente con el peso de esa cerrada menos venta intra-turno)
2. Si un can desaparece sin que la abierta lo cuente → debilita la hipótesis de apertura
3. Si hay varias cerradas casi iguales → resolver a nivel de conjunto si el resultado no depende de identidad individual

**Tipos de resolución explícitos**:

| Tipo | Significado |
|------|-------------|
| RESUELTO_INDIVIDUAL | Se identificó cuál cerrada es cuál con confianza suficiente |
| RESUELTO_CONJUNTO | No se sabe cuál es cuál, pero el resultado numérico no depende de ello |
| IDENTITY_AMBIGUOUS | La identidad individual importaría para el resultado, pero no se puede determinar |

IDENTITY_AMBIGUOUS va a UNRESOLVED con el rango de incertidumbre documentado.

#### 4.8 Orden de aplicación de correcciones (Corrección 7)

Heurística por defecto (NO verdad absoluta):

```
Orden 1: Phantoms con violación física fuerte (RM-3, ab confirma)
Orden 2: Entrantes duplicados con genealogía directa
Orden 3: Omisiones compatibles (bilateral con historial)
Orden 4: Aperturas parciales / PF6 y similares
```

**Después de aplicar este orden**: verificar que los 4 planos convergen.
Si la convergencia es insuficiente después de aplicar el orden:

- Si hay orden alternativo que converge mejor → evaluar ambos
- Si ningún orden converge → UNRESOLVED
- Si el resultado es igual bajo cualquier orden → RESUELTO_CONJUNTO

**Riesgo F — no conmutatividad**: este orden es heurística, no axioma.
Si el caso muestra que el orden importa (resultado distinto según secuencia),
documentar ambas secuencias con sus resultados y dejar como UNRESOLVED
salvo que un orden tenga convergencia claramente superior (≥2 planos más).

#### 4.9 H0 / UNRESOLVED

Un caso queda sin resolver cuando:
1. Solo 1 plano tiene evidencia (Corrección 3)
2. La única evidencia contra una cerrada es "no tiene genealogía"
3. Múltiples hipótesis equiprobables con resultados materialmente distintos
4. El orden de correcciones cambia el resultado y ninguno converge mejor
5. La corrección potencial depende de un dato marcado COPIA_POSIBLE_FUERTE

**H0 no significa "correcto". Significa "evidencia insuficiente para intervenir".**

---

### Capa 5 — Segunda pasada residual

**Responsabilidad**: detectar falsos LIMPIO por errores compensados.

Esta capa se ejecuta **después** de resolver todo el día en Capas 1-4.
No opera dentro del expediente local de un sabor. Opera sobre el perfil
completo del día ya resuelto.

Ver documento dedicado: `04e_segunda_pasada_residual_v3_draft.md`

**Principio**: un sabor puede quedar LIMPIO en Capa 3 porque un error
se compensó con otro error (ej: dígito +1000 y omisión -1000 se cancelan).
La segunda pasada busca estos falsos LIMPIO sin reabrir todo indiscriminadamente.

---

## RESUMEN VISUAL v3

```
                ┌──────────────────────┐
                │  CAPA 1: Parser      │
                │  Datos crudos sin    │
                │  interpretación      │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │  CAPA 2: Contrato    │
                │  contable            │
                │  Fórmula global      │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │  CAPA 3: Motor local │
                │  Screening + señales │
                │  + prototipos fuertes│
                │  + calidad del dato  │
                └──────────┬───────────┘
                           │
            ┌──────────────┼──────────────────────┐
            │              │                      │
     ┌──────▼──────┐ ┌────▼─────┐         ┌──────▼──────────┐
     │  LIMPIO     │ │ RESUELTO │         │ ESCALAR_A_CAPA_4│
     │  ENGINE_OK  │ │ PROTOTIPO│         │ (≤5% de sabores)│
     │  OBSERV.    │ │          │         │                 │
     └──────┬──────┘ └────┬─────┘         └──────┬──────────┘
            │              │                      │
            │              │          ┌───────────▼───────────┐
            │              │          │  CAPA 4: Expediente   │
            │              │          │  ampliado 4 planos    │
            │              │          │  Coherencia conjunta  │
            │              │          │  ≥2 planos independ.  │
            │              │          └───────────┬───────────┘
            │              │                      │
            │              │          ┌───────────┼───────────┐
            │              │          │           │           │
            │              │     ┌────▼───┐ ┌────▼────┐ ┌────▼────┐
            │              │     │RESUELTO│ │RESUELTO │ │H0/UNRES.│
            │              │     │INDIV.  │ │CONJUNTO │ │AMBIGUOUS│
            │              │     └────┬───┘ └────┬────┘ └────┬────┘
            │              │          │          │           │
            └──────────────┴──────────┴──────────┴───────────┘
                                      │
                           ┌──────────▼───────────┐
                           │  CAPA 5: Segunda     │
                           │  pasada residual     │
                           │  Falsos LIMPIO       │
                           └──────────┬───────────┘
                                      │
                              ┌───────┼───────┐
                              │               │
                        ┌─────▼────┐   ┌──────▼──────┐
                        │CONFIRMADO│   │REABRIR →    │
                        │LIMPIO    │   │vuelve a     │
                        │          │   │Capa 3 o 4   │
                        └──────────┘   └─────────────┘
```

---

## CONFLICTOS DETECTADOS CON v2

### Conflicto 1: Apertura definida por umbral fijo
v2 usa `ab sube >3000g con cerr gone` como proxy de apertura confirmada (criterio 2 de clasificación).
v3 redefine APERTURA como señal compuesta de 3 patas.
**Resolución**: el criterio de clasificación en Capa 3 sigue usando el proxy >3000g como screening rápido.
La redefinición de APERTURA como señal compuesta aplica solo en Capa 4 (expediente ampliado).

### Conflicto 2: Matching individual en v2
v2 usa matching ±30g como base de la detección (criterio 4 de clasificación).
v3 lo mantiene como screening pero agrega la vista de conjunto en Capa 4.
**Resolución**: sin conflicto real. El matching individual sigue siendo el screening.
La resolución por conjunto es refinamiento solo para Capa 4.

### Conflicto 3: LIMPIO como estado terminal
En v2, LIMPIO es estado terminal sin revisión posterior.
En v3, LIMPIO pasa por Capa 5 (segunda pasada residual).
**Resolución**: Capa 5 puede reabrir un LIMPIO, pero la mayoría seguirán siendo LIMPIO.
El costo computacional es bajo porque Capa 5 usa filtros estadísticos antes de reabrir.

---

## ABSTENCIONES EXPLÍCITAS

1. **No se define un threshold automático para "contexto improbable" de COPIA_POSIBLE**.
   Requiere calibración empírica con más días validados.

2. **No se define la ventana exacta de la segunda pasada residual** (¿cuántos σ? ¿qué distribución?).
   Requiere análisis estadístico del dataset completo de Febrero.

3. **No se puede resolver automáticamente** el caso donde el orden de correcciones importa
   Y ningún orden tiene convergencia clara. Esto requiere juicio humano o PDF.

4. **La marca COPIA_POSIBLE_FUERTE** no puede distinguir entre dato copiado y sabor genuinamente
   sin venta (ej: sabor impopular que realmente no se vendió en 3 turnos). Requiere historial
   de ventas del sabor para calibrar.
