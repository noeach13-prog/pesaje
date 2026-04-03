"""
web_entrada.py — Blueprint Flask para carga de pesaje.

Acceso por PIN de sucursal. Sin cuentas, sin passwords.
El PIN identifica la sucursal; la sesion recuerda el acceso.

Rutas /entrada/* — coexiste con el sistema de analisis en /.
"""
import json
from datetime import date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, jsonify, session,
)

from .db import (
    get_db, obtener_sucursales, verificar_pin, crear_turno,
    guardar_sabores, obtener_turno, listar_turnos,
    sabores_turno_anterior, derivar_nombre_hoja, catalogo_sabores,
)

entrada_bp = Blueprint(
    'entrada', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/entrada/static',
)


# ─── Acceso por PIN ─────────────────────────────────────────────────

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
    hoy = date.today().isoformat()
    recientes = listar_turnos(db, sucursal_id=sid)[:10]
    db.close()

    return render_template('entrada/seleccion.html',
                           sucursal_nombre=nombre, sucursal_id=sid,
                           modo=modo, hoy=hoy, recientes=recientes)


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
    data = obtener_turno(db, turno_id)
    if not data or data['turno']['sucursal_id'] != sid:
        db.close()
        return "Turno no encontrado o no pertenece a esta sucursal", 404

    previos = sabores_turno_anterior(db, sid, data['turno']['fecha'])
    catalogo = catalogo_sabores(db, sid)
    db.close()

    # Sabores ya cargados en este turno (por nombre_norm)
    cargados = {s['nombre_norm'] for s in data['sabores']}

    return render_template('entrada/turno_form.html',
                           data=data, sabores_previos=previos,
                           catalogo=catalogo, cargados=cargados)


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
        return jsonify({'ok': False, 'error': 'Turno no encontrado'}), 404

    if turno['estado'] == 'confirmado':
        db.close()
        return jsonify({'ok': False, 'error': 'Turno ya confirmado'}), 400

    warnings = guardar_sabores(db, turno_id, sabores)
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
