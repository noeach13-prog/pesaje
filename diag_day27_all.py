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

shift_map = {s.name: s for s in shifts}

for r in results:
    if 'Viernes 27' in r.shift_a and 'Viernes 27' in r.shift_b:
        sa = shift_map[r.shift_a]
        sb = shift_map[r.shift_b]
        items = sorted(r.flavors.items(), key=lambda x: x[0])
        total = 0
        print(f"SABOR;ABIERTA DIA;ABIERTA NOCHE;CELIACA DIA;CELIACA NOCHE;CERRADAS DIA;CERRADAS NOCHE;ENTRANTES DIA;ENTRANTES NOCHE;TOTAL DIA;TOTAL NOCHE;VENTA;NOTA")
        for flavor, fdata in items:
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
            sold = fdata.sold_grams
            total += sold
            cerr_a = " + ".join(f"{c:.0f}" for c in a_cerr) if a_cerr else "-"
            cerr_b = " + ".join(f"{c:.0f}" for c in b_cerr) if b_cerr else "-"
            entr_a = " + ".join(f"{e:.0f}" for e in a_entr) if a_entr else "-"
            entr_b = " + ".join(f"{e:.0f}" for e in b_entr) if b_entr else "-"
            nota = ""
            if fdata.sold_grams < -500:
                # Check if restocking
                new_cerr = [c for c in b_cerr if not a_cerr or not any(abs(c-a)<50 for a in a_cerr)]
                if new_cerr:
                    nota = f"REPOSICION: cerrada nueva {'+'.join(f'{c:.0f}' for c in new_cerr)}g"
                else:
                    nota = "STOCK AUMENTO"
            if fdata.corrections_a or fdata.corrections_b:
                corrs = []
                for c in (fdata.corrections_a or []):
                    corrs.append(f"{c.rule}({c.action} {c.value_affected:.0f}g)")
                for c in (fdata.corrections_b or []):
                    corrs.append(f"{c.rule}({c.action} {c.value_affected:.0f}g)")
                nota = "CORRECCION: " + ", ".join(corrs)
            print(f"{flavor};{a_ab:.0f};{b_ab:.0f};{a_cel:.0f};{b_cel:.0f};{cerr_a};{cerr_b};{entr_a};{entr_b};{a_tot:.0f};{b_tot:.0f};{sold:.0f};{nota}")
        print(f"TOTAL;;;;;;;;;;;;;{total:.0f}")
        break
