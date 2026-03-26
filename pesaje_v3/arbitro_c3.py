"""
arbitro_c3.py -- Arbitro unico de Capa 3.

Recibe todas las hipotesis, las filtra, las agrupa, y emite un unico veredicto.
Durante esta transicion: multiples targets compatibles escalan conservadoramente.
Calidad no tiene fuerza de veto antes de Fase 7 (tiene_marcas_descalificantes retorna False).
"""
from typing import List
from .modelos import (
    HipotesisCorreccion, ObservacionC3, MarcaCalidad,
    DecisionC3, ResolucionC3, MotivoDecisionC3,
)
from .constantes_c3 import CONFIANZA_MINIMA_FUERTE, CONFIANZA_MINIMA_VIABLE


# Flag: se activa despues de Fase 7 (calidad saneada)
_CALIDAD_TIENE_FUERZA_DE_VETO = False


def tiene_marcas_descalificantes(marcas: List[MarcaCalidad]) -> bool:
    """
    Retorna True si hay marcas que deberian descalificar una hipotesis media.
    DESACTIVADO antes de Fase 7: siempre retorna False.
    """
    if not _CALIDAD_TIENE_FUERZA_DE_VETO:
        return False
    return any(m.penalizacion > 0 for m in marcas)


def resolver_hipotesis(
    hipotesis: List[HipotesisCorreccion],
    obs: ObservacionC3,
    marcas: List[MarcaCalidad],
) -> DecisionC3:
    """
    Arbitro unico. Emite veredicto sobre todas las hipotesis.

    Logica de transicion (replica comportamiento viejo):
    - Exactly 1 hipotesis con confianza viable -> resolver
    - 0 hipotesis -> escalar
    - 2+ hipotesis -> escalar (conflicto)

    Post-transicion el arbitro sera mas sofisticado (agrupar por target, etc).
    """
    # Paso 1: descartar hipotesis invalidas
    viable = []
    descartadas = []
    for h in hipotesis:
        if h.confianza < CONFIANZA_MINIMA_VIABLE:
            descartadas.append(h)
        elif h.contradicciones:
            descartadas.append(h)
        else:
            viable.append(h)

    if not viable:
        return DecisionC3(
            resolucion=ResolucionC3.ESCALAR_C4,
            motivo_codigo=MotivoDecisionC3.SIN_HIPOTESIS_VIABLE,
            hipotesis_descartadas=descartadas,
            motivo_detalle=f'{len(hipotesis)} hipotesis generadas, 0 viables',
        )

    # Paso 2: agrupar por target (para detectar conflictos)
    by_target = {}
    for h in viable:
        clave = h.target.clave_agrupamiento
        by_target.setdefault(clave, []).append(h)

    # Paso 3: dentro de cada grupo, elegir la mejor
    ganadores = []
    for clave, hs in by_target.items():
        if len(hs) == 1:
            ganadores.append(hs[0])
        else:
            # Multiples hipotesis para mismo target: elegir por confianza
            hs.sort(key=lambda h: h.confianza, reverse=True)
            if hs[0].confianza - hs[1].confianza < 0.10:
                # Demasiado cerrado -> conflicto
                return DecisionC3(
                    resolucion=ResolucionC3.ESCALAR_C4,
                    motivo_codigo=MotivoDecisionC3.CONFLICTO_EN_TARGET,
                    hipotesis_descartadas=descartadas + hs,
                    motivo_detalle=f'Conflicto en target {clave}: conf {hs[0].confianza:.2f} vs {hs[1].confianza:.2f}',
                )
            ganadores.append(hs[0])
            descartadas.extend(hs[1:])

    # Paso 4: multiples targets -> filtrar por coherencia, luego desempatar
    if len(ganadores) > 1:
        # 4a: descartar hipotesis cuya venta corregida es incoherente
        coherentes = []
        incoherentes = []
        for g in ganadores:
            if g.venta_propuesta is not None and g.venta_propuesta < -300:
                incoherentes.append(g)
            elif g.venta_propuesta is not None and obs.total_a > 0 and g.venta_propuesta > obs.total_a:
                incoherentes.append(g)
            else:
                coherentes.append(g)

        descartadas.extend(incoherentes)

        if len(coherentes) == 1:
            ganadores = coherentes
        elif len(coherentes) > 1:
            # 4b: desempate por confianza
            coherentes.sort(key=lambda h: h.confianza, reverse=True)
            if coherentes[0].confianza > coherentes[1].confianza:
                descartadas.extend(coherentes[1:])
                ganadores = [coherentes[0]]
            else:
                # 4c: misma confianza -> PF1 (error digito) prioriza por especificidad
                pf1s = [h for h in coherentes if h.codigo_pf == 'PF1']
                if len(pf1s) == 1:
                    descartadas.extend([h for h in coherentes if h is not pf1s[0]])
                    ganadores = pf1s
                else:
                    return DecisionC3(
                        resolucion=ResolucionC3.ESCALAR_C4,
                        motivo_codigo=MotivoDecisionC3.MULTIBLANCO_NO_SOPORTADO,
                        hipotesis_descartadas=descartadas + ganadores,
                        motivo_detalle=f'{len(ganadores)} targets distintos, conflicto genuino',
                    )
        else:
            # Todos incoherentes
            return DecisionC3(
                resolucion=ResolucionC3.ESCALAR_C4,
                motivo_codigo=MotivoDecisionC3.SIN_HIPOTESIS_VIABLE,
                hipotesis_descartadas=descartadas,
                motivo_detalle=f'{len(ganadores)} hipotesis todas incoherentes',
            )

    # Paso 5: exactamente 1 ganadora
    ganadora = ganadores[0]

    # Paso 6: check de calidad (desactivado antes de Fase 7)
    if tiene_marcas_descalificantes(marcas) and ganadora.confianza < CONFIANZA_MINIMA_FUERTE:
        return DecisionC3(
            resolucion=ResolucionC3.ESCALAR_C4,
            motivo_codigo=MotivoDecisionC3.MARCAS_DESCALIFICANTES,
            hipotesis_ganadora=ganadora,
            hipotesis_descartadas=descartadas,
            motivo_detalle=f'Confianza {ganadora.confianza:.2f} con marcas negativas',
        )

    # Paso 7: resolver
    if ganadora.confianza >= CONFIANZA_MINIMA_FUERTE:
        return DecisionC3(
            resolucion=ResolucionC3.CORREGIDO_C3,
            motivo_codigo=MotivoDecisionC3.HIPOTESIS_UNICA_FUERTE,
            hipotesis_ganadora=ganadora,
            hipotesis_descartadas=descartadas,
            motivo_detalle=f'{ganadora.codigo_pf}: {ganadora.descripcion}',
        )
    else:
        return DecisionC3(
            resolucion=ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA,
            motivo_codigo=MotivoDecisionC3.HIPOTESIS_UNICA_BAJA_CONF,
            hipotesis_ganadora=ganadora,
            hipotesis_descartadas=descartadas,
            motivo_detalle=f'{ganadora.codigo_pf} (baja conf={ganadora.confianza:.2f}): {ganadora.descripcion}',
        )
