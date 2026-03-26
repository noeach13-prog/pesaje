"""
Análisis multi-turno completo: TODOS los sabores, TODOS los días.
Detecta anomalías por continuidad física comparando ±3 turnos.
"""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

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

# Build index: shift_index -> shift
shift_map = {s.index: s for s in non_stock}

# ─── Multi-turn anomaly detection ───
anomalies = []

for pr in results:
    day_a = extract_day_number(pr.shift_a)
    day_b = extract_day_number(pr.shift_b)
    if day_a != day_b:
        continue  # skip cross-day periods

    # Find shift objects
    sa = sb = None
    for s in non_stock:
        if s.name == pr.shift_a:
            sa = s
        if s.name == pr.shift_b:
            sb = s
    if sa is None or sb is None:
        continue

    idx_a, idx_b = sa.index, sb.index

    for fname in sorted(pr.flavors.keys()):
        fr = pr.flavors[fname]
        sold = round(fr.sold_grams)
        raw = round(fr.raw_sold)
        diff = sold - raw
        all_corr = fr.corrections_a + fr.corrections_b

        obs_a = sa.flavors.get(fname)
        obs_b = sb.flavors.get(fname)
        if obs_a is None or obs_b is None:
            continue

        # Context: ±3 shifts
        context_indices = range(idx_a - 3, idx_b + 4)
        ctx = [(i, shift_map.get(i)) for i in context_indices if i in shift_map]

        # ── Pattern 1: Digit error in cerrada ──
        # A cerrada that differs ~1000-2000g from stable history
        for shift_side, obs, label in [(idx_a, obs_a, 'DIA'), (idx_b, obs_b, 'NOCHE')]:
            for ci, cerr_val in enumerate(obs.cerradas):
                # Check if this cerrada is wildly different from same flavor's
                # cerradas in surrounding shifts
                other_cerr = []
                for ci2, s2 in ctx:
                    if ci2 == shift_side:
                        continue
                    obs2 = s2.flavors.get(fname) if s2 else None
                    if obs2:
                        other_cerr.extend(obs2.cerradas)
                if not other_cerr:
                    continue
                # Find closest match in other shifts
                closest = min(other_cerr, key=lambda x: abs(x - cerr_val))
                gap = abs(cerr_val - closest)
                if 900 < gap < 2200:
                    # Try +1000, -1000, +2000, -2000 and pick closest to history
                    candidates = [cerr_val + d for d in [1000, -1000, 2000, -2000]]
                    corrected = min(candidates, key=lambda c: abs(c - closest))
                    if abs(corrected - closest) <= 50:
                        anomalies.append({
                            'day': day_a, 'flavor': fname, 'type': 'DIGIT_ERROR_CERRADA',
                            'shift': label, 'idx': shift_side,
                            'detail': f'cerrada {cerr_val:.0f}g -> debería ser ~{corrected:.0f}g (historial ~{closest:.0f}g)',
                            'raw_val': cerr_val, 'corrected_val': corrected,
                            'impact': corrected - cerr_val,
                            'sold_engine': sold,
                        })

        # ── Pattern 2: Impossible abierta ──
        # Abierta drops dramatically then recovers, or rises without opening
        for shift_side, obs, label, other_obs in [
            (idx_a, obs_a, 'DIA', obs_b),
            (idx_b, obs_b, 'NOCHE', obs_a)
        ]:
            ab = obs.abierta
            # Get abierta from prev and next shifts
            prev_abs = []
            next_abs = []
            for ci2, s2 in ctx:
                if s2 is None:
                    continue
                obs2 = s2.flavors.get(fname)
                if obs2 is None:
                    continue
                if ci2 < shift_side:
                    prev_abs.append((ci2, obs2.abierta))
                elif ci2 > shift_side:
                    next_abs.append((ci2, obs2.abierta))

            if prev_abs and next_abs:
                prev_ab = prev_abs[-1][1]  # closest previous
                next_ab = next_abs[0][1]   # closest next

                # Pattern: abierta drops >2000g from prev, then next is close to prev
                drop = prev_ab - ab
                recovery = next_ab - ab
                if drop > 2000 and recovery > 1500 and abs(prev_ab - next_ab) < 1000:
                    # Abierta at this shift is wrong
                    expected = prev_ab  # best estimate
                    anomalies.append({
                        'day': day_a, 'flavor': fname, 'type': 'ABIERTA_IMPOSIBLE',
                        'shift': label, 'idx': shift_side,
                        'detail': f'abierta {ab:.0f}g imposible (prev={prev_ab:.0f}, next={next_ab:.0f}). Esperado ~{expected:.0f}g',
                        'raw_val': ab, 'corrected_val': expected,
                        'impact': expected - ab,
                        'sold_engine': sold,
                    })

                # Pattern: abierta RISES >500g without cerrada opening
                rise = ab - prev_ab
                n_cerr_prev = 0
                n_cerr_curr = len(obs.cerradas)
                if prev_abs:
                    prev_s = shift_map.get(prev_abs[-1][0])
                    if prev_s:
                        prev_obs = prev_s.flavors.get(fname)
                        if prev_obs:
                            n_cerr_prev = len(prev_obs.cerradas)
                if rise > 500 and n_cerr_curr >= n_cerr_prev:
                    # Abierta rose but no cerrada was opened (count didn't decrease)
                    anomalies.append({
                        'day': day_a, 'flavor': fname, 'type': 'ABIERTA_SUBE_SIN_APERTURA',
                        'shift': label, 'idx': shift_side,
                        'detail': f'abierta sube {prev_ab:.0f}->{ab:.0f} (+{rise:.0f}g) sin apertura (cerradas prev={n_cerr_prev}, curr={n_cerr_curr})',
                        'raw_val': ab, 'corrected_val': prev_ab,
                        'impact': prev_ab - ab,
                        'sold_engine': sold,
                    })

        # ── Pattern 3: Cerrada 1-sighting disappears without opening ──
        for cerr_val in obs_a.cerradas:
            # Was this cerrada in prev shift?
            in_prev = False
            for ci2, s2 in ctx:
                if ci2 >= idx_a or s2 is None:
                    continue
                obs2 = s2.flavors.get(fname)
                if obs2 and any(abs(c - cerr_val) <= 30 for c in obs2.cerradas):
                    in_prev = True
                    break
            # Is it in shift B?
            in_b = any(abs(c - cerr_val) <= 30 for c in obs_b.cerradas)
            # Is it in any future shift?
            in_future = False
            for ci2, s2 in ctx:
                if ci2 <= idx_b or s2 is None:
                    continue
                obs2 = s2.flavors.get(fname)
                if obs2 and any(abs(c - cerr_val) <= 50 for c in obs2.cerradas):
                    in_future = True
                    break

            if not in_prev and not in_b and not in_future and cerr_val > 5000:
                # New cerrada that appears once and vanishes
                ab_jump = obs_b.abierta - obs_a.abierta
                if ab_jump < 1500:  # no opening evidence
                    anomalies.append({
                        'day': day_a, 'flavor': fname, 'type': 'CERRADA_1SIGHT_DESAPARECE',
                        'shift': 'DIA', 'idx': idx_a,
                        'detail': f'cerrada {cerr_val:.0f}g aparece solo en DIA, no en NOCHE ni turnos adyacentes. ab_jump={ab_jump:.0f}g (no apertura)',
                        'raw_val': cerr_val, 'corrected_val': 0,
                        'impact': -cerr_val,
                        'sold_engine': sold,
                    })

        # ── Pattern 4: Name inconsistency ──
        # Check if this flavor only exists in one shift of the period
        # and a similar name exists in the other
        if obs_a and not obs_b:
            # flavor in DIA but not NOCHE - check for similar name in NOCHE
            for fname2 in sb.flavors:
                if fname2 != fname and (fname.startswith(fname2[:5]) or fname2.startswith(fname[:5])):
                    obs_b2 = sb.flavors[fname2]
                    if obs_b2 and fname2 not in [f for f in pr.flavors]:
                        pass  # would need cross-flavor check

        # ── Pattern 5: Engine correction that looks wrong ──
        if all_corr and abs(diff) > 3000:
            for c in all_corr:
                anomalies.append({
                    'day': day_a, 'flavor': fname, 'type': 'ENGINE_CORRECTION_GRANDE',
                    'shift': 'A' if c in fr.corrections_a else 'B',
                    'idx': idx_a if c in fr.corrections_a else idx_b,
                    'detail': f'{c.action}:{c.rule}({c.value_affected:.0f}g) conf={c.confidence:.2f} -> sold={sold} vs raw={raw}',
                    'raw_val': raw, 'corrected_val': sold,
                    'impact': diff,
                    'sold_engine': sold,
                })

        # ── Pattern 6: Large negative sale (no correction) ──
        if sold < -300 and not all_corr:
            anomalies.append({
                'day': day_a, 'flavor': fname, 'type': 'VENTA_NEGATIVA_SIN_CORRECCION',
                'shift': '-', 'idx': idx_a,
                'detail': f'venta={sold}g negativa sin corrección del engine',
                'raw_val': raw, 'corrected_val': sold,
                'impact': 0,
                'sold_engine': sold,
            })

        # ── Pattern 7: Huge positive sale (>6000g, no correction) ──
        if sold > 6000 and not all_corr:
            anomalies.append({
                'day': day_a, 'flavor': fname, 'type': 'VENTA_ENORME_SIN_CORRECCION',
                'shift': '-', 'idx': idx_a,
                'detail': f'venta={sold}g enorme sin corrección',
                'raw_val': raw, 'corrected_val': sold,
                'impact': 0,
                'sold_engine': sold,
            })

# ── Check name inconsistency globally ──
# Find flavors that appear in some shifts but not others, with similar names
from collections import defaultdict
flavor_shifts = defaultdict(set)
for s in non_stock:
    for fname in s.flavors:
        flavor_shifts[fname].add(s.index)

# Check pairs
checked = set()
for f1 in sorted(flavor_shifts.keys()):
    for f2 in sorted(flavor_shifts.keys()):
        if f1 >= f2:
            continue
        pair = (f1, f2)
        if pair in checked:
            continue
        checked.add(pair)
        # Similar names?
        if len(f1) < 4 or len(f2) < 4:
            continue
        # Check if they're alternate spellings (differ by 1-2 chars, similar length)
        if abs(len(f1) - len(f2)) <= 2:
            common = sum(1 for a, b in zip(f1, f2) if a == b)
            if common >= min(len(f1), len(f2)) - 2 and common >= 4:
                # Check if they ever coexist in the same shift
                overlap = flavor_shifts[f1] & flavor_shifts[f2]
                if not overlap:
                    anomalies.append({
                        'day': 'ALL', 'flavor': f'{f1}/{f2}',
                        'type': 'NOMBRE_INCONSISTENTE',
                        'shift': '-', 'idx': 0,
                        'detail': f'{f1} aparece en {len(flavor_shifts[f1])} turnos, {f2} en {len(flavor_shifts[f2])} turnos. Nunca coexisten.',
                        'raw_val': 0, 'corrected_val': 0,
                        'impact': 0,
                        'sold_engine': 0,
                    })

# ─── Output ───
print('='*140)
print('ANÁLISIS MULTI-TURNO COMPLETO — TODAS LAS ANOMALÍAS DETECTADAS')
print('='*140)

# Group by type
from collections import Counter
type_counts = Counter(a['type'] for a in anomalies)
print(f'\nTotal anomalías: {len(anomalies)}')
for t, c in type_counts.most_common():
    print(f'  {t}: {c}')

print(f'\n{"="*140}')
print('DETALLE POR DÍA')
print(f'{"="*140}')

# Group by day
by_day = defaultdict(list)
for a in anomalies:
    by_day[str(a['day'])].append(a)

for day_key in sorted(by_day.keys(), key=lambda x: (0 if x == 'ALL' else 1, x.zfill(3) if x != 'ALL' else '')):
    day_anoms = by_day[day_key]
    print(f'\n--- DÍA {day_key} ({len(day_anoms)} anomalías) ---')
    for a in sorted(day_anoms, key=lambda x: (x['flavor'], x['type'])):
        print(f'  [{a["type"]:<35}] {a["flavor"]:<20} {a["shift"]:<6} {a["detail"]}')
