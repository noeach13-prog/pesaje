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


def _paso2_plano2(nombre: str, datos: DatosDia, timeline: List[Snapshot]) -> PlanoP2:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return PlanoP2([], [], [], [], [])

    from .matching import match_cerradas
    cerr_a = list(d.cerradas)
    cerr_b = list(n.cerradas)
    mr = match_cerradas(cerr_a, cerr_b)

    matches = []
    for ia, ib, pa, pb, diff in mr.matched:
        s = _count_sightings(pa, timeline)
        matches.append((pa, pb, diff, s))

    unmatched_a = [(cerr_a[ia], _count_sightings(cerr_a[ia], timeline))
                   for ia in mr.unmatched_a]
    unmatched_b = [(cerr_b[ib], _count_sightings(cerr_b[ib], timeline))
                   for ib in mr.unmatched_b]

    all_sightings = {}
    for c in cerr_a + cerr_b:
        all_sightings[c] = _count_sightings(c, timeline)

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

def _paso3_hipotesis(sc, p1: PlanoP1, p2: PlanoP2, p3: PlanoP3) -> List[Hipotesis]:
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
    # hay un MISMATCH_LEVE viable para OTRO slot del mismo episodio,
    # el caso requiere resolución conjunta → no resolver unilateralmente.
    # Condiciones: (1) mismatch no descartado por absurdo (n_contra == 0),
    # (2) mismatch toca otro slot del mismo bloque causal de cerradas,
    # (3) la unilateral no explica el cuadro completo sin resto.
    if mejor.tipo in ('PHANTOM_DIA', 'APERTURA_REAL'):
        mismatch_viable = [h for h in hips
                           if h.tipo == 'MISMATCH_LEVE'
                           and h.peso != mejor.peso
                           and h.n_contra == 0]
        if mismatch_viable:
            # Hay estructura bilateral: un slot desaparece + otro es mismatch
            # El sistema no tiene derecho a resolver uno sin el otro
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
        else:
            return None

    return mejor


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

    # PASO 2
    p1 = _paso2_plano1(nombre, datos)
    p2 = _paso2_plano2(nombre, datos, timeline)
    p3 = _paso2_plano3(nombre, datos, timeline)

    # PASO 3
    hips = _paso3_hipotesis(sc, p1, p2, p3)
    if not hips:
        return None

    # PASO 4
    _paso4_evaluar(hips, sc, p1, p2, p3)

    # PASO 5
    mejor = _paso5_seleccionar(hips, sc, p2)
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
    if mejor.tipo == 'MISMATCH_LEVE':
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
class ResultadoC4:
    correcciones: List[Correccion] = field(default_factory=list)
    sin_resolver: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

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
