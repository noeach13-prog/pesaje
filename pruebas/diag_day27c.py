import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)

shift_map = {s.index: s for s in shifts}

# Show periods near day 27
for r in results:
    sa = shift_map.get(r.shift_a)
    sb = shift_map.get(r.shift_b)
    if not sa or not sb:
        continue
    day_a = extract_day_number(sa.name)
    day_b = extract_day_number(sb.name)
    if day_a in ('26','27','28') or day_b in ('26','27','28'):
        total = sum(f.sold_grams for f in r.flavors.values())
        print(f"{sa.name:30s} -> {sb.name:30s} | total={total:8.0f}g | days {day_a}->{day_b}")

# Detail for all day-27 related periods
print("\n" + "="*100)
for r in results:
    sa = shift_map.get(r.shift_a)
    sb = shift_map.get(r.shift_b)
    if not sa or not sb:
        continue
    day_a = extract_day_number(sa.name)
    day_b = extract_day_number(sb.name)
    if day_a == '27' or day_b == '27':
        total = sum(f.sold_grams for f in r.flavors.values())
        print(f"\n=== {sa.name} -> {sb.name} === (total={total:.0f}g)")
        items = sorted(r.flavors.items(), key=lambda x: x[1].sold_grams)
        for flavor, fdata in items:
            marker = ' <<<' if abs(fdata.sold_grams) > 2000 or fdata.sold_grams < -300 else ''
            corr_a = len(fdata.corrections_a) if fdata.corrections_a else 0
            corr_b = len(fdata.corrections_b) if fdata.corrections_b else 0
            print(f"  {flavor:25s} sold={fdata.sold_grams:8.0f} raw={fdata.raw_sold:8.0f} conf={fdata.confidence:.2f} corr_a={corr_a} corr_b={corr_b}{marker}")
