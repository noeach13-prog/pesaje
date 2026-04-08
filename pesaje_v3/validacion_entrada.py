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
from .capa5_residual import _timeline_sabor


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

                # Ajustes manuales del supervisor
                _aplicar_ajustes_manuales(db, turno_id, res_dia)

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

            # Venta negativa es fisicamente imposible.
            # Diagnosticar causa y estimar si hay datos suficientes.
            motivo_cero = None
            if vf < 0:
                d_sab = datos_dia.turno_dia.sabores.get(nombre)
                n_sab = datos_dia.turno_noche.sabores.get(nombre)
                ab_d = (d_sab.abierta or 0) if d_sab else 0
                ab_n = (n_sab.abierta or 0) if n_sab else 0
                cerr_d = [int(c) for c in d_sab.cerradas] if d_sab else []
                cerr_n = [int(c) for c in n_sab.cerradas] if n_sab else []
                rise = ab_n - ab_d
                tiene_datos_dia = d_sab and (ab_d > 0 or cerr_d)

                if rise > 4000:
                    vf = max(0, ab_d)
                    if ab_d > 0:
                        motivo_cero = f'Se abrio una lata no registrada (abierta subio {rise}g). Venta estimada en {vf}g (lo que habia de abierta).'
                    else:
                        motivo_cero = f'Se abrio una lata no registrada (abierta subio {rise}g). No habia abierta previa, no se puede calcular cuanto se vendio.'
                elif not tiene_datos_dia:
                    vf = 0
                    motivo_cero = f'El sabor no fue registrado en el turno anterior. Sin dato de stock inicial, no se puede calcular la venta. Verificar con el empleado si olvido anotarlo.'
                elif rise > 0 and rise <= 4000 and any(abs(cd - cn) <= 200 for cd in cerr_d for cn in cerr_n):
                    vf = 0
                    motivo_cero = f'La abierta subio {rise}g (se abrio una cerrada). La venta da negativa por varianza de pesaje en las cerradas ({sc.venta_raw}g). Marcar como venta no calculable.'
                else:
                    vf = 0
                    motivo_cero = f'La venta da {sc.venta_raw}g (negativa). Probablemente falto registrar un entrante o hay un error en los pesos. Verificar los datos con el empleado.'

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
                sabor_info['correccion'] = _resumen_correccion(c4_corr)
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
            # Historial para TODOS (OK lo muestra expandible, no-OK lo tiene en explicacion)
            sabor_info['historial'] = _timeline_sabor(nombre, datos_dia)

            # Agregar motivo del clamp a 0 si aplica
            if motivo_cero:
                exp_base = sabor_info.get('explicacion', '')
                sabor_info['explicacion'] = (exp_base + '\n\n' + motivo_cero).strip() if exp_base else motivo_cero
                if status == 'OK':
                    # Era OK pero quedó en 0 → marcar como H0
                    sabor_info['status'] = 'H0'
                    status = 'H0'
                    n_h0 += 1

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

    # Ajustes manuales del supervisor
    _aplicar_ajustes_manuales(db, turno_id, resultado)

    # Conteo de alertas
    resultado['n_errores'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'error')
    resultado['n_warnings'] = sum(1 for a in resultado['alertas'] if a['severidad'] == 'warning')

    return resultado


def _aplicar_ajustes_manuales(db, turno_id, resultado):
    """Aplica ajustes manuales del supervisor sobre el resultado del pipeline.

    No destruye el pipeline: preserva final_pipeline y agrega datos del ajuste.
    Recalcula totales con los valores manuales.
    """
    ajustes = db.execute(
        "SELECT * FROM ajustes_manuales WHERE turno_id = ?", (turno_id,)
    ).fetchall()

    if not ajustes:
        return

    ajustes_map = {a['nombre_norm']: a for a in ajustes}
    delta_total = 0

    for sabor_info in resultado.get('sabores', []):
        nombre = sabor_info['nombre']
        if nombre not in ajustes_map:
            continue

        ajuste = ajustes_map[nombre]

        # Preservar valor pipeline
        sabor_info['final_pipeline'] = sabor_info['final']
        sabor_info['status_pipeline'] = sabor_info['status']

        # Aplicar override
        delta_total += ajuste['venta_manual'] - sabor_info['final']
        sabor_info['final'] = ajuste['venta_manual']
        sabor_info['status'] = 'MANUAL'
        sabor_info['ajuste'] = {
            'pipeline': ajuste['venta_pipeline'],
            'status_original': ajuste['status_pipeline'],
            'manual': ajuste['venta_manual'],
            'motivo': ajuste['motivo'],
            'categoria': ajuste['categoria'],
            'supervisor': ajuste['supervisor'] or '',
            'fecha': ajuste['updated_at'],
        }

    # Recalcular totales
    if delta_total != 0 and 'totales' in resultado:
        resultado['totales']['venta'] += delta_total
        resultado['totales']['neto'] += delta_total


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

                motivo_cero = None
                if vf < 0:
                    d_sab = datos.turno_dia.sabores.get(nombre)
                    n_sab = datos.turno_noche.sabores.get(nombre)
                    ab_d = (d_sab.abierta or 0) if d_sab else 0
                    ab_n = (n_sab.abierta or 0) if n_sab else 0
                    cerr_d = [int(c) for c in d_sab.cerradas] if d_sab else []
                    cerr_n = [int(c) for c in n_sab.cerradas] if n_sab else []
                    rise = ab_n - ab_d
                    tiene_datos_dia = d_sab and (ab_d > 0 or cerr_d)

                    if rise > 4000:
                        vf = max(0, ab_d)
                        if ab_d > 0:
                            motivo_cero = f'Se abrio una lata no registrada (abierta subio {rise}g). Venta estimada en {vf}g.'
                        else:
                            motivo_cero = f'Se abrio una lata no registrada (abierta subio {rise}g). No habia abierta previa, no se puede calcular.'
                    elif not tiene_datos_dia:
                        vf = 0
                        motivo_cero = f'El sabor no fue registrado en el turno anterior. Sin dato de stock inicial, no se puede calcular la venta.'
                    elif rise > 0 and rise <= 4000 and any(abs(cd - cn) <= 200 for cd in cerr_d for cn in cerr_n):
                        vf = 0
                        motivo_cero = f'La abierta subio {rise}g (se abrio una cerrada). Venta negativa por varianza de pesaje ({sc.venta_raw}g).'
                    else:
                        vf = 0
                        motivo_cero = f'La venta da {sc.venta_raw}g (negativa). Probablemente falto registrar un entrante o hay un error en los pesos.'

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
                    sabor_info['correccion'] = _resumen_correccion(c4_corr)
                    sabor_info['confianza'] = c4_corr.confianza

                d = datos.turno_dia.sabores.get(nombre)
                n = datos.turno_noche.sabores.get(nombre)
                if status != 'OK':
                    sabor_info['explicacion'] = _explicar_caso(
                        nombre, sc, d, n, proto, c4_corr, False,
                        0, vf, status,
                    )
                sabor_info['historial'] = _timeline_sabor(nombre, datos)

                if motivo_cero:
                    exp_base = sabor_info.get('explicacion', '')
                    sabor_info['explicacion'] = (exp_base + '\n\n' + motivo_cero).strip() if exp_base else motivo_cero
                    if status == 'OK':
                        sabor_info['status'] = 'H0'
                        status = 'H0'
                        n_h0 += 1

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
        c5_explicaciones = {}
        if hasattr(c5, 'sabores'):
            for nn, c5_sab in c5.sabores.items():
                if c5_sab.senales:
                    c5_senales[nn] = [
                        {'tipo': s.tipo, 'subtipo': s.subtipo, 'detalle': s.detalle}
                        for s in c5_sab.senales
                    ]
                if c5_sab.explicacion:
                    c5_explicaciones[nn] = c5_sab.explicacion

        # Señales a nivel día (R3)
        c5_dia = []
        if hasattr(c5, 'senales_dia') and c5.senales_dia:
            c5_dia = [
                {'tipo': s.tipo, 'subtipo': s.subtipo, 'detalle': s.detalle}
                for s in c5.senales_dia
            ]

        resultado['profundo'] = True
        resultado['c5_senales'] = c5_senales
        resultado['c5_explicaciones'] = c5_explicaciones
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


def _resumen_correccion(c4_corr) -> str:
    """Traduce motivo técnico C4 a resumen legible para el header."""
    m = c4_corr.motivo or ''
    if 'COMPOSICION' in m:
        return 'Correccion multiple combinada'
    if 'FORZADO_H0' in m:
        return 'Estimacion forzada (revisar)'
    if 'PHANTOM_DIA' in m:
        return 'Cerrada fantasma eliminada (turno anterior)'
    if 'PHANTOM_NOCHE' in m:
        return 'Cerrada fantasma eliminada (turno actual)'
    if 'OMISION_DIA' in m:
        return 'Cerrada faltante recuperada (turno anterior)'
    if 'OMISION_NOCHE' in m:
        return 'Cerrada faltante recuperada (turno actual)'
    if 'OMISION_BILATERAL' in m:
        return 'Cerrada omitida detectada por turno siguiente'
    if 'MISMATCH_LEVE' in m:
        return 'Ajuste por varianza de pesaje'
    if 'GENEALOGIA' in m:
        return 'Entrante reclasificado como cerrada'
    if 'ENTRANTE_MISMO_CAN' in m:
        return 'Entrante duplicado descontado'
    if 'ENTRANTE_DUP' in m:
        return 'Entrante duplicado descontado'
    if 'APERTURA_REAL' in m:
        return 'Apertura de cerrada confirmada'
    if 'CONTINUIDAD' in m:
        return 'Varianza de pesaje ajustada'
    if 'DUPLICADO_CERRADA' in m:
        return 'Cerrada duplicada detectada'
    return f'Correccion aplicada ({c4_corr.delta:+d}g)'


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
        m = c4_corr.motivo or ''

        # --- Extraer pesos involucrados del motivo para referencia ---
        import re
        pesos_mencionados = [int(x) for x in re.findall(r'\b(\d{4,5})\b', m)]

        L.append('')
        L.append('ANALISIS:')

        if 'PHANTOM_DIA' in m:
            peso = pesos_mencionados[0] if pesos_mencionados else '?'
            L.append(f'  La cerrada de {peso}g del turno anterior no aparece en turnos cercanos.')
            L.append(f'  Revisando el historial, esa lata solo aparece en este turno y en ningun otro.')
            L.append(f'  Eso indica que fue un error de carga: la lata no existia realmente.')
            L.append(f'  Al quitarla del calculo, la venta baja {abs(c4_corr.delta)}g.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Se elimino la cerrada fantasma de {peso}g del turno anterior.')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'PHANTOM_NOCHE' in m:
            peso = pesos_mencionados[0] if pesos_mencionados else '?'
            L.append(f'  La cerrada de {peso}g del turno actual no aparece en el turno anterior ni en turnos cercanos.')
            L.append(f'  No hay entrante que la explique y no estaba antes. Es una lata "fantasma".')
            L.append(f'  Al quitarla del turno actual, la venta sube {abs(c4_corr.delta)}g.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Se elimino la cerrada fantasma de {peso}g del turno actual.')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'OMISION_DIA' in m:
            peso = pesos_mencionados[0] if pesos_mencionados else '?'
            L.append(f'  La cerrada de {peso}g no aparece en el turno anterior, pero SI aparece en turnos cercanos.')
            L.append(f'  Eso indica que la lata estaba en la heladera pero el empleado olvido anotarla.')
            L.append(f'  Al agregarla al turno anterior, el stock inicial sube y la venta baja {abs(c4_corr.delta)}g.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Se agrego la cerrada de {peso}g al turno anterior (estaba pero no se registro).')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'OMISION_NOCHE' in m or 'OMISION_BILATERAL' in m:
            peso = pesos_mencionados[0] if pesos_mencionados else '?'
            L.append(f'  La cerrada de {peso}g estaba en el turno anterior pero no aparece en el turno actual.')
            L.append(f'  Sin embargo, reaparece en el turno siguiente, asi que no se abrio ni se perdio.')
            L.append(f'  El empleado olvido registrarla en este turno.')
            L.append(f'  Al agregarla al turno actual, la venta baja {abs(c4_corr.delta)}g.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Se agrego la cerrada de {peso}g al turno actual (omitida pero presente fisicamente).')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'MISMATCH_LEVE' in m:
            if len(pesos_mencionados) >= 2:
                p1, p2 = pesos_mencionados[0], pesos_mencionados[1]
                diff = abs(p1 - p2)
                L.append(f'  La cerrada paso de {p1}g a {p2}g entre turnos (diferencia de {diff}g).')
                L.append(f'  Esa diferencia es menor a 200g, que es la varianza normal de pesaje.')
                L.append(f'  Son la misma lata fisica pesada en momentos distintos.')
            else:
                L.append(f'  Una cerrada cambio levemente de peso entre turnos (varianza de pesaje).')
            L.append(f'  Se ajusto el calculo para usar el peso correcto.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Ajuste por varianza de pesaje: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'GENEALOGIA' in m:
            if len(pesos_mencionados) >= 2:
                p1, p2 = pesos_mencionados[0], pesos_mencionados[1]
                L.append(f'  La cerrada de {p1}g se relaciona con el entrante de {p2}g.')
                L.append(f'  El entrante que llego en un turno anterior se convirtio en cerrada.')
                L.append(f'  Eso genera una diferencia en el calculo porque el peso cambio ligeramente.')
            else:
                L.append(f'  Un entrante que llego en un turno previo se convirtio en cerrada en este turno.')
            L.append(f'  Se ajusto el calculo para reconocer que es la misma lata.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Entrante reclasificado como cerrada: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'ENTRANTE_MISMO_CAN' in m or 'ENTRANTE_DUP' in m:
            if len(pesos_mencionados) >= 2:
                p1, p2 = pesos_mencionados[0], pesos_mencionados[1]
                L.append(f'  El entrante de {p1}g y la cerrada de {p2}g son la misma lata.')
                L.append(f'  El empleado anoto la misma lata dos veces: como entrante y como cerrada.')
                L.append(f'  Eso infla el stock y hace que la venta parezca mas alta de lo real.')
            else:
                L.append(f'  Un entrante resulto ser la misma lata que una cerrada (doble registro).')
            L.append(f'  Se desconto el peso duplicado del calculo.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Entrante duplicado descontado: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'APERTURA_REAL' in m:
            peso = pesos_mencionados[0] if pesos_mencionados else '?'
            L.append(f'  La cerrada de {peso}g fue abierta durante el turno.')
            L.append(f'  La abierta paso de {ab_d}g a {ab_n}g, lo cual es consistente con abrir una lata.')
            L.append(f'  La cerrada desaparecio porque su contenido se paso a la batea abierta.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Apertura confirmada. La venta incluye lo que se vendio de esa lata.')
            L.append(f'  Venta: {vf}g')

        elif 'CONTINUIDAD' in m:
            if len(pesos_mencionados) >= 2:
                p1, p2 = pesos_mencionados[0], pesos_mencionados[1]
                diff = abs(p1 - p2)
                L.append(f'  La cerrada de {p1}g del turno anterior aparece como {p2}g en el turno actual.')
                L.append(f'  La diferencia de {diff}g esta dentro de la varianza normal de pesaje.')
                L.append(f'  Es la misma lata fisica, solo cambio el peso por como se puso en la balanza.')
            else:
                L.append(f'  Una cerrada cambio de peso entre turnos pero es la misma lata fisica.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Ajuste por continuidad fisica: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        elif 'COMPOSICION' in m:
            # Contar cuantas correcciones compuestas
            n_parts = m.count('+')
            L.append(f'  Se detectaron {n_parts + 1} problemas combinados en este sabor.')
            L.append(f'  Cada uno por separado no explica el caso, pero juntos si.')
            # Desglosar las partes del motivo
            parts = [p.strip() for p in m.split('+') if p.strip()]
            for i, part in enumerate(parts, 1):
                if 'PHANTOM' in part:
                    L.append(f'  {i}. Una cerrada fantasma fue eliminada.')
                elif 'OMISION' in part:
                    L.append(f'  {i}. Una cerrada omitida fue recuperada.')
                elif 'MISMATCH' in part:
                    L.append(f'  {i}. Se ajusto una varianza de pesaje.')
                elif 'GENEALOGIA' in part:
                    L.append(f'  {i}. Un entrante fue reclasificado como cerrada.')
                elif 'CONTINUIDAD' in part:
                    L.append(f'  {i}. Se reconocio continuidad fisica de una lata.')
                elif 'BILATERAL' in part:
                    L.append(f'  {i}. Una cerrada omitida fue detectada por el turno siguiente.')
                else:
                    L.append(f'  {i}. Ajuste adicional.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Correccion combinada: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        else:
            L.append(f'  Se detecto una anomalia en los datos de este sabor.')
            L.append(f'  El sistema analizo los turnos cercanos y encontro una explicacion.')
            L.append('')
            L.append('CONCLUSION:')
            L.append(f'  Correccion aplicada: {c4_corr.delta:+d}g')
            L.append(f'  Venta corregida: {vf}g (antes {sc.venta_raw}g)')

        # Confianza
        if c4_corr.confianza:
            nivel = 'alta' if c4_corr.confianza >= 0.85 else ('media' if c4_corr.confianza >= 0.70 else 'baja')
            L.append(f'  Confianza: {nivel} ({int(c4_corr.confianza*100)}%)')

        # Que verificar
        L.append('')
        L.append('QUE VERIFICAR:')
        if 'PHANTOM' in m:
            L.append(f'  Revisar si la cerrada marcada como fantasma realmente existia o fue un error de tipeo.')
        elif 'OMISION' in m:
            L.append(f'  Buscar la lata en la heladera. Si sigue ahi, la correccion es correcta.')
        elif 'MISMATCH' in m or 'CONTINUIDAD' in m:
            L.append(f'  Comparar el peso de la cerrada con los turnos anteriores y siguientes.')
            L.append(f'  Si el peso se mantiene estable salvo este turno, fue error de pesaje.')
        elif 'GENEALOGIA' in m or 'ENTRANTE' in m:
            L.append(f'  Verificar con el empleado si el entrante era una lata nueva real o si la copio de las cerradas.')
        elif 'APERTURA' in m:
            L.append(f'  Verificar que la batea abierta se haya pesado correctamente.')
        else:
            L.append(f'  Comparar los pesos con los turnos anteriores y siguientes en el historial de abajo.')

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
