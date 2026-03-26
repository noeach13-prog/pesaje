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

# Day 27 periods: those where shift_a or shift_b is day 27
# But for "day 27 sold" we want periods WITHIN day 27 only:
# Viernes 27 (DIA) -> Viernes 27 (NOCHE)
print("=== ALL PERIODS touching day 27 ===")
for r in results:
    sa_name = shift_map[r.shift_a].name if r.shift_a in shift_map else '?'
    sb_name = shift_map[r.shift_b].name if r.shift_b in shift_map else '?'
    day_a = extract_day_number(sa_name)
    day_b = extract_day_number(sb_name)
    if day_a == '27' or day_b == '27':
        total = sum(d.get('sold', 0) for d in r.flavors.values())
        print(f"  {sa_name} -> {sb_name}  total_sold={total:.0f}")

# Show the period within day 27
print("\n=== PERIOD: Viernes 27 (DIA) -> Viernes 27 (NOCHE) ===")
for r in results:
    sa_name = shift_map.get(r.shift_a, None)
    sb_name = shift_map.get(r.shift_b, None)
    if sa_name is None or sb_name is None:
        continue
    sa_name = sa_name.name
    sb_name = sb_name.name
    if '27' in sa_name and '27' in sb_name:
        items = sorted(r.flavors.items(), key=lambda x: x[1].get('sold', 0))
        for flavor, data in items:
            sold = data.get('sold', 0)
            conf = data.get('confidence', 1.0)
            source = data.get('source', 'raw')
            marker = ' <<<' if abs(sold) > 3000 or sold < -500 else ''
            print(f"  {flavor:25s} sold={sold:8.0f}  conf={conf:.2f}  src={source}{marker}")
        total = sum(d.get('sold', 0) for d in r.flavors.values())
        print(f"\n  PERIOD TOTAL: {total:.0f}g")

# Show cross-day periods
print("\n=== PERIOD: Jueves 26 (NOCHE) -> Viernes 27 (DIA) ===")
for r in results:
    sa = shift_map.get(r.shift_a)
    sb = shift_map.get(r.shift_b)
    if sa and sb and '26' in sa.name and 'NOCHE' in sa.name and '27' in sb.name:
        items = sorted(r.flavors.items(), key=lambda x: x[1].get('sold', 0))
        for flavor, data in items:
            sold = data.get('sold', 0)
            if abs(sold) > 2000 or sold < -300:
                conf = data.get('confidence', 1.0)
                source = data.get('source', 'raw')
                print(f"  {flavor:25s} sold={sold:8.0f}  conf={conf:.2f}  src={source} <<<")
        total = sum(d.get('sold', 0) for d in r.flavors.values())
        print(f"\n  PERIOD TOTAL: {total:.0f}g")

print("\n=== PERIOD: Viernes 27 (NOCHE) -> Sabado 28 (DIA) ===")
for r in results:
    sa = shift_map.get(r.shift_a)
    sb = shift_map.get(r.shift_b)
    if sa and sb and '27' in sa.name and 'NOCHE' in sa.name and '28' in sb.name:
        items = sorted(r.flavors.items(), key=lambda x: x[1].get('sold', 0))
        for flavor, data in items:
            sold = data.get('sold', 0)
            if abs(sold) > 2000 or sold < -300:
                conf = data.get('confidence', 1.0)
                source = data.get('source', 'raw')
                print(f"  {flavor:25s} sold={sold:8.0f}  conf={conf:.2f}  src={source} <<<")
        total = sum(d.get('sold', 0) for d in r.flavors.values())
        print(f"\n  PERIOD TOTAL: {total:.0f}g")
