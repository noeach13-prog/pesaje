import sys, os
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number
from inference import build_trajectories
from calculator import calculate_sold_grams, aggregate_by_day

config = PesajeConfig.default()
xlsx = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx'
shifts, vdp_entries = load_shifts_v2(xlsx)
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_grams(periods, trajectories, config)
day_results = aggregate_by_day(results, vdp_entries, tracked_cans, shifts)

TARGET_DAY = 25

# Show shifts for this day
day_shifts = [s for s in shifts if extract_day_number(s.name) == TARGET_DAY and 'STOCK' not in s.name]
print(f"{'='*120}")
print(f"DIA {TARGET_DAY} - Turnos: {[s.name for s in day_shifts]}")
print(f"Periodos: {[f'{r.shift_a.name} -> {r.shift_b.name}' for r in results if extract_day_number(r.shift_a.name) == TARGET_DAY]}")
print(f"{'='*120}")

# Period-level detail
day_periods = [r for r in results if extract_day_number(r.shift_a.name) == TARGET_DAY]
print(f"\nFound {len(day_periods)} period-level results for day {TARGET_DAY}\n")

for r in day_periods:
    print(f"  Periodo: {r.shift_a.name} -> {r.shift_b.name}")
    print(f"  {'SABOR':<25} {'VENDIDO':>8} {'RAW':>8} {'DIFF':>8} {'CONF':>5} CORRECCIONES")
    print(f"  {'-'*100}")
    subtotal_engine = 0
    subtotal_raw = 0
    suspects = []
    for fr in sorted(r.flavor_results, key=lambda x: x.flavor):
        eng = round(fr.sold_grams)
        raw = round(fr.raw_naive_sold)
        diff = eng - raw
        corr_str = ', '.join(
            f"{'A' if c.action=='added' else 'R'}:{c.rule}({c.value_affected:.0f}g)"
            for c in (fr.corrections or [])
        )
        flag = ' *' if diff != 0 else ''
        subtotal_engine += eng
        subtotal_raw += raw
        print(f"  {fr.flavor:<25} {eng:>8} {raw:>8} {diff:>+8} {fr.confidence:>5.2f} {corr_str}{flag}")
        # Flag suspects
        if eng < -200 or eng > 6000 or abs(diff) > 500:
            suspects.append((fr.flavor, eng, raw, diff, corr_str))
    print(f"  {'-'*100}")
    print(f"  {'SUBTOTAL':<25} {subtotal_engine:>8} {subtotal_raw:>8} {subtotal_engine-subtotal_raw:>+8}")

# Day aggregate
print(f"\n{'='*120}")
print(f"AGREGADO DIA {TARGET_DAY}")
print(f"{'='*120}")
dr = [d for d in day_results if d.day_number == TARGET_DAY]
if dr:
    d = dr[0]
    print(f"SABOR                      VENDIDO")
    print(f"-----------------------------------")
    for flavor in sorted(d.flavor_totals.keys()):
        print(f"{flavor:<25} {round(d.flavor_totals[flavor]):>8}")

    print(f"\n{'='*60}")
    print(f"LATAS ABIERTAS:")
    print(f"  Total: {d.opened_can_count} latas")
    for ev in d.opening_events:
        print(f"  - {ev}")
    print(f"  Lid discount: {d.lid_discount_grams}g ({d.opened_can_count} x 280g)")

    print(f"\n{'='*60}")
    print(f"VDP dia {TARGET_DAY}: {d.vdp_grams}g")

    print(f"\n{'='*60}")
    print(f"RESUMEN DIA {TARGET_DAY}:")
    print(f"  Stock-based sold:     {d.stock_sold_total}g")
    print(f"  VDP:                   {d.vdp_grams}g")
    print(f"  Latas cambiadas:        {d.lid_discount_grams}g ({d.opened_can_count} latas)")
    print(f"  -----------------------------")
    print(f"  TOTAL DIA:            {d.day_sold_total}g")
    print(f"  (= stock + VDP - lid_discount)")

# Multi-shift analysis for suspects
print(f"\n{'='*120}")
print(f"ANALISIS MULTI-TURNO DE SABORES SOSPECHOSOS")
print(f"{'='*120}")

# Get shifts around day 25 (day 24 NOCHE through day 27 DIA)
context_shifts = [s for s in shifts if 'STOCK' not in s.name]
context_range = range(
    min(s.index for s in day_shifts) - 2,
    max(s.index for s in day_shifts) + 3
)
context = [s for s in context_shifts if s.index in context_range]

for r in day_periods:
    for fr in sorted(r.flavor_results, key=lambda x: x.flavor):
        eng = round(fr.sold_grams)
        raw = round(fr.raw_naive_sold)
        if eng < -200 or eng > 6000 or abs(eng - raw) > 500:
            flavor = fr.flavor
            print(f"\n--- {flavor} (engine={eng}, raw={raw}) ---")
            for s in context:
                obs = s.flavors.get(flavor)
                if obs:
                    cerr_str = ', '.join(f'{c:.0f}' for c in obs.cerradas)
                    ent_str = ', '.join(f'{e:.0f}' for e in obs.entrantes)
                    day_marker = ' <<<' if s in day_shifts else ''
                    print(f"  idx{s.index:>2} {s.name:<30} ab={obs.abierta:<8.0f} cerr=[{cerr_str:<20}] ent=[{ent_str:<15}]{day_marker}")
                else:
                    print(f"  idx{s.index:>2} {s.name:<30} -- no data --")
            # Tracker info
            print(f"  Tracker cans:")
            for can in tracked_cans.get(flavor, []):
                relevant = [sg for sg in can.sightings if sg.shift_index in context_range]
                if relevant:
                    sightings_str = ', '.join(f'idx{sg.shift_index}:{sg.weight:.0f}' for sg in can.sightings if sg.shift_index in context_range)
                    print(f"    Can {can.id[:8]} [{can.status}] n={len(can.sightings)}: {sightings_str}")
                    if can.opened_at and can.opened_at in context_range:
                        print(f"      -> opened at idx{can.opened_at}")
            # Corrections
            if fr.corrections:
                print(f"  Corrections applied:")
                for c in fr.corrections:
                    print(f"    [{c.rule}] {c.description} (conf={c.confidence:.2f})")
