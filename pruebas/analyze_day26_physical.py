"""Análisis día 26 con reglas físicas aplicadas a TODOS los sabores."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import (build_timeline, find_resets, generate_periods, extract_day_number)
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

INPUT = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'
TARGET = '26'

config = PesajeConfig.default()
shifts, annotations = load_shifts_v2(INPUT)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)
day_results = aggregate_by_day(results, shifts, config, tracked_cans)

# Find target day
day_obj = None
for d in day_results:
    if d.day_label == TARGET:
        day_obj = d
        break

# Find period-level results
day_periods = []
for r in results:
    da = extract_day_number(r.shift_a)
    db = extract_day_number(r.shift_b)
    if da == TARGET and db == TARGET:
        day_periods.append(r)

# Find shifts for this day
day_shifts = [s for s in shifts if extract_day_number(s.name) == TARGET and 'STOCK' not in s.name]
day_indices = set(s.index for s in day_shifts)
shift_a = min(day_indices)  # DIA
shift_b = max(day_indices)  # NOCHE

# Get day number from shift name for temporal adjacency
import re
def get_day_num(shift_name):
    m = re.search(r'(\d+)', shift_name)
    return int(m.group(1)) if m else None

target_day_num = 26

# WIDE context: all non-STOCK shifts within ±5 days
wide_range_shifts = []
for s in shifts:
    if 'STOCK' in s.name:
        continue
    dn = get_day_num(s.name)
    if dn and abs(dn - target_day_num) <= 5:
        wide_range_shifts.append(s)
wide_range_shifts.sort(key=lambda s: s.index)
wide_indices = set(s.index for s in wide_range_shifts)

print("=" * 130)
print(f"DIA {TARGET} — ANALISIS REGLAS FISICAS SOBRE TODOS LOS SABORES")
print(f"Turnos: idx{shift_a} (DIA) -> idx{shift_b} (NOCHE)")
print(f"Contexto: {len(wide_range_shifts)} turnos (días {target_day_num-5}-{target_day_num+5})")
print("=" * 130)

# Collect ALL flavor names from day shifts
all_flavors = set()
for s in day_shifts:
    all_flavors.update(s.flavors.keys())

# Get the period result for easy access
pr = day_periods[0]

# ── Apply 4 physical rules to EVERY flavor ──
corrections = {}  # flavor -> (corrected_sold, rule, explanation)

for fname in sorted(all_flavors):
    fr = pr.flavors.get(fname)
    engine_sold = round(fr.sold_grams) if fr else 0
    raw_sold = round(fr.raw_sold) if fr else 0

    # Get raw observations for DIA and NOCHE
    obs_a = None  # DIA
    obs_b = None  # NOCHE
    for s in day_shifts:
        if s.index == shift_a:
            obs_a = s.flavors.get(fname)
        if s.index == shift_b:
            obs_b = s.flavors.get(fname)

    if not obs_a and not obs_b:
        continue

    # Build full timeline for this flavor
    timeline = []
    for s in wide_range_shifts:
        obs = s.flavors.get(fname)
        if obs:
            total = obs.abierta + sum(obs.cerradas) + sum(obs.entrantes)
            timeline.append({
                'idx': s.index,
                'name': s.name,
                'ab': obs.abierta,
                'cerr': list(obs.cerradas),
                'ent': list(obs.entrantes),
                'total': total,
                'is_day': s.index in day_indices,
            })

    # ── RULE 1: Abierta imposible ──
    # If abierta goes UP between DIA->NOCHE without a cerrada opening
    if obs_a and obs_b:
        ab_a = obs_a.abierta
        ab_b = obs_b.abierta
        n_cerr_a = len(obs_a.cerradas)
        n_cerr_b = len(obs_b.cerradas)

        if ab_b > ab_a + 50:  # abierta rose beyond measurement noise
            # Did a cerrada get opened? (fewer cerradas in B than A)
            cerrada_opened = n_cerr_a > n_cerr_b
            if not cerrada_opened:
                # IMPOSSIBLE: abierta can't rise without opening a cerrada
                # Find the correct abierta from surrounding context
                # Look for abierta values before and after day 26
                ab_before = []
                ab_after = []
                for t in timeline:
                    if t['idx'] < shift_a:
                        ab_before.append((t['idx'], t['ab'], t['name']))
                    elif t['idx'] > shift_b:
                        ab_after.append((t['idx'], t['ab'], t['name']))

                # The correct abierta is the one consistent with the trend
                # If ab_a is consistent with before, ab_b is the error
                # If ab_b is consistent with after, ab_a is the error
                explanation_parts = []
                explanation_parts.append(f"  AB_A={ab_a:.0f} (DIA), AB_B={ab_b:.0f} (NOCHE), diff={ab_b-ab_a:+.0f}")

                if ab_before:
                    last_before = ab_before[-1]
                    explanation_parts.append(f"  Antes: idx{last_before[0]} {last_before[2]} ab={last_before[1]:.0f}")
                if ab_after:
                    first_after = ab_after[0]
                    explanation_parts.append(f"  Después: idx{first_after[0]} {first_after[2]} ab={first_after[1]:.0f}")

                # Determine which abierta is wrong
                # If NOCHE ab is closer to the context, DIA is wrong (and vice versa)
                ref_abs = [t[1] for t in ab_before[-2:]] + [t[1] for t in ab_after[:2]]

                if ref_abs:
                    avg_context_ab = sum(ref_abs) / len(ref_abs)
                    err_a = abs(ab_a - avg_context_ab)
                    err_b = abs(ab_b - avg_context_ab)

                    if err_b < err_a:
                        # DIA abierta is wrong -> use NOCHE as reference
                        # True sold = total_A_corrected - total_B
                        # But we use RAW as base and correct
                        corrected_ab_a = ab_b  # DIA should have been same as NOCHE (or close)
                        # Actually: venta = stock_A - stock_B, with corrected stock_A
                        # Simpler: venta_real ~ raw - (ab_a - corrected_ab_a)
                        # raw used ab_a. Correct ab_a to something consistent.
                        # For now: corrected_sold = raw + (ab_a - corrected_ab_a) ... no
                        # raw_sold = total_A - total_B (using observed values)
                        # The error is that ab_a is too LOW (NOCHE is higher, so DIA must have been higher too)
                        # Wait - ab_b > ab_a means NOCHE abierta is HIGHER than DIA
                        # If DIA is the error: real ab_a should be higher -> stock_A increases -> sold increases
                        # corrected = raw + (correct_ab_a - observed_ab_a)
                        # But actually the impossible case is ab going UP. Context says DIA was wrong (too low)
                        # Let me think again: if ab_b > ab_a and no cerrada opened, someone recorded wrong
                        # If context says ab should be around avg_context_ab:
                        # If ab_a is the outlier (far from context), then DIA was recorded wrong
                        # If ab_b is the outlier, NOCHE was recorded wrong
                        explanation_parts.append(f"  -> DIA abierta parece incorrecta (lejos del contexto)")
                        explanation_parts.append(f"  -> Contexto promedio ab={avg_context_ab:.0f}")
                        corrections[fname] = {
                            'rule': 'AB_IMP',
                            'engine': engine_sold,
                            'raw': raw_sold,
                            'explanation': '\n'.join(explanation_parts),
                            'issue': f'DIA ab={ab_a:.0f} debería ser ~{avg_context_ab:.0f}',
                        }
                    else:
                        # NOCHE abierta is wrong -> it should be lower
                        # Real sold = raw - (observed_ab_b - correct_ab_b)
                        # correct_ab_b ~ ab_a - (normal_daily_consumption)
                        explanation_parts.append(f"  -> NOCHE abierta parece incorrecta (lejos del contexto)")
                        explanation_parts.append(f"  -> Contexto promedio ab={avg_context_ab:.0f}")
                        # For NOCHE wrong, the correct ab_b should be lower
                        # sold_raw was calculated with inflated ab_b -> sold was too negative
                        # Real sold ~ ab_a - correct_ab_b + cerr changes
                        corrections[fname] = {
                            'rule': 'AB_IMP',
                            'engine': engine_sold,
                            'raw': raw_sold,
                            'explanation': '\n'.join(explanation_parts),
                            'issue': f'NOCHE ab={ab_b:.0f} debería ser ~{avg_context_ab:.0f}',
                        }

    # ── RULE 2: Cerrada fantasma ──
    # Cerrada appears in DIA, disappears in NOCHE, but abierta didn't jump
    if obs_a and obs_b:
        cerr_a = set()
        for c in obs_a.cerradas:
            cerr_a.add(round(c))
        cerr_b = set()
        for c in obs_b.cerradas:
            cerr_b.add(round(c))

        ab_a = obs_a.abierta
        ab_b = obs_b.abierta

        # Check each cerrada in A that's not in B (within tolerance)
        disappeared = []
        for ca in obs_a.cerradas:
            found_in_b = False
            for cb in obs_b.cerradas:
                if abs(ca - cb) <= 100:  # reasonable tolerance
                    found_in_b = True
                    break
            if not found_in_b:
                # Did abierta jump by this amount? (cerrada was opened and consumed)
                # If cerrada was opened: ab_b should be much higher than ab_a
                # Or more precisely, the opened cerrada contributes to ab
                # If ab didn't jump proportionally, cerrada wasn't opened
                disappeared.append(ca)

        for dc in disappeared:
            # Was this cerrada a 1-sighting? Check tracker
            is_1_sighting = True
            for can in tracked_cans.get(fname, []):
                for sg in can.sightings:
                    if sg.shift_index == shift_a and abs(sg.weight - dc) <= 50:
                        if len(can.sightings) > 1:
                            is_1_sighting = False
                        break

            if is_1_sighting and dc > 5000:  # full cerrada that appeared once
                # Check if abierta compensates
                ab_jump = ab_b - ab_a
                if ab_jump < dc * 0.5:  # abierta didn't absorb the cerrada
                    if fname not in corrections:  # don't overwrite AB_IMP
                        corrections[fname] = {
                            'rule': 'CERR_PHANTOM',
                            'engine': engine_sold,
                            'raw': raw_sold,
                            'explanation': f"  Cerrada {dc:.0f}g en DIA, desaparece en NOCHE\n"
                                         f"  Abierta: {ab_a:.0f}->{ab_b:.0f} (jump={ab_jump:+.0f})\n"
                                         f"  Cerrada nunca fue abierta ni vendida, 1-sighting\n"
                                         f"  Venta real = raw - cerrada = {raw_sold} - {dc:.0f} = {raw_sold - round(dc)}",
                            'corrected': raw_sold - round(dc),
                            'issue': f'cerrada {dc:.0f}g 1-sighting fantasma',
                        }

    # ── RULE 3: Error de dígito en cerrada ──
    # Already handled by engine (KITKAT) - check if engine already applied

    # ── RULE 4: Nombre inconsistente ──
    # Would need fuzzy matching - skip for now, handle manually if needed

# ── Print full analysis ──
print(f"\n{'='*130}")
print("SABORES CON VIOLACION DE REGLA FISICA:")
print(f"{'='*130}")

if not corrections:
    print("  Ninguno detectado")
else:
    for fname, info in sorted(corrections.items()):
        print(f"\n--- {fname} [{info['rule']}] ---")
        print(f"  Engine: {info['engine']}g, RAW: {info['raw']}g")
        print(info['explanation'])

# ── Now print full multi-turn for ALL flagged flavors + those with engine != raw ──
flagged = set(corrections.keys())
# Also flag negative sold, very high sold, or engine != raw
for fname in sorted(all_flavors):
    fr = pr.flavors.get(fname)
    if not fr:
        continue
    engine = round(fr.sold_grams)
    raw = round(fr.raw_sold)
    if engine < -50 or engine > 5500 or abs(engine - raw) > 100:
        flagged.add(fname)

print(f"\n{'='*130}")
print(f"TIMELINE MULTI-TURNO PARA {len(flagged)} SABORES FLAGGED:")
print(f"{'='*130}")

for fname in sorted(flagged):
    fr = pr.flavors.get(fname)
    engine = round(fr.sold_grams) if fr else 0
    raw = round(fr.raw_sold) if fr else 0
    rule_tag = f" [{corrections[fname]['rule']}]" if fname in corrections else ""
    print(f"\n--- {fname} (engine={engine}, raw={raw}){rule_tag} ---")
    for s in wide_range_shifts:
        obs = s.flavors.get(fname)
        if obs:
            cerr_str = ', '.join(f'{c:.0f}' for c in obs.cerradas)
            ent_str = ', '.join(f'{e:.0f}' for e in obs.entrantes)
            day_marker = ' <<<' if s.index in day_indices else ''
            total = obs.abierta + sum(obs.cerradas) + sum(obs.entrantes)
            print(f"  idx{s.index:>2} {s.name:<30} ab={obs.abierta:<8.0f} "
                  f"cerr=[{cerr_str:<20}] ent=[{ent_str:<15}] tot={total:<8.0f}{day_marker}")

# ── Corrected totals ──
print(f"\n{'='*130}")
print("CALCULO TOTAL DIA 26 CORREGIDO:")
print(f"{'='*130}")

stock_total = 0
corrections_applied = []
for fname in sorted(all_flavors):
    fr = pr.flavors.get(fname)
    engine = round(fr.sold_grams) if fr else 0

    if fname in corrections:
        c = corrections[fname]
        if 'corrected' in c:
            corrected = c['corrected']
        else:
            corrected = engine  # couldn't auto-correct, keep engine
        delta = corrected - engine
        if delta != 0:
            corrections_applied.append((fname, engine, corrected, delta, c['rule']))
        stock_total += corrected
    else:
        stock_total += engine

print(f"\n  Correcciones aplicadas:")
for fname, old, new, delta, rule in corrections_applied:
    print(f"    {fname:<25} {old:>8} -> {new:>8} ({delta:+d}) [{rule}]")

print(f"\n  Stock-based sold (engine):  {round(day_obj.stock_sold_total):>8}g")
print(f"  Stock-based sold (corr):   {stock_total:>8}g")
print(f"  VDP:                        {round(day_obj.vdp_grams):>8}g")
print(f"  Lid discount:               {round(day_obj.lid_discount_grams):>8}g ({day_obj.opened_cans} latas)")
print(f"  -----------------------------------")
total = stock_total + round(day_obj.vdp_grams) - round(day_obj.lid_discount_grams)
print(f"  TOTAL DÍA 26:              {total:>8}g")
