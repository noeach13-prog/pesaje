"""Stage 1: Classify every flavor-period as clean/suspicious/conflicting."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

config = PesajeConfig.default()
shifts, ann = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)

clean = []
suspicious = []
conflicting = []

for pr in results:
    da = extract_day_number(pr.shift_a)
    db = extract_day_number(pr.shift_b)
    if da != db:
        continue
    for fname, fr in pr.flavors.items():
        sold = round(fr.sold_grams)
        raw = round(fr.raw_sold)
        diff = sold - raw
        corr = fr.corrections_a + fr.corrections_b
        conf = fr.confidence

        # Classification rules:
        # CLEAN: no corrections, sold >= -100, sold <= 5000, conf == 1.0
        # SUSPICIOUS: small corrections or mild negatives
        # CONFLICTING: large corrections, very negative, very large, or low confidence
        if not corr and -100 <= sold <= 5000 and conf >= 0.9:
            clean.append((da, fname, sold, raw, 'clean'))
        elif abs(diff) > 3000 or sold < -300 or sold > 6000 or conf < 0.5:
            conflicting.append((da, fname, sold, raw, diff, conf,
                ', '.join(f'{c.action[0]}:{c.rule}({c.value_affected:.0f})' for c in corr)))
        else:
            suspicious.append((da, fname, sold, raw, diff, conf,
                ', '.join(f'{c.action[0]}:{c.rule}({c.value_affected:.0f})' for c in corr)))

print(f'STAGE 1: CLASSIFICATION')
print(f'  Clean:       {len(clean)} flavor-periods')
print(f'  Suspicious:  {len(suspicious)} flavor-periods')
print(f'  Conflicting: {len(conflicting)} flavor-periods')
print(f'  Total:       {len(clean)+len(suspicious)+len(conflicting)}')

print(f'\n{"="*120}')
print(f'CONFLICTING CASES ({len(conflicting)}) - These need Stage 2 deep analysis')
print(f'{"="*120}')
print(f'{"DIA":>4} {"SABOR":<22} {"ENGINE":>8} {"RAW":>8} {"DIFF":>8} {"CONF":>5} CORRECCIONES')
print(f'{"-"*100}')
for da, fn, sold, raw, diff, conf, corr_str in sorted(conflicting, key=lambda x: (x[0].zfill(3), x[1])):
    print(f'{da:>4} {fn:<22} {sold:>8} {raw:>8} {diff:>+8} {conf:>5.2f} {corr_str}')

print(f'\n{"="*120}')
print(f'SUSPICIOUS CASES ({len(suspicious)}) - May need review but lower priority')
print(f'{"="*120}')
print(f'{"DIA":>4} {"SABOR":<22} {"ENGINE":>8} {"RAW":>8} {"DIFF":>8} {"CONF":>5} CORRECCIONES')
print(f'{"-"*100}')
for da, fn, sold, raw, diff, conf, corr_str in sorted(suspicious, key=lambda x: (x[0].zfill(3), x[1])):
    print(f'{da:>4} {fn:<22} {sold:>8} {raw:>8} {diff:>+8} {conf:>5.2f} {corr_str}')
