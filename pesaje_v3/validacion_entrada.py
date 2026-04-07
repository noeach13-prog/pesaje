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


def analizar_turno(db: sqlite3.Connection, turno_id: int, profundo: bool = False) -> Dict:
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

    # ── Intentar pipeline batch (analizar_mes) para paridad con reporte ──
    from datetime import date as date_cls
    fecha = turno['fecha']
    mes = fecha[:7]  # 'YYYY-MM'
    dia_label = str(date_cls.fromisoformat(fecha).day)

    # Contar turnos del mes para decidir si vale la pena batch
    n_turnos_mes = db.execute(
        "SELECT COUNT(*) as n FROM turnos WHERE sucursal_id=? AND fecha LIKE ?",
        (turno['sucursal_id'], f"{mes}%"),
    ).fetchone()['n']

    if n_turnos_mes >= 4:  # Al menos 2 días de datos → batch vale la pena
        try:
            res_mes = analizar_mes(db, turno['sucursal_id'], mes)
            if dia_label in res_mes and res_mes[dia_label].get('tiene_analisis'):
                res_dia = res_mes[dia_label]
                # Combinar alertas de nivel 3 con las del pipeline batch
                res_dia['alertas'] = resultado['alertas'] + res_dia.get('alertas', [])
                res_dia['n_errores'] = sum(1 for a in res_dia['alertas'] if a['severidad'] == 'error')
                res_dia['n_warnings'] = sum(1 for a in res_dia['alertas'] if a['severidad'] == 'warning')

                # C5 profundo si se pidió
                if profundo and turno['estado'] == 'confirmado':
                    res_dia = _agregar_c5_profundo(db, turno, res_dia)

                return res_dia
        except Exception:
            pass  # Fallback al pipeline individual

    # ── Fallback: pipeline individual (armar_datos_dia) ──
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

        # C5: segunda pasada — solo si el supervisor lo pide explicitamente
        # C5: segunda pasada — senales residuales de calidad
        # C5 no modifica ventas. Agrega senales (R1, R2, etc.) que
        # indican patrones sospechosos no resueltos por C3/C4.
        c5_senales = {}
        if profundo and turno['estado'] == 'confirmado':
            try:
                from .capa5_residual import segunda_pasada
                c5 = segunda_pasada(datos_dia, c3, c4.correcciones, stats={})
                if hasattr(c5, 'sabores'):
                    for nn, c5_sab in c5.sabores.items():
                        if c5_sab.senales:
                            c5_senales[nn] = [
                                {'tipo': s.tipo, 'subtipo': s.subtipo, 'detalle': s.detalle}
                                for s in c5_sab.senales
                            ]
            except Exception as e:
                resultado['alertas'].append({
                    'nivel': 'analisis', 'severidad': 'info', 'sabor': None,
                    'codigo': 'C5_ERROR', 'detalle': f'Error en C5: {str(e)[:80]}',
                })

        c4_correcciones_final = c4.correcciones

        resultado['tiene_analisis'] = True
        resultado['profundo'] = profundo and turno['estado'] == 'confirmado'
        resultado['c5_senales'] = c5_senales

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
            c4_corr = next((c for c in c4_correcciones_final if c.nombre_norm == nombre), None)
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

            # Senales C5 si se ejecuto analisis profundo
            if nombre in c5_senales:
                sabor_info['c5_senales'] = c5_senales[nombre]
            # Explicación clara para verificación humana
            d = datos_dia.turno_dia.sabores.get(nombre)
            n = datos_dia.turno_noche.sabores.get(nombre)
            if status != 'OK':
                sabor_info['explicacion'] = _explicar_caso(
                    nombre, sc, d, n, proto, c4_corr, False,
                    0, vf, status,
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


# Cache de analizar_mes: evita correr el pipeline completo multiples veces
# para el mismo mes cuando el supervisor revisa varios turnos seguidos.
# Se invalida cuando cambia el ultimo turno modificado del mes.
_cache_mes = {}  # (sucursal_id, mes) → {'ts': max_updated, 'data': resultado}


def _cache_key_ts(db, sucursal_id, mes):
    """Timestamp del ultimo cambio en turnos del mes (para invalidación)."""
    row = db.execute(
        """SELECT MAX(COALESCE(fin_carga, inicio_carga, created_at)) as ts
           FROM turnos WHERE sucursal_id=? AND fecha LIKE ?""",
        (sucursal_id, f"{mes}%"),
    ).fetchone()
    return row['ts'] if row else None


def invalidar_cache_mes(sucursal_id: int = None, mes: str = None):
    """Invalida cache manualmente (ej: después de guardar/confirmar turno)."""
    if sucursal_id and mes:
        _cache_mes.pop((sucursal_id, mes), None)
    elif sucursal_id:
        keys = [k for k in _cache_mes if k[0] == sucursal_id]
        for k in keys:
            del _cache_mes[k]
    else:
        _cache_mes.clear()


def analizar_mes(db: sqlite3.Connection, sucursal_id: int, mes: str) -> Dict:
    """Corre el pipeline completo sobre TODOS los turnos del mes.

    Replica EXACTAMENTE web.py:_procesar() pero leyendo de la DB.
    Retorna dict {dia_label: resultado_analisis} donde cada resultado
    tiene la misma estructura que analizar_turno().

    Usa cache por (sucursal_id, mes) invalidado por timestamp de
    ultimo turno modificado. Evita corridas redundantes (~170s cada una)
    cuando el supervisor revisa varios turnos del mismo mes.

    Args:
        db: conexión SQLite
        sucursal_id: id de la sucursal
        mes: formato 'YYYY-MM' (ej: '2026-02')
    """
    # Cache check
    cache_key = (sucursal_id, mes)
    ts = _cache_key_ts(db, sucursal_id, mes)
    if cache_key in _cache_mes and _cache_mes[cache_key]['ts'] == ts:
        return _cache_mes[cache_key]['data']

    from .db_to_pipeline import cargar_todos_los_dias_db
    from .capa2_contrato import calcular_contabilidad
    from .capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
    from .capa4_expediente import resolver_escalados
    from .modelos import ResolucionC3

    dias = cargar_todos_los_dias_db(db, sucursal_id, mes)
    if not dias:
        return {}

    resultados = {}
    for datos in sorted(dias, key=lambda d: int(d.dia_label) if d.dia_label.isdigit() else 0):
        try:
            canon = canonicalizar_nombres(datos)
            aplicar_canonicalizacion(datos, canon)
            cont = calcular_contabilidad(datos)
            c3 = clasificar(datos, cont)
            c4 = resolver_escalados(datos, cont, c3)

            # Armar resultado con misma estructura que analizar_turno
            resultado = {
                'ok': True,
                'alertas': [],
                'sabores': [],
                'totales': {},
                'tiene_analisis': True,
                'profundo': False,
                'c5_senales': {},
            }

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

                d = datos.turno_dia.sabores.get(nombre)
                n = datos.turno_noche.sabores.get(nombre)
                if status != 'OK':
                    sabor_info['explicacion'] = _explicar_caso(
                        nombre, sc, d, n, proto, c4_corr, False,
                        0, vf, status,
                    )

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

            resultado['n_errores'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'error')
            resultado['n_warnings'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'warning')

            resultados[datos.dia_label] = resultado

        except Exception as e:
            resultados[datos.dia_label] = {
                'ok': False,
                'error': f'Error en pipeline D{datos.dia_label}: {str(e)[:120]}',
                'alertas': [],
                'sabores': [],
                'totales': {},
                'tiene_analisis': False,
            }

    # Store in cache
    _cache_mes[cache_key] = {'ts': ts, 'data': resultados}

    return resultados


def _calcular_stats_mes(db, sucursal_id, mes):
    """Calcula estadísticas históricas del mes para C5 (R1 y R3).

    Retorna (stats, media_dia, std_dia) donde:
    - stats: Dict[nombre_norm, EstadisticaSabor] con media/std por sabor
    - media_dia: promedio de venta total diaria del mes
    - std_dia: desvío estándar de venta total diaria
    """
    from .capa5_residual import calcular_estadisticas
    import math

    res_mes = analizar_mes(db, sucursal_id, mes)
    if not res_mes:
        return {}, 0, 0

    # Recoger ventas finales por sabor y totales por día
    ventas_por_sabor = {}  # nombre → [venta_d1, venta_d2, ...]
    totales_dia = []

    for dia_label, r in res_mes.items():
        if not r.get('tiene_analisis'):
            continue
        total_dia = 0
        for s in r.get('sabores', []):
            nombre = s['nombre']
            vf = s['final']
            if nombre not in ventas_por_sabor:
                ventas_por_sabor[nombre] = []
            ventas_por_sabor[nombre].append(vf)
            total_dia += vf
        totales_dia.append(total_dia)

    stats = calcular_estadisticas(ventas_por_sabor)

    # Media y std del total diario
    media_dia = sum(totales_dia) / len(totales_dia) if totales_dia else 0
    if len(totales_dia) >= 2:
        var = sum((t - media_dia) ** 2 for t in totales_dia) / (len(totales_dia) - 1)
        std_dia = math.sqrt(var) if var > 0 else 0
    else:
        std_dia = 0

    return stats, media_dia, std_dia


def _agregar_c5_profundo(db, turno, resultado):
    """Agrega señales C5 a un resultado ya calculado.
    Usa stats del mes completo para R1 (desvío histórico) y R3 (día anómalo)."""
    try:
        from .capa5_residual import segunda_pasada
        datos_dia = armar_datos_dia(db, turno['sucursal_id'], turno['fecha'])
        if not datos_dia:
            return resultado

        from .capa2_contrato import calcular_contabilidad
        from .capa3_motor import clasificar, canonicalizar_nombres, aplicar_canonicalizacion
        from .capa4_expediente import resolver_escalados

        canon = canonicalizar_nombres(datos_dia)
        aplicar_canonicalizacion(datos_dia, canon)
        cont = calcular_contabilidad(datos_dia)
        c3 = clasificar(datos_dia, cont)
        c4 = resolver_escalados(datos_dia, cont, c3)

        # Calcular stats del mes para R1 y R3
        mes = turno['fecha'][:7]
        stats, media_dia, std_dia = _calcular_stats_mes(db, turno['sucursal_id'], mes)

        c5 = segunda_pasada(datos_dia, c3, c4.correcciones, stats=stats,
                            media_dia=media_dia, std_dia=std_dia)

        c5_senales = {}
        if hasattr(c5, 'sabores'):
            for nn, c5_sab in c5.sabores.items():
                if c5_sab.senales:
                    c5_senales[nn] = [
                        {'tipo': s.tipo, 'subtipo': s.subtipo, 'detalle': s.detalle}
                        for s in c5_sab.senales
                    ]

        # Señales a nivel día (R3)
        c5_dia = []
        if hasattr(c5, 'senales_dia') and c5.senales_dia:
            c5_dia = [
                {'tipo': s.tipo, 'subtipo': s.subtipo, 'detalle': s.detalle}
                for s in c5.senales_dia
            ]

        resultado['profundo'] = True
        resultado['c5_senales'] = c5_senales
        resultado['c5_senales_dia'] = c5_dia
        for sab in resultado.get('sabores', []):
            if sab['nombre'] in c5_senales:
                sab['c5_senales'] = c5_senales[sab['nombre']]
    except Exception as e:
        resultado['alertas'].append({
            'nivel': 'analisis', 'severidad': 'info', 'sabor': None,
            'codigo': 'C5_ERROR', 'detalle': f'Error en C5: {str(e)[:80]}',
        })

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
    Estructura: DATOS → QUE PASO → QUE SE HIZO → QUE VERIFICAR
    """
    ab_d = (d.abierta or 0) if d else 0
    ab_n = (n.abierta or 0) if n else 0
    cerr_d = [int(c) for c in d.cerradas] if d else []
    cerr_n = [int(c) for c in n.cerradas] if n else []
    ent_d = [int(e) for e in d.entrantes] if d else []
    ent_n = [int(e) for e in n.entrantes] if n else []

    # ── DATOS: que cargaron los empleados ──
    L = [f'--- {nombre} ---']
    L.append('')
    L.append('DATOS CARGADOS:')
    # Turno anterior
    partes_ant = [f'Abierta {ab_d}g']
    if cerr_d:
        partes_ant.append(f'Cerradas: {", ".join(str(c)+"g" for c in cerr_d)}')
    if ent_d:
        partes_ant.append(f'Entrantes: {", ".join(str(e)+"g" for e in ent_d)}')
    total_d = ab_d + sum(cerr_d) + sum(ent_d)
    L.append(f'  Turno anterior: {" | ".join(partes_ant)} = {total_d}g total')

    # Turno actual
    partes_act = [f'Abierta {ab_n}g']
    if cerr_n:
        partes_act.append(f'Cerradas: {", ".join(str(c)+"g" for c in cerr_n)}')
    if ent_n:
        partes_act.append(f'Entrantes: {", ".join(str(e)+"g" for e in ent_n)}')
    total_n = ab_n + sum(cerr_n) + sum(ent_n)
    L.append(f'  Turno actual:   {" | ".join(partes_act)} = {total_n}g total')
    L.append(f'  Venta calculada: {total_d}g - {total_n}g = {sc.venta_raw}g')

    if web_corr and dup_peso:
        L.append('')
        L.append('QUE PASO:')
        L.append(f'  El entrante de {dup_peso}g pesa igual que una cerrada del mismo turno.')
        L.append(f'  Esto pasa cuando anotan la misma lata dos veces: una como cerrada y otra como entrante.')
        L.append('')
        L.append('QUE SE HIZO:')
        L.append(f'  Se desconto {dup_peso}g del calculo (el peso duplicado).')
        L.append(f'  Venta corregida: {vf}g')
        L.append('')
        L.append('QUE VERIFICAR:')
        L.append(f'  Preguntar al empleado si realmente llego un entrante nuevo de {dup_peso}g o si lo copio de las cerradas.')

    elif proto:
        codigo = proto.codigo
        L.append('')
        L.append('QUE PASO:')

        if codigo == 'PF1':
            L.append(f'  Una cerrada tiene un peso raro que no coincide con los demas turnos.')
            L.append(f'  Parece que se equivocaron al escribir el numero (ej: pusieron 5705 en vez de 6705).')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Se reemplazo por el peso que aparece en otros turnos cercanos.')
            L.append(f'  Diferencia aplicada: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')
            L.append('')
            L.append('QUE VERIFICAR:')
            L.append(f'  Mirar la cerrada en cuestion y comparar con los 2-3 turnos anteriores.')
            L.append(f'  Si el peso siempre fue similar y solo este turno cambio, la correccion es correcta.')

        elif 'PFIT' in codigo:
            n_dup = abs(proto.delta) // max(1, max(cerr_d) if cerr_d else 6500)
            L.append(f'  Hay entrantes que pesan casi igual que cerradas en el mismo turno.')
            L.append(f'  Esto pasa cuando copian los pesos de las cerradas como si fueran entrantes nuevos.')
            L.append(f'  Es un doble registro: la misma lata aparece como cerrada Y como entrante.')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Se sacaron los entrantes duplicados del calculo.')
            L.append(f'  Diferencia aplicada: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')
            L.append('')
            L.append('QUE VERIFICAR:')
            L.append(f'  Ver si ese dia realmente llegaron latas nuevas o si el empleado las copio de las cerradas.')

        elif codigo == 'PF4':
            cerr_faltante = [c for c in cerr_d if not any(abs(c - cn) <= 200 for cn in cerr_n)]
            L.append(f'  Una cerrada del turno anterior ({cerr_faltante[0]}g) no aparece en el turno actual.' if cerr_faltante else f'  Una cerrada del turno anterior desaparecio.')
            L.append(f'  No se abrio (la abierta no subio) y no se anoto como vendida.')
            L.append(f'  Lo mas probable es que se olvidaron de anotarla.')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Se agrego la cerrada faltante al stock actual para el calculo.')
            L.append(f'  Diferencia aplicada: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')
            L.append('')
            L.append('QUE VERIFICAR:')
            L.append(f'  Buscar la lata en la heladera. Si sigue ahi, la correccion es correcta.')
            L.append(f'  Si no esta, puede que se haya abierto sin registrar.')

        elif codigo == 'PF5':
            cerr_nueva = [c for c in cerr_n if not any(abs(c - cd) <= 200 for cd in cerr_d)]
            L.append(f'  Aparecio una cerrada nueva ({cerr_nueva[0]}g) que no estaba en el turno anterior.' if cerr_nueva else f'  Aparecio una cerrada nueva que no estaba antes.')
            L.append(f'  No hay entrante registrado que la explique.')
            L.append(f'  Probablemente ya estaba pero no la anotaron en el turno anterior.')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Se considero que la cerrada ya existia y se ajusto el calculo.')
            L.append(f'  Diferencia aplicada: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')
            L.append('')
            L.append('QUE VERIFICAR:')
            L.append(f'  Confirmar si la lata llego como entrante y no se anoto, o si ya estaba desde antes.')

        elif codigo == 'PF7':
            ab_diff = ab_n - ab_d
            L.append(f'  La abierta paso de {ab_d}g a {ab_n}g (cambio de {ab_diff:+d}g).')
            if ab_diff > 0:
                L.append(f'  Subio {ab_diff}g sin que se abra una cerrada nueva. Eso es imposible fisicamente.')
                L.append(f'  Probablemente pesaron mal la batea o la cambiaron sin anotar.')
            else:
                L.append(f'  Bajo mucho mas de lo normal. Comparando con otros turnos, el valor no tiene sentido.')
                L.append(f'  Puede ser un error de pesaje o que se cambio la batea.')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Se uso como referencia el peso de la abierta en otros turnos cercanos.')
            L.append(f'  Diferencia aplicada: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')
            L.append('')
            L.append('QUE VERIFICAR:')
            L.append(f'  Preguntar al empleado si peso bien la batea abierta o si la cambio.')
            L.append(f'  Comparar con la abierta de los turnos anterior y siguiente.')

        else:
            L.append(f'  Se detecto un patron inusual en los datos.')
            if proto.descripcion:
                L.append(f'  Detalle: {proto.descripcion}')
            L.append('')
            L.append('QUE SE HIZO:')
            L.append(f'  Correccion automatica: {proto.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g')

    elif c4_corr:
        L.append('')
        L.append('QUE PASO:')
        L.append(f'  Se detecto una combinacion de problemas que requirio analisis cruzado con otros turnos.')
        if c4_corr.motivo:
            L.append(f'  Detalle: {c4_corr.motivo}')
        L.append('')
        L.append('QUE SE HIZO:')
        L.append(f'  Se analizo el historial de este sabor en turnos cercanos para encontrar la causa.')
        L.append(f'  Diferencia aplicada: {c4_corr.delta:+d}g')
        L.append(f'  Venta corregida: {vf}g')
        if c4_corr.confianza:
            nivel = 'alta' if c4_corr.confianza >= 0.85 else ('media' if c4_corr.confianza >= 0.70 else 'baja')
            L.append(f'  Confianza de la correccion: {nivel} ({int(c4_corr.confianza*100)}%)')
        L.append('')
        L.append('QUE VERIFICAR:')
        L.append(f'  Comparar las cerradas de este sabor con los 2-3 turnos anteriores y siguientes.')
        L.append(f'  Si un peso aparece en muchos turnos y solo falta en este, la correccion es correcta.')

    elif status == 'H0':
        L.append('')
        L.append('QUE PASO:')
        L.append(f'  El sistema detecto algo raro pero no tiene suficiente informacion para corregirlo solo.')

        if sc.venta_raw < -200:
            L.append(f'  La venta da negativa ({sc.venta_raw}g): hay MAS stock ahora que antes.')
            L.append(f'  Eso es imposible salvo que haya llegado stock nuevo que no se registro.')
            L.append('')
            L.append('POSIBLES CAUSAS:')
            L.append(f'  1. Llego una lata nueva (entrante) y no se anoto')
            L.append(f'  2. La abierta del turno anterior estaba mal pesada')
            L.append(f'  3. Se olvido de anotar una cerrada en el turno anterior')
        elif sc.venta_raw > 8000:
            L.append(f'  La venta es muy alta ({sc.venta_raw}g): se vendio casi una lata entera o mas.')
            L.append('')
            L.append('POSIBLES CAUSAS:')
            L.append(f'  1. Un entrante se anoto dos veces (como entrante y como cerrada)')
            L.append(f'  2. Una cerrada desaparecio sin abrirse (se llevo o se anoto mal)')
            L.append(f'  3. La abierta del turno actual tiene un peso demasiado bajo')
        else:
            cerr_desaparecidas = [c for c in cerr_d if not any(abs(c - cn) <= 200 for cn in cerr_n)]
            cerr_nuevas = [c for c in cerr_n if not any(abs(c - cd) <= 200 for cd in cerr_d)]
            if cerr_desaparecidas or cerr_nuevas:
                L.append('')
                L.append('DETALLE DE CERRADAS:')
            if cerr_desaparecidas:
                for c in cerr_desaparecidas:
                    L.append(f'  - Cerrada de {c}g estaba antes y ahora NO esta.')
                    L.append(f'    Si se abrio, la abierta deberia haber subido. Si no, falta anotarla.')
            if cerr_nuevas:
                for c in cerr_nuevas:
                    L.append(f'  - Cerrada de {c}g aparecio ahora y antes NO estaba.')
                    L.append(f'    Si llego nueva, deberia figurar como entrante. Si no, verificar.')

        L.append('')
        L.append('QUE VERIFICAR:')
        L.append(f'  Revisar con el empleado los pesos de {nombre} en este turno.')
        L.append(f'  Comparar con los 2-3 turnos anteriores para ver que cambio.')

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
