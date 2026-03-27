"""
capa2_contrato.py — Fórmula de venta pura.
Sin lógica, sin inferencia. Solo aritmética.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parser import text_to_grams

from .modelos import DatosDia, SaborContable, ContabilidadDia


def _matching_entrantes(ent_a: list, ent_b: list, tolerancia: int = 50) -> int:
    """
    Calcula la suma de entrantes en B que NO estaban en A (dentro de tolerancia).
    Retorna new_ent_b en gramos.
    """
    restantes_a = list(ent_a)
    new_ent_b = 0

    for eb in ent_b:
        encontrado = False
        for i, ea in enumerate(restantes_a):
            if abs(eb - ea) <= tolerancia:
                encontrado = True
                restantes_a.pop(i)
                break
        if not encontrado:
            new_ent_b += eb

    return new_ent_b


def calcular_contabilidad(datos: DatosDia) -> ContabilidadDia:
    """
    Aplica la fórmula de venta a cada sabor del día.
    Fórmula inmutable:
        venta = total_A + new_ent_B - total_B - ajuste_latas
        ajuste_latas = max(0, n_cerr_A - n_cerr_B) * 280
    """
    resultado = ContabilidadDia(dia_label=datos.dia_label)
    dia = datos.turno_dia
    noche = datos.turno_noche

    todos_sabores = sorted(set(list(dia.sabores.keys()) + list(noche.sabores.keys())))

    for nombre in todos_sabores:
        d = dia.sabores.get(nombre)
        n = noche.sabores.get(nombre)

        # SOLO_DIA / SOLO_NOCHE
        if d is None:
            resultado.sabores[nombre] = SaborContable(
                nombre_norm=nombre,
                nombre_display=n.nombre,
                total_a=0, total_b=n.total,
                new_ent_b=0, n_cerr_a=0, n_cerr_b=len(n.cerradas),
                n_latas=0, ajuste_latas=0, venta_raw=0,
                solo_noche=True,
            )
            continue

        if n is None:
            resultado.sabores[nombre] = SaborContable(
                nombre_norm=nombre,
                nombre_display=d.nombre,
                total_a=d.total, total_b=0,
                new_ent_b=0, n_cerr_a=len(d.cerradas), n_cerr_b=0,
                n_latas=0, ajuste_latas=0, venta_raw=0,
                solo_dia=True,
            )
            continue

        # Ambos turnos presentes
        total_a = d.total
        total_b = n.total
        new_ent_b = _matching_entrantes(d.entrantes, n.entrantes)

        n_cerr_a = len(d.cerradas)
        n_cerr_b = len(n.cerradas)
        n_latas = max(0, n_cerr_a - n_cerr_b)
        ajuste = n_latas * 280

        # Ajuste entrante promovido a cerrada:
        # Si una cerrada NOCHE matchea con un entrante DIA (y NO con cerrada DIA),
        # es un entrante que se convirtió en cerrada.
        # PERO: total_A ya incluye el entrante y total_B ya incluye la cerrada,
        # así que la promoción se cancela naturalmente en total_A - total_B.
        # El ajuste solo aplica cuando el entrante DIA TAMBIÉN persiste en NOCHE
        # como entrante (no fue consumido). En ese caso, total_B cuenta la cerrada
        # promovida + el entrante persistente, y necesitamos compensar.
        ajuste_promo = 0
        restantes_ent_a = list(d.entrantes)
        for cn in n.cerradas:
            # Ya matchea con cerrada DIA? -> no es promocion
            if any(abs(cn - cd) <= 200 for cd in d.cerradas):
                continue
            # Matchea con entrante DIA? -> posible promocion
            for i, ea in enumerate(restantes_ent_a):
                if abs(cn - ea) <= 100:
                    # Solo ajustar si el entrante NO persiste en NOCHE
                    # (si persiste, total_B ya lo cuenta correctamente)
                    ent_persiste = any(abs(ea - en) <= 50 for en in n.entrantes)
                    if not ent_persiste:
                        # Entrante DIA se convirtió en cerrada NOCHE y desapareció
                        # como entrante. total_A tiene el ent, total_B tiene la cerr.
                        # Se cancelan. NO ajustar.
                        pass
                    else:
                        # Entrante DIA persiste en NOCHE como entrante Y apareció
                        # como cerrada NOCHE. El entrante en total_B resta doble.
                        # Compensar sumando el peso de la cerrada promovida.
                        ajuste_promo += cn
                    restantes_ent_a.pop(i)
                    break

        # venta_raw SIN descuento de latas (convención spec).
        # El ajuste se aplica al total final, no por sabor.
        venta_raw = total_a + new_ent_b + ajuste_promo - total_b

        nombre_display = d.nombre if d.nombre else n.nombre
        resultado.sabores[nombre] = SaborContable(
            nombre_norm=nombre,
            nombre_display=nombre_display,
            total_a=total_a, total_b=total_b,
            new_ent_b=new_ent_b,
            n_cerr_a=n_cerr_a, n_cerr_b=n_cerr_b,
            n_latas=n_latas, ajuste_latas=ajuste,
            venta_raw=venta_raw,
        )

    # VDP
    vdp = 0
    for txt in dia.vdp_textos + noche.vdp_textos:
        vdp += int(text_to_grams(txt))
    resultado.vdp_total = vdp

    # Total raw
    resultado.venta_raw_total = sum(
        s.venta_raw for s in resultado.sabores.values()
        if not s.solo_dia and not s.solo_noche
    )

    return resultado
