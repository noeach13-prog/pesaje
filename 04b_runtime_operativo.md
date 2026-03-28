# Runtime operativo — Ejecución diaria

## CRITERIOS DE ACTIVACIÓN

Para cada sabor, evaluar en orden. Primera condición que falla → nivel asignado.

| # | Condición | Si falla → |
|---|-----------|------------|
| 1 | `raw_sold >= -50g` | SOSPECHOSO |
| 2 | `raw_sold < 5000g` o hay apertura confirmada (ab sube >3000g con cerr gone) | SOSPECHOSO |
| 3 | `ab_NOCHE <= ab_DIA + 20g` o hay apertura confirmada | SOSPECHOSO |
| 4 | No hay cerrada en un solo turno sin match en el otro (±30g) | SOSPECHOSO |
| 5 | `engine_sold == raw_sold` | ENGINE |
| todas pasan | | LIMPIO |

---

## ORDEN DE DECISIÓN

```
F0  Extraer raw de ambos turnos. Calcular raw_sold por sabor.
F1  Clasificar: LIMPIO / ENGINE / SOSPECHOSO (tabla arriba).
F2  Para ENGINE: verificar corrección (omission/phantom/digit/compuesta).
    → Correcto: mantener. → Cuestionable: escalar a SOSPECHOSO.
F3  Para SOSPECHOSO: screening de dígito (offset ±1000/±2000 vs historial ≥5 sightings).
F3.5 Aplicar precedencias P1–P5 (abajo).
F4  Análisis multi-turno SOLO para escalados: detectores a→g en orden.
F5  Calcular total conservador + estimado.
F6  Registrar con scorecard.
```

---

## PRECEDENCIAS P1–P5

```
P1  PRESERVAR: toda cerrada es real salvo evidencia directa.
    Phantom solo si: (a) fue abierta en turno anterior (RM-3), o
    (b) nota humana "no existe", o (c) desaparece sin apertura +
    ab no sube + no reaparece + no hay entrante que la explique.

P2  ELIMINAR: poner en 0 solo phantoms que cumplen P1.a/b/c.

P3  COMPLETAR: cerrada en un turno sin match en el otro +
    historial ≥2 sightings → agregarla al turno faltante.

P4  RECONTAR LATAS: solo después de P1–P3. Verificar que ab sube
    coherente con la cerrada desaparecida. Si ab sube menos de lo
    esperado para N aperturas → alguna cerrada era phantom (volver P1).

P5  NO ELIMINAR cerrada extra sin evidencia directa.
    "Sin historial" ≠ phantom. Puede ser entrante no documentado.
```

---

## PROTOTIPOS FUERTES (validados contra GT)

| ID | Nombre | Firma | Corrección |
|----|--------|-------|------------|
| PF1 | DIGIT_TYPO | Cerr difiere ±1000/±2000 de historial estable ≥5 sightings | Corregir peso, recalcular |
| PF2 | ENTRANTE_DUP | Entrante DIA persiste en NOCHE tras ser abierto (ab sube) | Poner entrante NOCHE en 0 |
| PF3 | PHANTOM_CERR | Cerrada fue abierta en turno anterior (RM-3) y reaparece | Poner en 0 |
| PF4 | CERR_OMITIDA_NOCHE | Cerrada DIA con historial no aparece en NOCHE, ab no sube | Agregar a NOCHE |
| PF5 | CERR_OMITIDA_DIA | Cerrada NOCHE con historial no aparece en DIA, raw negativo | Agregar a DIA |
| PF6 | APERTURA_CON_PHANTOM | De N cerr DIA, M<N existen. ab sube para M no para N. | Eliminar phantoms, contar M latas |
| PF7 | AB_IMP | Abierta sube sin fuente y sin cerr desaparecida | Forward>backward para valor correcto |
| PF8 | NOMBRE_INCONSISTENTE | Par de sabores que nunca coexiste, pesos coherentes | Combinar como uno |

---

## CUÁNDO APLICAR PROTOTIPO DIRECTO

Aplicar sin análisis multi-turno extensivo si:
1. El caso matchea exactamente 1 prototipo fuerte.
2. La evidencia es unívoca (no hay hipótesis alternativa plausible).
3. La confianza del prototipo es ≥0.85.

Registrar como: `prototipo:[ID], conf:[valor], delta:[g]`.

---

## CUÁNDO DEJAR EN OBSERVACIÓN

Dejar sin corregir (H0) si:
1. Múltiples prototipos compiten sin evidencia para elegir.
2. El historial del can tiene <2 sightings.
3. El impacto es <200g (ruido de pesaje plausible).
4. No hay violación física clara.

Registrar como: `H0, motivo:[razón], impacto_max:[g]`.

---

## CUÁNDO ACTIVAR MULTI-TURNO EXTENSIVO

Activar SOLO si:
1. El caso tiene ≥2 señales simultáneas (ej: raw negativo + cerr 1-sighting + ab sube).
2. Ningún prototipo solo explica todas las señales.
3. El impacto potencial es >2000g.
4. El engine dio resultado cuestionable o contradictorio.

Análisis extensivo = extraer timeline completa + aplicar detectores a→g + verificar forward/backward ±3 turnos.

**El multi-turno extensivo NO es default. Es excepción.**

---

## FORMATO DE SALIDA DIARIO

```
# Auditoría Día [N] — [fecha]

## Clasificación: [X] LIMPIO, [Y] ENGINE, [Z] ESCALADO

## Engine confirmados
| Sabor | Tipo | Venta neta | Latas | Conf |

## Escalados (plantilla 04d por caso)

## Tabla final
| Sabor | Nivel | Venta | Latas | Conf |

## Totales
| Conservador | venta_stock | latas | VDP | total |
| Estimado    | venta_stock | latas | VDP | total |

## Casos abiertos (si hay)
| Sabor | Impacto max | Motivo |

## Scorecard (si hay GT)
| AC | AN | FA | SC | OP | Δ total |
```
