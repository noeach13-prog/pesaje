import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, extract_day_number
from inference import build_trajectories

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)

# Find day-28 shifts
day28_indices = set()
for s in shifts:
    if not s.is_stock_sheet and extract_day_number(s.name) == '28':
        day28_indices.add(s.index)
        print(f"Day 28 shift: {s.name} (index {s.index})")

print(f"\nOpened cans on day 28:")
for flavor, cans in sorted(tracked_cans.items()):
    for c in cans:
        if c.status == 'opened' and c.opened_at in day28_indices:
            last = c.sightings[-1]
            first = c.sightings[0]
            print(f"\n  {flavor}: can {c.id}")
            print(f"    Weight: {c.last_weight}g")
            print(f"    Last slot_type: {last.slot_type}")
            print(f"    First seen: shift {first.shift_index} ({first.shift_name})")
            print(f"    Last seen: shift {last.shift_index} ({last.shift_name})")
            print(f"    Sightings: {len(c.sightings)}")
            print(f"    Opened at: shift {c.opened_at}")
            # Show all sightings
            for sg in c.sightings:
                print(f"      [{sg.shift_index}] {sg.shift_name}: {sg.weight}g col={sg.column} type={sg.slot_type}")

            # Check abierta at the transition
            prev_shift = None
            curr_shift = None
            for s in shifts:
                if s.index == c.opened_at:
                    curr_shift = s
                if s.index == c.opened_at - 1 or (prev_shift is None and s.index < c.opened_at and not s.is_stock_sheet):
                    prev_shift = s
            # Find the actual previous non-stock shift
            prev_shift = None
            for s in sorted(shifts, key=lambda x: x.index, reverse=True):
                if s.index < c.opened_at and not s.is_stock_sheet:
                    prev_shift = s
                    break
            if prev_shift and curr_shift:
                obs_prev = prev_shift.flavors.get(flavor)
                obs_curr = curr_shift.flavors.get(flavor)
                if obs_prev and obs_curr:
                    jump = obs_curr.abierta - obs_prev.abierta
                    print(f"    Abierta: {obs_prev.abierta} -> {obs_curr.abierta} (jump={jump})")
                    print(f"    Cerradas before: {obs_prev.cerradas}")
                    print(f"    Cerradas after: {obs_curr.cerradas}")
                    print(f"    Entrantes before: {obs_prev.entrantes}")
                    print(f"    Entrantes after: {obs_curr.entrantes}")
