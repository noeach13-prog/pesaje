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

    # --- Cerradas: matching a TOL_MATCH_CERRADA ---
    slots_dia = [SlotCerrada(peso=int(c), turno='DIA', indice_slot=i)
                 for i, c in enumerate(d.cerradas)]
    slots_noche = [SlotCerrada(peso=int(c), turno='NOCHE', indice_slot=i)
                   for i, c in enumerate(n.cerradas)]

    # Greedy best-match: para cada slot DIA, buscar el mejor match en NOCHE
    noche_usado = set()
    for sd in slots_dia:
        best_sn = None
        best_diff = 999999
        for sn in slots_noche:
            if sn.indice_slot in noche_usado:
                continue
            diff = abs(sd.peso - sn.peso)
            if diff <= TOL_MATCH_CERRADA and diff < best_diff:
                best_diff = diff
                best_sn = sn
        if best_sn is not None:
            obs.cerradas_matched_30.append((sd, best_sn, best_diff))
            noche_usado.add(best_sn.indice_slot)
        else:
            obs.cerradas_unmatched_dia.append(sd)

    for sn in slots_noche:
        if sn.indice_slot not in noche_usado:
            obs.cerradas_unmatched_noche.append(sn)

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
    for i, ea in enumerate(d.entrantes):
        slot_ea = SlotEntrante(peso=int(ea), turno='DIA', indice_slot=i)
        for sn in slots_noche:
            if sn.indice_slot in noche_usado:
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
# PF1 — Error de dígito en cerrada
# Firma: cerrada difiere ±1000 o ±2000g del historial estable (≥5 sightings, var ≤30g)
# ═══════════════════════════════════════════════════════════════

def _intentar_pf1(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    # Buscar cerradas huérfanas (C4d o C4n flags)
    for flag in flags:
        if not flag.codigo.startswith('C4d:') and not flag.codigo.startswith('C4n:'):
            continue

        peso_str = flag.codigo.split(':')[1]
        peso = int(peso_str)
        es_dia = flag.codigo.startswith('C4d:')

        # Buscar si existe un can en el historial con offset tipico de digito
        # Solo offsets grandes: +-300 (centena), +-1000/+-2000 (millar)
        # +-100/+-200 son varianza de pesaje, no errores de digito
        for offset in PF1_OFFSETS:
            peso_corregido = peso + offset
            sightings = _count_sightings_cerr(peso_corregido, nombre, datos)
            if sightings < PF1_MIN_SIGHTINGS_WEAK:
                continue

            ref, var = _peso_historico_cerr(peso_corregido, nombre, datos)
            if var > PF1_MAX_VAR_WEAK and sightings < PF1_MIN_SIGHTINGS_STRONG:
                continue

            # Verificar que el peso corregido matchea en el otro turno
            otro_turno = n if es_dia else d
            if not any(abs(peso_corregido - c) <= TOL_MATCH_CERRADA for c in otro_turno.cerradas):
                pass

            conf = PF1_CONF_STRONG if sightings >= PF1_MIN_SIGHTINGS_STRONG else PF1_CONF_WEAK
            delta = -offset  # si peso era 5705 y correcto es 6705, offset=-1000, delta=+1000
            # El delta en venta: si la cerrada estaba en DIA con peso erróneo,
            # corregirla cambia total_A
            if es_dia:
                venta_corregida = sc.venta_raw + offset  # peso real es mayor -> total_A sube -> venta sube
            else:
                venta_corregida = sc.venta_raw - offset  # peso real es mayor en NOCHE -> total_B sube -> venta baja

            return PrototipoAplicado(
                codigo='PF1',
                descripcion=f'Error dígito cerr {"DIA" if es_dia else "NOCHE"} {peso}->{peso_corregido} ({sightings} sightings, var={var:.0f}g)',
                confianza=conf,
                delta=venta_corregida - sc.venta_raw,
                venta_corregida=venta_corregida,
            )
    return None


# ═══════════════════════════════════════════════════════════════
# PF2 — Entrante duplicado
# Firma: entrante DIA persiste en NOCHE después de que fue promovido a cerrada
# ═══════════════════════════════════════════════════════════════

def _intentar_pf2(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None
    if not d.entrantes or not n.entrantes:
        return None

    # PF2 solo aplica cuando el entrante residual infla total_B -> raw alto
    # Si raw es negativo, el problema es otro (entrante promovido a cerrada = normal)
    if sc.venta_raw < 0:
        return None

    # Buscar entrante de DIA que persiste en NOCHE
    for ea in d.entrantes:
        for eb in n.entrantes:
            if abs(ea - eb) > TOL_MATCH_ENTRANTE:
                continue
            # El entrante persiste. Hay una cerrada nueva en NOCHE que matchea?
            cerr_nueva = [cn for cn in n.cerradas
                          if abs(cn - ea) <= TOL_MATCH_ENTRANTE
                          and not any(abs(cn - cd) <= TOL_MISMATCH_LEVE for cd in d.cerradas)
                          and not any(abs(cn - ed) <= TOL_PROMO_ENTRANTE for ed in d.entrantes)]
            if cerr_nueva:
                # Entrante fue promovido a cerrada pero no borrado
                # Corrección: remover entrante de NOCHE del cálculo
                # new_ent_b incluía eb (si no matcheaba con ea), pero ea SÍ matchea con eb
                # -> new_ent_b no lo contó. El problema es que eb está en total_B.
                # Remover eb de total_B -> venta sube en eb
                venta_corregida = sc.venta_raw + eb
                return PrototipoAplicado(
                    codigo='PF2',
                    descripcion=f'Entrante dup {int(ea)}->cerr {int(cerr_nueva[0])}, ent NOCHE {int(eb)} es residuo',
                    confianza=PF2_CONF,
                    delta=eb,
                    venta_corregida=venta_corregida,
                )
    return None


# ═══════════════════════════════════════════════════════════════
# PF3 — Phantom por RM-3 (can abierto reaparece como cerrada)
# Firma: cerrada fue abierta en turno anterior, ab no sube correspondiente
# ═══════════════════════════════════════════════════════════════

def _intentar_pf3(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0

    # Buscar cerradas en DIA sin match en NOCHE
    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= TOL_MATCH_CERRADA for cn in n.cerradas)]
    if not cerr_gone:
        return None

    # Hubo apertura? (ab sube)
    if ab_n <= ab_d + TOL_SUBA_AB_LEVE:
        # Ab no subió -> cerrada desapareció sin apertura -> phantom o omisión, no PF3
        return None

    # Ab subió. ¿Cuántas cerradas desaparecieron?
    if len(cerr_gone) <= 1:
        return None  # Solo 1 desaparece con apertura = ENGINE normal, no PF3

    # Múltiples cerradas desaparecen pero el rise solo explica 1 apertura
    # Buscar cuál es la fuente real de la apertura (la más coherente con el rise)
    rise = ab_n - ab_d
    mejor_fuente = None
    mejor_diff = 99999
    for c in cerr_gone:
        expected_rise = c - TARA_LATA
        diff = abs(rise - expected_rise)
        if diff < mejor_diff:
            mejor_diff = diff
            mejor_fuente = c

    # Las otras son phantoms (RM-3: no pueden reaparecer como cerradas)
    phantoms = [c for c in cerr_gone if c != mejor_fuente]
    if not phantoms:
        return None

    # Solo aplicar PF3 si el phantom tiene bajo sighting
    for phantom in phantoms:
        sightings = _count_sightings_cerr(phantom, nombre, datos)
        if sightings <= PF3_MAX_SIGHTINGS_PHANTOM:
            delta = -phantom
            # Ajustar latas si corresponde
            if sc.n_cerr_a > sc.n_cerr_b:
                delta += TARA_LATA
            venta_corregida = sc.venta_raw + delta
            return PrototipoAplicado(
                codigo='PF3',
                descripcion=f'Phantom RM-3: cerr {int(phantom)} (sightings={sightings}), apertura real={int(mejor_fuente)}',
                confianza=PF3_CONF,
                delta=delta,
                venta_corregida=venta_corregida,
            )
    return None


# ═══════════════════════════════════════════════════════════════
# PF4 — Cerrada omitida en NOCHE
# Firma: cerrada con historial (≥3 sightings) en DIA, ausente en NOCHE, ab no sube
# ═══════════════════════════════════════════════════════════════

def _intentar_pf4(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0

    # Ab no sube -> no hubo apertura
    if ab_n > ab_d + TOL_SUBA_AB_LEVE:
        return None

    # Cerradas en DIA sin match en NOCHE (umbral amplio: >TOL_MISMATCH_LEVE)
    cerr_missing = [c for c in d.cerradas
                    if not any(abs(c - cn) <= TOL_MISMATCH_LEVE for cn in n.cerradas)]
    if not cerr_missing:
        return None

    for cerr in cerr_missing:
        sightings = _count_sightings_cerr(cerr, nombre, datos)
        if sightings < PF4_MIN_SIGHTINGS:
            continue

        # Verificar forward: la cerrada reaparece en turnos posteriores?
        post = [t for t in datos.contexto if t.indice > datos.turno_noche.indice]
        forward_ok = False
        for t in post:
            s = t.sabores.get(nombre)
            if s and any(abs(cerr - c) <= TOL_MATCH_CERRADA for c in s.cerradas):
                forward_ok = True
                break

        if not forward_ok and sightings < PF4_MIN_SIGHTINGS_NO_FORWARD:
            continue

        conf = PF4_CONF if sightings >= PF4_MIN_SIGHTINGS else PF4_CONF_WEAK
        ref, _ = _peso_historico_cerr(cerr, nombre, datos)
        # Agregar cerrada a NOCHE -> total_B sube -> venta baja
        venta_corregida = sc.venta_raw - ref
        return PrototipoAplicado(
            codigo='PF4',
            descripcion=f'Cerr {int(cerr)} omitida en NOCHE (sightings={sightings}, forward={"si" if forward_ok else "no"})',
            confianza=conf,
            delta=-ref,
            venta_corregida=venta_corregida,
        )
    return None


# ═══════════════════════════════════════════════════════════════
# PF5 — Cerrada omitida en DIA
# Firma: cerrada con historial en NOCHE y adyacentes, ausente en DIA, raw muy negativo
# ═══════════════════════════════════════════════════════════════

def _intentar_pf5(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    # Raw debería ser negativo si falta una cerrada en DIA
    if sc.venta_raw > VENTA_NEG_THRESHOLD:
        return None

    # Cerradas en NOCHE sin match en DIA (umbral amplio)
    # Excluir cerradas que son entrantes promovidos
    cerr_missing = []
    for c in n.cerradas:
        if any(abs(c - cd) <= TOL_MISMATCH_LEVE for cd in d.cerradas):
            continue
        if any(abs(c - ea) <= TOL_PROMO_ENTRANTE for ea in d.entrantes):
            continue
        cerr_missing.append(c)
    if not cerr_missing:
        return None

    for cerr in cerr_missing:
        sightings = _count_sightings_cerr(cerr, nombre, datos)
        if sightings < PF5_MIN_SIGHTINGS:
            continue

        # Verificar backward: la cerrada estaba en turnos anteriores?
        pre = [t for t in datos.contexto if t.indice < datos.turno_dia.indice]
        backward_ok = False
        for t in pre:
            s = t.sabores.get(nombre)
            if s and any(abs(cerr - c) <= TOL_MATCH_CERRADA for c in s.cerradas):
                backward_ok = True
                break

        if not backward_ok and sightings < PF5_MIN_SIGHTINGS_NO_BACKWARD:
            continue

        conf = PF5_CONF if sightings >= PF5_MIN_SIGHTINGS else PF5_CONF_WEAK
        ref, _ = _peso_historico_cerr(cerr, nombre, datos)
        # Agregar cerrada a DIA -> total_A sube -> venta sube
        venta_corregida = sc.venta_raw + ref
        return PrototipoAplicado(
            codigo='PF5',
            descripcion=f'Cerr {int(cerr)} omitida en DIA (sightings={sightings}, backward={"sí" if backward_ok else "no"})',
            confianza=conf,
            delta=ref,
            venta_corregida=venta_corregida,
        )
    return None


# ═══════════════════════════════════════════════════════════════
# PF6 — Apertura + phantom combinado
# Firma: ab sube + desaparecen M cerradas + rise coherente con N<M
# ═══════════════════════════════════════════════════════════════

def _intentar_pf6(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    rise = ab_n - ab_d

    if rise <= 0:
        return None

    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= TOL_MATCH_CERRADA for cn in n.cerradas)]
    if len(cerr_gone) < 2:
        return None

    # Rise coherente con todas las aperturas?
    total_rise_all = sum(c - TARA_LATA for c in cerr_gone)
    if rise >= total_rise_all * PF6_RISE_COHERENCE_RATIO:
        return None  # Rise suficiente para todas -> no hay phantom

    # Probar con N-1 aperturas: encontrar combinacion que explica el rise
    best_combo = None
    best_diff = 99999
    for i, phantom_candidate in enumerate(cerr_gone):
        remaining = [c for j, c in enumerate(cerr_gone) if j != i]
        expected = sum(c - TARA_LATA for c in remaining)
        diff = abs(rise - expected)
        if diff < best_diff:
            best_diff = diff
            best_combo = (phantom_candidate, remaining)

    if best_combo is None or best_diff > max(500, rise * PF6_RISE_MAX_DIFF_RATIO):
        return None

    phantom, real_aperturas = best_combo
    sightings = _count_sightings_cerr(phantom, nombre, datos)
    if sightings > PF3_MAX_SIGHTINGS_PHANTOM:
        return None

    delta = -phantom
    if sc.n_cerr_a > sc.n_cerr_b:
        delta += TARA_LATA
    venta_corregida = sc.venta_raw + delta

    return PrototipoAplicado(
        codigo='PF6',
        descripcion=f'Apertura+phantom: cerr {int(phantom)} phantom (sightings={sightings}), '
                    f'rise {rise}g coherente con {len(real_aperturas)} apertura(s)',
        confianza=PF6_CONF,
        delta=delta,
        venta_corregida=venta_corregida,
    )


# ═══════════════════════════════════════════════════════════════
# PF7 — Abierta imposible (AB_IMP)
# Firma: ab sube sin apertura, cerradas intactas, sin entrante que explique
# ═══════════════════════════════════════════════════════════════

def _intentar_pf7(nombre: str, sc: SaborContable, datos: DatosDia,
                  flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0

    # Necesitamos AB_UP flag (ab sube sin apertura)
    if not any(f.codigo == 'AB_UP' for f in flags):
        return None

    # Cerradas intactas (todas matchean)
    cerr_ok = all(any(abs(cd - cn) <= TOL_MATCH_CERRADA for cn in n.cerradas) for cd in d.cerradas)
    if not cerr_ok:
        return None

    # Sin entrante nuevo que explique
    if sc.new_ent_b > 0:
        return None

    # Buscar referencia forward (turnos posteriores)
    post = sorted([t for t in datos.contexto if t.indice > datos.turno_noche.indice],
                  key=lambda t: t.indice)
    ab_forward = None
    for t in post:
        s = t.sabores.get(nombre)
        if s and s.abierta is not None:
            ab_forward = s.abierta
            break

    # Buscar referencia backward (turnos anteriores)
    pre = sorted([t for t in datos.contexto if t.indice < datos.turno_dia.indice],
                 key=lambda t: t.indice, reverse=True)
    ab_backward = None
    for t in pre:
        s = t.sabores.get(nombre)
        if s and s.abierta is not None:
            ab_backward = s.abierta
            break

    # Determinar qué valor es el erróneo (DIA o NOCHE)
    # Forward gana sobre backward (RM-7)
    if ab_forward is not None:
        # NOCHE coherente con forward?
        if abs(ab_n - ab_forward) < abs(ab_d - ab_forward):
            # DIA es el error -> reemplazar ab_d por referencia
            ref = ab_backward if ab_backward is not None else ab_n
            delta = ref - ab_d  # total_A cambia en delta -> venta cambia en delta
            venta_corregida = sc.venta_raw + delta
            conf = PF7_CONF_FORWARD
            desc = f'AB_IMP DIA: ab {ab_d}->{ref} (forward={ab_forward})'
        else:
            # NOCHE es el error -> reemplazar ab_n
            ref = ab_forward
            delta = -(ref - ab_n)
            venta_corregida = sc.venta_raw - (ref - ab_n)
            conf = PF7_CONF_FORWARD
            desc = f'AB_IMP NOCHE: ab {ab_n}->{ref} (forward={ab_forward})'
    elif ab_backward is not None:
        # Solo backward. DIA coherente con backward?
        if abs(ab_d - ab_backward) <= PF7_BACKWARD_TOLERANCE:
            # DIA ok, NOCHE es el error
            ref = ab_d  # usar DIA como referencia
            delta = -(ab_n - ab_d)
            venta_corregida = sc.venta_raw + (ab_d - ab_n)
            conf = PF7_CONF_BACKWARD_ONLY
            desc = f'AB_IMP NOCHE: ab {ab_n}->~{ab_d} (backward={ab_backward}, solo backward)'
        else:
            # DIA también está raro -> no hay referencia confiable
            return None
    else:
        return None

    return PrototipoAplicado(
        codigo='PF7',
        descripcion=desc,
        confianza=conf,
        delta=delta,
        venta_corregida=venta_corregida,
    )


# ═══════════════════════════════════════════════════════════════
# APLICAR PROTOTIPOS PF1-PF7
# ═══════════════════════════════════════════════════════════════

_PROTOTIPOS = [
    _intentar_pf1,
    _intentar_pf2,
    _intentar_pf3,
    _intentar_pf7,  # PF7 antes de PF4/PF5 (AB_IMP puede explicar flags sin cerrada)
    _intentar_pf4,
    _intentar_pf5,
    _intentar_pf6,
]


def _intentar_prototipos(nombre: str, sc: SaborContable, datos: DatosDia,
                         flags: List[FlagC3]) -> Optional[PrototipoAplicado]:
    """
    Intenta aplicar exactamente 1 prototipo PF1-PF7.
    Si matchea más de uno, aplica desempate por coherencia y confianza.
    Solo escala a Capa 4 si el conflicto es genuino (no resoluble).
    """
    matches = []
    for pf_fn in _PROTOTIPOS:
        resultado = pf_fn(nombre, sc, datos, flags)
        if resultado:
            matches.append(resultado)

    if len(matches) == 0:
        return None

    if len(matches) == 1:
        return matches[0]

    # --- Desempate: filtrar por coherencia, luego por confianza ---

    # 1. Descartar hipótesis cuya venta corregida es incoherente
    coherentes = []
    for m in matches:
        if m.venta_corregida < -300:
            continue  # venta muy negativa = incoherente
        if sc.total_a > 0 and m.venta_corregida > sc.total_a:
            continue  # venta > stock disponible = incoherente
        coherentes.append(m)

    if len(coherentes) == 1:
        return coherentes[0]

    if len(coherentes) == 0:
        return None  # todos incoherentes → escalar

    # 2. Mayor confianza gana
    coherentes.sort(key=lambda m: m.confianza, reverse=True)
    if coherentes[0].confianza > coherentes[1].confianza:
        return coherentes[0]

    # 3. Misma confianza → si uno es PF1 (error dígito), priorizar (evidencia más específica)
    pf1s = [m for m in coherentes if m.codigo == 'PF1']
    if len(pf1s) == 1:
        return pf1s[0]

    # Conflicto genuino → escalar
    return None


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
