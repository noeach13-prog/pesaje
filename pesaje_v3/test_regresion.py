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

def test_bilateral_sambayon_d28_no_resuelve_unilateral():
    """
    CASO CONCRETO: SAMBAYON D28.
    cerr DIA [6450, 6675] -> cerr NOCHE [6575].
    6675 desaparece (PHANTOM candidato), 6450->6575 es mismatch (125g).
    El sistema NO debe resolver PHANTOM_DIA unilateral porque existe
    MISMATCH_LEVE del otro slot en el mismo episodio.
    Debe caer a H0.
    """
    _, cont, c3, c4 = _correr_pipeline(28)

    assert 'SAMBAYON' in c4.sin_resolver, \
        'SAMBAYON D28 fue resuelto — deberia estar en H0 por estructura bilateral'

    samb = c3.sabores.get('SAMBAYON')
    assert samb is not None
    assert samb.prototipo is None, \
        f'SAMBAYON no deberia tener prototipo C3, tiene {samb.prototipo}'


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
