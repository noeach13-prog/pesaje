# Baseline operativo — Lógica de resolución congelada

Fecha de congelamiento: 2026-03-20
Estado: PRODUCCIÓN

---

## 1. ARCHIVOS CONGELADOS

Estos archivos constituyen el sistema de resolución validado.
No deben modificarse mientras se trabaja en parser, exporter u otros componentes.

| Archivo | Rol | Versión |
|---------|-----|---------|
| `04b_runtime_operativo.md` | Ejecución diaria: criterios, orden, precedencias, prototipos | v1 (2026-03-20) |
| `04c_matriz_de_activacion.md` | Decisión por caso: matriz, conflictos, regla anti-default | v1 (2026-03-20) |
| `04d_plantilla_caso_escalado.md` | Formato de salida para escalados (8 líneas/caso) + ejemplos D28 | v1 (2026-03-20) |
| `04_sistema_de_escalado.md` | Documento maestro de referencia (NO se usa en ejecución diaria) | v2 (2026-03-20) |

### Archivos de datos (fuentes, no lógica)

| Archivo | Rol | Estado |
|---------|-----|--------|
| `02_observaciones_normalizadas.csv` | Datos raw por sabor/turno | Congelado para Febrero 2026 |
| `03_historias_por_sabor.json` | Timelines mensuales con métricas | Congelado para Febrero 2026 |
| `03_historias_por_sabor.md` | Versión legible de historias | Congelado para Febrero 2026 |

### Archivos de método (referencia, no ejecución)

| Archivo | Rol | Estado |
|---------|-----|--------|
| `00_metodo_operativo.md` | Método extraído del DOCX D26 | Referencia. No se usa en runtime. |
| `01_mapa_workbook.md` | Estructura del Excel | Referencia. |

---

## 2. PARTES QUE NO DEBEN MODIFICARSE

### Lógica congelada

| Componente | Ubicación | Prohibición |
|------------|-----------|-------------|
| Criterios de activación (5 condiciones) | 04b §CRITERIOS | No cambiar thresholds ni orden |
| Precedencias P1–P5 | 04b §PRECEDENCIAS | No agregar, quitar ni reordenar |
| Prototipos PF1–PF8 | 04b §PROTOTIPOS FUERTES | No agregar ni modificar firmas/confianzas |
| Orden de detectores a→g | 04b §F4 (implícito vía 04_v2) | No reordenar |
| Matriz de 5 niveles | 04c §MATRIZ PRINCIPAL | No agregar niveles ni cambiar acciones |
| Regla anti-default | 04c §REGLA ANTI-DEFAULT | No relajar secuencia ①→⑥ |
| Protocolo de conflicto | 04c §CONFLICTO | No cambiar prioridad de violación física |
| Formato de caso (7 campos) | 04d §Formato | No agregar campos |
| Scorecard (AC/AN/FA/SC/OP) | 04_v2 §MÉTRICA | No cambiar definiciones |

### Lo que SÍ puede modificarse

| Componente | Condición |
|------------|-----------|
| `parser.py` | Libre. El parser no afecta la lógica de resolución. |
| `exporter.py` | Libre. |
| `calculator.py` | Solo si no cambia la fórmula `venta = total_A - total_B`. |
| VDP parsing | Libre y prioritario (ver §4). |
| Nuevas auditorías diarias (`auditorias_diarias/`) | Libre. Usar runtime congelado. |
| Agregar nuevos prototipos PF9+ | Solo tras validación contra GT de un nuevo día. |

---

## 3. ESTADO DE VALIDACIÓN

### D28: convergencia confirmada

| Métrica | Runtime | GT (v3) | Δ |
|---------|---------|---------|---|
| Venta stock | 51,165g | 51,165g | **0g** |
| Latas | 5 (1,400g) | 5 (1,400g) | **0** |
| Scorecard | 51 AC, 1 AN | — | — |

### D26: validación parcial (pre-runtime v2)

| Métrica | Estado |
|---------|--------|
| Auditoría completa | Existe (`05_auditoria_dia_26.md` pendiente de escritura formal) |
| Prototipos extraídos | PF1, PF2, PF3, PF7 validados contra DOCX |

### Días no auditados

27 días restantes de Febrero sin auditoría. El runtime está listo para corrida.

---

## 4. DIVERGENCIA PENDIENTE: VDP

| Fuente | Valor D28 | Notas |
|--------|-----------|-------|
| Engine (`parser.py`) | 2,270g | Parsea 5 entries: 1KILO+1/4x2+2CUCUR+2BOCHAS+2CUCUR |
| GT (PDF) | 3,020g | NOCHE solamente, DIA=0 |
| Δ | **−750g** | |

**Causa**: el parser no captura todas las entradas de VDP, o las convierte con gramaje distinto al GT.

**Impacto**: afecta el total del día pero NO la venta stock ni las correcciones de sabores.

**Acción requerida**: revisar `parser.py` función `_parse_vdp_texts` / `text_to_grams`. Esta corrección es independiente del baseline de resolución y no lo afecta.

---

## 5. PROTOCOLO PARA AGREGAR NUEVOS DÍAS

```
1. Extraer datos del día desde CSV + JSON (ya congelados para Febrero).
2. Ejecutar F0→F6 de 04b_runtime_operativo.md.
3. Para escalados: usar 04c para decidir, 04d para formato.
4. Guardar en auditorias_diarias/dia_[N]_auditoria.md.
5. Si hay GT disponible (PDF resuelto):
   a. Crear dia_[N]_ground_truth.md.
   b. Comparar con scorecard.
   c. Si aparece patrón nuevo no cubierto por PF1–PF8:
      documentar como candidato, NO agregarlo al baseline
      hasta validar contra ≥1 GT adicional.
```
