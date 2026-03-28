"""
capa4_expediente.py — Motor multifactor de 4 planos.

Traducción directa del pseudocódigo (capa4_pseudocodigo.md).
Cada función corresponde a un PASO numerado.

Flujo:
  PASO 1: timeline
  PASO 2: 4 planos de evidencia (P1, P2, P3, P4)
  PASO 3: generar TODAS las hipótesis
  PASO 4: evaluar cada hipótesis contra todos los planos
  PASO 5: seleccionar la mejor (o combinación)
  PASO 6: asignar tipo/banda/confianza
  PASO 7: guardia de coherencia post-corrección
  ESPECIAL: ENGINE con phantom oculto
  ESPECIAL: análisis CONJUNTO cross-sabor
"""
from .modelos import (
    DatosDia, ContabilidadDia, ResultadoC3, SaborClasificado,
    StatusC3, FlagC3, Correccion,
    TipoJustificacion, Banda, TipoResolucion,
    SaborCrudo, TurnoCrudo,
)
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
# ESTRUCTURAS INTERNAS
# ═══════════════════════════════════════════════════════════════

@dataclass
class Snapshot:
    label: str
    ab: int
    cerradas: List[int]
    entrantes: List[int]
    total: int


@dataclass
class PlanoP1:
    clasificacion: str  # VENTA_PURA, ESTATICA, APERTURA_SOPORTADA, etc.
    ab_d: int
    ab_n: int
    delta_ab: int
    fuente: Optional[int] = None  # peso de la fuente de apertura


@dataclass
class PlanoP2:
    cerr_a: List[int]
    cerr_b: List[int]
    desaparecen: List[Tuple[int, int]]   # (peso, sightings) — en A no en B
    aparecen: List[Tuple[int, int]]      # (peso, sightings) — en B no en A
    persisten: List[Tuple[int, int, int, int]]  # (ca, cb, diff, sightings_a)
    sightings: Dict[int, int] = field(default_factory=dict)  # peso -> count


@dataclass
class PlanoP3:
    ent_a: List[int]
    ent_b: List[int]
    persisten: List[Tuple[int, int, int]]  # (ea, eb, diff)
    nuevos_b: List[int]
    gone_a: List[int]


@dataclass
class Hipotesis:
    tipo: str           # PHANTOM_DIA, OMISION_DIA, PHANTOM_NOCHE, ENTRANTE_DUP, MISMATCH_LEVE, APERTURA_REAL
    peso: int           # peso de la cerrada/entrante involucrada
    accion: str         # descripción legible
    delta_stock: int    # cambio en venta
    delta_latas: int    # cambio en latas (±1 o 0)

    # Evaluación (se llena en paso 4)
    planos_favor: List[str] = field(default_factory=list)
    planos_neutros: List[str] = field(default_factory=list)
    planos_contra: List[str] = field(default_factory=list)
    sightings: int = 0

    @property
    def n_favor(self):
        return len(self.planos_favor)

    @property
    def n_contra(self):
        return len(self.planos_contra)

    @property
    def independientes(self):
        return len(set(self.planos_favor))

    @property
    def converge(self):
        return self.independientes >= 2 and self.n_contra == 0


# ═══════════════════════════════════════════════════════════════
# PASO 1: Timeline
# ═══════════════════════════════════════════════════════════════

def _paso1_timeline(nombre: str, datos: DatosDia) -> List[Snapshot]:
    timeline = []
    for ctx in datos.contexto:
        s = ctx.sabores.get(nombre)
        if s:
            timeline.append(Snapshot(
                label=ctx.nombre_hoja,
                ab=s.abierta or 0,
                cerradas=list(s.cerradas),
                entrantes=list(s.entrantes),
                total=s.total,
            ))
    sd = datos.turno_dia.sabores.get(nombre)
    if sd:
        timeline.append(Snapshot(
            label=datos.turno_dia.nombre_hoja,
            ab=sd.abierta or 0,
            cerradas=list(sd.cerradas),
            entrantes=list(sd.entrantes),
            total=sd.total,
        ))
    sn = datos.turno_noche.sabores.get(nombre)
    if sn:
        timeline.append(Snapshot(
            label=datos.turno_noche.nombre_hoja,
            ab=sn.abierta or 0,
            cerradas=list(sn.cerradas),
            entrantes=list(sn.entrantes),
            total=sn.total,
        ))
    return timeline


# ═══════════════════════════════════════════════════════════════
# PASO 1b: Lifecycle scan — detectar aperturas previas en timeline
# No mata identidades; produce señales probatorias para Paso 3/4.
# ═══════════════════════════════════════════════════════════════

@dataclass
class CanLifecycle:
    """Estado inferido de una cerrada en el timeline."""
    peso_ref: int
    estado: str  # VIVA, ABIERTA_ALTA_CONFIANZA, REAPARICION_SOSPECHOSA
    turno_apertura: Optional[str] = None  # label del turno donde se abrió
    sightings_pre: int = 0   # sightings antes de apertura
    sightings_post: int = 0  # sightings después de apertura (reapariciones)
    sightings_relevantes: int = 0  # sightings que cuentan para hipótesis actuales
    confianza_apertura: float = 0.0  # qué tan seguro es que se abrió


def _paso1b_lifecycle(timeline: List[Snapshot], tol: int = 30) -> Dict[int, CanLifecycle]:
    """
    Recorre el timeline buscando eventos de apertura:
      - Cerrada presente en turno T, ausente en T+1, ab sube significativamente.

    Produce un dict peso_ref -> CanLifecycle con estados blandos.
    No emite sentencias; produce evidencia para pasos posteriores.
    """
    lifecycle = {}

    if len(timeline) < 2:
        return lifecycle

    # Recolectar todos los pesos de cerradas vistos en el timeline
    all_cerr_pesos = set()
    for snap in timeline:
        for c in snap.cerradas:
            all_cerr_pesos.add(int(c))

    for peso_ref in all_cerr_pesos:
        # Rastrear presencia/ausencia a lo largo del timeline
        presencia = []
        for i, snap in enumerate(timeline):
            present = any(abs(peso_ref - c) <= tol for c in snap.cerradas)
            # También contar como entrante
            present_ent = any(abs(peso_ref - e) <= tol for e in snap.entrantes)
            presencia.append({
                'idx': i,
                'label': snap.label,
                'cerr': present,
                'ent': present_ent,
                'ab': snap.ab,
            })

        # Buscar patrón de apertura: cerr presente en T, ausente en T+1, ab sube
        apertura_detectada = False
        turno_apertura = None
        idx_apertura = None
        conf_apertura = 0.0

        for i in range(len(presencia) - 1):
            curr = presencia[i]
            next_p = presencia[i + 1]

            if curr['cerr'] and not next_p['cerr']:
                # Cerrada desapareció. ¿Ab subió?
                rise = next_p['ab'] - curr['ab']
                expected_rise = peso_ref - 280  # peso neto sin tara

                if rise > 500:
                    # Rise significativo. ¿Coherente con esta cerrada?
                    coherencia = 1.0 - min(1.0, abs(rise - expected_rise) / max(expected_rise, 1))

                    if coherencia > 0.5:
                        conf_apertura = min(0.95, 0.7 + coherencia * 0.25)
                    else:
                        # Rise existe pero no coherente con ESTA cerrada
                        # Podría ser otra cerrada la que se abrió
                        conf_apertura = 0.4

                    apertura_detectada = True
                    turno_apertura = curr['label']
                    idx_apertura = i
                    break

                elif len(timeline[i].cerradas) > len(timeline[i + 1].cerradas):
                    # Desapareció y hay menos cerradas, aunque ab no subió mucho
                    # Posible apertura con venta inmediata fuerte
                    conf_apertura = 0.5
                    apertura_detectada = True
                    turno_apertura = curr['label']
                    idx_apertura = i
                    break

        if not apertura_detectada:
            # Can viva — contar sightings normales
            total_sightings = sum(1 for p in presencia if p['cerr'])
            lifecycle[peso_ref] = CanLifecycle(
                peso_ref=peso_ref,
                estado='VIVA',
                sightings_pre=total_sightings,
                sightings_relevantes=total_sightings,
            )
        else:
            # Can con apertura detectada
            sightings_pre = sum(1 for p in presencia[:idx_apertura + 1] if p['cerr'])
            sightings_post = sum(1 for p in presencia[idx_apertura + 1:] if p['cerr'])

            if sightings_post > 0:
                estado = 'REAPARICION_SOSPECHOSA'
            else:
                estado = 'ABIERTA_ALTA_CONFIANZA'

            lifecycle[peso_ref] = CanLifecycle(
                peso_ref=peso_ref,
                estado=estado,
                turno_apertura=turno_apertura,
                sightings_pre=sightings_pre,
                sightings_post=sightings_post,
                sightings_relevantes=sightings_pre,  # post-apertura no cuenta
                confianza_apertura=conf_apertura,
            )

    return lifecycle


# ═══════════════════════════════════════════════════════════════
# PASO 2: Planos de evidencia
# ═══════════════════════════════════════════════════════════════

def _paso2_plano1(nombre: str, datos: DatosDia) -> PlanoP1:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return PlanoP1('NO_DATA', 0, 0, 0)

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    delta = ab_n - ab_d

    # Buscar fuentes que desaparecen
    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= 30 for cn in n.cerradas)]
    ent_gone = [e for e in d.entrantes if not any(abs(e - en) <= 50 for en in n.entrantes)]

    # También considerar entrantes que PERSISTEN como fuente de apertura
    # (el entrante fue abierto pero sigue listado)
    ent_persist = []
    for ea in d.entrantes:
        for eb in n.entrantes:
            if abs(ea - eb) <= 50:
                ent_persist.append(ea)
                break

    fuente = None
    todas_fuentes = cerr_gone + ent_gone + ent_persist

    if abs(delta) <= 20:
        cls = 'ESTATICA'
    elif delta < -20:
        cls = 'VENTA_PURA'
    elif delta > 20 and todas_fuentes:
        # Buscar la fuente más coherente con el rise
        mejor_fuente = None
        mejor_diff = 99999
        for f in todas_fuentes:
            expected = f - 280
            diff = abs(delta - expected)
            if diff < mejor_diff:
                mejor_diff = diff
                mejor_fuente = f
        fuente = mejor_fuente
        if mejor_diff <= max(500, (mejor_fuente - 280) * 0.15):
            cls = 'APERTURA_SOPORTADA'
        else:
            cls = 'APERTURA_PLAUSIBLE_NO_CONFIRMADA'
    elif delta > 20:
        cls = 'AB_SUBE_SIN_FUENTE'
    else:
        cls = 'VENTA_PURA'

    return PlanoP1(cls, ab_d, ab_n, delta, fuente)


def _count_sightings(peso: int, timeline: List[Snapshot], tol: int = 30) -> int:
    count = 0
    for snap in timeline:
        if any(abs(peso - c) <= tol for c in snap.cerradas):
            count += 1
        if any(abs(peso - e) <= tol for e in snap.entrantes):
            count += 1
    return count


def _paso2_plano2(nombre: str, datos: DatosDia, timeline: List[Snapshot],
                  lifecycle: Optional[Dict[int, CanLifecycle]] = None) -> PlanoP2:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return PlanoP2([], [], [], [], [])

    from .matching import match_cerradas
    cerr_a = list(d.cerradas)
    cerr_b = list(n.cerradas)
    mr = match_cerradas(cerr_a, cerr_b)

    def _effective_sightings(peso, timeline):
        """Sightings relevantes: usa lifecycle si disponible."""
        if lifecycle:
            # Buscar en lifecycle con tolerancia
            for lc_peso, lc in lifecycle.items():
                if abs(peso - lc_peso) <= 30:
                    return lc.sightings_relevantes
        return _count_sightings(peso, timeline)

    matches = []
    for ia, ib, pa, pb, diff in mr.matched:
        s = _effective_sightings(pa, timeline)
        matches.append((pa, pb, diff, s))

    unmatched_a = [(cerr_a[ia], _effective_sightings(cerr_a[ia], timeline))
                   for ia in mr.unmatched_a]
    unmatched_b = [(cerr_b[ib], _effective_sightings(cerr_b[ib], timeline))
                   for ib in mr.unmatched_b]

    all_sightings = {}
    for c in cerr_a + cerr_b:
        all_sightings[c] = _effective_sightings(c, timeline)

    return PlanoP2(
        cerr_a=cerr_a, cerr_b=cerr_b,
        desaparecen=unmatched_a,
        aparecen=unmatched_b,
        persisten=matches,
        sightings=all_sightings,
    )


def _paso2_plano3(nombre: str, datos: DatosDia, timeline: List[Snapshot]) -> PlanoP3:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return PlanoP3([], [], [], [], [])

    ent_a = list(d.entrantes)
    ent_b = list(n.entrantes)

    ent_a_rem = list(ent_a)
    matched = []
    new_b = []
    for eb in ent_b:
        found = False
        for i, ea in enumerate(ent_a_rem):
            if abs(eb - ea) <= 50:
                matched.append((ea, eb, abs(ea - eb)))
                ent_a_rem.pop(i)
                found = True
                break
        if not found:
            new_b.append(eb)

    return PlanoP3(
        ent_a=ent_a, ent_b=ent_b,
        persisten=matched,
        nuevos_b=new_b,
        gone_a=list(ent_a_rem),
    )


# ═══════════════════════════════════════════════════════════════
# PASO 3: Generar TODAS las hipótesis
# ═══════════════════════════════════════════════════════════════

def _paso3_hipotesis(sc, p1: PlanoP1, p2: PlanoP2, p3: PlanoP3,
                     timeline: List[Snapshot] = None) -> List[Hipotesis]:
    hips = []

    # --- 3a: Cerradas que DESAPARECEN (en DIA, no en NOCHE) ---
    for peso, sightings in p2.desaparecen:
        # H: phantom
        delta_latas = 0
        if sc.n_cerr_a > sc.n_cerr_b:
            delta_latas = -1
        hips.append(Hipotesis(
            tipo='PHANTOM_DIA',
            peso=peso,
            accion=f'Eliminar cerr {int(peso)} de DIA (phantom)',
            delta_stock=-peso,
            delta_latas=delta_latas,
            sightings=sightings,
        ))

        # H: apertura real
        # Señales: (a) P1 detecta apertura, o (b) menos cerradas en NOCHE que en DIA
        apertura_por_p1 = p1.clasificacion in ('APERTURA_SOPORTADA', 'APERTURA_PLAUSIBLE_NO_CONFIRMADA')
        apertura_por_conteo = sc.n_cerr_a > sc.n_cerr_b
        if apertura_por_p1 or apertura_por_conteo:
            hips.append(Hipotesis(
                tipo='APERTURA_REAL',
                peso=peso,
                accion=f'Confirmar apertura cerr {int(peso)}',
                delta_stock=0,
                delta_latas=0,
                sightings=sightings,
            ))

    # --- 3a-bis: Continuidad de conteo — detección de cerrada duplicada ---
    # Patrón sándwich: turno previo N cerr → DIA N+1 cerr → NOCHE N cerr,
    # sin entrante que justifique la cerrada extra, y dos cerradas de DIA
    # con diff ≤30g (varianza de pesaje de misma lata).
    if timeline and len(timeline) >= 3 and sc.n_cerr_a > sc.n_cerr_b:
        # Buscar turno inmediatamente anterior al DIA
        turnos_pre = [s for s in timeline if s.label != p2.cerr_a and s.label != p2.cerr_b]
        # El turno previo es el último antes del DIA en el timeline
        dia_idx = None
        for i, s in enumerate(timeline):
            if s.cerradas == list(p2.cerr_a) or set(int(c) for c in s.cerradas) == set(int(c) for c in p2.cerr_a):
                dia_idx = i
                break
        turno_previo = timeline[dia_idx - 1] if dia_idx and dia_idx > 0 else None
        # El turno siguiente es NOCHE (último del timeline para este día)
        noche_idx = None
        for i, s in enumerate(timeline):
            if set(int(c) for c in s.cerradas) == set(int(c) for c in p2.cerr_b):
                noche_idx = i
        turno_siguiente_cerr_n = len(p2.cerr_b)

        if turno_previo is not None:
            n_previo = len(turno_previo.cerradas)
            n_dia = sc.n_cerr_a
            n_noche = sc.n_cerr_b

            # Patrón sándwich: N → N+1 → N (o menos)
            if n_previo <= n_noche and n_dia == n_previo + 1:
                # Buscar par de cerradas en DIA con diff ≤30g
                cerr_dia = sorted(p2.cerr_a)
                for i in range(len(cerr_dia)):
                    for j in range(i + 1, len(cerr_dia)):
                        diff = abs(cerr_dia[i] - cerr_dia[j])
                        if diff <= 30:
                            # Verificar que no hay entrante que justifique la extra
                            tiene_entrante = False
                            if turno_previo:
                                for e in turno_previo.entrantes:
                                    if any(abs(e - c) <= 200 for c in [cerr_dia[i], cerr_dia[j]]):
                                        tiene_entrante = True
                            # Solo si no hay entrante que justifique
                            if not tiene_entrante:
                                # La cerrada que desaparece es la duplicada
                                # (la que matchea con NOCHE persiste, la otra es fantasma)
                                peso_dup = None
                                for peso_d, _ in p2.desaparecen:
                                    if abs(peso_d - cerr_dia[i]) <= 30 or abs(peso_d - cerr_dia[j]) <= 30:
                                        peso_dup = peso_d
                                        break
                                if peso_dup is not None:
                                    hips.append(Hipotesis(
                                        tipo='DUPLICADO_CERRADA',
                                        peso=peso_dup,
                                        accion=f'Cerr {int(peso_dup)} es duplicado registral de ~{int(cerr_dia[j]) if abs(peso_dup - cerr_dia[i]) <= 30 else int(cerr_dia[i])}. '
                                               f'Sandwich {n_previo}->{n_dia}->{n_noche}, diff={diff}g. Eliminar duplicado.',
                                        delta_stock=-peso_dup,
                                        delta_latas=0,  # no es apertura, es duplicado
                                        sightings=0,  # la duplicada no tiene historia propia
                                    ))

    # --- 3b: Cerradas que APARECEN (en NOCHE, no en DIA) ---
    for peso, sightings in p2.aparecen:
        # H: omisión en DIA
        hips.append(Hipotesis(
            tipo='OMISION_DIA',
            peso=peso,
            accion=f'Agregar cerr {int(peso)} a DIA (omitida)',
            delta_stock=+peso,
            delta_latas=0,
            sightings=sightings,
        ))

        # H: phantom en NOCHE
        hips.append(Hipotesis(
            tipo='PHANTOM_NOCHE',
            peso=peso,
            accion=f'Eliminar cerr {int(peso)} de NOCHE (phantom)',
            delta_stock=+peso,
            delta_latas=0,
            sightings=sightings,
        ))

    # --- 3c: Entrantes que PERSISTEN con apertura ---
    if p1.clasificacion in ('APERTURA_SOPORTADA', 'APERTURA_PLAUSIBLE_NO_CONFIRMADA'):
        for ea, eb, diff in p3.persisten:
            hips.append(Hipotesis(
                tipo='ENTRANTE_DUP',
                peso=eb,
                accion=f'Eliminar entrante {int(eb)} de NOCHE (dup post-apertura)',
                delta_stock=+eb,
                delta_latas=0,
                sightings=0,
            ))

    # --- 3e: Mismatch leve (30-100g) en cerradas ya persistidas ---
    for ca, cb, diff, sightings in p2.persisten:
        if diff > 30:
            hips.append(Hipotesis(
                tipo='MISMATCH_LEVE',
                peso=ca,
                accion=f'Ajuste pesaje cerr {int(ca)}->{int(cb)} ({int(diff)}g)',
                delta_stock=-diff,
                delta_latas=0,
                sightings=sightings,
            ))

    # --- 3f: Cerradas sin match formal pero con diff moderada (30-200g) ---
    # Buscar pares plausibles entre desaparecen y aparecen (greedy por menor diff)
    restantes_aparecen = list(p2.aparecen)
    for ca_peso, ca_sight in p2.desaparecen:
        mejor_match = None
        mejor_diff = 999
        mejor_idx = -1
        for i, (cb_peso, cb_sight) in enumerate(restantes_aparecen):
            diff = abs(ca_peso - cb_peso)
            if 30 < diff <= 200 and diff < mejor_diff:
                mejor_match = (cb_peso, cb_sight)
                mejor_diff = diff
                mejor_idx = i
        if mejor_match:
            cb_peso, cb_sight = mejor_match
            delta = ca_peso - cb_peso
            hips.append(Hipotesis(
                tipo='MISMATCH_LEVE',
                peso=ca_peso,
                accion=f'Ajuste pesaje cerr {int(ca_peso)}->{int(cb_peso)} ({int(mejor_diff)}g)',
                delta_stock=-delta,
                delta_latas=0,
                sightings=max(ca_sight, cb_sight),
            ))
            restantes_aparecen.pop(mejor_idx)

    # --- 3g: Entrante mismo can con matching amplio (50-200g) ---
    # Cuando P3 no matcheó dos entrantes que son plausiblemente el mismo
    for ea in p3.gone_a:
        for eb in p3.nuevos_b:
            diff = abs(ea - eb)
            if 50 < diff <= 200:
                # Hipótesis: mismo entrante, remover eb de new_ent_b
                hips.append(Hipotesis(
                    tipo='ENTRANTE_MISMO_CAN',
                    peso=eb,
                    accion=f'Entrante {int(ea)}<->{int(eb)} son mismo can ({int(diff)}g diff), remover de new_ent_b',
                    delta_stock=-eb,
                    delta_latas=0,
                    sightings=0,
                ))

    # --- 3h: Genealogía entrante→cerrada (cruce P2 x P3 x timeline) ---
    # Una cerrada que aparece sin historia como cerrada pero tiene una entrante
    # reciente en el timeline con peso cercano (±200g) es probablemente esa
    # entrante promovida con error de pesaje.
    # Igualmente, una cerrada que "desaparece" pero tiene una entrante reciente
    # en su vecindario es sospechosa de ser esa entrante mal pesada.
    if timeline:
        # Recolectar entrantes del timeline reciente (turnos previos al DIA)
        entrantes_recientes = []  # (peso, turno_label)
        for snap in timeline:
            # Solo turnos anteriores al DIA actual (contexto previo)
            for e in snap.entrantes:
                entrantes_recientes.append((int(e), snap.label))

        if entrantes_recientes:
            # Para cerradas que DESAPARECEN en DIA (sin match en NOCHE)
            for peso_d, sightings_d in p2.desaparecen:
                for ent_peso, ent_turno in entrantes_recientes:
                    diff = abs(peso_d - ent_peso)
                    if diff <= 200 and diff > 30:
                        # Cerrada DIA podría ser la entrante mal pesada
                        hips.append(Hipotesis(
                            tipo='GENEALOGIA_ENT_CERR',
                            peso=peso_d,
                            accion=f'Cerr DIA {int(peso_d)} es entrante {ent_peso} ({ent_turno}) con error pesaje {int(diff)}g. Corregir a {ent_peso}',
                            delta_stock=ent_peso - peso_d,  # ajuste por diferencia de peso
                            delta_latas=0,
                            sightings=sightings_d,
                        ))
                        break  # una sola entrante rival por cerrada

            # Para cerradas que APARECEN en NOCHE (sin match en DIA)
            for peso_n, sightings_n in p2.aparecen:
                for ent_peso, ent_turno in entrantes_recientes:
                    diff = abs(peso_n - ent_peso)
                    if diff <= 30:
                        # Cerrada NOCHE es la entrante promovida (peso coherente)
                        # Esto no necesita corrección por sí solo, pero refuerza
                        # que la cerrada tiene genealogía legítima
                        hips.append(Hipotesis(
                            tipo='GENEALOGIA_ENT_CERR',
                            peso=peso_n,
                            accion=f'Cerr NOCHE {int(peso_n)} es entrante {ent_peso} ({ent_turno}) promovida. Genealogia confirmada.',
                            delta_stock=0,  # sin corrección, solo identidad
                            delta_latas=0,
                            sightings=sightings_n,
                        ))
                        break

    return hips


# ═══════════════════════════════════════════════════════════════
# PASO 4: Evaluar cada hipótesis contra TODOS los planos
# ═══════════════════════════════════════════════════════════════

def _paso4_evaluar(hips: List[Hipotesis], sc, p1: PlanoP1, p2: PlanoP2, p3: PlanoP3):
    for h in hips:
        h.planos_favor = []
        h.planos_neutros = []
        h.planos_contra = []

        # --- Evaluar P1 ---
        if h.tipo in ('PHANTOM_DIA', 'OMISION_DIA'):
            if p1.clasificacion in ('VENTA_PURA', 'ESTATICA'):
                h.planos_favor.append('P1')
            elif p1.clasificacion == 'APERTURA_SOPORTADA':
                if h.tipo == 'PHANTOM_DIA' and h.peso != p1.fuente:
                    h.planos_favor.append('P1')
                else:
                    h.planos_contra.append('P1')
            else:
                h.planos_neutros.append('P1')

        elif h.tipo == 'PHANTOM_NOCHE':
            if p1.clasificacion in ('VENTA_PURA', 'ESTATICA'):
                h.planos_favor.append('P1')
            else:
                h.planos_neutros.append('P1')

        elif h.tipo == 'ENTRANTE_DUP':
            if p1.clasificacion in ('APERTURA_SOPORTADA', 'APERTURA_PLAUSIBLE_NO_CONFIRMADA'):
                h.planos_favor.append('P1')
            else:
                h.planos_contra.append('P1')

        elif h.tipo == 'APERTURA_REAL':
            # Guardia duplicado: si hay DUPLICADO_CERRADA viable para el mismo peso,
            # APERTURA_REAL no puede ganar por conteo
            tiene_duplicado_rival = any(
                hh.tipo == 'DUPLICADO_CERRADA' and abs(hh.peso - h.peso) <= 30
                for hh in hips
            )
            if tiene_duplicado_rival:
                h.planos_contra.append('P4_DUPLICADO_RIVAL')
                h.planos_neutros.append('P1')
                continue  # no evaluar más planos, ya está vetado

            # Guardia: si la cerrada desaparecida tiene competidora mismatch
            # en NOCHE (30-200g), apertura pierde privilegio de confirmación.
            tiene_mismatch_competitivo = False
            for cb_peso, _ in p2.aparecen:
                if 30 < abs(h.peso - cb_peso) <= 200:
                    tiene_mismatch_competitivo = True
                    break

            if p1.clasificacion == 'APERTURA_SOPORTADA' and p1.fuente == h.peso:
                if tiene_mismatch_competitivo:
                    # Apertura soportada pero con rival mismatch → neutro, no favor
                    h.planos_neutros.append('P1')
                else:
                    h.planos_favor.append('P1')
            elif p1.clasificacion == 'APERTURA_PLAUSIBLE_NO_CONFIRMADA':
                if tiene_mismatch_competitivo:
                    h.planos_neutros.append('P1')
                else:
                    h.planos_favor.append('P1')
            elif sc.n_cerr_a > sc.n_cerr_b:
                if tiene_mismatch_competitivo:
                    # Apertura por conteo + mismatch rival → contra
                    h.planos_contra.append('P1_MISMATCH_RIVAL')
                else:
                    h.planos_favor.append('P1_CONTEO')
            else:
                h.planos_neutros.append('P1')

        elif h.tipo == 'MISMATCH_LEVE':
            h.planos_neutros.append('P1')

        elif h.tipo == 'GENEALOGIA_ENT_CERR':
            h.planos_neutros.append('P1')  # P1 no dice nada sobre genealogia

        elif h.tipo == 'DUPLICADO_CERRADA':
            h.planos_neutros.append('P1')  # P1 no dice nada sobre duplicados

        # --- Evaluar P2 ---
        if h.tipo == 'PHANTOM_DIA':
            if h.sightings <= 1:
                h.planos_favor.append('P2')
            elif h.sightings == 2:
                h.planos_neutros.append('P2')
            else:
                h.planos_contra.append('P2')

        elif h.tipo == 'OMISION_DIA':
            if h.sightings >= 2:
                h.planos_favor.append('P2')
            else:
                h.planos_contra.append('P2')

        elif h.tipo == 'PHANTOM_NOCHE':
            if h.sightings <= 1:
                h.planos_favor.append('P2')
            elif h.sightings >= 3:
                h.planos_contra.append('P2')
            else:
                h.planos_neutros.append('P2')

        elif h.tipo == 'ENTRANTE_DUP':
            h.planos_neutros.append('P2')

        elif h.tipo == 'APERTURA_REAL':
            if h.sightings >= 2:
                h.planos_favor.append('P2')
            else:
                h.planos_neutros.append('P2')

        elif h.tipo == 'MISMATCH_LEVE':
            h.planos_favor.append('P2')  # solo P2

        elif h.tipo == 'GENEALOGIA_ENT_CERR':
            # P2: la genealogía explica la cerrada — a favor
            h.planos_favor.append('P2_GENEALOGIA')

        elif h.tipo == 'DUPLICADO_CERRADA':
            # P2: conteo sándwich N→N+1→N — a favor
            h.planos_favor.append('P2_CONTEO')
            # P4: continuidad temporal confirma que eran N, no N+1
            h.planos_favor.append('P4_CONTINUIDAD')

        elif h.tipo == 'ENTRANTE_MISMO_CAN':
            h.planos_neutros.append('P2')

            # P1: si raw es imposible sin apertura (venta > abierta) -> reductio
            ab_d = p1.ab_d
            if ab_d > 0 and sc.venta_raw > ab_d and p1.clasificacion == 'VENTA_PURA':
                h.planos_favor.append('P1_REDUCTIO')
            else:
                h.planos_neutros.append('P1')

        # --- Evaluar P3 ---
        if h.tipo == 'ENTRANTE_DUP':
            h.planos_favor.append('P3')
        elif h.tipo == 'ENTRANTE_MISMO_CAN':
            # P3 a favor: la corrección elimina un entrante fantasma
            h.planos_favor.append('P3')
        elif h.tipo == 'GENEALOGIA_ENT_CERR':
            # P3 a favor: hay entrante en timeline que explica la cerrada
            h.planos_favor.append('P3_GENEALOGIA')
        elif h.tipo == 'DUPLICADO_CERRADA':
            # P3: sin entrante que justifique la cerrada extra — a favor del duplicado
            h.planos_favor.append('P3_SIN_ENTRANTE')
        else:
            h.planos_neutros.append('P3')

        # --- Guardia de coherencia ---
        venta_corr = sc.venta_raw + h.delta_stock + h.delta_latas * 280
        if venta_corr < -300:
            h.planos_contra.append('COHERENCIA_NEG')
        if sc.total_a > 0 and abs(venta_corr) > sc.total_a * 0.8:
            h.planos_contra.append('COHERENCIA_HIGH')
        # Sin apertura y venta corregida > 5000g es poco realista
        # Pero si hay menos cerradas en NOCHE (apertura por conteo), venta alta es esperada
        apertura_por_conteo = sc.n_cerr_a > sc.n_cerr_b
        if p1.clasificacion in ('VENTA_PURA', 'ESTATICA') and venta_corr >= 5000 and not apertura_por_conteo:
            h.planos_contra.append('COHERENCIA_HIGH_NO_APERTURA')


# ═══════════════════════════════════════════════════════════════
# PASO 5: Seleccionar mejor hipótesis
# ═══════════════════════════════════════════════════════════════

def _paso5_seleccionar(hips: List[Hipotesis], sc, p2: PlanoP2
                       ) -> Optional[Hipotesis]:
    # Filtrar: descartar con planos en contra
    viables = [h for h in hips if h.n_contra == 0]

    if not viables:
        return None

    # Ordenar: convergencia > n_favor
    viables.sort(key=lambda h: (h.independientes, h.n_favor), reverse=True)

    mejor = viables[0]

    # Guardia bilateral: si la mejor es unilateral (PHANTOM/APERTURA) pero
    # hay un MISMATCH_LEVE o GENEALOGIA viable para OTRO slot del mismo episodio,
    # la unilateral no puede resolverse sola — buscar si hay una GENEALOGIA
    # que explique mejor el cuadro. Si la hay, usarla. Si no, H0.
    if mejor.tipo in ('PHANTOM_DIA', 'APERTURA_REAL'):
        mismatch_viable = [h for h in hips
                           if h.tipo in ('MISMATCH_LEVE', 'GENEALOGIA_ENT_CERR')
                           and h.peso != mejor.peso
                           and h.n_contra == 0]
        if mismatch_viable:
            # Hay estructura bilateral. ¿Hay una GENEALOGIA que explique
            # el slot conflictivo directamente?
            genealogia_del_mismo_slot = [h for h in viables
                                         if h.tipo == 'GENEALOGIA_ENT_CERR'
                                         and h.peso == mejor.peso]
            if genealogia_del_mismo_slot:
                # La genealogía explica la cerrada que "desaparece" —
                # reemplazar la hipótesis unilateral por la genealogía
                mejor = genealogia_del_mismo_slot[0]
            else:
                # Sin genealogía directa → H0
                return None

    # Regla ≥2 planos independientes
    if mejor.independientes < 2:
        # Excepción Tipo C: phantom 1-sighting con cerradas matched ≥3 sightings
        if mejor.tipo == 'PHANTOM_DIA' and mejor.sightings <= 1:
            matched_sightings = [s for _, _, _, s in p2.persisten]
            if any(s >= 3 for s in matched_sightings):
                mejor._tipo_c_override = True
            else:
                return None
        elif mejor.tipo == 'MISMATCH_LEVE':
            # Mismatch leve con solo 1 plano -> ESTIMADO, permitido
            mejor._tipo_d_override = True
        elif mejor.tipo == 'ENTRANTE_MISMO_CAN':
            # Entrante mismo can con P3 + P1_REDUCTIO o solo P3 -> FORZADO o ESTIMADO
            mejor._tipo_d_override = True
        elif mejor.tipo == 'GENEALOGIA_ENT_CERR':
            # Genealogia con 1 plano -> ESTIMADO
            mejor._tipo_d_override = True
        elif mejor.tipo == 'DUPLICADO_CERRADA':
            # Duplicado con evidencia compuesta -> CONFIRMADO si >=2 planos
            pass  # dejar que la convergencia normal lo maneje
        else:
            return None

    return mejor


# ═══════════════════════════════════════════════════════════════
# PASO 5b: Composición de correcciones independientes
# Solo combina hipótesis que:
#   1. Apuntan a targets distintos (diferentes cerradas)
#   2. No compiten causalmente
#   3. Cada una pasa coherencia individual
#   4. Una no presupone la falsedad de la otra
# ═══════════════════════════════════════════════════════════════

def _paso5b_componer(hips: List[Hipotesis], sc, p2: PlanoP2,
                     lifecycle: Optional[Dict[int, CanLifecycle]] = None
                     ) -> Optional[List[Hipotesis]]:
    """
    Intenta componer 2+ correcciones independientes.
    Retorna lista de hipótesis compatibles o None si no aplica.
    """
    # Solo intentar composición si hay cerradas que desaparecen en DIA
    # y la resolución individual dejaría una parte sin explicar
    if len(p2.desaparecen) < 2:
        return None

    viables = [h for h in hips if h.n_contra == 0]
    if len(viables) < 2:
        return None

    # Agrupar viables por peso target (la cerrada que tocan)
    por_target = {}
    for h in viables:
        target = int(h.peso)
        if target not in por_target:
            por_target[target] = []
        por_target[target].append(h)

    if len(por_target) < 2:
        return None

    # Para cada target, elegir la mejor hipótesis
    candidatos = {}
    for target, hs in por_target.items():
        hs.sort(key=lambda h: (h.independientes, h.n_favor), reverse=True)
        best = hs[0]
        # Filtrar: no componer hipótesis que solo tienen 0 planos favor
        if best.n_favor == 0:
            continue
        # No componer APERTURA_REAL vetada
        if best.tipo == 'APERTURA_REAL' and any('RIVAL' in c or 'DUPLICADO' in c for c in best.planos_contra):
            continue
        candidatos[target] = best

    if len(candidatos) < 2:
        return None

    # Verificar compatibilidad: no deben competir causalmente
    # Regla: no puede haber dos PHANTOM_DIA + dos OMISION_DIA sobre targets distintos
    # (eso sería inventar dos explicaciones independientes para el mismo desorden)
    # Permitido: PHANTOM + GENEALOGIA, PHANTOM + MISMATCH, GENEALOGIA + GENEALOGIA
    combo = list(candidatos.values())

    tipos = set(h.tipo for h in combo)
    # Dos PHANTOM_DIA sería muy agresivo — permitir solo si uno tiene lifecycle sospechoso
    n_phantom = sum(1 for h in combo if h.tipo == 'PHANTOM_DIA')
    if n_phantom >= 2 and lifecycle:
        # Solo permitir si al menos uno tiene REAPARICION_SOSPECHOSA
        phantom_con_lifecycle = 0
        for h in combo:
            if h.tipo == 'PHANTOM_DIA':
                for lc_peso, lc in lifecycle.items():
                    if abs(h.peso - lc_peso) <= 30 and lc.estado == 'REAPARICION_SOSPECHOSA':
                        phantom_con_lifecycle += 1
                        break
        if phantom_con_lifecycle == 0:
            return None
    elif n_phantom >= 2:
        return None

    # Verificar compatibilidad causal: una hipótesis no puede afirmar
    # la existencia de un can que otra hipótesis niega.
    # GENEALOGIA dice "peso X es en realidad peso Y (que existe)"
    # PHANTOM dice "peso Z no existe"
    # Si Y == Z → incompatibles.
    pesos_afirmados = set()  # pesos cuya existencia se afirma
    pesos_negados = set()    # pesos cuya existencia se niega

    for h in combo:
        if h.tipo == 'GENEALOGIA_ENT_CERR':
            # Genealogía afirma que el can es realmente otro peso (el entrante)
            # El entrante que hereda existe legítimamente
            # Extraer peso del entrante del acción text o del delta
            # El peso target de genealogía es el peso de la cerrada que se corrige
            pesos_afirmados.add(int(h.peso))
        elif h.tipo in ('PHANTOM_DIA', 'PHANTOM_NOCHE'):
            pesos_negados.add(int(h.peso))
        elif h.tipo == 'OMISION_DIA':
            pesos_afirmados.add(int(h.peso))

    # Conflicto: un peso no puede ser afirmado y negado a la vez
    conflicto_directo = pesos_afirmados & pesos_negados
    if conflicto_directo:
        # Remover hipótesis conflictivas — quedarse con las que no contradicen
        combo = [h for h in combo
                 if not (h.tipo in ('PHANTOM_DIA', 'PHANTOM_NOCHE')
                         and int(h.peso) in conflicto_directo)]
        if len(combo) < 2:
            return None

    # También verificar: GENEALOGIA implica que un entrante se convirtió en cerrada.
    # Si hay PHANTOM_NOCHE sobre esa misma cerrada target → conflicto implícito.
    for h in list(combo):
        if h.tipo == 'GENEALOGIA_ENT_CERR':
            # El peso genealógico es la cerrada DIA. El entrante es el can real.
            # Si hay phantom NOCHE sobre un peso cercano al entrante → conflicto
            for h2 in combo:
                if h2.tipo == 'PHANTOM_NOCHE' and h2 is not h:
                    # Verificar si el phantom toca el mismo can que la genealogía establece
                    if abs(int(h2.peso) - int(h.peso)) <= 200:
                        combo = [x for x in combo if x is not h2]

    if len(combo) < 2:
        return None

    # Verificar coherencia compuesta
    delta_total = sum(h.delta_stock + h.delta_latas * 280 for h in combo)
    venta_compuesta = sc.venta_raw + delta_total
    if venta_compuesta < -300:
        return None
    if sc.total_a > 0 and abs(venta_compuesta) > sc.total_a * 0.8:
        return None

    # Verificar que cada componente aporta al resultado
    # (no componer si uno de los deltas es 0 y no cambia nada)
    deltas_reales = [h for h in combo if abs(h.delta_stock + h.delta_latas * 280) > 0]
    if len(deltas_reales) < 2:
        return None

    return combo


# ═══════════════════════════════════════════════════════════════
# PASO 6: Asignar tipo/banda/confianza
# ═══════════════════════════════════════════════════════════════

def _paso6_clasificar(h: Hipotesis, sc) -> Tuple[TipoJustificacion, Banda, float]:
    # Tipo de justificación
    if h.independientes >= 2:
        tipo = TipoJustificacion.A
    elif getattr(h, '_tipo_c_override', False):
        tipo = TipoJustificacion.C
    elif getattr(h, '_tipo_d_override', False):
        tipo = TipoJustificacion.D
    elif sc.venta_raw < -300 or sc.venta_raw > 7000:
        tipo = TipoJustificacion.B  # raw imposible
    else:
        tipo = TipoJustificacion.D

    # Banda
    if tipo in (TipoJustificacion.A, TipoJustificacion.C):
        banda = Banda.CONFIRMADO
    elif tipo == TipoJustificacion.B:
        banda = Banda.FORZADO
    else:
        banda = Banda.ESTIMADO

    # Confianza
    conf = 0.65 + 0.10 * h.independientes
    if tipo == TipoJustificacion.B:
        conf -= 0.10
    conf = max(0.30, min(0.95, conf))

    return tipo, banda, conf


# ═══════════════════════════════════════════════════════════════
# PASO 7: Guardia post-corrección
# ═══════════════════════════════════════════════════════════════

def _paso7_guardia(h: Hipotesis, sc) -> bool:
    """Retorna True si pasa la guardia, False si debe rechazarse."""
    venta_final = sc.venta_raw + h.delta_stock + h.delta_latas * 280
    if venta_final < -300:
        return False
    # Si raw no era negativo y corrección lo empeora
    if sc.venta_raw >= 0 and abs(venta_final) > abs(sc.venta_raw):
        return False
    return True


# ═══════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL: resolver un sabor
# ═══════════════════════════════════════════════════════════════

def _resolver_sabor(nombre: str, clasificado: SaborClasificado,
                    datos: DatosDia) -> Optional[Correccion]:
    sc = clasificado.contable

    # PASO 1
    timeline = _paso1_timeline(nombre, datos)

    # PASO 1b: Lifecycle scan
    lifecycle = _paso1b_lifecycle(timeline)

    # PASO 2
    p1 = _paso2_plano1(nombre, datos)
    p2 = _paso2_plano2(nombre, datos, timeline, lifecycle=lifecycle)
    p3 = _paso2_plano3(nombre, datos, timeline)

    # PASO 3
    hips = _paso3_hipotesis(sc, p1, p2, p3, timeline=timeline)
    if not hips:
        return None

    # PASO 4
    _paso4_evaluar(hips, sc, p1, p2, p3)

    # PASO 5: Seleccionar mejor hipótesis individual
    mejor = _paso5_seleccionar(hips, sc, p2)

    # PASO 5b: Intentar composición de correcciones independientes
    # Si hay una ganadora + otras viables sobre targets DISTINTOS,
    # componer si no se contradicen.
    composicion = _paso5b_componer(hips, sc, p2, lifecycle)

    if composicion:
        # Composición gana sobre hipótesis individual
        delta_total = sum(h.delta_stock + h.delta_latas * 280 for h in composicion)
        venta_corr = sc.venta_raw + delta_total

        # Guardia de coherencia compuesta
        if venta_corr < -300:
            composicion = None
        elif sc.total_a > 0 and abs(venta_corr) > sc.total_a * 0.8:
            composicion = None

    if composicion:
        # Recalcular latas en composición: la suma ingenua de delta_latas
        # puede ser incorrecta si GENEALOGIA + PHANTOM eliminan la misma "apertura".
        # Contar cerradas reales post-composición:
        cerr_dia_reales = len(p2.cerr_a)
        cerr_noche_reales = len(p2.cerr_b)
        for h in composicion:
            if h.tipo == 'PHANTOM_DIA':
                cerr_dia_reales -= 1
            elif h.tipo == 'PHANTOM_NOCHE':
                cerr_noche_reales -= 1
            elif h.tipo == 'DUPLICADO_CERRADA':
                cerr_dia_reales -= 1
            elif h.tipo == 'GENEALOGIA_ENT_CERR':
                # Genealogía no agrega ni quita latas — reinterpreta identidad
                pass
        n_latas_reales = max(0, cerr_dia_reales - cerr_noche_reales)
        # Limpiar delta_latas de los componentes y recalcular
        for h in composicion:
            h.delta_latas = 0
        # El delta de latas va en el total, no por componente
        # (se aplica al total final del día)

        # Clasificar: la composición hereda la banda más baja de sus componentes
        tipos_bandas = [_paso6_clasificar(h, sc) for h in composicion]
        banda_orden = {'CONFIRMADO': 0, 'FORZADO': 1, 'ESTIMADO': 2}
        peor_banda = max(tipos_bandas, key=lambda tb: banda_orden.get(tb[1].value, 99))
        tipo, banda, conf = peor_banda[0], peor_banda[1], min(tb[2] for tb in tipos_bandas)

        delta_total = sum(h.delta_stock + h.delta_latas * 280 for h in composicion)
        venta_corr = sc.venta_raw + delta_total

        motivos = ' + '.join(f'[{h.tipo}]{h.accion[:40]}' for h in composicion)
        planos = ' | '.join(f'{h.tipo}:fav={h.planos_favor}' for h in composicion)

        return Correccion(
            nombre_norm=nombre,
            venta_raw=sc.venta_raw,
            venta_corregida=venta_corr,
            delta=delta_total,
            tipo_justificacion=tipo,
            banda=banda,
            tipo_resolucion=TipoResolucion.RESUELTO_CONJUNTO,
            confianza=conf,
            motivo=f'[COMPOSICION {len(composicion)}x] {motivos} | {planos}',
        )

    # Sin composición: usar hipótesis individual
    if not mejor:
        return None

    # PASO 7 (guardia antes de clasificar, para no gastar esfuerzo)
    if not _paso7_guardia(mejor, sc):
        # Intentar la segunda mejor
        viables = [h for h in hips if h.n_contra == 0 and h is not mejor]
        viables.sort(key=lambda h: (h.independientes, h.n_favor), reverse=True)
        mejor = None
        for alt in viables:
            if _paso7_guardia(alt, sc):
                # Re-check convergence
                if alt.independientes >= 2 or getattr(alt, '_tipo_d_override', False):
                    mejor = alt
                    break
        if not mejor:
            return None

    # PASO 6
    tipo, banda, conf = _paso6_clasificar(mejor, sc)

    # Calcular venta corregida
    venta_corr = sc.venta_raw + mejor.delta_stock + mejor.delta_latas * 280

    tipo_res = TipoResolucion.RESUELTO_INDIVIDUAL
    if mejor.tipo in ('MISMATCH_LEVE', 'CONJUNTO_BILATERAL', 'DUPLICADO_CERRADA'):
        tipo_res = TipoResolucion.RESUELTO_CONJUNTO

    motivo_planos = f"P_favor={mejor.planos_favor}, P_contra={mejor.planos_contra}"

    return Correccion(
        nombre_norm=nombre,
        venta_raw=sc.venta_raw,
        venta_corregida=venta_corr,
        delta=mejor.delta_stock + mejor.delta_latas * 280,
        tipo_justificacion=tipo,
        banda=banda,
        tipo_resolucion=tipo_res,
        confianza=conf,
        motivo=f'[{mejor.tipo}] {mejor.accion} | sightings={mejor.sightings} | {motivo_planos}',
    )


# ═══════════════════════════════════════════════════════════════
# ESPECIAL: ENGINE con phantom oculto
# ═══════════════════════════════════════════════════════════════

def _revisar_engine(nombre: str, clasificado: SaborClasificado,
                    datos: DatosDia) -> Optional[Correccion]:
    sc = clasificado.contable
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    timeline = _paso1_timeline(nombre, datos)

    # Solo si hay >=2 cerradas que desaparecen
    cerr_gone = [c for c in d.cerradas if not any(abs(c - cn) <= 30 for cn in n.cerradas)]
    if len(cerr_gone) < 2:
        return None

    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    delta_ab = ab_n - ab_d

    if delta_ab <= 0:
        return None

    n_gone = len(cerr_gone)
    total_cerr_gone = sum(cerr_gone)

    # Rise esperado para N aperturas
    rise_esperado_n = total_cerr_gone - n_gone * 280
    if delta_ab >= rise_esperado_n * 0.6:
        return None  # Rise suficiente, todas las aperturas son plausibles

    # Rise insuficiente -> buscar phantom
    for cerr_peso in cerr_gone:
        s = _count_sightings(cerr_peso, timeline)
        if s <= 1:
            # Verificar coherencia con N-1 aperturas
            remaining = [c for c in cerr_gone if c != cerr_peso]
            rise_n1 = sum(remaining) - (n_gone - 1) * 280
            # Verificar que el rise real sea coherente con N-1
            if rise_n1 > 0 and abs(delta_ab - rise_n1) <= max(500, rise_n1 * 0.25):
                # Phantom confirmado por P1 + P2
                venta_corr = sc.venta_raw - cerr_peso
                # Ajustar latas: si era N latas, ahora N-1
                if sc.n_cerr_a > sc.n_cerr_b:
                    venta_corr += 280  # ahorramos un ajuste de lata
                    delta_total = -cerr_peso + 280
                else:
                    delta_total = -cerr_peso

                return Correccion(
                    nombre_norm=nombre,
                    venta_raw=sc.venta_raw,
                    venta_corregida=venta_corr,
                    delta=delta_total,
                    tipo_justificacion=TipoJustificacion.A,
                    banda=Banda.CONFIRMADO,
                    tipo_resolucion=TipoResolucion.RESUELTO_INDIVIDUAL,
                    confianza=0.85,
                    motivo=f'[ENGINE_PHANTOM] Cerr {int(cerr_peso)} phantom (1-sighting). '
                           f'Rise {delta_ab}g insuficiente para {n_gone} aperturas. '
                           f'Coherente con {n_gone-1}. P_favor=[P1, P2]',
                )
    return None


# ═══════════════════════════════════════════════════════════════
# ESPECIAL: Análisis CONJUNTO cross-sabor
# ═══════════════════════════════════════════════════════════════

def _analisis_conjunto(correcciones: List[Correccion]):
    """
    Post-procesamiento: busca patrones cross-sabor.
    Modifica correcciones in-place si encuentra patrón.
    """
    # Patrón 1: Omisiones DIA sistemáticas
    omisiones_dia = [c for c in correcciones if 'OMISION_DIA' in c.motivo]
    if len(omisiones_dia) >= 2:
        for c in omisiones_dia:
            c.grupo_conjunto = 'OMISION_DIA_SISTEMATICA'
            if c.tipo_justificacion != TipoJustificacion.A:
                c.tipo_justificacion = TipoJustificacion.A
                c.banda = Banda.CONFIRMADO
                c.motivo += ' | ELEVADO por patron cross-sabor (>=2 omisiones DIA)'

    # Patron 2: Phantoms DIA sistematicos
    phantoms_dia = [c for c in correcciones if 'PHANTOM_DIA' in c.motivo]
    if len(phantoms_dia) >= 2:
        for c in phantoms_dia:
            c.grupo_conjunto = 'PHANTOM_DIA_SISTEMATICO'
            if c.tipo_justificacion != TipoJustificacion.A:
                c.tipo_justificacion = TipoJustificacion.A
                c.banda = Banda.CONFIRMADO
                c.motivo += ' | ELEVADO por patron cross-sabor (>=2 phantoms DIA)'


# ═══════════════════════════════════════════════════════════════
# RESULTADO
# ═══════════════════════════════════════════════════════════════

@dataclass
class EstimacionH0:
    """Mejor estimación para un sabor que quedó H0 (sin resolver)."""
    nombre_norm: str
    venta_raw: int
    venta_estimada: int
    delta: int
    hipotesis_tipo: str
    motivo: str
    n_planos_favor: int
    razon_no_confirmada: str  # por qué no convergió


@dataclass
class ResultadoC4:
    correcciones: List[Correccion] = field(default_factory=list)
    sin_resolver: List[str] = field(default_factory=list)
    estimaciones_h0: List[EstimacionH0] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def _estimar_h0(nombre: str, clasificado: SaborClasificado,
                datos: DatosDia) -> Optional[EstimacionH0]:
    """Extrae la mejor estimación para un sabor que no se pudo resolver."""
    sc = clasificado.contable
    timeline = _paso1_timeline(nombre, datos)
    lifecycle = _paso1b_lifecycle(timeline)
    p1 = _paso2_plano1(nombre, datos)
    p2 = _paso2_plano2(nombre, datos, timeline, lifecycle=lifecycle)
    p3 = _paso2_plano3(nombre, datos, timeline)
    hips = _paso3_hipotesis(sc, p1, p2, p3, timeline=timeline)
    _paso4_evaluar(hips, sc, p1, p2, p3)

    # Buscar mejor viable (sin contra)
    viables = [h for h in hips if h.n_contra == 0]
    viables.sort(key=lambda h: (h.independientes, h.n_favor), reverse=True)

    if viables:
        best = viables[0]
        venta_est = sc.venta_raw + best.delta_stock + best.delta_latas * 280
        razon = f'Solo {best.independientes} plano(s) independiente(s), requiere >=2 para confirmar'
    else:
        # Mejor con menos contra
        hips.sort(key=lambda h: (h.n_contra, -h.independientes, -h.n_favor))
        if not hips:
            return None
        best = hips[0]
        venta_est = sc.venta_raw + best.delta_stock + best.delta_latas * 280
        razon = f'{best.n_contra} plano(s) en contra: {best.planos_contra}'

    return EstimacionH0(
        nombre_norm=nombre,
        venta_raw=sc.venta_raw,
        venta_estimada=venta_est,
        delta=venta_est - sc.venta_raw,
        hipotesis_tipo=best.tipo,
        motivo=f'[{best.tipo}] {best.accion[:60]}',
        n_planos_favor=best.n_favor,
        razon_no_confirmada=razon,
    )


def resolver_escalados(datos: DatosDia, contabilidad: ContabilidadDia,
                       resultado_c3: ResultadoC3) -> ResultadoC4:
    resultado = ResultadoC4()

    # 1. Resolver escalados (SENAL + COMPUESTO)
    for nombre, clasificado in resultado_c3.escalados.items():
        corr = _resolver_sabor(nombre, clasificado, datos)
        if corr:
            resultado.correcciones.append(corr)
        else:
            resultado.sin_resolver.append(nombre)
            # Capturar mejor estimación para el reporte
            est = _estimar_h0(nombre, clasificado, datos)
            if est:
                resultado.estimaciones_h0.append(est)

    # 2. Revisar ENGINE con posibles phantoms ocultos
    engines = {k: v for k, v in resultado_c3.sabores.items()
               if v.status == StatusC3.ENGINE}
    for nombre, clasificado in engines.items():
        corr = _revisar_engine(nombre, clasificado, datos)
        if corr:
            resultado.correcciones.append(corr)

    # 3. Análisis CONJUNTO cross-sabor
    _analisis_conjunto(resultado.correcciones)

    return resultado
