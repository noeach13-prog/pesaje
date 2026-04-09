"""
db.py — Capa de persistencia dual SQLite/PostgreSQL.

Tres reglas de diseño:
1. nombre_hoja es DERIVADO de (fecha, tipo_turno, modo), no dato soberano.
2. updated_at desde el primer día — sin rastro temporal no hay auditoría.
3. Las validaciones de campo se repiten server-side aunque el client las haga.

Dual dialect:
- Sin DATABASE_URL → SQLite local (dev)
- Con DATABASE_URL → PostgreSQL (Railway prod)
"""
import os
import sqlite3
import re
from datetime import date, datetime
from typing import Optional, List, Dict, Any

# Importar normalize_name del parser existente — NO reimplementar
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parser import normalize_name

_DB_PATH = os.environ.get('PESAJE_DB', os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'pesaje.db'
))
_DATABASE_URL = os.environ.get('DATABASE_URL', '')

_DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _to_dict(row):
    """Convierte una fila de DB a dict con valores serializables.
    Postgres retorna datetime objects; los convertimos a string."""
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
    return d


def _is_postgres():
    return bool(_DATABASE_URL)


# ─── Conexión dual ────────────────────────────────────────────────

def _pg_row_to_dict(row):
    """Convierte un row de RealDictCursor a dict con datetime→string."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif hasattr(v, 'isoformat'):  # date objects
            d[k] = v.isoformat()
    return d


class _PgCursorWrapper:
    """Wrapper de cursor Postgres que convierte datetime a string en resultados."""

    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return _pg_row_to_dict(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        return [_pg_row_to_dict(r) for r in rows]

    @property
    def lastrowid(self):
        return getattr(self._cur, 'lastrowid', None)

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description


class DBConn:
    """Wrapper que expone la misma interfaz para SQLite y PostgreSQL.

    No usa replace mágico de '?' a '%s'. Cada dialecto tiene su propio
    formato de parametrización, manejado por el wrapper.
    """

    def __init__(self, conn, is_pg=False):
        self._conn = conn
        self.is_pg = is_pg

    def execute(self, sql, params=None):
        if self.is_pg:
            sql_pg = _translate_sql(sql)
            import psycopg2.extras
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql_pg, params or ())
            return _PgCursorWrapper(cur)
        else:
            return self._conn.execute(sql, params or ())

    def executescript(self, sql):
        if self.is_pg:
            self._conn.cursor().execute(sql)
            self._conn.commit()
        else:
            self._conn.executescript(sql)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    @property
    def row_factory(self):
        if not self.is_pg:
            return self._conn.row_factory
        return None

    @row_factory.setter
    def row_factory(self, val):
        if not self.is_pg:
            self._conn.row_factory = val


def _translate_sql(sql):
    """Traduce SQL de SQLite a PostgreSQL.

    Solo traduce lo traducible de forma segura:
    - ? → %s (placeholders)
    - INSERT OR IGNORE INTO → INSERT INTO (caller debe manejar ON CONFLICT)
    - datetime('now') → CURRENT_TIMESTAMP

    NO traduce INSERT OR REPLACE — eso requiere intención explícita
    (ON CONFLICT con target y columnas). Cada query OR REPLACE debe
    resolverse manualmente en db.py.
    """
    import re
    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    if re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", sql, flags=re.IGNORECASE):
        sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)
        # Append ON CONFLICT DO NOTHING after the last )
        sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    # datetime('now') → CURRENT_TIMESTAMP (con o sin paréntesis envolventes)
    sql = re.sub(r"\(datetime\s*\(\s*'now'\s*\)\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"datetime\s*\(\s*'now'\s*\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)

    # Placeholders: ? → %s (respetando strings)
    result = []
    in_string = False
    quote_char = None
    for ch in sql:
        if in_string:
            result.append(ch)
            if ch == quote_char:
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            quote_char = ch
            result.append(ch)
        elif ch == '?':
            result.append('%s')
        else:
            result.append(ch)
    return ''.join(result)


def get_db() -> DBConn:
    """Retorna conexión wrapeada. SQLite local o PostgreSQL según entorno."""
    if _is_postgres():
        import psycopg2
        url = _DATABASE_URL
        # Railway a veces da postgres:// en vez de postgresql://
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(url, sslmode='require')
        conn.autocommit = False
        return DBConn(conn, is_pg=True)
    else:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return DBConn(conn, is_pg=False)


def _get_schema():
    """Retorna schema SQL adaptado al dialecto actual."""
    if _is_postgres():
        # Postgres: SERIAL, CURRENT_TIMESTAMP, ON CONFLICT
        schema = _SCHEMA.replace(
            'INTEGER PRIMARY KEY,', 'SERIAL PRIMARY KEY,'
        ).replace(
            "(datetime('now'))", 'CURRENT_TIMESTAMP'
        ).replace(
            "datetime('now')", 'CURRENT_TIMESTAMP'
        ).replace(
            'INSERT OR IGNORE', 'INSERT INTO'
        )
        return schema
    return _SCHEMA


def _col_exists(conn, table, column):
    """Verifica si una columna existe en una tabla (dual dialect)."""
    if conn.is_pg:
        row = conn.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name=? AND column_name=?",
            (table, column)
        ).fetchone()
        return row is not None
    else:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return column in cols


def init_db():
    """Crea tablas si no existen. Idempotente. Migra schema si faltan columnas."""
    conn = get_db()

    if conn.is_pg:
        # Postgres: ejecutar cada CREATE TABLE por separado
        schema = _get_schema()
        for stmt in schema.split(';'):
            stmt = stmt.strip()
            if stmt and stmt.upper().startswith('CREATE'):
                try:
                    conn.execute(stmt)
                except Exception:
                    conn._conn.rollback()  # tabla ya existe, seguir
        conn.commit()
    else:
        conn.executescript(_SCHEMA)

    # Migrations
    if not _col_exists(conn, 'sucursales', 'pin'):
        conn.execute("ALTER TABLE sucursales ADD COLUMN pin TEXT NOT NULL DEFAULT '0000'")
    if not _col_exists(conn, 'sucursales', 'pin_supervisor'):
        conn.execute("ALTER TABLE sucursales ADD COLUMN pin_supervisor TEXT NOT NULL DEFAULT '0000'")
    if not _col_exists(conn, 'turnos', 'inicio_carga'):
        conn.execute("ALTER TABLE turnos ADD COLUMN inicio_carga TEXT")
    if not _col_exists(conn, 'turnos', 'fin_carga'):
        conn.execute("ALTER TABLE turnos ADD COLUMN fin_carga TEXT")
    if _col_exists(conn, 'consumo_turno', 'texto') and not _col_exists(conn, 'consumo_turno', 'empleado'):
        conn.execute("ALTER TABLE consumo_turno ADD COLUMN empleado TEXT")

    # Migración: recrear stock_insumos con snapshot_id
    try:
        conn.execute("DROP TABLE IF EXISTS stock_inventario")
        conn.execute("DROP TABLE IF EXISTS stock_insumos")
        conn.commit()
    except Exception:
        try:
            conn._conn.rollback()
        except Exception:
            pass

    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS stock_insumos (
            id %s,
            sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
            fecha TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            seccion TEXT NOT NULL,
            item TEXT NOT NULL,
            cantidad TEXT,
            registrado_por TEXT,
            created_at TEXT NOT NULL DEFAULT %s
        )""" % ('SERIAL PRIMARY KEY' if conn.is_pg else 'INTEGER PRIMARY KEY',
                'CURRENT_TIMESTAMP' if conn.is_pg else "(datetime('now'))"))
        conn.commit()
    except Exception:
        try:
            conn._conn.rollback()
        except Exception:
            pass

    # Crear postres_turno si no existe
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS postres_turno (
            id %s,
            turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 0,
            UNIQUE(turno_id, producto)
        )""" % ('SERIAL PRIMARY KEY' if conn.is_pg else 'INTEGER PRIMARY KEY'))
        conn.commit()
    except Exception:
        try:
            conn._conn.rollback()
        except Exception:
            pass

    conn.commit()

    # Migración: agregar columnas entrante_3..6 si no existen
    for i in range(3, 7):
        col = f'entrante_{i}'
        if not _col_exists(conn, 'sabores_turno', col):
            try:
                conn.execute(f"ALTER TABLE sabores_turno ADD COLUMN {col} INTEGER")
                conn.commit()
            except Exception:
                try: conn._conn.rollback()
                except: pass

    # Semilla: sucursales con PIN empleado + PIN supervisor
    _SUCURSALES = [
        ('San Martín', 'DIA_NOCHE', '1234', '2512'),
        ('Triunvirato', 'TURNO_UNICO', '5678', '2512'),
        ('Unión', 'TURNO_UNICO', '9012', '2512'),
        ('San Miguel', 'DIA_NOCHE', '3456', '2512'),
        ('Florida', 'DIA_NOCHE', '7890', '2512'),
    ]
    for nombre, modo, pin, pin_sup in _SUCURSALES:
        if conn.is_pg:
            conn.execute(
                """INSERT INTO sucursales (nombre, modo, pin, pin_supervisor)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT (nombre) DO UPDATE SET pin = EXCLUDED.pin, pin_supervisor = EXCLUDED.pin_supervisor""",
                (nombre, modo, pin, pin_sup),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO sucursales (nombre, modo, pin, pin_supervisor) VALUES (?, ?, ?, ?)",
                (nombre, modo, pin, pin_sup),
            )
            conn.execute(
                "UPDATE sucursales SET pin = ?, pin_supervisor = ? WHERE nombre = ?",
                (pin, pin_sup, nombre),
            )

    # Limpieza unica: borrar turnos viejos
    if conn.is_pg:
        conn.execute("CREATE TABLE IF NOT EXISTS _flags (key TEXT PRIMARY KEY, val TEXT)")
    else:
        conn.execute("CREATE TABLE IF NOT EXISTS _flags (key TEXT PRIMARY KEY, val TEXT)")
    conn.commit()
    flag = conn.execute("SELECT 1 FROM _flags WHERE key=?", ('LIMPIEZA_2026_04',)).fetchone()
    if not flag:
        for tbl in ['ajustes_manuales', 'log_actividad', 'postres_turno', 'notas_turno',
                     'consumo_turno', 'vdp_turno', 'sabores_turno', 'turnos']:
            conn.execute(f"DELETE FROM {tbl}")
        if conn.is_pg:
            conn.execute("INSERT INTO _flags (key, val) VALUES (?, CURRENT_TIMESTAMP)", ('LIMPIEZA_2026_04',))
        else:
            conn.execute("INSERT INTO _flags (key, val) VALUES (?, datetime('now'))", ('LIMPIEZA_2026_04',))

    # Semilla: catálogo de sabores por sucursal
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
    row = conn.execute("SELECT COUNT(*) as n FROM catalogo_sabores").fetchone()
    count = row['n'] if conn.is_pg else row[0]
    if count > 0:
        return  # ya sembrado

    rows = conn.execute("SELECT id, nombre FROM sucursales").fetchall()
    sucursales = {r['nombre']: r['id'] for r in rows} if conn.is_pg else {r[1]: r[0] for r in rows}
    for suc_nombre, suc_id in sucursales.items():
        sabores = list(_SABORES_BASE)
        sabores.extend(_SABORES_EXTRA.get(suc_nombre, []))
        for s in sorted(set(sabores)):
            if conn.is_pg:
                conn.execute(
                    "INSERT INTO catalogo_sabores (sucursal_id, nombre_norm) VALUES (?, ?) ON CONFLICT DO NOTHING",
                    (suc_id, s),
                )
            else:
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
    entrante_1 INTEGER, entrante_2 INTEGER, entrante_3 INTEGER,
    entrante_4 INTEGER, entrante_5 INTEGER, entrante_6 INTEGER,
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

CREATE TABLE IF NOT EXISTS ajustes_manuales (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    nombre_norm TEXT NOT NULL,
    venta_pipeline INTEGER NOT NULL,
    status_pipeline TEXT NOT NULL,
    venta_manual INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'otro'
        CHECK(categoria IN ('omision_cerrada','entrante_no_registrado','error_pesaje',
                            'apertura_no_detectada','duplicado_no_detectado','otro')),
    supervisor TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(turno_id, nombre_norm)
);

CREATE TABLE IF NOT EXISTS stock_insumos (
    id INTEGER PRIMARY KEY,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    fecha TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    seccion TEXT NOT NULL,
    item TEXT NOT NULL,
    cantidad TEXT,
    registrado_por TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS postres_turno (
    id INTEGER PRIMARY KEY,
    turno_id INTEGER NOT NULL REFERENCES turnos(id) ON DELETE CASCADE,
    producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    UNIQUE(turno_id, producto)
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

    for i in range(1, 7):
        err = validar_peso(row.get(f'entrante_{i}'))
        if err:
            errores.append(f'entrante_{i}: {err}')

    # Al menos un campo con dato
    tiene_dato = any(
        row.get(c) is not None and row.get(c) != ''
        for c in ['abierta', 'celiaca'] +
                 [f'cerrada_{i}' for i in range(1, 7)] +
                 [f'entrante_{i}' for i in range(1, 7)]
    )
    if not tiene_dato:
        errores.append('Sabor sin ningun peso registrado')

    return errores


# ─── CRUD ────────────────────────────────────────────────────────────

def crear_turno(db, sucursal_id: int, fecha: str,
                tipo_turno: str, ingresado_por: str = None) -> int:
    """Crea un turno vacío en estado borrador. Retorna turno.id."""
    if hasattr(db, 'is_pg') and db.is_pg:
        cur = db.execute(
            """INSERT INTO turnos (sucursal_id, fecha, tipo_turno, ingresado_por)
               VALUES (?, ?, ?, ?) RETURNING id""",
            (sucursal_id, fecha, tipo_turno, ingresado_por),
        )
        row = cur.fetchone()
        db.commit()
        return row['id']
    else:
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
            """INSERT INTO sabores_turno
               (turno_id, nombre, nombre_norm, abierta, celiaca,
                cerrada_1, cerrada_2, cerrada_3, cerrada_4, cerrada_5, cerrada_6,
                entrante_1, entrante_2, entrante_3, entrante_4, entrante_5, entrante_6)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                turno_id, nombre, nombre_norm,
                _int_or_none(row.get('abierta')),
                _int_or_none(row.get('celiaca')),
                *[_int_or_none(row.get(f'cerrada_{i}')) for i in range(1, 7)],
                *[_int_or_none(row.get(f'entrante_{i}')) for i in range(1, 7)],
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

    # Verificar que tenga al menos 1 sabor con datos REALES (no solo filas vacias)
    row = db.execute(
        """SELECT COUNT(*) as n FROM sabores_turno WHERE turno_id = ?
           AND (abierta IS NOT NULL OR celiaca IS NOT NULL
                OR cerrada_1 IS NOT NULL OR cerrada_2 IS NOT NULL
                OR cerrada_3 IS NOT NULL OR cerrada_4 IS NOT NULL
                OR cerrada_5 IS NOT NULL OR cerrada_6 IS NOT NULL
                OR entrante_1 IS NOT NULL OR entrante_2 IS NOT NULL
                OR entrante_3 IS NOT NULL OR entrante_4 IS NOT NULL
                OR entrante_5 IS NOT NULL OR entrante_6 IS NOT NULL)""",
        (turno_id,)
    ).fetchone()
    n_sabores = row['n'] if isinstance(row, dict) else row[0]
    if n_sabores == 0:
        return {'ok': False, 'error': 'No hay sabores con pesos cargados. Cargar al menos un sabor antes de confirmar.'}

    db.execute(
        """UPDATE turnos SET estado = 'confirmado', fin_carga = ?,
           confirmado_por = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (timestamp_cliente, confirmado_por, turno_id),
    )
    db.commit()

    # Resumen
    row_peso = db.execute(
        """SELECT COALESCE(SUM(
            COALESCE(abierta,0)+COALESCE(celiaca,0)+
            COALESCE(cerrada_1,0)+COALESCE(cerrada_2,0)+COALESCE(cerrada_3,0)+
            COALESCE(cerrada_4,0)+COALESCE(cerrada_5,0)+COALESCE(cerrada_6,0)+
            COALESCE(entrante_1,0)+COALESCE(entrante_2,0)+
            COALESCE(entrante_3,0)+COALESCE(entrante_4,0)+
            COALESCE(entrante_5,0)+COALESCE(entrante_6,0)
        ), 0) as total FROM sabores_turno WHERE turno_id = ?""",
        (turno_id,),
    ).fetchone()
    total_peso = row_peso['total'] if isinstance(row_peso, dict) else row_peso[0]

    row_nvdp = db.execute("SELECT COUNT(*) as n FROM vdp_turno WHERE turno_id=?", (turno_id,)).fetchone()
    n_vdp = row_nvdp['n'] if isinstance(row_nvdp, dict) else row_nvdp[0]
    row_tvdp = db.execute("SELECT COALESCE(SUM(gramos),0) as total FROM vdp_turno WHERE turno_id=?", (turno_id,)).fetchone()
    total_vdp = row_tvdp['total'] if isinstance(row_tvdp, dict) else row_tvdp[0]

    return {
        'ok': True,
        'n_sabores': n_sabores,
        'total_peso': total_peso,
        'n_vdp': n_vdp,
        'total_vdp': total_vdp,
        'inicio_carga': turno['inicio_carga'],
        'fin_carga': timestamp_cliente,
    }


def borrar_turno(db: sqlite3.Connection, turno_id: int,
                  pin_supervisor: str) -> dict:
    """Borra un turno y todos sus datos. Requiere PIN de supervisor."""
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return {'ok': False, 'error': 'Turno no encontrado'}

    suc = db.execute(
        "SELECT pin_supervisor FROM sucursales WHERE id = ?",
        (turno['sucursal_id'],),
    ).fetchone()
    if not suc or suc['pin_supervisor'] != pin_supervisor.strip():
        return {'ok': False, 'error': 'PIN de supervisor incorrecto'}

    # CASCADE borra sabores_turno, vdp_turno, consumo_turno, notas_turno, log_actividad
    db.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    db.commit()
    return {'ok': True}


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

    postres = db.execute(
        "SELECT * FROM postres_turno WHERE turno_id = ? ORDER BY producto", (turno_id,)
    ).fetchall()

    return {
        'turno': _to_dict(turno),
        'sabores': [_to_dict(s) for s in sabores],
        'sucursal': _to_dict(sucursal),
        'nombre_hoja': derivar_nombre_hoja(
            turno['fecha'], turno['tipo_turno'], sucursal['modo']
        ),
        'vdp': [dict(v) for v in vdp],
        'consumos': [dict(c) for c in consumos],
        'notas': [dict(n) for n in notas],
        'postres': [dict(p) for p in postres],
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
    return [_to_dict(r) for r in rows]


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
    return [_to_dict(r) for r in rows]


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
    return [_to_dict(r) for r in rows]


# ─── Postres ──────────────────────────────────────────────────────

CATALOGO_POSTRES = [
    'BALDE 2 LITROS', 'BALDE 4 LITROS', 'ALMENDRADO 1400CC', 'MIXTO 1400CC',
    'BOMBON ESCOCES X 6 UN', 'SEMIFRIO CHOCO AMOR', 'SEMIFRIO AMOR TIRANO',
    'TORTA FRUTILLA', 'TORTA PRIMAVERA', 'TORTA COOKIES', 'TORTA CHOCOTORTA',
    'TORTA BOSQUE', 'ALMENDRADO X 20 PORC.', 'MIXTO X 20 PORC.',
    'BOMBON X 18 UNI', 'GIO FRUTILLA', 'GIO FRAMBUEZA', 'GIO MORA',
    'GIO PISTACHO', 'ALFAJOR HELADO', 'PALETAS',
]


# ─── Stock / Inventario de insumos (solo anotación, no afecta análisis) ─────

CATALOGO_STOCK = {
    'TERMICOS': ['1/4', '1/2', 'KG', '1/4 CON LOGO', '1/8 CON LOGO'],
    'SALSAS': ['CHOCOLATE', 'CARAMELO', 'DULCE DE LECHE', 'FRUTILLA', 'FRUTOS DEL BOSQUE'],
    'VASOS Y CUCURUCHOS': ['CONO 70', 'MINI CUCURUCHON', 'VASO 65', 'BLISTER CUCURUCHO X3',
                            'BLISTER VASITOS X5', 'VASO MILKSHAKE', 'TAPA MILKSHAKE', 'SORBETES MILKSHAKE'],
    'BEBIDAS E INSUMOS': ['CREMA DE LECHE', 'LECHE (LITROS)'],
    'BOLSAS': ['CAMISETA CHICA', 'CAMISETA MEDIANA', 'CAMISETA GRANDE'],
    'CUCHARITAS Y SERVILLETAS': ['SERVILLETAS ZIGZAG', 'CUCHARITAS TE', 'SUNDAE',
                                  'CINTA LOGO', 'FOLEX', 'ROLLO COMUN', 'ROLLO POSNET',
                                  'CARTUCHO IMPRESORA', 'ROLLO IMPRESORA DE PEDIDOS'],
    'LIMPIEZA': ['LIMPIAVIDRIOS', 'JABON EN BARRA', 'DESODORANTE PARA PISO CONCENTRADO',
                  'ALCOHOL EN GEL', 'REJILLAS', 'JABON LIQUIDO PARA MANOS',
                  'CIF CREMA', 'LAVANDINA', 'DETERGENTE', 'PAPEL HIGIENICO',
                  'TRAPO DE PISOS', 'ESPONJAS/VIRULANAS'],
}


def guardar_stock(db, sucursal_id: int, fecha: str, items: List[dict],
                   registrado_por: str = ''):
    """Guarda snapshot de inventario. Cada guardado es un registro nuevo, no sobreescribe."""
    import uuid
    snapshot_id = str(uuid.uuid4())[:8]  # ID corto unico por snapshot
    for row in items:
        item = (row.get('item') or '').strip()
        if not item:
            continue
        cantidad = (row.get('cantidad') or '').strip()
        if not cantidad:
            continue
        seccion = (row.get('seccion') or '').strip()
        db.execute(
            "INSERT INTO stock_insumos (sucursal_id, fecha, snapshot_id, seccion, item, cantidad, registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sucursal_id, fecha, snapshot_id, seccion, item, cantidad, registrado_por),
        )
    db.commit()
    return snapshot_id


def obtener_stock(db, sucursal_id: int, snapshot_id: str) -> List[dict]:
    """Retorna items de un snapshot especifico."""
    rows = db.execute(
        "SELECT * FROM stock_insumos WHERE sucursal_id = ? AND snapshot_id = ? ORDER BY seccion, item",
        (sucursal_id, snapshot_id),
    ).fetchall()
    return [_to_dict(r) for r in rows]


def obtener_ultimo_stock(db, sucursal_id: int, fecha: str) -> List[dict]:
    """Retorna el snapshot mas reciente de una fecha (para precargar)."""
    row = db.execute(
        """SELECT snapshot_id FROM stock_insumos
           WHERE sucursal_id = ? AND fecha = ?
           ORDER BY created_at DESC LIMIT 1""",
        (sucursal_id, fecha),
    ).fetchone()
    if not row:
        return []
    return obtener_stock(db, sucursal_id, row['snapshot_id'])


def listar_stocks(db, sucursal_id: int) -> List[dict]:
    """Lista todos los snapshots de stock."""
    rows = db.execute(
        """SELECT snapshot_id, fecha, COUNT(*) as n_items,
                  MAX(registrado_por) as registrado_por, MAX(created_at) as ultima
           FROM stock_insumos WHERE sucursal_id = ?
           GROUP BY snapshot_id, fecha ORDER BY MAX(created_at) DESC""",
        (sucursal_id,),
    ).fetchall()
    return [_to_dict(r) for r in rows]


def guardar_postres(db, turno_id: int, postres: List[dict]):
    """Guarda postres de un turno. postres: [{producto, cantidad}]"""
    db.execute("DELETE FROM postres_turno WHERE turno_id = ?", (turno_id,))
    for p in postres:
        producto = (p.get('producto') or '').strip()
        if not producto:
            continue
        cantidad = p.get('cantidad', 0)
        try:
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            cantidad = 0
        if cantidad <= 0:
            continue
        db.execute(
            "INSERT INTO postres_turno (turno_id, producto, cantidad) VALUES (?, ?, ?)",
            (turno_id, producto, cantidad),
        )
    db.execute("UPDATE turnos SET updated_at = datetime('now') WHERE id = ?", (turno_id,))
    db.commit()


def obtener_postres(db, turno_id: int) -> List[dict]:
    """Retorna postres de un turno."""
    rows = db.execute(
        "SELECT * FROM postres_turno WHERE turno_id = ? ORDER BY producto",
        (turno_id,),
    ).fetchall()
    return [_to_dict(r) for r in rows]


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
