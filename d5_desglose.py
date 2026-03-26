"""Day 5 — Full flavor breakdown v3
Fuente: Febrero San Martin 2026 (1).xlsx
Hojas: Jueves 5 (DIA) y Jueves 5 (NOCHE)
Contexto: Martes 3, Viernes 6 (Día/Noche)
Nota: Miércoles 4 está vacío (0 sabores).
"""

# =============================================
# CAPA 1: DATOS CRUDOS
# =============================================

# DIA - Jueves 5 (DIA)
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
    'COCO':          {'ab':4505, 'cerr':[], 'ent':[]},  # from POSTRES notes section (not in main grid)
}

# NOCHE - Jueves 5 (NOCHE)
# KIYKAT -> KITKAT (name correction PF8)
# FRANUI: EMPTY in NOCHE -> None
# IRLANDESA: EMPTY in NOCHE -> None
# CHOCOLATE DUBAI: EMPTY in NOCHE -> None
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
    # IRLANDESA: EMPTY in NOCHE
    'NUTE':          {'ab':4190, 'cerr':[6685], 'ent':[]},
    'RUSA':          {'ab':3345, 'cerr':[], 'ent':[]},
    # FRANUI: EMPTY in NOCHE
    'CIELO':         {'ab':2215, 'cerr':[6520], 'ent':[]},
    'KITKAT':        {'ab':4400, 'cerr':[], 'ent':[]},  # listed as "KIYKAT" in sheet
    'KINDER':        {'ab':1585, 'cerr':[6485], 'ent':[]},
    'MARACUYA':      {'ab':3790, 'cerr':[], 'ent':[]},
    'PISTACHO':      {'ab':1495, 'cerr':[6330], 'ent':[]},
    # CHOCOLATE DUBAI: EMPTY in NOCHE
    'COCO':          {'ab':4080, 'cerr':[], 'ent':[]},
}

# Timeline context for escalated flavors
timeline = {
    'CADBURY': {'D3': {'ab':5615, 'cerr':[6410]}, 'D6D': {'ab':3800, 'cerr':[6360]}, 'D6N': {'ab':2290, 'cerr':[6360]}},
    'DULCE D LECHE': {'D3': {'ab':2140, 'cerr':[6680, 6555]}, 'D6D': {'ab':1465, 'cerr':[6680, 6555]}, 'D6N': {'ab':6540, 'cerr':[6555]}},
    'VAINILLA': {'D3': {'ab':5690, 'cerr':[]}, 'D6D': {'ab':4970, 'cerr':[6445]}, 'D6N': {'ab':4050, 'cerr':[6445]}},
    'DULCE AMORES': {'D3': {'ab':3500, 'cerr':[6700]}, 'D6D': {'ab':850, 'cerr':[6700]}, 'D6N': {'ab':5880, 'cerr':[6795]}},
    'PISTACHO': {'D3': {'ab':3520, 'cerr':[6330]}, 'D6D': {'ab':1490, 'cerr':[6330]}, 'D6N': {'ab':5360, 'cerr':[]}},
    'CH C/ALM': {'D3': {'ab':3280, 'cerr':[6615]}, 'D6D': {'ab':1040, 'cerr':[6665, 6615]}, 'D6N': {'ab':5775, 'cerr':[6665]}},
    'KITKAT': {'D3': {'ab':4905, 'cerr':[]}, 'D6D': {'ab':4395, 'cerr':[]}, 'D6N': {'ab':4060, 'cerr':[]}},
    'CH AMORES': {'D3': {'ab':6545, 'cerr':[6665]}, 'D6D': {'ab':6165, 'cerr':[6660]}, 'D6N': {'ab':5315, 'cerr':[6665]}},
    'MARROC': {'D3': {'ab':1940, 'cerr':[6570]}, 'D6D': {'ab':1355, 'cerr':[6570]}, 'D6N': {'ab':6570, 'cerr':[]}},
    'FRANUI': {'D3': {'ab':1885, 'cerr':[]}, 'D6D_notes': 'cerr=[6760], ent=[6440]'},
    'IRLANDESA': {'D3': 'EMPTY', 'D6D': {'ab':0, 'ent':[6740, 6670]}},
}

# =============================================
# CAPA 2 + 3: COMPUTE AND CLASSIFY
# =============================================

all_sabores = sorted(set(list(dia_raw.keys()) + list(noche_raw.keys())))

results = []
for sabor in all_sabores:
    d = dia_raw.get(sabor)
    n = noche_raw.get(sabor)

    # Handle missing
    if d is None:
        results.append((sabor, None, None, 0, 0, 0, 0, 0, 'SOLO_NOCHE', '', []))
        continue
    if n is None:
        results.append((sabor, d['ab'], None, 0, 0, 0, 0, 0, 'SOLO_DIA', '', d['cerr']))
        continue

    # Compute
    total_a = d['ab'] + sum(d['cerr']) + sum(d['ent'])
    total_b = n['ab'] + sum(n['cerr']) + sum(n['ent'])

    # new_entrantes_B
    new_ent_b = 0
    ent_a_remaining = list(d['ent'])
    for eb in n['ent']:
        found = False
        for i, ea in enumerate(ent_a_remaining):
            if abs(eb - ea) <= 50:
                found = True
                ent_a_remaining.pop(i)
                break
        if not found:
            new_ent_b += eb

    n_cerr_a = len(d['cerr'])
    n_cerr_b = len(n['cerr'])
    n_latas = max(0, n_cerr_a - n_cerr_b)
    ajuste = n_latas * 280

    raw_venta = total_a + new_ent_b - total_b - ajuste

    # Cerr matching
    cerr_info_parts = []
    used_b = set()
    for ca in d['cerr']:
        best_i, best_diff = -1, 9999
        for i, cb in enumerate(n['cerr']):
            if i not in used_b and abs(ca - cb) < best_diff:
                best_i, best_diff = i, abs(ca - cb)
        if best_i >= 0 and best_diff <= 100:
            cerr_info_parts.append(f"{int(ca)}~{int(n['cerr'][best_i])}({int(best_diff)}g)")
            used_b.add(best_i)
        else:
            cerr_info_parts.append(f"{int(ca)}->X")
    for i, cb in enumerate(n['cerr']):
        if i not in used_b:
            cerr_info_parts.append(f"X->{int(cb)}")
    cerr_info = ', '.join(cerr_info_parts)

    # Ent matching
    ent_info_parts = []
    ent_a_rem2 = list(d['ent'])
    for eb in n['ent']:
        matched = False
        for i, ea in enumerate(ent_a_rem2):
            if abs(eb - ea) <= 50:
                ent_info_parts.append(f"e{int(ea)}~e{int(eb)}({int(abs(ea-eb))}g)")
                ent_a_rem2.pop(i)
                matched = True
                break
        if not matched:
            ent_info_parts.append(f"X->e{int(eb)}")
    for ea in ent_a_rem2:
        ent_info_parts.append(f"e{int(ea)}->X")
    ent_info = ', '.join(ent_info_parts)

    # Flags
    ab_delta = n['ab'] - d['ab']
    apertura = ab_delta > 3000 and n_cerr_a > n_cerr_b
    flags = []

    if raw_venta < -50: flags.append('NEG')
    if raw_venta >= 5000 and not apertura: flags.append('HIGH')
    if n['ab'] > d['ab'] + 20 and not apertura: flags.append('AB_UP')
    for ca in d['cerr']:
        if not any(abs(ca-cb)<=30 for cb in n['cerr']):
            flags.append(f'C4d:{int(ca)}')
    for cb in n['cerr']:
        if not any(abs(cb-ca)<=30 for ca in d['cerr']):
            flags.append(f'C4n:{int(cb)}')
    # Extra cerr in NOCHE
    if n_cerr_b > n_cerr_a:
        flags.append(f'CERR+{n_cerr_b - n_cerr_a}N')

    if apertura:
        status = 'ENGINE'
    elif not flags:
        status = 'LIMPIO'
    elif len(set(f.split(':')[0] for f in flags)) >= 2:
        status = 'COMPUESTO'
    else:
        status = 'SEÑAL'

    results.append((sabor, d['ab'], n['ab'], ab_delta, raw_venta, n_latas,
                     total_a, total_b, status, cerr_info + (' | ' + ent_info if ent_info else ''), flags))

# =============================================
# PRINT
# =============================================
print(f"{'#':>2} {'SABOR':<20} {'ab_D':>6} {'ab_N':>6} {'dAb':>6} | {'raw':>7} {'L':>2} | {'STATUS':<10} | cerr/ent matching | flags")
print('-' * 140)

tot_raw = 0
tot_latas = 0
i = 0
for r in results:
    i += 1
    if len(r) == 11:
        sabor, ab_d, ab_n, ab_delta, raw_v, latas, ta, tb, status, info, flags = r
    else:
        sabor, ab_d, ab_n, _, _, _, _, _, status, info, flags = r
        raw_v = 0; latas = 0; ab_delta = 0

    abd = f"{ab_d:>6}" if ab_d is not None else f"{'N/A':>6}"
    abn = f"{ab_n:>6}" if ab_n is not None else f"{'N/A':>6}"
    abd_str = f"{ab_delta:>+6}" if ab_d is not None and ab_n is not None else f"{'':>6}"
    flags_str = ', '.join(flags) if flags else ''

    print(f"{i:>2} {sabor:<20} {abd} {abn} {abd_str} | {raw_v:>7} {latas:>2} | {status:<10} | {info:<40} | {flags_str}")

    if status not in ('SOLO_DIA', 'SOLO_NOCHE'):
        tot_raw += raw_v
        tot_latas += latas

print('-' * 140)
print(f"   {'TOTAL':<20} {'':>6} {'':>6} {'':>6} | {tot_raw:>7} {tot_latas:>2} |")
print()

# Summary by status
for st in ['LIMPIO', 'ENGINE', 'SEÑAL', 'COMPUESTO', 'SOLO_DIA', 'SOLO_NOCHE']:
    group = [(r[0], r[4] if len(r)==11 else 0) for r in results if r[8] == st]
    if group:
        total = sum(g[1] for g in group)
        print(f"{st}: {len(group)} sabores, total_raw={total}g")
        if st in ('SEÑAL', 'COMPUESTO', 'SOLO_DIA'):
            for name, val in group:
                print(f"  - {name}: {val}g")

print(f"\nVenta stock RAW:       {tot_raw:>8}g")
print(f"Latas abiertas:        {tot_latas:>8}  ({tot_latas*280}g)")
print(f"Venta neta RAW:        {tot_raw - tot_latas*280:>8}g")

# VDP: DIA has VENTA ANTES DEL PESAJE: 2 VASO 65, 4/1, 1 CUCUCRUCHON
# NOCHE: nothing
print(f"VDP DIA (2 vasos65 + 4/1 + 1 cucurucho): ~{250+1000+245}g est.")
print(f"VDP NOCHE: 0g")
