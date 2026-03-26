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

# Show all results
print(f"Total results: {len(results)}")
for i, r in enumerate(results):
    sa = shift_map.get(r.shift_a)
    sb = shift_map.get(r.shift_b)
    sa_name = sa.name if sa else f'?{r.shift_a}'
    sb_name = sb.name if sb else f'?{r.shift_b}'
    total = sum(d.get('sold', 0) for d in r.flavors.values())
    n_flavors = len(r.flavors)
    day_a = extract_day_number(sa_name) if sa else '?'
    day_b = extract_day_number(sb_name) if sb else '?'
    if day_a in ('26','27','28') or day_b in ('26','27','28'):
        print(f"  [{i}] {sa_name} -> {sb_name} | {n_flavors} flavors | total={total:.0f}g | days {day_a}->{day_b}")
