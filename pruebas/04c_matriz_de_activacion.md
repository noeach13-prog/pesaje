# Matriz de activación — Decisión por caso

## MATRIZ PRINCIPAL

| Clasificación | Señales | Acción | Multi-turno |
|--------------|---------|--------|-------------|
| **LIMPIO** | Todas las condiciones 1–5 pasan | Usar raw_sold. No analizar. | NO |
| **ENGINE** | engine_sold ≠ raw_sold, sin otra señal | Verificar tipo (omission/phantom/digit). Si correcto: usar engine_sold. Si cuestionable: escalar. | NO (solo verificación) |
| **OBSERVACIÓN** | 1 señal aislada de baja magnitud (<500g): cerr diff T3, ab sube ≤100g sin cerr gone, raw ligeramente negativo (-50 a -200g) | Registrar nota. Usar raw_sold. No corregir. | NO |
| **SOSPECHA COMPUESTA** | ≥2 señales simultáneas O 1 señal de alta magnitud (>2000g): raw muy negativo + cerr sin match, venta alta + cerr desaparece sin apertura, ab sube + cerr nueva sin fuente | Aplicar prototipos P1–P5 en orden. Si 1 prototipo resuelve: aplicar directo. Si no: escalar a multi-turno. | SOLO SI ningún prototipo solo resuelve |
| **VIOLACIÓN ESTRUCTURAL** | Imposibilidad física directa: ab sube sin fuente (S2), venta > stock disponible, lata reaparece post-apertura (RM-3) | Corrección obligatoria. La violación física no queda en H0. Aplicar prototipo + P1–P5. | SÍ si el prototipo no alcanza |

---

## DECISIÓN POR PROTOTIPO FUERTE

| Si matchea prototipo | Evidencia requerida | Acción |
|---------------------|---------------------|--------|
| PF1 DIGIT_TYPO | ≥5 sightings estables + offset exacto ±1000/±2000 | Corregir peso. Conf 0.92. |
| PF2 ENTRANTE_DUP | Entrante DIA = entrante NOCHE + ab sube de 0 a ~5500-6200 | Poner entrante NOCHE en 0. Conf 0.90. |
| PF3 PHANTOM_CERR | RM-3 (abierta en turno anterior) O nota "no existe" | Poner cerr en 0. Conf 0.90 (RM-3) / 1.00 (nota). |
| PF4 CERR_OMITIDA_NOCHE | Cerr DIA con ≥2 sightings, no está en NOCHE, ab no sube | Agregar a NOCHE. Conf 0.85. |
| PF5 CERR_OMITIDA_DIA | Cerr NOCHE con ≥2 sightings, no está en DIA, raw negativo | Agregar a DIA. Conf 0.85. |
| PF6 APERTURA+PHANTOM | N cerr DIA, ab sube solo para M<N. Cerr extra sin historial/RM-3 | Eliminar phantoms, contar M latas. Conf 0.80. |
| PF7 AB_IMP | Ab sube sin cerr gone ni entrante. Sin threshold mínimo. | Forward>backward. Conf 0.60–0.85. |
| PF8 NOMBRE_INCONS | Par que nunca coexiste + pesos coherentes ±30g | Combinar. Conf 0.90. |

---

## CONFLICTO ENTRE HIPÓTESIS

Cuando 2+ prototipos compiten para el mismo sabor:

```
1. ¿Alguno implica violación física (RM-3, ab imposible)?
   → Sí: ese tiene prioridad.

2. ¿Alguno tiene evidencia directa (nota humana, historial ≥5)?
   → Sí: ese tiene prioridad.

3. ¿Los dos dan el mismo resultado numérico?
   → Sí: aplicar cualquiera, registrar como AN (acierto numérico).

4. Si dan resultados distintos:
   a. Aplicar P1 (preservar stock mínimo).
   b. Elegir la hipótesis que elimina MENOS stock.
   c. Registrar la alternativa como nota.
   d. Confianza = min(conf_H1, conf_H2) - 0.15.

5. Si ninguna hipótesis tiene conf >0.50:
   → H0. No corregir. Registrar como caso abierto.
```

---

## REGLA ANTI-DEFAULT

```
EL MULTI-TURNO EXTENSIVO NO ES DEFAULT.

Secuencia obligatoria antes de activar multi-turno:
  ① ¿Es LIMPIO?           → Sí: parar.
  ② ¿Es ENGINE verificado? → Sí: parar.
  ③ ¿Es OBSERVACIÓN menor? → Sí: registrar, parar.
  ④ ¿Matchea 1 prototipo?  → Sí: aplicar, parar.
  ⑤ ¿Hay conflicto <0.50?  → Sí: H0, parar.
  ⑥ Solo si llega aquí     → Multi-turno extensivo.
```
