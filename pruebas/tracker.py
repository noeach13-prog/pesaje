"""
tracker.py — Physical can identity tracking across shifts.

Builds CanIdentity objects by matching weights across shifts.
Detects status changes (openings, disappearances).
Does NOT decide what stock is correct — only provides evidence.

KEY PRINCIPLE: A can's lifecycle is:
  new -> live (tracked across shifts) -> opened (became abierta) or gone (disappeared)
  Once opened or gone, that CanIdentity is DEAD. It does not produce ghost
  detections 40 shifts later. New cans with similar weights are NEW identities.
"""
import uuid
from models import (RawShift, RawFlavorObs, CanIdentity, CanSighting, SlotValue)
from config import PesajeConfig


def _new_can_id() -> str:
    return str(uuid.uuid4())[:8]


def _decay(distance: int, rate: float) -> float:
    """Confidence decay by temporal distance."""
    return 1.0 / (1.0 + rate * abs(distance))


def track_flavor(
    flavor: str,
    shifts: list,
    resets: set,
    config: PesajeConfig,
) -> list:
    """
    Build CanIdentity objects for one flavor across all shifts.

    The tracker operates in a single forward pass:
    - At each shift, it tries to match observed slot values to ACTIVE live cans.
    - If matched: extend sighting history.
    - If not matched: create a new CanIdentity.
    - If a live can is NOT matched at a shift: check if abierta jumped (opening).
    - Cans not seen for too long become 'gone'.

    Returns: list[CanIdentity]
    """
    tol = config.match_tolerance

    # Collect non-STOCK observations in order
    observations = []
    for s in shifts:
        if s.is_stock_sheet:
            observations.append((s.index, s.name, None, True))
            continue
        obs = s.flavors.get(flavor)
        is_reset_here = s.index in resets
        observations.append((s.index, s.name, obs, is_reset_here))

    all_cans = []
    active_cans = []  # currently live CanIdentities

    # Previous shift observation for opening detection
    prev_obs = None
    prev_idx = None

    for shift_idx, shift_name, obs, is_reset in observations:
        if is_reset:
            for can in active_cans:
                if can.status == 'live':
                    can.status = 'gone'
            active_cans = []
            prev_obs = None
            prev_idx = None
            if obs is None:
                continue

        if obs is None:
            # Flavor not present this shift — check if any active cans should be marked
            # (they'll time out naturally)
            prev_obs = None
            prev_idx = shift_idx
            continue

        slots_to_match = list(obs.slots)

        # ── Match active live cans to slots ──
        matched_slot_indices = set()
        matched_can_ids = set()
        unmatched_cans = []

        candidates = []
        for can in active_cans:
            if can.status != 'live':
                continue
            for si, slot in enumerate(slots_to_match):
                dist = abs(can.last_weight - slot.value)
                if dist <= tol:
                    candidates.append((can, si, dist))

        candidates.sort(key=lambda x: x[2])

        for can, si, dist in candidates:
            if can.id in matched_can_ids or si in matched_slot_indices:
                continue
            slot = slots_to_match[si]
            can.sightings.append(CanSighting(
                shift_index=shift_idx,
                shift_name=shift_name,
                weight=slot.value,
                column=slot.column,
                slot_type=slot.slot_type,
            ))
            matched_slot_indices.add(si)
            matched_can_ids.add(can.id)

        # ── Detect openings for unmatched active cans ──
        # RULE: One abierta jump = at most one can opening per flavor per shift.
        # Pick the heaviest unmatched can (most likely to explain the jump).
        unmatched_live = [can for can in active_cans
                         if can.status == 'live' and can.id not in matched_can_ids]

        opening_attributed = False
        if unmatched_live and prev_obs is not None:
            abierta_before = prev_obs.abierta
            abierta_after = obs.abierta
            jump = abierta_after - abierta_before

            if jump > 1500:
                # Mark only the heaviest unmatched can as opened
                # Filter: cerradas < 5000g are likely typos (e.g., 4385 should be 6385)
                eligible = [c for c in unmatched_live if c.last_weight >= 5000]
                if eligible:
                    best = max(eligible, key=lambda c: c.last_weight)
                    best.status = 'opened'
                    best.opened_at = shift_idx
                    opening_attributed = True

        # Remaining unmatched cans: check staleness
        for can in unmatched_live:
            if can.status != 'live':
                continue  # already marked opened above
            distance = shift_idx - can.last_seen
            if distance > 3:
                can.status = 'gone'

        # ── Create new cans for unmatched slots ──
        for si, slot in enumerate(slots_to_match):
            if si not in matched_slot_indices:
                new_can = CanIdentity(
                    id=_new_can_id(),
                    flavor=flavor,
                    sightings=[CanSighting(
                        shift_index=shift_idx,
                        shift_name=shift_name,
                        weight=slot.value,
                        column=slot.column,
                        slot_type=slot.slot_type,
                    )],
                    status='live',
                )
                active_cans.append(new_can)
                all_cans.append(new_can)

        # ── Prune dead cans from active list ──
        active_cans = [c for c in active_cans if c.status == 'live']

        prev_obs = obs
        prev_idx = shift_idx

    return all_cans
