"""
web_entrada.py — Blueprint Flask para carga de pesaje.

Acceso por PIN de sucursal. Sin cuentas, sin passwords.
El PIN identifica la sucursal; la sesion recuerda el acceso.

Rutas /entrada/* — coexiste con el sistema de analisis en /.
"""
import json
from datetime import date, datetime, timezone, timedelta
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, jsonify, session,
)

from .db import (
    get_db, obtener_sucursales, verificar_pin, crear_turno,
    guardar_sabores, obtener_turno, listar_turnos,
    sabores_turno_anterior, derivar_nombre_hoja, catalogo_sabores,
    agregar_sabor_catalogo, guardar_vdp, guardar_consumos, guardar_notas,
    registrar_inicio_carga, confirmar_turno, registrar_actividad,
    desbloquear_turno, borrar_turno, obtener_turno,
)

entrada_bp = Blueprint(
    'entrada', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/entrada/static',
)


# ─── Acceso por PIN ─────────────────────────────────────────────────

@entrada_bp.before_request
def _validar_sesion():
    """Si la sesion tiene una sucursal_id que ya no existe en la DB
    (porque Railway recreo la DB), limpiar sesion silenciosamente."""
    sid = session.get('sucursal_id')
    if sid:
        db = get_db()
        existe = db.execute("SELECT 1 FROM sucursales WHERE id = ?", (sid,)).fetchone()
        db.close()
        if not existe:
            session.clear()


def _datos_turno_anterior(db, sucursal_id, fecha):
    """Retorna dict {nombre_norm: {abierta, cerrada_1..6, entrante_1..2}} del turno anterior."""
    row = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id = ? AND fecha < ? ORDER BY fecha DESC, tipo_turno DESC LIMIT 1",
        (sucursal_id, fecha),
    ).fetchone()
    if not row:
        return {}
    sabores = db.execute(
        "SELECT * FROM sabores_turno WHERE turno_id = ?", (row['id'],)
    ).fetchall()
    return {s['nombre_norm']: dict(s) for s in sabores}


def _sucursal_activa():
    """Retorna (sucursal_id, nombre) de la sesion, o (None, None)."""
    sid = session.get('sucursal_id')
    nombre = session.get('sucursal_nombre')
    if sid and nombre:
        return sid, nombre
    return None, None


@entrada_bp.route('/entrada/')
def index():
    """Si hay sesion activa, va a seleccion. Si no, pide PIN."""
    sid, nombre = _sucursal_activa()
    if sid:
        return redirect(url_for('entrada.seleccion'))
    db = get_db()
    sucursales = obtener_sucursales(db)
    db.close()
    return render_template('entrada/login.html', sucursales=sucursales, error=None)


@entrada_bp.route('/entrada/login', methods=['POST'])
def login():
    """Verifica PIN y crea sesion."""
    db = get_db()
    sucursal_id = request.form.get('sucursal_id', type=int)
    pin = request.form.get('pin', '').strip()

    if not sucursal_id or not pin:
        sucursales = obtener_sucursales(db)
        db.close()
        return render_template('entrada/login.html',
                               sucursales=sucursales, error='Selecciona sucursal e ingresa el codigo')

    sucursal = verificar_pin(db, sucursal_id, pin)
    db.close()

    if not sucursal:
        db2 = get_db()
        sucursales = obtener_sucursales(db2)
        db2.close()
        return render_template('entrada/login.html',
                               sucursales=sucursales, error='Codigo incorrecto')

    session.permanent = True  # sesion larga (30 dias)
    session['sucursal_id'] = sucursal['id']
    session['sucursal_nombre'] = sucursal['nombre']
    session['sucursal_modo'] = sucursal['modo']
    return redirect(url_for('entrada.seleccion'))


@entrada_bp.route('/entrada/salir')
def salir():
    """Cierra sesion."""
    session.pop('sucursal_id', None)
    session.pop('sucursal_nombre', None)
    session.pop('sucursal_modo', None)
    return redirect(url_for('entrada.index'))


# ─── Rutas protegidas ───────────────────────────────────────────────

@entrada_bp.route('/entrada/seleccion')
def seleccion():
    """Pagina de seleccion: fecha + turno (sucursal ya definida por sesion)."""
    sid, nombre = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))

    db = get_db()
    modo = session.get('sucursal_modo', 'DIA_NOCHE')
    _AR = timezone(timedelta(hours=-3))
    hoy = datetime.now(_AR).date().isoformat()
    recientes = listar_turnos(db, sucursal_id=sid)[:10]

    # Determinar proximo turno en secuencia
    ultimo = db.execute(
        "SELECT fecha, tipo_turno FROM turnos WHERE sucursal_id = ? ORDER BY fecha DESC, tipo_turno DESC LIMIT 1",
        (sid,),
    ).fetchone()

    if ultimo:
        ult_fecha = ultimo['fecha']
        ult_tipo = ultimo['tipo_turno']
        if modo == 'DIA_NOCHE' and ult_tipo == 'DIA':
            # Siguiente: NOCHE del mismo dia
            prox_fecha = ult_fecha
            prox_tipo = 'NOCHE'
        else:
            # Siguiente: dia siguiente
            from datetime import date as date_cls
            d = date_cls.fromisoformat(ult_fecha) + timedelta(days=1)
            prox_fecha = d.isoformat()
            prox_tipo = 'DIA' if modo == 'DIA_NOCHE' else 'UNICO'
    else:
        prox_fecha = hoy
        prox_tipo = 'DIA' if modo == 'DIA_NOCHE' else 'UNICO'

    # Turnos ya creados para esta sucursal (para bloquear duplicados en el form)
    existentes = db.execute(
        "SELECT fecha, tipo_turno, estado FROM turnos WHERE sucursal_id = ? ORDER BY fecha, tipo_turno",
        (sid,),
    ).fetchall()
    turnos_existentes = [{'fecha': r['fecha'], 'tipo': r['tipo_turno'], 'estado': r['estado']} for r in existentes]

    db.close()

    return render_template('entrada/seleccion.html',
                           sucursal_nombre=nombre, sucursal_id=sid,
                           modo=modo, hoy=hoy, recientes=recientes,
                           prox_fecha=prox_fecha, prox_tipo=prox_tipo,
                           turnos_existentes=turnos_existentes)


@entrada_bp.route('/entrada/turno/nuevo', methods=['POST'])
def nuevo_turno():
    """Crea turno vacio y redirige al form."""
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))

    db = get_db()
    fecha = request.form['fecha']
    tipo_turno = request.form['tipo_turno']
    ingresado_por = request.form.get('ingresado_por', '').strip() or None
    modo = session.get('sucursal_modo', 'DIA_NOCHE')

    # Si ya existe, redirigir al existente
    existente = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno=?",
        (sid, fecha, tipo_turno),
    ).fetchone()

    if existente:
        db.close()
        return redirect(url_for('entrada.editar_turno', turno_id=existente['id']))

    turno_id = crear_turno(db, sid, fecha, tipo_turno, ingresado_por)
    db.close()
    return redirect(url_for('entrada.editar_turno', turno_id=turno_id))


@entrada_bp.route('/entrada/turno/<int:turno_id>')
def editar_turno(turno_id):
    """Formulario de carga de sabores para un turno."""
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))

    db = get_db()

    # Verificar que la sesion sigue valida (sucursal existe en DB)
    suc_check = db.execute("SELECT id FROM sucursales WHERE id = ?", (sid,)).fetchone()
    if not suc_check:
        db.close()
        session.clear()
        return redirect(url_for('entrada.index'))

    data = obtener_turno(db, turno_id)
    if not data:
        db.close()
        return redirect(url_for('entrada.seleccion'))
    if data['turno']['sucursal_id'] != sid:
        db.close()
        return redirect(url_for('entrada.seleccion'))

    catalogo = catalogo_sabores(db, sid)

    # Datos del turno anterior: pesos completos para referencia visual
    ref_turno = _datos_turno_anterior(db, sid, data['turno']['fecha'])

    db.close()

    # Sabores ya cargados en este turno (por nombre_norm)
    cargados_dict = {s['nombre_norm']: s for s in data['sabores']}

    return render_template('entrada/turno_form.html',
                           data=data, catalogo=catalogo,
                           cargados=cargados_dict, ref=ref_turno)


@entrada_bp.route('/entrada/api/guardar', methods=['POST'])
def api_guardar():
    """Guarda sabores. Revalida server-side SIEMPRE."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json()
    if not payload:
        return jsonify({'ok': False, 'error': 'JSON vacio'}), 400

    turno_id = payload.get('turno_id')
    sabores = payload.get('sabores', [])

    if not turno_id:
        return jsonify({'ok': False, 'error': 'turno_id requerido'}), 400

    db = get_db()
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return jsonify({'ok': False, 'error': 'Turno no encontrado. Recargar la pagina e intentar de nuevo.'}), 404

    if turno['estado'] == 'confirmado':
        db.close()
        return jsonify({'ok': False, 'error': 'Turno ya confirmado'}), 400

    warnings = guardar_sabores(db, turno_id, sabores)

    # Registrar actividad con timestamp del dispositivo
    ts = payload.get('timestamp', '')
    if ts:
        registrar_actividad(db, turno_id, ts, 'guardar', f'{len(sabores)} sabores')

    db.close()

    return jsonify({
        'ok': True,
        'warnings': warnings,
        'n_sabores': len(sabores),
    })


@entrada_bp.route('/entrada/api/sabores-previos/<fecha>')
def api_sabores_previos(fecha):
    """Retorna nombres de sabores del turno anterior."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'sabores': []})
    db = get_db()
    nombres = sabores_turno_anterior(db, sid, fecha)
    db.close()
    return jsonify({'sabores': nombres})


@entrada_bp.route('/entrada/historial')
def historial():
    """Lista de turnos cargados para la sucursal activa."""
    sid, nombre = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))

    db = get_db()
    mes = request.args.get('mes')
    turnos = listar_turnos(db, sucursal_id=sid, mes=mes)
    db.close()
    return render_template('entrada/historial.html',
                           turnos=turnos, sucursal_nombre=nombre, mes=mes)


# ─── APIs: VDP, Consumos, Notas, Agregar sabor ──────────────────────

def _verificar_turno_editable(turno_id):
    """Helper: verifica sesion + pertenencia + estado borrador. Retorna (db, turno) o (None, error_response)."""
    sid, _ = _sucursal_activa()
    if not sid:
        return None, (jsonify({'ok': False, 'error': 'No autenticado'}), 401)
    db = get_db()
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return None, (jsonify({'ok': False, 'error': 'Turno no encontrado. Recargar la pagina e intentar de nuevo.'}), 404)
    if turno['estado'] == 'confirmado':
        db.close()
        return None, (jsonify({'ok': False, 'error': 'Turno ya confirmado'}), 400)
    return db, turno


@entrada_bp.route('/entrada/api/guardar-extras', methods=['POST'])
def api_guardar_extras():
    """Guarda VDP + consumos + notas de un turno."""
    payload = request.get_json()
    if not payload:
        return jsonify({'ok': False, 'error': 'JSON vacio'}), 400

    turno_id = payload.get('turno_id')
    if not turno_id:
        return jsonify({'ok': False, 'error': 'turno_id requerido'}), 400

    db, turno_or_err = _verificar_turno_editable(turno_id)
    if db is None:
        return turno_or_err

    vdp = payload.get('vdp', [])
    consumos = payload.get('consumos', [])
    notas = payload.get('notas', [])

    guardar_vdp(db, turno_id, vdp)
    guardar_consumos(db, turno_id, consumos)
    guardar_notas(db, turno_id, notas)
    db.close()

    return jsonify({
        'ok': True,
        'n_vdp': len([v for v in vdp if (v.get('texto') or '').strip()]),
        'n_consumos': len([c for c in consumos if (c.get('texto') or '').strip()]),
        'n_notas': len([n for n in notas if (n.get('detalle') or '').strip()]),
    })


@entrada_bp.route('/entrada/api/agregar-sabor', methods=['POST'])
def api_agregar_sabor():
    """Agrega un sabor nuevo al catálogo de la sucursal activa."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json()
    nombre = (payload.get('nombre') or '').strip() if payload else ''
    if not nombre:
        return jsonify({'ok': False, 'error': 'Nombre vacio'}), 400

    db = get_db()
    nombre_norm = agregar_sabor_catalogo(db, sid, nombre)
    db.close()

    if not nombre_norm:
        return jsonify({'ok': False, 'error': 'Nombre invalido'}), 400

    return jsonify({'ok': True, 'nombre_norm': nombre_norm})


@entrada_bp.route('/entrada/api/desbloquear', methods=['POST'])
def api_desbloquear():
    """Desbloquea turno confirmado con PIN de supervisor."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json() or {}
    turno_id = payload.get('turno_id')
    pin = payload.get('pin_supervisor', '')
    ts = payload.get('timestamp', '')

    if not turno_id or not pin:
        return jsonify({'ok': False, 'error': 'Faltan datos'}), 400

    db = get_db()
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return jsonify({'ok': False, 'error': 'Turno no encontrado'}), 404

    resultado = desbloquear_turno(db, turno_id, pin)
    if resultado.get('ok') and ts:
        registrar_actividad(db, turno_id, ts, 'desbloquear', 'Desbloqueado por supervisor')
    db.close()
    return jsonify(resultado)


@entrada_bp.route('/entrada/planilla/<int:turno_id>')
def planilla(turno_id):
    """Vista planilla: datos crudos tipo Excel con comparativa del dia anterior."""
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))
    db = get_db()
    data = obtener_turno(db, turno_id)
    if not data or data['turno']['sucursal_id'] != sid:
        db.close()
        return redirect(url_for('entrada.seleccion'))

    # Turno anterior para comparativa
    t_ant = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha<? ORDER BY fecha DESC, tipo_turno DESC LIMIT 1",
        (sid, data['turno']['fecha']),
    ).fetchone()
    data_ant = obtener_turno(db, t_ant['id']) if t_ant else None
    db.close()

    # Indexar anterior por nombre_norm para comparar
    ant_por_sabor = {}
    if data_ant:
        for s in data_ant['sabores']:
            ant_por_sabor[s['nombre_norm']] = s

    return render_template('entrada/planilla.html', data=data,
                           data_ant=data_ant, ant=ant_por_sabor)


@entrada_bp.route('/entrada/exportar-turno/<int:turno_id>')
def exportar_turno_route(turno_id):
    """Descarga Excel de un turno individual."""
    from flask import send_file
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))
    db = get_db()
    turno = db.execute("SELECT * FROM turnos WHERE id=?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return redirect(url_for('entrada.seleccion'))
    from .excel_generador import exportar_turno
    path = exportar_turno(db, turno_id)
    db.close()
    return send_file(path, as_attachment=True)


@entrada_bp.route('/entrada/exportar-mes/<int:anio>/<int:mes>')
def exportar_mes_route(anio, mes):
    """Descarga Excel del mes completo de la sucursal activa."""
    from flask import send_file
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))
    db = get_db()
    from .excel_generador import exportar_mes
    try:
        path = exportar_mes(db, sid, anio, mes)
    except ValueError as e:
        db.close()
        return str(e), 404
    db.close()
    return send_file(path, as_attachment=True)


@entrada_bp.route('/entrada/pedido/<int:turno_id>')
def pedido(turno_id):
    """Sugerencia de pedido por sabor basada en historial confirmado."""
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))
    db = get_db()
    data = obtener_turno(db, turno_id)
    if not data or data['turno']['sucursal_id'] != sid:
        db.close()
        return redirect(url_for('entrada.seleccion'))

    pedidos, n_turnos_hist = _calcular_sugerencia_pedido(db, data)
    db.close()
    return render_template('entrada/pedido.html',
                           data=data, pedidos=pedidos, n_turnos_hist=n_turnos_hist)


def _calcular_sugerencia_pedido(db, data):
    """
    Para cada sabor del turno, calcula sugerencia de pedido.
    Usa historial de ventas CONFIRMADAS de la misma sucursal.
    Lógica operativa, no analítica — no usa el pipeline.
    """
    sid = data['turno']['sucursal_id']
    fecha = data['turno']['fecha']
    tipo = data['turno']['tipo_turno']

    # Buscar turnos confirmados anteriores de la misma sucursal
    turnos_hist = db.execute(
        """SELECT t.id, t.fecha, t.tipo_turno FROM turnos t
           WHERE t.sucursal_id = ? AND t.estado = 'confirmado' AND t.fecha < ?
           ORDER BY t.fecha DESC LIMIT 10""",
        (sid, fecha),
    ).fetchall()

    n_turnos = len(turnos_hist)

    # Para cada turno histórico, calcular ventas por sabor
    # venta = diferencia entre turno anterior y el turno
    # Simplificación: usar la abierta como proxy de consumo
    # (abierta_anterior - abierta_actual = lo que se vendió de la abierta)
    # Más robusto: usar total_anterior - total_actual

    # Recoger todos los sabores con sus pesos por turno
    hist_por_sabor = {}
    all_turnos = list(reversed(turnos_hist))  # cronológico

    for i in range(len(all_turnos)):
        t = all_turnos[i]
        sabs = db.execute(
            "SELECT nombre_norm, abierta, cerrada_1, cerrada_2, cerrada_3, cerrada_4, cerrada_5, cerrada_6 FROM sabores_turno WHERE turno_id=?",
            (t['id'],),
        ).fetchall()

        for s in sabs:
            nn = s['nombre_norm']
            ab = s['abierta'] or 0
            cerr = sum(s[f'cerrada_{j}'] or 0 for j in range(1, 7))
            total = ab + cerr

            if nn not in hist_por_sabor:
                hist_por_sabor[nn] = []
            hist_por_sabor[nn].append(total)

    # Calcular ventas como diferencia entre turnos consecutivos
    ventas_por_sabor = {}
    for nn, totales in hist_por_sabor.items():
        ventas = []
        for i in range(1, len(totales)):
            v = totales[i - 1] - totales[i]  # anterior - actual = venta
            if v > 0:
                ventas.append(v)
        ventas_por_sabor[nn] = ventas

    # Generar sugerencia para cada sabor del turno actual
    pedidos = []
    for s in data['sabores']:
        nn = s['nombre_norm']

        # Desglose del stock actual tal como lo cargó el empleado
        ab = s['abierta'] or 0
        cel = s.get('celiaca') or 0
        cerradas = [s[f'cerrada_{i}'] for i in range(1, 7) if s.get(f'cerrada_{i}') is not None]
        entrantes = [s[f'entrante_{i}'] for i in range(1, 3) if s.get(f'entrante_{i}') is not None]
        stock_actual = ab + cel + sum(cerradas) + sum(entrantes)

        ventas = ventas_por_sabor.get(nn, [])
        N = len(ventas)

        base = {
            'nombre': nn,
            'abierta': ab if ab else None,
            'celiaca': cel if cel else None,
            'cerradas': cerradas,
            'entrantes': entrantes,
            'stock_actual': stock_actual,
            'ventas_hist': ventas,
        }

        if N == 0:
            base.update({
                'venta_promedio': None,
                'tendencia': None,
                'venta_proyectada': None,
                'stock_necesario': 0,
                'sugerencia': 'Sin historial suficiente',
            })
            pedidos.append(base)
            continue

        venta_promedio = sum(ventas) / N
        tendencia = (ventas[-1] - ventas[0]) / (N - 1) if N >= 2 else 0
        venta_proyectada = max(0, venta_promedio + tendencia)
        stock_necesario = venta_proyectada * 2
        deficit = stock_necesario - stock_actual

        if deficit > 9000:
            sug = 'Pedir urgente: 2 latas'
        elif deficit > 3000:
            sug = 'Pedir 1 lata (~6500g)'
        elif deficit > 0:
            sug = 'Stock justo'
        else:
            sug = 'Stock suficiente'

        base.update({
            'venta_promedio': venta_promedio,
            'tendencia': tendencia,
            'venta_proyectada': venta_proyectada,
            'stock_necesario': stock_necesario,
            'sugerencia': sug,
        })
        pedidos.append(base)

    # Ordenar: urgentes primero, luego pedir, luego justo, luego ok, luego sin historial
    orden = {'Pedir urgente: 2 latas': 0, 'Pedir 1 lata (~6500g)': 1, 'Stock justo': 2, 'Stock suficiente': 3, 'Sin historial suficiente': 4}
    pedidos.sort(key=lambda p: (orden.get(p['sugerencia'], 5), p['nombre']))

    return pedidos, n_turnos


@entrada_bp.route('/entrada/revision/<int:turno_id>')
def revision(turno_id):
    """Página de revisión con resultados de validación."""
    sid, _ = _sucursal_activa()
    if not sid:
        return redirect(url_for('entrada.index'))

    db = get_db()
    data = obtener_turno(db, turno_id)
    if not data or data['turno']['sucursal_id'] != sid:
        db.close()
        return redirect(url_for('entrada.seleccion'))

    from .validacion_entrada import analizar_turno
    analisis = analizar_turno(db, turno_id)
    db.close()

    return render_template('entrada/revision.html',
                           data=data, analisis=analisis)


@entrada_bp.route('/entrada/api/borrar-turno', methods=['POST'])
def api_borrar_turno():
    """Borra turno completo con PIN de supervisor."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json() or {}
    turno_id = payload.get('turno_id')
    pin = payload.get('pin_supervisor', '')

    if not turno_id or not pin:
        return jsonify({'ok': False, 'error': 'Faltan datos'}), 400

    db = get_db()
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return jsonify({'ok': False, 'error': 'Turno no encontrado'}), 404

    resultado = borrar_turno(db, turno_id, pin)
    db.close()
    return jsonify(resultado)


@entrada_bp.route('/entrada/api/carga-masiva', methods=['POST'])
def api_carga_masiva():
    """Carga masiva de turnos desde JSON. Para importar datos de Excel."""
    payload = request.get_json()
    if not payload or not isinstance(payload, list):
        return jsonify({'ok': False, 'error': 'Se espera lista de turnos'}), 400

    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    db = get_db()
    resultados = []
    for item in payload:
        fecha = item.get('fecha')
        sabores = item.get('sabores', [])
        label = item.get('label', fecha)
        tipo = item.get('tipo', 'UNICO')

        if not fecha or not sabores:
            continue

        # Si ya existe, borrar y recrear
        existing = db.execute(
            "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno=?",
            (sid, fecha, tipo),
        ).fetchone()
        if existing:
            db.execute("DELETE FROM turnos WHERE id=?", (existing['id'],))
            db.commit()

        tid = crear_turno(db, sid, fecha, tipo)
        warnings = guardar_sabores(db, tid, sabores)
        db.execute("UPDATE turnos SET estado='confirmado' WHERE id=?", (tid,))
        db.commit()
        resultados.append({'fecha': fecha, 'label': label, 'turno_id': tid, 'n_sabores': len(sabores)})

    db.close()
    return jsonify({'ok': True, 'turnos': resultados})


@entrada_bp.route('/entrada/api/debug-turnos')
def api_debug_turnos():
    """Debug: muestra datos crudos de todos los turnos."""
    db = get_db()
    turnos = db.execute('SELECT id, fecha, tipo_turno, estado FROM turnos ORDER BY fecha, tipo_turno').fetchall()
    result = []
    for t in turnos:
        sabs = db.execute('SELECT nombre_norm, abierta, celiaca, cerrada_1, cerrada_2, cerrada_3, cerrada_4, cerrada_5, cerrada_6, entrante_1, entrante_2 FROM sabores_turno WHERE turno_id=? ORDER BY nombre_norm', (t['id'],)).fetchall()
        sabores = []
        for s in sabs:
            cerr = [s[f'cerrada_{i}'] for i in range(1,7) if s[f'cerrada_{i}'] is not None]
            ent = [s[f'entrante_{i}'] for i in range(1,3) if s[f'entrante_{i}'] is not None]
            sabores.append({'nombre': s['nombre_norm'], 'ab': s['abierta'], 'cel': s['celiaca'], 'cerr': cerr, 'ent': ent})
        result.append({'id': t['id'], 'fecha': t['fecha'], 'tipo': t['tipo_turno'], 'estado': t['estado'], 'sabores': sabores})
    db.close()
    return jsonify(result)


@entrada_bp.route('/entrada/api/inicio-carga', methods=['POST'])
def api_inicio_carga():
    """Registra timestamp del dispositivo cuando abre el form (solo la primera vez)."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False}), 401
    payload = request.get_json() or {}
    turno_id = payload.get('turno_id')
    ts = payload.get('timestamp', '')
    if turno_id and ts:
        db = get_db()
        registrar_inicio_carga(db, turno_id, ts)
        registrar_actividad(db, turno_id, ts, 'abrir', 'Inicio de carga')
        db.close()
    return jsonify({'ok': True})


@entrada_bp.route('/entrada/api/confirmar', methods=['POST'])
def api_confirmar():
    """Confirma el turno. No se puede editar después."""
    sid, _ = _sucursal_activa()
    if not sid:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json() or {}
    turno_id = payload.get('turno_id')
    ts = payload.get('timestamp', '')
    nombre = payload.get('confirmado_por', '')

    if not turno_id:
        return jsonify({'ok': False, 'error': 'turno_id requerido'}), 400

    db = get_db()
    # Verificar pertenencia
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno or turno['sucursal_id'] != sid:
        db.close()
        return jsonify({'ok': False, 'error': 'Turno no encontrado. Recargar la pagina e intentar de nuevo.'}), 404

    # Correr analisis completo antes de confirmar
    from .validacion_entrada import analizar_turno
    analisis = analizar_turno(db, turno_id)

    resultado = confirmar_turno(db, turno_id, ts, nombre)
    if resultado.get('ok'):
        registrar_actividad(db, turno_id, ts, 'confirmar',
                            f'{resultado["n_sabores"]} sabores, {resultado["total_peso"]}g')
        resultado['analisis'] = analisis
    db.close()
    return jsonify(resultado)
