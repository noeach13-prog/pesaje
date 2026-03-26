import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number, group_periods_by_day
from inference import build_trajectories
from calculator import calculate_sold_v2

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)

# Build name lookup
shift_by_name = {s.name: s for s in shifts}
shift_by_idx = {s.index: s for s in shifts}

# Result lookup by names (same as aggregate_by_day uses)
result_lookup = {(r.shift_a, r.shift_b): r for r in results}

# What does group_periods_by_day assign to day 27?
day_periods = group_periods_by_day(shifts, periods)
print("=== PERIODS ASSIGNED TO DAY 27 ===")
for idx_a, idx_b, is_reset in day_periods.get('27', []):
    sa = shift_by_idx[idx_a]
    sb = shift_by_idx[idx_b]
    pr = result_lookup.get((sa.name, sb.name))
    if pr:
        total = sum(f.sold_grams for f in pr.flavors.values())
        print(f"  {sa.name} -> {sb.name} total_sold={total:.0f}")
    else:
        print(f"  {sa.name} -> {sb.name} NO RESULT FOUND!")

# Show all 3 periods touching day 27
print("\n=== ALL PERIODS NEAR DAY 27 ===")
for idx_a, idx_b, is_reset in periods:
    sa = shift_by_idx[idx_a]
    sb = shift_by_idx[idx_b]
    da = extract_day_number(sa.name)
    db = extract_day_number(sb.name)
    if da in ('26','27','28') and db in ('26','27','28'):
        pr = result_lookup.get((sa.name, sb.name))
        total = sum(f.sold_grams for f in pr.flavors.values()) if pr else 0
        assigned_day = db  # same-day or cross-day?
        print(f"  {sa.name} -> {sb.name}  days={da}->{db}  total_sold={total:.0f}")

# Detail the period within day 27: Viernes 27 DIA -> Viernes 27 NOCHE
print("\n=== Viernes 27 (DIA) -> Viernes 27 (NOCHE) DETAIL ===")
for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        items = sorted(r.flavors.items(), key=lambda x: x[1].sold_grams)
        for flavor, fdata in items:
            marker = ''
            if fdata.sold_grams < -300: marker = ' <<< NEGATIVE'
            if abs(fdata.sold_grams) > 3000: marker = ' <<< LARGE'
            if marker or abs(fdata.sold_grams - fdata.raw_sold) > 100:
                print(f"  {flavor:25s} sold={fdata.sold_grams:8.0f} raw={fdata.raw_sold:8.0f} conf={fdata.confidence:.2f}{marker}")
        total = sum(f.sold_grams for f in r.flavors.values())
        raw_total = sum(f.raw_sold for f in r.flavors.values())
        print(f"\n  ENGINE TOTAL: {total:.0f}g  RAW TOTAL: {raw_total:.0f}g")

# Also check the cross-day periods
for label_a, label_b in [('Jueves 26 (NOCHE)', 'Viernes 27 (DIA)'), ('Viernes 27 (NOCHE)', None)]:
    for r in results:
        if r.shift_a == label_a or ('27' in r.shift_a and 'NOCHE' in r.shift_a and '28' in r.shift_b):
            items = sorted(r.flavors.items(), key=lambda x: x[1].sold_grams)
            total = sum(f.sold_grams for f in r.flavors.values())
            print(f"\n=== {r.shift_a} -> {r.shift_b} === (total={total:.0f}g)")
            for flavor, fdata in items:
                if fdata.sold_grams < -300 or abs(fdata.sold_grams) > 3000:
                    print(f"  {flavor:25s} sold={fdata.sold_grams:8.0f} raw={fdata.raw_sold:8.0f} conf={fdata.confidence:.2f}")
    break
