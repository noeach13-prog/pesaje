"""Desglose completo del día 26: per-flavor, VDP, latas, total."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import (build_timeline, find_resets, generate_periods, extract_day_number)
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

INPUT = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'

config = PesajeConfig.default()
shifts, annotations = load_shifts_v2(INPUT)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)
day_results = aggregate_by_day(results, shifts, config, tracked_cans)

# ── Find day 26 ──
day26 = None
for d in day_results:
    if d.day_label == '26':
        day26 = d
        break

if day26 is None:
    print("ERROR: Day 26 not found!")
    sys.exit(1)

# ── Find period-level results for day 26 ──
day26_periods = []
for r in results:
    da = extract_day_number(r.shift_a)
    db = extract_day_number(r.shift_b)
    if da == '26' and db == '26':
        day26_periods.append(r)

# ── Header ──
print("=" * 120)
print(f"DIA 26 - Turnos: {day26.shifts}")
print(f"Periodos: {day26.periods}")
print("=" * 120)

print(f"\nFound {len(day26_periods)} period-level results for day 26")

# ── Per-period breakdown ──
for pr in day26_periods:
    print(f"\n  Periodo: {pr.shift_a} -> {pr.shift_b}")
    print(f"  {'SABOR':<25} {'VENDIDO':>8} {'RAW':>8} {'DIFF':>7} {'CONF':>5} CORRECCIONES")
    print(f"  {'-' * 100}")
    period_sold = 0
    period_raw = 0
    for fname in sorted(pr.flavors.keys()):
        fr = pr.flavors[fname]
        sold = round(fr.sold_grams)
        raw = round(fr.raw_sold)
        diff = sold - raw
        period_sold += sold
        period_raw += raw
        corr_str = ''
        all_corr = fr.corrections_a + fr.corrections_b
        if all_corr:
            parts = []
            for c in all_corr:
                parts.append(f"{c.action[0].upper()}:{c.rule}({c.value_affected:.0f}g)")
            corr_str = ', '.join(parts)
        marker = ' *' if diff != 0 else ''
        print(f"  {fname:<25} {sold:>8} {raw:>8} {diff:>+7} {fr.confidence:>5.2f} {corr_str}{marker}")
    print(f"  {'-' * 100}")
    print(f"  {'SUBTOTAL':<25} {period_sold:>8} {period_raw:>8} {period_sold - period_raw:>+7}")

# ── Day-level aggregate by flavor ──
print(f"\n{'=' * 120}")
print("AGREGADO DIA 26 (todos los periodos)")
print(f"{'=' * 120}")
print(f"{'SABOR':<25} {'VENDIDO':>8}")
print(f"{'-' * 35}")
for fname in sorted(day26.flavors.keys()):
    v = round(day26.flavors[fname])
    print(f"{fname:<25} {v:>8}")

# ── Latas abiertas ──
print(f"\n{'=' * 60}")
print("LATAS ABIERTAS:")
print(f"  Total: {day26.opened_cans} latas")
for detail in day26.opened_cans_detail:
    print(f"  - {detail}")
print(f"  Lid discount: {day26.lid_discount_grams:.0f}g ({day26.opened_cans} x 280g)")

# ── VDP ──
print(f"\n{'=' * 60}")
print(f"VDP dia 26: {day26.vdp_grams:.0f}g")

# ── Resumen final ──
print(f"\n{'=' * 60}")
print(f"RESUMEN DIA 26:")
print(f"  Stock-based sold:  {day26.stock_sold_total:>8.0f}g")
print(f"  VDP:               {day26.vdp_grams:>8.0f}g")
print(f"  Latas cambiadas:   {day26.lid_discount_grams:>8.0f}g ({day26.opened_cans} latas)")
print(f"  -----------------------------")
print(f"  TOTAL DIA:         {day26.day_sold_total:>8.0f}g")
print(f"  (= stock + VDP - lid_discount)")
