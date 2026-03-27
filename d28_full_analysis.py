"""Analisis completo D28 por capas."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\EliteBook\Pesaje')

from pesaje_v3.capa1_parser import cargar_dia
from pesaje_v3.capa2_contrato import calcular_contabilidad
from pesaje_v3.capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
from pesaje_v3.capa4_expediente import (resolver_escalados, _paso1_timeline,
    _paso2_plano1, _paso2_plano2, _paso2_plano3, _paso3_hipotesis, _paso4_evaluar)
from pesaje_v3.capa5_residual import segunda_pasada
from pesaje_v3.cli import _armar_resultado
from pesaje_v3.modelos import StatusC3

EXCEL = r'C:\Users\EliteBook\Downloads\Febrero San Martin 2026.xlsx'

datos = cargar_dia(EXCEL, 28)
canon = canonicalizar_nombres(datos)
aplicar_canonicalizacion(datos, canon)
cont = calcular_contabilidad(datos)
c3 = clasificar(datos, cont)
c4 = resolver_escalados(datos, cont, c3)
c5 = segunda_pasada(datos, c3, c4.correcciones, stats={})
r = _armar_resultado(datos, cont, c3, c4)

sep = '=' * 110
print(sep)
print('DIA 28 -- ANALISIS COMPLETO')
print(f'DIA: {datos.turno_dia.nombre_hoja}  NOCHE: {datos.turno_noche.nombre_hoja}')
print(f'Contexto: {[t.nombre_hoja for t in datos.contexto]}')
print(sep)

c4_map = {c.nombre_norm: c for c in c4.correcciones}

for name in sorted(cont.sabores.keys()):
    sc = cont.sabores[name]
    s3 = c3.sabores[name]
    d = datos.turno_dia.sabores.get(name)
    n = datos.turno_noche.sabores.get(name)

    ab_d = d.abierta if d else None
    ab_n = n.abierta if n else None
    cel_d = d.celiaca if d and d.celiaca else None
    cel_n = n.celiaca if n and n.celiaca else None
    cerr_d = list(d.cerradas) if d else []
    cerr_n = list(n.cerradas) if n else []
    ent_d = list(d.entrantes) if d else []
    ent_n = list(n.entrantes) if n else []

    flags_str = ', '.join(f.codigo for f in s3.flags) if s3.flags else '-'

    print(f'--- {name} ---')
    cel_d_s = f' cel={cel_d}' if cel_d else ''
    cel_n_s = f' cel={cel_n}' if cel_n else ''
    print(f'  C1: DIA  ab={ab_d}{cel_d_s} cerr={cerr_d} ent={ent_d} total={sc.total_a}')
    print(f'      NOCHE ab={ab_n}{cel_n_s} cerr={cerr_n} ent={ent_n} total={sc.total_b}')
    print(f'  C2: new_ent={sc.new_ent_b} latas={sc.n_latas} ajuste={sc.ajuste_latas} RAW={sc.venta_raw}')

    proto_str = ''
    if s3.prototipo:
        proto_str = f' PROTO={s3.prototipo.codigo}(d={s3.prototipo.delta:+},v={s3.prototipo.venta_corregida})'
    res = getattr(s3, 'resolution_status', None)
    res_str = f' res={res.value}' if res else ''
    print(f'  C3: status={s3.status.value} flags=[{flags_str}]{proto_str}{res_str} v_c3={s3.venta_final_c3}')

    if s3.marcas:
        for m in s3.marcas:
            if m.tipo != 'DATO_NORMAL':
                det = m.detalle[:50] if m.detalle else ''
                print(f'      marca: {m.tipo} {det}')

    c4c = c4_map.get(name)
    is_h0 = name in c4.sin_resolver

    if s3.status in (StatusC3.SENAL, StatusC3.COMPUESTO) and not s3.prototipo:
        timeline = _paso1_timeline(name, datos)
        p1 = _paso2_plano1(name, datos)
        p2 = _paso2_plano2(name, datos, timeline)
        p3 = _paso2_plano3(name, datos, timeline)
        hips = _paso3_hipotesis(sc, p1, p2, p3)
        _paso4_evaluar(hips, sc, p1, p2, p3)

        print(f'  C4: P1={p1.clasificacion} ab_d={p1.ab_d} ab_n={p1.ab_n} delta={p1.delta_ab} fuente={p1.fuente}')
        desap = ' '.join(str(int(p)) + '(' + str(s) + 's)' for p,s in p2.desaparecen) or '-'
        apar = ' '.join(str(int(p)) + '(' + str(s) + 's)' for p,s in p2.aparecen) or '-'
        pers = ' '.join(str(int(a)) + '->' + str(int(b)) + '(' + str(d) + 'g)' for a,b,d,_ in p2.persisten) or '-'
        print(f'      P2: desap=[{desap}] apar=[{apar}] persist=[{pers}]')
        if p3.ent_a or p3.ent_b:
            print(f'      P3: ent_a={p3.ent_a} ent_b={p3.ent_b} persist={p3.persisten} nuevos={p3.nuevos_b}')

        for h in hips:
            v = sc.venta_raw + h.delta_stock + h.delta_latas * 280
            print(f'      H: {h.tipo:20} w={int(h.peso):>5} d={h.delta_stock:>+7} fav={h.planos_favor} con={h.planos_contra} ->v={v}')

        if c4c:
            print(f'      >> RESUELTO: {c4c.banda.value} conf={c4c.confianza:.2f} delta={c4c.delta:+} venta={c4c.venta_corregida}')
            mot = c4c.motivo[:80]
            print(f'         {mot}')
        elif is_h0:
            print(f'      >> H0: SIN RESOLVER')

    elif s3.status == StatusC3.ENGINE and c4c:
        print(f'  C4: ENGINE_REVIEW: {c4c.banda.value} delta={c4c.delta:+} venta={c4c.venta_corregida}')
        print(f'      {c4c.motivo[:80]}')

    c5s = c5.sabores.get(name)
    if c5s and c5s.status.value != 'LIMPIO_CONFIRMADO':
        ss = ', '.join(s.tipo + ':' + s.subtipo for s in c5s.senales)
        print(f'  C5: {c5s.status.value} [{ss}]')

    vf = c4c.venta_corregida if c4c else s3.venta_final_c3
    print(f'  => VENTA FINAL: {vf}')
    print()

print(sep)
print('RESULTADO FINAL D28:')
print(f'  RAW:        {r.venta_raw:>8,}g')
print(f'  CONFIRMADO: {r.venta_confirmado:>8,}g')
print(f'  OPERATIVO:  {r.venta_operativo:>8,}g')
print(f'  REFINADA:   {r.venta_refinado:>8,}g')
print(f'  VDP:        {r.vdp:>8,}g')
print(f'  LATAS:      {r.n_latas} ({r.lid_discount}g)')
print(f'  H0:         {c4.sin_resolver}')
print(sep)
