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
    PF1_OFFSETS, PF1_MIN_SIGHTINGS_STRONG, PF1_MIN_SIGHTINGS_WEAK,
    PF1_MAX_VAR_WEAK, PF1_CONF_STRONG, PF1_CONF_WEAK,
    PF2_CONF, PF3_CONF, PF3_MAX_SIGHTINGS_PHANTOM,
    PF4_MIN_SIGHTINGS, PF4_MIN_SIGHTINGS_NO_FORWARD, PF4_CONF, PF4_CONF_WEAK,
    PF5_MIN_SIGHTINGS, PF5_MIN_SIGHTINGS_NO_BACKWARD, PF5_CONF, PF5_CONF_WEAK,
    PF6_CONF, PF6_RISE_COHERENCE_RATIO, PF6_RISE_MAX_DIFF_RATIO,
    PF7_CONF_FORWARD, PF7_CONF_BACKWARD_ONLY, PF7_BACKWARD_TOLERANCE,
    APERTURA_PROXY_MIN_RISE,
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

        for offset in PF1_OFFSETS:
            peso_corregido = peso + offset
            sightings = _count_sightings_cerr(peso_corregido, nombre, datos)
            if sightings < PF1_MIN_SIGHTINGS_WEAK:
                continue

            ref, var = _peso_historico_cerr(peso_corregido, nombre, datos)
            if var > PF1_MAX_VAR_WEAK and sightings < PF1_MIN_SIGHTINGS_STRONG:
                continue

            conf = PF1_CONF_STRONG if sightings >= PF1_MIN_SIGHTINGS_STRONG else PF1_CONF_WEAK
            if es_dia:
                delta = offset
            else:
                delta = -offset

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
# COLECTOR
# ===================================================================

_GENERADORES = [
    generar_hipotesis_pf1,
    generar_hipotesis_pf2,
    generar_hipotesis_pf3,
    generar_hipotesis_pf7,  # PF7 antes de PF4/PF5
    generar_hipotesis_pf4,
    generar_hipotesis_pf5,
    generar_hipotesis_pf6,
]


def generar_todas_hipotesis(nombre: str, sc: SaborContable, datos: DatosDia,
                            obs: ObservacionC3, flags: List[FlagC3]) -> List[HipotesisCorreccion]:
    """Colecta todas las hipotesis de todos los PFs."""
    todas = []
    for gen_fn in _GENERADORES:
        todas.extend(gen_fn(nombre, sc, datos, obs, flags))
    return todas
