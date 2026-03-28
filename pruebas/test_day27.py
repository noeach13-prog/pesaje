"""Quick test: day 27 per-flavor comparison against resolved PDF."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_v2

RESOLVED_27 = {
    'CADBURY': 435, 'AMERICANA': 765, 'ANANA': 1520, 'B, SPLIT': 1210,
    'CHOCOLATE': 1395, 'AMARGO': 1440, 'BLANCO': 295, 'CH C/ALM': 1660,
    'CH AMORES': 280, 'DOS CORAZONES': 260, 'CABSHA': 185, 'COOKIES': 245,
    'DULCE C/NUEZ': 275, 'DULCE D LECHE': 2155, 'D. GRANIZADO': 1690,
    'DULCE AMORES': 895, 'SUPER': 580, 'DURAZNO': 555, 'FERRERO': 635,
    'FLAN': 335, 'CEREZA': 460, 'FRAMBUEZA': 325, 'FRUTILLA CREMA': 1435,
    'FRUTILLA REINA': 285, 'FRUTILLA AGUA': 495, 'BOSQUE': 825,
    'GRANIZADO': 535, 'LIMON': 540, 'MANTECOL': 620, 'MANZANA': 170,
    'MARROC': 80, 'MASCARPONE': 310, 'MENTA': 380, 'MIX DE FRUTA': 5,
    'MOUSSE LIMON': 110, 'SAMBAYON': 1475, 'SAMBAYON AMORES': 395,
    'TRAMONTANA': 635, 'TIRAMISU': 85, 'VAINILLA': 660, 'LEMON PIE': 850,
    'IRLANDESA': 365, 'NUTE': 20, 'RUSA': 305, 'FRANUI': 425,
    'CIELO': 350, 'COCO': 370, 'KINDER': 405, 'MARACUYA': 0,
    'PISTACHO': 830, 'CHOCOLATE DUBAI': 860, 'KITKAT': 2130,
    'CHOCOLATE CON PASAS': 0,
}

INPUT = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'

config = PesajeConfig.default()
shifts, annotations = load_shifts_v2(INPUT)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)

# Find the period for day 27 DIA->NOCHE
day27_period = None
for r in results:
    if '27' in r.shift_a and '27' in r.shift_b and 'DIA' in r.shift_a and 'NOCHE' in r.shift_b:
        day27_period = r
        break

if day27_period is None:
    # Try alternate matching
    for r in results:
        if '27' in r.shift_a and '27' in r.shift_b:
            day27_period = r
            break

if day27_period is None:
    print("ERROR: Day 27 period not found!")
    print("Available periods:")
    for r in results:
        print(f"  {r.shift_a} -> {r.shift_b}")
    sys.exit(1)

print(f"Period: {day27_period.shift_a} -> {day27_period.shift_b}")
print(f"{'SABOR':<25} {'ENGINE':>8} {'RESOLVED':>8} {'DIFF':>6} {'CONF':>5} {'SOURCE':>10} CORRECTIONS")
print("-" * 100)

matches = 0
mismatches = 0
total_engine = 0
total_resolved = 0

for flavor in sorted(RESOLVED_27.keys()):
    resolved = RESOLVED_27[flavor]
    fr = day27_period.flavors.get(flavor)
    if fr is None:
        engine = 0
    else:
        engine = round(fr.sold_grams)
    diff = engine - resolved
    total_engine += engine
    total_resolved += resolved

    conf = fr.confidence if fr else 0
    corr_str = ''
    all_corr = []
    if fr:
        all_corr = fr.corrections_a + fr.corrections_b
    if all_corr:
        parts = []
        for c in all_corr:
            parts.append(f"{c.action[0].upper()}:{c.rule}({c.value_affected:.0f}g)")
        corr_str = ', '.join(parts)
    source = 'tracker' if all_corr else 'raw'

    marker = '' if diff == 0 else f' *** MISMATCH'
    if diff == 0:
        matches += 1
    else:
        mismatches += 1
    print(f"{flavor:<25} {engine:>8} {resolved:>8} {diff:>+6} {conf:>5.2f} {source:>10} {corr_str}{marker}")

print("=" * 100)
print(f"Matches: {matches}/{matches+mismatches}")
print(f"Mismatches: {mismatches}")
print(f"Engine total: {total_engine}")
print(f"Resolved total: {total_resolved}")
print(f"RESULT: {'PASS' if mismatches == 0 else 'FAIL'}")
