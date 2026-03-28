"""
reconciler.py — Multi-turn stock reconciliation.

Reconstructs the most probable stock timeline across shifts, accounting for
omissions, undocumented entrants, and noisy observations.

Principles:
- Maintain raw vs reconciled separation
- Use multi-turn windows for inference
- Leave traceability for each correction
- Mark as unresolved if confidence insufficient
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Dict, Set
from models import ShiftData, FlavorShiftData


@dataclass
class ReconciliationEvent:
    """Event explaining a stock correction."""
    tipo: str  # 'omitted_closed', 'undocumented_entrant', 'skipped_lata', etc.
    description: str
    confidence: float  # 0.0 to 1.0
    adjustment_grams: float  # net grams added to stock


@dataclass
class ReconciledFlavor:
    """Reconciled flavor data with events."""
    name: str
    raw: FlavorShiftData
    reconciled: FlavorShiftData
    events: List[ReconciliationEvent] = field(default_factory=list)
    unresolved: bool = False


@dataclass
class ReconciledShift:
    """Shift with reconciled flavors."""
    name: str
    index: int
    flavors: dict = field(default_factory=dict)  # norm_name -> ReconciledFlavor

    def to_shift_data(self) -> ShiftData:
        """Convert to ShiftData using reconciled flavors."""
        from models import ShiftData, FlavorShiftData
        shift = ShiftData(name=self.name, index=self.index)
        shift.flavors = {fname: rf.reconciled for fname, rf in self.flavors.items()}
        # Keep other fields empty for now, as reconciliation doesn't touch them
        return shift


# Tolerances
TOL_TIGHT = 20    # same lata, next shift
TOL_MEDIUM = 50   # entrante matched as re-weighed cerrada
TOL_WIDE = 200    # lata reappears after skipping a shift


def _match(val: float, candidates: List[float], tol: float) -> tuple:
    """Return (best_match_val, index) or (None, -1)."""
    best, best_idx, best_diff = None, -1, tol + 1
    for i, c in enumerate(candidates):
        d = abs(val - c)
        if d <= tol and d < best_diff:
            best, best_idx, best_diff = c, i, d
    return best, best_idx


def reconcile_flavor_across_shifts(flavor_name: str, shifts: List[ShiftData]) -> Dict[str, ReconciledFlavor]:
    """
    Reconcile a single flavor across all shifts.
    Returns dict shift_name -> ReconciledFlavor
    """
    reconciled = {}

    # Track known closed latas: list of (weight, last_seen_shift_index)
    known_closed: List[tuple] = []

    for i, shift in enumerate(shifts):
        raw_flavor = shift.flavors.get(flavor_name)
        if not raw_flavor:
            raw_flavor = FlavorShiftData(name=flavor_name)

        reconciled_flavor = ReconciledFlavor(
            name=flavor_name,
            raw=raw_flavor,
            reconciled=FlavorShiftData(
                name=flavor_name,
                abierta=raw_flavor.abierta,
                celiaca=raw_flavor.celiaca,
                cerradas=[],
                entrantes=[]
            )
        )

        # Start with observed entrantes in reconciled
        reconciled_flavor.reconciled.entrantes = list(raw_flavor.entrantes)

        # Match observed cerradas to known or add as new
        remaining_known = list(known_closed)
        for obs_closed in raw_flavor.cerradas:
            match, idx = _match(obs_closed, [w for w, _ in remaining_known], TOL_TIGHT)
            if match is not None:
                # Matched existing, keep
                reconciled_flavor.reconciled.cerradas.append(obs_closed)
                # Update last seen
                remaining_known[idx] = (obs_closed, i)
            else:
                # New closed, check if there's a matching entrant in this shift
                ent_match, _ = _match(obs_closed, raw_flavor.entrantes, TOL_MEDIUM)
                if ent_match is not None:
                    # Entrant justifies it
                    reconciled_flavor.reconciled.cerradas.append(obs_closed)
                    known_closed.append((obs_closed, i))
                else:
                    # Undocumented new closed, infer undocumented entrant
                    reconciled_flavor.reconciled.cerradas.append(obs_closed)
                    known_closed.append((obs_closed, i))
                    reconciled_flavor.events.append(ReconciliationEvent(
                        tipo='undocumented_entrant',
                        description=f'New closed {obs_closed:.0f}g without documented entrant - inferred undocumented entrant',
                        confidence=0.6,
                        adjustment_grams=obs_closed
                    ))
                    # Add to reconciled entrantes for stock calc
                    reconciled_flavor.reconciled.entrantes.append(obs_closed)

        # Update known_closed: handle omissions and skips
        new_known = []
        for w, last_idx in known_closed:
            if last_idx == i - 1 and w not in [c for c in reconciled_flavor.reconciled.cerradas]:
                # Was in previous, not in current - check if in next
                if i + 1 < len(shifts):
                    next_shift = shifts[i + 1]
                    next_raw = next_shift.flavors.get(flavor_name)
                    if next_raw:
                        next_match, _ = _match(w, next_raw.cerradas, TOL_WIDE)
                        if next_match:
                            # Skipped this shift, infer omitted
                            reconciled_flavor.reconciled.cerradas.append(w)
                            reconciled_flavor.events.append(ReconciliationEvent(
                                tipo='omitted_closed',
                                description=f'Closed {w:.0f}g from previous shift omitted in this observation - added back',
                                confidence=0.8,
                                adjustment_grams=w
                            ))
                            new_known.append((w, i))
                        else:
                            # Disappeared, perhaps opened
                            pass  # don't keep
                    else:
                        new_known.append((w, last_idx))
                else:
                    new_known.append((w, last_idx))
            elif last_idx >= i - 1:
                new_known.append((w, last_idx))
        known_closed = new_known

        # Add new from entrantes
        for ent in raw_flavor.entrantes:
            if not any(abs(ent - w) <= TOL_MEDIUM for w, _ in known_closed):
                known_closed.append((ent, i))

        reconciled[shift.name] = reconciled_flavor

    return reconciled


def reconcile_shifts(shifts: List[ShiftData]) -> List[ReconciledShift]:
    """
    Reconcile stock across all shifts for each flavor.
    Returns list of ReconciledShift with raw, reconciled, and events.
    """
    reconciled_shifts = []

    # Get all flavors across all shifts
    all_flavors = set()
    for shift in shifts:
        all_flavors.update(shift.flavors.keys())

    # Reconcile each flavor separately
    flavor_reconciled = {}
    for fname in all_flavors:
        flavor_reconciled[fname] = reconcile_flavor_across_shifts(fname, shifts)

    # Build reconciled shifts
    for shift in shifts:
        reconciled_shift = ReconciledShift(
            name=shift.name,
            index=shift.index
        )

        for fname in all_flavors:
            if fname in flavor_reconciled and shift.name in flavor_reconciled[fname]:
                reconciled_shift.flavors[fname] = flavor_reconciled[fname][shift.name]
            else:
                # Should not happen
                raw = shift.flavors.get(fname) or FlavorShiftData(name=fname)
                reconciled_shift.flavors[fname] = ReconciledFlavor(
                    name=fname,
                    raw=raw,
                    reconciled=raw
                )

        reconciled_shifts.append(reconciled_shift)

    return reconciled_shifts
