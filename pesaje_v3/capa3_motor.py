"""
capa3_motor.py — Screening, señales y prototipos fuertes.
Resuelve ~95% de los sabores. El resto escala a Capa 4.
"""
from .modelos import (
    DatosDia, ContabilidadDia, SaborContable, SaborCrudo, TurnoCrudo,
    StatusC3, FlagC3, SaborClasificado, ResultadoC3,
    PrototipoAplicado, MarcaCalidad,
    ObservacionC3, SlotCerrada, SlotEntrante,
    DecisionC3, ResolucionC3, MotivoDecisionC3,
)
from .constantes_c3 import (
    APERTURA_PROXY_MIN_RISE, TOL_SUBA_AB_LEVE, TOL_MATCH_CERRADA,
    TOL_MATCH_ENTRANTE, TOL_PROMO_ENTRANTE, TOL_MISMATCH_LEVE,
    VENTA_NEG_THRESHOLD, VENTA_HIGH_THRESHOLD, TARA_LATA,
    PF1_OFFSETS, PF1_MIN_SIGHTINGS_STRONG, PF1_MIN_SIGHTINGS_WEAK,
    PF1_MAX_VAR_WEAK, PF1_CONF_STRONG, PF1_CONF_WEAK,
    PF2_CONF, PF3_CONF, PF3_MAX_SIGHTINGS_PHANTOM,
    PF4_MIN_SIGHTINGS, PF4_MIN_SIGHTINGS_NO_FORWARD, PF4_CONF, PF4_CONF_WEAK,
    PF5_MIN_SIGHTINGS, PF5_MIN_SIGHTINGS_NO_BACKWARD, PF5_CONF, PF5_CONF_WEAK,
    PF6_CONF, PF6_RISE_COHERENCE_RATIO, PF6_RISE_MAX_DIFF_RATIO,
    PF7_CONF_FORWARD, PF7_CONF_BACKWARD_ONLY, PF7_BACKWARD_TOLERANCE,
    CALIDAD_PENALIZACION_COPIA_FUERTE,
)
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# SCREENING — 5 condiciones
# ═══════════════════════════════════════════════════════════════

def _screening(nombre: str, sc: SaborContable, obs: ObservacionC3) -> tuple:
    """
    Evalua C1-C4 para un sabor. Lee SOLO desde ObservacionC3 y SaborContable.
    No toca datos crudos del turno. Retorna (status, flags).
    """
    if sc.solo_dia:
        return StatusC3.SOLO_DIA, []
    if sc.solo_noche:
        return StatusC3.SOLO_NOCHE, []

    flags = []

    # Apertura proxy: juicio derivado de metricas de observacion
    ab_d = obs.ab_d or 0
    ab_n = obs.ab_n or 0
    ab_delta = obs.ab_delta or 0
    apertura = ab_delta > APERTURA_PROXY_MIN_RISE and sc.n_cerr_a > sc.n_cerr_b

    # C1: raw >= VENTA_NEG_THRESHOLD
    if sc.venta_raw < VENTA_NEG_THRESHOLD:
        flags.append(FlagC3('NEG', 1, f'raw={sc.venta_raw}g'))

    # C2: raw < VENTA_HIGH_THRESHOLD o apertura
    if sc.venta_raw >= VENTA_HIGH_THRESHOLD and not apertura:
        flags.append(FlagC3('HIGH', 2, f'raw={sc.venta_raw}g sin apertura'))

    # C3: ab sube sin apertura
    if ab_n > ab_d + TOL_SUBA_AB_LEVE and not apertura:
        flags.append(FlagC3('AB_UP', 3, f'ab {ab_d}->{ab_n} (+{ab_delta}g)'))

    # C4: cerradas sin match (broadcast — cada cerrada DIA se compara con TODAS las de NOCHE)
    # Esto replica la semantica vieja: una cerrada NOCHE puede "servir" a multiples DIA.
    # La observacion tiene greedy match (mas preciso) para analisis posterior.
    all_slots_dia = [s for s, _, _ in obs.cerradas_matched_30] + list(obs.cerradas_unmatched_dia)
    all_slots_noche = [s for _, s, _ in obs.cerradas_matched_30] + list(obs.cerradas_unmatched_noche)
    all_pesos_dia = [s.peso for s in all_slots_dia]
    all_pesos_noche = [s.peso for s in all_slots_noche]

    for slot in all_slots_dia:
        if not any(abs(slot.peso - pn) <= TOL_MATCH_CERRADA for pn in all_pesos_noche):
            flags.append(FlagC3(f'C4d:{slot.peso}', 4, f'cerr DIA {slot.peso} sin match en NOCHE'))

    for slot in all_slots_noche:
        if not any(abs(slot.peso - pd) <= TOL_MATCH_CERRADA for pd in all_pesos_dia):
            # Es una proximidad entrante-cerrada? -> no flaggear (es promocion)
            es_promo = any(sn.indice_slot == slot.indice_slot
                           for _, sn, _ in obs.proximidades_entrante_cerrada)
            if es_promo:
                continue
            flags.append(FlagC3(f'C4n:{slot.peso}', 4, f'cerr NOCHE {slot.peso} sin match en DIA'))

    # Extra: mas cerradas en NOCHE (descontar promociones)
    n_promo = sum(1 for _, sn, _ in obs.proximidades_entrante_cerrada
                  if any(sn.indice_slot == un.indice_slot for un in obs.cerradas_unmatched_noche))
    n_cerr_b_eff = sc.n_cerr_b - n_promo
    if n_cerr_b_eff > sc.n_cerr_a:
        flags.append(FlagC3(f'CERR+{n_cerr_b_eff - sc.n_cerr_a}N', 4,
                            f'{n_cerr_b_eff} cerr NOCHE (eff) vs {sc.n_cerr_a} DIA'))

    # Clasificar
    if apertura and not flags:
        return StatusC3.ENGINE, flags

    if not flags:
        return StatusC3.LIMPIO, flags

    # ENGINE: apertura con flags que son esperables (C4d de cerradas que se abrieron)
    if apertura:
        flags_no_c4d = [f for f in flags if not f.codigo.startswith('C4d:')]
        if not flags_no_c4d:
            return StatusC3.ENGINE, flags

    # Contar tipos de condicion
    condiciones = set(f.condicion for f in flags)
    if len(condiciones) >= 2:
        return StatusC3.COMPUESTO, flags
    else:
        return StatusC3.SENAL, flags


# ═══════════════════════════════════════════════════════════════
# PF8 — Nombres inconsistentes (pre-proceso)
# ═══════════════════════════════════════════════════════════════

# Alias conocidos que el parser no normaliza
_ALIAS_RUNTIME = {
    'KIYKAT': 'KITKAT',
    'KIT KAT': 'KITKAT',
    'TIRAMIZU': 'TIRAMISU',  # backup por si parser no lo normaliza
}


def canonicalizar_nombres(datos: DatosDia) -> 'CanonicalizacionResult':
    """
    Analiza nombres sin mutar datos. Detecta colisiones.
    Retorna CanonicalizacionResult con aliases a aplicar y colisiones encontradas.
    """
    from .modelos import CanonicalizacionResult
    result = CanonicalizacionResult()

    for turno in [datos.turno_dia, datos.turno_noche] + datos.contexto:
        for norm in list(turno.sabores.keys()):
            if norm in _ALIAS_RUNTIME:
                new_name = _ALIAS_RUNTIME[norm]
                if new_name in turno.sabores and new_name != norm:
                    # COLISION: ambos nombres existen en el mismo turno
                    result.colisiones.append((norm, new_name, turno.nombre_hoja))
                elif (norm, new_name) not in result.aliases_aplicados:
                    result.aliases_aplicados.append((norm, new_name))
                    result.sabores_normalizados[norm] = new_name

    return result


def aplicar_canonicalizacion(datos: DatosDia, canon: 'CanonicalizacionResult') -> List[str]:
    """
    Aplica renames. Retorna warnings. Si hay colision para un nombre, NO lo renombra.
    """
    warnings = []
    nombres_con_colision = set(old for old, new, _ in canon.colisiones)

    for turno in [datos.turno_dia, datos.turno_noche] + datos.contexto:
        renames = {}
        for norm in list(turno.sabores.keys()):
            if norm in canon.sabores_normalizados and norm not in nombres_con_colision:
                renames[norm] = canon.sabores_normalizados[norm]
        for old, new in renames.items():
            if new not in turno.sabores:
                sabor = turno.sabores.pop(old)
                sabor.nombre_norm = new
                turno.sabores[new] = sabor

    for old, new, hoja in canon.colisiones:
        warnings.append(f'COLISION_IDENTIDAD: {old}->{new} en {hoja}')

    return warnings


def _aplicar_pf8(datos: DatosDia):
    """Legacy wrapper. Usa canonicalizacion segura internamente."""
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)


# ═══════════════════════════════════════════════════════════════
# HELPERS — Timeline y sightings para prototipos
# ═══════════════════════════════════════════════════════════════

def _todos_los_turnos(datos: DatosDia) -> List[TurnoCrudo]:
    """Retorna todos los turnos ordenados: contexto previo + DIA + NOCHE + contexto posterior."""
    pre = [t for t in datos.contexto if t.indice < datos.turno_dia.indice]
    post = [t for t in datos.contexto if t.indice > datos.turno_noche.indice]
    return sorted(pre, key=lambda t: t.indice) + [datos.turno_dia, datos.turno_noche] + sorted(post, key=lambda t: t.indice)


def _count_sightings_cerr(peso: int, nombre: str, datos: DatosDia, tol: int = TOL_MATCH_CERRADA) -> int:
    """Cuenta en cuántos turnos aparece una cerrada con peso similar."""
    count = 0
    for t in _todos_los_turnos(datos):
        s = t.sabores.get(nombre)
        if s and any(abs(peso - c) <= tol for c in s.cerradas):
            count += 1
    return count


def _peso_historico_cerr(peso: int, nombre: str, datos: DatosDia, tol: int = TOL_MATCH_CERRADA) -> Tuple[int, float]:
    """Busca el peso más frecuente de un can en el historial. Retorna (peso_ref, varianza)."""
    pesos = []
    for t in _todos_los_turnos(datos):
        s = t.sabores.get(nombre)
        if s:
            for c in s.cerradas:
                if abs(peso - c) <= tol:
                    pesos.append(c)
    if not pesos:
        return peso, 0.0
    avg = sum(pesos) / len(pesos)
    var = (sum((p - avg) ** 2 for p in pesos) / len(pesos)) ** 0.5 if len(pesos) > 1 else 0.0
    # Retornar la mediana como referencia
    pesos_sorted = sorted(pesos)
    ref = pesos_sorted[len(pesos_sorted) // 2]
    return ref, var


# ═══════════════════════════════════════════════════════════════
# OBSERVAR — unico punto de contacto con datos crudos del turno
# Produce metricas puras. No emite juicios.
# ═══════════════════════════════════════════════════════════════

def _observar(nombre: str, sc: SaborContable, datos: DatosDia) -> ObservacionC3:
    """
    Extrae metricas y correspondencias brutas.
    Este es el UNICO lugar que toca datos crudos del turno para un sabor.
    Colecciones salen en orden determinista (sorted por peso, luego indice).
    """
    obs = ObservacionC3(nombre_norm=nombre)

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)

    if not d and not n:
        return obs
    if d and not n:
        obs.ab_d = d.abierta if d.abierta is not None else None
        return obs
    if n and not d:
        obs.ab_n = n.abierta if n.abierta is not None else None
        return obs

    # --- Abierta ---
    obs.ab_d = d.abierta if d.abierta is not None else None
    obs.ab_n = n.abierta if n.abierta is not None else None
    if obs.ab_d is not None and obs.ab_n is not None:
        obs.ab_delta = obs.ab_n - obs.ab_d

    # --- Cerradas: matching via funcion unica ---
    from .matching import match_cerradas
    cerr_a_list = [int(c) for c in d.cerradas]
    cerr_b_list = [int(c) for c in n.cerradas]
    mr = match_cerradas(cerr_a_list, cerr_b_list)

    slots_dia = [SlotCerrada(peso=cerr_a_list[i], turno='DIA', indice_slot=i)
                 for i in range(len(cerr_a_list))]
    slots_noche = [SlotCerrada(peso=cerr_b_list[i], turno='NOCHE', indice_slot=i)
                   for i in range(len(cerr_b_list))]

    for ia, ib, pa, pb, diff in mr.matched:
        obs.cerradas_matched_30.append((slots_dia[ia], slots_noche[ib], diff))
    for ia in mr.unmatched_a:
        obs.cerradas_unmatched_dia.append(slots_dia[ia])
    for ib in mr.unmatched_b:
        obs.cerradas_unmatched_noche.append(slots_noche[ib])

    # --- Nearest: para cada unmatched, el slot mas cercano del otro turno ---
    for sd in obs.cerradas_unmatched_dia:
        best_sn = None
        best_diff = 999999
        for sn in slots_noche:
            diff = abs(sd.peso - sn.peso)
            if diff < best_diff:
                best_diff = diff
                best_sn = sn
        if best_sn is not None:
            obs.nearest_por_slot_dia.append((sd, best_sn, best_diff))
            # Mismatch leve?
            if TOL_MATCH_CERRADA < best_diff <= TOL_MISMATCH_LEVE:
                obs.mismatches_leves_dia.append((sd, best_sn, best_diff))

    for sn in obs.cerradas_unmatched_noche:
        best_sd = None
        best_diff = 999999
        for sd in slots_dia:
            diff = abs(sn.peso - sd.peso)
            if diff < best_diff:
                best_diff = diff
                best_sd = sd
        if best_sd is not None:
            obs.nearest_por_slot_noche.append((sn, best_sd, best_diff))
            if TOL_MATCH_CERRADA < best_diff <= TOL_MISMATCH_LEVE:
                obs.mismatches_leves_noche.append((sn, best_sd, best_diff))

    # --- Proximidades entrante-cerrada (nombre neutro) ---
    noche_matched_indices = set(mr.unmatched_b)  # invertido: queremos los NO matcheados
    # Corrección: indices matcheados son los que NO están en unmatched_b
    noche_matched_indices = set(ib for _, ib, _, _, _ in mr.matched)
    for i, ea in enumerate(d.entrantes):
        slot_ea = SlotEntrante(peso=int(ea), turno='DIA', indice_slot=i)
        for sn in slots_noche:
            if sn.indice_slot in noche_matched_indices:
                continue  # ya matcheada con cerrada DIA
            diff = abs(ea - sn.peso)
            if diff <= TOL_PROMO_ENTRANTE:
                obs.proximidades_entrante_cerrada.append((slot_ea, sn, diff))

    # --- Contexto temporal: forward/backward abierta ---
    post = sorted([t for t in datos.contexto if t.indice > datos.turno_noche.indice],
                  key=lambda t: t.indice)
    for t in post:
        s = t.sabores.get(nombre)
        if s and s.abierta is not None:
            obs.forward_ab = s.abierta
            obs.forward_turno = t.nombre_hoja
            break

    pre = sorted([t for t in datos.contexto if t.indice < datos.turno_dia.indice],
                 key=lambda t: t.indice, reverse=True)
    for t in pre:
        s = t.sabores.get(nombre)
        if s and s.abierta is not None:
            obs.backward_ab = s.abierta
            obs.backward_turno = t.nombre_hoja
            break

    # --- Sightings y varianza para cerradas unmatched (lazy: solo las que importan) ---
    todos = _todos_los_turnos(datos)
    n_turnos_total = len(todos)
    for slot in obs.cerradas_unmatched_dia + obs.cerradas_unmatched_noche:
        if slot.peso in obs.sightings:
            continue
        count = 0
        pesos_hist = []
        for t in todos:
            s = t.sabores.get(nombre)
            if s:
                for c in s.cerradas:
                    if abs(slot.peso - c) <= TOL_MATCH_CERRADA:
                        count += 1
                        pesos_hist.append(c)
                        break
        obs.sightings[slot.peso] = (count, n_turnos_total)
        if pesos_hist:
            pesos_sorted = sorted(pesos_hist)
            mediana = pesos_sorted[len(pesos_sorted) // 2]
            avg = sum(pesos_hist) / len(pesos_hist)
            stddev = (sum((p - avg) ** 2 for p in pesos_hist) / max(len(pesos_hist) - 1, 1)) ** 0.5
            obs.varianza_historica[slot.peso] = (mediana, stddev, len(pesos_hist))
        else:
            obs.varianza_historica[slot.peso] = (slot.peso, 0.0, 0)

    # Totales contables (espejo de sc, para guardias de coherencia en arbitro)
    obs.total_a = sc.total_a
    obs.total_b = sc.total_b
    obs.venta_raw = sc.venta_raw

    return obs


# ═══════════════════════════════════════════════════════════════
# NOTA: Los prototipos legacy (_intentar_pf1 a _intentar_pf7 + _intentar_prototipos)
# fueron eliminados en la auditoria sistémica v3.0.2.
# El pipeline usa generadores_c3.py + arbitro_c3.py desde la reforma constitucional.
# Referencia historica: commit v3.0.0 (792c244).
# ═══════════════════════════════════════════════════════════════


# (legacy PFs eliminados — ver nota arriba)


# ═══════════════════════════════════════════════════════════════
# MARCAS DE CALIDAD
# ═══════════════════════════════════════════════════════════════

def _evaluar_calidad(nombre: str, datos: DatosDia) -> List[MarcaCalidad]:
    """Evalua marcas de calidad sobre la abierta usando adyacencia fisica real."""
    marcas = []
    turnos = _todos_los_turnos(datos)

    # Pares (indice_turno, abierta) — NO secuencia comprimida
    ab_pairs = []
    for t in turnos:
        s = t.sabores.get(nombre)
        if s and s.abierta is not None:
            ab_pairs.append((t.indice, s.abierta))

    if len(ab_pairs) >= 3:
        # Buscar 3+ FISICAMENTE adyacentes con abierta identica
        for i in range(len(ab_pairs) - 2):
            idx_a, ab_a = ab_pairs[i]
            idx_b, ab_b = ab_pairs[i + 1]
            idx_c, ab_c = ab_pairs[i + 2]
            # Adyacencia fisica: indices consecutivos (diff=1)
            if (idx_b - idx_a == 1) and (idx_c - idx_b == 1) and ab_a == ab_b == ab_c:
                marcas.append(MarcaCalidad(
                    tipo='COPIA_POSIBLE_FUERTE',
                    detalle=f'ab={ab_a}g identica en >=3 turnos adyacentes (idx {idx_a}-{idx_c})',
                    penalizacion=CALIDAD_PENALIZACION_COPIA_FUERTE,
                ))
                break

    if not marcas and len(ab_pairs) >= 2:
        # 2 FISICAMENTE adyacentes con abierta identica
        for i in range(len(ab_pairs) - 1):
            idx_a, ab_a = ab_pairs[i]
            idx_b, ab_b = ab_pairs[i + 1]
            if (idx_b - idx_a == 1) and ab_a == ab_b and ab_a > 0:
                marcas.append(MarcaCalidad(
                    tipo='COPIA_POSIBLE_LEVE',
                    detalle=f'ab={ab_a}g identica en 2 turnos adyacentes (idx {idx_a}-{idx_b})',
                    penalizacion=0.0,
                ))
                break

    if not marcas:
        marcas.append(MarcaCalidad(tipo='DATO_NORMAL'))

    return marcas


# ═══════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def clasificar(datos: DatosDia, contabilidad: ContabilidadDia) -> ResultadoC3:
    """
    Capa 3: clasifica todos los sabores del día.
    1. PF8 nombres
    2. Screening C1-C5
    3. Prototipos PF1-PF7 para sospechosos
    4. Marcas de calidad
    Retorna ResultadoC3 con status y flags por sabor.
    """
    # PF8 ya se aplico en pipeline antes de Capa 2.
    # clasificar() NO muta nombres.

    resultado = ResultadoC3(dia_label=datos.dia_label)

    for nombre, sc in contabilidad.sabores.items():
        # Fase 1: Observar (unico punto de contacto con datos crudos)
        obs = _observar(nombre, sc, datos)

        # Fase 2: Screening (lee desde observacion, no desde datos crudos)
        status, flags = _screening(nombre, sc, obs)

        clasificado = SaborClasificado(
            nombre_norm=nombre,
            contable=sc,
            status=status,
            flags=flags,
            observacion=obs,
        )

        # Marcas de calidad para todos los sabores con ambos turnos
        if status not in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
            clasificado.marcas = _evaluar_calidad(nombre, datos)

        # Fase 3: Decidir
        if status in (StatusC3.LIMPIO, StatusC3.ENGINE):
            clasificado.venta_final_c3 = sc.venta_raw
            clasificado.decision = DecisionC3(
                resolucion=ResolucionC3.RAW_VALIDO,
                motivo_codigo=MotivoDecisionC3.SCREENING_LIMPIO if status == StatusC3.LIMPIO else MotivoDecisionC3.SCREENING_ENGINE,
            )
            clasificado.screening_status = status
            clasificado.resolution_status = ResolucionC3.RAW_VALIDO

        elif status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
            clasificado.venta_final_c3 = None  # NO_CALCULABLE: None, no 0
            clasificado.decision = DecisionC3(
                resolucion=ResolucionC3.NO_CALCULABLE,
                motivo_codigo=MotivoDecisionC3.SOLO_UN_TURNO,
            )
            clasificado.screening_status = status
            clasificado.resolution_status = ResolucionC3.NO_CALCULABLE

        elif status in (StatusC3.SENAL, StatusC3.COMPUESTO):
            # Nuevo pipeline: generar hipotesis + arbitrar
            from .generadores_c3 import generar_todas_hipotesis
            from .arbitro_c3 import resolver_hipotesis
            hipotesis = generar_todas_hipotesis(nombre, sc, datos, obs, flags)
            decision = resolver_hipotesis(hipotesis, obs, clasificado.marcas)
            clasificado.decision = decision
            clasificado.screening_status = status
            clasificado.resolution_status = decision.resolucion

            if decision.hipotesis_ganadora and decision.resolucion in (
                ResolucionC3.CORREGIDO_C3, ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA
            ):
                h = decision.hipotesis_ganadora
                # Bridge backward-compatible: construir PrototipoAplicado desde hipotesis
                clasificado.prototipo = PrototipoAplicado(
                    codigo=h.codigo_pf,
                    descripcion=h.descripcion,
                    confianza=h.confianza,
                    delta=h.delta_venta,
                    venta_corregida=h.venta_propuesta,
                )
                clasificado.venta_final_c3 = h.venta_propuesta

        resultado.sabores[nombre] = clasificado

    return resultado
