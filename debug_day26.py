"""Debug day 26: multi-shift raw comparison for suspicious flavors."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2

INPUT = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'

config = PesajeConfig.default()
shifts, annotations = load_shifts_v2(INPUT)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)

# Suspicious flavors from day 26
SUSPICIOUS = [
    'CADBURY', 'KITKAT', 'DULCE D LECHE', 'PISTACHO', 'SUPER',
    'CH C/ALM', 'BLANCO', 'DOS CORAZONES', 'SAMBAYON', 'SAMBAYON AMORES',
    'DULCE AMORES',
]

# Show shifts around day 26: days 24-28 (wider window)
target_days = {'24', '25', '26', '27', '28'}
relevant_shifts = []
for s in shifts:
    if s.is_stock_sheet:
        continue
    d = extract_day_number(s.name)
    if d in target_days:
        relevant_shifts.append(s)

relevant_shifts.sort(key=lambda s: s.index)

print(f"Shifts in window (days 24-28):")
for s in relevant_shifts:
    print(f"  idx={s.index:>3}  {s.name}")

for flavor in sorted(SUSPICIOUS):
    print(f"\n{'=' * 140}")
    print(f"FLAVOR: {flavor}")
    print(f"{'=' * 140}")

    # Header
    header = f"{'TURNO':<30} {'IDX':>4} {'ABIERTA':>8} {'CELIACA':>8} {'CERRADAS':<40} {'ENTRANTES':<25}"
    print(header)
    print("-" * 140)

    for s in relevant_shifts:
        obs = s.flavors.get(flavor)
        if obs is None:
            print(f"{s.name:<30} {s.index:>4}  -- no data --")
            continue

        cerr_str = ', '.join(f"{v:.0f}" for v in obs.cerradas) if obs.cerradas else '-'
        entr_str = ', '.join(f"{v:.0f}" for v in obs.entrantes) if obs.entrantes else '-'
        total = obs.total
        print(f"{s.name:<30} {s.index:>4} {obs.abierta:>8.0f} {obs.celiaca:>8.0f} {cerr_str:<40} {entr_str:<25} total={total:.0f}")

    # Show tracker cans for this flavor
    cans = tracked_cans.get(flavor, [])
    if cans:
        print(f"\n  Tracker identities:")
        for can in cans:
            sightings_str = ', '.join(
                f"idx{sg.shift_index}:{sg.weight:.0f}({sg.slot_type[0]})"
                for sg in can.sightings
            )
            # Filter to show only cans active in our window
            relevant_sg = [sg for sg in can.sightings
                          if any(sg.shift_index == rs.index for rs in relevant_shifts)]
            if not relevant_sg:
                continue
            print(f"  [{can.id}] status={can.status}"
                  f"{f' opened_at={can.opened_at}' if can.opened_at else ''}"
                  f"  sightings: {sightings_str}")

    # Show what the engine computed for day 26 period
    periods = generate_periods(shifts, resets)
    results = calculate_sold_v2(trajectories, periods, shifts)
    for r in results:
        da = extract_day_number(r.shift_a)
        db = extract_day_number(r.shift_b)
        if da == '26' and db == '26':
            fr = r.flavors.get(flavor)
            if fr:
                corr_a = ', '.join(f"{c.action[0].upper()}:{c.rule}({c.value_affected:.0f}g)"
                                   for c in fr.corrections_a) or 'none'
                corr_b = ', '.join(f"{c.action[0].upper()}:{c.rule}({c.value_affected:.0f}g)"
                                   for c in fr.corrections_b) or 'none'
                print(f"\n  Engine day 26: sold={fr.sold_grams:.0f}g  raw={fr.raw_sold:.0f}g")
                print(f"    Corrections A (DIA): {corr_a}")
                print(f"    Corrections B (NOCHE): {corr_b}")
            break

    # Manual calculation
    print(f"\n  --- Manual deduction ---")
    dia26 = None
    noche26 = None
    for s in relevant_shifts:
        d = extract_day_number(s.name)
        if d == '26' and 'DIA' in s.name.upper():
            dia26 = s.flavors.get(flavor)
        if d == '26' and 'NOCHE' in s.name.upper():
            noche26 = s.flavors.get(flavor)

    if dia26 and noche26:
        raw_sold = dia26.total - noche26.total
        print(f"  DIA total={dia26.total:.0f}  NOCHE total={noche26.total:.0f}  raw_sold={raw_sold:.0f}")
    elif dia26:
        print(f"  DIA total={dia26.total:.0f}  NOCHE: no data")
    elif noche26:
        print(f"  DIA: no data  NOCHE total={noche26.total:.0f}")
