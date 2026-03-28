import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)

# Show KITKAT raw data shifts 44-55
print("=== KITKAT raw data ===")
for s in shifts:
    if s.is_stock_sheet or s.index < 44:
        continue
    obs = s.flavors.get('KITKAT')
    if obs:
        total = obs.abierta + obs.celiaca + sum(obs.cerradas) + sum(obs.entrantes)
        print(f"  [{s.index:2d}] {s.name:30s} ab={obs.abierta:6.0f} cerr={obs.cerradas!s:20s} entr={obs.entrantes!s:20s} total={total:.0f}")

# Show tracker cans for KITKAT
from inference import build_trajectories
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
print("\n=== KITKAT tracked cans ===")
for can in tracked_cans.get('KITKAT', []):
    print(f"  Can {can.id}: status={can.status} opened_at={can.opened_at} weight={can.last_weight:.0f}")
    for sg in can.sightings:
        print(f"    [{sg.shift_index}] {sg.shift_name}: {sg.weight:.0f}g type={sg.slot_type}")
