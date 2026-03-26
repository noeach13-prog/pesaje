# Capa 4 — Pseudocódigo ejecutable

Traducción directa de los 6 archivos draft a algoritmo paso a paso.
Cada paso tiene: INPUT, OPERACIÓN, OUTPUT, REFERENCIA al draft.

---

## PASO 0: Entrada

```
INPUT:
  sabor: str
  datos_dia: DatosDia          (Capa 1)
  contabilidad: SaborContable  (Capa 2)
  flags_c3: List[FlagC3]       (Capa 3)

OUTPUT:
  Correccion | H0
```

---

## PASO 1: Construir timeline del sabor

REF: 04_v3 §4.2, 04b_v3 §4.2

```
timeline = []
para cada turno en [contexto_previo, DIA, NOCHE, contexto_posterior]:
    si turno tiene este sabor:
        agregar snapshot(turno_label, ab, cerradas[], entrantes[], total)

# Necesitamos al menos DIA y NOCHE para operar.
si falta DIA o NOCHE: return H0("datos insuficientes")
```

---

## PASO 2: Generar los 4 planos de evidencia

### PLANO 1 — Serie temporal de abierta

REF: 04_v3 §4.2, §4.3

```
ab_D = dia.abierta
ab_N = noche.abierta
delta_ab = ab_N - ab_D

# Buscar fuentes que desaparecen (cerrada o entrante)
fuentes_desaparecidas = cerr_DIA sin match en NOCHE (±30g)
                      + ent_DIA sin match en NOCHE (±50g)

# Clasificar transición
si |delta_ab| <= 20:
    P1 = ESTATICA
sino si delta_ab < -20:
    P1 = VENTA_PURA
sino si delta_ab > 20 y hay fuente_desaparecida:
    expected_rise = peso_fuente - 280 (tapa)
    si |delta_ab - expected_rise| <= max(500, expected_rise * 0.15):
        P1 = APERTURA_SOPORTADA(fuente=X)
    sino:
        P1 = APERTURA_PLAUSIBLE_NO_CONFIRMADA
sino si delta_ab > 20 y NO hay fuente:
    P1 = AB_SUBE_SIN_FUENTE  # imposibilidad física

# Output: clasificación + delta_ab + fuente si existe
```

### PLANO 2 — Multiconjunto de cerradas

REF: 04_v3 §4.3

```
cerr_A = dia.cerradas (sorted)
cerr_B = noche.cerradas (sorted)

# Vista 1: delta bruto
desaparecen = cerr en A sin match en B (±30g)
aparecen    = cerr en B sin match en A (±30g)
persisten   = pares matched (ca, cb, diff)

# Vista 2: sightings (de TODA la timeline, no solo DIA/NOCHE)
para cada cerrada (tanto A como B como matched):
    sightings[peso] = count(turnos donde aparece ±30g)

# Output: desaparecen[], aparecen[], persisten[], sightings{}
```

### PLANO 3 — Genealogía de entrantes

REF: 04_v3 §4.4

```
ent_A = dia.entrantes
ent_B = noche.entrantes

# Matching
persisten = pares (ea, eb) donde |ea - eb| <= 50g
nuevos_B  = ent en B sin match en A  # entrantes nuevos en NOCHE
gone_A    = ent en A sin match en B  # entrantes que desaparecen

# Genealogía: buscar en timeline
para cada entrante:
    primera_aparicion = primer turno en timeline donde aparece (±50g)
    ciclo = COMPLETO | PARCIAL | SIN_GENEALOGIA | HUERFANO

# Output: persisten[], nuevos_B[], gone_A[], genealogias[]
```

### PLANO 4 — Celíacas/sublíneas

```
# Solo si hay vínculo operativo real con el caso
# Por ahora: skip (la mayoría de casos no lo necesitan)
P4 = NO_APLICA
```

---

## PASO 3: Generar TODAS las hipótesis posibles

REF: 04_v3 §4.6, 04b_v3 §4.6, 04c_v3 §CONFLICTO

```
hipotesis = []

# --- 3a: Para cada cerrada que DESAPARECE (en DIA, no en NOCHE) ---
para cada (peso, sightings) en P2.desaparecen:

    # H: Phantom — esta cerrada no existía realmente
    hipotesis.agregar(
        tipo = 'PHANTOM_DIA',
        accion = "eliminar cerr {peso} de DIA",
        delta_stock = -peso,
        delta_latas = -1 si n_cerr_A > n_cerr_B sino 0,
        evidencia_P1 = P1.clasificacion,  # VENTA_PURA o ESTATICA soporta
        evidencia_P2 = sightings,          # 1-sighting soporta
    )

    # H: Fue abierta legítimamente (parte de ENGINE)
    si P1 es APERTURA_SOPORTADA y P1.fuente == peso:
        hipotesis.agregar(
            tipo = 'APERTURA_REAL',
            accion = "confirmar apertura de cerr {peso}",
            delta_stock = 0,  # ya está en el raw
            evidencia_P1 = 'APERTURA_SOPORTADA',
            evidencia_P2 = sightings,
        )

# --- 3b: Para cada cerrada que APARECE (en NOCHE, no en DIA) ---
para cada (peso, sightings) en P2.aparecen:

    # H: Omisión en DIA — la cerrada existía pero no la anotaron
    hipotesis.agregar(
        tipo = 'OMISION_DIA',
        accion = "agregar cerr {peso} a DIA",
        delta_stock = +peso,
        evidencia_P1 = P1.clasificacion,  # VENTA_PURA soporta (ab no sube)
        evidencia_P2 = sightings,          # ≥2 sightings soporta
    )

    # H: Phantom en NOCHE — alguien la anotó de más
    hipotesis.agregar(
        tipo = 'PHANTOM_NOCHE',
        accion = "eliminar cerr {peso} de NOCHE",
        delta_stock = +peso,  # same direction: más venta
        evidencia_P1 = P1.clasificacion,
        evidencia_P2 = sightings,  # 1-sighting soporta phantom
    )

# --- 3c: Para cada entrante que PERSISTE (DIA→NOCHE matched) ---
para cada (ea, eb, diff) en P3.persisten:
    si P1 es APERTURA (la abierta subió):
        # H: Entrante fue abierto pero sigue listado en NOCHE
        hipotesis.agregar(
            tipo = 'ENTRANTE_DUP',
            accion = "eliminar entrante {eb} de NOCHE",
            delta_stock = +eb,  # total_B baja → venta sube
            evidencia_P1 = 'APERTURA',
            evidencia_P3 = 'genealogia confirma apertura',
        )

# --- 3d: Para cada entrante NUEVO en NOCHE ---
para cada ent_nuevo en P3.nuevos_B:
    # H: entrante legítimo (ya contado en new_ent_B del contrato)
    # No requiere corrección, ya está en el raw
    pass  # Solo documentar

# --- 3e: Para cerradas con match 30-100g (mismatch leve) ---
para cada (ca, cb, diff, sightings) en P2.persisten donde diff > 30:
    hipotesis.agregar(
        tipo = 'MISMATCH_LEVE',
        accion = "ajuste pesaje {ca}→{cb}",
        delta_stock = -(diff),
        evidencia_P2 = 'solo P2, ajuste fino',
    )
```

---

## PASO 4: Evaluar cada hipótesis contra TODOS los planos

REF: 04_v3 §4.6 "Regla epistemológica fuerte"

```
para cada H en hipotesis:

    planos_a_favor = []
    planos_neutros = []
    planos_en_contra = []

    # --- Evaluar P1 ---
    si H.tipo en (PHANTOM_DIA, OMISION_DIA):
        si P1 es VENTA_PURA o ESTATICA:
            # Ab no sube → no hubo apertura → cerr no se abrió
            # Soporta tanto phantom como omisión
            planos_a_favor.append('P1')
        sino si P1 es APERTURA_SOPORTADA:
            si H.tipo == PHANTOM_DIA y H.peso != P1.fuente:
                planos_a_favor.append('P1')  # la apertura es de OTRA cerrada
            sino:
                planos_en_contra.append('P1')  # ab sube, contradicción

    si H.tipo == ENTRANTE_DUP:
        si P1 es APERTURA:
            planos_a_favor.append('P1')  # apertura confirma que el entrante se abrió
        sino:
            planos_en_contra.append('P1')  # sin apertura, no hay dup

    # --- Evaluar P2 ---
    si H.tipo == PHANTOM_DIA:
        si H.sightings <= 1:
            planos_a_favor.append('P2')  # 1-sighting = phantom probable
        sino si H.sightings == 2:
            planos_neutros.append('P2')  # ambiguo
        sino:
            planos_en_contra.append('P2')  # ≥3 sightings = cerrada real

    si H.tipo == OMISION_DIA:
        si H.sightings >= 3:
            planos_a_favor.append('P2')  # muchos sightings = cerrada real
        sino si H.sightings == 2:
            planos_a_favor.append('P2')  # 2 sightings (NOCHE + otro) = probable
        sino:
            planos_en_contra.append('P2')  # 1 sighting = puede ser phantom

    si H.tipo == ENTRANTE_DUP:
        planos_neutros.append('P2')  # cerradas no afectadas

    # --- Evaluar P3 ---
    si H.tipo == ENTRANTE_DUP:
        planos_a_favor.append('P3')  # genealogía directa
    sino:
        planos_neutros.append('P3')  # sin entrantes relevantes = NEUTRO

    # --- Verificar independencia ---
    independientes = len(set(planos_a_favor))  # planos distintos

    # --- GUARDIA DE COHERENCIA ---
    venta_corregida = raw + H.delta_stock + H.delta_latas * 280
    si venta_corregida < -300:
        planos_en_contra.append('COHERENCIA')  # resultado imposible
    si abs(venta_corregida) > total_A * 0.8:
        planos_en_contra.append('COHERENCIA')  # vendió casi todo = sospechoso

    # --- Score final ---
    H.n_favor = len(planos_a_favor)
    H.n_contra = len(planos_en_contra)
    H.independientes = independientes
    H.converge = independientes >= 2 y n_contra == 0
```

---

## PASO 5: Seleccionar la mejor hipótesis (o combinación)

REF: 04c_v3 §CONFLICTO, 04_v3 §4.8

```
# Filtrar: descartar hipótesis con plano en contra
viables = [H para H en hipotesis si H.n_contra == 0]

# Si ninguna viable: H0
si viables está vacío:
    return H0("todas las hipótesis tienen contradicción")

# Ordenar por: convergencia > n_favor > confianza
viables.sort(key=lambda H: (H.independientes, H.n_favor), reverse=True)

mejor = viables[0]

# Verificar regla ≥2 planos independientes
si mejor.independientes < 2:
    # Excepción: Tipo C (prototipo fuerte con ratio sightings ≥3:1)
    si mejor.tipo == PHANTOM_DIA y mejor.sightings <= 1:
        # Verificar si hay cerradas con ≥3 sightings que sí están
        ratio_ok = any(s >= 3 for s in P2.sightings_matched.values())
        si ratio_ok:
            mejor.tipo_just = C  # prototipo fuerte
        sino:
            return H0("solo 1 plano, sin ratio suficiente")
    sino:
        return H0("requiere ≥2 planos independientes")

# Para COMPUESTO: ¿hay múltiples hipótesis compatibles?
# (ej: phantom + omisión en el mismo sabor)
si len(viables) > 1 y viables[0] y viables[1] no se contradicen:
    # Intentar componer
    compuesta_delta = viables[0].delta + viables[1].delta
    compuesta_venta = raw + compuesta_delta
    si compuesta_venta es razonable (0 a stock_disponible):
        # Corrección compuesta
        mejor = combinar(viables[0], viables[1])
```

---

## PASO 6: Asignar tipo de justificación y banda

REF: metodo_bandas_decision_d5.md §C, §D

```
# Tipo de justificación
si mejor.independientes >= 2:
    tipo = A  # convergencia independiente
sino si mejor es prototipo fuerte con ratio ≥3:1:
    tipo = C  # prototipo histórico
sino si raw es físicamente imposible y mejor es la única alternativa:
    tipo = B  # reductio
sino:
    tipo = D  # ajuste menor

# Banda
si tipo == A o tipo == C:
    banda = CONFIRMADO
sino si tipo == B:
    banda = FORZADO
sino:
    banda = ESTIMADO

# Confianza
conf_base = 0.65 + 0.10 * mejor.independientes
si COPIA_POSIBLE_FUERTE: conf -= 0.15
si tipo == B: conf -= 0.10  # incertidumbre residual
conf = max(0.30, min(0.95, conf))
```

---

## PASO 7: Verificación post-corrección

REF: nueva regla de la conversación (guardia de coherencia)

```
venta_final = raw + mejor.delta_total
si venta_final < -300:
    RECHAZAR corrección, return H0("corrección produce resultado imposible")
si |venta_final| > |raw| y raw no era negativo:
    RECHAZAR corrección, return H0("corrección empeora el resultado")

return Correccion(mejor)
```

---

## PASO ESPECIAL: ENGINE con phantom oculto

REF: 04_v3 §4.7 "Abierta como testigo"

```
Para cada sabor ENGINE con N cerradas que desaparecen (N >= 2):

    # ¿El rise de ab es coherente con N aperturas?
    rise_esperado_N = sum(cerr_gone) - N * 280
    rise_real = delta_ab

    si rise_real < rise_esperado_N * 0.6:
        # Rise insuficiente para N aperturas
        # Buscar phantom entre las cerradas que desaparecen
        para cada cerr en cerr_gone:
            si sightings(cerr) <= 1:
                # Candidato a phantom
                # Verificar: sin esta cerr, ¿rise es coherente con N-1?
                rise_esperado_N1 = sum(cerr_gone) - cerr - (N-1) * 280
                si |rise_real - rise_esperado_N1| <= max(500, rise_esperado_N1 * 0.15):
                    → Phantom confirmado por P1 + P2
                    → Tipo A, CONFIRMADO
```

---

## PASO ESPECIAL: Análisis CONJUNTO cross-sabor

REF: conversación sobre DDL+DA, routing A- → CONJUNTO

```
Después de resolver todos los escalados individualmente:

# Buscar patrones cruzados
omisiones_dia = [sabores donde H ganadora = OMISION_DIA]
phantoms_dia  = [sabores donde H ganadora = PHANTOM_DIA]

si len(omisiones_dia) >= 2:
    # Patrón: turno DIA omitió cerradas en múltiples sabores
    # Elevar confianza de todos a CONFIRMADO_CONJUNTO
    para cada sabor en omisiones_dia:
        sabor.grupo = "OMISION_DIA_SISTEMATICA"
        si sabor.independientes < 2:
            sabor.independientes = 2  # patrón cross-sabor = plano adicional
            sabor.tipo = A
            sabor.banda = CONFIRMADO

# Buscar misregistro bilateral (DDL+DA style)
# Cerrada X aparece en sabor A pero no en B en DIA,
# y en sabor B pero no en A en NOCHE
para cada cerr_peso en todas_las_cerradas_anomalas:
    sabor_tiene_en_dia = [s donde cerr_peso está en s.DIA.cerradas]
    sabor_tiene_en_noche = [s donde cerr_peso está en s.NOCHE.cerradas]
    si sabor_tiene_en_dia != sabor_tiene_en_noche:
        # Misregistro de asignación
        → Corrección bilateral: mover cerr de un sabor a otro
        → Tipo A, CONFIRMADO_CONJUNTO
```

---

## RESUMEN DE GUARDIAS

| Guardia | Qué previene | Paso |
|---------|-------------|------|
| Resultado peor que raw | Corrección contraproducente (CHOCOLATE) | 7 |
| ≥2 planos independientes | Corrección por señal única | 5 |
| Plano en contra descarta | Hipótesis contradictoria con evidencia | 4 |
| Sightings ≥3 = cerrada real | Eliminar cerrada que existe | 4 (P2) |
| Rise coherente con N aperturas | ENGINE con phantom oculto | Especial |
| Patrón cross-sabor | A- routing a CONJUNTO | Especial |
