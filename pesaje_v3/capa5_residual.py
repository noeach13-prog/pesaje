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
# SEÑALES UTILES PARA EL SUPERVISOR
# Cada señal detecta algo que no se ve mirando un solo turno.
# ===================================================================

def _evaluar_senales_sabor(nombre: str, datos: DatosDia, sc: SaborClasificado,
                           venta_final: int, stats: Dict[str, EstadisticaSabor],
                           correcciones: List[Correccion]) -> List[SenalResidual]:
    """Evalúa todas las señales relevantes para un sabor."""
    senales = []
    d = datos.turno_dia.sabores.get(nombre)
    n = datos.turno_noche.sabores.get(nombre)
    if not d or not n:
        return senales

    pre = sorted([t for t in datos.contexto if t.indice < datos.turno_dia.indice],
                 key=lambda t: t.indice)

    # --- S1: Abierta estancada (copian peso en vez de pesar) ---
    ab_d = d.abierta or 0
    if ab_d > 0 and len(pre) >= 2:
        ab_iguales = 0
        for tc in reversed(pre):
            s = tc.sabores.get(nombre)
            if s and s.abierta is not None:
                if abs((s.abierta or 0) - ab_d) <= 25:
                    ab_iguales += 1
                else:
                    break
        if ab_iguales >= 2:
            senales.append(SenalResidual('S1', 'ABIERTA_ESTANCADA',
                f'La abierta tiene practicamente el mismo peso ({ab_d}g) en {ab_iguales + 1} turnos seguidos. Puede que no la esten pesando.', 0.8))

    # --- S2: Cerrada congelada (lata sin abrir hace muchos turnos) ---
    for cn in n.cerradas:
        cn_int = int(cn)
        turnos_presente = 0
        for tc in pre:
            s = tc.sabores.get(nombre)
            if s and any(abs(cn_int - int(c)) <= 50 for c in s.cerradas):
                turnos_presente += 1
        if turnos_presente >= 6:
            senales.append(SenalResidual('S2', 'CERRADA_CONGELADA',
                f'La cerrada de {cn_int}g lleva al menos {turnos_presente + 1} turnos sin abrirse. Verificar si esta trabada o congelada.', 0.6))
            break  # una por sabor

    # --- S3: Stock nuevo no documentado ---
    cerr_n = [int(c) for c in n.cerradas]
    cerr_d = [int(c) for c in d.cerradas]
    ent_d = [int(e) for e in d.entrantes]
    ent_n = [int(e) for e in n.entrantes]
    for cn in cerr_n:
        in_d = any(abs(cn - cd) <= 200 for cd in cerr_d)
        in_ent = any(abs(cn - e) <= 100 for e in ent_d + ent_n)
        if not in_d and not in_ent:
            # Cerrada nueva sin origen
            senales.append(SenalResidual('S3', 'STOCK_SIN_ORIGEN',
                f'La cerrada de {cn}g aparecio en el turno actual sin estar antes ni figurar como entrante. Posible mercaderia no registrada.', 0.7))
            break

    # --- S4: Venta acumulada inconsistente (venta de hoy + stock final != stock inicial) ---
    # Detecta cuando el stock total no cierra con lo que se vendio.
    # Util para encontrar mermas, regalos o errores de conteo.
    ab_n = n.abierta or 0
    total_d = ab_d + sum(cerr_d) + sum(ent_d)
    total_n = ab_n + sum(cerr_n) + sum(ent_n)
    if total_d > 0 and total_n > total_d and not ent_n:
        incremento = total_n - total_d
        senales.append(SenalResidual('S4', 'STOCK_CRECE_SIN_ENTRANTE',
            f'El stock total subio {incremento}g (de {total_d}g a {total_n}g) sin entrantes registrados. Llego mercaderia sin anotar.', 0.7))

    # --- S5: Abierta subio sin apertura documentada ---
    rise = ab_n - ab_d
    if rise > 2000 and len(cerr_d) > 0 and len(cerr_n) >= len(cerr_d):
        # Abierta subio pero no desaparecio ninguna cerrada
        senales.append(SenalResidual('S5', 'ABIERTA_SUBE_SIN_APERTURA',
            f'La abierta subio {rise}g (de {ab_d}g a {ab_n}g) pero todas las cerradas siguen presentes. No hay apertura que lo explique.', 0.8))

    return senales


def _evaluar_senales_dia(datos: DatosDia, ventas_finales: Dict[str, int],
                          stats: Dict[str, EstadisticaSabor]) -> List[SenalResidual]:
    """Señales a nivel dia (no por sabor)."""
    senales = []

    # --- SD1: Muchos sabores con entrantes sin documentar ---
    n_sin_origen = 0
    for nombre in datos.turno_noche.sabores:
        n_sab = datos.turno_noche.sabores[nombre]
        d_sab = datos.turno_dia.sabores.get(nombre)
        for cn in n_sab.cerradas:
            cn_int = int(cn)
            in_d = d_sab and any(abs(cn_int - int(c)) <= 200 for c in d_sab.cerradas)
            in_ent = d_sab and any(abs(cn_int - int(e)) <= 100 for e in d_sab.entrantes + n_sab.entrantes)
            if not in_d and not in_ent:
                n_sin_origen += 1
                break
    if n_sin_origen >= 3:
        senales.append(SenalResidual('SD1', 'RECEPCION_NO_REGISTRADA',
            f'{n_sin_origen} sabores tienen cerradas nuevas sin entrante documentado. Posible recepcion de mercaderia sin registrar.', 0.7))

    # --- SD2: Muchas abiertas sin cambio (turno sin pesaje real) ---
    n_estancadas = 0
    for nombre in datos.turno_dia.sabores:
        d_sab = datos.turno_dia.sabores[nombre]
        n_sab = datos.turno_noche.sabores.get(nombre)
        if not n_sab:
            continue
        ab_d = d_sab.abierta or 0
        ab_n = n_sab.abierta or 0
        if ab_d > 0 and abs(ab_d - ab_n) <= 10:
            n_estancadas += 1
    total_sab = len(datos.turno_dia.sabores)
    if total_sab > 0 and n_estancadas >= 5 and n_estancadas / total_sab > 0.15:
        senales.append(SenalResidual('SD2', 'PESAJE_DUDOSO',
            f'{n_estancadas} de {total_sab} sabores tienen la abierta identica entre turnos. Puede que no se haya pesado realmente.', 0.8))

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

    # Generar explicaciones por cada señal detectada
    for s in senales:
        L.append(f'  {s.detalle}')

    # Timeline: 4 turnos anteriores + DIA + NOCHE + 2 posteriores
    timeline = _timeline_sabor(nombre, datos)
    if timeline:
        L.append('')
        L.append('HISTORIAL:')
        for entry in timeline:
            L.append(f'  {entry}')

    return '\n'.join(L)


def _timeline_sabor(nombre: str, datos: DatosDia) -> List[str]:
    """Arma secuencia legible del sabor en turnos cercanos."""
    entries = []

    # Contexto antes (hasta 4, ordenados cronológicamente)
    pre = sorted([t for t in datos.contexto if t.indice < datos.turno_dia.indice],
                 key=lambda t: t.indice)
    pre = pre[-4:]  # últimos 4

    for tc in pre:
        s = tc.sabores.get(nombre)
        if s:
            ab = s.abierta or 0
            cel = s.celiaca or 0
            cerr = [int(c) for c in s.cerradas]
            ent = [int(e) for e in s.entrantes]
            parts = [f'ab={ab}']
            if cel:
                parts.append(f'cel={cel}')
            if cerr:
                parts.append(f'cerr={cerr}')
            if ent:
                parts.append(f'ent={ent}')
            entries.append(f'{tc.nombre_hoja}: {", ".join(parts)}')

    # Turno DIA (actual)
    d = datos.turno_dia.sabores.get(nombre)
    if d:
        ab = d.abierta or 0
        cel = d.celiaca or 0
        cerr = [int(c) for c in d.cerradas]
        ent = [int(e) for e in d.entrantes]
        parts = [f'ab={ab}']
        if cel:
            parts.append(f'cel={cel}')
        if cerr:
            parts.append(f'cerr={cerr}')
        if ent:
            parts.append(f'ent={ent}')
        entries.append(f'>> {datos.turno_dia.nombre_hoja}: {", ".join(parts)}')

    # Turno NOCHE (actual)
    n = datos.turno_noche.sabores.get(nombre)
    if n:
        ab = n.abierta or 0
        cel = n.celiaca or 0
        cerr = [int(c) for c in n.cerradas]
        ent = [int(e) for e in n.entrantes]
        parts = [f'ab={ab}']
        if cel:
            parts.append(f'cel={cel}')
        if cerr:
            parts.append(f'cerr={cerr}')
        if ent:
            parts.append(f'ent={ent}')
        entries.append(f'>> {datos.turno_noche.nombre_hoja}: {", ".join(parts)}')

    # Contexto después (hasta 4)
    post = sorted([t for t in datos.contexto if t.indice > datos.turno_noche.indice],
                  key=lambda t: t.indice)
    post = post[:4]

    for tc in post:
        s = tc.sabores.get(nombre)
        if s:
            ab = s.abierta or 0
            cel = s.celiaca or 0
            cerr = [int(c) for c in s.cerradas]
            ent = [int(e) for e in s.entrantes]
            parts = [f'ab={ab}']
            if cel:
                parts.append(f'cel={cel}')
            if cerr:
                parts.append(f'cerr={cerr}')
            if ent:
                parts.append(f'ent={ent}')
            entries.append(f'{tc.nombre_hoja}: {", ".join(parts)}')

    return entries


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

    # Señales a nivel dia
    senales_dia = _evaluar_senales_dia(datos, ventas_finales, stats)
    resultado.senales_dia = senales_dia

    # Evaluar TODOS los sabores con señales útiles para el supervisor
    for nombre, sc in clasificacion.sabores.items():
        if sc.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE):
            continue
        vf = ventas_finales.get(nombre, 0)

        senales = _evaluar_senales_sabor(nombre, datos, sc, vf, stats, correcciones)

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
