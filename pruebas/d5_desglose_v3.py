"""Day 5 — Desglose completo v3 con correcciones
Fuente: Febrero San Martin 2026 (1).xlsx
Hojas: Jueves 5 (DIA) y Jueves 5 (NOCHE)
Contexto: Martes 3, Viernes 6 (Día/Noche)
Nota: Miércoles 4 está vacío (0 sabores).
"""

# =============================================
# CAPA 1: DATOS CRUDOS
# =============================================

dia_raw = {
    'CADBURY':       {'ab':5175, 'cerr':[6360], 'ent':[]},
    'AMERICANA':     {'ab':760,  'cerr':[6700], 'ent':[6645]},
    'ANANA':         {'ab':1900, 'cerr':[6785], 'ent':[]},
    'B, SPLIT':      {'ab':5675, 'cerr':[], 'ent':[]},
    'CHOCOLATE':     {'ab':1980, 'cerr':[6640], 'ent':[6530, 6475]},
    'AMARGO':        {'ab':5265, 'cerr':[], 'ent':[6765]},
    'BLANCO':        {'ab':1055, 'cerr':[6545], 'ent':[]},
    'CH C/ALM':      {'ab':2385, 'cerr':[6675], 'ent':[6665]},
    'CH AMORES':     {'ab':6395, 'cerr':[6675], 'ent':[]},
    'DOS CORAZONES': {'ab':980,  'cerr':[6535], 'ent':[]},
    'CABSHA':        {'ab':3665, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':775,  'cerr':[6630], 'ent':[6745]},
    'DULCE C/NUEZ':  {'ab':6875, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':1705, 'cerr':[6685], 'ent':[]},
    'D. GRANIZADO':  {'ab':5680, 'cerr':[], 'ent':[6710, 6775]},
    'DULCE AMORES':  {'ab':2475, 'cerr':[6700, 6555], 'ent':[6795]},
    'SUPER':         {'ab':3835, 'cerr':[], 'ent':[]},
    'DURAZNO':       {'ab':6120, 'cerr':[6605], 'ent':[]},
    'FERRERO':       {'ab':5025, 'cerr':[], 'ent':[6585]},
    'FLAN':          {'ab':3695, 'cerr':[], 'ent':[6675]},
    'CEREZA':        {'ab':6460, 'cerr':[], 'ent':[6600]},
    'FRAMBUEZA':     {'ab':4535, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':5190, 'cerr':[6430], 'ent':[6775]},
    'FRUTILLA REINA':{'ab':3350, 'cerr':[6790], 'ent':[]},
    'FRUTILLA AGUA': {'ab':3090, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':2025, 'cerr':[6495], 'ent':[]},
    'GRANIZADO':     {'ab':3195, 'cerr':[6725], 'ent':[]},
    'LIMON':         {'ab':4345, 'cerr':[6360], 'ent':[6425]},
    'MANTECOL':      {'ab':1135, 'cerr':[6670], 'ent':[]},
    'MANZANA':       {'ab':765,  'cerr':[6160], 'ent':[]},
    'MARROC':        {'ab':1645, 'cerr':[6570], 'ent':[]},
    'MASCARPONE':    {'ab':2100, 'cerr':[], 'ent':[6490]},
    'MENTA':         {'ab':1695, 'cerr':[6610], 'ent':[]},
    'MIX DE FRUTA':  {'ab':6710, 'cerr':[], 'ent':[]},
    'MOUSSE LIMON':  {'ab':4700, 'cerr':[], 'ent':[]},
    'SAMBAYON':      {'ab':2720, 'cerr':[6365], 'ent':[]},
    'SAMBAYON AMORES':{'ab':1030, 'cerr':[6255], 'ent':[]},
    'TRAMONTANA':    {'ab':2420, 'cerr':[6620, 6735], 'ent':[]},
    'TIRAMIZU':      {'ab':2885, 'cerr':[], 'ent':[]},
    'VAINILLA':      {'ab':5055, 'cerr':[], 'ent':[]},
    'LEMON PIE':     {'ab':2870, 'cerr':[6540], 'ent':[]},
    'IRLANDESA':     {'ab':775,  'cerr':[], 'ent':[]},
    'NUTE':          {'ab':4375, 'cerr':[6695], 'ent':[]},
    'RUSA':          {'ab':3705, 'cerr':[], 'ent':[]},
    'FRANUI':        {'ab':1095, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':2510, 'cerr':[6520], 'ent':[]},
    'KINDER':        {'ab':2040, 'cerr':[6485], 'ent':[]},
    'MARACUYA':      {'ab':4230, 'cerr':[], 'ent':[]},
    'PISTACHO':      {'ab':3140, 'cerr':[6630], 'ent':[]},
    'CHOCOLATE DUBAI':{'ab':0,   'cerr':[], 'ent':[]},
    'KITKAT':        {'ab':4630, 'cerr':[6400], 'ent':[]},
    'COCO':          {'ab':4505, 'cerr':[], 'ent':[]},
}

noche_raw = {
    'CADBURY':       {'ab':3805, 'cerr':[6410], 'ent':[]},
    'AMERICANA':     {'ab':6805, 'cerr':[], 'ent':[6645]},
    'ANANA':         {'ab':1190, 'cerr':[6785], 'ent':[]},
    'B, SPLIT':      {'ab':4805, 'cerr':[], 'ent':[]},
    'CHOCOLATE':     {'ab':1025, 'cerr':[6640], 'ent':[6630, 6475]},
    'AMARGO':        {'ab':3790, 'cerr':[], 'ent':[6785]},
    'BLANCO':        {'ab':645,  'cerr':[6545], 'ent':[]},
    'CH C/ALM':      {'ab':1045, 'cerr':[6615], 'ent':[6665]},
    'CH AMORES':     {'ab':5230, 'cerr':[6665], 'ent':[]},
    'DOS CORAZONES': {'ab':700,  'cerr':[6535], 'ent':[]},
    'CABSHA':        {'ab':3420, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':6900, 'cerr':[], 'ent':[6745]},
    'DULCE C/NUEZ':  {'ab':6820, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':1470, 'cerr':[6680, 6555], 'ent':[]},
    'D. GRANIZADO':  {'ab':4190, 'cerr':[], 'ent':[6710, 6775]},
    'DULCE AMORES':  {'ab':1515, 'cerr':[6700], 'ent':[6795]},
    'SUPER':         {'ab':3400, 'cerr':[], 'ent':[]},
    'DURAZNO':       {'ab':6015, 'cerr':[6605], 'ent':[]},
    'FERRERO':       {'ab':4545, 'cerr':[], 'ent':[6585]},
    'FLAN':          {'ab':3605, 'cerr':[], 'ent':[6675]},
    'CEREZA':        {'ab':3430, 'cerr':[], 'ent':[6600]},
    'FRAMBUEZA':     {'ab':4320, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':4135, 'cerr':[6430], 'ent':[6775]},
    'FRUTILLA REINA':{'ab':3020, 'cerr':[6795], 'ent':[]},
    'FRUTILLA AGUA': {'ab':2670, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':1165, 'cerr':[6495], 'ent':[]},
    'GRANIZADO':     {'ab':2560, 'cerr':[6725], 'ent':[]},
    'LIMON':         {'ab':2155, 'cerr':[6360], 'ent':[6425]},
    'MANTECOL':      {'ab':990,  'cerr':[6690], 'ent':[]},
    'MANZANA':       {'ab':770,  'cerr':[6160], 'ent':[]},
    'MARROC':        {'ab':1360, 'cerr':[6600], 'ent':[]},
    'MASCARPONE':    {'ab':1115, 'cerr':[], 'ent':[6490]},
    'MENTA':         {'ab':7050, 'cerr':[], 'ent':[]},
    'MIX DE FRUTA':  {'ab':6500, 'cerr':[], 'ent':[]},
    'MOUSSE LIMON':  {'ab':4015, 'cerr':[], 'ent':[]},
    'SAMBAYON':      {'ab':1870, 'cerr':[6315], 'ent':[]},
    'SAMBAYON AMORES':{'ab':6255, 'cerr':[], 'ent':[]},
    'TRAMONTANA':    {'ab':1050, 'cerr':[6620, 6735], 'ent':[]},
    'TIRAMIZU':      {'ab':2270, 'cerr':[], 'ent':[]},
    'VAINILLA':      {'ab':4970, 'cerr':[6445], 'ent':[]},
    'LEMON PIE':     {'ab':2000, 'cerr':[6540], 'ent':[]},
    'NUTE':          {'ab':4190, 'cerr':[6685], 'ent':[]},
    'RUSA':          {'ab':3345, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':2215, 'cerr':[6520], 'ent':[]},
    'KITKAT':        {'ab':4400, 'cerr':[], 'ent':[]},
    'KINDER':        {'ab':1585, 'cerr':[6485], 'ent':[]},
    'MARACUYA':      {'ab':3790, 'cerr':[], 'ent':[]},
    'PISTACHO':      {'ab':1495, 'cerr':[6330], 'ent':[]},
    'COCO':          {'ab':4080, 'cerr':[], 'ent':[]},
}

# =============================================
# CAPA 4: CORRECCIONES v3
# =============================================

# Corrección 1: DULCE D LECHE + DULCE AMORES (RESUELTO_CONJUNTO)
# DDL: cerr 6555 omitida en DIA (PF5). D3=[6680,6555], D5N=[6680,6555], D6D=[6680,6555]
# DA: cerr 6555 phantom en DIA (misregistro de la cerr de DDL). D3=[6700], D5N=[6700], D6D=[6700]
corr_1_ddl_cerr_dia = [6685, 6555]   # agregar 6555 omitida
corr_1_da_cerr_dia  = [6700]          # remover 6555 phantom

# Corrección 2: VAINILLA — cerr 6445 es entrante no documentado (PF4)
# D3: cerr=[]. D5D: cerr=[]. D5N: cerr=[6445]. D6D: cerr=[6445]. D6N: cerr=[6445]
# Apareció entre DIA y NOCHE -> new_entrante_B
corr_2_van_new_ent = 6445

# Corrección 3: KITKAT — cerr 6400 phantom en DIA (PF3)
# D3: cerr=[]. D5D: cerr=[6400]. D5N: cerr=[]. D6D: cerr=[]. D6N: cerr=[]
# 1-sighting, sin soporte bilateral. KIYKAT en NOCHE (PF8 nombre).
corr_3_kit_cerr_dia = []  # remover phantom

# Corrección 4: PISTACHO — cerr 6630->6330 digit error en DIA (PF1)
# D3: cerr=[6330]. D5N: cerr=[6330]. D6D: cerr=[6330]. Solo D5D dice 6630.
corr_4_pis_cerr_dia = [6330]

# Corrección 5: CHOCOLATE — entrante 6530~6630 pesaje variance (100g)
# Sin apertura, raw=7485g implausible. Tratar 6530~6630 como mismo entrante.
corr_5_choc_ent_match_override = True  # forzar matching 6530~6630

# Corrección 6: CH C/ALM — cerr 6675->6615 pesaje variance (60g)
# D3: cerr=[6615]. D5N: cerr=[6615]. D6D: cerr=[6615].
corr_6_chc_cerr_dia = [6615]

# =============================================
# CAPA 2+3: CÓMPUTO CON CORRECCIONES
# =============================================

def compute(sabor, d, n, label=''):
    """Compute venta for a sabor given dia/noche dicts. Returns (raw, latas, total_a, total_b)"""
    total_a = d['ab'] + sum(d['cerr']) + sum(d['ent'])
    total_b = n['ab'] + sum(n['cerr']) + sum(n['ent'])

    # new_entrantes_B
    new_ent_b = 0
    extra_new_ent = d.get('extra_new_ent_b', 0)
    ent_a_remaining = list(d['ent'])

    match_tol = d.get('ent_match_tol', 50)

    for eb in n['ent']:
        found = False
        for i, ea in enumerate(ent_a_remaining):
            if abs(eb - ea) <= match_tol:
                found = True
                ent_a_remaining.pop(i)
                break
        if not found:
            new_ent_b += eb

    new_ent_b += extra_new_ent

    n_cerr_a = len(d['cerr'])
    n_cerr_b = len(n['cerr'])
    n_latas = max(0, n_cerr_a - n_cerr_b)
    ajuste = n_latas * 280

    raw = total_a + new_ent_b - total_b - ajuste
    return raw, n_latas, total_a, total_b, new_ent_b, ajuste


# Build corrected data
import copy
dia = copy.deepcopy(dia_raw)
noche = copy.deepcopy(noche_raw)

# Apply corrections
dia['DULCE D LECHE']['cerr'] = corr_1_ddl_cerr_dia
dia['DULCE AMORES']['cerr'] = corr_1_da_cerr_dia
dia['VAINILLA']['extra_new_ent_b'] = corr_2_van_new_ent
dia['KITKAT']['cerr'] = corr_3_kit_cerr_dia
dia['PISTACHO']['cerr'] = corr_4_pis_cerr_dia
dia['CHOCOLATE']['ent_match_tol'] = 110  # override matching threshold for 6530~6630
dia['CH C/ALM']['cerr'] = corr_6_chc_cerr_dia

# =============================================
# COMPUTE ALL
# =============================================

all_sabores = sorted(set(list(dia_raw.keys()) + list(noche_raw.keys())))

print("=" * 150)
print("DÍA 5 (Jueves 5) — DESGLOSE COMPLETO v3")
print("=" * 150)
print()
print(f"{'#':>2} {'SABOR':<20} {'ab_D':>6} {'ab_N':>6} | {'totA':>7} {'totB':>7} {'newE':>5} {'adj':>5} | {'RAW':>7} {'CORR':>7} {'L':>2} | {'STATUS':<12} | NOTA")
print("-" * 150)

tot_raw = 0
tot_corr = 0
tot_latas_raw = 0
tot_latas_corr = 0
n_limpio = 0
n_engine = 0
n_corr = 0
n_solo = 0
corrections_detail = []

i = 0
for sabor in all_sabores:
    i += 1
    d_raw = dia_raw.get(sabor)
    n_raw = noche_raw.get(sabor)
    d_corr = dia.get(sabor)
    n_corr_data = noche.get(sabor)

    # SOLO_DIA / SOLO_NOCHE
    if d_raw is None:
        print(f"{i:>2} {sabor:<20} {'N/A':>6} {n_raw['ab']:>6} | {'':>7} {'':>7} {'':>5} {'':>5} | {'':>7} {'':>7} {'':>2} | {'SOLO_NOCHE':<12} |")
        n_solo += 1
        continue
    if n_raw is None:
        print(f"{i:>2} {sabor:<20} {d_raw['ab']:>6} {'N/A':>6} | {'':>7} {'':>7} {'':>5} {'':>5} | {'':>7} {'':>7} {'':>2} | {'SOLO_DIA':<12} |")
        n_solo += 1
        continue

    # Raw computation (original data)
    raw_v, raw_l, raw_ta, raw_tb, raw_ne, raw_aj = compute(sabor, d_raw, n_raw)

    # Corrected computation
    corr_v, corr_l, corr_ta, corr_tb, corr_ne, corr_aj = compute(sabor, d_corr, n_corr_data)

    # Determine status
    ab_delta = n_raw['ab'] - d_raw['ab']
    apertura = ab_delta > 3000 and len(d_raw['cerr']) > len(n_raw['cerr'])

    delta = corr_v - raw_v

    if apertura:
        status = 'ENGINE'
        n_engine += 1
        nota = f"apertura cerr {'->'.join(str(c) for c in d_raw['cerr'])}"
    elif delta != 0:
        status = 'CORREGIDO'
        n_corr += 1
        nota = f"delta={delta:+d}g"
    else:
        status = 'LIMPIO'
        n_limpio += 1
        nota = ''

    # Minor flags
    flags = []
    for ca in d_raw['cerr']:
        if not any(abs(ca-cb) <= 30 for cb in n_raw['cerr']):
            flags.append(f'C4d:{ca}')
    for cb in n_raw['cerr']:
        if not any(abs(cb-ca) <= 30 for ca in d_raw['cerr']):
            flags.append(f'C4n:{cb}')
    if flags and status == 'LIMPIO':
        nota = ', '.join(flags) + ' (tolerancia extendida)'

    tot_raw += raw_v
    tot_corr += corr_v
    tot_latas_raw += raw_l
    tot_latas_corr += corr_l

    raw_str = f"{raw_v:>7}"
    corr_str = f"{corr_v:>7}" if delta != 0 else f"{'=':>7}"

    print(f"{i:>2} {sabor:<20} {d_raw['ab']:>6} {n_raw['ab']:>6} | {corr_ta:>7} {corr_tb:>7} {corr_ne:>5} {corr_aj:>5} | {raw_str} {corr_str} {corr_l:>2} | {status:<12} | {nota}")

    if delta != 0 and not apertura:
        corrections_detail.append((sabor, raw_v, corr_v, delta))

print("-" * 150)
print(f"   {'TOTAL':<20} {'':>6} {'':>6} | {'':>7} {'':>7} {'':>5} {'':>5} | {tot_raw:>7} {tot_corr:>7} {tot_latas_corr:>2} |")

print()
print("=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"Sabores activos (DIA+NOCHE): {i - n_solo}")
print(f"SOLO_DIA: 3 (CHOCOLATE DUBAI, FRANUI, IRLANDESA)")
print(f"LIMPIO:     {n_limpio} sabores")
print(f"ENGINE:     {n_engine} sabores (aperturas confirmadas)")
print(f"CORREGIDO:  {n_corr} sabores")
print()

print("--- CORRECCIONES APLICADAS ---")
for s, rv, cv, d in corrections_detail:
    print(f"  {s:<20}: raw={rv:>7}g -> corr={cv:>7}g  (delta={d:+d}g)")

print()
print(f"Venta stock RAW:           {tot_raw:>8}g")
print(f"Venta stock CORREGIDA:     {tot_corr:>8}g")
print(f"Latas abiertas (corr):     {tot_latas_corr:>8}  (ajuste ya incluido en venta)")
print()

# VDP
vdp_dia = 250 + 1000 + 245  # 2 vasos 65 + 4/1 + 1 cucurucho
vdp_noche = 0
vdp_total = vdp_dia + vdp_noche
print(f"VDP DIA:                   {vdp_dia:>8}g  (2 vasos65 + 4/1 + 1 cucurucho)")
print(f"VDP NOCHE:                 {vdp_noche:>8}g")
print(f"VDP TOTAL:                 {vdp_total:>8}g")
print()
print(f"TOTAL DÍA 5 =             {tot_corr + vdp_total:>8}g")

print()
print("=" * 80)
print("DETALLE DE EXPEDIENTES (CAPA 4)")
print("=" * 80)

expedientes = [
    {
        'id': 'EXP-D5-01',
        'sabores': 'DULCE D LECHE + DULCE AMORES',
        'tipo': 'RESUELTO_CONJUNTO',
        'proto': 'PF5 (cerr omitida DIA) + PF3 (phantom cerr)',
        'conf': 0.92,
        'desc': """DDL: cerr 6555 omitida en DIA.
  Timeline: D3=[6680,6555], D5D=[6685], D5N=[6680,6555], D6D=[6680,6555]
  La cerr 6555 existe en D3, D5N, D6D -> fue omitida al registrar D5 DIA.
DA: cerr 6555 phantom en DIA (misregistro).
  Timeline: D3=[6700], D5D=[6700,6555], D5N=[6700], D6D=[6700]
  La cerr 6555 aparece SOLO en D5 DIA -> 1-sighting. Es la cerr de DDL mal asignada.
P1 (ab): DDL ab baja 1705->1470 (ok). DA ab baja 2475->1515 (ok).
P2 (cerr): DDL 6555 tiene 4 sightings, DA 6555 tiene 1 sighting -> pertenece a DDL.
Convergencia: P1+P2 independientes -> >=2 planos. Corrección bilateral válida.
DDL: raw=-6315 -> corr=240g.  DA: raw=7235 -> corr=960g.""",
    },
    {
        'id': 'EXP-D5-02',
        'sabores': 'VAINILLA',
        'tipo': 'RESUELTO_INDIVIDUAL',
        'proto': 'PF4 (entrante/cerr no documentado)',
        'conf': 0.88,
        'desc': """Cerr 6445 aparece en NOCHE sin estar en DIA ni en D3.
  Timeline: D3=[], D5D=[], D5N=[6445], D6D=[6445], D6N=[6445]
  Persiste en D6D y D6N -> es un can real que llegó entre DIA y NOCHE.
P1 (ab): 5055->4970 (-85g), descenso normal.
P2 (cerr): 6445 no existía antes -> nueva incorporación.
P3 (genealogía): no hay entrante documentado, pero el can es real (3+ sightings post).
Hipótesis: entrante no documentado, tratar como new_entrante_B.
raw=-6360 -> corr=85g.""",
    },
    {
        'id': 'EXP-D5-03',
        'sabores': 'KITKAT',
        'tipo': 'RESUELTO_INDIVIDUAL',
        'proto': 'PF3 (phantom cerrada)',
        'conf': 0.90,
        'desc': """Cerr 6400 aparece en DIA, desaparece en NOCHE.
  Timeline: D3=[], D5D=[6400], D5N=[], D6D=[], D6N=[]
  1-sighting sin soporte bilateral. KITKAT nunca tiene cerrada en ±3 turnos.
  Nota: NOCHE la registra como "KIYKAT" (PF8 nombre inconsistente).
P1 (ab): 4630->4400 (-230g), consistente con venta normal (D3:4905->D5D:4630->D5N:4400->D6D:4395).
P2 (cerr): 0 sightings fuera de D5D -> phantom.
Hipótesis: cerr 6400 registrada por error en KITKAT (pertenece a otro sabor o es phantom).
raw=6350 -> corr=230g.""",
    },
    {
        'id': 'EXP-D5-04',
        'sabores': 'PISTACHO',
        'tipo': 'RESUELTO_INDIVIDUAL',
        'proto': 'PF1 (digit error)',
        'conf': 0.95,
        'desc': """Cerr 6630 en DIA vs 6330 en NOCHE (300g diferencia).
  Timeline: D3=[6330], D5D=[6630], D5N=[6330], D6D=[6330]
  Cerr 6330 tiene 3+ sightings. El valor 6630 es 1-sighting.
  Diferencia 300g = error de dígito (6->3 en centenas).
P2 (cerr): 6330 es la identidad estable. 6630 es misread.
Corrección: 6630->6330 en DIA.
raw=1945 -> corr=1645g.""",
    },
    {
        'id': 'EXP-D5-05',
        'sabores': 'CHOCOLATE',
        'tipo': 'RESUELTO_INDIVIDUAL',
        'proto': 'Pesaje variance entrante (100g)',
        'conf': 0.75,
        'desc': """Entrante 6530 DIA -> 6630 NOCHE. Diff=100g (fuera de threshold 50g).
  Sin apertura de cerrada. raw=7485g sería implausible.
  El entrante 6475 matchea perfecto (0g diff).
  La cerrada 6640 matchea perfecto (0g diff).
P1 (ab): 1980->1025 (-955g), venta alta pero razonable con 3 latas en stock.
P2 (cerr): cerr 6640 estable -> no hay apertura.
P3 (ent): 6530 y 6630 son probablemente el mismo can con pesaje impreciso.
Confianza reducida por gap 100g (2x tolerancia normal).
raw=7485 -> corr=855g.""",
    },
    {
        'id': 'EXP-D5-06',
        'sabores': 'CH C/ALM',
        'tipo': 'RESUELTO_INDIVIDUAL',
        'proto': 'Pesaje variance cerrada (60g)',
        'conf': 0.85,
        'desc': """Cerr 6675 DIA -> 6615 NOCHE (60g diferencia).
  Timeline: D3=[6615], D5N=[6615], D6D=[6665,6615]
  Cerr 6615 tiene 3+ sightings. El 6675 es 1-sighting (pesaje alto).
Corrección: normalizar a 6615 para matching.
raw=1400 -> corr=1340g.  Delta=-60g (menor).""",
    },
]

for exp in expedientes:
    print(f"\n{'-'*80}")
    print(f"  {exp['id']}: {exp['sabores']}")
    print(f"  Tipo: {exp['tipo']}  |  Proto: {exp['proto']}  |  Conf: {exp['conf']}")
    print(f"{'-'*80}")
    for line in exp['desc'].strip().split('\n'):
        print(f"  {line}")

print()
print("=" * 80)
print("NOTAS MENORES (sin corrección)")
print("=" * 80)
print("  CADBURY: cerr 6360~6410 (50g). D3=6410. Pesaje variance. raw=1320g sin cambio.")
print("  SAMBAYON: cerr 6365~6315 (50g). Pesaje variance. raw=900g sin cambio.")
print("  MANTECOL: cerr 6670~6690 (20g). Dentro de tolerancia normal.")
print("  MARROC: cerr 6570~6600 (30g). Dentro de tolerancia normal.")
print("  CH AMORES: cerr 6675~6665 (10g). Dentro de tolerancia normal.")
print("  FRUTILLA REINA: cerr 6790~6795 (5g). Dentro de tolerancia normal.")
print("  NUTE: cerr 6695~6685 (10g). Dentro de tolerancia normal.")
