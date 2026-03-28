"""
inference.py — Trajectory-based stock inference engine.

For each flavor, builds the most probable stock trajectory across all shifts
using can-identity evidence from the tracker.

The trajectory is built by:
1. Starting from raw observation at each shift
2. Checking tracker evidence: which cans were definitely present? which are suspicious?
3. Applying corrections ONLY where evidence is strong
4. Falling back to raw (H0) wherever evidence is insufficient

This is the CORE of the engine.
"""
from models import (
    RawShift, RawFlavorObs, CanIdentity, TrajectoryPoint,
    TrajectoryCorrection, SlotValue,
)
from config import PesajeConfig
from tracker import _decay


def build_trajectories(
    shifts: list,
    resets: set,
    config: PesajeConfig,
) -> tuple:
    """
    For every flavor, build the stock trajectory across all shifts.
    Returns:
        trajectories: {flavor_name: [TrajectoryPoint, ...]}
        tracked_cans: {flavor_name: [CanIdentity, ...]}
    """
    from tracker import track_flavor

    all_flavors = set()
    for s in shifts:
        if not s.is_stock_sheet:
            all_flavors.update(s.flavors.keys())

    trajectories = {}
    tracked_cans = {}
    for flavor in sorted(all_flavors):
        cans = track_flavor(flavor, shifts, resets, config)
        trajectory = _build_flavor_trajectory(flavor, cans, shifts, resets, config)
        trajectories[flavor] = trajectory
        tracked_cans[flavor] = cans

    return trajectories, tracked_cans


def _shifts_since_last_reset(shift_idx, shifts, resets):
    """Count how many non-STOCK shifts have passed since last reset."""
    count = 0
    for s in reversed(sorted(shifts, key=lambda x: x.index)):
        if s.index >= shift_idx:
            continue
        if s.is_stock_sheet or s.index in resets:
            break
        count += 1
    return count + 1  # include current


def _build_flavor_trajectory(flavor, cans, shifts, resets, config):
    """Build trajectory for one flavor using tracker evidence."""
    trajectory = []
    non_stock = [s for s in shifts if not s.is_stock_sheet]
    shift_by_index = {s.index: s for s in non_stock}

    prev_raw = None
    prev_shift_name = None

    for s in non_stock:
        raw = s.flavors.get(flavor)
        if raw is None:
            prev_raw = None
            prev_shift_name = None
            continue

        point = TrajectoryPoint(
            shift_index=s.index,
            shift_name=s.name,
            raw=raw,
            inferred_abierta=raw.abierta,
            inferred_celiaca=raw.celiaca,
            inferred_cerradas=list(raw.cerradas),
            inferred_entrantes=list(raw.entrantes),
            source='raw_fallback',
            confidence=1.0,
        )

        # Check if enough history for inference
        history_depth = _shifts_since_last_reset(s.index, shifts, resets)
        if history_depth < config.min_history:
            trajectory.append(point)
            prev_raw = raw
            prev_shift_name = s.name
            continue

        corrections = []

        # Sorted non-stock indices for neighbor lookups
        non_stock_indices = sorted(shift_by_index.keys())

        # 0. ENTRANTE DUPLICATE: Entrante from DIA persists in NOCHE and
        #    matches a new cerrada — the entrante is a duplicate (promoted
        #    to cerrada but employee didn't clear the entrante entry).
        corrections += _detect_entrante_duplicates(
            flavor, s.index, raw, prev_raw, prev_shift_name, s.name, config)

        # 0.5 DIGIT TYPO: Raw value ≈ ref_weight ± 1000/2000g for a
        #     well-established can.  Must run BEFORE omissions so the
        #     corrected value makes the can "present" and the expanded
        #     digit-error check in omissions marks it as already=True.
        corrections += _detect_digit_typos(flavor, s.index, raw, cans, config)

        # 1. OMISSION: Can tracked before and after this shift, but not here
        corrections += _detect_omissions(flavor, s.index, raw, cans, config)

        # 2. GHOST (recent): Can was opened in the IMMEDIATELY preceding shift
        #    and its weight reappears here (copy-paste error)
        corrections += _detect_recent_ghosts(flavor, s.index, raw, cans, config)

        # 3. DUPLICATE: Two raw values at this shift match the same tracked can
        corrections += _detect_duplicates(flavor, s.index, raw, cans, config)

        # 4. PHANTOM: Value matches no tracked can and coexists with matched values
        corrections += _detect_phantoms(flavor, s.index, raw, cans, config)

        # 5. OPENED ENTRANTE: Entrante persists but was consumed (abierta appeared)
        corrections += _detect_opened_entrantes(flavor, s.index, raw, cans,
                                                 shift_by_index, config)

        # 6. IMPOSSIBLE ABIERTA: Abierta drops >2000g then recovers >1500g
        #    with coherent prev/next — data entry error on abierta.
        corrections += _detect_impossible_abierta(flavor, s.index, raw,
                                                   shift_by_index,
                                                   non_stock_indices, config)

        if corrections:
            # Stacking limit: when both removal and addition corrections exist,
            # only keep additions with confidence > 0.7. This prevents
            # over-correction (e.g., SAMBAYON: ghost removal is correct, but
            # stacking a low-confidence omission on top over-corrects).
            has_removals = any(c.action == 'removed' for c in corrections)
            has_additions = any(c.action == 'added' for c in corrections)
            if has_removals and has_additions:
                corrections = [c for c in corrections
                               if c.action == 'removed' or c.confidence > 0.7]

            if corrections:
                _apply_corrections(point, corrections)
                point.source = 'tracker'
                point.confidence = min(c.confidence for c in corrections)
            else:
                point.source = 'raw_fallback'
                point.confidence = 1.0
        else:
            point.source = 'raw_fallback'
            point.confidence = 1.0

        trajectory.append(point)
        prev_raw = raw
        prev_shift_name = s.name

    return trajectory


def _detect_entrante_duplicates(flavor, shift_idx, raw, prev_raw, prev_shift_name,
                                 shift_name, config):
    """Detect entrantes that persist from DIA to NOCHE and are duplicates.

    Business rule: "en el turno noche no deberían figurar las latas en entrantes,
    deberían figurar en cerradas o abiertas según corresponda."

    When an entrante from DIA persists in NOCHE AND a new cerrada appeared at
    NOCHE with similar weight (within 50g), the entrante is a duplicate —
    the physical can was promoted to cerrada but the employee didn't clear
    the entrante entry.
    """
    corrections = []

    if prev_raw is None:
        return corrections

    # Only applies on DIA→NOCHE transitions within the same day
    if prev_shift_name is None or shift_name is None:
        return corrections
    if '(DIA)' not in prev_shift_name.upper() or '(NOCHE)' not in shift_name.upper():
        return corrections

    # Get entrantes from current shift
    curr_entrantes = [(s, s.value) for s in raw.slots if s.slot_type == 'entrante']
    if not curr_entrantes:
        return corrections

    prev_entrante_vals = prev_raw.entrantes
    if not prev_entrante_vals:
        return corrections

    # Get cerradas that are NEW at this shift (not present in prev shift)
    prev_cerrada_vals = prev_raw.cerradas
    curr_cerradas = [(s, s.value) for s in raw.slots if s.slot_type == 'cerrada']

    new_cerradas = []
    for cs, cv in curr_cerradas:
        matched_prev = any(abs(cv - pv) <= config.match_tolerance for pv in prev_cerrada_vals)
        if not matched_prev:
            new_cerradas.append((cs, cv))

    # For each entrante in NOCHE, check if it persists from DIA
    dup_tol = 50.0  # tolerance for entrante→cerrada promotion matching
    used_cerradas = set()

    for es, ev in curr_entrantes:
        # Does this entrante persist from DIA? (same weight within tolerance)
        persists = any(abs(ev - pev) <= config.match_tolerance for pev in prev_entrante_vals)
        if not persists:
            continue

        # Does a NEW cerrada at NOCHE match this entrante? (promoted)
        for i, (cs, cv) in enumerate(new_cerradas):
            if i in used_cerradas:
                continue
            if abs(ev - cv) <= dup_tol:
                # Match: the entrante was promoted to cerrada but entry wasn't cleared
                used_cerradas.add(i)
                corrections.append(TrajectoryCorrection(
                    rule='entrante_duplicate',
                    description=(f"Entrante {ev:.0f}g persists from {prev_shift_name} "
                                f"but matches new cerrada {cv:.0f}g — "
                                f"promoted, duplicate entry"),
                    confidence=0.90,
                    value_affected=ev,
                    action='removed',
                ))
                break

    return corrections


def _detect_digit_typos(flavor, shift_idx, raw, cans, config):
    """Detect digit typos in raw cerrada/entrante values.

    Common data-entry error: first digit wrong, producing ~1000g or ~2000g
    offset from the can's established weight.  E.g., 5705 typed instead of
    6705 for a can tracked at ~6715g across 11 shifts.

    Only fires for well-established cans (≥5 sightings) seen both before
    and after this shift, ensuring strong identity evidence.

    Generates two corrections per typo: remove the wrong value, add the
    digit-corrected value (raw + offset that matches the can).
    """
    tol = config.match_tolerance
    all_raw_vals = raw.cerradas + raw.entrantes

    for can in cans:
        if can.status == 'opened' and can.opened_at is not None and can.opened_at <= shift_idx:
            continue

        seen_before = [sg for sg in can.sightings if sg.shift_index < shift_idx]
        seen_after = [sg for sg in can.sightings if sg.shift_index > shift_idx]
        if not seen_before or not seen_after:
            continue

        n_total = len(can.sightings)
        if n_total < 5:
            continue

        ref_weight = can.weight_at(shift_idx)
        if ref_weight is None:
            nearest = max(seen_before, key=lambda sg: sg.shift_index)
            ref_weight = nearest.weight

        # Skip if the can is already present (normal match or adaptive tolerance)
        omission_tol = tol * 1.5
        if any(abs(ref_weight - v) <= omission_tol for v in all_raw_vals):
            continue

        # Check each raw slot for a digit error pattern
        for slot in raw.slots:
            v = slot.value

            # Skip if this slot is claimed by another well-established can
            claimed = False
            for other in cans:
                if other.id == can.id:
                    continue
                if len(other.sightings) < config.min_history:
                    continue
                if other.status == 'opened' and other.opened_at and other.opened_at <= shift_idx:
                    continue
                other_ref = other.weight_at(shift_idx)
                if other_ref is None:
                    o_before = [sg for sg in other.sightings if sg.shift_index < shift_idx]
                    if o_before:
                        other_ref = max(o_before, key=lambda sg: sg.shift_index).weight
                if other_ref and abs(other_ref - v) <= tol:
                    claimed = True
                    break
            if claimed:
                continue

            for offset in [1000, -1000, 2000, -2000]:
                corrected = v + offset
                if abs(ref_weight - corrected) <= tol:
                    conf = 0.92 if n_total >= 8 else 0.80
                    return [
                        TrajectoryCorrection(
                            rule='digit_typo',
                            description=(
                                f"Digit typo: raw {v:.0f}g should be {corrected:.0f}g "
                                f"(can {can.id}, {n_total} sightings at ~{ref_weight:.0f}g, "
                                f"offset {offset:+d}g)"),
                            confidence=conf,
                            value_affected=v,
                            action='removed',
                        ),
                        TrajectoryCorrection(
                            rule='digit_typo',
                            description=(
                                f"Digit typo correction: adding {corrected:.0f}g "
                                f"for can {can.id}"),
                            confidence=conf,
                            value_affected=corrected,
                            action='added',
                        ),
                    ]

    return []


def _detect_omissions(flavor, shift_idx, raw, cans, config):
    """Detect cans that should be present but aren't in raw observation.

    Key constraint: only infer omission when the can had the SAME slot_type
    (cerrada or entrante) on both sides. A can transitioning from entrante
    to cerrada is a normal state change, not an omission.
    """
    corrections = []
    tol = config.match_tolerance

    all_raw_vals = raw.cerradas + raw.entrantes

    # Use wider tolerance for "already present" check in omissions.
    # This prevents false omissions when a can's weight oscillates slightly
    # beyond match_tolerance (e.g., 6710 vs 6750 = 40g for GRANIZADO).
    omission_tol = tol * 1.5

    for can in cans:
        if can.status == 'opened' and can.opened_at is not None and can.opened_at <= shift_idx:
            continue

        seen_before = [sg for sg in can.sightings if sg.shift_index < shift_idx]
        seen_after = [sg for sg in can.sightings if sg.shift_index > shift_idx]

        if not seen_before or not seen_after:
            continue

        # Require minimum sighting count: a can with too few sightings has
        # weak identity evidence. Don't infer omission for uncertain cans.
        # (e.g., D. GRANIZADO 6675g: 2 sightings, weight oscillates 100g)
        if len(can.sightings) < config.min_history:
            continue

        # Adaptive tolerance: well-established cans (many sightings) get wider
        # "already present" check. A can tracked across 8+ shifts might be
        # weighed 50-100g differently at one shift (same physical can,
        # measurement variance). We should not add a false omission.
        # E.g., CADBURY 6355→6455 (100g), PISTACHO 6355→6405 (50g).
        n_total = len(can.sightings)
        if n_total >= 8:
            check_tol = tol * 3.5   # ~105g
        elif n_total >= 5:
            check_tol = tol * 2.5   # ~75g
        else:
            check_tol = omission_tol  # tol * 1.5 = 45g

        # Compute reference weight once
        ref_weight = can.weight_at(shift_idx)
        if ref_weight is None:
            nearest = max(seen_before, key=lambda sg: sg.shift_index)
            ref_weight = nearest.weight

        # Check 1: can has a sighting at this shift matching a raw value
        already = any(abs(sg.weight - v) <= check_tol
                     for sg in can.sightings if sg.shift_index == shift_idx
                     for v in all_raw_vals)

        # Check 2: reference weight matches raw value
        # Two tiers:
        # a) Within standard omission_tol → always accept (same as before).
        # b) Within wider check_tol (adaptive) → only accept if no other
        #    well-established can has a CLOSER claim to this raw value.
        #    E.g., CH C/ALM: raw 6445 is closer to can 6445 (diff 0) than
        #    can 6525 (diff 80), so it doesn't prove can 6525 is present.
        if not already:
            for v in all_raw_vals:
                dist = abs(ref_weight - v)
                if dist <= omission_tol:
                    # Within standard tolerance — always accept
                    already = True
                    break
                elif dist <= check_tol:
                    # Within wider adaptive tolerance — check if claimed
                    claimed_by_closer = False
                    for other in cans:
                        if other.id == can.id:
                            continue
                        if (other.status == 'opened' and other.opened_at
                                and other.opened_at <= shift_idx):
                            continue
                        # Claiming can must be well-established: at least
                        # min_history AND at least half the omitted can's
                        # sightings. A 3-sighting can shouldn't override
                        # a 9-sighting can (likely same physical can).
                        min_claim = max(config.min_history,
                                       int(n_total * 0.5))
                        if len(other.sightings) < min_claim:
                            continue
                        other_ref = other.weight_at(shift_idx)
                        if other_ref is None:
                            o_before = [sg for sg in other.sightings
                                       if sg.shift_index < shift_idx]
                            if o_before:
                                other_ref = max(o_before,
                                               key=lambda sg: sg.shift_index).weight
                        if other_ref and abs(other_ref - v) < dist:
                            claimed_by_closer = True
                            break
                    if not claimed_by_closer:
                        already = True
                        break

        # Check 3: digit error — e.g., 5705 typed instead of 6705 (~1000g),
        # or 4385 typed instead of 6385 (~2000g). First digit wrong.
        if not already and n_total >= 5:
            for v in all_raw_vals:
                for _offset in [1000, -1000, 2000, -2000]:
                    if abs(ref_weight - (v + _offset)) <= tol:
                        already = True
                        break
                if already:
                    break

        if already:
            continue

        nearest_before = max(seen_before, key=lambda sg: sg.shift_index)
        nearest_after = min(seen_after, key=lambda sg: sg.shift_index)

        # If the can is transitioning slot_type (entrante -> cerrada),
        # this MIGHT be an omission or a normal transition.
        # Lower confidence for transitions vs same-type omissions.
        type_transition = (nearest_before.slot_type != nearest_after.slot_type)

        dist_before = shift_idx - nearest_before.shift_index
        dist_after = nearest_after.shift_index - shift_idx

        if dist_before > 2 or dist_after > 2:
            continue  # too far away

        n_sightings = len(can.sightings)
        conf = min(
            _decay(dist_before, config.decay_rate),
            _decay(dist_after, config.decay_rate)
        )
        if n_sightings >= 5:
            conf = min(conf * 1.2, 0.95)

        # Lower confidence for type transitions (entrante->cerrada)
        if type_transition:
            conf *= 0.6

        weight = nearest_before.weight

        corrections.append(TrajectoryCorrection(
            rule='omission',
            description=(f"Can {can.id} ({weight:.0f}g) seen at "
                        f"{nearest_before.shift_name} ({nearest_before.slot_type}) and "
                        f"{nearest_after.shift_name} ({nearest_after.slot_type}) "
                        f"but absent here"
                        f"{' [type transition]' if type_transition else ''}"),
            confidence=conf,
            value_affected=weight,
            action='added',
        ))

    return corrections


def _detect_recent_ghosts(flavor, shift_idx, raw, cans, config):
    """Detect ghosts from cans opened in the RECENT past (1-2 shifts).

    A ghost is when a can was opened (abierta jumped), but its weight
    still appears in the next shift's cerradas — likely a copy-paste error.

    We ONLY detect ghosts from very recent openings. A can opened 20 shifts
    ago does not produce ghost detections — any similar weight now is a
    different physical can.
    """
    corrections = []
    tol = config.match_tolerance

    for can in cans:
        if can.status != 'opened' or can.opened_at is None:
            continue

        # Ghost detection only within 2 shifts of opening
        distance = shift_idx - can.opened_at
        if distance < 0 or distance > 2:
            continue

        # Does a raw value match this opened can?
        for slot in raw.slots:
            if abs(slot.value - can.last_weight) <= tol:
                # Check if this slot is explained by another ACTIVE, well-established
                # (non-opened) tracked can. E.g., DDL opened can 6690 vs active
                # can 6675 — slot 6675 belongs to the active can, not a ghost.
                # Require min_history sightings: a 1-sighting identity is too
                # weak to override ghost detection.
                explained_by_other = False
                for other in cans:
                    if other.id == can.id:
                        continue
                    if other.status == 'opened':
                        continue
                    if len(other.sightings) < config.min_history:
                        continue
                    if other.seen_at(shift_idx):
                        w = other.weight_at(shift_idx)
                        if w is not None and abs(w - slot.value) <= tol:
                            explained_by_other = True
                            break
                if explained_by_other:
                    continue  # Not a ghost — it's a different, live can

                conf = _decay(distance, config.decay_rate) * 0.85

                corrections.append(TrajectoryCorrection(
                    rule='ghost',
                    description=(f"Can {can.id} ({slot.value:.0f}g col {slot.column}) "
                                f"was opened {distance} shifts ago but value persists "
                                f"— ghost"),
                    confidence=conf,
                    value_affected=slot.value,
                    action='removed',
                ))
                break

    return corrections


def _was_active_at(can, shift_idx):
    """Check if a can was active (being tracked) at a given shift.
    A can is active at shift_idx if it has sightings before AND at/after shift_idx,
    OR if shift_idx falls within its sighting range."""
    if not can.sightings:
        return False
    first = can.first_seen
    last = can.last_seen
    # Can was active during its sighting range
    if first <= shift_idx <= last:
        return True
    # Also active if first_seen == shift_idx (just appeared)
    return False


def _detect_duplicates(flavor, shift_idx, raw, cans, config):
    """Detect two raw values that map to the same physical can."""
    corrections = []
    tol = config.match_tolerance

    # Check cans that were ACTIVE at this shift (not just 'live' at end)
    for can in cans:
        if not _was_active_at(can, shift_idx):
            continue
        # Skip cans that were already opened before this shift
        if can.status == 'opened' and can.opened_at is not None and can.opened_at <= shift_idx:
            continue

        matching_slots = []
        for slot in raw.slots:
            # Use the weight the can had at or near this shift
            ref_weight = can.weight_at(shift_idx) or can.last_weight
            if abs(ref_weight - slot.value) <= tol:
                matching_slots.append(slot)

        if len(matching_slots) <= 1:
            continue

        n_prior = len([sg for sg in can.sightings if sg.shift_index < shift_idx])
        if n_prior < config.min_history:
            continue

        # Exclude slots better claimed by a DIFFERENT well-established can.
        # Two cans with similar weights (e.g., DDL 6675 and 6690) both
        # match slots within tolerance. Each slot belongs to its closest can.
        # Only well-established cans (min_history sightings) can claim slots
        # — a 1-sighting identity is too weak to override a duplicate detection.
        ref_weight = can.weight_at(shift_idx) or can.last_weight
        unclaimed = []
        for slot in matching_slots:
            claimed_by_other = False
            for other in cans:
                if other.id == can.id:
                    continue
                if not _was_active_at(other, shift_idx):
                    continue
                if other.status == 'opened' and other.opened_at and other.opened_at <= shift_idx:
                    continue
                # Other can must be well-established to claim a slot
                other_sightings = len(other.sightings)
                if other_sightings < config.min_history:
                    continue
                other_ref = other.weight_at(shift_idx) or other.last_weight
                if abs(other_ref - slot.value) <= tol:
                    if abs(other_ref - slot.value) < abs(ref_weight - slot.value):
                        claimed_by_other = True
                        break
            if not claimed_by_other:
                unclaimed.append(slot)

        if len(unclaimed) <= 1:
            continue

        # Keep the closest match, remove the rest as duplicates
        unclaimed.sort(key=lambda s: abs(s.value - ref_weight))
        for slot in unclaimed[1:]:
            conf = min(0.85, n_prior / 6.0)

            corrections.append(TrajectoryCorrection(
                rule='duplicate',
                description=(f"Value {slot.value:.0f}g (col {slot.column}) duplicates "
                            f"can {can.id} — history shows one can across "
                            f"{n_prior} shifts"),
                confidence=conf,
                value_affected=slot.value,
                action='removed',
            ))

    return corrections


def _detect_phantoms(flavor, shift_idx, raw, cans, config):
    """Detect values that match no tracked can and coexist with matched values."""
    corrections = []
    tol = config.match_tolerance

    # Identify which slots ARE matched by the tracker (have a sighting at this shift)
    matched_slots = set()
    unmatched_slots = []

    for slot in raw.slots:
        found = False
        for can in cans:
            if not _was_active_at(can, shift_idx):
                continue
            if can.status == 'opened' and can.opened_at and can.opened_at <= shift_idx:
                continue
            if can.seen_at(shift_idx):
                w = can.weight_at(shift_idx)
                if w is not None and abs(w - slot.value) <= tol:
                    n_prior = len([sg for sg in can.sightings if sg.shift_index < shift_idx])
                    if n_prior >= config.min_history:
                        # Well-established can — strong match
                        matched_slots.add(id(slot))
                        found = True
                        break
                    elif n_prior == 0 and slot.slot_type == 'entrante':
                        # Brand new entrante: this is a delivery, not phantom.
                        # H0: entrantes are inherently first-appearances.
                        found = True
                        break
        if not found:
            unmatched_slots.append(slot)

    if not unmatched_slots or not matched_slots:
        return corrections

    for slot in unmatched_slots:
        # Does this value match any RECENTLY ACTIVE can with prior history?
        # "Recently active" means the can had sightings within max_history_window
        has_recent_match = False
        for can in cans:
            # Can must have prior sightings
            prior = [sg for sg in can.sightings if sg.shift_index < shift_idx]
            if not prior:
                # Check: is this a brand-new can (created at this shift) that
                # persists in future shifts? If so, it's a real arrival, not phantom.
                if (can.sightings and can.sightings[0].shift_index == shift_idx
                        and abs(can.sightings[0].weight - slot.value) <= tol):
                    future = [sg for sg in can.sightings if sg.shift_index > shift_idx]
                    if future:
                        has_recent_match = True
                        break
                continue
            # Can must have been active recently (not 20+ shifts ago)
            most_recent = max(sg.shift_index for sg in prior)
            if shift_idx - most_recent > config.max_history_window:
                continue  # too old, irrelevant
            # Does the value match this can?
            for sg in can.sightings:
                if abs(sg.weight - slot.value) <= tol:
                    has_recent_match = True
                    break
            if has_recent_match:
                break

        if has_recent_match:
            continue

        corrections.append(TrajectoryCorrection(
            rule='phantom',
            description=(f"Value {slot.value:.0f}g (col {slot.column}) has no match "
                        f"in any recently active tracked can — phantom"),
            confidence=0.70,
            value_affected=slot.value,
            action='removed',
        ))

    return corrections


def _detect_opened_entrantes(flavor, shift_idx, raw, cans, shift_by_index, config):
    """Detect entrantes that were opened (abierta appeared from ~0)."""
    corrections = []
    tol = config.match_tolerance

    entrante_slots = [s for s in raw.slots if s.slot_type == 'entrante']
    if not entrante_slots:
        return corrections

    shift_indices = sorted(shift_by_index.keys())
    try:
        pos = shift_indices.index(shift_idx)
    except ValueError:
        return corrections
    if pos == 0:
        return corrections

    prev_idx = shift_indices[pos - 1]
    prev_shift = shift_by_index.get(prev_idx)
    if prev_shift is None:
        return corrections
    prev_obs = prev_shift.flavors.get(flavor)
    if prev_obs is None:
        return corrections

    # Abierta went from ~0 to substantial?
    if prev_obs.abierta > 500 or raw.abierta < 500:
        return corrections

    prev_ent_vals = prev_obs.entrantes
    for ent_slot in entrante_slots:
        matches_prev = any(abs(ent_slot.value - pe) <= tol for pe in prev_ent_vals)
        if matches_prev:
            corrections.append(TrajectoryCorrection(
                rule='opened_entrante',
                description=(f"Entrante {ent_slot.value:.0f}g persists from prev shift "
                            f"but abierta appeared ({prev_obs.abierta:.0f}"
                            f"->{raw.abierta:.0f}g) — opened, ghost persistence"),
                confidence=0.65,
                value_affected=ent_slot.value,
                action='removed',
            ))

    return corrections


def _detect_impossible_abierta(flavor, shift_idx, raw, shift_by_index,
                                non_stock_indices, config):
    """Detect impossible abierta transitions.

    Pattern: abierta drops >2000g without cerrada opening, then recovers
    >1500g next shift.  The prev and next abiertas are coherent
    (|prev − next| < 1000g), proving the current value is the outlier.

    Example (AMERICANA Day 25):
      idx47 ab=4365 → idx48 ab=1650 → idx49 ab=4110
      drop=2715 > 2000, recovery=2460 > 1500, |4365−4110|=255 < 1000.
      Correction: replace ab with prev value (4365).
    """
    try:
        pos = non_stock_indices.index(shift_idx)
    except ValueError:
        return []

    if pos == 0 or pos >= len(non_stock_indices) - 1:
        return []

    prev_idx = non_stock_indices[pos - 1]
    next_idx = non_stock_indices[pos + 1]

    prev_shift = shift_by_index.get(prev_idx)
    next_shift = shift_by_index.get(next_idx)
    if prev_shift is None or next_shift is None:
        return []

    prev_obs = prev_shift.flavors.get(flavor)
    next_obs = next_shift.flavors.get(flavor)
    if prev_obs is None or next_obs is None:
        return []

    prev_ab = prev_obs.abierta
    curr_ab = raw.abierta
    next_ab = next_obs.abierta

    drop = prev_ab - curr_ab
    recovery = next_ab - curr_ab
    prev_next_diff = abs(prev_ab - next_ab)

    if drop > 2000 and recovery > 1500 and prev_next_diff < 1000:
        return [TrajectoryCorrection(
            rule='impossible_abierta',
            description=(
                f"Abierta impossible: {prev_ab:.0f}->{curr_ab:.0f}->{next_ab:.0f} "
                f"(drop={drop:.0f}g, recovery={recovery:.0f}g, "
                f"|prev-next|={prev_next_diff:.0f}g) -- using prev {prev_ab:.0f}g"),
            confidence=0.90,
            value_affected=prev_ab,
            action='abierta_corrected',
        )]

    return []


def _apply_corrections(point, corrections):
    """Apply corrections to a TrajectoryPoint."""
    for corr in corrections:
        if corr.action == 'added':
            point.inferred_cerradas.append(corr.value_affected)
        elif corr.action == 'removed':
            val = corr.value_affected
            removed = False
            for i, c in enumerate(point.inferred_cerradas):
                if abs(c - val) < 1.0:
                    point.inferred_cerradas.pop(i)
                    removed = True
                    break
            if not removed:
                for i, e in enumerate(point.inferred_entrantes):
                    if abs(e - val) < 1.0:
                        point.inferred_entrantes.pop(i)
                        removed = True
                        break
        elif corr.action == 'abierta_corrected':
            point.inferred_abierta = corr.value_affected
        point.corrections.append(corr)
