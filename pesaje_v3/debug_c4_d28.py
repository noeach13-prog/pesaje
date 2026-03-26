"""Debug: por qué CHOCOLATE, SAMBAYON y PISTACHO fallan en Capa 4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pesaje_v3.capa1_parser import cargar_dia
from pesaje_v3.capa2_contrato import calcular_contabilidad
from pesaje_v3.capa3_motor import clasificar, _aplicar_pf8
from pesaje_v3.capa4_expediente import (
    _paso1_timeline, _paso2_plano1, _paso2_plano2, _paso2_plano3,
    _paso3_hipotesis, _paso4_evaluar, _count_sightings,
)

EXCEL = r"C:\Users\EliteBook\Downloads\Febrero San Martin 2026 (1).xlsx"
datos = cargar_dia(EXCEL, 28)
_aplicar_pf8(datos)
c2 = calcular_contabilidad(datos)
c3 = clasificar(datos, c2)

for nombre in ['CHOCOLATE', 'SAMBAYON', 'PISTACHO']:
    print(f"\n{'='*60}")
    print(f"  {nombre}")
    print(f"{'='*60}")

    sc = c2.sabores[nombre]
    cl = c3.sabores[nombre]

    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    print(f"  DIA:   ab={d.abierta}, cerr={d.cerradas}, ent={d.entrantes}")
    print(f"  NOCHE: ab={n.abierta}, cerr={n.cerradas}, ent={n.entrantes}")
    print(f"  RAW: {sc.venta_raw}g, n_cerr_A={sc.n_cerr_a}, n_cerr_B={sc.n_cerr_b}, latas={sc.n_latas}")

    timeline = _paso1_timeline(nombre, datos)
    print(f"\n  Timeline ({len(timeline)} snapshots):")
    for snap in timeline:
        print(f"    {snap.label}: ab={snap.ab}, cerr={snap.cerradas}, ent={snap.entrantes}")

    p1 = _paso2_plano1(nombre, datos)
    p2 = _paso2_plano2(nombre, datos, timeline)
    p3 = _paso2_plano3(nombre, datos, timeline)

    print(f"\n  P1: {p1.clasificacion}, delta_ab={p1.delta_ab}, fuente={p1.fuente}")
    print(f"  P2: desaparecen={p2.desaparecen}, aparecen={p2.aparecen}")
    print(f"      persisten={p2.persisten}")
    print(f"      sightings={p2.sightings}")
    print(f"  P3: persisten={p3.persisten}, nuevos_b={p3.nuevos_b}, gone_a={p3.gone_a}")

    hips = _paso3_hipotesis(sc, p1, p2, p3)
    _paso4_evaluar(hips, sc, p1, p2, p3)

    print(f"\n  Hipotesis ({len(hips)}):")
    for h in hips:
        venta_corr = sc.venta_raw + h.delta_stock + h.delta_latas * 280
        print(f"    {h.tipo:<16} peso={int(h.peso):>5} delta={h.delta_stock:>+6} "
              f"latas={h.delta_latas:>+2} -> venta={venta_corr:>6}g "
              f"sight={h.sightings} "
              f"favor={h.planos_favor} contra={h.planos_contra} "
              f"indep={h.independientes} conv={'YES' if h.converge else 'no'}")
