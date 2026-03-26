"""Debug D28: comparar pipeline v3 vs ground truth"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pesaje_v3.capa1_parser import cargar_dia
from pesaje_v3.capa2_contrato import calcular_contabilidad
from pesaje_v3.capa3_motor import clasificar, _aplicar_pf8

EXCEL = r"C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx"
datos = cargar_dia(EXCEL, 28)
_aplicar_pf8(datos)
contabilidad = calcular_contabilidad(datos)
c3 = clasificar(datos, contabilidad)

# GT corrections and expected values
gt_corrections = {
    'CHOCOLATE':      {'raw': -3635, 'corregido': 2910,  'delta': +6545, 'tipo': 'cerr omitida DIA +6545'},
    'SAMBAYON':       {'raw': 6825,  'corregido': 655,   'delta': -6450, 'tipo': 'phantom cerr 6450 DIA'},  # GT says 7105->655 but raw might differ
    'MARACUYA':       {'raw': -5825, 'corregido': 555,   'delta': +6380, 'tipo': 'entrante dup NOCHE'},
    'CHOCOLATE DUBAI':{'raw': 7580,  'corregido': 1740,  'delta': -6400, 'tipo': 'phantom cerr 6400 DIA, 1 lata no 2'},
    'PISTACHO':       {'raw': 7620,  'corregido': 1550,  'delta': -6350, 'tipo': 'phantom cerr 6350 DIA, 0 latas no 1'},
}

print("=== D28: Pipeline vs Ground Truth ===\n")
print(f"{'SABOR':<22} {'STATUS':<12} {'RAW_PIPE':>8} {'RAW_GT':>8} {'CORR_GT':>8} {'MATCH':>6}")
print('-' * 75)

# Check GT sabores
for nombre, gt in gt_corrections.items():
    sc = contabilidad.sabores.get(nombre)
    cl = c3.sabores.get(nombre)
    if sc:
        raw_match = 'OK' if sc.venta_raw == gt['raw'] else f"!{sc.venta_raw}"
        status = cl.status.value if cl else '?'
        print(f"{nombre:<22} {status:<12} {sc.venta_raw:>8}g {gt['raw']:>8}g {gt['corregido']:>8}g {raw_match:>6}")
    else:
        print(f"{nombre:<22} NOT FOUND")

# Total check
gt_total_venta = 51165  # sum of all VENDIDO corregidos
gt_latas = 5  # v3 count
gt_vdp = 3020

print(f"\n=== Totales ===")
print(f"Pipeline RAW:   {contabilidad.venta_raw_total:>8}g")
print(f"GT venta stock: {gt_total_venta:>8}g")
print(f"GT delta total: {sum(g['delta'] for g in gt_corrections.values()):>+8}g")
print(f"Pipeline RAW + GT deltas = {contabilidad.venta_raw_total + sum(g['delta'] for g in gt_corrections.values()):>8}g")
print(f"Diferencia vs GT: {contabilidad.venta_raw_total + sum(g['delta'] for g in gt_corrections.values()) - gt_total_venta:>+8}g")

print(f"\nPipeline VDP: {contabilidad.vdp_total:>6}g  (GT: {gt_vdp}g)")
print(f"Pipeline latas: {sum(s.n_latas for s in contabilidad.sabores.values())}  (GT: {gt_latas})")

# Check all 5 GT cases were escalated
print(f"\n=== Escalados vs GT ===")
escalados = {k: v for k, v in c3.sabores.items()
             if v.status.value in ('SENAL', 'COMPUESTO')}
gt_names = set(gt_corrections.keys())
escalated_names = set(escalados.keys())
print(f"GT requiere correccion: {sorted(gt_names)}")
print(f"Pipeline escalo: {sorted(escalated_names)}")
print(f"GT capturados: {sorted(gt_names & escalated_names)}")
print(f"GT no capturados: {sorted(gt_names - escalated_names)}")
print(f"Escalados extra (no en GT): {sorted(escalated_names - gt_names)}")

# Show raw for the extra escalados
extras = escalated_names - gt_names
if extras:
    print(f"\n=== Escalados extra - detalle ===")
    for nombre in sorted(extras):
        sc = contabilidad.sabores[nombre]
        cl = c3.sabores[nombre]
        flags = ', '.join(f.codigo for f in cl.flags)
        print(f"  {nombre:<22} raw={sc.venta_raw:>6}g  flags: {flags}")
