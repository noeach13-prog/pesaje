# Plantilla expediente ampliado v3 — Caso escalado (DRAFT)

## Cuándo usar esta plantilla

SOLO para casos que llegan a Capa 4:
- SOSPECHA COMPUESTA
- VIOLACIÓN ESTRUCTURAL que no cierra con prototipo fuerte
- Conflicto entre hipótesis plausibles
- Corrección material >2000g sin evidencia unívoca

NO usar para: LIMPIO, ENGINE simple, prototipo fuerte unívoco, OBSERVACIÓN.

---

## Formato obligatorio

```
### [SABOR] — Expediente ampliado

**Contexto**: [breve: qué señales dispararon el escalado]

#### Plano 1 — Serie temporal de abierta
| Turno | Ab | Transición | Clasificación |
|-------|----|-----------|---------------|
| [T-2] | [peso] | | |
| [T-1] | [peso] | [T-2→T-1] | [VENTA_PURA / APERTURA_SOPORTADA / etc.] |
| [A]   | [peso] | [T-1→A]   | [...] |
| [B]   | [peso] | [A→B]     | [...] |
| [T+1] | [peso] | [B→T+1]   | [...] |

Marca calidad: [DATO_NORMAL / COPIA_POSIBLE_LEVE / COPIA_POSIBLE_FUERTE]
Nota apertura: [si aplica: "ab sube [X]g + desaparece [fuente] + rise coherente/no coherente"]

#### Plano 2 — Multiconjunto de cerradas
**Vista 1 — Delta bruto**:
- cerradas_A = {[pesos]}
- cerradas_B = {[pesos]}
- delta = A - B = {[pesos que desaparecen]} / B - A = {[pesos que aparecen]}

**Vista 2 — Equivalencias plausibles (NO VINCULANTES)**:
| Cerr A | Cerr B | Dif | Plausibilidad |
|--------|--------|-----|---------------|
| [peso] | [peso] | [g] | [exacta / plausible / ambigua / sin match] |

Resolución cerradas: [INDIVIDUAL posible / solo CONJUNTO / IDENTITY_AMBIGUOUS]

#### Plano 3 — Genealogía de entrantes
| Entrante | Peso | Primera aparición | Estado | Ciclo |
|----------|------|-------------------|--------|-------|
| [ent_1]  | [g]  | [turno]           | [activo/promovido/desaparecido] | [COMPLETO/PARCIAL/SIN_GENEALOGÍA/HUÉRFANO] |

Nota: SIN_GENEALOGÍA = evidencia NEUTRA. No incrimina cerradas.

#### Plano 4 — Celíacas / sublíneas (si aplica)
[Incluir SOLO si hay vínculo operativo real con el caso]
| Sublínea | Turno A | Turno B | Vínculo con caso |
|----------|---------|---------|-------------------|
| [nombre] | [peso]  | [peso]  | [descripción del vínculo] |

[Si no aplica: "Sin sublíneas con vínculo operativo real."]

---

#### Hipótesis
- **H1**: [hipótesis principal]
  - Planos que la soportan: [P1, P2, ...] — [breve evidencia de cada uno]
  - Planos neutros: [...]
  - Planos en contra: [...]

- **H2**: [hipótesis alternativa]
  - Planos que la soportan: [...]
  - Planos neutros: [...]
  - Planos en contra: [...]

[Si solo hay 1 hipótesis plausible, H2 = "ninguna plausible"]
[Si hay H3, agregarla con el mismo formato]

#### Convergencia
- Planos convergentes para H elegida: [N] de 4 ([listar cuáles])
- ¿Son independientes? [Sí/No/Parcialmente — explicar si parcial]
- Regla ≥2 planos independientes: [CUMPLE / NO CUMPLE]

#### Resolución
- **Corrección**: [acción concreta o H0/UNRESOLVED]
- **Tipo**: [RESUELTO_INDIVIDUAL / RESUELTO_CONJUNTO / IDENTITY_AMBIGUOUS / H0 / UNRESOLVED]
- **Conf**: [0.XX] [ajustes: -0.15 por COPIA_POSIBLE_FUERTE, -0.15 por conflicto, etc.]
- **Delta**: [raw → corregido = ±Ng] o [sin corrección]
- **Impacto**: [MASA: ±Ng en venta_stock] o [INTERP: redistribuye, neto 0]
```

---

## Ejemplo: CHOC DUBAI D28 (reescrito con formato v3)

```
### CHOC DUBAI — Expediente ampliado

**Contexto**: raw=8140g, 2 cerr DIA (6400, 6355), 0 cerr NOCHE, ab sube 1420→6035.
Señales: venta muy alta + 2 cerr desaparecen + ab sube insuficiente para 2 aperturas.

#### Plano 1 — Serie temporal de abierta
| Turno | Ab | Transición | Clasificación |
|-------|----|-----------|---------------|
| D27 DIA | 1580 | | |
| D27 NOCHE | 1420 | D27D→D27N | VENTA_PURA (-160g) |
| D28 DIA | 1420 | D27N→D28D | ESTÁTICA (0g) |
| D28 NOCHE | 6035 | D28D→D28N | APERTURA_SOPORTADA (+4615g) |

Marca calidad: DATO_NORMAL (estática solo 1 turno, sin patrón repetido)
Nota apertura: ab sube 4615g + desaparece cerr(es) + rise coherente con 1 cerr ~6355
  menos venta intra-turno ~1740g: 6355-1740=4615. Coherente exacto con 1 apertura.
  Para 2 aperturas esperaríamos ~11000g de rise. Incompatible.

#### Plano 2 — Multiconjunto de cerradas
Vista 1: cerr_A = {6400, 6355}, cerr_B = {}. Delta = {6400, 6355} desaparecen.
Vista 2:
| Cerr A | Cerr B | Dif | Plausibilidad |
|--------|--------|-----|---------------|
| 6400 | — | — | sin match |
| 6355 | — | — | sin match |

Resolución cerradas: no hay matching posible (B vacío).
Pregunta clave: ¿ambas existían?

#### Plano 3 — Genealogía de entrantes
Sin entrantes relevantes en este período.

#### Plano 4 — Celíacas / sublíneas
Sin sublíneas con vínculo operativo real.

---

#### Hipótesis
- **H1**: cerr 6400 phantom (sin historial, sin entrante), solo 6355 real y abierta. 1 lata.
  - P1: APERTURA_SOPORTADA, rise coherente con 1 cerr (4615g ≈ 6355-1740). ✓
  - P2: 6400 sin historial tracker, 6355 con historial. ✓
  - P3: neutro (sin entrantes).
  - P4: no aplica.

- **H2**: ambas reales, ambas abiertas. 2 latas.
  - P1: rise 4615g incompatible con 2 aperturas (~11000g esperado). ✗
  - P2: 6400 sin historial (debilita pero no refuta). Parcial.
  - P3: neutro.

#### Convergencia
- H1: 2 planos (P1, P2) convergentes e independientes.
- ¿Independientes? Sí: P1 mide abierta, P2 mide cerradas.
- Regla ≥2 planos independientes: CUMPLE.

#### Resolución
- Corrección: poner cerr 6400 en 0, contar 1 lata.
- Tipo: RESUELTO_INDIVIDUAL
- Conf: 0.80
- Delta: 8140 → 1740 = -6400g
- Impacto: MASA: -6400g en venta_stock, -1 lata
```

---

## Ejemplo: caso IDENTITY_AMBIGUOUS (hipotético)

```
### [SABOR_X] — Expediente ampliado

**Contexto**: 2 cerradas cercanas en DIA (6400, 6420), 1 cerrada en NOCHE (6410).
¿Cuál de las dos quedó? La otra fue abierta.

#### Plano 2 — Multiconjunto de cerradas
Vista 1: cerr_A = {6400, 6420}, cerr_B = {6410}. Delta: 1 cerr desaparece.
Vista 2:
| Cerr A | Cerr B | Dif | Plausibilidad |
|--------|--------|-----|---------------|
| 6400 | 6410 | 10g | plausible (varianza pesaje) |
| 6420 | 6410 | 10g | plausible (varianza pesaje) |

Ambas son match plausible. No se puede elegir cuál quedó.

#### Convergencia
- Si 6400 fue la abierta: venta cambia en ~20g vs si 6420 fue la abierta.
- Delta entre hipótesis: 20g. Inmaterial.

#### Resolución
- Tipo: RESUELTO_CONJUNTO (identidad individual ambigua, resultado no depende: Δ=20g)
- Conf: 0.90 (resultado numérico robusto independientemente de identidad)
```

---

## Diferencia con plantilla v2 (04d)

| Aspecto | v2 | v3 |
|---------|----|----|
| Formato | 8 líneas máximo | Expediente completo con 4 planos |
| Planos | No existen | P1 abierta, P2 cerradas, P3 entrantes, P4 sublíneas |
| Hipótesis | H1/H2 breves | H1/H2 con planos a favor/neutro/en contra |
| Convergencia | Implícita | Explícita: ≥2 planos independientes |
| Tipo resolución | No existe | INDIVIDUAL / CONJUNTO / AMBIGUOUS / H0 |
| Calidad dato | No existe | COPIA_POSIBLE_LEVE / FUERTE |
| Cuándo usar | Todo caso escalado | SOLO Capa 4 (compuestos/violaciones sin prototipo) |
| Casos simples | También usaban esta plantilla | Resueltos en Capa 3 con formato breve de v2 |
