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
    for i in range(1, 7):
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
                     fecha: str, turnos_contexto: int = 6) -> Optional[DatosDia]:
    """
    Arma un DatosDia completo desde la DB para una fecha dada.

    Para DIA_NOCHE: busca turnos DIA y NOCHE del mismo día.
    Para TURNO_UNICO: busca turno de fecha anterior (referencia) + turno actual.
    Incluye contexto de ±turnos_contexto turnos adyacentes.
    """
    suc = db.execute("SELECT * FROM sucursales WHERE id = ?", (sucursal_id,)).fetchone()
    if not suc:
        return None

    # Buscar todos los turnos de esta fecha
    turnos_fecha = db.execute(
        "SELECT id, tipo_turno FROM turnos WHERE sucursal_id=? AND fecha=?",
        (sucursal_id, fecha),
    ).fetchall()
    tipos = {t['tipo_turno'] for t in turnos_fecha}

    # Estrategia flexible: probar en orden de preferencia
    # 1. DIA + NOCHE del mismo dia (si existen ambos)
    if 'DIA' in tipos and 'NOCHE' in tipos:
        r = _armar_dia_noche(db, sucursal_id, fecha, 'DIA_NOCHE', turnos_contexto)
        if r:
            return r

    # 2. UNICO + NOCHE del mismo dia (UNICO actúa como DIA)
    if 'UNICO' in tipos and 'NOCHE' in tipos:
        r = _armar_unico_noche(db, sucursal_id, fecha, 'DIA_NOCHE', turnos_contexto)
        if r:
            return r

    # 3. Turno unico: dia anterior + dia actual (cualquier tipo)
    r = _armar_turno_unico(db, sucursal_id, fecha, 'TURNO_UNICO', turnos_contexto)
    if r:
        return r

    return None


def _armar_unico_noche(db, sucursal_id, fecha, modo, n_ctx):
    """Arma DatosDia cuando hay UNICO+NOCHE el mismo dia.
    UNICO actúa como turno DIA (referencia), NOCHE como turno actual."""
    t_unico = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno='UNICO'",
        (sucursal_id, fecha),
    ).fetchone()
    t_noche = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? AND tipo_turno='NOCHE'",
        (sucursal_id, fecha),
    ).fetchone()

    if not t_unico or not t_noche:
        return None

    turno_dia = _turno_db_to_crudo(db, t_unico['id'], modo, indice=0)
    turno_noche = _turno_db_to_crudo(db, t_noche['id'], modo, indice=1)

    if not turno_dia or not turno_noche:
        return None

    contexto = _cargar_contexto(db, sucursal_id, fecha, modo, n_ctx,
                                 excluir_ids={t_unico['id'], t_noche['id']})

    from datetime import date
    dia_label = str(date.fromisoformat(fecha).day)

    return DatosDia(
        dia_label=dia_label,
        turno_dia=turno_dia,
        turno_noche=turno_noche,
        contexto=contexto,
        modo='DIA_NOCHE',
    )


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
    """Arma DatosDia comparando turno anterior vs turno actual.
    turno_dia = ultimo turno antes de esta fecha (referencia).
    turno_noche = turno mas reciente de esta fecha (actual).
    Funciona para TURNO_UNICO, y tambien como fallback para DIA_NOCHE
    cuando solo hay un turno del dia (compara con dia anterior)."""
    # Turno actual: el mas reciente de esta fecha
    t_actual = db.execute(
        "SELECT id FROM turnos WHERE sucursal_id=? AND fecha=? ORDER BY tipo_turno DESC LIMIT 1",
        (sucursal_id, fecha),
    ).fetchone()
    if not t_actual:
        return None

    # Turno anterior: el mas reciente antes de esta fecha
    t_anterior = db.execute(
        "SELECT id, fecha FROM turnos WHERE sucursal_id=? AND fecha<? ORDER BY fecha DESC, tipo_turno DESC LIMIT 1",
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
    """Carga turnos adyacentes como contexto para el pipeline.

    CRITICO: los indices deben reflejar el orden cronologico real.
    Turnos ANTES de la fecha target tienen indices < 0 (antes de turno_dia=0).
    Turnos DESPUES tienen indices > 1 (despues de turno_noche=1).
    El pipeline usa indice para distinguir backward (< turno_dia.indice)
    de forward (> turno_noche.indice).
    """
    from datetime import date as date_cls

    target = date_cls.fromisoformat(fecha)

    rows = db.execute(
        """SELECT id, fecha, tipo_turno FROM turnos
           WHERE sucursal_id = ? AND id NOT IN ({})
           ORDER BY fecha, tipo_turno""".format(
            ','.join(str(i) for i in excluir_ids) if excluir_ids else '0'
        ),
        (sucursal_id,),
    ).fetchall()

    # Separar en antes y despues de la fecha target
    antes = [r for r in rows if r['fecha'] < fecha]
    despues = [r for r in rows if r['fecha'] > fecha]

    # Los mas cercanos a la fecha, limitados a n_ctx por lado
    antes_cercanos = antes[-n_ctx:] if antes else []  # ultimos N antes
    despues_cercanos = despues[:n_ctx] if despues else []  # primeros N despues

    contexto = []

    # Antes: indices negativos descendentes (-1, -2, -3...)
    # El mas cercano tiene indice -1 (justo antes de turno_dia=0)
    for i, row in enumerate(reversed(antes_cercanos)):
        tc = _turno_db_to_crudo(db, row['id'], modo, indice=-(i + 1))
        if tc and tc.sabores:
            contexto.append(tc)

    # Despues: indices desde 2 en adelante (justo despues de turno_noche=1)
    for i, row in enumerate(despues_cercanos):
        tc = _turno_db_to_crudo(db, row['id'], modo, indice=i + 2)
        if tc and tc.sabores:
            contexto.append(tc)

    return contexto


# ═══════════════════════════════════════════════════════════════
# Carga batch: todos los días de un mes (replica cargar_todos_los_dias)
# ═══════════════════════════════════════════════════════════════

def cargar_todos_los_dias_db(db: sqlite3.Connection, sucursal_id: int,
                              mes: str) -> List[DatosDia]:
    """Replica cargar_todos_los_dias del parser pero leyendo de la DB.

    Soporta meses con modo mixto (DIA+NOCHE, UNICO+NOCHE, solo UNICO).
    Cada dia decide su propio modo:
    - DIA+NOCHE o UNICO+NOCHE: par dentro del mismo dia
    - Solo UNICO: par con turno anterior (TURNO_UNICO)

    Contexto por POSICION en la lista plana (+-3 turnos).

    Args:
        db: conexion SQLite
        sucursal_id: id de la sucursal
        mes: formato 'YYYY-MM' (ej: '2026-02')
    """
    from datetime import date as date_cls
    from collections import defaultdict

    # 1. Obtener todos los turnos del mes + últimos 6 del mes anterior (cross-mes)
    # Los turnos del mes anterior sirven como contexto backward para los
    # primeros días del mes, y como turno_dia para el primer par TURNO_UNICO.
    rows_mes = db.execute(
        """SELECT id, fecha, tipo_turno FROM turnos
           WHERE sucursal_id=? AND fecha LIKE ?
           ORDER BY fecha, tipo_turno""",
        (sucursal_id, f"{mes}%"),
    ).fetchall()
    if not rows_mes:
        return []

    # Turnos del mes anterior (últimos 6, suficientes para contexto ±3)
    primera_fecha = rows_mes[0]['fecha']
    rows_prev = db.execute(
        """SELECT id, fecha, tipo_turno FROM turnos
           WHERE sucursal_id=? AND fecha < ?
           ORDER BY fecha DESC, tipo_turno DESC LIMIT 6""",
        (sucursal_id, primera_fecha),
    ).fetchall()
    rows_prev = list(reversed(rows_prev))  # cronológico

    rows = rows_prev + list(rows_mes)
    n_prev = len(rows_prev)  # offset para saber qué turnos son del mes actual
    if not rows:
        return []

    # 2. Detectar modo predominante para nombre_hoja
    tipos = {r['tipo_turno'] for r in rows}
    tiene_pares = ('DIA' in tipos and 'NOCHE' in tipos) or ('UNICO' in tipos and 'NOCHE' in tipos)
    modo_hoja = 'DIA_NOCHE' if tiene_pares else 'TURNO_UNICO'

    # 3. Convertir todos a TurnoCrudo con indice posicional
    turnos_info = []
    for i, row in enumerate(rows):
        tc = _turno_db_to_crudo(db, row['id'], modo_hoja, indice=i)
        if tc:
            turnos_info.append((i, dict(row), tc))

    if not turnos_info:
        return []

    # Mapa posicion -> TurnoCrudo
    all_turnos = {idx: tc for idx, _, tc in turnos_info}
    total = len(rows)

    # 4. Agrupar por fecha (solo turnos del mes actual generan DatosDia;
    #    turnos previos participan solo como contexto en la lista plana)
    dias_dict = defaultdict(list)
    for idx, row, tc in turnos_info:
        dias_dict[row['fecha']].append((idx, row, tc))

    resultado = []
    fechas_usadas = set()
    fechas_mes = {row['fecha'] for row in rows_mes}  # solo fechas del mes pedido

    # 5a. Procesar pares DIA_NOCHE y UNICO_NOCHE
    for fecha in sorted(dias_dict.keys()):
        if fecha not in fechas_mes:
            continue  # turno del mes anterior, solo contexto
        entries = dias_dict[fecha]
        tipos_dia = {row['tipo_turno'] for _, row, _ in entries}

        dia_turno = noche_turno = None
        indices_par = []

        for idx, row, tc in entries:
            if row['tipo_turno'] == 'DIA':
                dia_turno = tc
                indices_par.append(idx)
            elif row['tipo_turno'] == 'NOCHE':
                noche_turno = tc
                indices_par.append(idx)
            elif row['tipo_turno'] == 'UNICO' and not dia_turno:
                # UNICO actua como DIA cuando hay NOCHE el mismo dia
                if 'NOCHE' in tipos_dia:
                    dia_turno = tc
                    indices_par.append(idx)

        if dia_turno and noche_turno:
            idx_min = max(0, min(indices_par) - 3)
            idx_max = min(total - 1, max(indices_par) + 3)
            contexto = [all_turnos[i] for i in range(idx_min, idx_max + 1)
                        if i in all_turnos and i not in indices_par]

            dia_label = str(date_cls.fromisoformat(fecha).day)
            resultado.append(DatosDia(
                dia_label=dia_label,
                turno_dia=dia_turno,
                turno_noche=noche_turno,
                contexto=contexto,
                modo='DIA_NOCHE',
            ))
            fechas_usadas.add(fecha)

    # 5b. Procesar turnos sueltos como TURNO_UNICO (pares consecutivos)
    # Incluye turnos del mes anterior como posible turno_dia (referencia).
    # Solo genera DatosDia cuando turno_b es del mes actual.
    sueltos = []
    for fecha in sorted(dias_dict.keys()):
        if fecha in fechas_usadas:
            continue
        for idx, row, tc in dias_dict[fecha]:
            if tc.sabores:
                sueltos.append((idx, row, tc))

    for j in range(len(sueltos) - 1):
        idx_a, row_a, turno_a = sueltos[j]
        idx_b, row_b, turno_b = sueltos[j + 1]

        # Solo generar DatosDia si turno_b es del mes pedido
        if row_b['fecha'] not in fechas_mes:
            continue

        dia_label = str(date_cls.fromisoformat(row_b['fecha']).day)

        idx_min = max(0, idx_a - 3)
        idx_max = min(total - 1, idx_b + 3)
        contexto = [all_turnos[i] for i in range(idx_min, idx_max + 1)
                    if i in all_turnos and i != idx_a and i != idx_b]

        resultado.append(DatosDia(
            dia_label=dia_label,
            turno_dia=turno_a,
            turno_noche=turno_b,
            contexto=contexto,
            modo='TURNO_UNICO',
        ))

    return resultado


def _todos_dia_noche_db(turnos_info, total):
    """Modo DIA/NOCHE: agrupar por fecha, buscar par DIA+NOCHE.

    Contexto = ±3 por posición en la lista plana (replica parser
    _todos_los_dias_dia_noche, capa1_parser.py:307-341).
    """
    from datetime import date as date_cls

    # Agrupar por fecha
    dias_dict = {}
    for idx, row, tc in turnos_info:
        fecha = row['fecha']
        if fecha not in dias_dict:
            dias_dict[fecha] = {'turnos': [], 'indices': [], 'rows': []}
        dias_dict[fecha]['turnos'].append(tc)
        dias_dict[fecha]['indices'].append(idx)
        dias_dict[fecha]['rows'].append(row)

    # Mapa posición → TurnoCrudo para contexto rápido
    all_turnos = {idx: tc for idx, _, tc in turnos_info}

    resultado = []
    for fecha, info in dias_dict.items():
        dia_turno = noche_turno = None
        for tc, row in zip(info['turnos'], info['rows']):
            if row['tipo_turno'] == 'DIA':
                dia_turno = tc
            elif row['tipo_turno'] == 'NOCHE':
                noche_turno = tc
            elif row['tipo_turno'] == 'UNICO' and not dia_turno:
                # UNICO actúa como DIA cuando hay NOCHE el mismo día
                dia_turno = tc

        if not dia_turno or not noche_turno:
            continue

        # Contexto: ±3 por posición en lista plana (como parser)
        idx_min = max(0, min(info['indices']) - 3)
        idx_max = min(total - 1, max(info['indices']) + 3)
        contexto = [all_turnos[i] for i in range(idx_min, idx_max + 1)
                    if i in all_turnos and i not in info['indices']]

        dia_label = str(date_cls.fromisoformat(fecha).day)
        resultado.append(DatosDia(
            dia_label=dia_label,
            turno_dia=dia_turno,
            turno_noche=noche_turno,
            contexto=contexto,
            modo='DIA_NOCHE',
        ))

    return resultado


def _todos_turno_unico_db(turnos_info, total):
    """Modo turno unico: pares consecutivos (A=referencia, B=venta).

    Contexto = ±3 por posición en la lista plana (replica parser
    _todos_los_dias_turno_unico, capa1_parser.py:344-373).
    """
    from datetime import date as date_cls

    # Filtrar turnos sin sabores (equivalente a es_vacio en parser)
    validos = [(idx, row, tc) for idx, row, tc in turnos_info if tc.sabores]
    all_turnos = {idx: tc for idx, _, tc in turnos_info}

    resultado = []
    for j in range(len(validos) - 1):
        idx_a, row_a, turno_a = validos[j]
        idx_b, row_b, turno_b = validos[j + 1]

        # Venta pertenece al día B
        dia_label = str(date_cls.fromisoformat(row_b['fecha']).day)

        # Contexto: ±3 por posición
        idx_min = max(0, idx_a - 3)
        idx_max = min(total - 1, idx_b + 3)
        contexto = [all_turnos[i] for i in range(idx_min, idx_max + 1)
                    if i in all_turnos and i != idx_a and i != idx_b]

        resultado.append(DatosDia(
            dia_label=dia_label,
            turno_dia=turno_a,
            turno_noche=turno_b,
            contexto=contexto,
            modo='TURNO_UNICO',
        ))

    return resultado
