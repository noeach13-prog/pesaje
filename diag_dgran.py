import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods
from inference import build_trajectories
from calculator import calculate_sold_v2

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)

traj = trajectories.get('D. GRANIZADO', [])
for tp in traj:
    if tp.shift_index in (51, 52, 53, 54):
        raw_total = tp.raw.total if tp.raw else 0
        print(f"  Shift {tp.shift_index} ({tp.shift_name}): raw_total={raw_total:.0f} inferred={tp.inferred_total:.0f} conf={tp.confidence:.2f}")
        for c in tp.corrections:
            print(f"    {c.rule}: {c.action} {c.value_affected:.0f}g conf={c.confidence:.2f}")
            print(f"      {c.description}")
