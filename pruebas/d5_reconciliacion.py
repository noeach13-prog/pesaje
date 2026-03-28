"""Dia 5 - Tabla de reconciliacion RAW vs CORREGIDA v3
Con clasificacion CONSERVADOR / ESTIMADO por regla de >=2 planos independientes.
"""

import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# ============================================================
# DATOS DE CORRECCIONES
# ============================================================

corrections = [
    {
        'id': 'EXP-D5-01',
        'sabor': 'DULCE D LECHE',
        'raw': -6315,
        'corr': 240,
        'delta': 6555,
        'tipo': 'PF5 cerr omitida DIA',
        'planos': ['P1 (ab baja normal 1705->1470)',
                    'P2 (cerr 6555: 4 sightings DDL vs 1 DA)'],
        'n_planos': 2,
        'joint': 'DULCE AMORES',
        'nota': 'Bilateral con DA. Cerr 6555 pertenece a DDL por timeline.',
    },
    {
        'id': 'EXP-D5-01',
        'sabor': 'DULCE AMORES',
        'raw': 7235,
        'corr': 960,
        'delta': -6275,
        'tipo': 'PF3 phantom cerr (misregistro)',
        'planos': ['P1 (ab baja normal 2475->1515)',
                    'P2 (cerr 6555: 1-sighting en DA, 4 en DDL)'],
        'n_planos': 2,
        'joint': 'DULCE D LECHE',
        'nota': 'Bilateral con DDL. Ajuste_latas cambia de 280->0.',
    },
    {
        'id': 'EXP-D5-02',
        'sabor': 'VAINILLA',
        'raw': -6360,
        'corr': 85,
        'delta': 6445,
        'tipo': 'PF4 entrante no documentado',
        'planos': ['P1 (ab 5055->4970, -85g descenso normal)',
                    'P2 (cerr 6445 persiste D6D+D6N = can real)'],
        'n_planos': 2,
        'joint': None,
        'nota': 'Can real confirmado por 3 sightings posteriores.',
    },
    {
        'id': 'EXP-D5-03',
        'sabor': 'KITKAT',
        'raw': 6350,
        'corr': 230,
        'delta': -6120,
        'tipo': 'PF3 phantom cerrada',
        'planos': ['P1 (ab 4905->4630->4400->4395: declive lineal perfecto)',
                    'P2 (cerr 6400: 1-sighting, 0 en D3/D6D/D6N)'],
        'n_planos': 2,
        'joint': None,
        'nota': 'KIYKAT en NOCHE (PF8). Ab confirma venta ~230g/turno.',
    },
    {
        'id': 'EXP-D5-05',
        'sabor': 'CHOCOLATE',
        'raw': 7485,
        'corr': 855,
        'delta': -6630,
        'tipo': 'Pesaje variance entrante 100g',
        'planos': ['P2 (cerr 6640 estable 0g diff -> no apertura)',
                    'P3 (ent 6530~6630, unica explicacion viable)'],
        'n_planos': 2,
        'joint': None,
        'nota': 'Conf 0.75. P3 debil (100g=2x tolerancia). Pero sin P3, raw 7485g sin apertura es fisicamente imposible.',
    },
    {
        'id': 'EXP-D5-04',
        'sabor': 'PISTACHO',
        'raw': 1945,
        'corr': 1645,
        'delta': -300,
        'tipo': 'PF1 digit error 6630->6330',
        'planos': ['P2 (cerr 6330: 3 sightings D3/D5N/D6D vs 6630: 1-sighting)'],
        'n_planos': 1,
        'joint': None,
        'nota': 'P1 no discrimina (1945 y 1645 ambos plausibles). Solo P2.',
    },
    {
        'id': 'EXP-D5-06',
        'sabor': 'CH C/ALM',
        'raw': 1400,
        'corr': 1340,
        'delta': -60,
        'tipo': 'Pesaje variance cerr 60g',
        'planos': ['P2 (cerr 6615: 3 sightings vs 6675: 1-sighting)'],
        'n_planos': 1,
        'joint': None,
        'nota': 'P1 no discrimina (1400 y 1340 ambos razonables). Solo P2. Delta menor.',
    },
]

# ============================================================
# TABLA
# ============================================================

print("=" * 140)
print("DIA 5 -- RECONCILIACION RAW vs CORREGIDA v3")
print("=" * 140)
print()

# Header
print(f"{'EXP':<12} {'SABOR':<20} {'RAW':>7} {'CORR':>7} {'DELTA':>7} | {'TIPO':<32} | {'PLANOS':>2} | {'BAND':<12} | NOTA")
print("-" * 140)

delta_conserv = 0
delta_estim = 0
sabores_conserv = []
sabores_estim = []

for c in corrections:
    band = 'CONSERVADOR' if c['n_planos'] >= 2 else 'ESTIMADO'

    if band == 'CONSERVADOR':
        delta_conserv += c['delta']
        sabores_conserv.append(c['sabor'])
    else:
        delta_estim += c['delta']
        sabores_estim.append(c['sabor'])

    joint_mark = f" [CONJ: {c['joint']}]" if c['joint'] else ''
    planos_str = ' + '.join(c['planos'])

    print(f"{c['id']:<12} {c['sabor']:<20} {c['raw']:>+7} {c['corr']:>7} {c['delta']:>+7} | {c['tipo']:<32} | P:{c['n_planos']}  | {band:<12} | {c['nota']}")
    # Print planos on separate line
    print(f"{'':>12} {'':>20} {'':>7} {'':>7} {'':>7} | {planos_str}")
    print()

print("-" * 140)

total_delta = sum(c['delta'] for c in corrections)

print()
print("=" * 100)
print("VERIFICACION ARITMETICA")
print("=" * 100)
print()

# Individual deltas
print("Deltas individuales:")
for c in corrections:
    band = 'CONSERV' if c['n_planos'] >= 2 else 'ESTIM  '
    print(f"  {c['sabor']:<20}  {c['delta']:>+7}g   [{band}]")

print(f"  {'':->50}")
print(f"  {'SUMA DELTAS':<20}  {total_delta:>+7}g")
print()

print(f"  Venta RAW                         = {40095:>8}g")
print(f"  + Suma de todos los deltas         = {total_delta:>+8}g")
print(f"  -------------------------------------------")
print(f"  = Venta CORREGIDA                  = {40095 + total_delta:>8}g   (check: 33710)")
print()

assert 40095 + total_delta == 33710, f"ERROR: {40095 + total_delta} != 33710"

print("  VERIFICADO: 40095 + ({}) = 33710".format(total_delta))
print()

# ============================================================
# DESCOMPOSICION CONSERVADOR / ESTIMADO
# ============================================================

print("=" * 100)
print("BANDAS DE CONFIANZA")
print("=" * 100)
print()

raw = 40095

print("CONSERVADOR (>=2 planos independientes convergentes):")
print(f"  Sabores: {', '.join(sabores_conserv)}")
print(f"  Delta acumulado: {delta_conserv:+d}g")
print(f"  Total CONSERVADOR = {raw} + ({delta_conserv}) = {raw + delta_conserv}g")
print()

print("ESTIMADO (1 plano o plano debil):")
print(f"  Sabores: {', '.join(sabores_estim)}")
print(f"  Delta acumulado: {delta_estim:+d}g")
print(f"  Total ESTIMADO = {raw + delta_conserv} + ({delta_estim}) = {raw + delta_conserv + delta_estim}g")
print()

conserv_total = raw + delta_conserv
estim_total = raw + delta_conserv + delta_estim

print("=" * 100)
print("ECUACION FINAL")
print("=" * 100)
print()
print("  40095  (RAW)")
print(f"  {delta_conserv:+d}    (CONSERVADOR: DDL+DA bilateral, VAINILLA entrante, KITKAT phantom, CHOCOLATE entrante)")
print(f"  ------")
print(f"  {conserv_total}  (PISO CONSERVADOR -- 5 correcciones, >=2 planos cada una)")
print()
print(f"  {delta_estim:+d}      (ESTIMADO: PISTACHO digit, CH C/ALM pesaje)")
print(f"  ------")
print(f"  {estim_total}  (TECHO ESTIMADO -- 7 correcciones, incluye 1-plano)")
print()

# ============================================================
# TABLA RESUMEN FINAL
# ============================================================

latas = 4
ajuste_latas = latas * 280
vdp = 1495

print("=" * 100)
print("CIERRE DIA 5")
print("=" * 100)
print()
print(f"  {'Concepto':<40} {'Conservador':>12} {'Estimado':>12}")
print(f"  {'-'*40} {'-'*12} {'-'*12}")
print(f"  {'Venta stock':<40} {conserv_total:>12}g {estim_total:>12}g")
print(f"  {'Latas abiertas (4 x 280g ya incluido)':<40} {'':>12} {'':>12}")
print(f"  {'VDP (2vasos65 + 4/1 + 1cucurucho)':<40} {vdp:>12}g {vdp:>12}g")
print(f"  {'-'*40} {'-'*12} {'-'*12}")
print(f"  {'TOTAL DIA 5':<40} {conserv_total + vdp:>12}g {estim_total + vdp:>12}g")
print()
print(f"  Rango: [{estim_total + vdp}g , {conserv_total + vdp}g]")
print(f"  Diferencia entre bandas: {conserv_total - estim_total}g ({(conserv_total - estim_total)/(estim_total + vdp)*100:.1f}%)")
print()

# ============================================================
# JUSTIFICACION DE CHOCOLATE EN CONSERVADOR
# ============================================================
print("=" * 100)
print("NOTA: CHOCOLATE EN CONSERVADOR -- JUSTIFICACION")
print("=" * 100)
print("""
  CHOCOLATE tiene conf=0.75 (la mas baja). El P3 (entrante) es debil (100g gap).
  Sin embargo, se incluye en CONSERVADOR porque:

  1. P2 prueba que NO hubo apertura (cerr 6640 identica DIA/NOCHE).
  2. Sin apertura, raw=7485g es FISICAMENTE IMPOSIBLE:
     - abierta solo bajo 955g (1980->1025)
     - no se abrio ninguna cerrada
     - el unico stock disponible era ab + 2 entrantes + 1 cerrada
     - 7485g implicaria que se vendio MAS que todo el stock de abierta
  3. La UNICA forma de reconciliar es que ent 6530~6630 sea el mismo can.

  P2 (no apertura) + reductio (raw imposible) = correccion forzada.
  P3 solo provee el mecanismo, no es la evidencia primaria.

  Si se prefiere mover CHOCOLATE a ESTIMADO:
    CONSERVADOR = 40095 + ({}+6630) = {}g
    ESTIMADO = {} + (-300-60-6630) = 33710g
""".format(delta_conserv, raw + delta_conserv + 6630, raw + delta_conserv + 6630))
