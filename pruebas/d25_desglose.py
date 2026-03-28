"""Day 25 — Full flavor breakdown"""

dia = {
    'CADBURY':       {'ab':6365, 'cerr':[6355], 'ent':[]},
    'AMERICANA':     {'ab':1650, 'cerr':[6370], 'ent':[]},
    'ANANA':         {'ab':1650, 'cerr':[7030], 'ent':[]},
    'B, SPLIT':      {'ab':6060, 'cerr':[6405,6360], 'ent':[]},
    'CHOCOLATE':     {'ab':1870, 'cerr':[5940], 'ent':[]},
    'AMARGO':        {'ab':6410, 'cerr':[6655], 'ent':[]},
    'BLANCO':        {'ab':5820, 'cerr':[], 'ent':[]},
    'CH C/ALM':      {'ab':5435, 'cerr':[6530,6445], 'ent':[]},
    'CH AMORES':     {'ab':5755, 'cerr':[6395], 'ent':[]},
    'DOS CORAZONES': {'ab':5800, 'cerr':[], 'ent':[]},
    'CABSHA':        {'ab':3805, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':2870, 'cerr':[6715], 'ent':[]},
    'DULCE C/NUEZ':  {'ab':4390, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':1905, 'cerr':[6690,6675], 'ent':[]},
    'D. GRANIZADO':  {'ab':4995, 'cerr':[6575,6605], 'ent':[]},
    'DULCE AMORES':  {'ab':3195, 'cerr':[6640,6700], 'ent':[]},
    'SUPER':         {'ab':4895, 'cerr':[6730], 'ent':[]},
    'DURAZNO':       {'ab':6595, 'cerr':[], 'ent':[]},
    'FERRERO':       {'ab':2300, 'cerr':[6365,6530], 'ent':[]},
    'FLAN':          {'ab':4190, 'cerr':[], 'ent':[]},
    'CEREZA':        {'ab':6205, 'cerr':[], 'ent':[]},
    'FRAMBUEZA':     {'ab':4585, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':7035, 'cerr':[6565], 'ent':[]},
    'FRUTILLA REINA':{'ab':5455, 'cerr':[6575], 'ent':[]},
    'FRUTILLA AGUA': {'ab':7425, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':4045, 'cerr':[6580], 'ent':[]},
    'GRANIZADO':     {'ab':6810, 'cerr':[6750], 'ent':[]},
    'LIMON':         {'ab':4080, 'cerr':[6280], 'ent':[]},
    'MANTECOL':      {'ab':5265, 'cerr':[], 'ent':[]},
    'MANZANA':       {'ab':3590, 'cerr':[], 'ent':[]},
    'MARROC':        {'ab':5215, 'cerr':[6840], 'ent':[]},
    'MASCARPONE':    {'ab':2415, 'cerr':[6600], 'ent':[]},
    'MENTA':         {'ab':1470, 'cerr':[6460], 'ent':[]},
    'MIX DE FRUTA':  {'ab':5340, 'cerr':[6790], 'ent':[]},
    'MOUSSE LIMON':  {'ab':5000, 'cerr':[6485], 'ent':[]},
    'SAMBAYON':      {'ab':2395, 'cerr':[6450], 'ent':[]},
    'SAMBAYON AMORES':{'ab':835, 'cerr':[6505], 'ent':[]},
    'TRAMONTANA':    {'ab':7055, 'cerr':[6790], 'ent':[]},
    'TIRAMIZU':      {'ab':4345, 'cerr':[6560], 'ent':[]},
    'VAINILLA':      {'ab':5455, 'cerr':[6465], 'ent':[]},
    'LEMON PIE':     {'ab':1335, 'cerr':[6645], 'ent':[]},
    'IRLANDESA':     {'ab':4085, 'cerr':[6605], 'ent':[]},
    'NUTE':          {'ab':1490, 'cerr':[6710], 'ent':[]},
    'RUSA':          {'ab':4480, 'cerr':[], 'ent':[]},
    'FRANUI':        {'ab':6090, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':6330, 'cerr':[], 'ent':[]},
    'COCO':          {'ab':5060, 'cerr':[], 'ent':[]},
    'KINDER':        {'ab':4480, 'cerr':[], 'ent':[]},
    'PISTACHO':      {'ab':5775, 'cerr':[6350], 'ent':[]},
    'CHOCOLATE DUBAI':{'ab':3445, 'cerr':[6355], 'ent':[]},
    'KITKAT':        {'ab':4630, 'cerr':[6400], 'ent':[]},
}

noche = {
    'CADBURY':       {'ab':6050, 'cerr':[6355], 'ent':[]},
    'AMERICANA':     {'ab':4110, 'cerr':[6360], 'ent':[]},
    'ANANA':         {'ab':1405, 'cerr':[7040], 'ent':[]},
    'B, SPLIT':      {'ab':5805, 'cerr':[6395,6360], 'ent':[]},
    'CHOCOLATE':     {'ab':6415, 'cerr':[], 'ent':[]},
    'AMARGO':        {'ab':5890, 'cerr':[6665], 'ent':[]},
    'BLANCO':        {'ab':5800, 'cerr':[], 'ent':[]},
    'CH C/ALM':      {'ab':5210, 'cerr':[6445,6525], 'ent':[]},
    'CH AMORES':     {'ab':5415, 'cerr':[6390], 'ent':[]},
    'DOS CORAZONES': {'ab':5440, 'cerr':[], 'ent':[]},
    'CABSHA':        {'ab':3615, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':2750, 'cerr':[5705], 'ent':[]},
    'DULCE C/NUEZ':  {'ab':4390, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':1465, 'cerr':[6690,6675], 'ent':[]},
    'D. GRANIZADO':  {'ab':4245, 'cerr':[6575,6610], 'ent':[]},
    'DULCE AMORES':  {'ab':2730, 'cerr':[6630,6740], 'ent':[]},
    'SUPER':         {'ab':4680, 'cerr':[6770], 'ent':[]},
    'DURAZNO':       {'ab':6175, 'cerr':[], 'ent':[]},
    'FERRERO':       {'ab':2055, 'cerr':[6530,6360], 'ent':[]},
    'FLAN':          {'ab':3515, 'cerr':[], 'ent':[]},
    'CEREZA':        {'ab':5915, 'cerr':[], 'ent':[]},
    'FRAMBUEZA':     {'ab':4440, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':5955, 'cerr':[6555], 'ent':[]},
    'FRUTILLA REINA':{'ab':5070, 'cerr':[6575], 'ent':[]},
    'FRUTILLA AGUA': {'ab':6680, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':3465, 'cerr':[6570], 'ent':[]},
    'GRANIZADO':     {'ab':6465, 'cerr':[6710], 'ent':[]},
    'LIMON':         {'ab':3185, 'cerr':[6265], 'ent':[]},
    'MANTECOL':      {'ab':4950, 'cerr':[], 'ent':[]},
    'MANZANA':       {'ab':3085, 'cerr':[], 'ent':[]},
    'MARROC':        {'ab':4965, 'cerr':[6830], 'ent':[]},
    'MASCARPONE':    {'ab':1855, 'cerr':[6600], 'ent':[]},
    'MENTA':         {'ab':1045, 'cerr':[6460], 'ent':[]},
    'MIX DE FRUTA':  {'ab':5340, 'cerr':[6785], 'ent':[]},
    'MOUSSE LIMON':  {'ab':4995, 'cerr':[6485], 'ent':[]},
    'SAMBAYON':      {'ab':1720, 'cerr':[6450], 'ent':[]},
    'SAMBAYON AMORES':{'ab':6450, 'cerr':[], 'ent':[]},
    'TRAMONTANA':    {'ab':6220, 'cerr':[6790], 'ent':[]},
    'TIRAMIZU':      {'ab':4255, 'cerr':[6555], 'ent':[]},
    'VAINILLA':      {'ab':5190, 'cerr':[6460], 'ent':[]},
    'LEMON PIE':     {'ab':1130, 'cerr':[6615], 'ent':[]},
    'IRLANDESA':     {'ab':3235, 'cerr':[6605], 'ent':[]},
    'NUTE':          {'ab':1420, 'cerr':[6695], 'ent':[]},
    'RUSA':          {'ab':4475, 'cerr':[], 'ent':[]},
    'FRANUI':        {'ab':6040, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':5950, 'cerr':[], 'ent':[]},
    'COCO':          {'ab':4985, 'cerr':[], 'ent':[]},
    'KINDER':        {'ab':4180, 'cerr':[], 'ent':[]},
    'PISTACHO':      {'ab':5315, 'cerr':[6355], 'ent':[]},
    'CHOCOLATE DUBAI':{'ab':2990, 'cerr':[6355], 'ent':[]},
    'KITKAT':        {'ab':4015, 'cerr':[6380], 'ent':[]},
}

# Corrections applied
corr_ab = {'AMERICANA': 4365}
corr_cerr_n = {'COOKIES': [6705]}

results = []
for sabor in sorted(dia.keys()):
    d = dia[sabor]
    n = noche[sabor]

    # Raw calculation
    raw_ta = d['ab'] + sum(d['cerr']) + sum(d['ent'])
    raw_tb = n['ab'] + sum(n['cerr']) + sum(n['ent'])
    raw_latas = max(0, len(d['cerr']) - len(n['cerr']))
    raw_venta = raw_ta - raw_tb - raw_latas * 280

    # Corrected calculation
    ab_d = corr_ab.get(sabor, d['ab'])
    cerr_n_use = corr_cerr_n.get(sabor, n['cerr'])
    corr_ta = ab_d + sum(d['cerr']) + sum(d['ent'])
    corr_tb = n['ab'] + sum(cerr_n_use) + sum(n['ent'])
    corr_latas = max(0, len(d['cerr']) - len(cerr_n_use))
    corr_venta = corr_ta - corr_tb - corr_latas * 280

    # Cerr diff
    cerr_info = ''
    if d['cerr'] and n['cerr']:
        pairs = []
        used = set()
        for ca in d['cerr']:
            best_i, best_d2 = -1, 9999
            for i, cb in enumerate(n['cerr']):
                if i not in used and abs(ca-cb) < best_d2:
                    best_i, best_d2 = i, abs(ca-cb)
            if best_i >= 0 and best_d2 <= 100:
                pairs.append(f"{int(ca)}~{int(n['cerr'][best_i])}({int(best_d2)}g)")
                used.add(best_i)
            else:
                pairs.append(f"{int(ca)}->X")
        for i, cb in enumerate(n['cerr']):
            if i not in used:
                pairs.append(f"X->{int(cb)}")
        cerr_info = ', '.join(pairs)
    elif d['cerr'] and not n['cerr']:
        cerr_info = ','.join(str(int(c)) for c in d['cerr']) + ' GONE'
    elif n['cerr'] and not d['cerr']:
        cerr_info = 'NEW ' + ','.join(str(int(c)) for c in n['cerr'])

    # Status
    has_corr = sabor in corr_ab or sabor in corr_cerr_n
    ab_delta = n['ab'] - d['ab']
    apertura = ab_delta > 3000 and len(d['cerr']) > len(n['cerr'])

    if has_corr:
        status = 'CORREG'
    elif apertura:
        status = 'ENGINE'
    else:
        status = 'LIMPIO'

    delta = corr_venta - raw_venta if has_corr else 0

    results.append((sabor, d['ab'], n['ab'], ab_delta,
                     d['cerr'], n['cerr'], cerr_info,
                     raw_venta, corr_venta, corr_latas, status, delta))

# Print
hdr = f"{'#':>2} {'SABOR':<20} {'ab_D':>6} {'ab_N':>6} {'dAb':>6} | {'cerr_D':<14} {'cerr_N':<14} {'cerr_match':<28} | {'raw':>7} {'CORR':>7} {'L':>2} {'delta':>7} | {'STATUS':<8}"
print(hdr)
print('-' * len(hdr))

tot_raw = 0
tot_corr = 0
tot_latas = 0
i = 0
for r in results:
    i += 1
    sabor, ab_d, ab_n, ab_delta, cerr_d, cerr_n, cerr_info, raw_v, corr_v, latas, status, delta = r
    cd = ','.join(str(int(c)) for c in cerr_d) if cerr_d else '-'
    cn = ','.join(str(int(c)) for c in cerr_n) if cerr_n else '-'
    corr_str = f"{corr_v:>7}" if corr_v != raw_v else f"{'=':>7}"
    delta_str = f"{delta:>+7}" if delta != 0 else f"{'':>7}"
    print(f"{i:>2} {sabor:<20} {ab_d:>6} {ab_n:>6} {ab_delta:>+6} | {cd:<14} {cn:<14} {cerr_info:<28} | {raw_v:>7} {corr_str} {latas:>2} {delta_str} | {status:<8}")
    tot_raw += raw_v
    tot_corr += corr_v
    tot_latas += latas

print('-' * len(hdr))
print(f"   {'TOTAL':<20} {'':>6} {'':>6} {'':>6} | {'':>14} {'':>14} {'':>28} | {tot_raw:>7} {tot_corr:>7} {tot_latas:>2} {tot_corr-tot_raw:>+7} |")
print()
print(f"Venta stock RAW:       {tot_raw:>8}g")
print(f"Venta stock CORREGIDA: {tot_corr:>8}g")
print(f"Latas abiertas:        {tot_latas:>8}  ({tot_latas*280}g)")
print(f"Venta neta (corr):     {tot_corr - tot_latas*280:>8}g")
print(f"VDP:                   {0:>8}g")
print(f"TOTAL DIA 25:          {tot_corr - tot_latas*280:>8}g")
