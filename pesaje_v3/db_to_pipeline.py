"""
db_to_pipeline.py — Convierte registros de la DB a los modelos del pipeline.

Este es el puente entre la web de carga y el sistema de análisis.
Produce TurnoCrudo/DatosDia idénticos a los que genera capa1_parser
desde Excel. El pipeline (capa2-capa5) recibe estos objetos sin saber
si vinieron de un Excel o de la DB.

Contrato preservado:
- SaborCrudo.abierta: None = no registrado, 0 = explícito
- SaborCrudo.cerradas: List[int] (vacía si no hay)
- SaborCrudo.entrantes: List[int] (vacía si no hay)
- TurnoCrudo.nombre_hoja: derivado de fecha+tipo+modo
- DatosDia.contexto: ±3 turnos adyacentes
"""
import sqlite3
from typing import Optional, List, Dict

from .modelos import SaborCrudo, TurnoCrudo, DatosDia
from .db import get_db, derivar_nombre_hoja


def _row_to_sabor_crudo(row: dict) -> SaborCrudo:
    """Convierte una fila de sabores_turno a SaborCrudo."""
    cerradas = []
    for i in range(1, 7):
        v = row.get(f'cerrada_{i}')
        if v is not None:
            cerradas.append(int(v))

    entrantes = []
    for i in range(1, 3):
        v = row.get(f'entrante_{i}')
        if v is not None:
            entrantes.append(int(v))

    return SaborCrudo(
        nombre=row['nombre'],
        nombre_norm=row['nombre_norm'],
        abierta=row['abierta'],       # None o int — semántica preservada
        celiaca=row.get('celiaca'),
        cerradas=cerradas,
        entrantes=entrantes,
    )


def _turno_db_to_crudo(db: sqlite3.Connection, turno_id: int,
                        modo: str, indice: int = 0) -> Optional[TurnoCrudo]:
    """Convierte un turno de la DB a TurnoCrudo."""
    turno = db.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,)).fetchone()
    if not turno:
        return None

    sabores_rows = db.execute(
        "SELECT * FROM sabores_turno WHERE turno_id = ? ORDER BY nombre_norm",
        (turno_id,),
    ).fetchall()

    vdp_rows = db.execute(
        "SELECT texto FROM vdp_turno WHERE turno_id = ? ORDER BY id",
        (turno_id,),
    ).fetchall()

    nombre_hoja = derivar_nombre_hoja(turno['fecha'], turno['tipo_turno'], modo)

    tc = TurnoCrudo(
        nombre_hoja=nombre_hoja,
        indice=indice,
    )

    for row in sabores_rows:
        sabor = _row_to_sabor_crudo(dict(row))
        # Solo incluir si tiene al menos un dato (mismo filtro que el parser)
        if sabor.abierta is not None or sabor.celiaca is not None or sabor.cerradas or sabor.entrantes:
            tc.sabores[sabor.nombre_norm] = sabor

    tc.vdp_textos = [r['texto'] for r in vdp_rows]

    return tc


def armar_datos_dia(db: sqlite3.Connection, sucursal_id: int,
                     fecha: str, turnos_contexto: int = 3) -> Optional[DatosDia]:
    """
    Arma un DatosDia completo desde la DB para una fecha dada.

    Para DIA_NOCHE: busca turnos DIA y NOCHE del mismo día.
    Para TURNO_UNICO: busca turno de fecha anterior (referencia) + turno actual.
    Incluye contexto de ±turnos_contexto turnos adyacentes.
    """
    suc = db.execute("SELECT * FROM sucursales WHERE id = ?", (sucursal_id,)).fetchone()
    if not suc:
        return None
    modo = suc['modo']

    if modo == 'DIA_NOCHE':
        return _armar_dia_noche(db, sucursal_id, fecha, modo, turnos_contexto)
    else:
        return _armar_turno_unico(db, sucursal_id, fecha, modo, turnos_contexto)


def _armar_dia_noche(db, sucursal_id, fecha, modo, n_ctx):
    """Arma DatosDia para modo DIA_NOCHE."""
    t_dia = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno='DIA'",
        (sucursal_id, fecha),
    ).fetchone()
    t_noche = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno='NOCHE'",
        (sucursal_id, fecha),
    ).fetchone()

    if not t_dia or not t_noche:
        return None

    turno_dia = _turno_db_to_crudo(db, t_dia['id'], modo, indice=0)
    turno_noche = _turno_db_to_crudo(db, t_noche['id'], modo, indice=1)

    if not turno_dia or not turno_noche:
        return None

    # Contexto: turnos de fechas adyacentes
    contexto = _cargar_contexto(db, sucursal_id, fecha, modo, n_ctx,
                                 excluir_ids={t_dia['id'], t_noche['id']})

    # dia_label: el número del día
    from datetime import date
    dia_label = str(date.fromisoformat(fecha).day)

    return DatosDia(
        dia_label=dia_label,
        turno_dia=turno_dia,
        turno_noche=turno_noche,
        contexto=contexto,
        modo='DIA_NOCHE',
    )


def _armar_turno_unico(db, sucursal_id, fecha, modo, n_ctx):
    """Arma DatosDia para modo TURNO_UNICO.
    turno_dia = día anterior (referencia), turno_noche = día actual."""
    # Turno actual
    t_actual = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=?",
        (sucursal_id, fecha),
    ).fetchone()
    if not t_actual:
        return None

    # Turno anterior (referencia)
    t_anterior = db.execute(
        "SELECT id, fecha FROM turnos WHERE sucursal_id=? AND fecha<? ORDER BY fecha DESC LIMIT 1",
        (sucursal_id, fecha),
    ).fetchone()
    if not t_anterior:
        return None

    turno_dia = _turno_db_to_crudo(db, t_anterior['id'], modo, indice=0)
    turno_noche = _turno_db_to_crudo(db, t_actual['id'], modo, indice=1)

    if not turno_dia or not turno_noche:
        return None

    contexto = _cargar_contexto(db, sucursal_id, fecha, modo, n_ctx,
                                 excluir_ids={t_anterior['id'], t_actual['id']})

    from datetime import date
    dia_label = str(date.fromisoformat(fecha).day)

    return DatosDia(
        dia_label=dia_label,
        turno_dia=turno_dia,
        turno_noche=turno_noche,
        contexto=contexto,
        modo='TURNO_UNICO',
    )


def _cargar_contexto(db, sucursal_id, fecha, modo, n_ctx, excluir_ids):
    """Carga ±n_ctx turnos adyacentes como contexto para el pipeline."""
    rows = db.execute(
        """SELECT id, fecha, tipo_turno FROM turnos
           WHERE sucursal_id = ? ORDER BY fecha, tipo_turno""",
        (sucursal_id,),
    ).fetchall()

    contexto = []
    idx = 0
    for row in rows:
        if row['id'] in excluir_ids:
            continue
        tc = _turno_db_to_crudo(db, row['id'], modo, indice=idx)
        if tc and tc.sabores:
            contexto.append(tc)
            idx += 1

    # Limitar a los más cercanos a la fecha target
    # Ordenar por cercanía a fecha
    from datetime import date
    target = date.fromisoformat(fecha)
    contexto.sort(key=lambda tc: abs((date.fromisoformat(
        _fecha_de_nombre_hoja(tc.nombre_hoja, target)) - target).days))

    return contexto[:n_ctx * 2]  # ±n_ctx = hasta 2*n_ctx turnos


def _fecha_de_nombre_hoja(nombre_hoja: str, fallback) -> str:
    """Intenta extraer fecha del nombre_hoja. Si falla, usa fallback."""
    # nombre_hoja es "Jueves 3 (DIA)" o "Jueves 3"
    import re
    m = re.search(r'(\d+)', nombre_hoja)
    if m:
        day = int(m.group(1))
        return fallback.replace(day=min(day, 28)).isoformat()
    return fallback.isoformat()
