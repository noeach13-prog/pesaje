"""
Calcula correcciones multi-turno y totales corregidos por dia.
Aplica regla maestra: analisis comparativo a TODOS los sabores.
"""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day
from collections import defaultdict

config = PesajeConfig.default()
xlsx = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'
shifts, ann = load_shifts_v2(xlsx)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)
day_results = aggregate_by_day(results, shifts, config, tracked_cans)
non_stock = [s for s in shifts if 'STOCK' not in s.name]
shift_map = {s.index: s for s in non_stock}

# ── Collect corrections per day ──
day_corrections = defaultdict(list)  # day -> [(flavor, engine_val, corrected_val, reason)]

for pr in results:
    day_a = extract_day_number(pr.shift_a)
    day_b = extract_day_number(pr.shift_b)
    if day_a != day_b:
        continue

    sa = sb = None
    for s in non_stock:
        if s.name == pr.shift_a: sa = s
        if s.name == pr.shift_b: sb = s
    if not sa or not sb:
        continue

    idx_a, idx_b = sa.index, sb.index
    context_indices = range(idx_a - 3, idx_b + 4)
    ctx = [(i, shift_map.get(i)) for i in context_indices if i in shift_map]

    for fname in sorted(pr.flavors.keys()):
        fr = pr.flavors[fname]
        sold = fr.sold_grams
        raw = fr.raw_sold
        obs_a = sa.flavors.get(fname)
        obs_b = sb.flavors.get(fname)
        if not obs_a or not obs_b:
            continue

        # ── DIGIT ERROR in cerrada ──
        target_day_int = int(day_a)
        for shift_side, obs, label in [(idx_a, obs_a, 'DIA'), (idx_b, obs_b, 'NOCHE')]:
            for cerr_val in obs.cerradas:
                other_cerr = []
                for ci2, s2 in ctx:
                    if ci2 == shift_side or s2 is None: continue
                    # Guard against out-of-order shifts
                    cd = extract_day_number(s2.name)
                    if cd and abs(int(cd) - target_day_int) > 2: continue
                    obs2 = s2.flavors.get(fname)
                    if obs2: other_cerr.extend(obs2.cerradas)
                if not other_cerr: continue
                closest = min(other_cerr, key=lambda x: abs(x - cerr_val))
                gap = abs(cerr_val - closest)
                if 900 < gap < 2200:
                    # Try +1000, -1000, +2000, -2000 and pick closest to history
                    candidates = [cerr_val + d for d in [1000, -1000, 2000, -2000]]
                    corrected = min(candidates, key=lambda c: abs(c - closest))
                    if abs(corrected - closest) <= 50:
                        delta = corrected - cerr_val
                        # ALWAYS use RAW as base, not engine value.
                        # The engine may have applied wrong corrections CAUSED by this error.
                        if label == 'NOCHE':
                            sold_delta = -delta  # higher NOCHE stock = lower sold
                        else:
                            sold_delta = delta   # higher DIA stock = higher sold
                        new_sold = raw + sold_delta
                        day_corrections[day_a].append((fname, sold, new_sold, f'DIGIT_ERROR {label}: cerrada {cerr_val:.0f}->{corrected:.0f}g'))

        # ── ABIERTA IMPOSIBLE ──
        for shift_side, obs, label in [(idx_a, obs_a, 'DIA'), (idx_b, obs_b, 'NOCHE')]:
            ab = obs.abierta
            if ab <= 0:
                continue  # abierta=0 is valid (no open can)
            prev_abs = []
            next_abs = []
            target_day = int(day_a)
            for ci2, s2 in ctx:
                if s2 is None: continue
                # Guard against out-of-order shifts: only use context from
                # temporally adjacent days (target-2 .. target+2)
                ctx_day_str = extract_day_number(s2.name)
                if not ctx_day_str: continue
                ctx_day = int(ctx_day_str)
                if abs(ctx_day - target_day) > 2: continue
                obs2 = s2.flavors.get(fname)
                if obs2 is None: continue
                # Use TEMPORAL day to determine prev/next, not just index.
                # This prevents out-of-order sheets (e.g., Viernes 13 NOCHE
                # at idx17 between Martes 10 and Miercoles 11) from
                # contaminating the context.
                if ctx_day <= target_day and ci2 < shift_side:
                    prev_abs.append((ci2, obs2.abierta))
                elif ctx_day >= target_day and ci2 > shift_side:
                    next_abs.append((ci2, obs2.abierta))
            if prev_abs and next_abs:
                prev_ab = prev_abs[-1][1]
                next_ab = next_abs[0][1]
                drop = prev_ab - ab
                recovery = next_ab - ab
                if drop > 2000 and recovery > 1500 and abs(prev_ab - next_ab) < 1000:
                    expected = prev_ab
                    delta = expected - ab
                    # ALWAYS use RAW as base, not engine value.
                    # The engine may have applied wrong corrections CAUSED by this error.
                    if label == 'DIA':
                        sold_delta = delta
                    else:
                        sold_delta = -delta
                    new_sold = raw + sold_delta
                    day_corrections[day_a].append((fname, sold, new_sold, f'ABIERTA_IMPOSIBLE {label}: {ab:.0f}->{expected:.0f}g'))

# ── NAME INCONSISTENCY (global) ──
from collections import Counter
flavor_shifts_map = defaultdict(set)
for s in non_stock:
    for fname in s.flavors:
        flavor_shifts_map[fname].add(s.index)

name_pairs = []
checked = set()
for f1 in sorted(flavor_shifts_map.keys()):
    for f2 in sorted(flavor_shifts_map.keys()):
        if f1 >= f2: continue
        if (f1, f2) in checked: continue
        checked.add((f1, f2))
        if len(f1) < 4 or len(f2) < 4: continue
        if abs(len(f1) - len(f2)) <= 2:
            common = sum(1 for a, b in zip(f1, f2) if a == b)
            if common >= min(len(f1), len(f2)) - 2 and common >= 4:
                overlap = flavor_shifts_map[f1] & flavor_shifts_map[f2]
                if not overlap:
                    name_pairs.append((f1, f2))

# For name pairs, find days where they affect results
for f1, f2 in name_pairs:
    for pr in results:
        day_a = extract_day_number(pr.shift_a)
        day_b = extract_day_number(pr.shift_b)
        if day_a != day_b: continue
        has_f1 = f1 in pr.flavors
        has_f2 = f2 in pr.flavors
        if has_f1 and has_f2:
            # Both appear in same period = both in separate shifts = name inconsistency
            s1 = pr.flavors[f1].sold_grams
            s2 = pr.flavors[f2].sold_grams
            combined = s1 + s2  # net effect
            # f1 should be 0, f2 should be 0, combined should be the real sale
            day_corrections[day_a].append((f'{f1}/{f2}', s1 + s2, combined, f'NOMBRE: {f1}+{f2} combinados (neto={combined:.0f}g, sin cambio en total)'))

# ── Output corrected totals ──
print('='*140)
print('REPORTE FINAL: TOTALES POR DIA CON CORRECCIONES MULTI-TURNO')
print('='*140)
print(f'\n{"DIA":>4} {"STOCK_ENGINE":>13} {"AJUSTE":>10} {"STOCK_CORR":>12} {"VDP":>8} {"LATAS":>6} {"LID":>8} {"TOTAL_CORR":>12} {"N_CORR":>7}')
print('-'*90)

grand_engine = grand_corr = grand_vdp = grand_lid = grand_total_e = grand_total_c = 0

for d in sorted(day_results, key=lambda x: int(x.day_label)):
    dn = d.day_label
    engine_stock = d.stock_sold_total
    vdp = d.vdp_grams
    lid = d.lid_discount_grams
    n_latas = d.opened_cans

    # Calculate adjustment
    adjustment = 0
    corrs = day_corrections.get(dn, [])
    # Deduplicate: same flavor can have multiple corrections
    # Apply each unique correction
    applied = {}
    for (flavor, old_val, new_val, reason) in corrs:
        if 'NOMBRE' in reason:
            continue  # name pair doesn't change total (they cancel out)
        key = (flavor, reason.split(':')[0])
        if key not in applied:
            applied[key] = (old_val, new_val, reason)
            adjustment += (new_val - old_val)

    corrected_stock = engine_stock + adjustment
    total_engine = d.day_sold_total
    total_corrected = corrected_stock + vdp - lid

    grand_engine += engine_stock
    grand_corr += corrected_stock
    grand_vdp += vdp
    grand_lid += lid
    grand_total_e += total_engine
    grand_total_c += total_corrected

    n_corr = len(applied)
    marker = ' *' if n_corr > 0 else ''
    print(f'{dn:>4} {engine_stock:>13.0f} {adjustment:>+10.0f} {corrected_stock:>12.0f} {vdp:>8.0f} {n_latas:>6} {lid:>8.0f} {total_corrected:>12.0f} {n_corr:>7}{marker}')

print('-'*90)
print(f'{"TOT":>4} {grand_engine:>13.0f} {grand_corr-grand_engine:>+10.0f} {grand_corr:>12.0f} {grand_vdp:>8.0f} {"":>6} {grand_lid:>8.0f} {grand_total_c:>12.0f}')
print(f'\nDiferencia total engine vs corregido: {grand_total_c - grand_total_e:+.0f}g')

# Detail corrections per day
print(f'\n{"="*140}')
print('DETALLE DE CORRECCIONES POR DIA')
print(f'{"="*140}')
for dn in sorted(day_corrections.keys(), key=lambda x: x.zfill(3)):
    corrs = day_corrections[dn]
    if not corrs:
        continue
    print(f'\n--- DIA {dn} ---')
    for (flavor, old_val, new_val, reason) in corrs:
        delta = new_val - old_val
        print(f'  {flavor:<25} {old_val:>8.0f} -> {new_val:>8.0f}  ({delta:>+8.0f}g)  {reason}')
