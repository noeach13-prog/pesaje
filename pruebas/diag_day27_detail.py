import sys
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')
from config import PesajeConfig
from parser import load_shifts_v2
from pairer import build_timeline, find_resets, generate_periods, extract_day_number, collect_vdp_by_day
from inference import build_trajectories
from calculator import calculate_sold_v2

config = PesajeConfig.default()
shifts, _ = load_shifts_v2(r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx')
shifts = build_timeline(shifts)
resets = find_resets(shifts)
periods = generate_periods(shifts, resets)
trajectories, tracked_cans = build_trajectories(shifts, resets, config)
results = calculate_sold_v2(trajectories, periods, shifts)

shift_map = {s.name: s for s in shifts}

# Period: Viernes 27 DIA -> NOCHE
for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        sa = shift_map[r.shift_a]
        sb = shift_map[r.shift_b]

        print(f"PERIODO: {r.shift_a} -> {r.shift_b}")
        print("=" * 120)

        items = sorted(r.flavors.items(), key=lambda x: x[0])
        total_sold = 0

        # Categories
        restocking = []
        corrected = []
        normal = []

        for flavor, fdata in items:
            total_sold += fdata.sold_grams
            diff = fdata.sold_grams - fdata.raw_sold
            if abs(diff) > 50:
                corrected.append((flavor, fdata))
            elif fdata.raw_sold < -500:
                restocking.append((flavor, fdata))
            else:
                normal.append((flavor, fdata))

        # VENTAS NORMALES
        print(f"\n--- VENTAS NORMALES ({len(normal)} sabores) ---")
        print(f"  {'SABOR':25s} {'ABIERTA':>14s} {'CELIACA':>14s} {'CERRADAS':>30s} {'ENTRANTES':>25s} {'TOTAL':>14s} {'VENTA':>8s}")
        print(f"  {'':25s} {'DIA->NOC':>14s} {'DIA->NOC':>14s} {'DIA':>14s}{'NOC':>16s} {'DIA':>12s}{'NOC':>13s} {'DIA->NOC':>14s} {'':>8s}")
        print("  " + "-" * 110)
        normal_total = 0
        for flavor, fdata in sorted(normal, key=lambda x: -x[1].sold_grams):
            obs_a = sa.flavors.get(flavor)
            obs_b = sb.flavors.get(flavor)
            a_ab = obs_a.abierta if obs_a else 0
            b_ab = obs_b.abierta if obs_b else 0
            a_cel = obs_a.celiaca if obs_a else 0
            b_cel = obs_b.celiaca if obs_b else 0
            a_cerr = obs_a.cerradas if obs_a else []
            b_cerr = obs_b.cerradas if obs_b else []
            a_entr = obs_a.entrantes if obs_a else []
            b_entr = obs_b.entrantes if obs_b else []
            a_tot = obs_a.total if obs_a else 0
            b_tot = obs_b.total if obs_b else 0

            cerr_a_s = ",".join(f"{c:.0f}" for c in a_cerr) if a_cerr else "-"
            cerr_b_s = ",".join(f"{c:.0f}" for c in b_cerr) if b_cerr else "-"
            entr_a_s = ",".join(f"{e:.0f}" for e in a_entr) if a_entr else "-"
            entr_b_s = ",".join(f"{e:.0f}" for e in b_entr) if b_entr else "-"

            normal_total += fdata.sold_grams
            print(f"  {flavor:25s} {a_ab:6.0f}->{b_ab:<6.0f} {a_cel:6.0f}->{b_cel:<6.0f} {cerr_a_s:>14s}->{cerr_b_s:<14s} {entr_a_s:>12s}->{entr_b_s:<12s} {a_tot:6.0f}->{b_tot:<6.0f} {fdata.sold_grams:7.0f}")
        print(f"  {'SUBTOTAL VENTAS NORMALES':70s} {normal_total:7.0f}g")

        # REPOSICION
        if restocking:
            print(f"\n--- REPOSICION: stock nuevo aparecio en NOCHE ({len(restocking)} sabores) ---")
            restock_total = 0
            for flavor, fdata in restocking:
                obs_a = sa.flavors.get(flavor)
                obs_b = sb.flavors.get(flavor)
                a_ab = obs_a.abierta if obs_a else 0
                b_ab = obs_b.abierta if obs_b else 0
                a_cerr = obs_a.cerradas if obs_a else []
                b_cerr = obs_b.cerradas if obs_b else []
                a_entr = obs_a.entrantes if obs_a else []
                b_entr = obs_b.entrantes if obs_b else []
                a_tot = obs_a.total if obs_a else 0
                b_tot = obs_b.total if obs_b else 0

                # Identify what appeared
                new_cerr = []
                for c in b_cerr:
                    if not a_cerr or not any(abs(c - a) < 50 for a in a_cerr):
                        new_cerr.append(c)

                restock_total += fdata.sold_grams
                cerr_a_s = ",".join(f"{c:.0f}" for c in a_cerr) if a_cerr else "-"
                cerr_b_s = ",".join(f"{c:.0f}" for c in b_cerr) if b_cerr else "-"
                entr_a_s = ",".join(f"{e:.0f}" for e in a_entr) if a_entr else "-"
                entr_b_s = ",".join(f"{e:.0f}" for e in b_entr) if b_entr else "-"
                new_str = f"  <- cerrada nueva {','.join(f'{c:.0f}' for c in new_cerr)}g" if new_cerr else ""
                print(f"  {flavor:25s} ab={a_ab:.0f}->{b_ab:.0f}  cerr=[{cerr_a_s}]->[{cerr_b_s}]  entr=[{entr_a_s}]->[{entr_b_s}]  total={a_tot:.0f}->{b_tot:.0f}  venta={fdata.sold_grams:.0f}g{new_str}")
            print(f"  SUBTOTAL REPOSICION:                                                         {restock_total:7.0f}g")

        # CORRECCIONES
        if corrected:
            print(f"\n--- CORRECCIONES DEL ENGINE ({len(corrected)} sabores) ---")
            corr_total = 0
            for flavor, fdata in corrected:
                corr_total += fdata.sold_grams
                print(f"  {flavor:25s} engine={fdata.sold_grams:7.0f}g  raw={fdata.raw_sold:7.0f}g  diff={fdata.sold_grams - fdata.raw_sold:+.0f}g")
                for c in (fdata.corrections_a or []):
                    print(f"    DIA:   {c.rule} -> {c.action} {c.value_affected:.0f}g (conf={c.confidence:.2f})")
                    print(f"           {c.description}")
                for c in (fdata.corrections_b or []):
                    print(f"    NOCHE: {c.rule} -> {c.action} {c.value_affected:.0f}g (conf={c.confidence:.2f})")
                    print(f"           {c.description}")
            print(f"  SUBTOTAL CORRECCIONES:                                                       {corr_total:7.0f}g")

        print(f"\n{'='*80}")
        print(f"TOTAL STOCK-SOLD:  {normal_total:7.0f} + {sum(f.sold_grams for _,f in restocking):7.0f} + {sum(f.sold_grams for _,f in corrected):7.0f} = {total_sold:7.0f}g")
        break

# Opened cans on day 27
print(f"\n{'='*80}")
print("LATAS ABIERTAS DIA 27:")
day27_indices = set()
for s in shifts:
    if not s.is_stock_sheet and extract_day_number(s.name) == '27':
        day27_indices.add(s.index)
count = 0
for flavor, cans_list in sorted(tracked_cans.items()):
    for can in cans_list:
        if can.status == 'opened' and can.opened_at in day27_indices:
            count += 1
            shift_name = [s.name for s in shifts if s.index == can.opened_at][0]
            # Show abierta jump
            prev_s = None
            curr_s = None
            for s in sorted(shifts, key=lambda x: x.index):
                if s.index == can.opened_at:
                    curr_s = s
                elif s.index < can.opened_at and not s.is_stock_sheet:
                    prev_s = s
            if prev_s and curr_s:
                obs_prev = prev_s.flavors.get(flavor)
                obs_curr = curr_s.flavors.get(flavor)
                if obs_prev and obs_curr:
                    jump = obs_curr.abierta - obs_prev.abierta
                    print(f"  {flavor:25s} lata {can.last_weight:.0f}g abierta en {shift_name}  (abierta: {obs_prev.abierta:.0f} -> {obs_curr.abierta:.0f}, salto={jump:.0f}g)")
                else:
                    print(f"  {flavor:25s} lata {can.last_weight:.0f}g abierta en {shift_name}")
            else:
                print(f"  {flavor:25s} lata {can.last_weight:.0f}g abierta en {shift_name}")
print(f"  Total: {count} latas abiertas -> lid discount = {count * 280}g")

# VDP
print(f"\n{'='*80}")
print("VDP DIA 27:")
day_vdp = collect_vdp_by_day(shifts, config)
vdp = day_vdp.get('27', 0)
# Show VDP items
for s in shifts:
    if not s.is_stock_sheet and extract_day_number(s.name) == '27':
        if hasattr(s, 'vdp_texts') and s.vdp_texts:
            from pairer import convert_vdp
            for txt in s.vdp_texts:
                grams = convert_vdp(txt, config)
                print(f"  {s.name}: '{txt}' = {grams:.0f}g")
print(f"  Total VDP: {vdp:.0f}g")

print(f"\n{'='*80}")
print("FORMULA FINAL DIA 27:")
print(f"  Stock sold:      {total_sold:7.0f}g")
print(f"  + VDP:           {vdp:7.0f}g")
print(f"  - Lid discount:  {count * 280:7.0f}g  ({count} latas x 280g)")
print(f"  = TOTAL DIA:     {total_sold + vdp - count * 280:7.0f}g")
