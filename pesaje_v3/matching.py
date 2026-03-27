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
    Matching greedy de cerradas por menor diferencia de peso.

    Para cada cerrada en A, busca la mejor match en B dentro de ±tol.
    Greedy: una cerrada de B solo puede matchear con una de A.

    Retorna MatchResult con matched, unmatched_a, unmatched_b.
    Los indices son posiciones en las listas cerr_a y cerr_b originales.
    """
    result = MatchResult()
    used_b: Set[int] = set()

    for ia, pa in enumerate(cerr_a):
        best_ib = -1
        best_diff = tol + 1  # peor que tolerancia

        for ib, pb in enumerate(cerr_b):
            if ib in used_b:
                continue
            diff = abs(pa - pb)
            if diff <= tol and diff < best_diff:
                best_ib = ib
                best_diff = diff

        if best_ib >= 0:
            result.matched.append((ia, best_ib, pa, cerr_b[best_ib], best_diff))
            used_b.add(best_ib)
        else:
            result.unmatched_a.append(ia)

    for ib in range(len(cerr_b)):
        if ib not in used_b:
            result.unmatched_b.append(ib)

    return result
