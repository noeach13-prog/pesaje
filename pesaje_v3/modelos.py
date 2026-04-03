"""
modelos.py — Estructuras de datos para el pipeline v3.
Cada capa produce su propio tipo de output.
Las capas superiores reciben el output de las inferiores sin modificarlo.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# CAPA 1 — Datos crudos del parser
# ═══════════════════════════════════════════════════════════════

@dataclass
class SaborCrudo:
    """Un sabor en un turno, tal cual sale del Excel."""
    nombre: str              # nombre TAL CUAL aparece en planilla
    nombre_norm: str         # normalizado (upper, sin acentos, aliases)
    abierta: Optional[int]   # None = no registrado, 0 = explícito
    celiaca: Optional[int]
    cerradas: List[int] = field(default_factory=list)
    entrantes: List[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        ab = self.abierta or 0
        cel = self.celiaca or 0
        return ab + cel + sum(self.cerradas) + sum(self.entrantes)


@dataclass
class TurnoCrudo:
    """Todos los sabores de un turno."""
    nombre_hoja: str         # "Jueves 5 (DIA)"
    indice: int              # posición en el workbook
    sabores: Dict[str, SaborCrudo] = field(default_factory=dict)  # nombre_norm → SaborCrudo
    vdp_textos: List[str] = field(default_factory=list)
    es_vacio: bool = False


@dataclass
class DatosDia:
    """Output de Capa 1: par de turnos DIA/NOCHE + contexto."""
    dia_label: str           # "5", "25", "28"
    turno_dia: TurnoCrudo
    turno_noche: TurnoCrudo
    contexto: List[TurnoCrudo] = field(default_factory=list)  # turnos adyacentes para Capa 4
    modo: str = 'DIA_NOCHE'  # 'DIA_NOCHE' | 'TURNO_UNICO'


# ═══════════════════════════════════════════════════════════════
# CAPA 2 — Cálculo contable por sabor
# ═══════════════════════════════════════════════════════════════

@dataclass
class SaborContable:
    """Resultado de aplicar la fórmula de venta a un sabor."""
    nombre_norm: str
    nombre_display: str      # nombre más legible

    # Stock
    total_a: int
    total_b: int
    new_ent_b: int           # entrantes nuevos en NOCHE (no estaban en DIA)
    n_cerr_a: int
    n_cerr_b: int

    # Cálculo
    n_latas: int             # max(0, n_cerr_a - n_cerr_b)
    ajuste_latas: int        # n_latas * 280
    venta_raw: int

    # Presencia
    solo_dia: bool = False   # presente en DIA pero no en NOCHE
    solo_noche: bool = False # presente en NOCHE pero no en DIA
    new_cerr_b: int = 0      # cerradas nuevas en B no matcheadas en A (TURNO_UNICO)


@dataclass
class ContabilidadDia:
    """Output de Capa 2: todos los sabores con su venta raw."""
    dia_label: str
    sabores: Dict[str, SaborContable] = field(default_factory=dict)
    vdp_total: int = 0
    venta_raw_total: int = 0


# ═══════════════════════════════════════════════════════════════
# CAPA 3 — Clasificación y motor local
# ═══════════════════════════════════════════════════════════════

class StatusC3(Enum):
    LIMPIO = 'LIMPIO'
    ENGINE = 'ENGINE'
    SENAL = 'SENAL'
    COMPUESTO = 'COMPUESTO'
    OBSERVACION = 'OBSERVACION'
    SOLO_DIA = 'SOLO_DIA'
    SOLO_NOCHE = 'SOLO_NOCHE'
    ESCALAR = 'ESCALAR'


@dataclass
class FlagC3:
    """Una señal detectada en screening."""
    codigo: str       # 'NEG', 'HIGH', 'AB_UP', 'C4d:6555', 'C4n:6445', 'CERR+1N'
    condicion: int    # qué condición C1-C4 la generó (1,2,3,4)
    detalle: str = ''


@dataclass
class PrototipoAplicado:
    """Un prototipo PF1-PF8 que se aplicó en Capa 3."""
    codigo: str           # 'PF1', 'PF2', ..., 'PF8'
    descripcion: str
    confianza: float
    delta: int            # cambio en venta (corregido - raw)
    venta_corregida: int


@dataclass
class MarcaCalidad:
    """Marca de calidad sobre un dato."""
    tipo: str         # 'DATO_NORMAL', 'COPIA_POSIBLE_LEVE', 'COPIA_POSIBLE_FUERTE'
    detalle: str = ''
    penalizacion: float = 0.0  # 0, 0, 0.15


@dataclass
class SaborClasificado:
    """Output de Capa 3 para un sabor."""
    nombre_norm: str
    contable: SaborContable       # referencia al calculo de Capa 2

    # Legacy: screening status (NO ES resolution, es como entro el caso)
    status: StatusC3
    flags: List[FlagC3] = field(default_factory=list)

    # Legacy: resolucion en C3
    prototipo: Optional[PrototipoAplicado] = None
    venta_final_c3: Optional[int] = None  # None si no resuelto aqui

    # Calidad
    marcas: List[MarcaCalidad] = field(default_factory=list)

    # --- Nuevo regimen (campos opcionales durante transicion) ---
    screening_status: Optional[StatusC3] = None
    resolution_status: Optional['ResolucionC3'] = None
    observacion: Optional['ObservacionC3'] = None
    decision: Optional['DecisionC3'] = None

    @property
    def resuelto_en_c3_legacy(self) -> bool:
        """Logica vieja. Muere cuando migracion completa."""
        return self.status in (StatusC3.LIMPIO, StatusC3.ENGINE,
                               StatusC3.OBSERVACION, StatusC3.SOLO_DIA,
                               StatusC3.SOLO_NOCHE) or self.prototipo is not None

    @property
    def resuelto_en_c3_v2(self) -> bool:
        """Logica nueva. Se vuelve canonical cuando legacy se borre."""
        if self.resolution_status is None:
            return self.resuelto_en_c3_legacy
        return self.resolution_status in (
            ResolucionC3.RAW_VALIDO,
            ResolucionC3.CORREGIDO_C3,
            ResolucionC3.CORREGIDO_C3_BAJA_CONFIANZA,
            ResolucionC3.NO_CALCULABLE,
        )

    @property
    def resuelto_en_c3(self) -> bool:
        """Delegado. Cambia a v2 cuando ambos coincidan en toda la bateria."""
        return self.resuelto_en_c3_legacy


@dataclass
class ResultadoC3:
    """Output de Capa 3: todos los sabores clasificados."""
    dia_label: str
    sabores: Dict[str, SaborClasificado] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)  # avisos a nivel de día (ej: INTRADUP_MASIVO)

    @property
    def escalados(self) -> Dict[str, SaborClasificado]:
        return {k: v for k, v in self.sabores.items()
                if v.status in (StatusC3.SENAL, StatusC3.COMPUESTO, StatusC3.ESCALAR)
                and v.prototipo is None}

    @property
    def limpios(self) -> Dict[str, SaborClasificado]:
        return {k: v for k, v in self.sabores.items()
                if v.status == StatusC3.LIMPIO}


# ═══════════════════════════════════════════════════════════════
# CAPA 3 — Nuevo regimen: observacion, hipotesis, decision
# Estos tipos NO reemplazan los legacy de arriba (conviven durante
# la transicion). Cada tipo trae su ley interna como metodo
# validar() que lanza InvariantError, no assert.
# ═══════════════════════════════════════════════════════════════

class InvariantError(Exception):
    """Violacion de invariante constitucional. Explota en ejecucion."""
    pass


# --- Slots: identidad minima simetrica ---

@dataclass(frozen=True)
class SlotCerrada:
    """Identidad minima de un slot de cerrada."""
    peso: int
    turno: str         # 'DIA' o 'NOCHE'
    indice_slot: int   # posicion en cerradas[]


@dataclass(frozen=True)
class SlotEntrante:
    """Identidad minima de un slot de entrante."""
    peso: int
    turno: str
    indice_slot: int   # posicion en entrantes[]


# --- Enums del nuevo regimen ---

class LadoError(Enum):
    DIA = 'DIA'
    NOCHE = 'NOCHE'


class CampoAfectado(Enum):
    CERRADA = 'CERRADA'
    ABIERTA = 'ABIERTA'
    ENTRANTE = 'ENTRANTE'


class OperacionCorreccion(Enum):
    SUSTITUIR = 'SUSTITUIR'    # reemplazar peso por otro
    ELIMINAR = 'ELIMINAR'      # remover slot del calculo
    AGREGAR = 'AGREGAR'        # insertar slot que no estaba


class MecanismoCausal(Enum):
    ERROR_DIGITO = 'ERROR_DIGITO'
    OMISION = 'OMISION'
    PHANTOM = 'PHANTOM'
    PROMO_DUP = 'PROMO_DUP'
    AB_IMP = 'AB_IMP'
    MISMATCH = 'MISMATCH'
    APERTURA_PHANTOM = 'APERTURA_PHANTOM'
    ENTRANTE_MISMO_CAN = 'ENTRANTE_MISMO_CAN'


class TipoFuente(Enum):
    FORWARD = 'FORWARD'
    BACKWARD = 'BACKWARD'
    SIGHTINGS = 'SIGHTINGS'
    MATCHING = 'MATCHING'
    REDUCTIO = 'REDUCTIO'


class ResolucionC3(Enum):
    RAW_VALIDO = 'RAW_VALIDO'
    CORREGIDO_C3 = 'CORREGIDO_C3'
    CORREGIDO_C3_BAJA_CONFIANZA = 'CORREGIDO_C3_BAJA_CONFIANZA'
    ESCALAR_C4 = 'ESCALAR_C4'
    NO_CALCULABLE = 'NO_CALCULABLE'


class MotivoDecisionC3(Enum):
    SCREENING_LIMPIO = 'SCREENING_LIMPIO'
    SCREENING_ENGINE = 'SCREENING_ENGINE'
    SOLO_UN_TURNO = 'SOLO_UN_TURNO'
    HIPOTESIS_UNICA_FUERTE = 'HIPOTESIS_UNICA_FUERTE'
    HIPOTESIS_UNICA_BAJA_CONF = 'HIPOTESIS_UNICA_BAJA_CONF'
    SIN_HIPOTESIS_VIABLE = 'SIN_HIPOTESIS_VIABLE'
    CONFLICTO_EN_TARGET = 'CONFLICTO_EN_TARGET'
    MULTIBLANCO_NO_SOPORTADO = 'MULTIBLANCO_NO_SOPORTADO'
    COLISION_IDENTIDAD = 'COLISION_IDENTIDAD'
    MARCAS_DESCALIFICANTES = 'MARCAS_DESCALIFICANTES'


# --- ObservacionC3: metricas puras, sin juicios ---

@dataclass
class ObservacionC3:
    """
    Metricas y correspondencias brutas extraidas de los datos.
    NO contiene: apertura_proxy, entrantes_promovidos, flags_screening.
    Esas son inferencias que pertenecen al screening, no a la observacion.
    """
    nombre_norm: str

    # Abierta — Optional porque SOLO_DIA/NOCHE no tiene el otro lado
    ab_d: Optional[int] = None
    ab_n: Optional[int] = None
    ab_delta: Optional[int] = None    # None si falta un lado

    # Cerradas: correspondencias y huerfanas (indexadas por slot)
    cerradas_matched_30: List[Tuple[SlotCerrada, SlotCerrada, int]] = field(default_factory=list)
    cerradas_unmatched_dia: List[SlotCerrada] = field(default_factory=list)
    cerradas_unmatched_noche: List[SlotCerrada] = field(default_factory=list)

    # Nearest: por slot (no por peso, para no colapsar identidad en duplicados)
    nearest_por_slot_dia: List[Tuple[SlotCerrada, SlotCerrada, int]] = field(default_factory=list)
    nearest_por_slot_noche: List[Tuple[SlotCerrada, SlotCerrada, int]] = field(default_factory=list)

    # Proximidades entrante-cerrada (nombre neutro, slots simetricos)
    proximidades_entrante_cerrada: List[Tuple[SlotEntrante, SlotCerrada, int]] = field(default_factory=list)

    # Mismatches en rango intermedio (30-200g)
    mismatches_leves_dia: List[Tuple[SlotCerrada, SlotCerrada, int]] = field(default_factory=list)
    mismatches_leves_noche: List[Tuple[SlotCerrada, SlotCerrada, int]] = field(default_factory=list)

    # Contexto temporal bruto
    forward_ab: Optional[int] = None
    backward_ab: Optional[int] = None
    forward_turno: Optional[str] = None
    backward_turno: Optional[str] = None

    # Totales contables (espejo de SaborContable, para guardias de coherencia)
    total_a: int = 0
    total_b: int = 0
    venta_raw: int = 0

    # Sightings: peso -> (count, n_turnos_totales)
    sightings: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    # Varianza: peso -> (mediana, stddev, n_observaciones)
    varianza_historica: Dict[int, Tuple[int, float, int]] = field(default_factory=dict)

    # Señal de doble-registro intra-turno: True si hay entrante DIA que matchea cerrada DIA
    intradup_candidato: bool = False


# --- FuenteEvidencia ---

@dataclass(frozen=True)
class FuenteEvidencia:
    """Fuente tipada de evidencia. El tipo gobierna; el detalle ilustra."""
    tipo: TipoFuente
    detalle: str    # "turno Viernes 27 NOCHE, ab=5440" — ilustrativo, no gobierna


# --- TargetCorreccion: nucleo unico de identidad ---

@dataclass
class TargetCorreccion:
    """
    Identifica exactamente QUE se corrige.
    El arbitro agrupa conflictos por clave_agrupamiento.
    """
    lado: LadoError
    campo: CampoAfectado
    operacion: OperacionCorreccion
    slot_cerrada: Optional[SlotCerrada] = None
    slot_entrante: Optional[SlotEntrante] = None
    peso_propuesto: Optional[int] = None    # obligatorio para SUSTITUIR y AGREGAR

    @property
    def clave_agrupamiento(self) -> tuple:
        """Clave unica para agrupamiento en el arbitro."""
        if self.slot_cerrada:
            return (self.lado.value, self.campo.value, self.operacion.value,
                    'cerr', self.slot_cerrada.turno, self.slot_cerrada.indice_slot)
        if self.slot_entrante:
            return (self.lado.value, self.campo.value, self.operacion.value,
                    'ent', self.slot_entrante.turno, self.slot_entrante.indice_slot)
        if self.operacion == OperacionCorreccion.AGREGAR:
            if self.peso_propuesto is None:
                raise InvariantError('AGREGAR sin peso_propuesto en clave_agrupamiento')
            return (self.lado.value, self.campo.value, 'AGREGAR', self.peso_propuesto)
        # ABIERTA SUSTITUIR: solo hay 1 abierta por turno
        return (self.lado.value, self.campo.value, self.operacion.value, 'ab', 0)

    def validar(self):
        """Invariantes internas. Lanza InvariantError si mal formado."""
        # Exclusion mutua de slots
        if self.slot_cerrada and self.slot_entrante:
            raise InvariantError('slot_cerrada y slot_entrante no pueden coexistir')

        # Campo vs slots: que NO puede existir
        if self.campo == CampoAfectado.ABIERTA:
            if self.slot_cerrada is not None:
                raise InvariantError('ABIERTA no puede tener slot_cerrada')
            if self.slot_entrante is not None:
                raise InvariantError('ABIERTA no puede tener slot_entrante')
            if self.operacion != OperacionCorreccion.SUSTITUIR:
                raise InvariantError(f'ABIERTA solo soporta SUSTITUIR, no {self.operacion.value}')
        if self.campo == CampoAfectado.CERRADA and self.slot_entrante is not None:
            raise InvariantError('CERRADA no puede tener slot_entrante')
        if self.campo == CampoAfectado.ENTRANTE and self.slot_cerrada is not None:
            raise InvariantError('ENTRANTE no puede tener slot_cerrada')

        # Campo vs slots: que DEBE existir
        if self.campo == CampoAfectado.CERRADA and self.operacion != OperacionCorreccion.AGREGAR:
            if self.slot_cerrada is None:
                raise InvariantError('CERRADA SUSTITUIR/ELIMINAR requiere slot_cerrada')
        if self.campo == CampoAfectado.ENTRANTE and self.operacion != OperacionCorreccion.AGREGAR:
            if self.slot_entrante is None:
                raise InvariantError('ENTRANTE SUSTITUIR/ELIMINAR requiere slot_entrante')

        # Operacion vs peso_propuesto
        if self.operacion == OperacionCorreccion.SUSTITUIR and self.peso_propuesto is None:
            raise InvariantError('SUSTITUIR requiere peso_propuesto')
        if self.operacion == OperacionCorreccion.AGREGAR and self.peso_propuesto is None:
            raise InvariantError('AGREGAR requiere peso_propuesto')
        if self.operacion == OperacionCorreccion.ELIMINAR and self.peso_propuesto is not None:
            raise InvariantError('ELIMINAR no debe tener peso_propuesto')

        # Turno del slot debe coincidir con lado
        if self.slot_cerrada and self.slot_cerrada.turno != self.lado.value:
            raise InvariantError(
                f'turno slot_cerrada ({self.slot_cerrada.turno}) != lado ({self.lado.value})')
        if self.slot_entrante and self.slot_entrante.turno != self.lado.value:
            raise InvariantError(
                f'turno slot_entrante ({self.slot_entrante.turno}) != lado ({self.lado.value})')


# --- HipotesisCorreccion ---

@dataclass
class HipotesisCorreccion:
    """
    Propuesta de correccion con cadena de custodia.
    Generada por un PF, evaluada por el arbitro.
    No es un veredicto: es un expediente.
    """
    codigo_pf: str
    target: TargetCorreccion
    delta_venta: int
    venta_propuesta: int
    confianza: float

    # Cadena de custodia
    mecanismo_causal: MecanismoCausal
    fuente_decision: FuenteEvidencia      # que evidencia determino el lado del error
    fuente_correccion: FuenteEvidencia    # que evidencia determino el valor corregido

    # Reconciliacion de fuentes: si difieren, debe ser explicita
    reconciliacion_explicita: bool = False
    motivo_reconciliacion: str = ''

    # Evidencia y contra-evidencia
    evidencias: List[str] = field(default_factory=list)
    contradicciones: List[str] = field(default_factory=list)
    requiere_contexto: bool = False
    descripcion: str = ''

    def validar(self):
        """Invariantes internas. Lanza InvariantError si mal formada."""
        # El target debe estar bien formado
        self.target.validar()

        # Regla de reconciliacion de fuentes
        fuentes_coinciden = (self.fuente_decision.tipo == self.fuente_correccion.tipo)
        if not fuentes_coinciden and not self.reconciliacion_explicita:
            raise InvariantError(
                f'{self.codigo_pf}: fuente_decision.tipo={self.fuente_decision.tipo.value} != '
                f'fuente_correccion.tipo={self.fuente_correccion.tipo.value} '
                f'pero reconciliacion_explicita=False')
        if not fuentes_coinciden and not self.motivo_reconciliacion:
            raise InvariantError(
                f'{self.codigo_pf}: reconciliacion explicita sin motivo_reconciliacion')
        if fuentes_coinciden and self.reconciliacion_explicita:
            raise InvariantError(
                f'{self.codigo_pf}: reconciliacion_explicita=True pero fuentes coinciden')
        if fuentes_coinciden and self.motivo_reconciliacion:
            raise InvariantError(
                f'{self.codigo_pf}: motivo_reconciliacion presente pero fuentes coinciden')

        # Confianza en rango
        if not (0.0 <= self.confianza <= 1.0):
            raise InvariantError(f'{self.codigo_pf}: confianza={self.confianza} fuera de [0,1]')


# --- DecisionC3 ---

@dataclass
class DecisionC3:
    """
    Veredicto emitido por el arbitro de Capa 3.
    motivo_codigo gobierna la logica; motivo_detalle es narrativo para humanos.
    """
    resolucion: ResolucionC3
    motivo_codigo: MotivoDecisionC3
    hipotesis_ganadora: Optional[HipotesisCorreccion] = None
    hipotesis_descartadas: List[HipotesisCorreccion] = field(default_factory=list)
    motivo_detalle: str = ''


# --- CanonicalizacionResult ---

@dataclass
class CanonicalizacionResult:
    """Resultado de PF8: analisis de nombres antes de mutar."""
    sabores_normalizados: Dict[str, str] = field(default_factory=dict)    # old -> new
    colisiones: List[Tuple[str, str, str]] = field(default_factory=list)  # (old, new, turno)
    aliases_aplicados: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def tiene_colisiones(self) -> bool:
        return len(self.colisiones) > 0


# ═══════════════════════════════════════════════════════════════
# CAPA 4 — Expediente ampliado (estructura, logica en capa4)
# ═══════════════════════════════════════════════════════════════

class TipoJustificacion(Enum):
    A = 'A'   # Convergencia independiente
    B = 'B'   # Reductio / exclusión física
    C = 'C'   # Prototipo histórico fuerte
    D = 'D'   # Ajuste plausible menor


class Banda(Enum):
    CONFIRMADO = 'CONFIRMADO'
    FORZADO = 'FORZADO'
    ESTIMADO = 'ESTIMADO'


class TipoResolucion(Enum):
    RESUELTO_INDIVIDUAL = 'RESUELTO_INDIVIDUAL'
    RESUELTO_CONJUNTO = 'RESUELTO_CONJUNTO'
    IDENTITY_AMBIGUOUS = 'IDENTITY_AMBIGUOUS'
    H0 = 'H0'
    UNRESOLVED = 'UNRESOLVED'
    # Rescate colectivo: patron cross-sabor compensa la falta de convergencia individual.
    # Semanticamente distinto de RESUELTO_INDIVIDUAL (>=2 planos independientes propios).
    ELEVADO_POR_PATRON_COLECTIVO = 'ELEVADO_POR_PATRON_COLECTIVO'
    # Forzado sin convergencia: ni individual ni colectiva. Mejor hipotesis disponible
    # aplicada con banda=FORZADO. Senaliza que el caso no tiene evidencia suficiente.
    FORZADO_H0 = 'FORZADO_H0'


@dataclass
class Correccion:
    """Una corrección aplicada a un sabor."""
    nombre_norm: str
    venta_raw: int
    venta_corregida: int
    delta: int                    # corregida - raw

    tipo_justificacion: TipoJustificacion
    banda: Banda
    tipo_resolucion: TipoResolucion
    confianza: float
    motivo: str

    # Para CONJUNTO cross-sabor
    grupo_conjunto: Optional[str] = None  # ID del grupo si es bilateral


# ═══════════════════════════════════════════════════════════════
# CAPA 5 — Segunda pasada (estructura)
# ═══════════════════════════════════════════════════════════════

class StatusC5(Enum):
    LIMPIO_CONFIRMADO = 'LIMPIO_CONFIRMADO'
    LIMPIO_CON_NOTA = 'LIMPIO_CON_NOTA'
    REABRIR = 'REABRIR'


@dataclass
class SenalResidual:
    tipo: str      # 'R1', 'R2', 'R3'
    subtipo: str   # 'R2a', 'R3b', etc.
    detalle: str
    peso: float    # 0-1, qué tan fuerte es la señal


# ═══════════════════════════════════════════════════════════════
# OUTPUT FINAL — Resultado del día
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResultadoDia:
    """Output final del pipeline completo."""
    dia_label: str

    # Totales por banda
    venta_raw: int
    venta_confirmado: int         # raw + deltas CONFIRMADO
    venta_operativo: int          # confirmado + deltas FORZADO
    venta_refinado: int           # operativo + deltas ESTIMADO

    # Componentes
    n_latas: int
    vdp: int
    lid_discount: int

    # Desglose
    correcciones: List[Correccion] = field(default_factory=list)
    n_limpio: int = 0
    n_engine: int = 0
    n_escalado: int = 0
    n_solo_dia: int = 0

    @property
    def total_operativo(self) -> int:
        return self.venta_operativo - self.lid_discount + self.vdp

    @property
    def total_refinado(self) -> int:
        return self.venta_refinado - self.lid_discount + self.vdp

    @property
    def delta_estimado(self) -> int:
        return self.venta_refinado - self.venta_operativo

    @property
    def pct_estimado(self) -> float:
        if self.venta_operativo == 0:
            return 0.0
        return abs(self.delta_estimado) / self.venta_operativo * 100
