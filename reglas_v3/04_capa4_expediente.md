# Capa 4 — Resolucion de hipotesis compuestas (expediente ampliado)

## Responsabilidad

Resolver los casos que Capa 3 no pudo, usando coherencia conjunta
de 4 planos de evidencia independientes.

---

## Input

- Sabores clasificados como ESCALAR_A_CAPA_4
- Datos crudos de Capa 1 (periodo analizado + ±3 turnos de contexto)
- Timeline del tracker por can (sightings historicos)

## Output

Por cada sabor escalado:
- Tipo de resolucion: RESUELTO_INDIVIDUAL / RESUELTO_CONJUNTO / IDENTITY_AMBIGUOUS / H0 / UNRESOLVED
- Correccion concreta (o ausencia)
- Confianza ajustada
- Delta: raw → corregido

---

## E4.1 — Principio rector

La resolucion NO sale de una senal unica.
Sale de la COHERENCIA CONJUNTA de 4 planos independientes.

---

## E4.2 — Plano 1: Serie temporal de abierta

Clasifica cada transicion de abierta entre turnos consecutivos:

| Clasificacion | Definicion |
|--------------|------------|
| VENTA_PURA | Ab baja, sin cerradas desaparecidas ni entrantes nuevos |
| APERTURA_SOPORTADA | Ab sube + desaparece fuente + rise coherente (±15% o ±500g) |
| APERTURA_PLAUSIBLE_NO_CONFIRMADA | Ab sube + fuente desaparece + rise NO coherente |
| AB_SUBE_SIN_FUENTE | Ab sube + no desaparece fuente → imposibilidad fisica |
| ESTATICA | Ab ±20g con venta esperada baja |
| ESTATICA_SOSPECHOSA | Ab ±0g exactos en >=3 turnos o 2 turnos con venta >200g |

### Definicion de apertura (completa, sin umbral fijo)
Apertura es senal compuesta de 3 patas:
1. Ab sube significativamente (>20g, mas alla de varianza)
2. Desaparece una fuente plausible (cerrada o entrante)
3. Rise coherente con esa fuente: `rise ≈ peso_fuente - venta_intra_turno` (±15% o ±500g)

Si falta cualquier pata → APERTURA_PLAUSIBLE_NO_CONFIRMADA o AB_SUBE_SIN_FUENTE.

---

## E4.3 — Plano 2: Multiconjunto de cerradas

DOS vistas obligatorias:

### Vista 1 — Delta bruto (hecho observable)
```
cerradas_A = multiset de pesos en turno A
cerradas_B = multiset de pesos en turno B
delta = diferencia de multisets (que aparecio, que desaparecio)
```

### Vista 2 — Equivalencias plausibles (NO VINCULANTES)
Matching individual ±30g como hipotesis, no como verdad.

| Cerr A | Cerr B | Dif | Plausibilidad |
|--------|--------|-----|---------------|
| peso | peso | Ng | exacta / plausible / ambigua / sin match |

### Reglas estrictas
- No forzar identidad individual en zona ambigua (30-75g)
- No colapsar dos cercanas como una sola sin evidencia adicional
- Permitir resolucion a nivel de CONJUNTO cuando identidad no afecta resultado

### Resolucion por conjunto
Si cerradas cercanas tienen identidad ambigua pero el resultado numerico
no depende de cual es cual → RESUELTO_CONJUNTO.

---

## E4.4 — Plano 3: Genealogia de entrantes

Ciclo de vida de cada entrante:
```
aparece → persiste (N turnos) → se promueve a cerrada → se abre → desaparece
```

Clasificaciones:
- CICLO_COMPLETO: toda la genealogia es visible
- CICLO_PARCIAL: aparece y desaparece con algun gap
- SIN_GENEALOGIA: aparece sin antecedente rastreable
- HUERFANO: desaparece sin explicacion

### Regla epistemologica critica
**SIN_GENEALOGIA = evidencia NEUTRA, no evidencia contra una cerrada.**
La ausencia de genealogia no puede incriminar a una cerrada por si sola.

---

## E4.5 — Plano 4: Celiacas / sublineas

Incluir SOLO si hay vinculo operativo real:
- Celiaca del mismo sabor comparte balde con la abierta
- Sublinea es variante del mismo producto
- Celiaca participa en el calculo de total

No incluir por reflejo solo por compartir nombre.

---

## E4.6 — Regla de convergencia

### Regla epistemologica fuerte
Para cualquier correccion material: **>=2 planos convergentes e independientes**.

"Suficientemente independientes" significa que no repiten la misma evidencia:
- P1 (abierta) + P2 (cerradas) = independientes ✓
- P2 (cerrada) + P3 (entrante de esa cerrada) = parcialmente independientes
- P2 + P2 (dos cerradas distintas) = NO independientes ✗

### Tabla de convergencia minima

| Correccion | Planos minimos |
|-----------|----------------|
| Phantom (RM-3) | P1 + P2 |
| Phantom (sin RM-3) | P1 + P2 + (P3 o P4) |
| Omision bilateral | P2 + historial tracker (>=3 sightings) |
| Error de digito | P2 + historial tracker (>=5 sightings) |
| AB_IMP | P1 + P2 |
| Apertura parcial | P1 + P2 + P3 |

**Si solo hay 1 plano → H0 / UNRESOLVED. No corregir.**

### Excepcion: Tipo C (prototipo historico fuerte)
Un solo plano dominante con ratio de sightings >=3:1 puede alcanzar CONFIRMADO
sin segundo plano formal, porque los multiples sightings constituyen
convergencia temporal interna.

---

## E4.7 — Abierta como testigo (R2/R8)

Cuando hay cerradas cercanas o tolerancias ambiguas:
1. Si cerrada supuestamente se abrio → ab debe comportarse coherente
2. Si can desaparece sin que ab lo cuente → debilita hipotesis de apertura
3. Si varias cerradas casi iguales → resolver por CONJUNTO si resultado no depende de identidad

---

## E4.8 — Analisis multifactor conjunto (cross-sabor)

### Cuando se activa
Cuando un sabor tiene convergencia numerica univoca pero mecanismo causal ambiguo
en analisis individual.

### Procedimiento
1. Buscar otros sabores del mismo turno con anomalia similar
2. Si se encuentra patron cruzado (ej: >=2 cerradas omitidas en DIA) → mecanismo confirmado
3. El sabor entra como CONFIRMADO_CONJUNTO

### Regla de routing
- Si hay patron cruzado → CONFIRMADO_CONJUNTO (tipo A)
- Si NO hay patron cruzado → FORZADO (tipo B)
- NO crear subcategorias (A-, A+, etc.)

### Ejemplo D5
DDL + VAINILLA: ambos tienen cerrada que aparece en NOCHE sin estar en DIA.
Patron: "turno DIA omitio cerradas sistematicamente" confirmado en >=2 sabores.
→ Ambos entran como CONFIRMADO_CONJUNTO.

---

## E4.9 — Orden de correciones

Heuristica por defecto (NO axioma):
```
1. Phantoms con violacion fisica fuerte (RM-3, ab confirma)
2. Entrantes duplicados con genealogia directa
3. Omisiones compatibles (bilateral con historial)
4. Aperturas parciales / PF6
```

Despues de aplicar: verificar que los 4 planos convergen.
Si el orden importa y resultado cambia → documentar ambos → UNRESOLVED.
Si resultado es igual bajo cualquier orden → RESUELTO_CONJUNTO.

---

## E4.10 — Tipos de resolucion

| Tipo | Significado |
|------|------------|
| RESUELTO_INDIVIDUAL | Identidad de cada cerrada determinada con confianza |
| RESUELTO_CONJUNTO | Identidad ambigua pero resultado numerico no depende |
| IDENTITY_AMBIGUOUS | Identidad importaria pero no se puede determinar → UNRESOLVED |
| H0 | Evidencia insuficiente. No corregir. Raw se mantiene |
| UNRESOLVED | Multiple hipotesis equiprobables con resultados distintos |

---

## E4.11 — Cuando H0 / UNRESOLVED

1. Solo 1 plano tiene evidencia
2. Unica evidencia contra cerrada es "no tiene genealogia"
3. Multiples hipotesis equiprobables con resultados materialmente distintos
4. Orden de correcciones cambia resultado y ninguno converge mejor
5. Correccion depende de dato marcado COPIA_POSIBLE_FUERTE

**H0 no significa "correcto". Significa "evidencia insuficiente para intervenir".**

---

## Formato del expediente

Ver `04d_plantilla_expediente_ampliado_v3_draft.md` para template completo.
Resumen: contexto + P1 + P2 + P3 + P4 + hipotesis H1/H2 + convergencia + resolucion.

---

## Test de validacion

Para D28 (5 escalados, GT disponible):
- MARACUYA: PF2 entrante dup → INDIVIDUAL, conf 0.90
- PISTACHO: phantom/omision → CONJUNTO, conf 0.92
- CHOCOLATE: cerr omitida → INDIVIDUAL+AMBIG, conf 0.75
- SAMBAYON: phantom RM-3 → INDIVIDUAL+H0, conf 0.82
- CHOC DUBAI: phantom → INDIVIDUAL, conf 0.88
- Resultado: 5/5 match con GT
