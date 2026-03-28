"""
Test V2 engine against resolved Feb 28 DIA->NOCHE example.
Runs the full pipeline, then does case analysis for every mismatch.
Also validates VDP same-day rule.
"""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import (build_timeline, find_resets, generate_periods,
                    collect_vdp_by_day, collect_vdp_by_shift, extract_day_number)
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

# Resolved PDF values (supervised reference) — stock-based sold only, no VDP
RESOLVED = {
    'CADBURY': 845, 'AMERICANA': 525, 'ANANA': 1115, 'B, SPLIT': 1765,
    'CHOCOLATE': 2910, 'AMARGO': 1345, 'BLANCO': 415, 'CH C/ALM': 2170,
    'CH AMORES': 415, 'DOS CORAZONES': 705, 'CABSHA': 660, 'COOKIES': 420,
    'DULCE C/NUEZ': 100, 'DULCE D LECHE': 1620, 'D. GRANIZADO': 4725,
    'DULCE AMORES': 1590, 'SUPER': 630, 'DURAZNO': 145, 'FERRERO': 180,
    'FLAN': 185, 'CEREZA': 1190, 'FRAMBUEZA': 530, 'FRUTILLA CREMA': 2210,
    'FRUTILLA REINA': 700, 'FRUTILLA AGUA': 855, 'BOSQUE': 980,
    'GRANIZADO': 1070, 'LIMON': 2925, 'MANTECOL': 860, 'MANZANA': 85,
    'MARROC': 1220, 'MASCARPONE': 390, 'MENTA': 2190, 'MIX DE FRUTA': -95,
    'MOUSSE LIMON': 80, 'SAMBAYON': 655, 'SAMBAYON AMORES': 460,
    'TRAMONTANA': 1325, 'TIRAMIZU': 1010, 'VAINILLA': 1075,
    'LEMON PIE': 85, 'IRLANDESA': 545, 'NUTE': 385, 'RUSA': 65,
    'FRANUI': 1445, 'CIELO': 835, 'COCO': 255, 'KINDER': 930,
    'MARACUYA': 555, 'PISTACHO': 1550, 'CHOCOLATE DUBAI': 1740,
    'KITKAT': 595, 'CHOCOLATE CON PASAS': 0,
}

# Normalize for comparison
from parser import normalize_name
RESOLVED_NORM = {normalize_name(k): v for k, v in RESOLVED.items()}


def main():
    config = PesajeConfig.default()
    print("Loading workbook...")
    shifts, annotations = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')

    print(f"  {len(shifts)} shifts loaded ({sum(1 for s in shifts if s.is_stock_sheet)} STOCK sheets)")

    shifts = build_timeline(shifts)
    resets = find_resets(shifts)
    print(f"  Resets at indices: {sorted(resets)}")

    periods = generate_periods(shifts, resets)
    print(f"  {len(periods)} periods generated")

    print("\nBuilding trajectories...")
    trajectories, tracked_cans = build_trajectories(shifts, resets, config)
    print(f"  {len(trajectories)} flavors tracked")

    # Count total opened cans detected
    total_opened = sum(1 for cans in tracked_cans.values()
                       for c in cans if c.status == 'opened')
    print(f"  {total_opened} can-opening events detected across all flavors")

    print("\nCalculating sold grams (stock-based, no VDP)...")
    results = calculate_sold_v2(trajectories, periods, shifts)
    print(f"  {len(results)} period results")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST A: Per-flavor stock-based sold for Feb 28 DIA -> NOCHE
    # ══════════════════════════════════════════════════════════════════════════

    target = None
    for r in results:
        if '28 (DIA)' in r.shift_a and '28 (NOCHE)' in r.shift_b:
            target = r
            break
        if '28' in r.shift_a and 'DIA' in r.shift_a.upper():
            if '28' in r.shift_b and 'NOCHE' in r.shift_b.upper():
                target = r
                break

    if target is None:
        print("\nERROR: Could not find Feb 28 DIA -> NOCHE period!")
        print("Available periods:")
        for r in results[-5:]:
            print(f"  {r.shift_a} -> {r.shift_b}")
        return

    print(f"\n{'='*100}")
    print(f"TEST A: STOCK-BASED SOLD — {target.shift_a} -> {target.shift_b}")
    print(f"{'='*100}")

    matches = 0
    mismatches = []
    total_engine = 0
    total_resolved = 0

    print(f"\n{'SABOR':<25} {'ENGINE':>8} {'RESOLVED':>9} {'RAW_NAIVE':>10} {'DIFF':>6} {'CONF':>5} {'SOURCE':>15} {'CORRECTIONS'}")
    print('-' * 120)

    for flavor_norm, result in sorted(target.flavors.items()):
        expected = RESOLVED_NORM.get(flavor_norm, None)
        engine_val = round(result.sold_grams)
        raw_val = round(result.raw_sold)
        diff = engine_val - expected if expected is not None else '?'

        corr_str = ''
        if result.corrections_a:
            for c in result.corrections_a:
                corr_str += f'A:{c.rule}({c.value_affected:.0f}g) '
        if result.corrections_b:
            for c in result.corrections_b:
                corr_str += f'B:{c.rule}({c.value_affected:.0f}g) '

        source = 'tracker' if (result.corrections_a or result.corrections_b) else 'raw'

        print(f'{flavor_norm:<25} {engine_val:>8} {expected if expected is not None else "?":>9} '
              f'{raw_val:>10} {str(diff):>6} {result.confidence:>5.2f} {source:>15} {corr_str}')

        if expected is not None:
            total_engine += engine_val
            total_resolved += expected
            if diff == 0:
                matches += 1
            else:
                mismatches.append((flavor_norm, engine_val, expected, raw_val,
                                  result.corrections_a, result.corrections_b,
                                  result.confidence))

    print(f"\n{'='*100}")
    print(f"TEST A RESULT: {'PASS' if len(mismatches) == 0 else 'FAIL'}")
    print(f"  Matches: {matches}/{len(RESOLVED_NORM)}")
    print(f"  Mismatches: {len(mismatches)}")
    print(f"  Engine STOCK_SOLD: {total_engine}")
    print(f"  Resolved STOCK_SOLD: {total_resolved}")

    if mismatches:
        print(f"\n{'='*100}")
        print(f"DETAILED MISMATCH ANALYSIS")
        print(f"{'='*100}")

        for flavor, eng, exp, raw, corr_a, corr_b, conf in mismatches:
            print(f"\n--- {flavor} ---")
            print(f"  Engine sold: {eng}g")
            print(f"  Expected (resolved): {exp}g")
            print(f"  Raw naive: {raw}g")
            print(f"  Discrepancy: {eng - exp}g")
            print(f"  Confidence: {conf}")

            if corr_a:
                print(f"  Corrections on shift A:")
                for c in corr_a:
                    print(f"    [{c.rule}] {c.description} (conf={c.confidence:.2f})")
            if corr_b:
                print(f"  Corrections on shift B:")
                for c in corr_b:
                    print(f"    [{c.rule}] {c.description} (conf={c.confidence:.2f})")

            if not corr_a and not corr_b:
                print(f"  No corrections applied (raw fallback)")
                if raw != exp:
                    print(f"  -> Engine used raw naive ({raw}g) but resolved shows {exp}g")
                    print(f"  -> This means the resolved example applies a correction "
                          f"that the engine did not detect.")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST B: VDP same-day rule
    # ══════════════════════════════════════════════════════════════════════════

    print(f"\n{'='*100}")
    print(f"TEST B: VDP SAME-DAY RULE")
    print(f"{'='*100}")

    shift_vdp = collect_vdp_by_shift(shifts, config)
    day_vdp = collect_vdp_by_day(shifts, config)

    print(f"\n  Per-shift VDP:")
    for s in shifts:
        if s.index in shift_vdp:
            day = extract_day_number(s.name)
            print(f"    {s.name} (day {day}): {shift_vdp[s.index]:.0f}g  <- {s.vdp_texts}")

    print(f"\n  Per-day VDP totals:")
    for day in sorted(day_vdp.keys(), key=int):
        print(f"    Day {day}: {day_vdp[day]:.0f}g")

    # Day 28 specifically
    day28_vdp = day_vdp.get('28', 0.0)
    print(f"\n  Day 28 VDP: {day28_vdp:.0f}g")
    print(f"  Day 28 stock-based sold: {total_engine}g")
    print(f"  Day 28 TOTAL (stock + VDP): {total_engine + day28_vdp:.0f}g")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST C: Day-level aggregation
    # ══════════════════════════════════════════════════════════════════════════

    print(f"\n{'='*100}")
    print(f"TEST C: DAY-LEVEL AGGREGATION")
    print(f"{'='*100}")

    day_results = aggregate_by_day(results, shifts, config, tracked_cans)

    print(f"\n  {'DAY':>4} {'SHIFTS':>8} {'PERIODS':>8} {'STOCK_SOLD':>12} {'VDP':>8} {'OPENED':>7} {'LID_DSC':>8} {'DAY_TOTAL':>12}")
    print(f"  {'-'*80}")
    for dr in day_results:
        print(f"  {dr.day_label:>4} {len(dr.shifts):>8} {len(dr.periods):>8} "
              f"{dr.stock_sold_total:>12.0f} {dr.vdp_grams:>8.0f} "
              f"{dr.opened_cans:>7} {dr.lid_discount_grams:>8.0f} {dr.day_sold_total:>12.0f}")

    # Verify day 28
    day28 = next((dr for dr in day_results if dr.day_label == '28'), None)
    if day28:
        print(f"\n  Day 28 detail:")
        print(f"    Shifts: {day28.shifts}")
        print(f"    Periods: {day28.periods}")
        print(f"    Stock sold:    {day28.stock_sold_total:>8.0f}g")
        print(f"    VDP:           {day28.vdp_grams:>8.0f}g")
        print(f"    Opened cans:   {day28.opened_cans}")
        print(f"    Lid discount:  {day28.lid_discount_grams:>8.0f}g ({day28.opened_cans} x 280g)")
        print(f"    DAY TOTAL:     {day28.day_sold_total:>8.0f}g")

        if day28.opened_cans_detail:
            print(f"    Opening events:")
            for d in day28.opened_cans_detail:
                print(f"      - {d}")

        # VDP rule check: VDP from NOCHE 28 stays in day 28
        vdp_check = day28.vdp_grams == day28_vdp
        print(f"\n  VDP same-day rule: {'PASS' if vdp_check else 'FAIL'}")
        if not vdp_check:
            print(f"    Expected VDP={day28_vdp:.0f}g, got {day28.vdp_grams:.0f}g")

    # ══════════════════════════════════════════════════════════════════════════
    # TEST D: Completeness check
    # ══════════════════════════════════════════════════════════════════════════

    print(f"\n{'='*100}")
    print(f"TEST D: COMPLETENESS CHECK (all periods)")
    total_results = 0
    null_results = 0
    for r in results:
        for fname, fr in r.flavors.items():
            total_results += 1
            if fr.sold_grams is None:
                null_results += 1
    print(f"  Total flavor-period results: {total_results}")
    print(f"  Null results: {null_results}")
    print(f"  Completeness: {'PASS' if null_results == 0 else 'FAIL'}")

    # ══════════════════════════════════════════════════════════════════════════
    # FINAL VERDICT
    # ══════════════════════════════════════════════════════════════════════════

    print(f"\n{'='*100}")
    all_pass = (len(mismatches) == 0) and (null_results == 0)
    print(f"FINAL VERDICT: {'ALL TESTS PASS' if all_pass else 'SOME TESTS FAILED'}")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()
