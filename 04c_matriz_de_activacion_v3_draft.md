# Matriz de activación v3 — Decisión por caso (DRAFT)

---

## MATRIZ PRINCIPAL

| Clasificación | Señales | Capa | Acción |
|--------------|---------|------|--------|
| **LIMPIO** | Condiciones 1-5 pasan | 3 → 5 | Usar raw_sold. No analizar en Capa 3. Pasa a Capa 5 (segunda pasada residual). |
| **ENGINE** | engine_sold ≠ raw_sold, sin otra señal | 3 | Verificar tipo. Si correcto: usar engine_sold. Si cuestionable: escalar a SOSPECHOSO. |
| **OBSERVACIÓN** | 1 señal aislada, baja magnitud (<500g): cerr diff T3, ab sube ≤100g, raw -50 a -200g | 3 | Registrar nota. Usar raw_sold. No corregir. |
| **SOSPECHA SIMPLE** | 1 señal clara que matchea exactamente 1 prototipo fuerte | 3 | Aplicar prototipo directo. Conf ≥0.85. |
| **SOSPECHA COMPUESTA** | ≥2 señales simultáneas O 1 señal >2000g sin prototipo unívoco | 3 → 4 | Escalar a Capa 4: expediente ampliado de 4 planos. |
| **VIOLACIÓN ESTRUCTURAL** | Imposibilidad física: ab sube sin fuente, venta > stock, RM-3 | 3 → 4 | Si prototipo fuerte resuelve: aplicar en Capa 3. Si no: Capa 4 obligatoria. |

---

## DECISIÓN POR PROTOTIPO FUERTE

| Prototipo | Aplicar directo (Capa 3) si... | Escalar a Capa 4 si... |
|-----------|-------------------------------|----------------------|
| PF1 DIGIT_TYPO | ≥5 sightings + offset exacto + turno prev/next normal | Offset no es exacto ±1000/±2000, o sightings <5 |
| PF2 ENTRANTE_DUP | Entrante DIA = NOCHE + ab sube desde ~0 | Entrante difiere >50g entre turnos, o ab ya tenía peso |
| PF3 PHANTOM_CERR | RM-3 claro (abierta turno anterior) | RM-3 ambiguo (abierta parcial) o cerr tiene 2+ sightings |
| PF4 CERR_OMIT_NOCHE | Cerr ≥2 sightings + no en NOCHE + ab no sube | Cerr con 1 sighting, o ab sube parcialmente |
| PF5 CERR_OMIT_DIA | Cerr ≥2 sightings + no en DIA + raw negativo | Cerr con 1 sighting, o raw negativo explicable de otro modo |
| PF6 APERTURA+PHANTOM | Ab sube coherente con M<N cerr + extras cumplen P1 | Ab sube no coherente con ningún M, o extras tienen historial |
| PF7 AB_IMP | Ab sube + cerradas intactas + forward confirma | Forward ambiguo, o cerr parcialmente cambiadas |
| PF8 NOMBRE_INCONS | Par nunca coexiste + pesos ±30g + 1 tiene muchos turnos | Pesos difieren >30g, o ambos tienen muchos turnos |

---

## DECISIÓN DE RESOLUCIÓN EN CAPA 4

Después de construir expediente de 4 planos:

| Situación | Resolución |
|-----------|------------|
| ≥2 planos independientes convergen | Aplicar corrección. Tipo: INDIVIDUAL o CONJUNTO. |
| 2 planos convergen pero repiten evidencia | NO suficiente. Buscar plano adicional o → H0. |
| Solo 1 plano tiene evidencia | H0 / UNRESOLVED. No corregir. |
| Única evidencia contra cerrada = "sin genealogía" | H0. La ausencia no incrimina. |
| Cerradas cercanas, identidad ambigua, resultado no depende | RESUELTO_CONJUNTO. |
| Cerradas cercanas, identidad ambigua, resultado SÍ depende | IDENTITY_AMBIGUOUS → UNRESOLVED. |
| Orden de correcciones cambia resultado, ninguno converge mejor | UNRESOLVED. Documentar ambos resultados. |
| Orden de correcciones cambia resultado, uno converge con ≥2 planos más | Aplicar ese orden. |
| Dato clave marcado COPIA_POSIBLE_FUERTE | Conf -0.15. Si conf resultante <0.50 → H0. |

---

## DECISIÓN DE SEGUNDA PASADA (Capa 5)

Para cada sabor que salió LIMPIO de Capa 3:

| Señales residuales detectadas | Acción |
|------------------------------|--------|
| 0 señales | LIMPIO_CONFIRMADO. No reabrir. |
| 1 señal aislada (solo desvío histórico O solo rareza estructural) | LIMPIO_CON_NOTA. Registrar, no reabrir. |
| ≥2 señales de distinto tipo (desvío + rareza + perfil anómalo) | REABRIR. Vuelve a Capa 3 (o Capa 4 si es compuesto). |

Señales residuales:
- **Desvío histórico**: venta del sabor está >1.8σ del promedio mensual
- **Rareza estructural débil**: cerr cercanas (30-75g), ab plana en contexto de venta, entrante sin genealogía
- **Perfil de día anómalo**: muchos sabores simultáneamente en extremos opuestos (compensación)

---

## CONFLICTO ENTRE HIPÓTESIS (actualizado de v2)

```
1. ¿Alguna implica violación física (RM-3, ab imposible)?
   → Sí: prioridad a esa hipótesis.

2. ¿Alguna tiene ≥2 planos independientes?
   → Sí: prioridad a esa hipótesis.

3. ¿Los dos dan el mismo resultado numérico?
   → Sí: RESUELTO_CONJUNTO. Registrar como AN.

4. Si dan resultados distintos:
   a. Aplicar P1 (preservar stock mínimo).
   b. Elegir la que elimina MENOS stock.
   c. Registrar alternativa como nota.
   d. Conf = min(conf_H1, conf_H2) - 0.15.

5. Si ninguna tiene conf >0.50 después de ajustes:
   → H0. No corregir. Caso abierto.
```

---

## REGLA ANTI-DEFAULT (actualizada)

```
EL EXPEDIENTE AMPLIADO DE 4 PLANOS NO ES DEFAULT.

Secuencia obligatoria:
  ① ¿Es LIMPIO?                          → Capa 5 (segunda pasada), parar Capa 3.
  ② ¿Es ENGINE verificado?               → Mantener, parar.
  ③ ¿Es OBSERVACIÓN menor?               → Registrar nota, parar.
  ④ ¿Matchea 1 prototipo fuerte unívoco? → Aplicar directo, parar.
  ⑤ ¿Hay conflicto sin evidencia >0.50?  → H0, parar.
  ⑥ Solo si llega aquí                   → Capa 4: expediente ampliado.
```
