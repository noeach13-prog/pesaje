"""Desglose completo del día 25: per-flavor, VDP, latas, total + análisis multi-turno."""
import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from config import PesajeConfig
from parser import load_shifts_v2
from pairer import (build_timeline, find_resets, generate_periods, extract_day_number)
from inference import build_trajectories
from calculator import calculate_sold_v2, aggregate_by_day

INPUT = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'
TARGET = '25'

config = PesajeConfig.default()
shifts, annotations = load_shifts_v2(INPUT)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)
day_results = aggregate_by_day(results, shifts, config, tracked_cans)

# ── Find target day ──
day_obj = None
for d in day_results:
    if d.day_label == TARGET:
        day_obj = d
        break

if day_obj is None:
    print(f"ERROR: Day {TARGET} not found!")
    sys.exit(1)

# ── Find period-level results ──
day_periods = []
for r in results:
    da = extract_day_number(r.shift_a)
    db = extract_day_number(r.shift_b)
    if da == TARGET and db == TARGET:
        day_periods.append(r)

# ── Find shifts for this day and context (±2 shifts) ──
day_shifts = [s for s in shifts if extract_day_number(s.name) == TARGET and 'STOCK' not in s.name]
day_indices = set(s.index for s in day_shifts)
min_idx = min(day_indices) - 2
max_idx = max(day_indices) + 3
context_range = range(min_idx, max_idx)
context_shifts = [s for s in shifts if s.index in context_range and 'STOCK' not in s.name]

# ── Header ──
print("=" * 120)
print(f"DIA {TARGET} - Turnos: {day_obj.shifts}")
print(f"Periodos: {day_obj.periods}")
print("=" * 120)

print(f"\nFound {len(day_periods)} period-level results for day {TARGET}\n")

# ── Per-period breakdown ──
suspects = []
for pr in day_periods:
    print(f"  Periodo: {pr.shift_a} -> {pr.shift_b}")
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
        # Flag suspects
        if sold < -200 or sold > 5500 or abs(diff) > 300:
            suspects.append((fname, sold, raw, diff, corr_str, fr))
    print(f"  {'-' * 100}")
    print(f"  {'SUBTOTAL':<25} {period_sold:>8} {period_raw:>8} {period_sold - period_raw:>+7}")

# ── Day-level aggregate by flavor ──
print(f"\n{'=' * 120}")
print(f"AGREGADO DIA {TARGET} (todos los periodos)")
print(f"{'=' * 120}")
print(f"{'SABOR':<25} {'VENDIDO':>8}")
print(f"{'-' * 35}")
for fname in sorted(day_obj.flavors.keys()):
    v = round(day_obj.flavors[fname])
    print(f"{fname:<25} {v:>8}")

# ── Latas abiertas ──
print(f"\n{'=' * 60}")
print("LATAS ABIERTAS:")
print(f"  Total: {day_obj.opened_cans} latas")
for detail in day_obj.opened_cans_detail:
    print(f"  - {detail}")
print(f"  Lid discount: {day_obj.lid_discount_grams:.0f}g ({day_obj.opened_cans} x 280g)")

# ── VDP ──
print(f"\n{'=' * 60}")
print(f"VDP dia {TARGET}: {day_obj.vdp_grams:.0f}g")

# ── Resumen final ──
print(f"\n{'=' * 60}")
print(f"RESUMEN DIA {TARGET}:")
print(f"  Stock-based sold:  {day_obj.stock_sold_total:>8.0f}g")
print(f"  VDP:               {day_obj.vdp_grams:>8.0f}g")
print(f"  Latas cambiadas:   {day_obj.lid_discount_grams:>8.0f}g ({day_obj.opened_cans} latas)")
print(f"  -----------------------------")
print(f"  TOTAL DIA:         {day_obj.day_sold_total:>8.0f}g")
print(f"  (= stock + VDP - lid_discount)")

# ── Multi-shift analysis for suspects ──
if suspects:
    print(f"\n{'=' * 120}")
    print(f"ANALISIS MULTI-TURNO DE SABORES SOSPECHOSOS")
    print(f"{'=' * 120}")
    for fname, sold, raw, diff, corr_str, fr in suspects:
        print(f"\n--- {fname} (engine={sold}, raw={raw}, diff={diff:+d}) ---")
        print(f"  Correcciones: {corr_str or 'ninguna'}")
        # Raw timeline
        for s in context_shifts:
            obs = s.flavors.get(fname)
            if obs:
                cerr_str = ', '.join(f'{c:.0f}' for c in obs.cerradas)
                ent_str = ', '.join(f'{e:.0f}' for e in obs.entrantes)
                day_marker = ' <<<' if s.index in day_indices else ''
                print(f"  idx{s.index:>2} {s.name:<30} ab={obs.abierta:<8.0f} "
                      f"cerr=[{cerr_str:<20}] ent=[{ent_str:<15}]{day_marker}")
            else:
                print(f"  idx{s.index:>2} {s.name:<30} -- no data --")
        # Tracker info
        print(f"  Tracker cans:")
        for can in tracked_cans.get(fname, []):
            relevant = [sg for sg in can.sightings if sg.shift_index in context_range]
            if relevant:
                sightings_str = ', '.join(f'idx{sg.shift_index}:{sg.weight:.0f}' for sg in relevant)
                print(f"    Can {can.id[:8]} [{can.status}] n={len(can.sightings)}: {sightings_str}")
                if can.opened_at and can.opened_at in context_range:
                    print(f"      -> opened at idx{can.opened_at}")
        # Corrections detail
        all_corr = fr.corrections_a + fr.corrections_b
        if all_corr:
            print(f"  Detalle correcciones:")
            for c in all_corr:
                print(f"    [{c.rule}] {c.description} (conf={c.confidence:.2f})")
