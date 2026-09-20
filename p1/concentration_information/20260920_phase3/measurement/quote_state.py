"""Pure quote-state logic for the frozen P1 venue-specific BBO contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Update:
    timestamp: int
    session: str
    bid: int | None
    ask: int | None
    bid_size: int | None
    ask_size: int | None
    withdrawn: bool = False
    halted: bool = False


@dataclass(frozen=True)
class Endpoint:
    target: int
    session: str
    status: str
    midpoint: float | None
    source_timestamp: int | None
    locked: bool = False


def classify(update: Update) -> tuple[str, float | None, bool]:
    if update.halted:
        return "INVALID_HALT", None, False
    if update.withdrawn:
        return "INVALID_WITHDRAWN", None, False
    values = (update.bid, update.ask, update.bid_size, update.ask_size)
    if any(value is None or value <= 0 for value in values):
        return "INVALID_UNDEFINED_OR_ZERO_SIDE", None, False
    assert update.bid is not None and update.ask is not None
    if update.ask < update.bid:
        return "INVALID_CROSSED", None, False
    locked = update.ask == update.bid
    return ("VALID_LOCKED" if locked else "VALID", (update.bid + update.ask) / 2, locked)


def sample_endpoints(
    updates: Iterable[Update], targets: Iterable[tuple[int, str]]
) -> list[Endpoint]:
    """Sample the last state at/before each target, with session-local carry only."""
    ordered_updates = sorted(updates, key=lambda row: row.timestamp)
    ordered_targets = sorted(targets)
    result: list[Endpoint] = []
    cursor = 0
    state_by_session: dict[str, tuple[str, float | None, int, bool]] = {}
    for target, target_session in ordered_targets:
        while cursor < len(ordered_updates) and ordered_updates[cursor].timestamp <= target:
            update = ordered_updates[cursor]
            status, midpoint, locked = classify(update)
            state_by_session[update.session] = (
                status, midpoint, update.timestamp, locked
            )
            cursor += 1
        state = state_by_session.get(target_session)
        if state is None:
            result.append(
                Endpoint(target, target_session, "UNKNOWN_NO_PRIOR_STATE", None, None)
            )
            continue
        status, midpoint, source_timestamp, locked = state
        if not status.startswith("VALID"):
            result.append(
                Endpoint(target, target_session, status, None, source_timestamp)
            )
            continue
        carried = source_timestamp < target
        suffix = "_CARRIED" if carried else "_OBSERVED"
        result.append(
            Endpoint(
                target, target_session, status + suffix, midpoint,
                source_timestamp, locked
            )
        )
    return result


def simple_midpoint_response(baseline: Endpoint, post: Endpoint) -> float | None:
    if baseline.midpoint is None or post.midpoint is None or baseline.midpoint <= 0:
        return None
    if baseline.session != post.session:
        return None
    return post.midpoint / baseline.midpoint - 1

