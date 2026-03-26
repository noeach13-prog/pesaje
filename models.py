from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class FlavorShiftData:
    name: str
    abierta: float = 0.0
    celiaca: float = 0.0
    cerradas: list = field(default_factory=list)   # list of floats
    entrantes: list = field(default_factory=list)  # list of floats

    @property
    def total(self) -> float:
        return self.abierta + self.celiaca + sum(self.cerradas) + sum(self.entrantes)

    @property
    def n_cerradas(self) -> int:
        return len(self.cerradas)


@dataclass
class SaleEntry:
    raw_text: str
    grams: float


@dataclass
class ConsumoEntry:
    employee: str
    description: str
    grams: float


@dataclass
class ObservacionEntry:
    flavor: str
    abierta: Optional[float] = None
    cerrada: Optional[float] = None
    entrante: Optional[float] = None
    nota: Optional[str] = None  # free text


@dataclass
class ShiftData:
    name: str
    index: int  # position in workbook (0-based)
    flavors: dict = field(default_factory=dict)        # norm_name -> FlavorShiftData
    ventas_sin_peso: list = field(default_factory=list)  # list[SaleEntry]
    consumos: list = field(default_factory=list)         # list[ConsumoEntry]
    observaciones: list = field(default_factory=list)    # list[ObservacionEntry]

    @property
    def is_valid(self) -> bool:
        return bool(self.flavors)


@dataclass
class AnomalyInfo:
    tipo: int
    message: str
    severity: str = 'warning'   # 'warning' | 'error'
    corr_stock_a: float = 0.0   # grams to ADD to stock_A correction
    corr_stock_b: float = 0.0   # grams to ADD to stock_B correction


@dataclass
class FlavorPeriodoResult:
    name: str
    # Turno A
    a_abierta: float
    a_celiaca: float
    a_cerradas: list
    a_entrantes: list
    a_total: float
    # Turno B
    b_abierta: float
    b_celiaca: float
    b_cerradas: list
    b_entrantes: list
    b_total: float
    # New entrantes in B (not present in A)
    new_entrantes_b: list
    # Calculations
    latas_abiertas: int
    ajuste: float
    stock_a_corr: float
    stock_b_corr: float
    venta_neta: float
    # Anomalies
    anomalies: list = field(default_factory=list)  # list[AnomalyInfo]


# ══════════════════════════════════════════════════════════════════════════════
# V2 — Trajectory-based inference models (additive, does not break V1)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SlotValue:
    """A single numeric value from a cell, preserving its column position."""
    column: str           # 'D', 'E', 'G', 'J', etc.
    value: float
    slot_type: str        # 'cerrada' | 'entrante' (by column range)


@dataclass
class RawFlavorObs:
    """Raw observation of a flavor in one shift — exactly what the workbook says."""
    name: str
    abierta: float = 0.0
    celiaca: float = 0.0
    slots: List[SlotValue] = field(default_factory=list)

    @property
    def cerradas(self) -> List[float]:
        return [s.value for s in self.slots if s.slot_type == 'cerrada']

    @property
    def entrantes(self) -> List[float]:
        return [s.value for s in self.slots if s.slot_type == 'entrante']

    @property
    def total(self) -> float:
        return self.abierta + self.celiaca + sum(s.value for s in self.slots)


@dataclass
class RawShift:
    """Raw shift data with slot-level detail."""
    name: str
    index: int
    flavors: dict = field(default_factory=dict)       # norm_name -> RawFlavorObs
    vdp_texts: List[str] = field(default_factory=list)
    is_stock_sheet: bool = False


@dataclass
class V2ShiftAnnotations:
    """Operational metadata — never enters inference."""
    shift_name: str
    latas_cambiadas_raw: Optional[str] = None
    consumos_raw: List[str] = field(default_factory=list)
    observaciones_raw: List[str] = field(default_factory=list)


@dataclass
class CanSighting:
    """One observation of a physical can at a specific shift."""
    shift_index: int
    shift_name: str
    weight: float
    column: str
    slot_type: str


@dataclass
class CanIdentity:
    """Inferred physical can tracked across shifts."""
    id: str
    flavor: str
    sightings: List[CanSighting] = field(default_factory=list)
    status: str = 'live'            # 'live' | 'opened' | 'gone'
    opened_at: Optional[int] = None  # shift_index where opening detected

    @property
    def last_weight(self) -> float:
        return self.sightings[-1].weight if self.sightings else 0.0

    @property
    def last_seen(self) -> int:
        return self.sightings[-1].shift_index if self.sightings else -1

    @property
    def first_seen(self) -> int:
        return self.sightings[0].shift_index if self.sightings else -1

    def seen_at(self, shift_index: int) -> bool:
        return any(s.shift_index == shift_index for s in self.sightings)

    def weight_at(self, shift_index: int) -> Optional[float]:
        for s in self.sightings:
            if s.shift_index == shift_index:
                return s.weight
        return None


@dataclass
class TrajectoryCorrection:
    """One correction applied at a shift in the trajectory."""
    rule: str              # 'omission', 'ghost', 'duplicate', 'phantom', 'opened_entrante'
    description: str
    confidence: float
    value_affected: float
    action: str            # 'added' | 'removed'


@dataclass
class TrajectoryPoint:
    """Inferred stock for one flavor at one shift."""
    shift_index: int
    shift_name: str
    raw: RawFlavorObs
    inferred_abierta: float
    inferred_celiaca: float
    inferred_cerradas: List[float] = field(default_factory=list)
    inferred_entrantes: List[float] = field(default_factory=list)
    corrections: List[TrajectoryCorrection] = field(default_factory=list)
    source: str = 'raw_fallback'   # 'tracker' | 'raw_fallback'
    confidence: float = 1.0

    @property
    def inferred_total(self) -> float:
        return (self.inferred_abierta + self.inferred_celiaca +
                sum(self.inferred_cerradas) + sum(self.inferred_entrantes))


@dataclass
class V2FlavorPeriodResult:
    """Sold grams for one flavor in one period, computed from trajectories."""
    flavor: str
    sold_grams: float
    raw_sold: float
    confidence: float
    corrections_a: List[TrajectoryCorrection] = field(default_factory=list)
    corrections_b: List[TrajectoryCorrection] = field(default_factory=list)


@dataclass
class V2PeriodResult:
    """Results for one period (shift pair). Pure stock-based, no VDP."""
    shift_a: str
    shift_b: str
    is_reset: bool = False
    flavors: dict = field(default_factory=dict)   # norm_name -> V2FlavorPeriodResult


@dataclass
class V2DayResult:
    """Aggregated results for one calendar day.

    TOTAL_DAY = STOCK_BASED_SOLD + VDP - (OPENED_CAN_COUNT * 280)

    All three components belong to the same calendar day.
    Nothing carries over to a different day."""
    day_label: str                                  # e.g. '28'
    periods: List[str] = field(default_factory=list)  # e.g. ['DIA->NOCHE']
    shifts: List[str] = field(default_factory=list)   # shift names in this day
    flavors: dict = field(default_factory=dict)       # norm_name -> stock_sold (float)
    vdp_grams: float = 0.0                            # total VDP for the day
    stock_sold_total: float = 0.0                     # sum of stock-based sold
    opened_cans: int = 0                              # cans opened this day (inferred)
    opened_cans_detail: List[str] = field(default_factory=list)  # e.g. ['CHOCOLATE can abc1']
    lid_discount_grams: float = 0.0                   # opened_cans * 280
    day_sold_total: float = 0.0                       # stock_sold + vdp - lid_discount


# ══════════════════════════════════════════════════════════════════════════════
# V1 — Original models (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PeriodoResult:
    turno_a_name: str
    turno_b_name: str
    extended: bool     # periodo extendido (STOCK sheet or gap detected)
    dias_entre: int
    flavors: dict = field(default_factory=dict)          # norm_name -> FlavorPeriodoResult
    ventas_sin_peso: list = field(default_factory=list)  # from both shifts combined
    consumos: list = field(default_factory=list)         # from both shifts combined
    observaciones: list = field(default_factory=list)    # from shift B
