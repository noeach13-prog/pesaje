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
        tipo = turno['tipo_turno']
        fecha = turno['fecha']
        # Verificar si hay turno anterior en la DB
        hay_anterior = db.execute(
            "SELECT 1 FROM turnos WHERE sucursal_id=? AND fecha<? LIMIT 1",
            (turno['sucursal_id'], fecha),
        ).fetchone()
        if not hay_anterior:
            msg = f'Para ver el analisis del {fecha}, necesitas tener cargado al menos un turno de un dia anterior como referencia.'
        else:
            msg = f'No se pudo armar el analisis del {fecha}. Verificar que los turnos tengan sabores cargados.'
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

        # Detectar INTRADUP no corregidos por el pipeline
        # Chequea AMBOS turnos (DIA y NOCHE) porque el doble registro
        # puede estar en el turno de referencia (DIA), no en el analizado.
        intradup_por_sabor = {}
        from .constantes_c3 import PFIT_TOL_INTRA
        for turno_crudo in [datos_dia.turno_dia, datos_dia.turno_noche]:
            for nombre, sab in turno_crudo.sabores.items():
                if not sab.entrantes or not sab.cerradas:
                    continue
                dup_pesos = []
                for e in sab.entrantes:
                    for c in sab.cerradas:
                        if abs(int(e) - int(c)) <= PFIT_TOL_INTRA:
                            dup_pesos.append(int(e))
                            break
                if dup_pesos and nombre not in intradup_por_sabor:
                    intradup_por_sabor[nombre] = sum(dup_pesos)

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

            # Corrección web: INTRADUP detectado en nivel 3 pero no corregido por pipeline
            web_corr = False
            if not proto and not c4_corr and nombre in intradup_por_sabor:
                dup_peso = intradup_por_sabor[nombre]
                vf = sc.venta_raw - dup_peso
                delta = -dup_peso
                web_corr = True

            if res and res == ResolucionC3.ESCALAR_C4:
                status = 'H0'
                n_h0 += 1
            elif proto or c4_corr or web_corr:
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
            elif web_corr:
                sabor_info['correccion'] = f'Doble registro: entrante duplica cerrada ({intradup_por_sabor[nombre]}g descontado)'
                sabor_info['confianza'] = 0.70

            # Explicación clara para verificación humana
            d = datos_dia.turno_dia.sabores.get(nombre)
            n = datos_dia.turno_noche.sabores.get(nombre)
            if status != 'OK':
                sabor_info['explicacion'] = _explicar_caso(
                    nombre, sc, d, n, proto, c4_corr, web_corr,
                    intradup_por_sabor.get(nombre, 0), vf, status,
                )

            # Alerta si hay problema
            if vf < -200:
                resultado['alertas'].append({
                    'nivel': 'analisis', 'severidad': 'error', 'sabor': nombre,
                    'codigo': 'VENTA_NEG',
                    'detalle': f'{nombre}: la venta da {vf}g (negativa). Revisar si faltan cerradas o si la abierta esta mal.',
                })
            elif status == 'H0':
                resultado['alertas'].append({
                    'nivel': 'analisis', 'severidad': 'warning', 'sabor': nombre,
                    'codigo': 'H0',
                    'detalle': sabor_info.get('explicacion', f'{nombre}: no se pudo corregir automaticamente.'),
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


def _explicar_caso(nombre, sc, d, n, proto, c4_corr, web_corr, dup_peso, vf, status):
    """
    Genera explicacion en espanol claro para verificacion humana.
    Sin jerga tecnica. Dice que se encontro, que datos mirar, y que se hizo.
    """
    ab_d = d.abierta if d else 0
    ab_n = n.abierta if n else 0
    cerr_d = [int(c) for c in d.cerradas] if d else []
    cerr_n = [int(c) for c in n.cerradas] if n else []
    ent_d = [int(e) for e in d.entrantes] if d else []

    L = [f'{nombre}:']
    L.append(f'Turno anterior: abierta {ab_d}g, cerradas {cerr_d or "ninguna"}, entrantes {ent_d or "ninguno"}')
    L.append(f'Turno actual: abierta {ab_n}g, cerradas {cerr_n or "ninguna"}')
    L.append(f'Venta sin corregir: {sc.venta_raw}g')

    if web_corr and dup_peso:
        L.append('')
        L.append(f'PROBLEMA: En el turno anterior, el entrante ({dup_peso}g) tiene el mismo peso que una cerrada.')
        L.append(f'Eso significa que la misma lata se anoto dos veces: una como cerrada y otra como entrante.')
        L.append(f'CORRECCION: Se desconto {dup_peso}g del calculo porque es el peso duplicado.')
        L.append(f'Venta corregida: {vf}g')
        L.append('')
        L.append(f'VERIFICAR: Fijarse si en el turno anterior habia realmente un entrante nuevo o si fue error de carga.')

    elif proto:
        codigo = proto.codigo
        if codigo == 'PF1':
            L.append('')
            L.append(f'PROBLEMA: Una cerrada tiene un peso que no aparece en otros turnos.')
            L.append(f'Parece un error al escribir el numero (error de digito).')
            L.append(f'CORRECCION: Se ajusto el peso al valor que aparece en los demas turnos.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')
            L.append('')
            L.append(f'VERIFICAR: Revisar la cerrada marcada y compararla con los turnos anteriores y siguientes.')

        elif 'PFIT' in codigo:
            L.append('')
            L.append(f'PROBLEMA: En el turno anterior hay entrantes que pesan igual que cerradas del mismo turno.')
            L.append(f'Es probable que la misma lata se haya anotado dos veces.')
            L.append(f'CORRECCION: Se descontaron los entrantes duplicados del calculo.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')
            L.append('')
            L.append(f'VERIFICAR: Fijarse si los entrantes eran latas nuevas reales o si se copiaron de las cerradas.')

        elif codigo == 'PF4':
            L.append('')
            L.append(f'PROBLEMA: Una cerrada del turno anterior no aparece en el turno actual.')
            L.append(f'Si no se abrio ni se vendio, puede ser que se olvido de anotarla.')
            L.append(f'CORRECCION: Se agrego la cerrada faltante al calculo.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')
            L.append('')
            L.append(f'VERIFICAR: Buscar la lata en la heladera. Si sigue ahi, la correccion es correcta.')

        elif codigo == 'PF5':
            L.append('')
            L.append(f'PROBLEMA: Una cerrada aparece en el turno actual pero no estaba en el anterior.')
            L.append(f'Puede ser que se olvido de anotarla antes.')
            L.append(f'CORRECCION: Se ajusto el calculo considerando que la cerrada ya estaba.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')

        elif codigo == 'PF7':
            L.append('')
            L.append(f'PROBLEMA: La abierta cambio de una forma que no se explica con las cerradas.')
            ab_diff = ab_n - ab_d
            L.append(f'La abierta paso de {ab_d}g a {ab_n}g ({ab_diff:+d}g).')
            if ab_diff > 0:
                L.append(f'Subio sin que se haya abierto una cerrada nueva.')
            else:
                L.append(f'El valor parece incorrecto comparado con turnos cercanos.')
            L.append(f'CORRECCION: Se uso un valor de referencia de otros turnos.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')
            L.append('')
            L.append(f'VERIFICAR: Revisar si la abierta se peso bien o si se cambio de batea sin anotar.')

        else:
            L.append('')
            L.append(f'Se detecto una anomalia y se corrigio automaticamente.')
            L.append(f'Venta corregida: {vf}g (diferencia: {proto.delta:+d}g)')

    elif c4_corr:
        L.append('')
        L.append(f'Se detecto una anomalia que requirio analisis avanzado.')
        L.append(f'Venta corregida: {vf}g (diferencia: {c4_corr.delta:+d}g)')
        L.append('')
        L.append(f'VERIFICAR: Comparar los pesos de las cerradas con los turnos anteriores y siguientes.')

    elif status == 'H0':
        L.append('')
        L.append(f'PROBLEMA: El sistema detecto algo inusual pero no pudo corregirlo automaticamente.')
        if sc.venta_raw < -200:
            L.append(f'La venta da negativa ({sc.venta_raw}g): aparecio mas stock del que habia.')
            L.append(f'Posibles causas: entrante no registrado, error en abierta, o cerrada que falto anotar antes.')
        elif sc.venta_raw > 8000:
            L.append(f'La venta es muy alta ({sc.venta_raw}g). Posible entrante duplicado o cerrada que desaparecio sin abrirse.')
        else:
            cerr_desaparecidas = [c for c in cerr_d if not any(abs(c - cn) <= 200 for cn in cerr_n)]
            cerr_nuevas = [c for c in cerr_n if not any(abs(c - cd) <= 200 for cd in cerr_d)]
            if cerr_desaparecidas:
                L.append(f'Cerradas que estaban antes y ahora no estan: {cerr_desaparecidas}')
                L.append(f'Si se abrieron, deberia verse en la abierta. Si no, falta anotarlas.')
            if cerr_nuevas:
                L.append(f'Cerradas nuevas que aparecieron: {cerr_nuevas}')
                L.append(f'Si son latas que llegaron, deberian estar como entrantes.')
        L.append('')
        L.append(f'VERIFICAR: Revisar los pesos de este sabor en los turnos cercanos y confirmar si hay un error de carga.')

    return '\n'.join(L)


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
