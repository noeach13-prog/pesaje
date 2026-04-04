"""
db.py — SQLite schema + CRUD para el sistema de carga de pesaje.

Tres reglas de diseño:
1. nombre_hoja es DERIVADO de (fecha, tipo_turno, modo), no dato soberano.
2. updated_at desde el primer día — sin rastro temporal no hay auditoría.
3. Las validaciones de campo se repiten server-side aunque el client las haga.
"""
import os
import sqlite3
from datetime import date, datetime
from typing import Optional, List, Dict, Any

# Importar normalize_name del parser existente — NO reimplementar
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parser import normalize_name

_DB_PATH = os.environ.get('PESAJE_DB', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'pesaje.db'
))

_DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


# ─── Conexión ───────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Retorna conexión con row_factory=sqlite3.Row."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Crea tablas si no existen. Idempotente. Migra schema si faltan columnas."""
    conn = get_db()
    conn.executescript(_SCHEMA)

    # Migrations
    cols_suc = [r[1] for r in conn.execute("PRAGMA table_info(sucursales)").fetchall()]
    if 'pin' not in cols_suc:
        conn.execute("ALTER TABLE sucursales ADD COLUMN pin TEXT NOT NULL DEFAULT '0000'")
    if 'pin_supervisor' not in cols_suc:
        conn.execute("ALTER TABLE sucursales ADD COLUMN pin_supervisor TEXT NOT NULL DEFAULT '0000'")

    cols_turno = [r[1] for r in conn.execute("PRAGMA table_info(turnos)").fetchall()]
    if 'inicio_carga' not in cols_turno:
        conn.execute("ALTER TABLE turnos ADD COLUMN inicio_carga TEXT")
    if 'fin_carga' not in cols_turno:
        conn.execute("ALTER TABLE turnos ADD COLUMN fin_carga TEXT")

    cols_consumo = [r[1] for r in conn.execute("PRAGMA table_info(consumo_turno)").fetchall()]
    if cols_consumo and 'empleado' not in cols_consumo:
        conn.execute("ALTER TABLE consumo_turno ADD COLUMN empleado TEXT")

    # Semilla: sucursales con PIN empleado + PIN supervisor
    for nombre, modo, pin, pin_sup in [
        ('San Martín', 'DIA_NOCHE', '2512', '2512'),
        ('Triunvirato', 'TURNO_UNICO', '2512', '2512'),
        ('Unión', 'TURNO_UNICO', '2512', '2512'),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO sucursales (nombre, modo, pin, pin_supervisor) VALUES (?, ?, ?, ?)",
            (nombre, modo, pin, pin_sup),
        )
        conn.execute(
            "UPDATE sucursales SET pin = ?, pin_supervisor = ? WHERE nombre = ? AND (pin = '0000' OR pin_supervisor = '0000')",
            (pin, pin_sup, nombre),
        )

    # Semilla: catálogo de sabores por sucursal (extraídos de workbooks reales)
    _sembrar_catalogo(conn)
    conn.commit()
    conn.close()


# Catálogo base: sabores comunes a todas las sucursales
_SABORES_BASE = [
    'AMARGO', 'AMERICANA', 'ANANA', 'B, SPLIT', 'BANANITA', 'BLANCO',
    'BOSQUE', 'CABSHA', 'CADBURY', 'CEREZA', 'CH AMORES', 'CH C/ALM',
    'CHOCOLATE', 'CHOCOLATE DUBAI', 'CHOCOLATE SUIZO', 'CIELO', 'COCO',
    'COOKIES', 'CREMA DE FRAMBUESAS', 'D. GRANIZADO', 'D. PATAGONICO',
    'DOS CORAZONES', 'DULCE AMORES', 'DULCE C/NUEZ', 'DULCE D LECHE',
    'DURAZNO', 'FERRERO', 'FLAN', 'FRAMBUEZA', 'FRANUI',
    'FRUTILLA AGUA', 'FRUTILLA CREMA', 'FRUTILLA REINA', 'GRANIZADO',
    'IRLANDESA', 'KINDER', 'KITKAT', 'LEMON PIE', 'LIMON',
    'MANTECOL', 'MANZANA', 'MARACUYA', 'MARROC', 'MASCARPONE',
    'MENTA', 'MIX DE FRUTA', 'MOUSSE LIMON', 'NUTE', 'PISTACHO',
    'RUSA', 'SAMBAYON', 'SAMBAYON AMORES', 'SUPER', 'TIRAMISU',
    'TRAMONTANA', 'VAINILLA', 'YOGURT',
]

# Sabores adicionales por sucursal
_SABORES_EXTRA = {
    'Unión': [
        'FRAMORE', 'HAVANNA', 'LEMON COOKIE', 'LUCUMA', 'MANGO',
        'NARANJA', 'NUTELLA', 'OREO', 'PERA', 'PRALINE',
        'QUINOA', 'RICOTTA', 'SANDIA', 'TOBLERONE', 'TORTUFA',
    ],
}


def _sembrar_catalogo(conn):
    """Inserta catálogo de sabores si la tabla está vacía."""
    count = conn.execute("SELECT COUNT(*) FROM catalogo_sabores").fetchone()[0]
    if count > 0:
        return  # ya sembrado

    sucursales = {r[1]: r[0] for r in conn.execute("SELECT id, nombre FROM sucursales").fetchall()}
    for suc_nombre, suc_id in sucursales.items():
        sabores = list(_SABORES_BASE)
        sabores.extend(_SABORES_EXTRA.get(suc_nombre, []))
        for s in sorted(set(sabores)):
            conn.execute(
                "INSERT OR IGNORE INTO catalogo_sabores (sucursal_id, nombre_norm) VALUES (?, ?)",
                (suc_id, s),
            )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sucursales (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    modo TEXT NOT NULL DEFAULT 'DIA_NOCHE',
    pin TEXT NOT NULL DEFAULT '0000',
    pin_supervisor TEXT NOT NULL DEFAULT '0000',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    fecha TEXT NOT NULL,                    -- 'YYYY-MM-DD'
    tipo_turno TEXT NOT NULL,               -- 'DIA', 'NOCHE', 'UNICO'
    estado TEXT NOT NULL DEFAULT 'borrador',-- 'borrador' o 'confirmado'
    ingresado_por TEXT,
    confirmado_por TEXT,
    inicio_carga TEXT,                      -- timestamp dispositivo: cuando abrio el form
    fin_carga TEXT,                         -- timestamp dispositivo: cuando confirmo
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(sucursal_id, fecha, tipo_turno)
);

CREATE TABLE IF NOT EXISTS sabores_turno (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    nombre_norm TEXT NOT NULL,
    abierta INTEGER,
    celiaca INTEGER,
    cerrada_1 INTEGER, cerrada_2 INTEGER, cerrada_3 INTEGER,
    cerrada_4 INTEGER, cerrada_5 INTEGER, cerrada_6 INTEGER,
    entrante_1 INTEGER, entrante_2 INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(turno_id, nombre_norm)
);

CREATE TABLE IF NOT EXISTS vdp_turno (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    gramos INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS consumo_turno (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    gramos INTEGER NOT NULL DEFAULT 0,
    empleado TEXT
);

CREATE TABLE IF NOT EXISTS notas_turno (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    categoria TEXT NOT NULL,
    detalle TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS catalogo_sabores (
    id INTEGER PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    nombre_norm TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sucursal_id, nombre_norm)
);

CREATE TABLE IF NOT EXISTS log_actividad (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    timestamp_cliente TEXT NOT NULL,        -- hora del dispositivo
    accion TEXT NOT NULL,                   -- 'guardar', 'confirmar', 'abrir'
    detalle TEXT,                           -- 'N sabores', 'inactivo 45 min', etc
    gap_minutos INTEGER,                   -- minutos desde la ultima actividad (NULL si primera)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# ─── nombre_hoja: derivado, no soberano ─────────────────────────────

def derivar_nombre_hoja(fecha_str: str, tipo_turno: str, modo: str) -> str:
    """
    Genera nombre_hoja a partir de (fecha, tipo_turno, modo).
    Es la misma convención que usa el parser para detectar hojas.
    """
    dt = date.fromisoformat(fecha_str)
    dia_semana = _DIAS_SEMANA[dt.weekday()]
    dia_num = dt.day

    if modo == 'DIA_NOCHE':
        sufijo = '(DIA)' if tipo_turno == 'DIA' else '(NOCHE)'
        return f'{dia_semana} {dia_num} {sufijo}'
    else:
        return f'{dia_semana} {dia_num}'


# ─── Validación server-side (tier 1: campos) ────────────────────────

_PESO_MAX = 7900  # constante física, misma que capa1_parser

def validar_peso(valor: Any) -> Optional[str]:
    """Valida un peso individual. Retorna mensaje de error o None si ok."""
    if valor is None:
        return None  # NULL es válido (no registrado)
    try:
        v = int(valor)
    except (ValueError, TypeError):
        return f'Valor "{valor}" no es numerico'
    if v < 0:
        return f'Peso negativo: {v}g'
    if v > _PESO_MAX:
        return f'Peso {v}g excede maximo fisico ({_PESO_MAX}g)'
    if 0 < v < 50:
        return f'Peso {v}g sospechosamente bajo (cantidad en vez de peso?)'
    return None


def validar_sabor_server(row: dict) -> List[str]:
    """
    Validación server-side de una fila de sabor completa.
    Se ejecuta SIEMPRE al guardar, aunque el client ya haya validado.
    Retorna lista de errores/warnings (vacía = ok).
    """
    errores = []

    # Nombre
    nombre = (row.get('nombre') or '').strip()
    if not nombre:
        errores.append('Nombre de sabor vacio')
        return errores

    # Campos de peso
    for campo in ['abierta', 'celiaca']:
        err = validar_peso(row.get(campo))
        if err:
            errores.append(f'{campo}: {err}')

    for i in range(1, 7):
        err = validar_peso(row.get(f'cerrada_{i}'))
        if err:
            errores.append(f'cerrada_{i}: {err}')

    for i in range(1, 3):
        err = validar_peso(row.get(f'entrante_{i}'))
        if err:
            errores.append(f'entrante_{i}: {err}')

    # Al menos un campo con dato
    tiene_dato = any(
        row.get(c) is not None and row.get(c) != ''
        for c in ['abierta', 'celiaca'] +
                 [f'cerrada_{i}' for i in range(1, 7)] +
                 [f'entrante_{i}' for i in range(1, 3)]
    )
    if not tiene_dato:
        errores.append('Sabor sin ningun peso registrado')

    return errores


# ─── CRUD ────────────────────────────────────────────────────────────

def crear_turno(db: sqlite3.Connection, sucursal_id: int, fecha: str,
                tipo_turno: str, ingresado_por: str = None) -> int:
    """Crea un turno vacío en estado borrador. Retorna turno.id."""
    cur = db.execute(
        """INSERT INTO turnos (sucursal_id, fecha, tipo_turno, ingresado_por)
           VALUES (?, ?, ?, ?)""",
        (sucursal_id, fecha, tipo_turno, ingresado_por),
    )
    db.commit()
    return cur.lastrowid


def guardar_sabores(db: sqlite3.Connection, turno_id: int,
                    sabores: List[dict]) -> List[str]:
    """
    Guarda/reemplaza todos los sabores de un turno.
    Revalida server-side antes de insertar.
    Retorna lista de warnings (vacía = todo limpio).
    """
    warnings = []

    # Borrar sabores previos del turno
    db.execute("DELETE FROM sabores_turno WHERE turno_id = ?", (turno_id,))

    for row in sabores:
        # Validación server-side obligatoria
        errs = validar_sabor_server(row)
        nombre = (row.get('nombre') or '').strip()
        if errs:
            for e in errs:
                warnings.append(f'{nombre}: {e}')
            # Si hay errores de tipo/rango, no insertar esa fila
            if any('no es numerico' in e or 'negativo' in e for e in errs):
                continue

        nombre_norm = normalize_name(nombre)
        if not nombre_norm:
            continue

        def _int_or_none(val):
            if val is None or val == '':
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        db.execute(
            """INSERT OR REPLACE INTO sabores_turno
               (turno_id, nombre, nombre_norm, abierta, celiaca,
                cerrada_1, cerrada_2, cerrada_3, cerrada_4, cerrada_5, cerrada_6,
                entrante_1, entrante_2)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                turno_id, nombre, nombre_norm,
                _int_or_none(row.get('abierta')),
                _int_or_none(row.get('celiaca')),
                _int_or_none(row.get('cerrada_1')),
                _int_or_none(row.get('cerrada_2')),
                _int_or_none(row.get('cerrada_3')),
                _int_or_none(row.get('cerrada_4')),
                _int_or_none(row.get('cerrada_5')),
                _int_or_none(row.get('cerrada_6')),
                _int_or_none(row.get('entrante_1')),
                _int_or_none(row.get('entrante_2')),
            ),
        )

    # Actualizar updated_at del turno
    db.execute(
        "UPDATE turnos SET updated_at = datetime('now') WHERE id = ?",
        (turno_id,),
    )
    db.commit()
    return warnings


def registrar_inicio_carga(db: sqlite3.Connection, turno_id: int, timestamp_cliente: str):
    """Registra cuándo el empleado abrió el form (timestamp del dispositivo).
    Solo se escribe una vez — si ya tiene inicio_carga, no sobreescribe."""
    db.execute(
        "UPDATE turnos SET inicio_carga = ? WHERE id = ? AND inicio_carga IS NULL",
        (timestamp_cliente, turno_id),
    )
    db.commit()


def confirmar_turno(db: sqlite3.Connection, turno_id: int,
                    timestamp_cliente: str, confirmado_por: str = None) -> dict:
    """Marca turno como confirmado. Registra fin_carga. No reversible.
    Retorna resumen del turno confirmado."""
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return {'ok': False, 'error': 'Turno no encontrado'}
    if turno['estado'] == 'confirmado':
        return {'ok': False, 'error': 'Turno ya confirmado'}

    # Verificar que tenga al menos 1 sabor con datos
    n_sabores = db.execute(
        "SELECT COUNT(*) FROM sabores_turno WHERE turno_id = ?", (turno_id,)
    ).fetchone()[0]
    if n_sabores == 0:
        return {'ok': False, 'error': 'No hay sabores cargados'}

    db.execute(
        """UPDATE turnos SET estado = 'confirmado', fin_carga = ?,
           confirmado_por = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (timestamp_cliente, confirmado_por, turno_id),
    )
    db.commit()

    # Resumen
    total_peso = db.execute(
        """SELECT COALESCE(SUM(
            COALESCE(abierta,0)+COALESCE(celiaca,0)+
            COALESCE(cerrada_1,0)+COALESCE(cerrada_2,0)+COALESCE(cerrada_3,0)+
            COALESCE(cerrada_4,0)+COALESCE(cerrada_5,0)+COALESCE(cerrada_6,0)+
            COALESCE(entrante_1,0)+COALESCE(entrante_2,0)
        ), 0) FROM sabores_turno WHERE turno_id = ?""",
        (turno_id,),
    ).fetchone()[0]

    n_vdp = db.execute("SELECT COUNT(*) FROM vdp_turno WHERE turno_id=?", (turno_id,)).fetchone()[0]
    total_vdp = db.execute("SELECT COALESCE(SUM(gramos),0) FROM vdp_turno WHERE turno_id=?", (turno_id,)).fetchone()[0]

    return {
        'ok': True,
        'n_sabores': n_sabores,
        'total_peso': total_peso,
        'n_vdp': n_vdp,
        'total_vdp': total_vdp,
        'inicio_carga': turno['inicio_carga'],
        'fin_carga': timestamp_cliente,
    }


def desbloquear_turno(db: sqlite3.Connection, turno_id: int,
                      pin_supervisor: str) -> dict:
    """Desbloquea un turno confirmado para editar. Requiere PIN de supervisor."""
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return {'ok': False, 'error': 'Turno no encontrado'}
    if turno['estado'] != 'confirmado':
        return {'ok': False, 'error': 'El turno no esta confirmado'}

    # Verificar PIN supervisor de la sucursal
    suc = db.execute(
        "SELECT pin_supervisor FROM sucursales WHERE id = ?",
        (turno['sucursal_id'],),
    ).fetchone()
    if not suc or suc['pin_supervisor'] != pin_supervisor.strip():
        return {'ok': False, 'error': 'PIN de supervisor incorrecto'}

    db.execute(
        "UPDATE turnos SET estado = 'borrador', updated_at = datetime('now') WHERE id = ?",
        (turno_id,),
    )
    db.commit()
    return {'ok': True}


def obtener_turno(db: sqlite3.Connection, turno_id: int) -> Optional[dict]:
    """Retorna turno con sus sabores."""
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return None

    sabores = db.execute(
        "SELECT * FROM sabores_turno WHERE turno_id = ? ORDER BY nombre_norm",
        (turno_id,),
    ).fetchall()

    sucursal = db.execute(
        "SELECT * FROM sucursales WHERE id = ?", (turno['sucursal_id'],)
    ).fetchone()

    vdp = db.execute(
        "SELECT * FROM vdp_turno WHERE turno_id = ? ORDER BY id", (turno_id,)
    ).fetchall()
    consumos = db.execute(
        "SELECT * FROM consumo_turno WHERE turno_id = ? ORDER BY id", (turno_id,)
    ).fetchall()
    notas = db.execute(
        "SELECT * FROM notas_turno WHERE turno_id = ? ORDER BY id", (turno_id,)
    ).fetchall()

    return {
        'turno': dict(turno),
        'sabores': [dict(s) for s in sabores],
        'sucursal': dict(sucursal),
        'nombre_hoja': derivar_nombre_hoja(
            turno['fecha'], turno['tipo_turno'], sucursal['modo']
        ),
        'vdp': [dict(v) for v in vdp],
        'consumos': [dict(c) for c in consumos],
        'notas': [dict(n) for n in notas],
        'log': obtener_log_actividad(db, turno_id),
    }


def listar_turnos(db: sqlite3.Connection, sucursal_id: int = None,
                  mes: str = None) -> List[dict]:
    """Lista turnos con filtros opcionales."""
    query = "SELECT t.*, s.nombre as sucursal_nombre, s.modo FROM turnos t JOIN sucursales s ON t.sucursal_id = s.id WHERE 1=1"
    params = []
    if sucursal_id:
        query += " AND t.sucursal_id = ?"
        params.append(sucursal_id)
    if mes:
        query += " AND t.fecha LIKE ?"
        params.append(f'{mes}%')  # 'YYYY-MM'
    query += " ORDER BY t.fecha DESC, t.tipo_turno"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def verificar_pin(db: sqlite3.Connection, sucursal_id: int, pin: str) -> Optional[dict]:
    """Verifica PIN de acceso. Retorna sucursal si correcto, None si no."""
    row = db.execute(
        "SELECT * FROM sucursales WHERE id = ? AND pin = ?",
        (sucursal_id, pin.strip()),
    ).fetchone()
    return dict(row) if row else None


def obtener_sucursales(db: sqlite3.Connection) -> List[dict]:
    """Lista todas las sucursales (sin exponer el PIN)."""
    rows = db.execute("SELECT id, nombre, modo FROM sucursales ORDER BY nombre").fetchall()
    return [dict(r) for r in rows]


def catalogo_sabores(db: sqlite3.Connection, sucursal_id: int) -> List[str]:
    """Retorna lista ordenada de sabores del catálogo para esta sucursal."""
    rows = db.execute(
        "SELECT nombre_norm FROM catalogo_sabores WHERE sucursal_id = ? AND activo = 1 ORDER BY nombre_norm",
        (sucursal_id,),
    ).fetchall()
    return [r['nombre_norm'] for r in rows]


def agregar_sabor_catalogo(db: sqlite3.Connection, sucursal_id: int, nombre: str) -> str:
    """Agrega un sabor nuevo al catálogo. Retorna el nombre_norm."""
    nombre_norm = normalize_name(nombre)
    if not nombre_norm:
        return ''
    db.execute(
        "INSERT OR IGNORE INTO catalogo_sabores (sucursal_id, nombre_norm) VALUES (?, ?)",
        (sucursal_id, nombre_norm),
    )
    db.commit()
    return nombre_norm


def sabores_turno_anterior(db: sqlite3.Connection, sucursal_id: int,
                           fecha: str) -> List[str]:
    """
    Retorna los nombres de sabores del turno más reciente antes de `fecha`
    para esta sucursal. Para pre-rellenar el formulario.
    """
    row = db.execute(
        """SELECT id FROM turnos
           WHERE sucursal_id = ? AND fecha < ?
           ORDER BY fecha DESC, tipo_turno DESC LIMIT 1""",
        (sucursal_id, fecha),
    ).fetchone()
    if not row:
        return []
    sabores = db.execute(
        "SELECT nombre FROM sabores_turno WHERE turno_id = ? ORDER BY nombre_norm",
        (row['id'],),
    ).fetchall()
    return [s['nombre'] for s in sabores]


# ─── VDP, Consumos, Notas ───────────────────────────────────────────

def registrar_actividad(db: sqlite3.Connection, turno_id: int,
                        timestamp_cliente: str, accion: str,
                        detalle: str = ''):
    """Registra una accion en el log. Calcula gap vs ultima actividad."""
    # Buscar ultima actividad de este turno
    ultima = db.execute(
        "SELECT timestamp_cliente FROM log_actividad WHERE turno_id = ? ORDER BY id DESC LIMIT 1",
        (turno_id,),
    ).fetchone()

    gap = None
    gap_texto = ''
    if ultima:
        gap = _calcular_gap_minutos(ultima['timestamp_cliente'], timestamp_cliente)
        if gap is not None and gap >= 30:
            gap_texto = f' (inactivo {gap} min)'

    db.execute(
        """INSERT INTO log_actividad (turno_id, timestamp_cliente, accion, detalle, gap_minutos)
           VALUES (?, ?, ?, ?, ?)""",
        (turno_id, timestamp_cliente, accion, (detalle + gap_texto).strip(), gap),
    )
    db.commit()
    return gap


def _calcular_gap_minutos(ts_anterior: str, ts_actual: str) -> Optional[int]:
    """Calcula diferencia en minutos entre dos timestamps DD/MM/YYYY HH:MM."""
    from datetime import datetime as dt
    formatos = ['%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
    def _parse(s):
        for fmt in formatos:
            try:
                return dt.strptime(s.strip(), fmt)
            except ValueError:
                continue
        return None
    a, b = _parse(ts_anterior), _parse(ts_actual)
    if a and b:
        diff = (b - a).total_seconds() / 60
        return max(0, int(diff))
    return None


def obtener_log_actividad(db: sqlite3.Connection, turno_id: int) -> List[dict]:
    """Retorna log de actividad ordenado cronologicamente."""
    rows = db.execute(
        "SELECT * FROM log_actividad WHERE turno_id = ? ORDER BY id",
        (turno_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def guardar_vdp(db: sqlite3.Connection, turno_id: int, items: List[dict]):
    """Guarda VDP (ventas despues del peso). items: [{texto, gramos}]"""
    db.execute("DELETE FROM vdp_turno WHERE turno_id = ?", (turno_id,))
    for item in items:
        texto = (item.get('texto') or '').strip()
        if not texto:
            continue
        gramos = item.get('gramos', 0)
        try:
            gramos = int(gramos)
        except (ValueError, TypeError):
            gramos = 0
        db.execute(
            "INSERT INTO vdp_turno (turno_id, texto, gramos) VALUES (?, ?, ?)",
            (turno_id, texto, gramos),
        )
    db.execute("UPDATE turnos SET updated_at = datetime('now') WHERE id = ?", (turno_id,))
    db.commit()


def guardar_consumos(db: sqlite3.Connection, turno_id: int, items: List[dict]):
    """Guarda consumos internos. items: [{texto, gramos, empleado}]"""
    db.execute("DELETE FROM consumo_turno WHERE turno_id = ?", (turno_id,))
    for item in items:
        texto = (item.get('texto') or '').strip()
        if not texto:
            continue
        gramos = item.get('gramos', 0)
        try:
            gramos = int(gramos)
        except (ValueError, TypeError):
            gramos = 0
        empleado = (item.get('empleado') or '').strip() or None
        db.execute(
            "INSERT INTO consumo_turno (turno_id, texto, gramos, empleado) VALUES (?, ?, ?, ?)",
            (turno_id, texto, gramos, empleado),
        )
    db.execute("UPDATE turnos SET updated_at = datetime('now') WHERE id = ?", (turno_id,))
    db.commit()


def guardar_notas(db: sqlite3.Connection, turno_id: int, notas: List[dict]):
    """Guarda notas de caja. notas: [{categoria, detalle}]"""
    db.execute("DELETE FROM notas_turno WHERE turno_id = ?", (turno_id,))
    for nota in notas:
        cat = (nota.get('categoria') or '').strip()
        det = (nota.get('detalle') or '').strip()
        if not det:
            continue
        if cat not in ('novedad', 'reclamo', 'faltante', 'otro'):
            cat = 'otro'
        db.execute(
            "INSERT INTO notas_turno (turno_id, categoria, detalle) VALUES (?, ?, ?)",
            (turno_id, cat, det),
        )
    db.execute("UPDATE turnos SET updated_at = datetime('now') WHERE id = ?", (turno_id,))
    db.commit()
