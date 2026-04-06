"""
validacion_entrada.py — Validación por niveles para la web de carga.

Reutiliza funciones existentes del pipeline. No duplica lógica.

Niveles:
1. Campo:  ya se hace client+server en db.py (validar_sabor_server)
2. Sabor:  PFIT intra-turno (entrante ≈ cerrada)
3. Turno:  INTRADUP_MASIVO, colisión nombres
4. Screening: C1-C4 (requiere ambos turnos)
5. Cross-turno: PF1-PF7 pipeline completo (requiere contexto)
"""
from typing import List, Dict, Optional
import sqlite3

from .db_to_pipeline import armar_datos_dia
from .db import get_db


def analizar_turno(db: sqlite3.Connection, turno_id: int) -> Dict:
    """
    Corre el pipeline completo sobre un turno y retorna:
    - alertas de validación (niveles 3-5)
    - ventas por sabor (raw + corregida + delta)
    - totales del día
    - correcciones aplicadas

    Es lo que se muestra al confirmar. Reusa el pipeline existente
    sin duplicar nada.
    """
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return {'ok': False, 'error': 'Turno no encontrado'}

    suc = db.execute("SELECT * FROM sucursales WHERE id = ?", (turno['sucursal_id'],)).fetchone()

    resultado = {
        'ok': True,
        'alertas': [],
        'sabores': [],
        'totales': {},
        'tiene_analisis': False,
    }

    # Nivel 3: validaciones de turno
    alertas_turno = _validar_nivel3_turno(db, turno_id, turno, suc)
    resultado['alertas'].extend(alertas_turno)

    # Armar DatosDia para pipeline
    datos_dia = armar_datos_dia(db, turno['sucursal_id'], turno['fecha'])
    if not datos_dia:
        modo = suc['modo'] if suc else 'DIA_NOCHE'
        tipo = turno['tipo_turno']
        fecha = turno['fecha']
        if modo == 'DIA_NOCHE':
            falta = 'NOCHE' if tipo == 'DIA' else 'DIA'
            msg = f'Para ver el analisis de ventas del {fecha}, falta cargar el turno {falta} de ese mismo dia.'
        else:
            msg = f'Para ver el analisis de ventas del {fecha}, falta cargar el turno del dia anterior.'
        resultado['alertas'].append({
            'nivel': 'info', 'severidad': 'info', 'sabor': None,
            'codigo': 'SIN_PAR', 'detalle': msg,
        })
        return resultado

    # Correr pipeline completo
    try:
        from .capa2_contrato import calcular_contabilidad
        from .capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
        from .capa4_expediente import resolver_escalados
        from .modelos import ResolucionC3

        canon = canonicalizar_nombres(datos_dia)
        aplicar_canonicalizacion(datos_dia, canon)
        cont = calcular_contabilidad(datos_dia)
        c3 = clasificar(datos_dia, cont)
        c4 = resolver_escalados(datos_dia, cont, c3)

        resultado['tiene_analisis'] = True

        # Ventas por sabor
        venta_total = 0
        latas_total = 0
        n_corregidos = 0
        n_h0 = 0

        for nombre in sorted(c3.sabores.keys()):
            sc3 = c3.sabores[nombre]
            sc = sc3.contable
            if sc.solo_dia or sc.solo_noche:
                continue

            res = sc3.resolution_status
            vf = sc3.venta_final_c3 if sc3.venta_final_c3 is not None else sc.venta_raw

            # Corrección de C4
            c4_corr = next((c for c in c4.correcciones if c.nombre_norm == nombre), None)
            if c4_corr:
                vf = c4_corr.venta_corregida

            proto = sc3.prototipo
            delta = proto.delta if proto else (c4_corr.delta if c4_corr else 0)

            if res and res == ResolucionC3.ESCALAR_C4:
                status = 'H0'
                n_h0 += 1
            elif proto or c4_corr:
                status = 'CORREGIDO'
                n_corregidos += 1
            else:
                status = 'OK'

            sabor_info = {
                'nombre': nombre,
                'raw': sc.venta_raw,
                'final': vf,
                'delta': delta,
                'status': status,
                'n_latas': sc.n_latas,
                'ajuste_latas': sc.ajuste_latas,
            }

            if proto:
                sabor_info['correccion'] = proto.descripcion[:80]
                sabor_info['confianza'] = proto.confianza
            elif c4_corr:
                sabor_info['correccion'] = c4_corr.motivo[:80]
                sabor_info['confianza'] = c4_corr.confianza

            # Alerta si hay problema
            if vf < -200:
                resultado['alertas'].append({
                    'nivel': 'analisis', 'severidad': 'error', 'sabor': nombre,
                    'codigo': 'VENTA_NEG', 'detalle': f'Venta = {vf}g (negativa)',
                })
            elif status == 'H0' and abs(vf) > 1000:
                resultado['alertas'].append({
                    'nivel': 'analisis', 'severidad': 'warning', 'sabor': nombre,
                    'codigo': 'H0', 'detalle': f'Sin resolver: venta raw = {sc.venta_raw}g',
                })

            venta_total += vf
            latas_total += sc.ajuste_latas
            resultado['sabores'].append(sabor_info)

        resultado['totales'] = {
            'venta': venta_total,
            'latas': latas_total,
            'n_latas': latas_total // 280 if latas_total else 0,
            'vdp': cont.vdp_total,
            'neto': venta_total - latas_total - cont.vdp_total,
            'n_sabores': len(resultado['sabores']),
            'n_corregidos': n_corregidos,
            'n_h0': n_h0,
        }

    except Exception as e:
        resultado['alertas'].append({
            'nivel': 'analisis', 'severidad': 'info', 'sabor': None,
            'codigo': 'PIPELINE_ERROR', 'detalle': f'Error en analisis: {str(e)[:120]}',
        })

    # Conteo de alertas
    resultado['n_errores'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'error')
    resultado['n_warnings'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'warning')

    return resultado


def validar_turno_completo(db: sqlite3.Connection, turno_id: int) -> Dict:
    """
    Corre todos los niveles de validación posibles para un turno.
    Retorna dict con alertas agrupadas por nivel y un resumen.
    """
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return {'ok': False, 'error': 'Turno no encontrado', 'alertas': []}

    suc = db.execute("SELECT * FROM sucursales WHERE id = ?", (turno['sucursal_id'],)).fetchone()
    resultado = {
        'ok': True,
        'alertas': [],
        'n_errores': 0,
        'n_warnings': 0,
        'resumen': {},
    }

    # ── Nivel 3: validaciones de turno ────────────────────────────
    alertas_turno = _validar_nivel3_turno(db, turno_id, turno, suc)
    resultado['alertas'].extend(alertas_turno)

    # ── Niveles 4-5: requieren DatosDia (ambos turnos + contexto) ──
    datos_dia = armar_datos_dia(db, turno['sucursal_id'], turno['fecha'])
    if datos_dia:
        alertas_screening = _validar_nivel4_screening(datos_dia)
        resultado['alertas'].extend(alertas_screening)

        alertas_cross = _validar_nivel5_cross_turno(datos_dia)
        resultado['alertas'].extend(alertas_cross)
    else:
        resultado['alertas'].append({
            'nivel': 'info',
            'severidad': 'info',
            'sabor': None,
            'codigo': 'SIN_PAR',
            'detalle': 'No se puede correr validación completa: falta el turno par (DIA/NOCHE) o el turno anterior.',
        })

    # Conteo
    resultado['n_errores'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'error')
    resultado['n_warnings'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'warning')

    return resultado


def _validar_nivel3_turno(db, turno_id, turno, suc) -> List[Dict]:
    """Nivel 3: INTRADUP_MASIVO + colisión nombres."""
    alertas = []

    sabores = db.execute(
        "SELECT * FROM sabores_turno WHERE turno_id = ?", (turno_id,)
    ).fetchall()

    # Colisión de nombres: dos filas con mismo nombre_norm
    norms = {}
    for s in sabores:
        nn = s['nombre_norm']
        if nn in norms:
            alertas.append({
                'nivel': 'turno',
                'severidad': 'error',
                'sabor': nn,
                'codigo': 'NOMBRE_DUP',
                'detalle': f'Sabor "{nn}" aparece duplicado en el turno.',
            })
        norms[nn] = True

    # INTRADUP: entrante ≈ cerrada en mismo turno (por sabor)
    from .constantes_c3 import PFIT_TOL_INTRA
    n_intradup = 0
    for s in sabores:
        cerradas = [s[f'cerrada_{i}'] for i in range(1, 7) if s[f'cerrada_{i}'] is not None]
        entrantes = [s[f'entrante_{i}'] for i in range(1, 3) if s[f'entrante_{i}'] is not None]
        for e in entrantes:
            for c in cerradas:
                if abs(e - c) <= PFIT_TOL_INTRA:
                    n_intradup += 1
                    alertas.append({
                        'nivel': 'turno',
                        'severidad': 'warning',
                        'sabor': s['nombre_norm'],
                        'codigo': 'INTRADUP',
                        'detalle': f'Entrante {e}g coincide con cerrada {c}g (dif {abs(e-c)}g). Posible doble registro.',
                    })
                    break  # uno por sabor

    from .constantes_c3 import INTRADUP_MASIVO_MIN_SABORES
    if n_intradup >= INTRADUP_MASIVO_MIN_SABORES:
        alertas.append({
            'nivel': 'turno',
            'severidad': 'error',
            'sabor': None,
            'codigo': 'INTRADUP_MASIVO',
            'detalle': f'{n_intradup} sabores con patron de doble registro. Posible error sistematico en la planilla.',
        })

    return alertas


def _validar_nivel4_screening(datos_dia) -> List[Dict]:
    """Nivel 4: screening C1-C4 reutilizando el pipeline."""
    alertas = []

    try:
        from .capa2_contrato import calcular_contabilidad
        from .capa3_motor import _observar, _screening, canonicalizar_nombres, aplicar_canonicalizacion

        canon = canonicalizar_nombres(datos_dia)
        aplicar_canonicalizacion(datos_dia, canon)
        cont = calcular_contabilidad(datos_dia)

        for nombre, sc in cont.sabores.items():
            if sc.solo_dia or sc.solo_noche:
                continue

            obs = _observar(nombre, sc, datos_dia)
            status, flags = _screening(nombre, sc, obs, modo=datos_dia.modo)

            for flag in flags:
                sev = 'error' if flag.condicion <= 1 else 'warning'
                alertas.append({
                    'nivel': 'screening',
                    'severidad': sev,
                    'sabor': nombre,
                    'codigo': flag.codigo,
                    'detalle': flag.detalle,
                })

            # Venta negativa fuerte
            if sc.venta_raw < -300:
                alertas.append({
                    'nivel': 'screening',
                    'severidad': 'error',
                    'sabor': nombre,
                    'codigo': 'VENTA_NEG',
                    'detalle': f'Venta raw = {sc.venta_raw}g (muy negativa). Revisar pesos.',
                })

    except Exception as e:
        alertas.append({
            'nivel': 'screening',
            'severidad': 'info',
            'sabor': None,
            'codigo': 'SCREENING_ERROR',
            'detalle': f'Error al correr screening: {str(e)[:100]}',
        })

    return alertas


def _validar_nivel5_cross_turno(datos_dia) -> List[Dict]:
    """Nivel 5: pipeline completo (PF1-PF7) para detectar anomalias cross-turno."""
    alertas = []

    try:
        from .capa2_contrato import calcular_contabilidad
        from .capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
        from .modelos import ResolucionC3

        # canonicalizar ya se hizo en nivel 4, pero por seguridad
        cont = calcular_contabilidad(datos_dia)
        c3 = clasificar(datos_dia, cont)

        for nombre, sc3 in c3.sabores.items():
            if not sc3.prototipo:
                continue

            # El pipeline detectó algo y lo corrigió o escaló
            proto = sc3.prototipo
            if sc3.resolution_status == ResolucionC3.ESCALAR_C4:
                alertas.append({
                    'nivel': 'cross',
                    'severidad': 'warning',
                    'sabor': nombre,
                    'codigo': f'H0_{proto.codigo}',
                    'detalle': f'Anomalia detectada pero sin correccion confiable: {proto.descripcion[:80]}',
                })
            else:
                alertas.append({
                    'nivel': 'cross',
                    'severidad': 'info',
                    'sabor': nombre,
                    'codigo': proto.codigo,
                    'detalle': f'Corregido: {proto.descripcion[:80]} (confianza {proto.confianza:.0%})',
                })

    except Exception as e:
        alertas.append({
            'nivel': 'cross',
            'severidad': 'info',
            'sabor': None,
            'codigo': 'CROSS_ERROR',
            'detalle': f'Error en analisis cross-turno: {str(e)[:100]}',
        })

    return alertas
