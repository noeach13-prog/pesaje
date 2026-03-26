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

# Viernes 27 DIA -> NOCHE detail
for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        items = sorted(r.flavors.items(), key=lambda x: x[1].sold_grams)
        for flavor, fdata in items:
            diff = fdata.sold_grams - fdata.raw_sold
            if abs(diff) > 100:
                print(f"\n{flavor}: sold={fdata.sold_grams:.0f} raw={fdata.raw_sold:.0f} diff={diff:.0f}")
                if fdata.corrections_a:
                    print(f"  Corrections A (DIA):")
                    for c in fdata.corrections_a:
                        print(f"    {c}")
                if fdata.corrections_b:
                    print(f"  Corrections B (NOCHE):")
                    for c in fdata.corrections_b:
                        print(f"    {c}")

        # Also show the raw slot data for worst offenders
        print("\n" + "="*80)
        print("RAW SLOT DATA for worst offenders:")
        sa = [s for s in shifts if s.name == r.shift_a][0]
        sb = [s for s in shifts if s.name == r.shift_b][0]
        for flavor, fdata in items:
            if fdata.sold_grams < -3000:
                obs_a = sa.flavors.get(flavor)
                obs_b = sb.flavors.get(flavor)
                print(f"\n  {flavor}:")
                if obs_a:
                    total_a = obs_a.abierta + obs_a.celiaca + sum(obs_a.cerradas) + sum(obs_a.entrantes)
                    print(f"    DIA:   ab={obs_a.abierta} cel={obs_a.celiaca} cerr={obs_a.cerradas} entr={obs_a.entrantes} total={total_a}")
                if obs_b:
                    total_b = obs_b.abierta + obs_b.celiaca + sum(obs_b.cerradas) + sum(obs_b.entrantes)
                    print(f"    NOCHE: ab={obs_b.abierta} cel={obs_b.celiaca} cerr={obs_b.cerradas} entr={obs_b.entrantes} total={total_b}")
        break

# Also show trajectory points for these flavors at shifts 52, 53
print("\n" + "="*80)
print("TRAJECTORY POINTS at shifts 52 (DIA), 53 (NOCHE):")
bad_flavors = ['D. GRANIZADO', 'COOKIES', 'LIMON', 'FRUTILLA CREMA', 'SAMBAYON', 'SAMBAYON AMORES', 'CIELO', 'CHOCOLATE']
for flavor in bad_flavors:
    traj = trajectories.get(flavor, [])
    for tp in traj:
        if tp.shift_index in (52, 53):
            print(f"  {flavor} shift {tp.shift_index}: raw={tp.raw_total:.0f} inferred={tp.inferred_total:.0f} conf={tp.confidence:.2f} corrections={len(tp.corrections)}")
            for c in tp.corrections:
                print(f"    {c}")
