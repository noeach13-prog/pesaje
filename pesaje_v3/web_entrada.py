"""
web_entrada.py — Blueprint Flask para carga de pesaje.

Rutas /entrada/* — coexiste con el sistema de analisis en /.
"""
import json
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, jsonify

from .db import (
    get_db, obtener_sucursales, crear_turno, guardar_sabores,
    obtener_turno, listar_turnos, sabores_turno_anterior,
    derivar_nombre_hoja,
)

entrada_bp = Blueprint(
    'entrada', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/entrada/static',
)


@entrada_bp.route('/entrada/')
def seleccion():
    """Pagina de seleccion: sucursal + fecha + turno."""
    db = get_db()
    sucursales = obtener_sucursales(db)
    hoy = date.today().isoformat()

    # Turnos recientes para mostrar estado
    recientes = listar_turnos(db)[:20]
    db.close()

    return render_template('entrada/seleccion.html',
                           sucursales=sucursales, hoy=hoy, recientes=recientes)


@entrada_bp.route('/entrada/turno/nuevo', methods=['POST'])
def nuevo_turno():
    """Crea turno vacio y redirige al form."""
    db = get_db()
    sucursal_id = int(request.form['sucursal_id'])
    fecha = request.form['fecha']
    tipo_turno = request.form['tipo_turno']
    ingresado_por = request.form.get('ingresado_por', '').strip() or None

    # Verificar si ya existe
    existente = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno=?",
        (sucursal_id, fecha, tipo_turno),
    ).fetchone()

    if existente:
        db.close()
        return redirect(url_for('entrada.editar_turno', turno_id=existente['id']))

    turno_id = crear_turno(db, sucursal_id, fecha, tipo_turno, ingresado_por)
    db.close()
    return redirect(url_for('entrada.editar_turno', turno_id=turno_id))


@entrada_bp.route('/entrada/turno/<int:turno_id>')
def editar_turno(turno_id):
    """Formulario de carga de sabores para un turno."""
    db = get_db()
    data = obtener_turno(db, turno_id)
    if not data:
        db.close()
        return "Turno no encontrado", 404

    # Sabores del turno anterior (para pre-rellenar)
    previos = sabores_turno_anterior(
        db, data['turno']['sucursal_id'], data['turno']['fecha']
    )
    db.close()

    return render_template('entrada/turno_form.html',
                           data=data, sabores_previos=previos)


@entrada_bp.route('/entrada/api/guardar', methods=['POST'])
def api_guardar():
    """
    Guarda todos los sabores del turno.
    Revalida server-side SIEMPRE, aunque client ya valido.
    Acepta JSON: {turno_id, sabores: [{nombre, abierta, celiaca, cerrada_1..6, entrante_1..2}]}
    """
    payload = request.get_json()
    if not payload:
        return jsonify({'ok': False, 'error': 'JSON vacio'}), 400

    turno_id = payload.get('turno_id')
    sabores = payload.get('sabores', [])

    if not turno_id:
        return jsonify({'ok': False, 'error': 'turno_id requerido'}), 400

    db = get_db()

    # Verificar que el turno existe y es borrador
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        db.close()
        return jsonify({'ok': False, 'error': 'Turno no encontrado'}), 404

    if turno['estado'] == 'confirmado':
        db.close()
        return jsonify({'ok': False, 'error': 'Turno ya confirmado, no se puede editar'}), 400

    warnings = guardar_sabores(db, turno_id, sabores)
    db.close()

    return jsonify({
        'ok': True,
        'warnings': warnings,
        'n_sabores': len(sabores),
    })


@entrada_bp.route('/entrada/api/sabores-previos/<int:sucursal_id>/<fecha>')
def api_sabores_previos(sucursal_id, fecha):
    """Retorna nombres de sabores del turno anterior."""
    db = get_db()
    nombres = sabores_turno_anterior(db, sucursal_id, fecha)
    db.close()
    return jsonify({'sabores': nombres})


@entrada_bp.route('/entrada/historial')
def historial():
    """Lista de turnos cargados."""
    db = get_db()
    sucursales = obtener_sucursales(db)
    sucursal_id = request.args.get('sucursal_id', type=int)
    mes = request.args.get('mes')
    turnos = listar_turnos(db, sucursal_id, mes)
    db.close()
    return render_template('entrada/historial.html',
                           turnos=turnos, sucursales=sucursales,
                           sucursal_id=sucursal_id, mes=mes)
