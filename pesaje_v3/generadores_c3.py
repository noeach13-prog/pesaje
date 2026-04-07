"""
generadores_c3.py -- PFs como generadores puros de hipotesis.

Cada funcion devuelve List[HipotesisCorreccion].
No emiten veredictos. Solo presentan expedientes al arbitro.
"""
from typing import List
from .modelos import (
    SaborContable, DatosDia, ObservacionC3, FlagC3,
    HipotesisCorreccion, TargetCorreccion, FuenteEvidencia,
    LadoError, CampoAfectado, OperacionCorreccion, MecanismoCausal, TipoFuente,
    SlotCerrada, SlotEntrante,
)
from .constantes_c3 import (
    TOL_MATCH_CERRADA, TOL_MATCH_ENTRANTE, TOL_PROMO_ENTRANTE, TOL_MISMATCH_LEVE,
    TOL_SUBA_AB_LEVE, TARA_LATA, VENTA_NEG_THRESHOLD,
    PF1_OFFSETS, PF1_OFFSETS_CENTENA_ALTA, PF1_MIN_SIGHTINGS_CENTENA_ALTA,
    PF1_MIN_SIGHTINGS_STRONG, PF1_MIN_SIGHTINGS_WEAK,
    PF1_MAX_VAR_WEAK, PF1_CONF_STRONG, PF1_CONF_WEAK,
    PF2_CONF, PF3_CONF, PF3_MAX_SIGHTINGS_PHANTOM,
    PF4_MIN_SIGHTINGS, PF4_MIN_SIGHTINGS_NO_FORWARD, PF4_CONF, PF4_CONF_WEAK,
    PF5_MIN_SIGHTINGS, PF5_MIN_SIGHTINGS_NO_BACKWARD, PF5_CONF, PF5_CONF_WEAK,
    PF6_CONF, PF6_RISE_COHERENCE_RATIO, PF6_RISE_MAX_DIFF_RATIO,
    PF7_CONF_FORWARD, PF7_CONF_BACKWARD_ONLY, PF7_BACKWARD_TOLERANCE,
    APERTURA_PROXY_MIN_RISE,
    PFIT_TOL_INTRA, PFIT_TOL_CONTEXTO, PFIT_CONF_FUERTE, PFIT_CONF_MEDIA, PFIT_CONF_AMBIGU,
    TOL_MATCH_CERRADA,
)


def _get_sightings(obs: ObservacionC3, peso: int):
    """Lee sightings de la observacion. Retorna (count, n_total)."""
    return obs.sightings.get(peso, (0, 0))


def _get_varianza(obs: ObservacionC3, peso: int):
    """Lee varianza de la observacion. Retorna (mediana, stddev, n)."""
    return obs.varianza_historica.get(peso, (peso, 0.0, 0))


# ===================================================================
# PF1: Error de digito en cerrada
# ===================================================================

def _recalcular_delta_pf1(nombre: str, datos, peso_original: int,
                           peso_corregido: int, es_dia: bool) -> int:
    """
    Recalcula el delta de venta al corregir una cerrada de peso_original a peso_corregido.

    En vez de asumir delta=offset, reconstruye la contabilidad del sabor con
    el peso corregido y calcula la diferencia real. Esto es necesario en
    TURNO_UNICO donde corregir una cerrada DIA puede cambiar new_cerr_b
    (la cerrada NOCHE que antes no matcheaba, ahora sí matchea).

    En DIA_NOCHE new_cerr_b siempre es 0, así que el resultado coincide
    con el shortcut delta=offset.
    """
    from .capa2_contrato import _matching_entrantes, _new_cerradas_b

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return peso_corregido - peso_original if es_dia else -(peso_corregido - peso_original)

    modo = getattr(datos, 'modo', 'DIA_NOCHE')

    # Construir listas de cerradas con la corrección aplicada
    def _aplicar(cerradas, p_orig, p_corr):
        result = []
        reemplazado = False
        for c in cerradas:
            if int(c) == p_orig and not reemplazado:
                result.append(p_corr)
                reemplazado = True
            else:
                result.append(int(c))
        return result

    if es_dia:
        cerr_dia_corr = _aplicar(d.cerradas, peso_original, peso_corregido)
        cerr_noche = [int(c) for c in n.cerradas]
    else:
        cerr_dia_corr = [int(c) for c in d.cerradas]
        cerr_noche = _aplicar(n.cerradas, peso_original, peso_corregido)

    # Contabilidad original
    cerr_dia_orig = [int(c) for c in d.cerradas]
    cerr_noche_orig = [int(c) for c in n.cerradas]
    ent_dia = [int(e) for e in d.entrantes]
    ent_noche = [int(e) for e in n.entrantes]

    total_a_orig = (d.abierta or 0) + (d.celiaca or 0) + sum(cerr_dia_orig) + sum(ent_dia)
    total_b = (n.abierta or 0) + (n.celiaca or 0) + sum(cerr_noche_orig) + sum(ent_noche)
    new_ent_b_orig = _matching_entrantes(ent_dia, ent_noche)
    new_cerr_b_orig = _new_cerradas_b(cerr_dia_orig, cerr_noche_orig) if modo == 'TURNO_UNICO' else 0
    venta_orig = total_a_orig + new_ent_b_orig + new_cerr_b_orig - total_b

    # Contabilidad corregida
    total_a_corr = (d.abierta or 0) + (d.celiaca or 0) + sum(cerr_dia_corr) + sum(ent_dia)
    total_b_corr = (n.abierta or 0) + (n.celiaca or 0) + sum(cerr_noche) + sum(ent_noche)
    new_cerr_b_corr = _new_cerradas_b(cerr_dia_corr, cerr_noche) if modo == 'TURNO_UNICO' else 0
    venta_corr = total_a_corr + new_ent_b_orig + new_cerr_b_corr - total_b_corr

    return venta_corr - venta_orig


def generar_hipotesis_pf1(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    """Devuelve TODAS las hipotesis para cada offset valido, no solo la primera."""
    from .capa3_motor import _count_sightings_cerr, _peso_historico_cerr

    hipotesis = []
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return hipotesis

    for flag in flags:
        if not flag.codigo.startswith('C4d:') and not flag.codigo.startswith('C4n:'):
            continue

        peso = int(flag.codigo.split(':')[1])
        es_dia = flag.codigo.startswith('C4d:')
        lado = LadoError.DIA if es_dia else LadoError.NOCHE

        # Encontrar el slot correspondiente
        cerradas_turno = d.cerradas if es_dia else n.cerradas
        indice = next((i for i, c in enumerate(cerradas_turno) if int(c) == peso), 0)

        # Si el peso original tiene identidad establecida en el historial, no es error de digito.
        # Un typo ocurre 1-2 veces; una lata real aparece 3+ veces.
        sightings_original = _count_sightings_cerr(peso, nombre, datos)
        if sightings_original >= PF1_MIN_SIGHTINGS_WEAK:
            continue

        all_offsets = list(PF1_OFFSETS) + list(PF1_OFFSETS_CENTENA_ALTA)
        for offset in all_offsets:
            peso_corregido = peso + offset
            sightings = _count_sightings_cerr(peso_corregido, nombre, datos)

            # Offsets de centena alta requieren mas sightings
            is_centena_alta = offset in PF1_OFFSETS_CENTENA_ALTA or -offset in PF1_OFFSETS_CENTENA_ALTA
            min_sightings = PF1_MIN_SIGHTINGS_CENTENA_ALTA if is_centena_alta else PF1_MIN_SIGHTINGS_WEAK
            if sightings < min_sightings:
                continue

            ref, var = _peso_historico_cerr(peso_corregido, nombre, datos)
            if var > PF1_MAX_VAR_WEAK and sightings < PF1_MIN_SIGHTINGS_STRONG:
                continue

            conf = PF1_CONF_STRONG if sightings >= PF1_MIN_SIGHTINGS_STRONG else PF1_CONF_WEAK

            # Delta: recalcular contabilidad completa con el peso corregido.
            # En TURNO_UNICO, corregir una cerrada DIA puede cambiar el matching
            # contra NOCHE (new_cerr_b), haciendo que delta != offset.
            # En DIA_NOCHE, el shortcut delta=offset sigue siendo correcto
            # porque new_cerr_b siempre es 0.
            delta = _recalcular_delta_pf1(
                nombre, datos, peso, peso_corregido, es_dia,
            )

            slot = SlotCerrada(peso=peso, turno=lado.value, indice_slot=indice)
            fuente = FuenteEvidencia(TipoFuente.SIGHTINGS,
                                     f'{sightings} sightings de {peso_corregido}, var={var:.0f}g')

            hipotesis.append(HipotesisCorreccion(
                codigo_pf='PF1',
                target=TargetCorreccion(
                    lado=lado, campo=CampoAfectado.CERRADA,
                    operacion=OperacionCorreccion.SUSTITUIR,
                    slot_cerrada=slot, peso_propuesto=peso_corregido,
                ),
                delta_venta=delta,
                venta_propuesta=sc.venta_raw + delta,
                confianza=conf,
                mecanismo_causal=MecanismoCausal.ERROR_DIGITO,
                fuente_decision=fuente,
                fuente_correccion=fuente,
                evidencias=[f'offset={offset}, sightings={sightings}, var={var:.0f}g'],
                descripcion=f'Error digito cerr {lado.value} {peso}->{peso_corregido} ({sightings} sightings, var={var:.0f}g)',
            ))

    return hipotesis


# ===================================================================
# PF2: Entrante duplicado
# ===================================================================

def generar_hipotesis_pf2(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n or not d.entrantes or not n.entrantes:
        return []
    if sc.venta_raw < 0:
        return []

    hipotesis = []
    for ea_idx, ea in enumerate(d.entrantes):
        for eb_idx, eb in enumerate(n.entrantes):
            if abs(ea - eb) > TOL_MATCH_ENTRANTE:
                continue
            cerr_nueva = [cn for cn in n.cerradas
                          if abs(cn - ea) <= TOL_MATCH_ENTRANTE
                          and not any(abs(cn - cd) <= TOL_MISMATCH_LEVE for cd in d.cerradas)
                          and not any(abs(cn - ed) <= TOL_PROMO_ENTRANTE for ed in d.entrantes)]
            if cerr_nueva:
                slot = SlotEntrante(peso=int(eb), turno='NOCHE', indice_slot=eb_idx)
                fuente = FuenteEvidencia(TipoFuente.MATCHING,
                                         f'ent DIA {int(ea)} persiste en NOCHE, cerr nueva {int(cerr_nueva[0])}')
                hipotesis.append(HipotesisCorreccion(
                    codigo_pf='PF2',
                    target=TargetCorreccion(
                        lado=LadoError.NOCHE, campo=CampoAfectado.ENTRANTE,
                        operacion=OperacionCorreccion.ELIMINAR,
                        slot_entrante=slot,
                    ),
                    delta_venta=int(eb),
                    venta_propuesta=sc.venta_raw + int(eb),
                    confianza=PF2_CONF,
                    mecanismo_causal=MecanismoCausal.PROMO_DUP,
                    fuente_decision=fuente,
                    fuente_correccion=fuente,
                    evidencias=[f'ent DIA {int(ea)}->cerr NOCHE {int(cerr_nueva[0])}, ent NOCHE {int(eb)} es residuo'],
                    descripcion=f'Entrante dup {int(ea)}->cerr {int(cerr_nueva[0])}, ent NOCHE {int(eb)} es residuo',
                ))
                return hipotesis  # solo 1 match por sabor
    return hipotesis


# ===================================================================
# PF3: Phantom RM-3
# ===================================================================

def generar_hipotesis_pf3(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    from .capa3_motor import _count_sightings_cerr

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return []

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    if ab_n <= ab_d + TOL_SUBA_AB_LEVE:
        return []

    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= TOL_MATCH_CERRADA for cn in n.cerradas)]
    if len(cerr_gone) <= 1:
        return []

    rise = ab_n - ab_d
    mejor_fuente = None
    mejor_diff = 99999
    for c in cerr_gone:
        diff = abs(rise - (c - TARA_LATA))
        if diff < mejor_diff:
            mejor_diff = diff
            mejor_fuente = c

    phantoms = [c for c in cerr_gone if c != mejor_fuente]
    hipotesis = []
    for phantom in phantoms:
        sightings = _count_sightings_cerr(phantom, nombre, datos)
        if sightings <= PF3_MAX_SIGHTINGS_PHANTOM:
            delta = -phantom
            if sc.n_cerr_a > sc.n_cerr_b:
                delta += TARA_LATA
            indice = next((i for i, c in enumerate(d.cerradas) if int(c) == phantom), 0)
            slot = SlotCerrada(peso=phantom, turno='DIA', indice_slot=indice)
            fuente = FuenteEvidencia(TipoFuente.MATCHING,
                                     f'rise={rise}g, apertura real={int(mejor_fuente)}, phantom sightings={sightings}')
            hipotesis.append(HipotesisCorreccion(
                codigo_pf='PF3',
                target=TargetCorreccion(
                    lado=LadoError.DIA, campo=CampoAfectado.CERRADA,
                    operacion=OperacionCorreccion.ELIMINAR,
                    slot_cerrada=slot,
                ),
                delta_venta=delta,
                venta_propuesta=sc.venta_raw + delta,
                confianza=PF3_CONF,
                mecanismo_causal=MecanismoCausal.APERTURA_PHANTOM,
                fuente_decision=fuente,
                fuente_correccion=fuente,
                evidencias=[f'phantom sightings={sightings}, apertura real={int(mejor_fuente)}'],
                descripcion=f'Phantom RM-3: cerr {int(phantom)} (sightings={sightings}), apertura real={int(mejor_fuente)}',
            ))
            return hipotesis  # solo el primer phantom viable
    return hipotesis


# ===================================================================
# PF4: Cerrada omitida en NOCHE
# ===================================================================

def generar_hipotesis_pf4(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    from .capa3_motor import _count_sightings_cerr, _peso_historico_cerr

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return []

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    if ab_n > ab_d + TOL_SUBA_AB_LEVE:
        return []

    cerr_missing = [c for c in d.cerradas
                    if not any(abs(c - cn) <= TOL_MISMATCH_LEVE for cn in n.cerradas)]
    if not cerr_missing:
        return []

    hipotesis = []
    for cerr in cerr_missing:
        sightings = _count_sightings_cerr(cerr, nombre, datos)
        if sightings < PF4_MIN_SIGHTINGS:
            continue

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
        indice = next((i for i, c in enumerate(d.cerradas) if int(c) == int(cerr)), 0)

        evidencias = [f'sightings={sightings}']
        if forward_ok:
            evidencias.append('forward: si')
            fuente = FuenteEvidencia(TipoFuente.FORWARD, f'sightings={sightings}, forward=si')
        else:
            evidencias.append('forward: no (sightings suficientes)')
            fuente = FuenteEvidencia(TipoFuente.SIGHTINGS, f'sightings={sightings}, forward=no')

        hipotesis.append(HipotesisCorreccion(
            codigo_pf='PF4',
            target=TargetCorreccion(
                lado=LadoError.NOCHE, campo=CampoAfectado.CERRADA,
                operacion=OperacionCorreccion.AGREGAR,
                peso_propuesto=ref,
            ),
            delta_venta=-ref,
            venta_propuesta=sc.venta_raw - ref,
            confianza=conf,
            mecanismo_causal=MecanismoCausal.OMISION,
            fuente_decision=fuente,
            fuente_correccion=fuente,
            evidencias=evidencias,
            descripcion=f'Cerr {int(cerr)} omitida en NOCHE (sightings={sightings}, forward={"si" if forward_ok else "no"})',
        ))
        return hipotesis  # solo la primera cerrada viable
    return hipotesis


# ===================================================================
# PF5: Cerrada omitida en DIA
# ===================================================================

def generar_hipotesis_pf5(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    from .capa3_motor import _count_sightings_cerr, _peso_historico_cerr

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return []
    if sc.venta_raw > VENTA_NEG_THRESHOLD:
        return []

    cerr_missing = []
    for c in n.cerradas:
        if any(abs(c - cd) <= TOL_MISMATCH_LEVE for cd in d.cerradas):
            continue
        if any(abs(c - ea) <= TOL_PROMO_ENTRANTE for ea in d.entrantes):
            continue
        cerr_missing.append(c)
    if not cerr_missing:
        return []

    hipotesis = []
    for cerr in cerr_missing:
        sightings = _count_sightings_cerr(cerr, nombre, datos)
        if sightings < PF5_MIN_SIGHTINGS:
            continue

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

        evidencias = [f'sightings={sightings}']
        if backward_ok:
            evidencias.append('backward: si')
            fuente = FuenteEvidencia(TipoFuente.BACKWARD, f'sightings={sightings}, backward=si')
        else:
            evidencias.append('backward: no (sightings suficientes)')
            fuente = FuenteEvidencia(TipoFuente.SIGHTINGS, f'sightings={sightings}, backward=no')

        hipotesis.append(HipotesisCorreccion(
            codigo_pf='PF5',
            target=TargetCorreccion(
                lado=LadoError.DIA, campo=CampoAfectado.CERRADA,
                operacion=OperacionCorreccion.AGREGAR,
                peso_propuesto=ref,
            ),
            delta_venta=ref,
            venta_propuesta=sc.venta_raw + ref,
            confianza=conf,
            mecanismo_causal=MecanismoCausal.OMISION,
            fuente_decision=fuente,
            fuente_correccion=fuente,
            evidencias=evidencias,
            descripcion=f'Cerr {int(cerr)} omitida en DIA (sightings={sightings}, backward={"si" if backward_ok else "no"})',
        ))
        return hipotesis
    return hipotesis


# ===================================================================
# PF6: Apertura + phantom combinado
# ===================================================================

def generar_hipotesis_pf6(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    from .capa3_motor import _count_sightings_cerr

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return []

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    rise = ab_n - ab_d
    if rise <= 0:
        return []

    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= TOL_MATCH_CERRADA for cn in n.cerradas)]
    if len(cerr_gone) < 2:
        return []

    total_rise_all = sum(c - TARA_LATA for c in cerr_gone)
    if rise >= total_rise_all * PF6_RISE_COHERENCE_RATIO:
        return []

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
        return []

    phantom, real_aperturas = best_combo
    sightings = _count_sightings_cerr(phantom, nombre, datos)
    if sightings > PF3_MAX_SIGHTINGS_PHANTOM:
        return []

    delta = -phantom
    if sc.n_cerr_a > sc.n_cerr_b:
        delta += TARA_LATA

    indice = next((i for i, c in enumerate(d.cerradas) if int(c) == phantom), 0)
    slot = SlotCerrada(peso=phantom, turno='DIA', indice_slot=indice)
    fuente = FuenteEvidencia(TipoFuente.MATCHING,
                             f'rise={rise}g, {len(real_aperturas)} apertura(s) reales, phantom sightings={sightings}')

    return [HipotesisCorreccion(
        codigo_pf='PF6',
        target=TargetCorreccion(
            lado=LadoError.DIA, campo=CampoAfectado.CERRADA,
            operacion=OperacionCorreccion.ELIMINAR,
            slot_cerrada=slot,
        ),
        delta_venta=delta,
        venta_propuesta=sc.venta_raw + delta,
        confianza=PF6_CONF,
        mecanismo_causal=MecanismoCausal.APERTURA_PHANTOM,
        fuente_decision=fuente,
        fuente_correccion=fuente,
        evidencias=[f'phantom sightings={sightings}, rise coherente con {len(real_aperturas)} apertura(s)'],
        descripcion=f'Apertura+phantom: cerr {int(phantom)} phantom (sightings={sightings}), '
                    f'rise {rise}g coherente con {len(real_aperturas)} apertura(s)',
    )]


# ===================================================================
# PF7: Abierta imposible
# ===================================================================

def generar_hipotesis_pf7(nombre: str, sc: SaborContable, datos: DatosDia,
                          obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return []

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0

    if not any(f.codigo == 'AB_UP' for f in flags):
        return []

    # Verificar cerradas intactas usando el matching formal de la observacion,
    # NO con any() que permite doble-match al mismo slot
    if obs.cerradas_unmatched_dia or obs.cerradas_unmatched_noche:
        return []  # Hay cerradas sin match → no es AB_IMP, es otro patron
    if sc.new_ent_b > 0:
        return []

    # Leer forward/backward de la observacion (ya calculado)
    ab_forward = obs.forward_ab
    ab_backward = obs.backward_ab

    if ab_forward is not None:
        if abs(ab_n - ab_forward) < abs(ab_d - ab_forward):
            # DIA es el error. Forward decide, forward corrige.
            ref = ab_forward  # NO usar backward para corregir cuando forward decidio
            # Pero el delta real es (ref_correccion - ab_d) donde ref_correccion
            # deberia ser backward o ab_n si backward no existe
            # CORRECCION: misma fuente decide y corrige
            # Si forward dice "DIA esta mal", usamos backward como valor corregido
            # SOLO SI reconciliacion explicita. Sin backward, usamos ab_n.
            if ab_backward is not None:
                ref_corr = ab_backward
                fuente_dec = FuenteEvidencia(TipoFuente.FORWARD, f'ab_forward={ab_forward}')
                fuente_cor = FuenteEvidencia(TipoFuente.BACKWARD, f'ab_backward={ab_backward}')
                reconciliacion = True
                motivo_rec = 'Forward identifica lado erroneo, backward provee valor de correccion'
            else:
                ref_corr = ab_n
                fuente_dec = FuenteEvidencia(TipoFuente.FORWARD, f'ab_forward={ab_forward}')
                fuente_cor = FuenteEvidencia(TipoFuente.FORWARD, f'ab_forward={ab_forward}, ab_n={ab_n} como proxy')
                reconciliacion = False
                motivo_rec = ''

            delta = ref_corr - ab_d
            return [HipotesisCorreccion(
                codigo_pf='PF7',
                target=TargetCorreccion(
                    lado=LadoError.DIA, campo=CampoAfectado.ABIERTA,
                    operacion=OperacionCorreccion.SUSTITUIR,
                    peso_propuesto=ref_corr,
                ),
                delta_venta=delta,
                venta_propuesta=sc.venta_raw + delta,
                confianza=PF7_CONF_FORWARD,
                mecanismo_causal=MecanismoCausal.AB_IMP,
                fuente_decision=fuente_dec,
                fuente_correccion=fuente_cor,
                reconciliacion_explicita=reconciliacion,
                motivo_reconciliacion=motivo_rec,
                evidencias=[f'forward={ab_forward}, backward={ab_backward}'],
                descripcion=f'AB_IMP DIA: ab {ab_d}->{ref_corr} (forward={ab_forward})',
            )]
        else:
            # NOCHE es el error. Forward decide Y corrige.
            ref = ab_forward
            delta = -(ref - ab_n)
            fuente = FuenteEvidencia(TipoFuente.FORWARD, f'ab_forward={ab_forward}')
            return [HipotesisCorreccion(
                codigo_pf='PF7',
                target=TargetCorreccion(
                    lado=LadoError.NOCHE, campo=CampoAfectado.ABIERTA,
                    operacion=OperacionCorreccion.SUSTITUIR,
                    peso_propuesto=ref,
                ),
                delta_venta=delta,
                venta_propuesta=sc.venta_raw + delta,
                confianza=PF7_CONF_FORWARD,
                mecanismo_causal=MecanismoCausal.AB_IMP,
                fuente_decision=fuente,
                fuente_correccion=fuente,
                evidencias=[f'forward={ab_forward}'],
                descripcion=f'AB_IMP NOCHE: ab {ab_n}->{ref} (forward={ab_forward})',
            )]

    elif ab_backward is not None:
        if abs(ab_d - ab_backward) <= PF7_BACKWARD_TOLERANCE:
            # DIA ok, NOCHE es el error. Backward decide Y corrige.
            ref = ab_d
            delta = -(ab_n - ab_d)
            fuente = FuenteEvidencia(TipoFuente.BACKWARD, f'ab_backward={ab_backward}')
            return [HipotesisCorreccion(
                codigo_pf='PF7',
                target=TargetCorreccion(
                    lado=LadoError.NOCHE, campo=CampoAfectado.ABIERTA,
                    operacion=OperacionCorreccion.SUSTITUIR,
                    peso_propuesto=ref,
                ),
                delta_venta=delta,
                venta_propuesta=sc.venta_raw + delta,
                confianza=PF7_CONF_BACKWARD_ONLY,
                mecanismo_causal=MecanismoCausal.AB_IMP,
                fuente_decision=fuente,
                fuente_correccion=fuente,
                evidencias=[f'backward={ab_backward}, solo backward'],
                descripcion=f'AB_IMP NOCHE: ab {ab_n}->~{ab_d} (backward={ab_backward}, solo backward)',
            )]

    return []


# ===================================================================
# PFIT: Entrante duplicado intra-turno
# ===================================================================
#
# Fenómeno: en la misma planilla (turno_DIA), el mismo can físico aparece
# registrado DOS veces: una en la columna de cerradas y otra en la de entrantes.
# Resultado: total_A inflado en ~peso_entrante → venta_raw inflada en el mismo monto.
#
# Distinción semántica obligatoria:
#   PF2 (PROMO_DUP): entrante DIA se TRANSFORMA en cerrada NOCHE (genealogía cross-turno)
#   PFIT (ENTRANTE_MISMO_CAN): cerrada DIA y entrante DIA son el mismo can (doble registro, mismo turno)
#
# Jerarquía de confianza:
#   FUERTE (0.88): match intra-turno ±100g + cerrada ya existía en turno PREVIO ±200g
#   MEDIA  (0.72): match intra-turno + cerrada persiste en turno SIGUIENTE ±200g, previo ambiguo
#   DÉBIL:  solo match intra-turno, sin soporte temporal → no genera hipótesis
#           EXCEPCIÓN: turno_masivo=True eleva DÉBIL a MEDIA (ver INTRADUP_MASIVO_TURNO)
#
# PFIT_MASIVO (N>=2 pares, bajo turno_masivo):
#   Cuando el sabor tiene N>=2 pares (entrante~cerrada) mutuamente no conflictivos,
#   se genera UNA hipótesis compuesta en lugar de N individuales.
#   Condición de no-conflicto: la asignación par↔par es forzada (biyectiva en slots Y en pesos).
#   Si dos entrantes son intercambiables con dos cerradas (pesos cruzados en tolerancia),
#   la asignación es ambigua → no se compone → se cae al comportamiento individual.
#   Confianza = min(confianzas individuales). No se premia la cantidad.
#
# Corrección: ELIMINAR el entrante de DIA. No tocar la cerrada (la cerrada es la identidad real).
# delta_venta = -entrante_peso  (total_A baja → venta_raw baja)
#
# Tests doctrinales (PFIT individual):
#   [+] Positivo: ent=6700, cerr=6720 mismo turno, cerr=6700 en previo → FUERTE
#   [-] Negativo: ent=6700, cerr=6720 mismo turno, cerr NO en previo ni siguiente → DÉBIL → sin hipótesis
#   [~] Borde: ent=6700, cerr=6720 mismo turno, cerr en siguiente pero NO en previo → MEDIA, conf=0.72
#
# Tests doctrinales (PFIT_MASIVO):
#   [+] Positivo: CH AMORES D14 — 2 PFIT individuales → 1 PFIT_MASIVO, delta acumulado
#   [-] Negativo masivo: pares ambiguos (pesos cruzados) → no compone, cae a individual
#   [!] Coherencia: delta acumulado > raw → venta_propuesta absurda → árbitro rechaza
#   [-] San Martín D5/D6: masivo=False → no aparece PFIT_MASIVO


def _pares_no_conflictivos(pares: List[tuple]) -> bool:
    """
    Verifica que los pares (ea_idx, ea, cerrada_match, c_idx) sean mutuamente no conflictivos.

    Condición doble:
    1. Biyectividad de slots: ningún slot de entrante ni de cerrada aparece más de una vez.
    2. No cruce de pesos: para cada par (e_i, c_i), ningún otro par (e_j, c_j) tiene
       |e_i - c_j| <= PFIT_TOL_INTRA (el entrante de i no puede reclamar la cerrada de j).

    Si cualquiera falla → asignación ambigua → no se compone.
    """
    if len(pares) < 2:
        return True

    # 1. Biyectividad de slots
    ent_slots = [p[0] for p in pares]
    cerr_slots = [p[3] for p in pares]
    if len(ent_slots) != len(set(ent_slots)):
        return False
    if len(cerr_slots) != len(set(cerr_slots)):
        return False

    # 2. No cruce de pesos: e_i no puede matchear c_j (para i != j)
    for i, (_, ei, ci, ci_idx) in enumerate(pares):
        for j, (_, ej, cj, cj_idx) in enumerate(pares):
            if i == j:
                continue
            if abs(ei - cj) <= PFIT_TOL_INTRA:
                return False  # e_i intercambiable con c_j → asignación ambigua

    return True


def _slots_biyectivos(pares: List[tuple]) -> bool:
    """
    Verifica solo la biyectividad de slots (sin chequear cruce de pesos).
    Precondición de PFIT_MASIVO_AMBIGU: N entrantes distintos → N cerradas distintas.
    pares: [(ea_idx, ea, c_val, c_idx), ...]
    """
    ent_slots = [p[0] for p in pares]
    cerr_slots = [p[3] for p in pares]
    return (len(ent_slots) == len(set(ent_slots)) and
            len(cerr_slots) == len(set(cerr_slots)))


def _cerradas_persisten_en_noche(pares: List[tuple], n) -> bool:
    """
    Condición 4 (PFIT_MASIVO_AMBIGU): cada cerrada DIA emparejada también aparece
    en NOCHE (dentro de TOL_MATCH_CERRADA = 30g).

    Usa TOL_MATCH_CERRADA (no PFIT_TOL_INTRA) porque la pregunta es de identidad
    física del mismo can, no de rango de emparejamiento entrante↔cerrada.
    Un can que pesa 5450 en DIA y está ausente de NOCHE no es el mismo que el
    de 5400 aunque ambos estén dentro de 100g.

    Si una cerrada desaparece entre DIA y NOCHE podría haberse abierto o
    transformado — el monto ya no es inequívoco.
    pares: [(ea_idx, ea, c_val, c_idx), ...]
    """
    if not n or not n.cerradas:
        return False
    for ea_idx, ea, c_val, c_idx in pares:
        if not any(abs(c_val - int(cn)) <= TOL_MATCH_CERRADA for cn in n.cerradas):
            return False
    return True


def _sin_rival_apertura_o_genealogia(pares: List[tuple], n) -> bool:
    """
    Condición 5 (PFIT_MASIVO_AMBIGU): ninguna cerrada emparejada está siendo
    reclamada por una hipótesis rival fuerte.

    Señal de rival: la cerrada DIA ~ algún entrante NOCHE (candidato PF2,
    promoción legítima de entrante→cerrada). Si hay rival, la masa puede
    estar participando en una genealogía real y el monto deja de ser inequívoco.
    pares: [(ea_idx, ea, c_val, c_idx), ...]
    """
    if not n:
        return True
    for ea_idx, ea, c_val, c_idx in pares:
        if n.entrantes and any(abs(c_val - int(en)) <= PFIT_TOL_INTRA for en in n.entrantes):
            return False  # rival de genealogía detectado
    return True


def _generar_pfit_masivo_ambigu(nombre: str, sc: SaborContable,
                                 pares: list) -> List[HipotesisCorreccion]:
    """
    Genera UNA hipótesis PFIT_MASIVO_AMBIGU cuando:
    - Los slots son biyectivos (N entrantes distintos → N cerradas distintas).
    - Pero los pesos se cruzan entre pares (asignación fina ambigua).
    - Todas las cerradas emparejadas persisten en NOCHE (cond. 4).
    - Sin rival de apertura/genealogía sobre esas masas (cond. 5).
    - turno_masivo = True.

    El monto total a eliminar es inequívoco:
    toda asignación bijéctiva posible produce el mismo delta = -sum(entrantes).
    La ambigüedad es de relato (¿cuál entrante duplica a cuál cerrada?),
    no de monto (¿cuánto sobra en total?).

    Confianza: PFIT_CONF_AMBIGU (0.65) → CORREGIDO_C3_BAJA_CONFIANZA.
    pares: [(ea_idx, ea_int, c_val, c_idx, conf, fuente_tipo, bw, fw), ...]
    """
    delta_total = -sum(p[1] for p in pares)
    venta_propuesta = sc.venta_raw + delta_total

    primer_slot = SlotEntrante(peso=pares[0][1], turno='DIA', indice_slot=pares[0][0])

    fuente = FuenteEvidencia(
        TipoFuente.MATCHING,
        f'PFIT_MASIVO_AMBIGU: {len(pares)} entrantes emparejables con cerradas DIA; '
        f'asignación bijéctiva ambigua (cruce de pesos) pero monto total '
        f'={delta_total:+d}g inequívoco; cerradas persisten en NOCHE; '
        f'sin rival; INTRADUP_MASIVO_TURNO confirmado',
    )

    evidencias = [
        f'PFIT_MASIVO_AMBIGU: {len(pares)} pares, delta acumulado={delta_total:+d}g',
        'slots biyectivos pero pesos cruzados entre pares (asignación fina ambigua)',
        'monto inequívoco: toda asignación bijéctiva posible produce el mismo delta',
        'cerradas emparejadas persisten en NOCHE (descartada apertura o transformación)',
        'sin rival de genealogía ni apertura sobre esas masas (cond. 5 ok)',
        'INTRADUP_MASIVO_TURNO: patrón colectivo de doble-registro en planilla',
    ]
    pares_desc = '; '.join(f'ent {p[1]}g~cerr {p[2]}g' for p in pares)

    return [HipotesisCorreccion(
        codigo_pf='PFIT_MASIVO_AMBIGU',
        target=TargetCorreccion(
            lado=LadoError.DIA,
            campo=CampoAfectado.ENTRANTE,
            operacion=OperacionCorreccion.ELIMINAR,
            slot_entrante=primer_slot,
        ),
        delta_venta=delta_total,
        venta_propuesta=venta_propuesta,
        confianza=PFIT_CONF_AMBIGU,
        mecanismo_causal=MecanismoCausal.ENTRANTE_MISMO_CAN,
        fuente_decision=fuente,
        fuente_correccion=fuente,
        evidencias=evidencias,
        descripcion=(
            f'Doble registro compuesto (asignación ambigua): {len(pares)} entrantes '
            f'({pares_desc}); '
            f'monto inequívoco={delta_total:+d}g bajo INTRADUP_MASIVO_TURNO'
        ),
    )]


def _evaluar_par_temporal(cerrada_match: int, nombre: str,
                          pre: list, post: list) -> tuple:
    """
    Evalúa soporte temporal para un par (entrante, cerrada).
    Retorna (conf, fuente_tipo, backward_ok, forward_ok).
    """
    backward_ok = any(
        s and any(abs(cerrada_match - int(c)) <= PFIT_TOL_CONTEXTO for c in s.cerradas)
        for t in pre
        for s in [t.sabores.get(nombre)]
    )
    forward_ok = any(
        s and any(abs(cerrada_match - int(c)) <= PFIT_TOL_CONTEXTO for c in s.cerradas)
        for t in post
        for s in [t.sabores.get(nombre)]
    )
    if backward_ok:
        return PFIT_CONF_FUERTE, TipoFuente.BACKWARD, True, False
    elif forward_ok:
        return PFIT_CONF_MEDIA, TipoFuente.FORWARD, False, True
    else:
        return None, None, False, False  # DÉBIL


def generar_hipotesis_pfit(nombre: str, sc: SaborContable, datos: DatosDia,
                           obs: ObservacionC3, flags: List[FlagC3],
                           turno_masivo: bool = False) -> List[HipotesisCorreccion]:
    """
    Detecta doble registro intra-turno: mismo can registrado como cerrada Y entrante
    en la MISMA planilla (mismo turno).

    Cuando turno_masivo=True y hay N>=2 pares mutuamente no conflictivos,
    genera UNA hipótesis compuesta PFIT_MASIVO en lugar de N individuales.
    Ver _pares_no_conflictivos() para la definición de no-conflicto.
    """
    d = datos.turno_dia.sabores.get(nombre)
    if not d or not d.entrantes or not d.cerradas:
        return []
    if sc.venta_raw < 0:
        return []

    pre = sorted([t for t in datos.contexto if t.indice < datos.turno_dia.indice],
                 key=lambda t: t.indice, reverse=True)
    post = sorted([t for t in datos.contexto if t.indice > datos.turno_noche.indice],
                  key=lambda t: t.indice)

    # --- Paso 1: recolectar todos los pares (entrante, cerrada) con su soporte temporal ---
    # Matching: asignación greedy por distancia mínima con slots reclamados.
    # Garantiza biyectividad de slots siempre que el matching sea posible
    # (cada entrante toma la cerrada más cercana aún no reclamada).
    # Par: (ea_idx, ea_int, cerrada_match, c_idx, conf, fuente_tipo, backward_ok, forward_ok)
    pares_completos = []
    cerradas_list = [(i, int(c)) for i, c in enumerate(d.cerradas)]
    cerradas_usadas: set = set()

    for ea_idx, ea in enumerate(d.entrantes):
        ea_int = int(ea)
        # Candidatas: cerradas no usadas dentro de PFIT_TOL_INTRA
        candidatas = [
            (c_idx, c_val, abs(ea_int - c_val))
            for c_idx, c_val in cerradas_list
            if c_idx not in cerradas_usadas and abs(ea_int - c_val) <= PFIT_TOL_INTRA
        ]
        if not candidatas:
            continue
        # Tomar la más cercana (menor distancia)
        c_idx, c_val, _ = min(candidatas, key=lambda x: x[2])
        cerradas_usadas.add(c_idx)
        conf, fuente_tipo, bw, fw = _evaluar_par_temporal(c_val, nombre, pre, post)
        pares_completos.append((ea_idx, ea_int, c_val, c_idx, conf, fuente_tipo, bw, fw))

    if not pares_completos:
        return []

    # --- Paso 2: determinar ruta —————————————————————————————————————————————————
    # Prioridad:
    #   A) PFIT_MASIVO       — pares no conflictivos (slots biyectivos + pesos no cruzados)
    #   B) PFIT_MASIVO_AMBIGU — slots biyectivos, pesos cruzados, cerradas persisten, sin rival
    #   C) PFIT individual   — cualquier otro caso (N=1 o condiciones AMBIGU no cumplidas)
    pares_para_conflicto = [(p[0], p[1], p[2], p[3]) for p in pares_completos]
    n_sab = datos.turno_noche.sabores.get(nombre)

    if turno_masivo and len(pares_completos) >= 2:
        if _pares_no_conflictivos(pares_para_conflicto):
            # A) Hipótesis compuesta: asignación inequívoca
            return _generar_pfit_masivo(nombre, sc, pares_completos, turno_masivo)
        elif (_slots_biyectivos(pares_para_conflicto)
              and _cerradas_persisten_en_noche(pares_para_conflicto, n_sab)
              and _sin_rival_apertura_o_genealogia(pares_para_conflicto, n_sab)):
            # B) Hipótesis compuesta: asignación ambigua pero monto inequívoco
            return _generar_pfit_masivo_ambigu(nombre, sc, pares_completos)

    # C) Comportamiento individual (con elevación DÉBIL→MEDIA si masivo)
    return _generar_pfit_individuales(nombre, sc, pares_completos, turno_masivo)


def _generar_pfit_masivo(nombre: str, sc: SaborContable,
                         pares: list, turno_masivo: bool) -> List[HipotesisCorreccion]:
    """
    Genera una hipótesis compuesta PFIT_MASIVO que elimina todos los entrantes duplicados
    de una sola vez. Solo se llama cuando los pares son mutuamente no conflictivos.
    Confianza = min(conf_individual). Conservador: no se premia la cantidad.
    """
    # Determinar confianzas individuales (incluyendo elevación masivo para DÉBIL)
    confs = []
    for ea_idx, ea, cm, c_idx, conf, fuente_tipo, bw, fw in pares:
        if conf is not None:
            confs.append(conf)
        elif turno_masivo:
            confs.append(PFIT_CONF_MEDIA)  # DÉBIL elevado
        # Si conf is None y no masivo: no debería llegar aquí (filtrado antes)

    if not confs:
        return []

    conf_compuesta = min(confs)
    delta_total = -sum(p[1] for p in pares)  # suma de todos los entrantes eliminados
    venta_propuesta = sc.venta_raw + delta_total

    # Slot representativo: el primero (para arbitraje de clave_agrupamiento)
    primer_slot = SlotEntrante(peso=pares[0][1], turno='DIA', indice_slot=pares[0][0])

    # Fuente: MATCHING colectivo (la asignación conjunta es la evidencia)
    fuente = FuenteEvidencia(
        TipoFuente.MATCHING,
        f'PFIT_MASIVO: {len(pares)} pares entrante~cerrada mutuamente no conflictivos; '
        f'INTRADUP_MASIVO_TURNO confirmado',
    )

    evidencias = [f'PFIT_MASIVO: {len(pares)} pares no conflictivos, delta acumulado={delta_total:+d}g']
    for ea_idx, ea, cm, c_idx, conf, fuente_tipo, bw, fw in pares:
        soporte = 'backward' if bw else ('forward' if fw else 'masivo')
        conf_ind = conf if conf is not None else PFIT_CONF_MEDIA
        evidencias.append(f'  par: ent {ea}g ~ cerr {cm}g ({soporte}, conf={conf_ind:.2f})')

    pares_desc = '; '.join(f'ent {p[1]}g~cerr {p[2]}g' for p in pares)

    return [HipotesisCorreccion(
        codigo_pf='PFIT_MASIVO',
        target=TargetCorreccion(
            lado=LadoError.DIA,
            campo=CampoAfectado.ENTRANTE,
            operacion=OperacionCorreccion.ELIMINAR,
            slot_entrante=primer_slot,
        ),
        delta_venta=delta_total,
        venta_propuesta=venta_propuesta,
        confianza=conf_compuesta,
        mecanismo_causal=MecanismoCausal.ENTRANTE_MISMO_CAN,
        fuente_decision=fuente,
        fuente_correccion=fuente,
        evidencias=evidencias,
        descripcion=(
            f'Doble registro compuesto: {len(pares)} entrantes duplicados '
            f'({pares_desc}); PFIT_MASIVO bajo patrón colectivo de turno'
        ),
    )]


def _generar_pfit_individuales(nombre: str, sc: SaborContable,
                               pares: list, turno_masivo: bool) -> List[HipotesisCorreccion]:
    """
    Genera hipótesis PFIT individuales (comportamiento original).
    Para N=1, o cuando los pares son conflictivos (no biyectivos o pesos cruzados).
    """
    hipotesis = []

    for ea_idx, ea, cerrada_match, c_idx, conf, fuente_tipo, backward_ok, forward_ok in pares:
        elevado_por_masivo = False

        if conf == PFIT_CONF_FUERTE:
            fuente = FuenteEvidencia(
                TipoFuente.BACKWARD,
                f'cerr {cerrada_match} confirmada en turno previo; ent {ea} ~ cerr {cerrada_match} mismo turno',
            )
            evidencias = [
                f'ent DIA {ea} ~ cerr DIA {cerrada_match} (±{PFIT_TOL_INTRA}g)',
                'cerrada confirmada en turno previo (backward)',
            ]

        elif conf == PFIT_CONF_MEDIA:
            fuente = FuenteEvidencia(
                TipoFuente.FORWARD,
                f'cerr {cerrada_match} persiste en turno siguiente; ent {ea} ~ cerr {cerrada_match} mismo turno',
            )
            evidencias = [
                f'ent DIA {ea} ~ cerr DIA {cerrada_match} (±{PFIT_TOL_INTRA}g)',
                'cerrada persiste en turno siguiente (forward), previo ambiguo',
            ]

        elif turno_masivo:
            # DÉBIL elevado a MEDIA por patrón colectivo
            conf = PFIT_CONF_MEDIA
            fuente = FuenteEvidencia(
                TipoFuente.MATCHING,
                f'ent {ea} ~ cerr {cerrada_match} mismo turno; sin soporte temporal individual; '
                f'ELEVADO_POR_INTRADUP_MASIVO_TURNO',
            )
            evidencias = [
                f'ent DIA {ea} ~ cerr DIA {cerrada_match} (±{PFIT_TOL_INTRA}g)',
                'sin backward ni forward individual',
                'ELEVADO_POR_INTRADUP_MASIVO_TURNO: patron colectivo de doble-registro en planilla',
            ]
            elevado_por_masivo = True

        else:
            continue  # DÉBIL sin masivo → descartar

        slot = SlotEntrante(peso=ea, turno='DIA', indice_slot=ea_idx)
        desc_suffix = '; PFIT reforzado por patrón colectivo de turno' if elevado_por_masivo else ''

        hipotesis.append(HipotesisCorreccion(
            codigo_pf='PFIT',
            target=TargetCorreccion(
                lado=LadoError.DIA,
                campo=CampoAfectado.ENTRANTE,
                operacion=OperacionCorreccion.ELIMINAR,
                slot_entrante=slot,
            ),
            delta_venta=-ea,
            venta_propuesta=sc.venta_raw - ea,
            confianza=conf,
            mecanismo_causal=MecanismoCausal.ENTRANTE_MISMO_CAN,
            fuente_decision=fuente,
            fuente_correccion=fuente,
            evidencias=evidencias,
            descripcion=(
                f'Doble registro: ent DIA {ea}g ~ cerr DIA {cerrada_match}g; '
                f'{"backward" if backward_ok else ("forward" if forward_ok else "masivo")} '
                f'confirma cerrada como identidad real{desc_suffix}'
            ),
        ))

    return hipotesis


# ===================================================================
# COLECTOR
# ===================================================================

_GENERADORES = [
    generar_hipotesis_pfit,  # antes que el resto: detecta doble registro intra-turno
    generar_hipotesis_pf1,
    generar_hipotesis_pf2,
    generar_hipotesis_pf3,
    generar_hipotesis_pf7,  # PF7 antes de PF4/PF5
    generar_hipotesis_pf4,
    generar_hipotesis_pf5,
    generar_hipotesis_pf6,
]


def generar_todas_hipotesis(nombre: str, sc: SaborContable, datos: DatosDia,
                            obs: ObservacionC3, flags: List[FlagC3],
                            turno_masivo: bool = False) -> List[HipotesisCorreccion]:
    """Colecta todas las hipotesis de todos los PFs.

    turno_masivo: si True, PFIT puede elevar señales DÉBIL a MEDIA por contexto colectivo.
    """
    todas = []
    for gen_fn in _GENERADORES:
        if gen_fn is generar_hipotesis_pfit:
            todas.extend(gen_fn(nombre, sc, datos, obs, flags, turno_masivo=turno_masivo))
        else:
            todas.extend(gen_fn(nombre, sc, datos, obs, flags))
    return todas
