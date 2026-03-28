import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, extract_day_number

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)

# Show raw data for problem flavors across shifts 49-55
problem_flavors = ['D. GRANIZADO', 'COOKIES', 'LIMON', 'FRUTILLA CREMA', 'SAMBAYON', 
                   'SAMBAYON AMORES', 'CIELO', 'CHOCOLATE']

for flavor in problem_flavors:
    print(f"\n{'='*80}")
    print(f"=== {flavor} across shifts 49-55 ===")
    for s in shifts:
        if s.is_stock_sheet or s.index < 49 or s.index > 55:
            continue
        obs = s.flavors.get(flavor)
        if obs:
            total = obs.abierta + obs.celiaca + sum(obs.cerradas) + sum(obs.entrantes)
            print(f"  [{s.index:2d}] {s.name:30s} ab={obs.abierta:6.0f} cel={obs.celiaca:4.0f} cerr={str(obs.cerradas):25s} entr={str(obs.entrantes):25s} total={total:.0f}")
        else:
            print(f"  [{s.index:2d}] {s.name:30s} -- not present --")
