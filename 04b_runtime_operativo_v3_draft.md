# Runtime operativo v3 — Ejecución diaria (DRAFT)

Solo reglas de ejecución. Sin teoría. Máximo 160 líneas.

---

## SECUENCIA DE CAPAS

```
CAPA 1 → CAPA 2 → CAPA 3 → CAPA 4 (si aplica) → CAPA 5 (siempre)
```

---

## CAPA 1: PARSER

Leer workbook. Entregar datos crudos. No interpretar.
- ab=None ≠ ab='' ≠ ab=0. Preservar distinción.
- Hojas válidas: A1='SABORES'. Saltar STOCK y vacías.

---

## CAPA 2: CONTRATO CONTABLE

```
venta_stock = total_A + new_entrantes_B - total_B - ajuste_latas
total = abierta + celiaca + sum(cerradas) + sum(entrantes)
ajuste_latas = max(0, n_cerradas_A - n_cerradas_B) * 280
```

No se modifica por historial ni por expediente. Es definición global.

---

## CAPA 3: MOTOR LOCAL

### 3.1 Clasificar cada sabor

| # | Condición | Si falla → |
|---|-----------|------------|
| 1 | `raw_sold >= -50g` | SOSPECHOSO |
| 2 | `raw_sold < 5000g` o apertura confirmada | SOSPECHOSO |
| 3 | `ab_B <= ab_A + 20g` o apertura confirmada | SOSPECHOSO |
| 4 | No hay cerrada en 1 turno sin match (±30g) | SOSPECHOSO |
| 5 | `engine_sold == raw_sold` | ENGINE |
| todas | | LIMPIO |

### 3.2 Verificar ENGINE

Tipo omission/phantom/digit/compuesta.
Correcto → mantener. Cuestionable → escalar a SOSPECHOSO.

### 3.3 Screening dígito

Offset ±1000/±2000 vs historial ≥5 sightings estables → SOSPECHOSO+DÍGITO.

### 3.4 Prototipos fuertes (aplicar si matchea exactamente 1, evidencia unívoca, conf ≥0.85)

| ID | Firma | Corrección |
|----|-------|------------|
| PF1 | Cerr ±1000/±2000 de historial ≥5 sightings | Corregir peso |
| PF2 | Entrante DIA persiste en NOCHE tras apertura | Entrante NOCHE=0 |
| PF3 | Cerrada abierta en turno anterior (RM-3) | Cerr=0 |
| PF4 | Cerr DIA con historial no aparece en NOCHE, ab no sube | Agregar a NOCHE |
| PF5 | Cerr NOCHE con historial no aparece en DIA, raw negativo | Agregar a DIA |
| PF6 | N cerr DIA, ab sube para M<N, extras sin historial/RM-3 | Eliminar phantoms, M latas |
| PF7 | Ab sube sin fuente | Forward>backward |
| PF8 | Par nunca coexiste, pesos coherentes | Combinar |

### 3.5 Precedencias P1-P5

```
P1 PRESERVAR: cerrada real salvo evidencia directa (RM-3, nota, P1.c completo).
P2 ELIMINAR: solo phantoms P1.a/b/c.
P3 COMPLETAR: cerrada con ≥2 sightings al turno faltante.
P4 RECONTAR: latas solo después de P1-P3. Ab coherente con aperturas.
P5 NO ELIMINAR extra sin evidencia directa.
```

### 3.6 Calidad del dato — marcas de estática

| Marca | Condición | Efecto |
|-------|-----------|--------|
| DATO_NORMAL | Variación normal | Ninguno |
| COPIA_POSIBLE_LEVE | 2 turnos ab idéntica exacta, venta esperada >200g | Nota |
| COPIA_POSIBLE_FUERTE | ≥3 turnos ab idéntica exacta | Conf -0.15 en resoluciones dependientes |

### 3.7 Decisión de salida

| Resultado | Acción |
|-----------|--------|
| LIMPIO | Usar raw_sold. Pasa a Capa 5. |
| ENGINE_CONFIRMADO | Usar engine_sold. |
| RESUELTO_PROTOTIPO | Usar valor corregido. |
| OBSERVACIÓN | Usar raw_sold. Registrar nota. |
| ESCALAR_A_CAPA_4 | → Capa 4. |

### 3.8 Criterios de escalado a Capa 4

Escalar SOLO si:
- SOSPECHA COMPUESTA (≥2 señales simultáneas)
- VIOLACIÓN ESTRUCTURAL que no cierra con 1 prototipo
- Conflicto entre ≥2 prototipos con resultados distintos
- Corrección >2000g sin evidencia unívoca

NO escalar: LIMPIO, ENGINE simple, prototipo fuerte unívoco.

---

## CAPA 4: EXPEDIENTE AMPLIADO (solo para escalados)

### 4.1 Construir expediente del sabor

Incluir: abierta, cerradas, entrantes del sabor.
Incluir celíacas/sublíneas SOLO si tienen vínculo operativo real con el caso.

### 4.2 Evaluar 4 planos

**Plano 1 — Abierta**: clasificar transiciones.
APERTURA = ab sube + desaparece fuente + rise coherente con fuente (±15% o ±500g).
Si falta una pata → no es APERTURA confirmada.

**Plano 2 — Cerradas**: reportar delta bruto multiconjunto + equivalencias plausibles NO VINCULANTES.
Si identidad individual ambigua pero resultado no depende de ella → RESUELTO_CONJUNTO.

**Plano 3 — Entrantes**: genealogía (aparece→persiste→promueve→abre→desaparece).
SIN_GENEALOGÍA = evidencia NEUTRA. No incrimina cerradas.

**Plano 4 — Celíacas/sublíneas**: solo si vínculo operativo real.

### 4.3 Regla de convergencia

Para corregir: ≥2 planos convergentes e independientes.
1 solo plano → H0 / UNRESOLVED.
Planos que repiten la misma evidencia no cuentan como independientes.

### 4.4 Abierta como testigo (R2/R8)

Si cerrada "se abrió" → ab debe ser compatible.
Si can desaparece sin que ab lo cuente → debilita hipótesis de apertura.
Cerradas cercanas → resolver por conjunto si resultado no depende de identidad.

### 4.5 Tipo de resolución

| Tipo | Cuándo |
|------|--------|
| RESUELTO_INDIVIDUAL | Identidad de cada cerrada determinada con confianza |
| RESUELTO_CONJUNTO | Identidad ambigua pero resultado numérico no depende |
| IDENTITY_AMBIGUOUS | Identidad importaría pero no se puede determinar → UNRESOLVED |

### 4.6 Orden de correcciones (heurística, no axioma)

```
1. Phantoms con violación física fuerte
2. Entrantes duplicados con genealogía directa
3. Omisiones compatibles
4. Aperturas parciales / PF6
```

Post-aplicación: verificar convergencia de 4 planos.
Si no converge bajo ningún orden → UNRESOLVED.
Si resultado igual bajo cualquier orden → RESUELTO_CONJUNTO.

---

## CAPA 5: SEGUNDA PASADA RESIDUAL

Se ejecuta DESPUÉS de resolver todo el día (Capas 1-4).
Ver detalle en `04e_segunda_pasada_residual_v3_draft.md`.

### Resumen operativo

```
Para cada sabor LIMPIO del día:
  5.1  ¿Desvío >1.8σ del promedio histórico del sabor? → candidato
  5.2  ¿Rareza estructural débil? (cerr cercanas, ab plana sospechosa) → candidato
  5.3  ¿Perfil del día es anómalo? (muchos sabores en extremos opuestos) → candidato
  5.4  Si ≥2 de {5.1, 5.2, 5.3}: REABRIR → vuelve a Capa 3 o 4.
  5.5  Si 1 solo: registrar como LIMPIO_CON_NOTA.
  5.6  Si 0: LIMPIO_CONFIRMADO.
```

---

## FORMATO DE SALIDA

```
# Auditoría Día [N] — [fecha]

## Clasificación: [X] LIMPIO, [Y] ENGINE, [Z] ESCALADO

## Engine confirmados
| Sabor | Tipo | Venta | Latas | Conf |

## Resueltos por prototipo
| Sabor | Prototipo | Venta | Latas | Conf | Delta |

## Expedientes ampliados (plantilla 04d_v3 por caso)

## Segunda pasada residual
| Sabor | Señal residual | Acción | Resultado |

## Tabla final
| Sabor | Capa | Tipo resolución | Venta | Latas | Conf |

## Totales
| Conservador | venta_stock | latas | VDP | total |
| Estimado    | venta_stock | latas | VDP | total |

## Casos abiertos
| Sabor | Tipo | Impacto max | Motivo |

## Scorecard (si hay GT)
| AC | AN | FA | SC | OP | Δ total |
```
