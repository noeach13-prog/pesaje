"""
test_regresion.py -- Cerrojos constitucionales del refactor Capa 3.

Tres familias:
  A) assert_invariantes_sabor: combinaciones ilegales de estado
  B) Snapshots de regresion: D5, D27, D28 normalizados
  C) Tests de especificacion futura: xfail hasta que el refactor los resuelva

Ejecutar: python -m pytest pesaje_v3/test_regresion.py -v
"""
import pytest
import json
import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pesaje_v3.modelos import (
    StatusC3, SaborClasificado, SaborContable, PrototipoAplicado,
    ResultadoC3, FlagC3,
)

EXCEL = os.path.join(os.path.expanduser('~'), 'Downloads', 'Febrero San Martin 2026.xlsx')
BASELINE = os.path.join(os.path.dirname(__file__), 'baseline_snapshots.json')


# ===================================================================
# A) INVARIANTES — combinaciones ilegales
# ===================================================================

class InvariantError(Exception):
    """Violacion de invariante constitucional. No es un assert: explota en ejecucion."""
    pass


def assert_invariantes_sabor(sc: SaborClasificado, strict: bool = True):
    """
    Verifica invariantes del SaborClasificado.
    strict=True: raise InvariantError (para shadow mode y ejecucion)
    strict=False: usa assert (para tests)

    Esta funcion es valida DURANTE LA TRANSICION (campos nuevos opcionales).
    Cuando resolution_status es None, solo valida las reglas legacy.
    """
    def check(condition, msg):
        if not condition:
            if strict:
                raise InvariantError(f'{sc.nombre_norm}: {msg}')
            else:
                assert False, f'{sc.nombre_norm}: {msg}'

    # --- Reglas legacy (siempre validas) ---

    # Si hay prototipo, debe tener campos basicos
    if sc.prototipo is not None:
        check(sc.prototipo.codigo != '', 'prototipo sin codigo')
        check(sc.venta_final_c3 is not None, 'prototipo presente pero venta_final_c3 is None')

    # LIMPIO/ENGINE sin prototipo -> venta_final_c3 debe ser numerico
    if sc.status in (StatusC3.LIMPIO, StatusC3.ENGINE) and sc.prototipo is None:
        check(sc.venta_final_c3 is not None, f'status={sc.status.value} sin venta_final_c3')

    # SENAL/COMPUESTO sin prototipo -> escala a C4, venta_final_c3 is None
    if sc.status in (StatusC3.SENAL, StatusC3.COMPUESTO) and sc.prototipo is None:
        check(sc.venta_final_c3 is None,
              f'status={sc.status.value} sin prototipo pero con venta_final_c3={sc.venta_final_c3}')

    # OBSERVACION es estado muerto
    check(sc.status != StatusC3.OBSERVACION,
          'OBSERVACION es estado muerto, no debe aparecer')

    # --- Reglas nuevas (solo si resolution_status existe) ---
    resolution = getattr(sc, 'resolution_status', None)
    decision = getattr(sc, 'decision', None)
    screening = getattr(sc, 'screening_status', None)

    if resolution is None:
        return  # transicion: campos nuevos aun no poblados

    # decision debe existir si resolution_status existe
    check(decision is not None, 'resolution_status sin decision')

    if decision is not None:
        # decision.resolucion debe coincidir con resolution_status
        check(decision.resolucion == resolution,
              f'decision.resolucion={decision.resolucion} != resolution_status={resolution}')

    # screening_status debe coincidir con status mientras convivan
    if screening is not None:
        check(screening == sc.status,
              f'screening_status={screening} != status={sc.status}')

    # Tabla de estados legales
    from pesaje_v3.modelos import ResolucionC3

    if resolution == ResolucionC3.RAW_VALIDO:
        check(sc.status in (StatusC3.LIMPIO, StatusC3.ENGINE),
              f'RAW_VALIDO con status={sc.status.value}')
        check(sc.prototipo is None, 'RAW_VALIDO con prototipo')
        check(sc.venta_final_c3 is not None, 'RAW_VALIDO sin venta_final_c3')
        if decision:
            check(decision.hipotesis_ganadora is None, 'RAW_VALIDO con hipotesis_ganadora')

    elif resolution == ResolucionC3.NO_CALCULABLE:
        check(sc.status in (StatusC3.SOLO_DIA, StatusC3.SOLO_NOCHE),
              f'NO_CALCULABLE con status={sc.status.value}')
        check(sc.prototipo is None, 'NO_CALCULABLE con prototipo')
        check(sc.venta_final_c3 is None, 'NO_CALCULABLE con venta_final_c3 numerico (cero es mentira)')
        if decision:
            check(decision.hipotesis_ganadora is None, 'NO_CALCULABLE con hipotesis_ganadora')

    elif resolution in (ResolucionC3.CORREGIDO_C3, ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA):
        check(sc.status in (StatusC3.SENAL, StatusC3.COMPUESTO),
              f'CORREGIDO con status={sc.status.value} (screening debe seguir siendo sospechoso)')
        check(sc.prototipo is not None, 'CORREGIDO sin prototipo (rompe contrato con C4)')
        check(sc.venta_final_c3 is not None, 'CORREGIDO sin venta_final_c3')
        if decision:
            check(decision.hipotesis_ganadora is not None, 'CORREGIDO sin hipotesis_ganadora')

    elif resolution == ResolucionC3.ESCALAR_C4:
        check(sc.status in (StatusC3.SENAL, StatusC3.COMPUESTO, StatusC3.ESCALAR),
              f'ESCALAR_C4 con status={sc.status.value}')
        check(sc.prototipo is None, 'ESCALAR_C4 con prototipo')
        if decision:
            check(decision.hipotesis_ganadora is None,
                  'ESCALAR_C4 con hipotesis_ganadora (en esta transicion, canal legacy no lo soporta)')


def assert_invariantes_resultado(c3: ResultadoC3):
    """Verifica invariantes de TODO el resultado C3."""
    for nombre, sc in c3.sabores.items():
        assert_invariantes_sabor(sc, strict=False)


# ===================================================================
# B) SNAPSHOTS DE REGRESION
# ===================================================================

def _cargar_baseline():
    with open(BASELINE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _correr_pipeline(dia: int):
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import canonicalizar_nombres, aplicar_canonicalizacion, clasificar
    from pesaje_v3.capa4_expediente import resolver_escalados

    datos = cargar_dia(EXCEL, dia)
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)
    c3 = clasificar(datos, cont)
    c4 = resolver_escalados(datos, cont, c3)
    return datos, cont, c3, c4


def _normalizar_snapshot(c3, c4, cont):
    """Produce snapshot normalizado comparable con baseline."""
    sabores = {}
    for nombre in sorted(c3.sabores.keys()):
        sc = c3.sabores[nombre]
        entry = {
            'status': sc.status.value,
            'venta_final_c3': sc.venta_final_c3,
            'prototipo': None,
        }
        if sc.prototipo:
            entry['prototipo'] = {'codigo': sc.prototipo.codigo, 'delta': sc.prototipo.delta}
        sabores[nombre] = entry

    escalados_detail = {}
    for nombre in sorted(c3.escalados.keys()):
        sc = c3.escalados[nombre]
        escalados_detail[nombre] = {
            'status': sc.status.value,
            'flags': sorted([f.codigo for f in sc.flags]),
            'prototipo_is_none': sc.prototipo is None,
        }

    correcciones = sorted(
        [{'nombre': c.nombre_norm, 'delta': c.delta, 'banda': c.banda.value} for c in c4.correcciones],
        key=lambda x: x['nombre']
    )

    return {
        'venta_raw_total': cont.venta_raw_total,
        'vdp_total': cont.vdp_total,
        'sabores': sabores,
        'escalados': escalados_detail,
        'correcciones_c4': correcciones,
        'sin_resolver': sorted(c4.sin_resolver),
    }


@pytest.fixture(scope='module')
def baseline():
    return _cargar_baseline()


@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_snapshot_sabores(baseline, dia):
    """Cada sabor debe tener mismo status, venta_final_c3 y prototipo."""
    _, cont, c3, c4 = _correr_pipeline(dia)
    actual = _normalizar_snapshot(c3, c4, cont)
    esperado = baseline[str(dia)]

    for nombre in sorted(set(list(actual['sabores'].keys()) + list(esperado['sabores'].keys()))):
        act = actual['sabores'].get(nombre)
        exp = esperado['sabores'].get(nombre)
        assert act == exp, f'D{dia} {nombre}: actual={act} != esperado={exp}'


@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_snapshot_escalados(baseline, dia):
    """Mismo set de escalados con mismo status, flags y prototipo_is_none."""
    _, cont, c3, c4 = _correr_pipeline(dia)
    actual = _normalizar_snapshot(c3, c4, cont)
    esperado = baseline[str(dia)]

    assert actual['escalados'] == esperado['escalados'], \
        f'D{dia} escalados differ: actual={list(actual["escalados"].keys())} esperado={list(esperado["escalados"].keys())}'


@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_snapshot_correcciones_c4(baseline, dia):
    """Mismas correcciones C4 (nombre, delta, banda)."""
    _, cont, c3, c4 = _correr_pipeline(dia)
    actual = _normalizar_snapshot(c3, c4, cont)
    esperado = baseline[str(dia)]

    assert actual['correcciones_c4'] == esperado['correcciones_c4'], \
        f'D{dia} correcciones C4 differ'


@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_snapshot_totales(baseline, dia):
    """venta_raw_total y vdp_total deben coincidir."""
    _, cont, c3, c4 = _correr_pipeline(dia)
    actual = _normalizar_snapshot(c3, c4, cont)
    esperado = baseline[str(dia)]

    assert actual['venta_raw_total'] == esperado['venta_raw_total'], \
        f'D{dia} venta_raw_total: {actual["venta_raw_total"]} != {esperado["venta_raw_total"]}'
    assert actual['vdp_total'] == esperado['vdp_total']


@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_integracion_c4_mismos_expedientes(baseline, dia):
    """C4 debe abrir los mismos expedientes (3 ejes de equivalencia)."""
    _, cont, c3, c4 = _correr_pipeline(dia)
    actual = _normalizar_snapshot(c3, c4, cont)
    esperado = baseline[str(dia)]

    # Eje 1: mismo conjunto de nombres escalados
    assert sorted(actual['escalados'].keys()) == sorted(esperado['escalados'].keys()), \
        f'D{dia} eje 1: set de escalados difiere'

    # Eje 2: mismo motivo estructural (status + flags)
    for nombre in esperado['escalados']:
        if nombre in actual['escalados']:
            assert actual['escalados'][nombre]['status'] == esperado['escalados'][nombre]['status'], \
                f'D{dia} eje 2: {nombre} status difiere'
            assert actual['escalados'][nombre]['flags'] == esperado['escalados'][nombre]['flags'], \
                f'D{dia} eje 2: {nombre} flags difieren'

    # Eje 3: misma disponibilidad de prototipo
    for nombre in esperado['escalados']:
        if nombre in actual['escalados']:
            assert actual['escalados'][nombre]['prototipo_is_none'] == esperado['escalados'][nombre]['prototipo_is_none'], \
                f'D{dia} eje 3: {nombre} prototipo_is_none difiere'


# ===================================================================
# C) TESTS DE ESPECIFICACION FUTURA (xfail)
# ===================================================================

def test_colision_alias():
    """Turno con KITKAT y KIT KAT simultaneos debe reportar COLISION_IDENTIDAD."""
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia
    # Fabricar turno con colision
    turno = TurnoCrudo(nombre_hoja='Test DIA', indice=0, sabores={
        'KITKAT': SaborCrudo(nombre='KitKat', nombre_norm='KITKAT', abierta=3000, celiaca=None),
        'KIT KAT': SaborCrudo(nombre='Kit Kat', nombre_norm='KIT KAT', abierta=2500, celiaca=None),
    })
    datos = DatosDia(dia_label='test', turno_dia=turno,
                     turno_noche=TurnoCrudo(nombre_hoja='Test NOCHE', indice=1))

    # canonicalizar debe detectar la colision
    from pesaje_v3.capa3_motor import canonicalizar_nombres, aplicar_canonicalizacion
    canon = canonicalizar_nombres(datos)

    # El test pasa si: (1) colision detectada Y (2) ambos sabores sobreviven
    assert canon.tiene_colisiones, \
        f'canonicalizar_nombres no detecto la colision. aliases={canon.aliases_aplicados}'

    warnings = aplicar_canonicalizacion(datos, canon)

    assert len(datos.turno_dia.sabores) == 2, \
        f'Colision: se piso un sabor. Quedan {len(datos.turno_dia.sabores)}: {list(datos.turno_dia.sabores.keys())}'
    assert any('COLISION_IDENTIDAD' in w for w in warnings), \
        f'No se emitio warning de colision. warnings={warnings}'


def test_pf1_dual_offset():
    """PF1 con cerrada que matchea +300 y +1000 debe generar 2 hipotesis."""
    from pesaje_v3.modelos import (
        SaborCrudo, TurnoCrudo, DatosDia, SaborContable,
        ObservacionC3, FlagC3,
    )
    from pesaje_v3.generadores_c3 import generar_hipotesis_pf1

    # Fabricar: cerrada DIA=6700, historial tiene 7000 (3 sightings) y 7700 (4 sightings)
    # offset +300 -> 7000, offset +1000 -> 7700
    turno_dia = TurnoCrudo(nombre_hoja='Test DIA', indice=0, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=3000, celiaca=None,
                           cerradas=[6700]),
    })
    turno_noche = TurnoCrudo(nombre_hoja='Test NOCHE', indice=1, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=2500, celiaca=None,
                           cerradas=[]),
    })
    # Contexto con sightings para ambos offsets
    ctx = []
    for i, peso in [(2, 7000), (3, 7000), (4, 7000), (5, 7700), (6, 7700), (7, 7700), (8, 7700)]:
        ctx.append(TurnoCrudo(nombre_hoja=f'CTX{i}', indice=i, sabores={
            'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=2000, celiaca=None,
                               cerradas=[peso]),
        }))

    datos = DatosDia(dia_label='test', turno_dia=turno_dia, turno_noche=turno_noche, contexto=ctx)
    sc = SaborContable(nombre_norm='TEST', nombre_display='Test',
                       total_a=9700, total_b=2500, new_ent_b=0,
                       n_cerr_a=1, n_cerr_b=0, n_latas=1, ajuste_latas=280, venta_raw=6920)
    obs = ObservacionC3(nombre_norm='TEST')
    flags = [FlagC3('C4d:6700', 4, 'cerr DIA 6700 sin match')]

    hipotesis = generar_hipotesis_pf1('TEST', sc, datos, obs, flags)

    assert len(hipotesis) >= 2, \
        f'PF1 deberia generar >=2 hipotesis, genero {len(hipotesis)}: {[h.descripcion for h in hipotesis]}'

    offsets_encontrados = set()
    for h in hipotesis:
        h.target.validar()
        h.validar()
        offsets_encontrados.add(h.target.peso_propuesto)

    assert 7000 in offsets_encontrados, '7000 (offset +300) deberia estar'
    assert 7700 in offsets_encontrados, '7700 (offset +1000) deberia estar'


def test_pf7_cadena_custodia():
    """PF7 debe tener cadena de custodia formal: fuentes tipadas, reconciliacion explicita si difieren."""
    from pesaje_v3.modelos import (
        SaborCrudo, TurnoCrudo, DatosDia, SaborContable,
        ObservacionC3, FlagC3, TipoFuente,
    )
    from pesaje_v3.generadores_c3 import generar_hipotesis_pf7

    # Fabricar: ab DIA=4000, ab NOCHE=4500 (sube sin apertura)
    # Forward ab=4100 (NOCHE cercana a forward -> DIA es error)
    # Backward ab=3900
    turno_dia = TurnoCrudo(nombre_hoja='Test DIA', indice=5, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=4000, celiaca=None,
                           cerradas=[6500]),
    })
    turno_noche = TurnoCrudo(nombre_hoja='Test NOCHE', indice=6, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=4500, celiaca=None,
                           cerradas=[6500]),
    })
    ctx = [
        TurnoCrudo(nombre_hoja='Prev', indice=4, sabores={
            'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=3900, celiaca=None, cerradas=[6500]),
        }),
        TurnoCrudo(nombre_hoja='Next', indice=7, sabores={
            'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=4100, celiaca=None, cerradas=[6500]),
        }),
    ]
    datos = DatosDia(dia_label='test', turno_dia=turno_dia, turno_noche=turno_noche, contexto=ctx)
    sc = SaborContable(nombre_norm='TEST', nombre_display='Test',
                       total_a=10500, total_b=11000, new_ent_b=0,
                       n_cerr_a=1, n_cerr_b=1, n_latas=0, ajuste_latas=0, venta_raw=-500)
    obs = ObservacionC3(nombre_norm='TEST', ab_d=4000, ab_n=4500, ab_delta=500,
                        forward_ab=4100, backward_ab=3900,
                        forward_turno='Next', backward_turno='Prev')
    flags = [FlagC3('AB_UP', 3, 'ab sube')]

    hipotesis = generar_hipotesis_pf7('TEST', sc, datos, obs, flags)

    assert len(hipotesis) == 1, f'PF7 deberia generar 1 hipotesis, genero {len(hipotesis)}'
    h = hipotesis[0]

    # Validar invariantes formales
    h.target.validar()
    h.validar()

    # La cadena de custodia debe existir con tipos formales
    assert h.fuente_decision.tipo is not None, 'fuente_decision sin tipo'
    assert h.fuente_correccion.tipo is not None, 'fuente_correccion sin tipo'

    # Si fuentes difieren, reconciliacion debe ser explicita
    if h.fuente_decision.tipo != h.fuente_correccion.tipo:
        assert h.reconciliacion_explicita, \
            f'Fuentes difieren ({h.fuente_decision.tipo} vs {h.fuente_correccion.tipo}) pero reconciliacion_explicita=False'
        assert h.motivo_reconciliacion, 'reconciliacion explicita sin motivo'


def test_calidad_hueco_temporal():
    """Abierta identica en turnos idx=3 e idx=7 NO debe marcar copia consecutiva."""
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia

    # Fabricar: turno 3 y turno 7 con ab=4000, sin turnos 4-6
    turnos_contexto = [
        TurnoCrudo(nombre_hoja='T3', indice=3, sabores={
            'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=4000, celiaca=None)
        }),
    ]
    turno_dia = TurnoCrudo(nombre_hoja='T7 DIA', indice=7, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=4000, celiaca=None)
    })
    turno_noche = TurnoCrudo(nombre_hoja='T7 NOCHE', indice=8, sabores={
        'TEST': SaborCrudo(nombre='Test', nombre_norm='TEST', abierta=3500, celiaca=None)
    })
    datos = DatosDia(dia_label='test', turno_dia=turno_dia, turno_noche=turno_noche,
                     contexto=turnos_contexto)

    from pesaje_v3.capa3_motor import _evaluar_calidad
    marcas = _evaluar_calidad('TEST', datos)

    # Turnos idx=3 e idx=7 NO son adyacentes. No deberia marcar copia.
    for m in marcas:
        assert m.tipo != 'COPIA_POSIBLE_LEVE', \
            f'Falso positivo: marcado como copia entre turnos no adyacentes (idx 3 y 7)'
        assert m.tipo != 'COPIA_POSIBLE_FUERTE', \
            f'Falso positivo: marcado como copia fuerte entre turnos no adyacentes'


# ===================================================================
# D) JURISPRUDENCIA DEL ARBITRO
# ===================================================================

def test_arbitro_descarta_incoherente_antes_de_contar__cookies_d25():
    """
    CASO CONCRETO: COOKIES D25.
    PF1 (error digito 5705->6705, 7 sightings) y PF4 (omision cerr 6715)
    compiten. PF4 produce venta=-5570g (fisicamente absurda).
    El arbitro debe descartar PF4 por incoherencia material y resolver con PF1.
    No debe escalar por multiblanco.
    """
    _, cont, c3, c4 = _correr_pipeline(25)

    cookies = c3.sabores.get('COOKIES')
    assert cookies is not None, 'COOKIES no aparece en D25'

    # COOKIES debe estar resuelta en C3 (no escalada)
    assert cookies.prototipo is not None, \
        'COOKIES D25 no fue resuelta en C3 — el arbitro volvio a escalar'
    assert cookies.prototipo.codigo == 'PF1', \
        f'COOKIES D25 resuelta con {cookies.prototipo.codigo}, esperaba PF1'
    assert cookies.prototipo.delta == -1000, \
        f'COOKIES D25 delta={cookies.prototipo.delta}, esperaba -1000 (error digito NOCHE 5705->6705)'

    # La venta corregida debe ser razonable (positiva, no absurda)
    assert cookies.venta_final_c3 is not None
    assert cookies.venta_final_c3 >= 0, \
        f'COOKIES D25 venta_final_c3={cookies.venta_final_c3} negativa'
    assert cookies.venta_final_c3 < 2000, \
        f'COOKIES D25 venta_final_c3={cookies.venta_final_c3} demasiado alta'

    # COOKIES no debe aparecer en escalados ni en sin_resolver de C4
    assert 'COOKIES' not in c3.escalados, 'COOKIES aparece en escalados (no fue resuelta)'
    assert 'COOKIES' not in c4.sin_resolver, 'COOKIES aparece en sin_resolver de C4'


def test_arbitro_regla_coherencia_material():
    """
    REGLA GENERAL: cuando dos hipotesis compiten y una produce venta
    fisicamente absurda (< -300g), el arbitro debe descartarla por
    incoherencia material ANTES de evaluar si hay conflicto.

    El bug que esta regla fija: el arbitro contaba hipotesis antes de
    juzgar si merecian contar. Dos hipotesis = multiblanco = escalar,
    sin importar que una fuera absurda.

    La ley nueva: primero se juzga coherencia, despues se cuentan
    los que merecen ser contados.
    """
    from pesaje_v3.modelos import (
        HipotesisCorreccion, TargetCorreccion, ObservacionC3,
        SlotCerrada, LadoError, CampoAfectado, OperacionCorreccion,
        MecanismoCausal, FuenteEvidencia, TipoFuente,
        DecisionC3, ResolucionC3, MotivoDecisionC3,
    )
    from pesaje_v3.arbitro_c3 import resolver_hipotesis

    obs = ObservacionC3(nombre_norm='TEST', total_a=10000, total_b=9000, venta_raw=1000)
    _fuente = FuenteEvidencia(tipo=TipoFuente.SIGHTINGS, detalle='test')

    # Hipotesis A: coherente (venta corregida = 500g, razonable)
    h_coherente = HipotesisCorreccion(
        codigo_pf='PF1',
        descripcion='Error digito test',
        confianza=0.92,
        delta_venta=-500,
        venta_propuesta=500,
        target=TargetCorreccion(
            lado=LadoError.NOCHE, campo=CampoAfectado.CERRADA,
            operacion=OperacionCorreccion.SUSTITUIR,
            slot_cerrada=SlotCerrada(peso=5000, turno='NOCHE', indice_slot=0),
            peso_propuesto=5500),
        mecanismo_causal=MecanismoCausal.ERROR_DIGITO,
        fuente_decision=_fuente, fuente_correccion=_fuente,
        evidencias=['7 sightings'],
        contradicciones=[],
    )

    # Hipotesis B: incoherente (venta corregida = -5000g, absurda)
    h_absurda = HipotesisCorreccion(
        codigo_pf='PF4',
        descripcion='Omision cerr test',
        confianza=0.85,
        delta_venta=-6000,
        venta_propuesta=-5000,
        target=TargetCorreccion(
            lado=LadoError.DIA, campo=CampoAfectado.CERRADA,
            operacion=OperacionCorreccion.AGREGAR,
            peso_propuesto=6000),
        mecanismo_causal=MecanismoCausal.OMISION,
        fuente_decision=_fuente, fuente_correccion=_fuente,
        evidencias=['4 sightings'],
        contradicciones=[],
    )

    decision = resolver_hipotesis([h_coherente, h_absurda], obs, [])

    # La regla: NO debe escalar por multiblanco
    assert decision.resolucion != ResolucionC3.ESCALAR_C4, \
        f'El arbitro escalo por multiblanco en vez de descartar la hipotesis absurda. ' \
        f'motivo={decision.motivo_codigo}'

    # Debe resolver con la hipotesis coherente
    assert decision.resolucion in (ResolucionC3.CORREGIDO_C3, ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA), \
        f'El arbitro no resolvio. resolucion={decision.resolucion}'
    assert decision.hipotesis_ganadora is not None, 'Sin hipotesis ganadora'
    assert decision.hipotesis_ganadora.codigo_pf == 'PF1', \
        f'Gano {decision.hipotesis_ganadora.codigo_pf} en vez de PF1'

    # PF4 debe haber sido descartada (no simplemente derrotada por confianza)
    assert h_absurda in decision.hipotesis_descartadas, \
        'PF4 no aparece en hipotesis_descartadas — fue derrotada por confianza, no por coherencia'


def test_arbitro_coherencia_no_filtra_cuando_ambas_razonables():
    """
    CONTRA-TEST: si ambas hipotesis producen venta razonable,
    la coherencia no debe eliminar ninguna. El conflicto es genuino.
    """
    from pesaje_v3.modelos import (
        HipotesisCorreccion, TargetCorreccion, ObservacionC3,
        SlotCerrada, LadoError, CampoAfectado, OperacionCorreccion,
        MecanismoCausal, FuenteEvidencia, TipoFuente,
        DecisionC3, ResolucionC3,
    )
    from pesaje_v3.arbitro_c3 import resolver_hipotesis

    obs = ObservacionC3(nombre_norm='TEST', total_a=10000, total_b=9000, venta_raw=1000)
    _fuente = FuenteEvidencia(tipo=TipoFuente.SIGHTINGS, detalle='test')

    h_a = HipotesisCorreccion(
        codigo_pf='PF4',
        descripcion='Hipotesis A razonable',
        confianza=0.85,
        delta_venta=-200,
        venta_propuesta=800,
        target=TargetCorreccion(
            lado=LadoError.NOCHE, campo=CampoAfectado.CERRADA,
            operacion=OperacionCorreccion.SUSTITUIR,
            slot_cerrada=SlotCerrada(peso=6000, turno='NOCHE', indice_slot=0),
            peso_propuesto=6200),
        mecanismo_causal=MecanismoCausal.OMISION,
        fuente_decision=_fuente, fuente_correccion=_fuente,
        evidencias=['3 sightings'],
        contradicciones=[],
    )

    h_b = HipotesisCorreccion(
        codigo_pf='PF5',
        descripcion='Hipotesis B razonable',
        confianza=0.85,
        delta_venta=300,
        venta_propuesta=1300,
        target=TargetCorreccion(
            lado=LadoError.DIA, campo=CampoAfectado.CERRADA,
            operacion=OperacionCorreccion.AGREGAR,
            peso_propuesto=6500),
        mecanismo_causal=MecanismoCausal.OMISION,
        fuente_decision=_fuente, fuente_correccion=_fuente,
        evidencias=['4 sightings'],
        contradicciones=[],
    )

    decision = resolver_hipotesis([h_a, h_b], obs, [])

    # Ambas razonables, misma confianza, ninguna es PF1 → conflicto genuino → escalar
    assert decision.resolucion == ResolucionC3.ESCALAR_C4, \
        f'El arbitro no escalo ante conflicto genuino. resolucion={decision.resolucion}'


# ===================================================================
# E-bis) MATCHING UNIFICADO — Capa 3 y Capa 4 usan la misma funcion
# ===================================================================

@pytest.mark.parametrize('dia', [5, 12, 25, 27, 28])
def test_matching_consistencia_c3_c4(dia):
    """
    Capa 3 (_observar) y Capa 4 (_paso2_plano2) deben producir el mismo
    set de cerradas unmatched, porque ambas usan matching.match_cerradas.
    """
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import canonicalizar_nombres, aplicar_canonicalizacion, _observar
    from pesaje_v3.capa4_expediente import _paso1_timeline, _paso2_plano2

    datos = cargar_dia(EXCEL, dia)
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)

    for nombre, sc in cont.sabores.items():
        if sc.solo_dia or sc.solo_noche:
            continue

        obs = _observar(nombre, sc, datos)
        timeline = _paso1_timeline(nombre, datos)
        p2 = _paso2_plano2(nombre, datos, timeline)

        # Extraer pesos unmatched de Capa 3
        c3_unm_dia = sorted(s.peso for s in obs.cerradas_unmatched_dia)
        c3_unm_noche = sorted(s.peso for s in obs.cerradas_unmatched_noche)

        # Extraer pesos unmatched de Capa 4
        c4_unm_dia = sorted(p for p, _ in p2.desaparecen)
        c4_unm_noche = sorted(p for p, _ in p2.aparecen)

        assert c3_unm_dia == c4_unm_dia, \
            f'D{dia} {nombre}: unmatched DIA difiere. C3={c3_unm_dia} C4={c4_unm_dia}'
        assert c3_unm_noche == c4_unm_noche, \
            f'D{dia} {nombre}: unmatched NOCHE difiere. C3={c3_unm_noche} C4={c4_unm_noche}'


# ===================================================================
# E) GUARDIA BILATERAL — Capa 4
# ===================================================================

def test_bilateral_sambayon_d28_resuelto_por_composicion():
    """
    CASO CONCRETO: SAMBAYON D28.
    cerr DIA [6450, 6675] -> cerr NOCHE [6575].
    - 6450 fue abierta en D27 (lifecycle: REAPARICION_SOSPECHOSA) -> GENEALOGIA con entrante 6575
    - 6675 es phantom (1 sighting, sin historia)
    Composicion: GENEALOGIA(6450->6575, +125) + PHANTOM(6675, -6675) = -6550
    Venta final = 555g (venta pura de abierta 6235->5680).
    """
    _, cont, c3, c4 = _correr_pipeline(28)

    samb_corr = next((c for c in c4.correcciones if c.nombre_norm == 'SAMBAYON'), None)
    assert samb_corr is not None, \
        'SAMBAYON D28 no fue resuelto — deberia resolverse por composicion'
    assert 'COMPOSICION' in samb_corr.motivo, \
        f'SAMBAYON D28 resuelto por {samb_corr.motivo[:40]}, esperaba COMPOSICION'
    # CONTINUIDAD_MISMATCH_LEVE reemplaza GENEALOGIA cuando 6450↔6575 (125g)
    # son la misma lata con varianza de pesaje + conteo 2→1
    assert 'CONTINUIDAD_MISMATCH_LEVE' in samb_corr.motivo or 'GENEALOGIA_ENT_CERR' in samb_corr.motivo, \
        f'SAMBAYON D28 debe incluir CONTINUIDAD o GENEALOGIA en composicion'
    assert 'PHANTOM_DIA' in samb_corr.motivo, \
        f'SAMBAYON D28 debe incluir PHANTOM_DIA en composicion'
    assert samb_corr.venta_corregida == 555, \
        f'SAMBAYON D28 venta={samb_corr.venta_corregida}, esperaba 555 (venta pura ab)'


def test_bilateral_no_veta_phantom_limpio():
    """
    CONTRA-TEST: PHANTOM_DIA limpio (sin mismatch rival del mismo episodio)
    debe seguir resolviendose normalmente.
    """
    from pesaje_v3.capa4_expediente import (
        Hipotesis, PlanoP2, _paso5_seleccionar,
    )
    from pesaje_v3.modelos import SaborContable

    sc = SaborContable(
        nombre_norm='TEST', nombre_display='Test',
        total_a=10000, total_b=4000, new_ent_b=0,
        n_cerr_a=1, n_cerr_b=0, n_latas=1, ajuste_latas=280,
        venta_raw=5720,
    )
    p2 = PlanoP2(
        cerr_a=[6500], cerr_b=[],
        desaparecen=[(6500, 1)],
        aparecen=[],
        persisten=[],
    )

    # PHANTOM_DIA con convergencia (P1+P2), sin mismatch rival
    phantom = Hipotesis(
        tipo='PHANTOM_DIA', peso=6500,
        accion='Eliminar cerr 6500', delta_stock=-6500, delta_latas=-1,
        planos_favor=['P1', 'P2'], planos_contra=[], sightings=1,
    )

    hips = [phantom]
    mejor = _paso5_seleccionar(hips, sc, p2)

    assert mejor is not None, 'PHANTOM limpio sin mismatch rival deberia resolverse'
    assert mejor.tipo == 'PHANTOM_DIA'


def test_bilateral_mismatch_incoherente_no_veta():
    """
    BORDE: un MISMATCH_LEVE que fue descartado por incoherencia fisica
    (planos_contra no vacio) NO debe vetar una unilateral valida.
    La guardia solo aplica para mismatch viable (sin contra).
    """
    from pesaje_v3.capa4_expediente import (
        Hipotesis, PlanoP2, _paso5_seleccionar,
    )
    from pesaje_v3.modelos import SaborContable

    sc = SaborContable(
        nombre_norm='TEST', nombre_display='Test',
        total_a=15000, total_b=8000, new_ent_b=0,
        n_cerr_a=2, n_cerr_b=1, n_latas=1, ajuste_latas=280,
        venta_raw=6720,
    )
    p2 = PlanoP2(
        cerr_a=[6500, 6700], cerr_b=[6600],
        desaparecen=[(6500, 1), (6700, 3)],
        aparecen=[(6600, 2)],
        persisten=[],
    )

    # PHANTOM_DIA de 6700 con convergencia
    phantom = Hipotesis(
        tipo='PHANTOM_DIA', peso=6700,
        accion='Eliminar cerr 6700', delta_stock=-6700, delta_latas=-1,
        planos_favor=['P1', 'P2'], planos_contra=[], sightings=1,
    )

    # MISMATCH_LEVE de 6500->6600 pero CON contra (incoherente)
    mismatch = Hipotesis(
        tipo='MISMATCH_LEVE', peso=6500,
        accion='Ajuste 6500->6600', delta_stock=-100, delta_latas=0,
        planos_favor=['P2'], planos_contra=['COHERENCIA_HIGH'], sightings=2,
    )

    hips = [phantom, mismatch]
    mejor = _paso5_seleccionar(hips, sc, p2)

    # El mismatch tiene contra -> no es viable -> no debe vetar phantom
    assert mejor is not None, \
        'PHANTOM deberia resolverse porque el mismatch rival fue descartado por incoherencia'
    assert mejor.tipo == 'PHANTOM_DIA'


# ===================================================================
# F) PFIT_MASIVO — hipótesis compuesta bajo patrón colectivo
# ===================================================================

EXCEL_TRIUNVIRATO = os.path.join(os.path.expanduser('~'), 'Downloads', 'Febrero Triunvirato 2026.xlsx')


def _fabricar_datos_pfit(cerradas_dia, entrantes_dia, cerradas_previo=None,
                         cerradas_siguiente=None, venta_raw=None, cerradas_noche=None):
    """
    Fabrica un DatosDia mínimo para tests PFIT.
    turno_DIA tiene cerradas + entrantes dados.
    turno_NOCHE tiene cerradas_noche (default: vacío) y sin entrantes.
    contexto: un turno previo y/o uno siguiente si se proveen.
    cerradas_noche: permite simular qué cerradas persisten en NOCHE para tests
    de condición 4 de PFIT_MASIVO_AMBIGU.
    """
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia, SaborContable
    nombre = 'TEST'

    noche_cerradas = cerradas_noche if cerradas_noche is not None else []
    turno_dia = TurnoCrudo(nombre_hoja='T_DIA', indice=5, sabores={
        nombre: SaborCrudo(nombre=nombre, nombre_norm=nombre, abierta=3000, celiaca=None,
                           cerradas=cerradas_dia, entrantes=entrantes_dia),
    })
    turno_noche = TurnoCrudo(nombre_hoja='T_NOCHE', indice=6, sabores={
        nombre: SaborCrudo(nombre=nombre, nombre_norm=nombre, abierta=2800, celiaca=None,
                           cerradas=noche_cerradas, entrantes=[]),
    })
    ctx = []
    if cerradas_previo is not None:
        ctx.append(TurnoCrudo(nombre_hoja='T_PREV', indice=4, sabores={
            nombre: SaborCrudo(nombre=nombre, nombre_norm=nombre, abierta=3100, celiaca=None,
                               cerradas=cerradas_previo, entrantes=[]),
        }))
    if cerradas_siguiente is not None:
        ctx.append(TurnoCrudo(nombre_hoja='T_NEXT', indice=7, sabores={
            nombre: SaborCrudo(nombre=nombre, nombre_norm=nombre, abierta=2700, celiaca=None,
                               cerradas=cerradas_siguiente, entrantes=[]),
        }))

    datos = DatosDia(dia_label='test', turno_dia=turno_dia, turno_noche=turno_noche, contexto=ctx)
    total_a = 3000 + sum(cerradas_dia) + sum(entrantes_dia)
    total_b = 2800
    raw = venta_raw if venta_raw is not None else total_a - total_b
    sc = SaborContable(
        nombre_norm=nombre, nombre_display=nombre,
        total_a=total_a, total_b=total_b, new_ent_b=0,
        n_cerr_a=len(cerradas_dia), n_cerr_b=0, n_latas=0, ajuste_latas=0,
        venta_raw=raw,
    )
    from pesaje_v3.modelos import ObservacionC3, FlagC3
    obs = ObservacionC3(nombre_norm=nombre, venta_raw=raw)
    flags = [FlagC3('HIGH', 2, f'raw={raw}g')]
    return nombre, datos, sc, obs, flags


def test_pfit_masivo_positivo_ch_amores_d14():
    """
    CASO CONCRETO: CH AMORES D14 Triunvirato.
    Dos entrantes (~6485g, ~6760g) coinciden con dos cerradas del mismo turno.
    Los pares son no conflictivos (pesos bien separados, ±100g no se cruzan).
    Con turno_masivo=True → debe generarse UNA hipótesis PFIT_MASIVO,
    no dos hipótesis PFIT individuales.
    El delta debe ser la suma de ambos entrantes (negativo).
    """
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import (
        canonicalizar_nombres, aplicar_canonicalizacion,
        _observar, _detectar_intradup_masivo, _screening, clasificar,
    )
    from pesaje_v3.generadores_c3 import generar_todas_hipotesis

    if not os.path.exists(EXCEL_TRIUNVIRATO):
        pytest.skip('Febrero Triunvirato 2026.xlsx no disponible')

    datos = cargar_dia(EXCEL_TRIUNVIRATO, 13)
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)
    observaciones = {n: _observar(n, sc, datos) for n, sc in cont.sabores.items()}
    masivo = _detectar_intradup_masivo(datos, observaciones)
    assert masivo, 'D14 Triunvirato deberia activar INTRADUP_MASIVO'

    nombre = 'CH AMORES'
    sc = cont.sabores[nombre]
    obs = observaciones[nombre]
    status, flags = _screening(nombre, sc, obs, modo='TURNO_UNICO', intradup_masivo=masivo)

    hipotesis = generar_todas_hipotesis(nombre, sc, datos, obs, flags, turno_masivo=masivo)
    pfit_h = [h for h in hipotesis if h.codigo_pf in ('PFIT', 'PFIT_MASIVO')]

    assert len(pfit_h) == 1, \
        f'Esperaba 1 hipótesis PFIT_MASIVO, encontré {len(pfit_h)}: {[h.codigo_pf for h in pfit_h]}'
    h = pfit_h[0]
    assert h.codigo_pf == 'PFIT_MASIVO', \
        f'Esperaba PFIT_MASIVO, encontré {h.codigo_pf}'
    assert h.delta_venta < -10000, \
        f'Delta acumulado debería ser < -10000g (dos latas ~6500g cada una), fue {h.delta_venta}'
    assert h.venta_propuesta >= 0, \
        f'venta_propuesta={h.venta_propuesta} negativa — incoherente'
    assert h.confianza >= 0.72, \
        f'confianza={h.confianza} demasiado baja para caso con backward'

    # El clasificar completo debe resolver CH AMORES (no escalar)
    resultado = clasificar(datos, cont)
    sc_final = resultado.sabores[nombre]
    assert sc_final.prototipo is not None, \
        'CH AMORES D14 debe estar resuelta con PFIT_MASIVO, no escalada a C4'
    assert sc_final.prototipo.codigo == 'PFIT_MASIVO', \
        f'Prototipo={sc_final.prototipo.codigo}, esperaba PFIT_MASIVO'


def test_pfit_masivo_negativo_pares_ambiguos():
    """
    NEGATIVO: dos entrantes que podrían reclamar la misma cerrada (pesos cruzados).
    entrantes=[6500, 6520], cerradas=[6510].
    Ambos entrantes están dentro de ±100g de la cerrada → asignación ambigua.
    Con turno_masivo=True → NO debe generarse PFIT_MASIVO.
    Debe caer a comportamiento individual (PFIT o sin hipótesis).
    """
    from pesaje_v3.generadores_c3 import generar_hipotesis_pfit, _pares_no_conflictivos

    # Verificar directamente la condición de no-conflicto
    # Par 0: ea_idx=0, ea=6500, cerrada=6510, c_idx=0
    # Par 1: ea_idx=1, ea=6520, cerrada=6510, c_idx=0  <- mismo c_idx: no biyectivo
    pares_no_biyectivos = [(0, 6500, 6510, 0), (1, 6520, 6510, 0)]
    assert not _pares_no_conflictivos(pares_no_biyectivos), \
        'Pares que comparten c_idx=0 deben ser conflictivos (no biyectivos)'

    # También: entrantes con pesos que se cruzan (cada entrante podría ir a cualquier cerrada)
    # ea0=6490, ea1=6510, c0=6500, c1=6500: |ea0-c1|=10 <= 100 → conflicto de cruce
    pares_cruzados = [(0, 6490, 6500, 0), (1, 6510, 6500, 1)]
    # Aquí: |ea0=6490 - c1=6500| = 10 <= 100 → cruce → conflictivo
    assert not _pares_no_conflictivos(pares_cruzados), \
        'Pares con pesos cruzados deben ser conflictivos'

    # Y con el generador completo: pares ambiguos → sin PFIT_MASIVO
    # Fabricar: 2 entrantes ~6500 y 1 cerrada 6510
    nombre, datos, sc, obs, flags = _fabricar_datos_pfit(
        cerradas_dia=[6510],
        entrantes_dia=[6500, 6520],
        cerradas_previo=[6510],
    )
    hipotesis = generar_hipotesis_pfit(nombre, sc, datos, obs, flags, turno_masivo=True)
    masivo_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO']
    assert len(masivo_h) == 0, \
        f'Pares ambiguos no deben generar PFIT_MASIVO, pero se generó: {masivo_h}'


def test_pfit_masivo_coherencia_delta_absurdo():
    """
    COHERENCIA: delta acumulado produce venta negativa absurda.
    Pesos bien separados (no hay cruce de pares) → PFIT_MASIVO se genera.
    raw=7000g, ent0=4010 ~ cerr0=4000, ent1=5490 ~ cerr1=5500 → no se cruzan.
    delta = -(4010+5490) = -9500 → venta_propuesta = -2500g (absurda).
    El generador crea la hipótesis; el árbitro debe rechazarla por incoherencia.
    Nota: los pesos 4000 y 5500 están 1500g separados → |ea0-c1|=1490 > 100 → no hay cruce.
    """
    from pesaje_v3.generadores_c3 import generar_hipotesis_pfit
    from pesaje_v3.arbitro_c3 import resolver_hipotesis
    from pesaje_v3.modelos import ObservacionC3, ResolucionC3

    nombre, datos, sc, obs, flags = _fabricar_datos_pfit(
        cerradas_dia=[4000, 5500],    # pesos separados: sin cruce posible
        entrantes_dia=[4010, 5490],   # cada uno matchea solo su cerrada
        cerradas_previo=[4000, 5500], # backward confirma ambos → FUERTE
        venta_raw=7000,
    )
    obs = ObservacionC3(nombre_norm=nombre, total_a=sc.total_a, total_b=sc.total_b, venta_raw=7000)

    hipotesis = generar_hipotesis_pfit(nombre, sc, datos, obs, flags, turno_masivo=True)
    masivo_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO']

    assert len(masivo_h) == 1, \
        f'Esperaba 1 PFIT_MASIVO, encontré {len(masivo_h)}: {[h.codigo_pf for h in hipotesis]}'
    h = masivo_h[0]
    assert h.venta_propuesta < -300, \
        f'venta_propuesta={h.venta_propuesta} debería ser < -300 (absurda)'

    # El árbitro debe rechazarla por incoherencia material
    decision = resolver_hipotesis(masivo_h, obs, [])
    assert decision.resolucion == ResolucionC3.ESCALAR_C4, \
        f'Árbitro debería rechazar PFIT_MASIVO con venta absurda, pero resolvió: {decision.resolucion}'


@pytest.mark.parametrize('dia', [5, 6])
def test_pfit_masivo_negativo_san_martin(dia):
    """
    AISLAMIENTO DIA/NOCHE: San Martín no debe generar PFIT_MASIVO.
    D5 y D6 son días DIA/NOCHE normales sin doble registro masivo.
    - masivo debe ser False (prueba la condición compuesta)
    - Ningún sabor debe tener hipótesis PFIT_MASIVO
    """
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import (
        canonicalizar_nombres, aplicar_canonicalizacion,
        _observar, _detectar_intradup_masivo, _screening,
    )
    from pesaje_v3.generadores_c3 import generar_todas_hipotesis

    if not os.path.exists(EXCEL):
        pytest.skip('Febrero San Martin 2026.xlsx no disponible')

    datos = cargar_dia(EXCEL, dia)
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)
    observaciones = {n: _observar(n, sc, datos) for n, sc in cont.sabores.items()}
    masivo = _detectar_intradup_masivo(datos, observaciones)

    assert not masivo, \
        f'San Martín D{dia} no debe activar INTRADUP_MASIVO (masivo={masivo})'

    # Sin masivo, ningún sabor debe producir PFIT_MASIVO
    for nombre, sc in cont.sabores.items():
        if sc.solo_dia or sc.solo_noche:
            continue
        obs = observaciones[nombre]
        status, flags = _screening(nombre, sc, obs, modo='DIA_NOCHE', intradup_masivo=False)
        hipotesis = generar_todas_hipotesis(nombre, sc, datos, obs, flags, turno_masivo=False)
        masivo_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO']
        assert len(masivo_h) == 0, \
            f'San Martín D{dia} {nombre}: PFIT_MASIVO no debería aparecer sin turno_masivo'


# ===================================================================
# G) PFIT_MASIVO_AMBIGU — monto inequívoco, asignación bijéctiva ambigua
# ===================================================================

def test_pfit_masivo_ambigu_positivo_menta_d13():
    """
    POSITIVO (MENTA D13 Triunvirato = Viernes 13):
    DIA cerradas=[6735, 6485, 6450], entrantes=[6485, 6450].
    Cruce: |6485-6450|=35g ≤ 100 → _pares_no_conflictivos=False.
    Pero: slots biyectivos, cerradas persisten en NOCHE=[6735,6485,6450],
    sin rival de genealogía.
    Esperado: 1 hipótesis PFIT_MASIVO_AMBIGU con delta=-(6485+6450)=-12935g.
    Resolución final: CORREGIDO_C3_BAJA_CONFIANZA.
    """
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import (clasificar, _observar, _screening,
                                       _detectar_intradup_masivo,
                                       canonicalizar_nombres, aplicar_canonicalizacion)
    from pesaje_v3.generadores_c3 import generar_hipotesis_pfit
    from pesaje_v3.modelos import ResolucionC3

    if not os.path.exists(EXCEL_TRIUNVIRATO):
        pytest.skip('Workbook Triunvirato no encontrado')

    datos = cargar_dia(EXCEL_TRIUNVIRATO, 13)  # DIA=Viernes 13
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)
    nombre = 'MENTA'

    observaciones = {n: _observar(n, sc, datos) for n, sc in cont.sabores.items()}
    masivo = _detectar_intradup_masivo(datos, observaciones)
    assert masivo, 'D13 Triunvirato (Viernes 13) debe tener INTRADUP_MASIVO=True'

    sc = cont.sabores[nombre]
    obs = observaciones[nombre]
    status, flags = _screening(nombre, sc, obs, modo='TURNO_UNICO', intradup_masivo=masivo)

    hipotesis = generar_hipotesis_pfit(nombre, sc, datos, obs, flags, turno_masivo=masivo)
    ambigu_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO_AMBIGU']

    assert len(ambigu_h) == 1, \
        f'Esperaba 1 PFIT_MASIVO_AMBIGU para MENTA, encontré {len(ambigu_h)}: ' \
        f'{[h.codigo_pf for h in hipotesis]}'
    h = ambigu_h[0]
    assert h.delta_venta == -(6485 + 6450), \
        f'delta esperado={-(6485+6450)}, obtenido={h.delta_venta}'
    assert h.confianza == pytest.approx(0.70, abs=0.01), \
        f'confianza={h.confianza}, esperaba 0.70 (CONFIANZA_MINIMA_VIABLE)'

    # Resolución final: CORREGIDO_C3_BAJA_CONFIANZA (confianza < CONFIANZA_MINIMA_FUERTE)
    resultado = clasificar(datos, cont)
    sc_final = resultado.sabores[nombre]
    assert sc_final.resolution_status == ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA, \
        f'MENTA D13: esperaba CORREGIDO_C3_BAJA_CONFIANZA, got {sc_final.resolution_status}'
    assert sc_final.venta_final_c3 == pytest.approx(sc.venta_raw - 12935, abs=5), \
        f'venta_final_c3={sc_final.venta_final_c3}, esperaba aprox {sc.venta_raw - 12935}'


def test_pfit_masivo_ambigu_positivo_tiramisu_d13():
    """
    POSITIVO (TIRAMISU D13 Triunvirato = Viernes 13):
    DIA cerradas=[6340, 6330], entrantes=[6340, 6330].
    Cruce: |6340-6330|=10g ≤ 100 → asignación ambigua.
    Pero: slots biyectivos, cerradas persisten en NOCHE=[6340,6330],
    sin rival de genealogía (NOCHE entrantes=[]).
    Esperado: 1 PFIT_MASIVO_AMBIGU con delta=-(6340+6330)=-12670g.
    """
    from pesaje_v3.capa1_parser import cargar_dia
    from pesaje_v3.capa2_contrato import calcular_contabilidad
    from pesaje_v3.capa3_motor import (clasificar, _observar, _screening,
                                       _detectar_intradup_masivo,
                                       canonicalizar_nombres, aplicar_canonicalizacion)
    from pesaje_v3.generadores_c3 import generar_hipotesis_pfit
    from pesaje_v3.modelos import ResolucionC3

    if not os.path.exists(EXCEL_TRIUNVIRATO):
        pytest.skip('Workbook Triunvirato no encontrado')

    datos = cargar_dia(EXCEL_TRIUNVIRATO, 13)
    canon = canonicalizar_nombres(datos)
    aplicar_canonicalizacion(datos, canon)
    cont = calcular_contabilidad(datos)
    nombre = 'TIRAMISU'

    observaciones = {n: _observar(n, sc, datos) for n, sc in cont.sabores.items()}
    masivo = _detectar_intradup_masivo(datos, observaciones)

    sc = cont.sabores[nombre]
    obs = observaciones[nombre]
    status, flags = _screening(nombre, sc, obs, modo='TURNO_UNICO', intradup_masivo=masivo)

    hipotesis = generar_hipotesis_pfit(nombre, sc, datos, obs, flags, turno_masivo=masivo)
    ambigu_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO_AMBIGU']

    assert len(ambigu_h) == 1, \
        f'Esperaba 1 PFIT_MASIVO_AMBIGU para TIRAMISU, encontré {len(ambigu_h)}'
    assert ambigu_h[0].delta_venta == -(6340 + 6330), \
        f'delta={ambigu_h[0].delta_venta}, esperaba {-(6340+6330)}'

    resultado = clasificar(datos, cont)
    sc_final = resultado.sabores[nombre]
    assert sc_final.resolution_status == ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA, \
        f'TIRAMISU D13: esperaba CORREGIDO_C3_BAJA_CONFIANZA, got {sc_final.resolution_status}'


def test_pfit_masivo_ambigu_negativo_cerrada_no_persiste():
    """
    NEGATIVO: cerrada ambigua que NO persiste en NOCHE (condición 4 falla).

    Diseño: cerradas_dia=[5400, 5550], entrantes_dia=[5480, 5540].
    - ent=5480 → cerr=5400 (|5480-5400|=80 ≤ 100, par 0).
    - ent=5540 → cerr=5550 (|5540-5400|=140 > 100, salta; |5540-5550|=10 ≤ 100, par 1).
    - Cross-match: |5480-5550|=70 ≤ 100 → _pares_no_conflictivos=False.
    - Slots biyectivos: ent_slots=[0,1], cerr_slots=[0,1] → True.
    - cerradas_noche=[5400]: 5550 ausente (|5550-5400|=150 > TOL_MATCH_CERRADA=30) → cond. 4 falla.
    turno_masivo=True.

    Resultado esperado: 0 PFIT_MASIVO_AMBIGU.
    """
    from pesaje_v3.generadores_c3 import (generar_hipotesis_pfit,
                                          _cerradas_persisten_en_noche,
                                          _slots_biyectivos)

    # Verificar condición 4 directamente con mock
    pares_test = [(0, 5480, 5400, 0), (1, 5540, 5550, 1)]
    assert _slots_biyectivos(pares_test), 'slots deben ser biyectivos'

    class _MockSabor:
        def __init__(self, cerradas, entrantes=None):
            self.cerradas = cerradas
            self.entrantes = entrantes or []

    n_mock = _MockSabor(cerradas=[5400])  # 5550 ausente
    assert not _cerradas_persisten_en_noche(pares_test, n_mock), \
        'Cond 4 debe fallar: 5550 (|5550-5400|=150 > 30g) no persiste en NOCHE'

    # Con el generador completo: cond. 4 falla → sin PFIT_MASIVO_AMBIGU
    # cerradas_noche=[5400]: 5550 desapareció entre DIA y NOCHE → monto no inequívoco
    nombre, datos, sc, obs, flags = _fabricar_datos_pfit(
        cerradas_dia=[5400, 5550],
        entrantes_dia=[5480, 5540],
        cerradas_noche=[5400],          # 5550 ausente en NOCHE
        cerradas_previo=[5400, 5550],   # previo para temporal support
    )
    hipotesis = generar_hipotesis_pfit(nombre, sc, datos, obs, flags, turno_masivo=True)
    ambigu_h = [h for h in hipotesis if h.codigo_pf == 'PFIT_MASIVO_AMBIGU']
    assert len(ambigu_h) == 0, \
        f'Cond. 4 falla (5550 ausente en NOCHE): no debe generarse PFIT_MASIVO_AMBIGU, ' \
        f'pero se generó: {ambigu_h}'


# ===================================================================
# H) Contratos arquitecturales — invariantes de diseño, no de datos
# ===================================================================

def test_contrato_ambigu_y_c4d_comparten_tolerancia():
    """
    CONTRATO ARQUITECTURAL: condición 4 de AMBIGU y generación de C4d usan
    la misma tolerancia (TOL_MATCH_CERRADA).

    Por qué esto importa:
    PF1 solo genera hipótesis para cerradas con flag C4d.
    C4d solo se genera cuando la cerrada NO matchea ninguna cerrada NOCHE
    dentro de TOL_MATCH_CERRADA.
    Condición 4 de AMBIGU (cerradas persisten en NOCHE) usa la misma tolerancia.

    Consecuencia: si una cerrada pasa condición 4, no tiene C4d, y PF1 no la
    toca. Si tiene C4d, condición 4 falla y AMBIGU no nace. Ergo: PF1 y AMBIGU
    no pueden coexistir sobre la misma cerrada — pero solo mientras ambas
    tolerancias sean iguales.

    Este test convierte esa coincidencia en contrato. Si alguien cambia la
    tolerancia en un lado sin cambiar el otro, el test falla y obliga a decidir
    si la protección cruzada sigue vigente.
    """
    from pesaje_v3.constantes_c3 import TOL_MATCH_CERRADA
    from pesaje_v3 import capa3_motor, generadores_c3
    import inspect

    # Verificar que _screening usa TOL_MATCH_CERRADA para generar C4d
    screening_src = inspect.getsource(capa3_motor._screening)
    assert 'TOL_MATCH_CERRADA' in screening_src, (
        '_screening ya no usa TOL_MATCH_CERRADA para generar C4d. '
        'Si la tolerancia cambió, verificar que condición 4 de AMBIGU '
        'siga siendo coherente con la generación de flags C4d.'
    )

    # Verificar que _cerradas_persisten_en_noche usa TOL_MATCH_CERRADA
    persist_src = inspect.getsource(generadores_c3._cerradas_persisten_en_noche)
    assert 'TOL_MATCH_CERRADA' in persist_src, (
        '_cerradas_persisten_en_noche ya no usa TOL_MATCH_CERRADA. '
        'Si la tolerancia cambió, la protección cruzada con C4d puede '
        'estar rota: PF1 y AMBIGU podrían coexistir sobre la misma cerrada.'
    )


def test_contrato_pfit_ambigu_nace_en_piso_viable():
    """
    CONTRATO ARQUITECTURAL: PFIT_CONF_AMBIGU == CONFIANZA_MINIMA_VIABLE.

    Esta igualdad no es casual — es una decisión de diseño:
    AMBIGU nace exactamente en el piso viable del árbitro.

    Por qué importa fijarlo como test:
    - Si PFIT_CONF_AMBIGU < CONFIANZA_MINIMA_VIABLE: el árbitro la descarta
      silenciosamente (0 viables → ESCALAR_C4). No hay error, no hay aviso.
      La hipótesis se genera, nadie la ve morir.
    - Si PFIT_CONF_AMBIGU > CONFIANZA_MINIMA_VIABLE pero < CONFIANZA_MINIMA_FUERTE:
      el contrato sigue válido (CORREGIDO_C3_BAJA_CONFIANZA).
      Pero entonces AMBIGU tendría más confianza que la mínima viable sin razón
      semántica: el monto es inequívoco pero la asignación es ambigua — eso vale
      exactamente el piso, no más.

    Si CONFIANZA_MINIMA_VIABLE cambia algún día, este test fallará.
    Ese fallo es la señal correcta: requiere una decisión consciente sobre
    si AMBIGU debe seguir al piso o establecer su propio umbral documentado.

    La falla silenciosa (AMBIGU muerta sin aviso) es peor que la falla ruidosa
    (test rojo que pide decisión explícita).
    """
    from pesaje_v3.constantes_c3 import (
        PFIT_CONF_AMBIGU,
        CONFIANZA_MINIMA_VIABLE,
        CONFIANZA_MINIMA_FUERTE,
    )

    assert PFIT_CONF_AMBIGU == CONFIANZA_MINIMA_VIABLE, (
        f'PFIT_CONF_AMBIGU ({PFIT_CONF_AMBIGU}) debe ser exactamente '
        f'CONFIANZA_MINIMA_VIABLE ({CONFIANZA_MINIMA_VIABLE}). '
        f'AMBIGU nace en el piso viable por diseño — si ese piso cambió, '
        f'decidir conscientemente si AMBIGU sigue al piso o se independiza.'
    )

    assert PFIT_CONF_AMBIGU < CONFIANZA_MINIMA_FUERTE, (
        f'PFIT_CONF_AMBIGU ({PFIT_CONF_AMBIGU}) debe ser menor que '
        f'CONFIANZA_MINIMA_FUERTE ({CONFIANZA_MINIMA_FUERTE}). '
        f'AMBIGU siempre produce CORREGIDO_C3_BAJA_CONFIANZA, nunca CORREGIDO_C3.'
    )


# ===================================================================
# I) PF1 delta recalculado en TURNO_UNICO
# ===================================================================

def test_pf1_turno_unico_delta_recalculado_chocolate():
    """
    CASO REAL: CHOCOLATE Triunvirato D15 (Sabado 14 -> Domingo 15).
    DIA cerradas=[5855, 6685, 6480], NOCHE cerradas=[6685, 6855, 6480].
    5855 es typo de 6855 (+1000).

    En TURNO_UNICO, 6855 de NOCHE estaba en new_cerr_b (no matcheaba DIA).
    Al corregir 5855->6855, la 6855 de NOCHE ahora matchea DIA ->
    new_cerr_b pierde 6855g.

    delta correcto = offset - new_cerr_b_eliminado = +1000 - 6855 = -5855
    venta_raw=6640, venta_corregida = 6640 + (-5855) = 785g
    """
    from pesaje_v3.generadores_c3 import _recalcular_delta_pf1
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia

    d = TurnoCrudo(nombre_hoja='T_DIA', indice=0, sabores={
        'CHOCOLATE': SaborCrudo(nombre='CHOCOLATE', nombre_norm='CHOCOLATE',
                                abierta=5545, celiaca=None,
                                cerradas=[5855, 6685, 6480], entrantes=[]),
    })
    n = TurnoCrudo(nombre_hoja='T_NOCHE', indice=1, sabores={
        'CHOCOLATE': SaborCrudo(nombre='CHOCOLATE', nombre_norm='CHOCOLATE',
                                abierta=4760, celiaca=None,
                                cerradas=[6685, 6855, 6480], entrantes=[]),
    })
    datos = DatosDia(dia_label='test', turno_dia=d, turno_noche=n, contexto=[],
                     modo='TURNO_UNICO')

    delta = _recalcular_delta_pf1('CHOCOLATE', datos, 5855, 6855, es_dia=True)

    assert delta == -5855, \
        f'delta={delta}, esperaba -5855 (offset +1000 menos new_cerr_b 6855)'

    # Verificar que venta corregida = 785g
    venta_raw = 6640  # calculado con 5855 + new_cerr_b=6855
    assert venta_raw + delta == 785, f'venta_corregida={venta_raw + delta}, esperaba 785'


def test_pf1_turno_unico_offset_solo_total_a():
    """
    TURNO_UNICO donde el offset solo cambia total_a (no afecta new_cerr_b).
    La cerrada corregida no matchea ninguna cerrada de NOCHE ni antes ni despues.
    En este caso delta == offset (comportamiento identico al shortcut viejo).
    """
    from pesaje_v3.generadores_c3 import _recalcular_delta_pf1
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia

    d = TurnoCrudo(nombre_hoja='T_DIA', indice=0, sabores={
        'TEST': SaborCrudo(nombre='TEST', nombre_norm='TEST',
                           abierta=3000, celiaca=None,
                           cerradas=[5400, 6600], entrantes=[]),
    })
    n = TurnoCrudo(nombre_hoja='T_NOCHE', indice=1, sabores={
        'TEST': SaborCrudo(nombre='TEST', nombre_norm='TEST',
                           abierta=2500, celiaca=None,
                           cerradas=[6600], entrantes=[]),
    })
    datos = DatosDia(dia_label='test', turno_dia=d, turno_noche=n, contexto=[],
                     modo='TURNO_UNICO')

    # 5400 -> 6400 (+1000). 6400 no matchea ninguna cerrada NOCHE.
    # new_cerr_b no cambia. delta debe ser = offset = +1000.
    delta = _recalcular_delta_pf1('TEST', datos, 5400, 6400, es_dia=True)

    assert delta == 1000, \
        f'delta={delta}, esperaba 1000 (offset puro, sin cambio en new_cerr_b)'


def test_pf1_dia_noche_delta_es_offset():
    """
    DIA_NOCHE: new_cerr_b siempre es 0, asi que delta == offset.
    Verifica que el recalculo no rompe el caso simple.
    """
    from pesaje_v3.generadores_c3 import _recalcular_delta_pf1
    from pesaje_v3.modelos import SaborCrudo, TurnoCrudo, DatosDia

    d = TurnoCrudo(nombre_hoja='T_DIA', indice=0, sabores={
        'TEST': SaborCrudo(nombre='TEST', nombre_norm='TEST',
                           abierta=3000, celiaca=None,
                           cerradas=[5855, 6685], entrantes=[]),
    })
    n = TurnoCrudo(nombre_hoja='T_NOCHE', indice=1, sabores={
        'TEST': SaborCrudo(nombre='TEST', nombre_norm='TEST',
                           abierta=2500, celiaca=None,
                           cerradas=[6685, 6855], entrantes=[]),
    })
    datos = DatosDia(dia_label='test', turno_dia=d, turno_noche=n, contexto=[],
                     modo='DIA_NOCHE')

    # 5855 -> 6855 en DIA, DIA_NOCHE: delta = +1000 (offset puro)
    # porque new_cerr_b es siempre 0 en DIA_NOCHE
    delta = _recalcular_delta_pf1('TEST', datos, 5855, 6855, es_dia=True)

    assert delta == 1000, \
        f'delta={delta}, esperaba 1000 (DIA_NOCHE, offset puro)'

    # NOCHE: corregir 6855->5855 reduce total_b en 1000 -> venta sube 1000
    # offset = -1000, -offset = +1000 = delta correcto
    delta_n = _recalcular_delta_pf1('TEST', datos, 6855, 5855, es_dia=False)
    assert delta_n == 1000, \
        f'delta_noche={delta_n}, esperaba +1000 (NOCHE menor -> venta mayor)'


# ===================================================================
# MAIN
# ===================================================================

if __name__ == '__main__':
    # Correr sin pytest para verificacion rapida
    print('=== Invariantes legacy (sin campos nuevos) ===')
    for dia in [5, 27, 28]:
        _, _, c3, _ = _correr_pipeline(dia)
        errores = 0
        for nombre, sc in c3.sabores.items():
            try:
                assert_invariantes_sabor(sc, strict=True)
            except InvariantError as e:
                print(f'  VIOLACION D{dia}: {e}')
                errores += 1
        if errores == 0:
            print(f'  D{dia}: {len(c3.sabores)} sabores OK')

    print()
    print('=== Regresion contra baseline ===')
    baseline_data = _cargar_baseline()
    for dia in [5, 27, 28]:
        _, cont, c3, c4 = _correr_pipeline(dia)
        actual = _normalizar_snapshot(c3, c4, cont)
        esperado = baseline_data[str(dia)]
        diffs = 0
        for nombre in sorted(actual['sabores'].keys()):
            if actual['sabores'][nombre] != esperado['sabores'].get(nombre):
                print(f'  DIFF D{dia} {nombre}')
                diffs += 1
        if diffs == 0:
            print(f'  D{dia}: regresion OK ({len(actual["sabores"])} sabores)')
