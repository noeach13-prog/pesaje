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

# Resolved day 27 from PDF
resolved_27 = {
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
    'TRAMONTANA': 635, 'TIRAMIZU': 85, 'VAINILLA': 660, 'LEMON PIE': 850,
    'IRLANDESA': 365, 'NUTE': 20, 'RUSA': 305, 'FRANUI': 425,
    'CIELO': 350, 'COCO': 370, 'KINDER': 405, 'MARACUYA': 0,
    'PISTACHO': 830, 'CHOCOLATE DUBAI': 860, 'KITKAT': 2130,
}

shift_map = {s.name: s for s in shifts}
mismatches = 0
matches = 0
for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        sa = shift_map[r.shift_a]
        sb = shift_map[r.shift_b]
        print(f"{'SABOR':25s} {'ENGINE':>8s} {'RESUELTO':>8s} {'DIFF':>8s} {'NOTA':s}")
        print("-" * 90)
        for flavor in sorted(resolved_27.keys()):
            fdata = r.flavors.get(flavor)
            eng = fdata.sold_grams if fdata else 0
            res = resolved_27[flavor]
            diff = eng - res
            nota = ''
            if diff != 0:
                mismatches += 1
                obs_a = sa.flavors.get(flavor)
                obs_b = sb.flavors.get(flavor)
                # Check if it's an entrante duplication
                if obs_a and obs_b:
                    entr_a = set(int(e) for e in obs_a.entrantes)
                    entr_b = set(int(e) for e in obs_b.entrantes)
                    persisting = entr_a & entr_b
                    cerr_b = set(int(c) for c in obs_b.cerradas)
                    if persisting:
                        nota = f'ENTRANTE DUPLICADO: {persisting} persiste en NOCHE (deberia ser cerrada)'
                nota += f'  <<<'
            else:
                matches += 1
            print(f"{flavor:25s} {eng:8.0f} {res:8.0f} {diff:+8.0f} {nota}")

        total_eng = sum(r.flavors[f].sold_grams for f in resolved_27 if f in r.flavors)
        total_res = sum(resolved_27.values())
        print("-" * 90)
        print(f"{'TOTAL':25s} {total_eng:8.0f} {total_res:8.0f} {total_eng-total_res:+8.0f}")
        print(f"\nMatches: {matches}/{matches+mismatches}")
        print(f"Mismatches: {mismatches}")

        # Latas comparison
        print(f"\n--- LATAS CAMBIADAS ---")
        print(f"  Resuelto: 3 latas = 840g")
        day27_indices = set(s.index for s in shifts if not s.is_stock_sheet and extract_day_number(s.name) == '27')
        opened = []
        for fl, cans_list in sorted(tracked_cans.items()):
            for can in cans_list:
                if can.status == 'opened' and can.opened_at in day27_indices:
                    opened.append((fl, can))
        print(f"  Engine:   {len(opened)} latas = {len(opened)*280}g")
        for fl, can in opened:
            print(f"    {fl}: lata {can.last_weight:.0f}g opened at shift {can.opened_at}")

        print(f"\n--- FORMULA ---")
        print(f"  Resuelto: {total_res} - 840 + 250 = {total_res - 840 + 250}")
        print(f"  Engine:   {total_eng} - {len(opened)*280} + 250 = {total_eng - len(opened)*280 + 250}")
        break
