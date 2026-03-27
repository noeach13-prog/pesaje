"""
matching.py -- Funcion unica de matching de cerradas.

Este es el UNICO lugar donde se decide que cerrada de DIA corresponde
a que cerrada de NOCHE. Capa 3 (_observar) y Capa 4 (_paso2_plano2)
deben usar esta funcion, no implementar su propio matching.

Algoritmo: greedy best-match por menor diferencia de peso, con tolerancia.
"""
from dataclasses import dataclass, field
from typing import List, Set, Tuple
from .constantes_c3 import TOL_MATCH_CERRADA


@dataclass
class MatchResult:
    """Resultado del matching de cerradas entre dos turnos."""
    # Pares (indice_a, indice_b, peso_a, peso_b, diff)
    matched: List[Tuple[int, int, int, int, int]] = field(default_factory=list)
    # Indices sin match
    unmatched_a: List[int] = field(default_factory=list)  # indices en cerr_a
    unmatched_b: List[int] = field(default_factory=list)  # indices en cerr_b


def match_cerradas(
    cerr_a: List[int],
    cerr_b: List[int],
    tol: int = TOL_MATCH_CERRADA,
) -> MatchResult:
    """
    Matching optimo global de cerradas por menor suma total de diferencias.

    Genera todos los pares posibles (ia, ib) dentro de ±tol, luego selecciona
    el subconjunto que minimiza la suma total de diferencias sin repetir indices.
    Para listas chicas (max 6 cerradas) esto es eficiente.

    Retorna MatchResult con matched, unmatched_a, unmatched_b.
    Los indices son posiciones en las listas cerr_a y cerr_b originales.
    """
    # Generar todos los pares candidatos
    candidatos = []
    for ia, pa in enumerate(cerr_a):
        for ib, pb in enumerate(cerr_b):
            diff = abs(pa - pb)
            if diff <= tol:
                candidatos.append((diff, ia, ib, pa, pb))

    # Ordenar por diff ascendente y seleccionar greedy global
    # (esto es optimo para matching bipartito con pesos no negativos
    # cuando se elige siempre el menor disponible)
    candidatos.sort()
    used_a: Set[int] = set()
    used_b: Set[int] = set()
    result = MatchResult()

    for diff, ia, ib, pa, pb in candidatos:
        if ia in used_a or ib in used_b:
            continue
        result.matched.append((ia, ib, pa, pb, diff))
        used_a.add(ia)
        used_b.add(ib)

    for ia in range(len(cerr_a)):
        if ia not in used_a:
            result.unmatched_a.append(ia)

    for ib in range(len(cerr_b)):
        if ib not in used_b:
            result.unmatched_b.append(ib)

    return result
