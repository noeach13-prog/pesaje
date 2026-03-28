# Cambios v2 → v3 — Tabla de diferencias (DRAFT)

---

## TABLA PRINCIPAL

| # | Qué cambia | v2 | v3 | Capa | Corrección | Riesgos cubiertos |
|---|-----------|----|----|------|------------|-------------------|
| 1 | **Arquitectura general** | Pipeline lineal (Fases 0-6) | 5 capas con responsabilidades separadas | Todas | C8 (separación de capas) | — |
| 2 | **Expediente ampliado** | No existe. Plantilla de 8 líneas para todo caso escalado | Solo para SOSPECHA COMPUESTA, VIOLACIÓN sin prototipo, conflicto de hipótesis, corrección >2000g sin evidencia unívoca | 4 | C1 (expediente selectivo) | Evita over-analysis de casos simples |
| 3 | **4 planos de evidencia** | No existen como estructura formal. El análisis multi-turno es libre | P1 abierta, P2 cerradas (2 vistas), P3 entrantes, P4 sublíneas. Obligatorios en Capa 4 | 4 | C2 (coherencia conjunta) | — |
| 4 | **Definición de APERTURA** | Proxy: ab sube >3000g con cerr gone | Señal compuesta de 3 patas: ab sube + desaparece fuente + rise coherente. Sin umbral fijo | 4 | C2 (Plano 1) | Evita clasificar como apertura sin evidencia completa |
| 5 | **Multiconjunto de cerradas** | Matching individual greedy ±30g | 2 vistas: delta bruto + equivalencias NO VINCULANTES. Resolución por conjunto cuando identidad no importa | 4 | C2 (Plano 2), C4 (R2/R8) | R2 (cerradas cercanas), R8 (tolerancia ambigua) |
| 6 | **Genealogía de entrantes** | Sin estructura formal | Ciclo de vida: aparece→persiste→promueve→abre→desaparece. SIN_GENEALOGÍA = evidencia NEUTRA | 4 | C2 (Plano 3), C3 (regla epistemológica) | Evita incriminar cerradas por ausencia de genealogía |
| 7 | **Regla epistemológica ≥2 planos** | No existe. Una señal fuerte puede resolver | Corrección material requiere ≥2 planos convergentes e independientes. Planos redundantes no cuentan | 4 | C3 (epistemología fuerte) | Evita correcciones por señal única |
| 8 | **Abierta como testigo R2/R8** | Abierta se usa para detectar AB_IMP pero no como testigo de cerradas | Abierta participa activamente en resolver identidad de cerradas cercanas | 4 | C4 (R2/R8) | R2, R8 |
| 9 | **Tipo de resolución** | No existe. Todo es "corregido" o "H0" | RESUELTO_INDIVIDUAL, RESUELTO_CONJUNTO, IDENTITY_AMBIGUOUS, H0, UNRESOLVED | 4 | C4 (honestidad de ambigüedad) | Evita fingir identidad cuando solo hay pool |
| 10 | **Segunda pasada residual** | No existe. LIMPIO es terminal | Capa 5: detector estadístico-estructural de falsos LIMPIO por errores compensados | 5 | C5 (falsos LIMPIO) | Riesgo A (errores compensados) |
| 11 | **Señales residuales** | No existen | R1 (desvío histórico), R2 (rareza estructural débil), R3 (perfil de día anómalo). Reabrir si ≥2 | 5 | C5 | Riesgo A |
| 12 | **Marca COPIA_POSIBLE** | No existe. Estática se trata como dato confiable | COPIA_POSIBLE_LEVE (2 turnos), COPIA_POSIBLE_FUERTE (≥3 turnos). Degrada conf -0.15 | 3 | C6 (Riesgo E) | Riesgo E (dato copiado) |
| 13 | **Orden de correcciones** | Orden fijo en Fase 4.2 (a→g) presentado como necesario | Heurística por defecto (phantom→entrante_dup→omisión→apertura). Si no converge → UNRESOLVED | 4 | C7 (Riesgo F) | Riesgo F (no conmutatividad) |
| 14 | **Separación parser/contrato/motor** | Implícita. Todo en el mismo documento | Capa 1 (parser), Capa 2 (contrato contable), Capa 3 (motor local) con responsabilidades estrictas | 1, 2, 3 | C8 (separación de capas) | Evita mezclar lectura, definición y resolución |
| 15 | **ab=None vs ab='' vs ab=0** | No diferenciados | Preservados como distintos en Capa 1, interpretados en Capa 3+ | 1 | C8 (parser) | Evita colapso prematuro de datos faltantes |

---

## QUÉ SE PRESERVA INTACTO DE v2

| Elemento | Estado en v3 |
|----------|-------------|
| Fórmula de venta (Capa 2) | Idéntica |
| Criterios de clasificación (5 condiciones) | Idénticos en Capa 3 |
| Prototipos fuertes PF1-PF8 | Idénticos en Capa 3 |
| Precedencias P1-P5 | Idénticas en Capa 3 |
| Scorecard AC/AN/FA/SC/OP | Idéntico |
| Criterios de confianza (alta/media/baja/H0) | Idénticos, +ajustes por COPIA_POSIBLE |
| Datos empíricos de referencia | Idénticos |
| Anomalías específicas (AB_IMP, 1-sighting, dígito, etc.) | Idénticos como detectores |

---

## MAPEO CORRECCIÓN → RIESGO

| Corrección | Riesgos que cubre |
|-----------|-------------------|
| C1 — Expediente ampliado selectivo | — (eficiencia, no riesgo específico) |
| C2 — 4 planos coherencia conjunta | R2 (cerradas cercanas), R8 (tolerancia) |
| C3 — Regla epistemológica ≥2 planos | R2, R8, evita sobre-corrección general |
| C4 — Abierta como testigo R2/R8 | R2, R8 directamente |
| C5 — Segunda pasada falsos LIMPIO | Riesgo A (errores compensados) |
| C6 — Marca COPIA_POSIBLE | Riesgo E (dato copiado) |
| C7 — Orden no conmutativo | Riesgo F (orden importa) |
| C8 — Separación de capas | Todos indirectamente (claridad arquitectural) |

---

## CONFLICTOS Y NOTAS

### Conflicto 1: Proxy de apertura >3000g
v2 lo usa en criterio 2 de clasificación. v3 lo redefine en Capa 4.
**Resolución**: el proxy se mantiene en Capa 3 como screening rápido.
La redefinición de 3 patas aplica solo en Capa 4.

### Conflicto 2: LIMPIO como terminal
v2 no revisita LIMPIO. v3 agrega Capa 5.
**Resolución**: Capa 5 es aditiva. No contradice v2, la extiende.

### Nota 1: Calibración pendiente
Los thresholds de Capa 5 (1.8σ, máximo 5 reaperturas) y Capa 3 (COPIA_POSIBLE)
requieren calibración empírica. Son propuestas razonables, no valores validados.

### Nota 2: Costo operativo
v3 agrega complejidad a los casos escalados (Capa 4) y una pasada extra (Capa 5).
Para la mayoría de sabores (~95%), el flujo es idéntico a v2.
El costo adicional se concentra en los ~5% que realmente lo necesitan.
