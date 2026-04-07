"""
capa5_residual.py -- Segunda pasada residual.

Detecta sabores LIMPIO con errores compensados invisibles al screening.
Senales: R1 (desvio historico), R2 (rareza estructural), R3 (perfil dia anomalo).
"""
from .modelos import (
    DatosDia, ContabilidadDia, ResultadoC3, SaborClasificado,
    StatusC3, StatusC5, SenalResidual, Correccion,
)
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math


# ===================================================================
# ESTADISTICAS HISTORICAS
# ===================================================================

@dataclass
class EstadisticaSabor:
    """Media y std de venta de un sabor en el mes."""
    nombre_norm: str
    media: float
    std: float
    n_periodos: int


def calcular_estadisticas(ventas_por_sabor: Dict[str, List[int]]) -> Dict[str, EstadisticaSabor]:
    """
    Calcula media/std por sabor a partir de un dict {nombre: [venta_dia1, venta_dia2, ...]}.
    Solo periodos donde venta > 0 (excluir dias sin presencia).
    """
    stats = {}
    for nombre, ventas in ventas_por_sabor.items():
        positivas = [v for v in ventas if v > 0]
        n = len(positivas)
        if n < 2:
            stats[nombre] = EstadisticaSabor(nombre, 0, 0, n)
            continue
        media = sum(positivas) / n
        var = sum((v - media) ** 2 for v in positivas) / (n - 1)
        std = math.sqrt(var) if var > 0 else 0
        stats[nombre] = EstadisticaSabor(nombre, media, std, n)
    return stats


# ===================================================================
# R1: Desvio historico del sabor
# ===================================================================

def _evaluar_r1(nombre: str, venta_final: int, stats: Dict[str, EstadisticaSabor],
                tiene_apertura: bool) -> Optional[SenalResidual]:
    est = stats.get(nombre)
    if not est or est.n_periodos < 5 or est.std > 2000 or est.std == 0:
        return None

    z = (venta_final - est.media) / est.std

    # Apertura confirmada con venta alta -> no marcar
    if tiene_apertura and z > 0:
        return None

    abs_z = abs(z)
    if abs_z <= 1.5:
        return None
    elif abs_z <= 1.8:
        return SenalResidual('R1', 'R1_LEVE', f'z={z:.2f} (media={est.media:.0f}, std={est.std:.0f})', 0.3)
    elif abs_z <= 2.5:
        return SenalResidual('R1', 'R1_MODERADO', f'z={z:.2f} (media={est.media:.0f}, std={est.std:.0f})', 0.6)
    else:
        return SenalResidual('R1', 'R1_FUERTE', f'z={z:.2f} (media={est.media:.0f}, std={est.std:.0f})', 0.9)


# ===================================================================
# R2: Rareza estructural debil
# ===================================================================

def _evaluar_r2(nombre: str, datos: DatosDia, sc: SaborClasificado) -> Optional[SenalResidual]:
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return None

    sub_senales = []

    # R2a: 2+ cerradas con diff 30-75g (zona ambigua)
    for cd in d.cerradas:
        for cn in n.cerradas:
            diff = abs(cd - cn)
            if 30 < diff <= 75:
                sub_senales.append('R2a')
                break
        if 'R2a' in sub_senales:
            break

    # R2b: Ab no cambio (+-5g) en periodo con venta final >500g
    ab_d = d.abierta or 0
    ab_n = n.abierta or 0
    vf = sc.venta_final_c3 or 0
    if abs(ab_d - ab_n) <= 5 and vf > 500:
        sub_senales.append('R2b')

    # R2c: Entrante sin genealogia (aparece solo en NOCHE, no en contexto)
    for en_val in n.entrantes:
        if not any(abs(en_val - ed) <= 50 for ed in d.entrantes):
            # Entrante nuevo en NOCHE -- buscar en contexto
            found = False
            for ctx in datos.contexto:
                s = ctx.sabores.get(nombre)
                if s:
                    if any(abs(en_val - c) <= 30 for c in s.cerradas + s.entrantes):
                        found = True
                        break
            if not found:
                sub_senales.append('R2c')
                break

    # R2d: Cerrada con 1 solo sighting preservada
    from .capa3_motor import _count_sightings_cerr
    for cn in n.cerradas:
        sightings = _count_sightings_cerr(cn, nombre, datos)
        if sightings <= 1:
            sub_senales.append('R2d')
            break

    # R2e: Matching en borde (25-35g)
    for cd in d.cerradas:
        for cn in n.cerradas:
            diff = abs(cd - cn)
            if 25 <= diff <= 35:
                sub_senales.append('R2e')
                break
        if 'R2e' in sub_senales:
            break

    sub_senales = list(set(sub_senales))
    if len(sub_senales) >= 2:
        return SenalResidual('R2', 'R2_FUERTE', f'sub-senales: {", ".join(sorted(sub_senales))}', 0.6)
    elif len(sub_senales) == 1:
        return SenalResidual('R2', f'R2_{sub_senales[0]}', sub_senales[0], 0.3)
    return None


# ===================================================================
# R3: Perfil de dia anomalo
# ===================================================================

def _evaluar_r3(ventas_finales: Dict[str, int],
                stats: Dict[str, EstadisticaSabor],
                media_dia: float, std_dia: float) -> List[SenalResidual]:
    senales = []

    # Calcular z-scores de todos los sabores
    z_scores = {}
    for nombre, vf in ventas_finales.items():
        est = stats.get(nombre)
        if est and est.n_periodos >= 5 and est.std > 0:
            z_scores[nombre] = (vf - est.media) / est.std

    # R3a: >=2 sabores con desvios fuertes en direcciones opuestas
    fuertes_pos = [n for n, z in z_scores.items() if z > 2.0]
    fuertes_neg = [n for n, z in z_scores.items() if z < -2.0]
    if len(fuertes_pos) >= 1 and len(fuertes_neg) >= 1:
        senales.append(SenalResidual('R3', 'R3a',
            f'{len(fuertes_pos)} fuertes+, {len(fuertes_neg)} fuertes-', 0.5))

    # R3b: >=3 sabores simultaneamente >1.5 sigma
    outliers = [n for n, z in z_scores.items() if abs(z) > 1.5]
    if len(outliers) >= 3:
        senales.append(SenalResidual('R3', 'R3b',
            f'{len(outliers)} sabores >1.5 sigma', 0.4))

    # R3c: Total ventas del dia difiere >2 sigma del promedio diario
    total_dia = sum(ventas_finales.values())
    if std_dia > 0:
        z_dia = (total_dia - media_dia) / std_dia
        if abs(z_dia) > 2.0:
            senales.append(SenalResidual('R3', 'R3c',
                f'total dia z={z_dia:.2f} ({total_dia}g vs media {media_dia:.0f}g)', 0.6))

    return senales


# ===================================================================
# DIAGNOSTICO ACCIONABLE
# ===================================================================

def _diagnostico_accionable(nombre: str, venta_final: int,
                             senales: List[SenalResidual],
                             stats: Dict[str, 'EstadisticaSabor'],
                             sc: SaborClasificado,
                             datos: DatosDia,
                             correcciones: List[Correccion]) -> str:
    """Genera explicación en español con diagnóstico y acción sugerida."""
    if not senales:
        return ''

    tipos = {s.tipo for s in senales}
    L = []

    est = stats.get(nombre)
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)

    # R1: desvío histórico
    r1 = next((s for s in senales if s.tipo == 'R1'), None)
    if r1 and est and est.std > 0:
        z = (venta_final - est.media) / est.std
        direccion = 'alta' if z > 0 else 'baja'

        L.append(f'{nombre}: la venta de este turno ({venta_final}g) es {direccion} comparada con el promedio del mes ({est.media:.0f}g).')

        if abs(z) > 2.0:
            # Desvío fuerte — diagnosticar causa probable
            if z > 2.0 and venta_final > 5000:
                L.append(f'POSIBLE CAUSA: Una cerrada pudo no haberse registrado en el turno actual, inflando la venta.')
                L.append(f'ACCION: Verificar con el empleado si todas las latas cerradas del sabor estan anotadas.')
            elif z > 2.0:
                L.append(f'POSIBLE CAUSA: Venta inusualmente alta. Puede ser un dia de mucha demanda o un error de pesaje en la abierta.')
                L.append(f'ACCION: Comparar la abierta con los turnos anteriores y siguientes.')
            elif z < -2.0 and venta_final < 0:
                L.append(f'POSIBLE CAUSA: La venta negativa indica que aparecio mas stock del que habia. Probablemente falto registrar un entrante.')
                L.append(f'ACCION: Preguntar al empleado si llego stock nuevo que no se anoto.')
            elif z < -2.0:
                L.append(f'POSIBLE CAUSA: Venta muy baja. Puede haber una cerrada anotada de mas o un error en la abierta.')
                L.append(f'ACCION: Revisar si los pesos de las cerradas coinciden con los turnos cercanos.')
        elif abs(z) > 1.5:
            L.append(f'Desvio leve respecto al promedio. Probablemente normal, pero queda marcado por si se repite.')

    # R2: rareza estructural
    r2 = next((s for s in senales if s.tipo == 'R2'), None)
    if r2:
        sub = r2.detalle
        if 'R2a' in sub and 'R2e' in sub:
            L.append(f'OBSERVACION: Hay cerradas con diferencias de peso en zona ambigua (30-75g) y justo en el borde de tolerancia (25-35g).')
            L.append(f'ACCION: Verificar que no se hayan intercambiado latas entre sabores o que no haya error de pesaje.')
        elif 'R2a' in sub:
            L.append(f'OBSERVACION: Hay cerradas con diferencia de 30-75g entre turnos. El sistema las considero como la misma lata, pero podrian ser latas distintas.')
            L.append(f'ACCION: Comparar los pesos de cerradas con los turnos anteriores para confirmar identidad.')
        elif 'R2b' in sub:
            L.append(f'OBSERVACION: La abierta no cambio entre turnos pero la venta final es alta. Eso es raro.')
            L.append(f'ACCION: Verificar si la abierta se peso correctamente en ambos turnos.')
        elif 'R2d' in sub:
            L.append(f'OBSERVACION: Hay una cerrada que solo aparece en este turno y no tiene historial en turnos cercanos.')
            L.append(f'ACCION: Verificar si es una lata nueva que deberia figurar como entrante.')
        elif 'R2e' in sub:
            L.append(f'OBSERVACION: Hay cerradas con diferencia justo en el borde de tolerancia (25-35g). El matching podria ser incorrecto.')
            L.append(f'ACCION: Revisar si esas cerradas son la misma lata o latas distintas.')

    # Corrección existente + señal = contexto adicional
    corr = next((c for c in correcciones if c.nombre_norm == nombre), None)
    if corr and r1:
        L.append(f'NOTA: Este sabor ya tiene una correccion aplicada (delta={corr.delta:+d}g). La senal C5 evalua el resultado DESPUES de la correccion.')

    return '\n'.join(L)


# ===================================================================
# MOTOR PRINCIPAL CAPA 5
# ===================================================================

@dataclass
class ResultadoC5Sabor:
    nombre_norm: str
    status: StatusC5
    senales: List[SenalResidual] = field(default_factory=list)
    explicacion: str = ''  # Diagnóstico accionable para el supervisor


@dataclass
class ResultadoC5:
    dia_label: str
    sabores: Dict[str, ResultadoC5Sabor] = field(default_factory=dict)
    senales_dia: List[SenalResidual] = field(default_factory=list)  # R3

    @property
    def reaperturas(self) -> List[str]:
        return [k for k, v in self.sabores.items() if v.status == StatusC5.REABRIR]


def segunda_pasada(
    datos: DatosDia,
    clasificacion: ResultadoC3,
    correcciones: List[Correccion],
    stats: Dict[str, EstadisticaSabor],
    media_dia: float = 0,
    std_dia: float = 0,
) -> ResultadoC5:
    """
    Capa 5: segunda pasada residual sobre sabores LIMPIO.
    """
    resultado = ResultadoC5(dia_label=datos.dia_label)

    # Armar ventas finales de todo el dia (para R3)
    ventas_finales = {}
    corr_map = {c.nombre_norm: c for c in correcciones}

    for nombre, sc in clasificacion.sabores.items():
        if nombre in corr_map:
            ventas_finales[nombre] = corr_map[nombre].venta_corregida
        elif sc.venta_final_c3 is not None:
            ventas_finales[nombre] = sc.venta_final_c3
        else:
            ventas_finales[nombre] = sc.contable.venta_raw

    # R3 a nivel dia
    senales_r3 = _evaluar_r3(ventas_finales, stats, media_dia, std_dia)
    resultado.senales_dia = senales_r3

    # Evaluar TODOS los sabores (no solo LIMPIO).
    # R1 (desvío histórico) es útil para CORREGIDOS y ENGINE también:
    # una venta corregida que sigue siendo outlier merece revisión.
    # R2 (rareza estructural) sigue siendo más relevante para LIMPIO.
    for nombre, sc in clasificacion.sabores.items():
        if sc.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
            continue
        senales = []
        vf = ventas_finales.get(nombre, 0)

        # R1
        tiene_apertura = sc.status == StatusC3.ENGINE
        r1 = _evaluar_r1(nombre, vf, stats, tiene_apertura)
        if r1:
            senales.append(r1)

        # R2
        r2 = _evaluar_r2(nombre, datos, sc)
        if r2:
            senales.append(r2)

        # R3 aplica a nivel dia, afecta a todos los limpios
        for r3 in senales_r3:
            senales.append(r3)

        # Clasificar
        tipos_distintos = set(s.tipo for s in senales if s.peso >= 0.3)
        if len(tipos_distintos) >= 2:
            status = StatusC5.REABRIR
        elif len(senales) > 0:
            status = StatusC5.LIMPIO_CON_NOTA
        else:
            status = StatusC5.LIMPIO_CONFIRMADO

        # Generar explicación accionable
        explicacion = _diagnostico_accionable(
            nombre, vf, senales, stats, sc, datos, correcciones)

        resultado.sabores[nombre] = ResultadoC5Sabor(
            nombre_norm=nombre,
            status=status,
            senales=senales,
            explicacion=explicacion,
        )

    # Maximo 5 reaperturas, priorizar por peso total de senales
    reaperturas = [(k, v) for k, v in resultado.sabores.items() if v.status == StatusC5.REABRIR]
    if len(reaperturas) > 5:
        reaperturas.sort(key=lambda x: sum(s.peso for s in x[1].senales), reverse=True)
        for k, v in reaperturas[5:]:
            v.status = StatusC5.LIMPIO_CON_NOTA

    return resultado
