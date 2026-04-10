"""
test_atomicidad_guardar.py — Tests crueles, no simbolicos, del refactor
que devuelve a "Guardar" su estatuto de operacion unica.

Dos invariantes verificados:

  1) ATOMICIDAD REAL: si cualquier helper falla durante el save, NINGUN
     dato queda persistido en ninguna de las 5 tablas del turno.

  2) TOKEN UNICO: los helpers ejecutados aisladamente NO modifican
     turnos.updated_at. La unica escritura valida de ese campo durante
     save esta en el orquestador.

Estado esperado al correrse:
  - Test 2 FALLA contra el codigo actual por comportamiento real
    (guardar_sabores ejecuta UPDATE turnos SET updated_at adentro).
    Este test es la unica herida viva del estado actual del repo.

  - Tests 1 y 3 FALLAN con ImportError contra el codigo actual porque
    _guardar_turno_atomico no existe aun. Son especificaciones
    ejecutables, no evidencia empirica — hasta que el refactor cree
    la funcion interna, momento en que pasan a ser tests reales.

Ejecutar: python -m pytest pesaje_v3/test_atomicidad_guardar.py -v

Smoke test de paridad de backend (Postgres):
  Si la variable de entorno TEST_DATABASE_URL esta seteada, los dos
  tests del wrapper con sufijo _pg se ejecutan contra Postgres real.
  Si no esta, esos tests se skippean limpiamente.

    python -m pytest pesaje_v3/test_atomicidad_guardar.py -v
    TEST_DATABASE_URL=postgresql://... python -m pytest \\
        pesaje_v3/test_atomicidad_guardar.py -v -k "_pg"

  REGLA DE PRODUCCION: el fixture PG usa exclusivamente la sucursal
  'San Miguel'. El resto de las sucursales tienen datos reales que NO
  deben tocarse bajo ninguna circunstancia.
"""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ───────────────────────────────────────────────────────────────────
# Fixtures y helpers
# ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """DB SQLite aislada en tmp_path. Inicializa schema + sucursales seed.

    Retorna (db, sucursal_id, turno_id) listo para ejercitar un save.
    """
    from pesaje_v3 import db as db_module

    db_path = str(tmp_path / 'test_atomicidad.db')
    monkeypatch.setattr(db_module, '_DB_PATH', db_path)
    # Forzar SQLite aunque el entorno tenga DATABASE_URL seteado
    monkeypatch.setattr(db_module, '_DATABASE_URL', '')

    db_module.init_db()

    db = db_module.get_db()
    # Usar la primera sucursal seed (San Martin)
    row = db.execute("SELECT id FROM sucursales ORDER BY id LIMIT 1").fetchone()
    sid = row['id']

    turno_id = db_module.crear_turno(db, sid, '2026-04-10', 'DIA', 'test_user')

    yield db, sid, turno_id

    db.close()


def _payload_valido(turno_id, updated_at=''):
    """Payload con datos reales en las 5 secciones del turno."""
    return {
        'turno_id': turno_id,
        'updated_at': updated_at,
        'sabores': [
            {'nombre': 'chocolate', 'abierta': 3000, 'cerrada_1': 6800},
            {'nombre': 'vainilla',  'abierta': 2500, 'cerrada_1': 6700},
        ],
        'vdp': [
            {'texto': 'copa grande', 'gramos': 300},
        ],
        'consumos': [
            {'texto': 'consumo empleado', 'gramos': 150, 'empleado': 'juan'},
        ],
        'notas': [
            {'categoria': 'novedad', 'detalle': 'todo ok'},
        ],
        'postres': [
            {'producto': 'flan', 'cantidad': 3},
        ],
        'timestamp': '2026-04-10T15:30:00-03:00',
    }


def _contar_filas(db, turno_id):
    """Retorna dict con count de filas por tabla para un turno_id."""
    tablas = ['sabores_turno', 'vdp_turno', 'consumo_turno', 'notas_turno', 'postres_turno']
    out = {}
    for t in tablas:
        row = db.execute(f"SELECT COUNT(*) as n FROM {t} WHERE turno_id = ?", (turno_id,)).fetchone()
        out[t] = row['n'] if isinstance(row, dict) else row[0]
    return out


def _leer_updated_at(db, turno_id):
    row = db.execute("SELECT updated_at FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    return row['updated_at']


# ───────────────────────────────────────────────────────────────────
# Test 1 — atomicidad cruel con escrituras reales pre-fallo
# ───────────────────────────────────────────────────────────────────

def test_helper_falla_a_mitad_no_persiste_nada(tmp_db, monkeypatch):
    """
    Invariante: si un helper tardio lanza excepcion despues de que los
    helpers previos hayan ejecutado escrituras reales, nada queda
    persistido en disco para ese turno_id.

    DISENO CRUEL:
      - guardar_sabores, guardar_vdp, guardar_consumos corren SIN mock,
        con datos reales del payload. Escriben filas reales adentro
        de la transaccion del orquestador (commit=False).
      - guardar_notas esta monkeypatcheado con un mock que:
          (a) verifica desde dentro de la transaccion que los 3 helpers
              previos ESCRIBIERON (evidencia pre-fallo),
          (b) ejecuta DELETE+INSERT reales sobre notas_turno (escritura
              propia tambien pre-fallo),
          (c) lanza RuntimeError.
      - Se espera que _guardar_turno_atomico atrape, haga rollback
        completo, y RE-LANCE la excepcion (no traduzca a 500).
      - Despues del raise, las 5 tablas deben estar vacias para ese
        turno_id y turnos.updated_at no debe haber cambiado.

    Este test no pasa por vacio: el bloque de intermediate_counts
    prueba adentro del mismo test que hubo escrituras reales.
    """
    from pesaje_v3.web_entrada import _guardar_turno_atomico

    db, sid, turno_id = tmp_db

    updated_at_inicial = _leer_updated_at(db, turno_id)
    # SQLite granularidad segundo: esperamos para que cualquier bump
    # posterior sea detectable via comparacion string.
    time.sleep(1.1)

    # Counts intermedios leidos DESDE el mock, dentro de la transaccion
    # no commiteada. Misma conexion = ve sus propias escrituras pendientes.
    intermediate_counts = {}

    def failing_guardar_notas(db_arg, turno_id_arg, notas_arg, commit=True):
        # (a) evidencia: los 3 helpers previos escribieron
        intermediate_counts['sabores_turno'] = db_arg.execute(
            "SELECT COUNT(*) as n FROM sabores_turno WHERE turno_id = ?",
            (turno_id_arg,),
        ).fetchone()['n']
        intermediate_counts['vdp_turno'] = db_arg.execute(
            "SELECT COUNT(*) as n FROM vdp_turno WHERE turno_id = ?",
            (turno_id_arg,),
        ).fetchone()['n']
        intermediate_counts['consumo_turno'] = db_arg.execute(
            "SELECT COUNT(*) as n FROM consumo_turno WHERE turno_id = ?",
            (turno_id_arg,),
        ).fetchone()['n']

        # (b) escritura propia real antes de lanzar
        db_arg.execute("DELETE FROM notas_turno WHERE turno_id = ?", (turno_id_arg,))
        db_arg.execute(
            "INSERT INTO notas_turno (turno_id, categoria, detalle) VALUES (?, ?, ?)",
            (turno_id_arg, 'otro', 'escritura que debe ser rollbackeada'),
        )
        intermediate_counts['notas_turno_pre_fallo'] = db_arg.execute(
            "SELECT COUNT(*) as n FROM notas_turno WHERE turno_id = ?",
            (turno_id_arg,),
        ).fetchone()['n']

        # (c) explota
        raise RuntimeError("simulated failure in guardar_notas")

    # El monkeypatch tiene que pegarle al simbolo que _guardar_turno_atomico
    # resuelve en su lookup. web_entrada.py importa guardar_notas al top
    # del modulo (via `from .db import ... guardar_notas ...`), asi que la
    # referencia viva esta en pesaje_v3.web_entrada.guardar_notas.
    from pesaje_v3 import web_entrada as we
    monkeypatch.setattr(we, 'guardar_notas', failing_guardar_notas)

    payload = _payload_valido(turno_id, updated_at=updated_at_inicial)

    # La funcion interna debe RE-LANZAR la RuntimeError del helper,
    # no traducirla a un (500, dict). El wrapper Flask hace esa traduccion.
    with pytest.raises(RuntimeError, match="simulated failure in guardar_notas"):
        _guardar_turno_atomico(db, sid, turno_id, payload)

    # BLOQUE 1: evidencia de que hubo escrituras reales pre-fallo.
    # Si este bloque fallara, el test cruel seria vacio.
    assert intermediate_counts.get('sabores_turno') == 2, (
        f"guardar_sabores no escribio filas adentro de la transaccion. "
        f"intermediate={intermediate_counts}"
    )
    assert intermediate_counts.get('vdp_turno') == 1, (
        f"guardar_vdp no escribio. intermediate={intermediate_counts}"
    )
    assert intermediate_counts.get('consumo_turno') == 1, (
        f"guardar_consumos no escribio. intermediate={intermediate_counts}"
    )
    assert intermediate_counts.get('notas_turno_pre_fallo') == 1, (
        f"mock de guardar_notas no escribio antes de lanzar. "
        f"intermediate={intermediate_counts}"
    )

    # BLOQUE 2: rollback total. Las 5 tablas deben quedar en cero.
    counts_finales = _contar_filas(db, turno_id)
    for tabla, n in counts_finales.items():
        assert n == 0, (
            f"FUGA DE ATOMICIDAD: {tabla} tiene {n} filas del turno {turno_id} "
            f"despues del fallo de guardar_notas. "
            f"pre-fallo={intermediate_counts}, post-rollback={counts_finales}"
        )

    # BLOQUE 3: updated_at no se movio.
    updated_at_final = _leer_updated_at(db, turno_id)
    assert updated_at_final == updated_at_inicial, (
        f"updated_at cambio pese al rollback: "
        f"{updated_at_inicial!r} -> {updated_at_final!r}"
    )


# ───────────────────────────────────────────────────────────────────
# Test 2 — helpers aislados no bumpean updated_at
# ───────────────────────────────────────────────────────────────────

def test_helpers_aislados_no_bumpean_updated_at(tmp_db):
    """
    Invariante: turnos.updated_at es propiedad del orquestador, no de
    los helpers. Llamar a los helpers directamente (con commit=True
    default) escribe sus datos en sus tablas, pero NO debe modificar
    turnos.updated_at.

    Este test NO neutraliza a los helpers: corren con comportamiento
    normal de persistencia, escriben filas reales. Lo unico que se
    verifica es que esa persistencia no incluya tocar turnos.*.

    Post-refactor: cada helper escribe solo su propia tabla. El test
    pasa.

    Contra el codigo actual: este test FALLA por comportamiento real.
    guardar_sabores ejecuta UPDATE turnos SET updated_at = datetime('now')
    adentro, y el sleep previo garantiza que el cambio sea detectable.
    """
    from pesaje_v3.db import (
        guardar_sabores, guardar_vdp, guardar_consumos,
        guardar_notas, guardar_postres,
    )

    db, sid, turno_id = tmp_db

    updated_at_inicial = _leer_updated_at(db, turno_id)
    time.sleep(1.1)

    # guardar_sabores
    guardar_sabores(db, turno_id, [
        {'nombre': 'chocolate', 'abierta': 3000, 'cerrada_1': 6800},
    ])
    assert _contar_filas(db, turno_id)['sabores_turno'] == 1, (
        "guardar_sabores no escribio — test invalido, no demuestra nada"
    )
    assert _leer_updated_at(db, turno_id) == updated_at_inicial, (
        "guardar_sabores modifico turnos.updated_at (invariante rota)"
    )

    # guardar_vdp
    guardar_vdp(db, turno_id, [{'texto': 'copa grande', 'gramos': 300}])
    assert _contar_filas(db, turno_id)['vdp_turno'] == 1, (
        "guardar_vdp no escribio — test invalido"
    )
    assert _leer_updated_at(db, turno_id) == updated_at_inicial, (
        "guardar_vdp modifico turnos.updated_at"
    )

    # guardar_consumos
    guardar_consumos(db, turno_id, [
        {'texto': 'consumo empleado', 'gramos': 150, 'empleado': 'juan'},
    ])
    assert _contar_filas(db, turno_id)['consumo_turno'] == 1, (
        "guardar_consumos no escribio — test invalido"
    )
    assert _leer_updated_at(db, turno_id) == updated_at_inicial, (
        "guardar_consumos modifico turnos.updated_at"
    )

    # guardar_notas
    guardar_notas(db, turno_id, [{'categoria': 'novedad', 'detalle': 'test'}])
    assert _contar_filas(db, turno_id)['notas_turno'] == 1, (
        "guardar_notas no escribio — test invalido"
    )
    assert _leer_updated_at(db, turno_id) == updated_at_inicial, (
        "guardar_notas modifico turnos.updated_at"
    )

    # guardar_postres
    guardar_postres(db, turno_id, [{'producto': 'flan', 'cantidad': 3}])
    assert _contar_filas(db, turno_id)['postres_turno'] == 1, (
        "guardar_postres no escribio — test invalido"
    )
    assert _leer_updated_at(db, turno_id) == updated_at_inicial, (
        "guardar_postres modifico turnos.updated_at"
    )


# ───────────────────────────────────────────────────────────────────
# Test 3 — camino feliz: save completo persiste todo y bumpea una vez
# ───────────────────────────────────────────────────────────────────

def test_save_valido_persiste_todo_y_bumpea_una_sola_vez(tmp_db):
    """
    Contraparte del test cruel: cuando no hay errores, el orquestador
    persiste las 5 secciones y bumpea turnos.updated_at exactamente a
    un nuevo valor, devolviendolo al cliente en el body.

    Verifica el camino feliz y cierra el triangulo:
      - Test 1: rollback total sobre fallo
      - Test 2: helpers aislados no tocan updated_at
      - Test 3: save valido persiste todo con un solo bump
    """
    from pesaje_v3.web_entrada import _guardar_turno_atomico

    db, sid, turno_id = tmp_db

    updated_at_inicial = _leer_updated_at(db, turno_id)
    time.sleep(1.1)

    payload = _payload_valido(turno_id, updated_at=updated_at_inicial)
    status, body = _guardar_turno_atomico(db, sid, turno_id, payload)

    assert status == 200, f"Se esperaba 200, se obtuvo {status}: {body}"
    assert body.get('ok') is True

    counts = _contar_filas(db, turno_id)
    assert counts['sabores_turno'] == 2
    assert counts['vdp_turno'] == 1
    assert counts['consumo_turno'] == 1
    assert counts['notas_turno'] == 1
    assert counts['postres_turno'] == 1

    updated_at_final = _leer_updated_at(db, turno_id)
    assert updated_at_final != updated_at_inicial, (
        "updated_at no cambio tras un save exitoso"
    )
    assert body.get('updated_at') == updated_at_final, (
        "el body devolvio un updated_at distinto al persistido en DB"
    )


# ───────────────────────────────────────────────────────────────────
# Tests 4 y 5 — smoke test del wrapper HTTP api_guardar_turno
# ───────────────────────────────────────────────────────────────────
#
# No reemplazan a los tests crueles de atomicidad (esos atacan el core).
# Verifican que el borde HTTP no traduzca la verdad del core con acento
# equivocado: camino feliz → 200 + updated_at; token viejo → 409 + conflict.

@pytest.fixture
def flask_client(tmp_path, monkeypatch):
    """Flask test client con DB aislada. Simula sesion con sucursal activa."""
    from pesaje_v3 import db as db_module

    db_path = str(tmp_path / 'test_wrapper.db')
    monkeypatch.setattr(db_module, '_DB_PATH', db_path)
    monkeypatch.setattr(db_module, '_DATABASE_URL', '')

    db_module.init_db()

    # Crear turno de test
    db = db_module.get_db()
    row = db.execute("SELECT id, nombre FROM sucursales ORDER BY id LIMIT 1").fetchone()
    sid = row['id']
    sucursal_nombre = row['nombre']
    turno_id = db_module.crear_turno(db, sid, '2026-04-10', 'DIA', 'test_user')
    updated_at_inicial = _leer_updated_at(db, turno_id)
    db.close()

    # Importar app y setear sesion
    from pesaje_v3.web import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['sucursal_id'] = sid
        sess['sucursal_nombre'] = sucursal_nombre
        sess['sucursal_modo'] = 'DIA_NOCHE'

    yield client, sid, turno_id, updated_at_inicial


def test_wrapper_http_camino_feliz(flask_client):
    """El wrapper api_guardar_turno debe devolver 200 + updated_at nuevo
    en un save valido. Verifica la traduccion Flask ↔ core ↔ JSON."""
    client, sid, turno_id, updated_at_inicial = flask_client
    time.sleep(1.1)

    payload = _payload_valido(turno_id, updated_at=updated_at_inicial)
    resp = client.post(
        '/entrada/api/guardar-turno',
        json=payload,
    )

    assert resp.status_code == 200, (
        f"Se esperaba 200, se obtuvo {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    body = resp.get_json()
    assert body['ok'] is True
    assert 'updated_at' in body
    assert body['updated_at'] != updated_at_inicial, (
        "wrapper devolvio el mismo updated_at del request (no hubo bump)"
    )
    assert body['n_sabores'] == 2


def test_wrapper_http_conflict_real(flask_client):
    """El wrapper debe devolver 409 con conflict=True cuando el token
    del cliente no coincide con el del servidor. Simula el caso de dos
    pestañas donde la segunda tiene un token viejo."""
    client, sid, turno_id, updated_at_inicial = flask_client
    time.sleep(1.1)

    # Primer save con token valido → exito, bumpea updated_at
    resp1 = client.post(
        '/entrada/api/guardar-turno',
        json=_payload_valido(turno_id, updated_at=updated_at_inicial),
    )
    assert resp1.status_code == 200

    # Segundo save con el token VIEJO (simula pestaña desactualizada)
    resp2 = client.post(
        '/entrada/api/guardar-turno',
        json=_payload_valido(turno_id, updated_at=updated_at_inicial),
    )
    assert resp2.status_code == 409, (
        f"Se esperaba 409, se obtuvo {resp2.status_code}: {resp2.get_data(as_text=True)}"
    )
    body2 = resp2.get_json()
    assert body2['ok'] is False
    assert body2.get('conflict') is True, (
        f"body no tiene conflict=True: {body2}"
    )
    assert body2.get('server_updated'), (
        "body no incluye server_updated para que el cliente pueda sincronizar"
    )


# ───────────────────────────────────────────────────────────────────
# Smoke test de paridad SQLite ↔ Postgres — solo wrapper HTTP
# ───────────────────────────────────────────────────────────────────
#
# Objetivo: validar que el optimistic lock con comparacion por igualdad
# estricta de updated_at siga comportandose correctamente cuando el
# backend devuelve timestamps con precision de microsegundos (Postgres)
# en lugar de segundos (SQLite).
#
# Solo se duplican los dos tests del wrapper HTTP (camino feliz + conflict
# real). Los tests del core atomico y los de helpers aislados NO se
# duplican: son backend-agnosticos y su verde en SQLite extrapola
# razonablemente al backend PG porque la diferencia estructural vive en
# el borde (formato del token), no en la logica transaccional.
#
# REGLA DE PRODUCCION: el fixture usa EXCLUSIVAMENTE la sucursal
# 'San Miguel'. Las demas sucursales tienen datos reales que no deben
# tocarse. Si San Miguel no existe en la DB de test, el fixture skippea.

def _limpiar_turno_pg(db, turno_id):
    """Borra un turno y todas sus filas hijas en orden FK-safe.

    Usado por flask_client_pg en setup defensivo y teardown. Una sola
    transaccion, un solo commit al final. Si algo falla, rollback.
    No toca sucursales, catalogos, ni otros turnos.
    """
    try:
        db.execute("DELETE FROM sabores_turno WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM vdp_turno     WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM consumo_turno WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM notas_turno   WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM postres_turno WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM log_actividad WHERE turno_id = ?", (turno_id,))
        db.execute("DELETE FROM turnos        WHERE id = ?",        (turno_id,))
        db.commit()
    except Exception:
        try:
            db._conn.rollback()
        except Exception:
            pass
        raise


@pytest.fixture
def flask_client_pg(monkeypatch):
    """Flask test client contra Postgres real. Smoke de paridad de backend.

    Requiere TEST_DATABASE_URL apuntando a una DB de tests. Si no esta,
    pytest.skip() limpio.

    Aislamiento de datos:
      - REGLA DE PRODUCCION: usa exclusivamente la sucursal 'San Miguel'.
        Si no existe, skip. Las demas sucursales tienen datos reales.
      - Usa fecha reservada '2099-01-01' que no colisiona con datos reales.
      - Setup defensivo: barre cualquier turno residual que coincida con
        la triple clave completa (sucursal_id_san_miguel, fecha_reservada,
        tipo_turno). NO barre por fecha+tipo a secas para no tocar turnos
        de otras sucursales.
      - Teardown: borra solo las filas del turno creado por este fixture,
        en orden FK-safe, sin tocar nada mas.
    """
    test_url = os.environ.get('TEST_DATABASE_URL', '')
    if not test_url:
        pytest.skip("TEST_DATABASE_URL no configurada; smoke Postgres omitido")

    from pesaje_v3 import db as db_module

    monkeypatch.setattr(db_module, '_DATABASE_URL', test_url)
    db_module.init_db()

    # Invariantes de test — no cambiar sin revisar la regla de produccion.
    SUCURSAL_TEST = 'San Miguel'
    FECHA_TEST = '2099-01-01'
    TIPO_TEST = 'DIA'

    db = db_module.get_db()

    # Resolver sucursal ANTES de cualquier limpieza defensiva. Si no existe,
    # abortar sin tocar nada.
    row_suc = db.execute(
        "SELECT id, nombre FROM sucursales WHERE nombre = ?",
        (SUCURSAL_TEST,),
    ).fetchone()
    if not row_suc:
        db.close()
        pytest.skip(
            f"Sucursal '{SUCURSAL_TEST}' no existe en la DB de test. "
            f"Esta es la unica sucursal permitida para pruebas."
        )
    sid = row_suc['id']
    sucursal_nombre = row_suc['nombre']

    # Setup defensivo: barrer cualquier turno residual de corridas anteriores
    # que haya fallado en teardown. Filtro por la triple clave COMPLETA para
    # no tocar turnos de otras sucursales ni con fechas distintas.
    # La unicidad (sucursal_id, fecha, tipo_turno) deberia garantizar que
    # haya a lo sumo uno, pero iteramos por robustez contra estados raros.
    residuales = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id = ? AND fecha = ? AND tipo_turno = ?",
        (sid, FECHA_TEST, TIPO_TEST),
    ).fetchall()
    for r in residuales:
        _limpiar_turno_pg(db, r['id'])

    turno_id = db_module.crear_turno(db, sid, FECHA_TEST, TIPO_TEST, 'test_pg_user')
    updated_at_inicial = _leer_updated_at(db, turno_id)
    db.close()

    # Configurar app Flask con sesion simulada
    from pesaje_v3.web import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-pg'

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['sucursal_id'] = sid
        sess['sucursal_nombre'] = sucursal_nombre
        sess['sucursal_modo'] = 'DIA_NOCHE'  # San Miguel es DIA_NOCHE en seed

    yield client, sid, turno_id, updated_at_inicial

    # Teardown: borrar solo el turno que este fixture creo.
    db = db_module.get_db()
    try:
        _limpiar_turno_pg(db, turno_id)
    finally:
        db.close()


def test_wrapper_http_camino_feliz_pg(flask_client_pg):
    """Camino feliz del wrapper contra Postgres real.

    Contraparte directa de test_wrapper_http_camino_feliz. Verifica que
    el flujo Flask → _guardar_turno_atomico → Postgres → response JSON
    se comporte identico al de SQLite cuando el backend devuelve
    timestamps con microsegundos.
    """
    client, sid, turno_id, updated_at_inicial = flask_client_pg
    time.sleep(1.1)

    payload = _payload_valido(turno_id, updated_at=updated_at_inicial)
    resp = client.post('/entrada/api/guardar-turno', json=payload)

    assert resp.status_code == 200, (
        f"[PG] Se esperaba 200, se obtuvo {resp.status_code}: "
        f"{resp.get_data(as_text=True)}"
    )
    body = resp.get_json()
    assert body['ok'] is True
    assert 'updated_at' in body
    assert body['updated_at'] != updated_at_inicial, (
        "[PG] wrapper devolvio el mismo updated_at del request (no hubo bump)"
    )
    assert body['n_sabores'] == 2


def test_wrapper_http_conflict_real_pg(flask_client_pg):
    """Conflict real entre dos tabs contra Postgres real.

    Contraparte directa de test_wrapper_http_conflict_real. Verifica que
    el optimistic lock con igualdad estricta de updated_at siga detectando
    el conflict cuando el backend devuelve timestamps con microsegundos.
    Este es el test mas sensible al formato del token.
    """
    client, sid, turno_id, updated_at_inicial = flask_client_pg
    time.sleep(1.1)

    # Primer save con token valido → 200, bumpea updated_at en PG
    resp1 = client.post(
        '/entrada/api/guardar-turno',
        json=_payload_valido(turno_id, updated_at=updated_at_inicial),
    )
    assert resp1.status_code == 200, (
        f"[PG] primer save fallo: {resp1.status_code} "
        f"{resp1.get_data(as_text=True)}"
    )

    # Segundo save con el token VIEJO (simula pestaña desactualizada)
    resp2 = client.post(
        '/entrada/api/guardar-turno',
        json=_payload_valido(turno_id, updated_at=updated_at_inicial),
    )
    assert resp2.status_code == 409, (
        f"[PG] se esperaba 409, se obtuvo {resp2.status_code}: "
        f"{resp2.get_data(as_text=True)}"
    )
    body2 = resp2.get_json()
    assert body2['ok'] is False
    assert body2.get('conflict') is True, (
        f"[PG] body no tiene conflict=True: {body2}"
    )
    assert body2.get('server_updated'), (
        "[PG] body no incluye server_updated para que el cliente pueda sincronizar"
    )
