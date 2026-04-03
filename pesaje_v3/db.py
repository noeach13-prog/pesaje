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

    # Migration: agregar columna pin si no existe (DB creada antes de este cambio)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sucursales)").fetchall()]
    if 'pin' not in cols:
        conn.execute("ALTER TABLE sucursales ADD COLUMN pin TEXT NOT NULL DEFAULT '0000'")

    # Semilla: sucursales conocidas con PIN de acceso
    for nombre, modo, pin in [
        ('San Martín', 'DIA_NOCHE', '1234'),
        ('Triunvirato', 'TURNO_UNICO', '5678'),
        ('Unión', 'TURNO_UNICO', '9012'),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO sucursales (nombre, modo, pin) VALUES (?, ?, ?)",
            (nombre, modo, pin),
        )
        # Actualizar PIN si sucursal ya existía sin PIN
        conn.execute(
            "UPDATE sucursales SET pin = ? WHERE nombre = ? AND pin = '0000'",
            (pin, nombre),
        )
    conn.commit()
    conn.close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sucursales (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    modo TEXT NOT NULL DEFAULT 'DIA_NOCHE',
    pin TEXT NOT NULL DEFAULT '0000',
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
    gramos INTEGER NOT NULL
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

    return {
        'turno': dict(turno),
        'sabores': [dict(s) for s in sabores],
        'sucursal': dict(sucursal),
        'nombre_hoja': derivar_nombre_hoja(
            turno['fecha'], turno['tipo_turno'], sucursal['modo']
        ),
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
