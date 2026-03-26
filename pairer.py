"""
pairer.py — Temporal ordering, reset detection, period generation, VDP association.

VDP RULE: Ventas después del peso belong to the SAME calendar day they were
recorded in. They never carry over to the next day. VDP is a day-level
sales layer, separate from stock-based inference.
"""
import re
from models import RawShift
from config import PesajeConfig
from parser import text_to_grams


def build_timeline(shifts: list) -> list:
    """Sort shifts chronologically by workbook index. Already ordered but verify."""
    return sorted(shifts, key=lambda s: s.index)


def find_resets(shifts: list) -> set:
    """Return shift indices where tracker must reset.
    Reset triggers: STOCK sheets, temporal gap > 1 position between non-STOCK sheets."""
    resets = set()
    for s in shifts:
        if s.is_stock_sheet:
            resets.add(s.index)

    # Detect gaps: if two consecutive non-STOCK sheets have index gap > 2
    non_stock = [s for s in shifts if not s.is_stock_sheet]
    for i in range(1, len(non_stock)):
        gap = non_stock[i].index - non_stock[i - 1].index
        if gap > 2:  # more than 1 sheet between them (allows for 1 STOCK in between)
            resets.add(non_stock[i].index)
    return resets


def generate_periods(shifts: list, resets: set) -> list:
    """Generate period definitions: (idx_a, idx_b, is_reset_boundary).
    Only pairs consecutive non-STOCK shifts."""
    non_stock = [s for s in shifts if not s.is_stock_sheet]
    periods = []
    for i in range(len(non_stock) - 1):
        a = non_stock[i]
        b = non_stock[i + 1]
        # Is there a reset between them?
        is_reset = any(a.index < r <= b.index for r in resets)
        periods.append((a.index, b.index, is_reset))
    return periods


def _extract_multiplier(text: str) -> tuple:
    """Extract 'X N' multiplier from text like '1/4 X 2' -> ('1/4', 2).
    Returns (cleaned_text, multiplier)."""
    m = re.search(r'\s*[xX]\s*(\d+)\s*$', text)
    if m:
        multiplier = int(m.group(1))
        cleaned = text[:m.start()].strip()
        return cleaned, multiplier
    return text, 1


def convert_vdp(texts: list, config: PesajeConfig) -> float:
    """Convert VDP texts to grams using config table + text_to_grams fallback.
    Handles 'X N' multipliers (e.g., '1/4 X 2' = 250 * 2 = 500g)."""
    total = 0.0
    for text in texts:
        upper = text.strip().upper()

        # Extract multiplier first: "1/4 X 2" -> base="1/4", mult=2
        base_text, multiplier = _extract_multiplier(upper)

        # Try config table on the base text (without multiplier)
        matched = False
        for key, grams in config.vdp_table.items():
            if key.upper() in base_text:
                total += grams * multiplier
                matched = True
                break
        if not matched:
            # Fallback to parser's text_to_grams on original text
            total += text_to_grams(text)
    return total


# ── DEPRECATED: carry-over model ──────────────────────────────────────────────
def associate_vdp(shifts: list, periods: list, config: PesajeConfig) -> dict:
    """DEPRECATED — kept for backward compat. Use collect_vdp_by_day instead.
    Maps each period to VDP grams from shift A. NOT used in V2 pipeline."""
    shift_by_index = {s.index: s for s in shifts}
    vdp_map = {}
    for idx_a, idx_b, is_reset in periods:
        sa = shift_by_index.get(idx_a)
        if sa and sa.vdp_texts:
            vdp_map[(idx_a, idx_b)] = convert_vdp(sa.vdp_texts, config)
        else:
            vdp_map[(idx_a, idx_b)] = 0.0
    return vdp_map


# ── VDP: same-day model ──────────────────────────────────────────────────────

def extract_day_number(shift_name: str) -> str:
    """Extract calendar day number from shift name.
    'Sábado 28 (DIA)' -> '28', 'Domingo 1' -> '1', 'STOCK 28-02' -> '28'."""
    # Try standard pattern: "Weekday N ..."
    m = re.search(r'(\d+)', shift_name)
    return m.group(1) if m else shift_name


def collect_vdp_by_shift(shifts: list, config: PesajeConfig) -> dict:
    """Return {shift_index: vdp_grams} for all shifts with VDP."""
    result = {}
    for s in shifts:
        if s.is_stock_sheet:
            continue
        if s.vdp_texts:
            result[s.index] = convert_vdp(s.vdp_texts, config)
    return result


def collect_vdp_by_day(shifts: list, config: PesajeConfig) -> dict:
    """Return {day_label: total_vdp_grams} aggregated by calendar day.
    VDP from ALL shifts of the same day are summed together."""
    day_vdp = {}
    for s in shifts:
        if s.is_stock_sheet:
            continue
        if not s.vdp_texts:
            continue
        day = extract_day_number(s.name)
        grams = convert_vdp(s.vdp_texts, config)
        day_vdp[day] = day_vdp.get(day, 0.0) + grams
    return day_vdp


def group_shifts_by_day(shifts: list) -> dict:
    """Return {day_label: [RawShift, ...]} grouping non-STOCK shifts by calendar day."""
    groups = {}
    for s in shifts:
        if s.is_stock_sheet:
            continue
        day = extract_day_number(s.name)
        groups.setdefault(day, []).append(s)
    return groups


def group_periods_by_day(shifts: list, periods: list) -> dict:
    """Return {day_label: [(idx_a, idx_b, is_reset), ...]} for same-day periods.
    A period belongs to a day if BOTH shifts share the same calendar day number."""
    shift_by_index = {s.index: s for s in shifts}
    day_periods = {}
    for idx_a, idx_b, is_reset in periods:
        sa = shift_by_index.get(idx_a)
        sb = shift_by_index.get(idx_b)
        if sa is None or sb is None:
            continue
        day_a = extract_day_number(sa.name)
        day_b = extract_day_number(sb.name)
        if day_a == day_b:
            day_periods.setdefault(day_a, []).append((idx_a, idx_b, is_reset))
    return day_periods
