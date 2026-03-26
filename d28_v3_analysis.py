"""
Día 28 — Análisis v3 completo
Fuente única: Febrero San Martin 2026 (1).xlsx
"""

# =============================================
# CAPA 1: PARSER — Datos crudos sin interpretación
# =============================================

dia = {
    'CADBURY':       {'ab':4875, 'cerr':[6355], 'ent':[]},
    'AMERICANA':     {'ab':2715, 'cerr':[6360], 'ent':[]},
    'ANANA':         {'ab':6485, 'cerr':[], 'ent':[]},
    'B, SPLIT':      {'ab':3640, 'cerr':[6405,6360], 'ent':[]},
    'CHOCOLATE':     {'ab':4045, 'cerr':[6655], 'ent':[]},
    'AMARGO':        {'ab':3580, 'cerr':[6655], 'ent':[]},
    'BLANCO':        {'ab':5390, 'cerr':[6770], 'ent':[]},
    'CH C/ALM':      {'ab':2325, 'cerr':[6445,6530], 'ent':[]},
    'CH AMORES':     {'ab':4065, 'cerr':[6390], 'ent':[]},
    'DOS CORAZONES': {'ab':5025, 'cerr':[], 'ent':[]},
    'CABSHA':        {'ab':3425, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':1825, 'cerr':[6715,6625], 'ent':[]},
    'DULCE C/NUEZ':  {'ab':4030, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':4530, 'cerr':[6675], 'ent':[]},
    'D. GRANIZADO':  {'ab':1775, 'cerr':[6675,6605], 'ent':[]},
    'DULCE AMORES':  {'ab':1145, 'cerr':[6635,6700], 'ent':[]},
    'SUPER':         {'ab':3910, 'cerr':[6775], 'ent':[]},
    'DURAZNO':       {'ab':5575, 'cerr':[], 'ent':[]},
    'FERRERO':       {'ab':1240, 'cerr':[6365,6530], 'ent':[]},
    'FLAN':          {'ab':2915, 'cerr':[], 'ent':[]},
    'CEREZA':        {'ab':4975, 'cerr':[], 'ent':[]},
    'FRAMBUEZA':     {'ab':3965, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':3135, 'cerr':[6560,6760], 'ent':[]},
    'FRUTILLA REINA':{'ab':4710, 'cerr':[6575], 'ent':[]},
    'FRUTILLA AGUA': {'ab':5630, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':2240, 'cerr':[6580], 'ent':[]},
    'GRANIZADO':     {'ab':5470, 'cerr':[6750], 'ent':[]},
    'LIMON':         {'ab':1960, 'cerr':[6280,6635], 'ent':[]},
    'MANTECOL':      {'ab':3920, 'cerr':[], 'ent':[]},
    'MANZANA':       {'ab':2920, 'cerr':[6365], 'ent':[]},
    'MARROC':        {'ab':4420, 'cerr':[6840], 'ent':[]},
    'MASCARPONE':    {'ab':1330, 'cerr':[6600], 'ent':[]},
    'MENTA':         {'ab':6140, 'cerr':[], 'ent':[]},
    'MIX DE FRUTA':  {'ab':5245, 'cerr':[6790], 'ent':[]},
    'MOUSSE LIMON':  {'ab':4735, 'cerr':[6485], 'ent':[]},
    'SAMBAYON':      {'ab':6235, 'cerr':[6450,6675], 'ent':[]},
    'SAMBAYON AMORES':{'ab':5980, 'cerr':[6600], 'ent':[]},
    'TRAMONTANA':    {'ab':4950, 'cerr':[6790,6665], 'ent':[]},
    'TIRAMIZU':      {'ab':3760, 'cerr':[6560], 'ent':[]},
    'VAINILLA':      {'ab':4140, 'cerr':[6465], 'ent':[]},
    'LEMON PIE':     {'ab':6485, 'cerr':[], 'ent':[]},
    'IRLANDESA':     {'ab':2685, 'cerr':[6605], 'ent':[]},
    'NUTE':          {'ab':1325, 'cerr':[6710], 'ent':[]},
    'RUSA':          {'ab':4015, 'cerr':[], 'ent':[]},
    'FRANUI':        {'ab':4920, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':5440, 'cerr':[6500], 'ent':[]},
    'COCO':          {'ab':4245, 'cerr':[], 'ent':[]},
    'KINDER':        {'ab':3700, 'cerr':[], 'ent':[]},
    'MARACUYA':      {'ab':0, 'cerr':[], 'ent':[6380]},  # ab=None in Excel → 0
    'PISTACHO':      {'ab':2705, 'cerr':[6350,6355], 'ent':[]},
    'CHOCOLATE DUBAI':{'ab':1420, 'cerr':[6400,6355], 'ent':[]},
    'KITKAT':        {'ab':3705, 'cerr':[6390], 'ent':[]},
}

noche = {
    'CADBURY':       {'ab':4030, 'cerr':[6355], 'ent':[]},
    'AMERICANA':     {'ab':2260, 'cerr':[6290], 'ent':[]},
    'ANANA':         {'ab':5370, 'cerr':[], 'ent':[]},
    'B, SPLIT':      {'ab':1885, 'cerr':[6360,6395], 'ent':[]},
    'CHOCOLATE':     {'ab':1535, 'cerr':[6255,6545], 'ent':[]},
    'AMARGO':        {'ab':2230, 'cerr':[6660], 'ent':[]},
    'BLANCO':        {'ab':4970, 'cerr':[6775], 'ent':[]},
    'CH C/ALM':      {'ab':6605, 'cerr':[6525], 'ent':[]},
    'CH AMORES':     {'ab':3655, 'cerr':[6385], 'ent':[]},
    'DOS CORAZONES': {'ab':4320, 'cerr':[], 'ent':[]},
    'CABSHA':        {'ab':2765, 'cerr':[], 'ent':[]},
    'COOKIES':       {'ab':1415, 'cerr':[6705,6625], 'ent':[]},
    'DULCE C/NUEZ':  {'ab':3930, 'cerr':[], 'ent':[]},
    'DULCE D LECHE': {'ab':2910, 'cerr':[6675], 'ent':[]},
    'D. GRANIZADO':  {'ab':3720, 'cerr':[6610], 'ent':[]},
    'DULCE AMORES':  {'ab':6185, 'cerr':[6705], 'ent':[]},
    'SUPER':         {'ab':3285, 'cerr':[6770], 'ent':[]},
    'DURAZNO':       {'ab':5430, 'cerr':[], 'ent':[]},
    'FERRERO':       {'ab':1065, 'cerr':[6530,6360], 'ent':[]},
    'FLAN':          {'ab':2730, 'cerr':[], 'ent':[]},
    'CEREZA':        {'ab':3785, 'cerr':[], 'ent':[]},
    'FRAMBUEZA':     {'ab':3435, 'cerr':[], 'ent':[]},
    'FRUTILLA CREMA':{'ab':935, 'cerr':[6555,6755], 'ent':[]},
    'FRUTILLA REINA':{'ab':4040, 'cerr':[6545], 'ent':[]},
    'FRUTILLA AGUA': {'ab':4775, 'cerr':[], 'ent':[]},
    'BOSQUE':        {'ab':1270, 'cerr':[6570], 'ent':[]},
    'GRANIZADO':     {'ab':4435, 'cerr':[6715], 'ent':[]},
    'LIMON':         {'ab':5315, 'cerr':[6635], 'ent':[]},
    'MANTECOL':      {'ab':3060, 'cerr':[], 'ent':[]},
    'MANZANA':       {'ab':2835, 'cerr':[6365], 'ent':[]},
    'MARROC':        {'ab':3220, 'cerr':[6820], 'ent':[]},
    'MASCARPONE':    {'ab':945, 'cerr':[6595], 'ent':[]},
    'MENTA':         {'ab':3950, 'cerr':[], 'ent':[]},
    'MIX DE FRUTA':  {'ab':5345, 'cerr':[6785], 'ent':[]},
    'MOUSSE LIMON':  {'ab':4660, 'cerr':[6480], 'ent':[]},
    'SAMBAYON':      {'ab':5680, 'cerr':[6575], 'ent':[]},
    'SAMBAYON AMORES':{'ab':5515, 'cerr':[6605], 'ent':[]},
    'TRAMONTANA':    {'ab':3610, 'cerr':[6800,6670], 'ent':[]},
    'TIRAMIZU':      {'ab':2755, 'cerr':[6555], 'ent':[]},
    'VAINILLA':      {'ab':3125, 'cerr':[6405], 'ent':[]},
    'LEMON PIE':     {'ab':6400, 'cerr':[], 'ent':[]},
    'IRLANDESA':     {'ab':2140, 'cerr':[6605], 'ent':[]},
    'NUTE':          {'ab':965, 'cerr':[6685], 'ent':[]},
    'RUSA':          {'ab':3950, 'cerr':[], 'ent':[]},
    'FRANUI':        {'ab':3475, 'cerr':[], 'ent':[]},
    'CIELO':         {'ab':4600, 'cerr':[6505], 'ent':[]},
    'COCO':          {'ab':3990, 'cerr':[], 'ent':[]},
    'KINDER':        {'ab':2770, 'cerr':[], 'ent':[]},
    'MARACUYA':      {'ab':5825, 'cerr':[], 'ent':[6380]},
    'PISTACHO':      {'ab':1155, 'cerr':[6355], 'ent':[]},
    'CHOCOLATE DUBAI':{'ab':6035, 'cerr':[], 'ent':[]},
    'KITKAT':        {'ab':3110, 'cerr':[6390], 'ent':[]},
}

# Timeline context (Capa 1 - datos crudos de turnos adyacentes)
timeline = {
    'SAMBAYON': {
        'D25_DIA':   {'ab':2395, 'cerr':[6450], 'ent':[]},
        'D25_NOCHE': {'ab':1720, 'cerr':[6450], 'ent':[]},
        'D26_DIA':   {'ab':1730, 'cerr':[6455], 'ent':[]},
        'D26_NOCHE': {'ab':2160, 'cerr':[6450], 'ent':[]},
        'D27_DIA':   {'ab':1260, 'cerr':[6450], 'ent':[6575]},
        'D27_NOCHE': {'ab':6235, 'cerr':[], 'ent':[6575]},
    },
    'PISTACHO': {
        'D25_DIA':   {'ab':5775, 'cerr':[6350], 'ent':[]},
        'D25_NOCHE': {'ab':5315, 'cerr':[6355], 'ent':[]},
        'D26_DIA':   None,  # not extracted but cerr 6350/6355 present historically
        'D27_DIA':   {'ab':3600, 'cerr':[6350], 'ent':[]},
        'D27_NOCHE': {'ab':2765, 'cerr':[6355], 'ent':[]},
    },
    'CHOCOLATE DUBAI': {
        'D25_DIA':   {'ab':3445, 'cerr':[6355], 'ent':[]},
        'D25_NOCHE': {'ab':2990, 'cerr':[6355], 'ent':[]},
        'D27_DIA':   {'ab':2285, 'cerr':[6355], 'ent':[]},
        'D27_NOCHE': {'ab':1425, 'cerr':[6355], 'ent':[]},
    },
    'CHOCOLATE': {
        'D27_DIA':   {'ab':5450, 'cerr':[], 'ent':[6545, 6405]},
        'D27_NOCHE': {'ab':4050, 'cerr':[6410], 'ent':[6545, 6405]},
    },
    'MARACUYA': {
        'D27_DIA':   {'ab':0, 'cerr':[], 'ent':[]},
        'D27_NOCHE': {'ab':None, 'cerr':[], 'ent':[]},
    },
}

# =============================================
# CAPA 2: CONTRATO CONTABLE
# =============================================
print("=" * 70)
print("CAPA 2 — CONTRATO CONTABLE: raw_sold por sabor")
print("=" * 70)

results = []
for sabor in dia:
    d = dia[sabor]
    n = noche[sabor]

    total_a = d['ab'] + sum(d['cerr']) + sum(d['ent'])
    total_b = n['ab'] + sum(n['cerr']) + sum(n['ent'])

    # new_entrantes_B
    new_ent_b = 0
    ent_b_used = []
    for eb in n['ent']:
        found = False
        for ea in d['ent']:
            if abs(eb - ea) <= 50:
                found = True
                break
        if not found:
            new_ent_b += eb
            ent_b_used.append(eb)

    n_cerr_a = len(d['cerr'])
    n_cerr_b = len(n['cerr'])
    ajuste_latas = max(0, n_cerr_a - n_cerr_b) * 280
    n_latas = max(0, n_cerr_a - n_cerr_b)

    raw_sold = total_a + new_ent_b - total_b - ajuste_latas

    results.append({
        'sabor': sabor, 'raw': raw_sold, 'latas': n_latas,
        'ab_d': d['ab'], 'ab_n': n['ab'], 'ab_delta': n['ab'] - d['ab'],
        'cerr_d': d['cerr'], 'cerr_n': n['cerr'],
        'ent_d': d['ent'], 'ent_n': n['ent'],
        'total_a': total_a, 'total_b': total_b,
        'new_ent_b': new_ent_b, 'ajuste': ajuste_latas,
    })

# =============================================
# CAPA 3: MOTOR LOCAL — Screening + clasificación
# =============================================
print("\n" + "=" * 70)
print("CAPA 3 — MOTOR LOCAL: Screening y clasificación")
print("=" * 70)

for r in results:
    s = r['sabor']
    d = dia[s]
    n = noche[s]

    ab_sube = r['ab_delta']
    n_cerr_a = len(d['cerr'])
    n_cerr_b = len(n['cerr'])
    cerr_gone = n_cerr_a > n_cerr_b
    apertura_screen = ab_sube > 3000 and cerr_gone  # proxy screening

    flags = []

    # C1: raw >= -50g
    if r['raw'] < -50:
        flags.append('C1:venta_negativa')

    # C2: raw < 5000g o apertura
    if r['raw'] >= 5000 and not apertura_screen:
        flags.append('C2:venta_alta_sin_apertura')

    # C3: ab_N <= ab_D + 20 o apertura
    if n['ab'] > d['ab'] + 20 and not apertura_screen:
        flags.append('C3:ab_sube_sin_apertura')

    # C4: cerrada en solo 1 turno sin match
    for ca in d['cerr']:
        matched = any(abs(ca - cb) <= 30 for cb in n['cerr'])
        if not matched:
            flags.append(f'C4:cerr_D_{int(ca)}_sin_match')
    for cb in n['cerr']:
        matched = any(abs(cb - ca) <= 30 for ca in d['cerr'])
        if not matched:
            flags.append(f'C4:cerr_N_{int(cb)}_sin_match')

    # Determine status
    if not flags:
        if apertura_screen and r['latas'] > 0:
            r['status'] = 'ENGINE'
        else:
            r['status'] = 'LIMPIO'
    else:
        # Count signal types
        signal_types = set(f.split(':')[0] for f in flags)
        if len(signal_types) >= 2:
            r['status'] = 'SOSPECHA_COMPUESTA'
        elif any('C1' in f for f in flags) and r['raw'] < -300:
            r['status'] = 'SOSPECHOSO'
        elif any('C2' in f for f in flags) and r['raw'] >= 5000:
            r['status'] = 'SOSPECHOSO'
        else:
            r['status'] = 'SOSPECHOSO'

    r['flags'] = flags

# Print results by status
for status in ['LIMPIO', 'ENGINE', 'SOSPECHOSO', 'SOSPECHA_COMPUESTA']:
    group = [r for r in results if r['status'] == status]
    if not group:
        continue
    print(f"\n--- {status}: {len(group)} sabores ---")
    for r in sorted(group, key=lambda x: x['sabor']):
        line = f"  {r['sabor']}: raw={r['raw']}g, latas={r['latas']}"
        if r['flags']:
            line += f", flags={r['flags']}"
        if status == 'ENGINE':
            line += f", ab {r['ab_d']}->{r['ab_n']} (+{r['ab_delta']})"
        print(line)

# Totals
print(f"\nTotal raw todos: {sum(r['raw'] for r in results)}g")
print(f"Total LIMPIO: {sum(r['raw'] for r in results if r['status']=='LIMPIO')}g ({len([r for r in results if r['status']=='LIMPIO'])} sabores)")

# =============================================
# ENGINE VERIFICATION (Capa 3.2)
# =============================================
print("\n" + "=" * 70)
print("CAPA 3.2 — VERIFICACIÓN ENGINE")
print("=" * 70)

engines = [r for r in results if r['status'] == 'ENGINE']
for r in engines:
    s = r['sabor']
    d_cerr = set(int(c) for c in dia[s]['cerr'])
    n_cerr = set(int(c) for c in noche[s]['cerr'])
    gone = d_cerr - n_cerr  # cerradas que desaparecieron
    appeared = n_cerr - d_cerr

    rise = r['ab_delta']

    # For each disappeared cerrada, check if rise is coherent
    for g in gone:
        expected_rise = g - 280  # peso cerrada - tapa
        # venta intra-turno razonable: 0-3000g
        min_rise = expected_rise - 3000
        max_rise = expected_rise
        coherent = min_rise <= rise <= max_rise + 500

    print(f"  {s}: ab +{rise}g, cerr_gone={gone}, cerr_appeared={appeared}")
    print(f"    Coherencia apertura: rise {rise} vs esperado ~{list(gone)}[-280]")

# =============================================
# CAPA 3 → CAPA 4: Determinar escalados
# =============================================
print("\n" + "=" * 70)
print("CAPA 3.7 — DECISIÓN DE SALIDA")
print("=" * 70)

sospechosos = [r for r in results if r['status'] in ('SOSPECHOSO', 'SOSPECHA_COMPUESTA')]
for r in sospechosos:
    s = r['sabor']
    flags = r['flags']

    # Check if matchea prototipo fuerte unívoco
    # For now, determine escalation
    signal_types = set(f.split(':')[0] for f in flags)

    if len(signal_types) >= 2:
        r['escalado'] = 'CAPA_4'
        r['reason'] = 'SOSPECHA_COMPUESTA'
    elif abs(r['raw']) > 5000:
        r['escalado'] = 'CAPA_4'
        r['reason'] = 'MAGNITUD_ALTA'
    else:
        r['escalado'] = 'CAPA_4'  # all sospechosos go to analysis
        r['reason'] = 'SEÑAL_SIMPLE'

    print(f"  {s}: {r['escalado']} ({r['reason']}) - flags: {flags}")
