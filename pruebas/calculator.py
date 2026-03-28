"""
calculator.py — Sales calculation + comprehensive anomaly detection.

Formula:
  venta_neta = total_A + new_entrantes_B - total_B - ajuste_latas

Where:
  total_X         = abierta + celiaca + sum(cerradas) + sum(entrantes)
  new_entrantes_B = entrantes in B that have NO match in A (within TIGHT tolerance)
  ajuste_latas    = max(0, n_cerradas_A - n_cerradas_B) * 280

Anomaly types
─────────────
  REGLAS DURAS (imposibles lógicos/físicos)
  T10  Peso negativo en cualquier slot
  T11  Lata cerrada/entrante > MAX_LATA (excede peso máximo físico)
  T12  Abierta aumenta entre turnos sin apertura de cerrada
  T13  Venta neta excede el stock disponible

  REGLAS DE PERÍODO ÚNICO (ya existentes)
  T3   Diferencia baja entre cerradas consecutivas (50–200 g)
  T4   Diferencia baja entrante A vs cerrada B (50–200 g)
  T7   Abierta > 7500 g (posible error de ingreso)
  T8   Venta muy negativa sin entrante documentado
  T9   Nueva lata cerrada sin entrante documentado

  REGLAS DE VENTANA 3 TURNOS (ya existentes)
  T1   Lata cerrada que salta un turno (A → skip → C)
  T2   Entrante que salta un turno → corrige stock
  T5   Lata cerrada desaparece sin abrirse
  T6   Entrante que nunca se materializa

  REGLAS ESTADÍSTICAS (desvíos anormales — segundo pase)
  T14  Venta fuera de ±Z_STAT σ del promedio mensual del sabor
  T15  Período extendido (gap en planilla) con venta casi nula

  REGLAS DE COMPORTAMIENTO (patrones sospechosos — tercer pase)
  T16  Abierta con peso idéntico ≥ 3 turnos consecutivos (posible copia)
  T17  Ventas negativas ≥ 3 períodos consecutivos (error sistemático)
  T18  Todas las cerradas redondeadas a múltiplos de 100 g en ≥ 4 turnos
"""
import math
from collections import defaultdict

from models import (
    ShiftData, FlavorShiftData, FlavorPeriodoResult,
    PeriodoResult, AnomalyInfo
)

# ── Tolerances & thresholds ────────────────────────────────────────────────────
TOL_TIGHT   = 20    # same lata, next shift
TOL_MEDIUM  = 50    # entrante matched as re-weighed cerrada
TOL_WIDE    = 200   # lata reappears after skipping a shift

AJUSTE_LATA = 280   # g deducted per opened closed container

# Hard rules
MAX_LATA           = 7900   # g — physically impossible above this
TOL_ABIERTA_UP     = 150    # g — tolerance for abierta increase without opening

# Single-period rules
VENTA_NEGATIVA_THRESHOLD = -300

# Statistical rules
Z_STAT          = 2.8   # z-score threshold for T14
MIN_PERIODS_STAT = 5    # minimum data points for T14
MIN_STD_STAT     = 400  # g — skip if standard deviation is too small
MIN_STOCK_STAT   = 200  # g — skip near-empty flavors for T14

# Behavioral rules
TOL_STATIC_ABIERTA  = 25   # g — "same weight" for T16
CONSEC_NEG_THRESHOLD = 3   # periods for T17
ROUND_CONSEC         = 4   # shifts for T18
ROUND_MOD            = 100 # g — rounded to nearest 100 for T18
ROUND_TOL            = 8   # g — tolerance for "rounded"


# ── Match helper ──────────────────────────────────────────────────────────────

def _match(val: float, candidates: list, tol: float) -> tuple:
    """Return (best_match_val, remaining_list) or (None, original_list)."""
    best, best_idx, best_diff = None, -1, tol + 1
    for i, c in enumerate(candidates):
        d = abs(val - c)
        if d <= tol and d < best_diff:
            best, best_idx, best_diff = c, i, d
    if best is not None:
        return best, candidates[:best_idx] + candidates[best_idx + 1:]
    return None, candidates


def _find_new_entrantes(entrantes_a: list, entrantes_b: list) -> list:
    """Return entrantes in B that are NOT present in A (within TIGHT tolerance)."""
    remaining_a = list(entrantes_a)
    new_in_b = []
    for e in entrantes_b:
        matched, remaining_a = _match(e, remaining_a, TOL_TIGHT)
        if matched is None:
            matched2, remaining_a2 = _match(e, remaining_a, TOL_MEDIUM)
            if matched2 is None:
                new_in_b.append(e)
            else:
                remaining_a = remaining_a2
    return new_in_b


# ── Per-flavor period calculation ─────────────────────────────────────────────

def _calc_flavor(name: str, fa: FlavorShiftData, fb: FlavorShiftData) -> FlavorPeriodoResult:
    new_entrantes_b = _find_new_entrantes(fa.entrantes, fb.entrantes)
    latas_abiertas  = max(0, fa.n_cerradas - fb.n_cerradas)
    ajuste          = latas_abiertas * AJUSTE_LATA

    stock_a     = fa.total
    stock_b     = fb.total
    new_ent_sum = sum(new_entrantes_b)
    venta_raw   = stock_a + new_ent_sum - stock_b - ajuste

    return FlavorPeriodoResult(
        name=name,
        a_abierta=fa.abierta, a_celiaca=fa.celiaca,
        a_cerradas=list(fa.cerradas), a_entrantes=list(fa.entrantes),
        a_total=stock_a,
        b_abierta=fb.abierta, b_celiaca=fb.celiaca,
        b_cerradas=list(fb.cerradas), b_entrantes=list(fb.entrantes),
        b_total=stock_b,
        new_entrantes_b=new_entrantes_b,
        latas_abiertas=latas_abiertas,
        ajuste=ajuste,
        stock_a_corr=stock_a,
        stock_b_corr=stock_b,
        venta_neta=venta_raw,
        anomalies=[],
    )


# ══════════════════════════════════════════════════════════════════════════════
# PASE 1 — Reglas duras + reglas de período único
# ══════════════════════════════════════════════════════════════════════════════

def _detect_hard_rules(res: FlavorPeriodoResult):
    """T10–T13: imposibles lógicos o físicos."""

    # T10 — Peso negativo
    slots = [
        (res.a_abierta,  'abierta A'),
        (res.a_celiaca,  'celiaca A'),
        (res.b_abierta,  'abierta B'),
        (res.b_celiaca,  'celiaca B'),
    ]
    for v in res.a_cerradas:
        slots.append((v, f'cerrada A ~{v:.0f}g'))
    for v in res.b_cerradas:
        slots.append((v, f'cerrada B ~{v:.0f}g'))
    for v in res.a_entrantes:
        slots.append((v, f'entrante A ~{v:.0f}g'))
    for v in res.b_entrantes:
        slots.append((v, f'entrante B ~{v:.0f}g'))

    for val, label in slots:
        if val < 0:
            res.anomalies.append(AnomalyInfo(
                tipo=10,
                message=f"PESO NEGATIVO en {label}: {val:.0f}g — error de ingreso imposible",
                severity='error',
            ))

    # T11 — Peso imposiblemente alto
    for val in res.a_cerradas + res.b_cerradas + res.a_entrantes + res.b_entrantes:
        if val > MAX_LATA:
            res.anomalies.append(AnomalyInfo(
                tipo=11,
                message=(
                    f"PESO IMPOSIBLE: ~{val:.0f}g excede el máximo de una lata "
                    f"({MAX_LATA}g) — verificar dígitos"
                ),
                severity='error',
            ))

    # T12 — Abierta aumenta sin apertura de cerrada
    if (
        res.latas_abiertas == 0
        and res.a_abierta > 100
        and res.b_abierta > res.a_abierta + TOL_ABIERTA_UP
    ):
        inc = res.b_abierta - res.a_abierta
        res.anomalies.append(AnomalyInfo(
            tipo=12,
            message=(
                f"ABIERTA AUMENTA SIN APERTURA: A={res.a_abierta:.0f}g → "
                f"B={res.b_abierta:.0f}g (+{inc:.0f}g) sin latas abiertas — "
                f"verificar si se abrió una cerrada sin registrar"
            ),
            severity='error',
        ))

    # T13 — Venta excede stock disponible
    available = res.a_total + sum(res.new_entrantes_b)
    if res.a_total > 200 and res.venta_neta > available + 150:
        res.anomalies.append(AnomalyInfo(
            tipo=13,
            message=(
                f"VENTA IMPOSIBLE: {res.venta_neta:.0f}g > stock disponible "
                f"{available:.0f}g — los números no cuadran"
            ),
            severity='error',
        ))


def _detect_single_period_anomalies(res: FlavorPeriodoResult, dias_entre: int = 1):
    """T3, T4, T7, T8, T9 — dentro de un único período A→B."""
    a_cerr = res.a_cerradas
    b_cerr = res.b_cerradas
    a_ent  = res.a_entrantes
    b_ent  = res.b_entrantes

    # T3 — Diferencia baja entre cerradas consecutivas (50–200 g)
    remaining_b = list(b_cerr)
    for lv in a_cerr:
        m, remaining_b = _match(lv, remaining_b, TOL_WIDE)
        if m is not None:
            diff = abs(lv - m)
            if TOL_MEDIUM <= diff <= TOL_WIDE:
                res.anomalies.append(AnomalyInfo(
                    tipo=3,
                    message=(
                        f"DIFERENCIA BAJA entre latas: A ~{lv:.0f}g → B ~{m:.0f}g "
                        f"(dif. {diff:.0f}g) — verificar si es la misma lata o error de pesaje"
                    ),
                ))

    # T4 — Diferencia baja entrante de A vs cerrada de B (50–200 g)
    remaining_b2 = list(b_cerr)
    for ev in a_ent:
        m, remaining_b2 = _match(ev, remaining_b2, TOL_WIDE)
        if m is not None:
            diff = abs(ev - m)
            if TOL_MEDIUM <= diff <= TOL_WIDE:
                res.anomalies.append(AnomalyInfo(
                    tipo=4,
                    message=(
                        f"DIFERENCIA BAJA: entrante de A ~{ev:.0f}g vs cerrada B ~{m:.0f}g "
                        f"(dif. {diff:.0f}g) — verificar si es la misma lata"
                    ),
                ))

    # T7 — Abierta > 7500 g
    for stock_val, label in [(res.a_abierta, 'A'), (res.b_abierta, 'B')]:
        if stock_val > 7500:
            res.anomalies.append(AnomalyInfo(
                tipo=7,
                message=(
                    f"ABIERTA MUY GRANDE en turno {label}: {stock_val:.0f}g "
                    f"(>7500g — posible error de ingreso)"
                ),
                severity='error',
            ))

    # T8 — Venta muy negativa sin entrante documentado
    if res.venta_neta < VENTA_NEGATIVA_THRESHOLD and not res.new_entrantes_b:
        res.anomalies.append(AnomalyInfo(
            tipo=8,
            message=(
                f"VENTA NETA MUY NEGATIVA: {res.venta_neta:.0f}g sin entrante documentado "
                f"— posible lata nueva no registrada"
            ),
            severity='error',
        ))

    # T9 — Nueva lata cerrada sin entrante que la justifique
    remaining_a_cerr = list(a_cerr)
    remaining_a_ent  = list(a_ent)
    unmatched_new    = []
    for lv in b_cerr:
        m1, remaining_a_cerr = _match(lv, remaining_a_cerr, TOL_WIDE)
        if m1 is not None:
            continue
        m2, remaining_a_ent = _match(lv, remaining_a_ent, TOL_MEDIUM)
        if m2 is not None:
            continue
        m3, _ = _match(lv, res.new_entrantes_b, TOL_MEDIUM)
        if m3 is not None:
            continue
        unmatched_new.append(lv)

    for lv in unmatched_new:
        res.anomalies.append(AnomalyInfo(
            tipo=9,
            message=(
                f"NUEVA LATA CERRADA ~{lv:.0f}g SIN ENTRANTE DOCUMENTADO "
                f"— verificar si hay error de carga o entrante omitido"
            ),
            severity='error',
        ))


# ══════════════════════════════════════════════════════════════════════════════
# PASE 1b — Ventana de 3 turnos (T1, T2, T5, T6)
# ══════════════════════════════════════════════════════════════════════════════

def _detect_window_anomalies(shifts: list, periods: list):
    """
    Anomalies requiring 3-shift sliding windows (T1, T2, T5, T6).
    Mutates anomaly lists in period results.
    """
    shift_by_name = {s.name: s for s in shifts}
    period_by_a   = {p.turno_a_name: p for p in periods}

    for period_ab in periods:
        name_a  = period_ab.turno_a_name
        name_b  = period_ab.turno_b_name
        period_bc = period_by_a.get(name_b)
        if period_bc is None:
            continue
        name_c = period_bc.turno_b_name

        shift_a = shift_by_name.get(name_a)
        shift_b = shift_by_name.get(name_b)
        shift_c = shift_by_name.get(name_c)
        if not (shift_a and shift_b and shift_c):
            continue

        all_flavors = set(shift_a.flavors) | set(shift_b.flavors) | set(shift_c.flavors)

        for fname in all_flavors:
            fa = shift_a.flavors.get(fname)
            fb = shift_b.flavors.get(fname)
            fc = shift_c.flavors.get(fname)
            if not fa:
                continue

            res_ab = period_ab.flavors.get(fname)
            res_bc = period_bc.flavors.get(fname) if period_bc else None

            # T1 — Lata cerrada que salta un turno
            if fb:
                for lv in fa.cerradas:
                    in_b = _match(lv, list(fb.cerradas), TOL_TIGHT)[0] is not None
                    if not in_b and fc:
                        in_c = _match(lv, list(fc.cerradas), TOL_WIDE)[0] is not None
                        if in_c:
                            note = ("POSIBLE ERROR HUMANO — 1 lata menos"
                                    if fa.n_cerradas - fb.n_cerradas == 1
                                    else "verificar carga")
                            msg = (
                                f"LATA CERRADA ~{lv:.0f}g: figura en A — "
                                f"NO figura en B — reaparece en C ({note})"
                            )
                            if res_ab:
                                res_ab.anomalies.append(AnomalyInfo(tipo=1, message=msg))

            # T2 — Entrante que salta un turno
            if fb and fc:
                for ev in fa.entrantes:
                    if ev < 1000:
                        continue
                    in_b_ent  = _match(ev, list(fb.entrantes), TOL_MEDIUM)[0] is not None
                    in_b_cerr = _match(ev, list(fb.cerradas),  TOL_MEDIUM)[0] is not None
                    if not in_b_ent and not in_b_cerr and fb.n_cerradas < fa.n_cerradas + 1:
                        in_c_cerr = _match(ev, list(fc.cerradas), TOL_WIDE)[0] is not None
                        if in_c_cerr:
                            msg = (
                                f"ENTRANTE ~{ev:.0f}g: registrada en A — "
                                f"NO figura en B — reaparece como cerrada en C "
                                f"→ lata contabilizada en este período"
                            )
                            if res_ab:
                                res_ab.anomalies.append(AnomalyInfo(
                                    tipo=2, message=msg,
                                    corr_stock_a=ev, corr_stock_b=ev,
                                ))
                                res_ab.stock_a_corr += ev
                                res_ab.stock_b_corr += ev
                                new_ent_sum = sum(res_ab.new_entrantes_b)
                                res_ab.venta_neta = (
                                    res_ab.stock_a_corr + new_ent_sum
                                    - res_ab.stock_b_corr - res_ab.ajuste
                                )

            # T5 — Lata cerrada desaparece sin justificación
            if fb and fc:
                for lv in fa.cerradas:
                    in_b = (_match(lv, list(fb.cerradas), TOL_WIDE)[0] is not None
                            or _match(lv, list(fb.entrantes), TOL_MEDIUM)[0] is not None)
                    if not in_b:
                        in_c = (_match(lv, list(fc.cerradas), TOL_WIDE)[0] is not None
                                or _match(lv, list(fc.entrantes), TOL_MEDIUM)[0] is not None)
                        if not in_c:
                            msg = (
                                f"LATA CERRADA ~{lv:.0f}g: desaparece en B y C "
                                f"sin ser abierta — verificar si fue consumida sin registro"
                            )
                            if res_ab:
                                res_ab.anomalies.append(AnomalyInfo(
                                    tipo=5, message=msg, severity='error'))

            # T6 — Entrante que nunca se materializa
            if fb and fc:
                for ev in fa.entrantes:
                    in_b = (_match(ev, list(fb.cerradas),  TOL_MEDIUM)[0] is not None
                            or _match(ev, list(fb.entrantes), TOL_TIGHT)[0] is not None)
                    in_c = (_match(ev, list(fc.cerradas),  TOL_WIDE)[0] is not None
                            or _match(ev, list(fc.entrantes), TOL_TIGHT)[0] is not None)
                    if not in_b and not in_c:
                        msg = (
                            f"ENTRANTE ~{ev:.0f}g: registrada en A — "
                            f"NO aparece en B ni en C — lata posiblemente perdida"
                        )
                        if res_ab:
                            res_ab.anomalies.append(AnomalyInfo(
                                tipo=6, message=msg, severity='error'))


# ══════════════════════════════════════════════════════════════════════════════
# PASE 2 — Reglas estadísticas (T14, T15)
# ══════════════════════════════════════════════════════════════════════════════

def _detect_statistical_anomalies(periods: list):
    """
    T14: venta fuera de ±Z_STAT σ del promedio mensual del sabor.
    T15: período con gap en la planilla (dias_entre > 1) y venta casi nula.
    """
    # T14 — Outlier estadístico por sabor
    flavor_ventas: dict = defaultdict(list)
    for p in periods:
        for fname, res in p.flavors.items():
            if res.a_total >= MIN_STOCK_STAT and abs(res.venta_neta) < 15000:
                flavor_ventas[fname].append(res.venta_neta)

    flavor_stats: dict = {}
    for fname, ventas in flavor_ventas.items():
        if len(ventas) < MIN_PERIODS_STAT:
            continue
        mean = sum(ventas) / len(ventas)
        std  = math.sqrt(sum((v - mean) ** 2 for v in ventas) / len(ventas))
        if std >= MIN_STD_STAT:
            flavor_stats[fname] = (mean, std)

    for p in periods:
        for fname, res in p.flavors.items():
            if fname not in flavor_stats or res.a_total < MIN_STOCK_STAT:
                continue
            mean, std = flavor_stats[fname]
            z = (res.venta_neta - mean) / std
            if abs(z) > Z_STAT:
                direction = "ALTA" if z > 0 else "BAJA"
                res.anomalies.append(AnomalyInfo(
                    tipo=14,
                    message=(
                        f"VENTA ANORMALMENTE {direction}: {res.venta_neta:.0f}g "
                        f"(media={mean:.0f}g  σ={std:.0f}g  z={z:.1f})"
                    ),
                    severity='warning',
                ))

    # T15 — Período extendido con venta mínima
    MIN_VENTA_EXTENDED = 300   # g — sale expected if stock > threshold and gap > 1
    MIN_STOCK_EXTENDED = 1200  # g — only flag if there was substantial stock in A
    for p in periods:
        if p.dias_entre <= 1:
            continue
        for fname, res in p.flavors.items():
            if (res.a_total >= MIN_STOCK_EXTENDED
                    and 0 < res.venta_neta < MIN_VENTA_EXTENDED):
                res.anomalies.append(AnomalyInfo(
                    tipo=15,
                    message=(
                        f"PERIODO CON GAP ({p.dias_entre} posiciones) Y VENTA MUY BAJA: "
                        f"{res.venta_neta:.0f}g con stock A={res.a_total:.0f}g — "
                        f"verificar si los datos son correctos"
                    ),
                    severity='warning',
                ))


# ══════════════════════════════════════════════════════════════════════════════
# PASE 3 — Reglas de comportamiento (T16, T17, T18)
# ══════════════════════════════════════════════════════════════════════════════

def _detect_behavioral_anomalies(shifts: list, periods: list):
    """
    T16: Abierta idéntica ≥ 3 turnos consecutivos (posible copia de planilla).
    T17: Ventas negativas ≥ 3 períodos consecutivos (error sistemático).
    T18: Cerradas siempre redondeadas a 100 g en ≥ 4 turnos (pesaje estimado).
    """
    period_lookup: dict = {
        (p.turno_a_name, p.turno_b_name): p for p in periods
    }
    all_fnames = set(fname for p in periods for fname in p.flavors)

    # ── T16: Abierta estática ─────────────────────────────────────────────────
    flavor_abierta: dict = defaultdict(list)  # fname -> [(shift_name, abierta)]
    for s in shifts:
        for fname, fd in s.flavors.items():
            flavor_abierta[fname].append((s.name, fd.abierta))

    for fname, timeline in flavor_abierta.items():
        i = 0
        while i <= len(timeline) - 3:
            window = [v for _, v in timeline[i:i + 3]]
            if (all(v > 100 for v in window)
                    and max(window) - min(window) <= TOL_STATIC_ABIERTA):
                # Flag on the period: shifts[i+1] → shifts[i+2]
                s_mid  = timeline[i + 1][0]
                s_next = timeline[i + 2][0]
                p = period_lookup.get((s_mid, s_next))
                if p and fname in p.flavors:
                    already = any(a.tipo == 16 for a in p.flavors[fname].anomalies)
                    if not already:
                        vals_str = ', '.join(f'{v:.0f}g' for v in window)
                        p.flavors[fname].anomalies.append(AnomalyInfo(
                            tipo=16,
                            message=(
                                f"ABIERTA ESTÁTICA: peso idéntico ({vals_str}) "
                                f"en 3 turnos consecutivos — posible copia de planilla"
                            ),
                            severity='warning',
                        ))
            i += 1

    # ── T17: Ventas negativas recurrentes ─────────────────────────────────────
    for fname in all_fnames:
        consec = 0
        for p in periods:
            res = p.flavors.get(fname)
            if res and res.venta_neta < -200:
                consec += 1
                if consec == CONSEC_NEG_THRESHOLD:
                    res.anomalies.append(AnomalyInfo(
                        tipo=17,
                        message=(
                            f"VENTAS NEGATIVAS RECURRENTES: {consec} períodos "
                            f"consecutivos con venta < -200g — posible error "
                            f"sistemático de carga para este sabor"
                        ),
                        severity='error',
                    ))
            else:
                consec = 0

    # ── T18: Pesos redondeados (pesaje estimado) ──────────────────────────────
    def _is_rounded(cerradas: list) -> bool:
        if not cerradas:
            return False
        return all(abs(c % ROUND_MOD) <= ROUND_TOL
                   or abs(c % ROUND_MOD - ROUND_MOD) <= ROUND_TOL
                   for c in cerradas)

    flavor_rounds: dict = defaultdict(list)  # fname -> [(shift_name, is_rounded)]
    for s in shifts:
        for fname, fd in s.flavors.items():
            flavor_rounds[fname].append((s.name, _is_rounded(fd.cerradas)))

    for fname, timeline in flavor_rounds.items():
        consec = 0
        for shift_name, is_rounded in timeline:
            if is_rounded:
                consec += 1
                if consec == ROUND_CONSEC:
                    # Flag on the period ending at this shift
                    for p in periods:
                        if p.turno_b_name == shift_name and fname in p.flavors:
                            already = any(a.tipo == 18 for a in p.flavors[fname].anomalies)
                            if not already:
                                p.flavors[fname].anomalies.append(AnomalyInfo(
                                    tipo=18,
                                    message=(
                                        f"PESOS REDONDEADOS: {consec} turnos consecutivos "
                                        f"con cerradas en múltiplos de {ROUND_MOD}g — "
                                        f"posible pesaje estimado en lugar de real"
                                    ),
                                    severity='warning',
                                ))
                            break
            else:
                consec = 0


# ══════════════════════════════════════════════════════════════════════════════
# Extended period detection
# ══════════════════════════════════════════════════════════════════════════════

def _detect_extended_period(shifts: list, i: int, j: int) -> tuple:
    """Return (extended, dias) using workbook index gaps."""
    gap      = shifts[j].index - shifts[i].index
    extended = gap > 1
    return extended, gap


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# V2 — Trajectory-based sold-grams calculation (additive)
# ══════════════════════════════════════════════════════════════════════════════

from models import (V2FlavorPeriodResult, V2PeriodResult, V2DayResult, TrajectoryPoint)


def calculate_sold_v2(trajectories, periods, shifts):
    """
    Calculate sold grams from inferred trajectories.
    Pure stock arithmetic. No VDP, no inference logic.

    sold(T→T+1) = inferred_total(T) - inferred_total(T+1)

    Args:
        trajectories: {flavor: [TrajectoryPoint, ...]}
        periods: [(idx_a, idx_b, is_reset), ...]
        shifts: list[RawShift]

    Returns: list[V2PeriodResult]
    """
    shift_by_index = {s.index: s for s in shifts if not s.is_stock_sheet}
    results = []

    # Build lookup: (flavor, shift_index) -> TrajectoryPoint
    tp_lookup = {}
    for flavor, traj in trajectories.items():
        for tp in traj:
            tp_lookup[(flavor, tp.shift_index)] = tp

    for idx_a, idx_b, is_reset in periods:
        sa = shift_by_index.get(idx_a)
        sb = shift_by_index.get(idx_b)
        if sa is None or sb is None:
            continue

        period = V2PeriodResult(
            shift_a=sa.name,
            shift_b=sb.name,
            is_reset=is_reset,
        )

        all_flavors = set(sa.flavors.keys()) | set(sb.flavors.keys())

        for flavor in sorted(all_flavors):
            tp_a = tp_lookup.get((flavor, idx_a))
            tp_b = tp_lookup.get((flavor, idx_b))

            # Raw sold (H0 baseline)
            raw_a = sa.flavors.get(flavor)
            raw_b = sb.flavors.get(flavor)
            raw_total_a = raw_a.total if raw_a else 0.0
            raw_total_b = raw_b.total if raw_b else 0.0
            raw_sold = raw_total_a - raw_total_b

            # Inferred sold
            inf_total_a = tp_a.inferred_total if tp_a else raw_total_a
            inf_total_b = tp_b.inferred_total if tp_b else raw_total_b
            sold = inf_total_a - inf_total_b

            # Confidence: min of both sides
            conf_a = tp_a.confidence if tp_a else 0.5
            conf_b = tp_b.confidence if tp_b else 0.5
            confidence = min(conf_a, conf_b)

            corrections_a = tp_a.corrections if tp_a else []
            corrections_b = tp_b.corrections if tp_b else []

            period.flavors[flavor] = V2FlavorPeriodResult(
                flavor=flavor,
                sold_grams=sold,
                raw_sold=raw_sold,
                confidence=confidence,
                corrections_a=corrections_a,
                corrections_b=corrections_b,
            )

        results.append(period)

    return results


LID_DISCOUNT_GRAMS = 280  # grams per opened can (lid weight)


def _count_opened_cans_by_day(tracked_cans, shifts):
    """Count can-opening events per calendar day from tracker evidence.

    A can-opening event = a tracked CanIdentity with status='opened' and
    a known opened_at shift index. The tracker only marks a can as 'opened'
    when it was live, disappeared, AND abierta jumped >1500g — meaning a
    true closed/entrant -> abierta transition occurred.

    Disappearances without abierta jump get status='gone', NOT 'opened'.
    This ensures omissions, ghosts, duplicates, phantoms, and normal
    transitions are NOT counted as openings.

    Returns: {day_label: (count, [detail_strings])}
    """
    from pairer import extract_day_number

    # Map shift_index -> day_label
    shift_day = {}
    for s in shifts:
        if not s.is_stock_sheet:
            shift_day[s.index] = extract_day_number(s.name)

    day_openings = {}  # day -> (count, details)
    for flavor, cans in tracked_cans.items():
        for can in cans:
            if can.status != 'opened' or can.opened_at is None:
                continue
            day = shift_day.get(can.opened_at)
            if day is None:
                continue
            count, details = day_openings.get(day, (0, []))
            details.append(f"{flavor} can {can.id} ({can.last_weight:.0f}g) "
                          f"opened at shift {can.opened_at}")
            day_openings[day] = (count + 1, details)

    return day_openings


def aggregate_by_day(results, shifts, config, tracked_cans=None):
    """
    Aggregate period-level stock-sold, shift-level VDP, and opening-event
    lid discount into day totals.

    TOTAL_DAY = STOCK_BASED_SOLD + VDP - (OPENED_CAN_COUNT * 280)

    All three components belong to the same calendar day.
    Nothing carries over to a different day.

    Opening events are inferred from the tracker's can lifecycle:
    a can marked 'opened' had a true closed/entrant -> abierta transition.
    Disappearances (omission, ghost, gone) are NOT openings.

    Returns: list[V2DayResult]
    """
    from pairer import (extract_day_number, group_periods_by_day,
                        group_shifts_by_day, collect_vdp_by_day,
                        generate_periods, find_resets)

    # Map period results by (shift_a_name, shift_b_name)
    result_lookup = {(r.shift_a, r.shift_b): r for r in results}
    shift_by_index = {s.index: s for s in shifts}

    # Group periods and VDP by day
    resets = find_resets(shifts)
    periods_raw = generate_periods(shifts, resets)
    day_periods = group_periods_by_day(shifts, periods_raw)
    day_shifts = group_shifts_by_day(shifts)
    day_vdp = collect_vdp_by_day(shifts, config)

    # Count opened cans per day
    day_openings = {}
    if tracked_cans is not None:
        day_openings = _count_opened_cans_by_day(tracked_cans, shifts)

    # All days that have at least one period or one shift
    all_days = sorted(set(day_periods.keys()) | set(day_shifts.keys()),
                      key=lambda d: int(d))

    day_results = []
    for day in all_days:
        dr = V2DayResult(day_label=day)
        dr.vdp_grams = day_vdp.get(day, 0.0)
        dr.shifts = [s.name for s in day_shifts.get(day, [])]

        # Opened cans and lid discount
        opened_count, opened_detail = day_openings.get(day, (0, []))
        dr.opened_cans = opened_count
        dr.opened_cans_detail = opened_detail
        dr.lid_discount_grams = opened_count * LID_DISCOUNT_GRAMS

        # Aggregate stock-sold across same-day periods
        flavor_sold = {}
        for idx_a, idx_b, _ in day_periods.get(day, []):
            sa = shift_by_index.get(idx_a)
            sb = shift_by_index.get(idx_b)
            if sa is None or sb is None:
                continue
            pr = result_lookup.get((sa.name, sb.name))
            if pr is None:
                continue
            dr.periods.append(f"{sa.name} -> {sb.name}")
            for flavor, fr in pr.flavors.items():
                flavor_sold[flavor] = flavor_sold.get(flavor, 0.0) + fr.sold_grams

        dr.flavors = flavor_sold
        dr.stock_sold_total = sum(flavor_sold.values())
        dr.day_sold_total = dr.stock_sold_total + dr.vdp_grams - dr.lid_discount_grams

        day_results.append(dr)

    return day_results


def calculate_periods(shifts: list) -> list:
    """
    For each consecutive pair of valid shifts compute PeriodoResult.
    Runs all three detection passes.
    Returns list[PeriodoResult].
    """
    periods = []

    # ── Pase 1: per-period calculation + hard rules + single-period anomalies ─
    for i in range(len(shifts) - 1):
        sa = shifts[i]
        sb = shifts[i + 1]
        extended, dias = _detect_extended_period(shifts, i, i + 1)

        periodo = PeriodoResult(
            turno_a_name=sa.name,
            turno_b_name=sb.name,
            extended=extended,
            dias_entre=dias,
            ventas_sin_peso=list(sa.ventas_sin_peso) + list(sb.ventas_sin_peso),
            consumos=list(sa.consumos)    + list(sb.consumos),
            observaciones=list(sb.observaciones),
        )

        all_flavors = set(sa.flavors.keys()) | set(sb.flavors.keys())

        for fname in sorted(all_flavors):
            fa = sa.flavors.get(fname) or FlavorShiftData(
                name=fname, abierta=0.0, celiaca=0.0, cerradas=[], entrantes=[])
            fb = sb.flavors.get(fname) or FlavorShiftData(
                name=fname, abierta=0.0, celiaca=0.0, cerradas=[], entrantes=[])

            res = _calc_flavor(fa.name, fa, fb)
            _detect_hard_rules(res)
            _detect_single_period_anomalies(res, dias)
            periodo.flavors[fname] = res

        periods.append(periodo)

    # ── Pase 1b: ventana de 3 turnos ─────────────────────────────────────────
    _detect_window_anomalies(shifts, periods)

    # ── Pase 2: reglas estadísticas ───────────────────────────────────────────
    _detect_statistical_anomalies(periods)

    # ── Pase 3: reglas de comportamiento ─────────────────────────────────────
    _detect_behavioral_anomalies(shifts, periods)

    return periods
