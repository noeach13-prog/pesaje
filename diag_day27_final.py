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

# Period: Viernes 27 DIA -> NOCHE
for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        print(f"=== {r.shift_a} -> {r.shift_b} ===\n")
        items = sorted(r.flavors.items(), key=lambda x: x[1].sold_grams)
        
        # Categories
        corrected_wrong = []  # engine != raw due to corrections
        raw_negative_big = []  # raw is very negative (restocking)
        raw_normal = []
        
        for flavor, fdata in items:
            diff = fdata.sold_grams - fdata.raw_sold
            if abs(diff) > 100:
                corrected_wrong.append((flavor, fdata))
            elif fdata.raw_sold < -500:
                raw_negative_big.append((flavor, fdata))
            else:
                raw_normal.append((flavor, fdata))
        
        print("--- WRONG CORRECTIONS (engine != raw, correction is harmful) ---")
        for flavor, fdata in corrected_wrong:
            diff = fdata.sold_grams - fdata.raw_sold
            print(f"  {flavor:25s} engine={fdata.sold_grams:8.0f} raw={fdata.raw_sold:8.0f} diff={diff:+.0f}")
            for c in (fdata.corrections_a or []):
                print(f"    A: {c}")
            for c in (fdata.corrections_b or []):
                print(f"    B: {c}")
        
        print(f"\n--- RESTOCKING (raw very negative, new stock appeared at NOCHE) ---")
        for flavor, fdata in raw_negative_big:
            print(f"  {flavor:25s} engine={fdata.sold_grams:8.0f} raw={fdata.raw_sold:8.0f}")
        
        print(f"\n--- NORMAL SALES ---")
        normal_total = sum(f.sold_grams for _, f in raw_normal)
        for flavor, fdata in raw_normal:
            if abs(fdata.sold_grams) > 500:
                print(f"  {flavor:25s} sold={fdata.sold_grams:8.0f}")
        print(f"  ... and {len(raw_normal) - sum(1 for _,f in raw_normal if abs(f.sold_grams)>500)} smaller entries")
        print(f"  Normal sales subtotal: {normal_total:.0f}g")
        
        total_corrected = sum(f.sold_grams for _, f in corrected_wrong)
        total_restock = sum(f.sold_grams for _, f in raw_negative_big)
        print(f"\n--- SUMMARY ---")
        print(f"  Normal sales:      {normal_total:8.0f}g")
        print(f"  Wrong corrections: {total_corrected:8.0f}g (should be raw: {sum(f.raw_sold for _,f in corrected_wrong):.0f}g)")
        print(f"  Restocking:        {total_restock:8.0f}g (raw: {sum(f.raw_sold for _,f in raw_negative_big):.0f}g)")
        print(f"  ENGINE TOTAL:      {sum(f.sold_grams for f in r.flavors.values()):8.0f}g")
        print(f"  RAW TOTAL:         {sum(f.raw_sold for f in r.flavors.values()):8.0f}g")
        print(f"  IF corrections fixed: {normal_total + sum(f.raw_sold for _,f in corrected_wrong) + total_restock:.0f}g")
        break
