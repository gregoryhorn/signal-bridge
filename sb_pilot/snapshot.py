"""Profile snapshot helpers for Pilot Intel card (no Tk)."""

from __future__ import annotations

from sb_pilot.flags import active_flags as filter_active_flags
from sb_pilot.terms import (
    is_pilot_signal_term,
    normalized_ship_status,
    pilot_info_term_kind,
)


def filtered_top_ships(profile: dict) -> list[dict]:
    out = []
    for x in profile.get("top_ships", []) or []:
        if pilot_info_term_kind(x.get("name")) == "ship":
            out.append(x)
    return out


def status_counts(profile: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for r0 in profile.get("recent_sightings", []) or []:
        _ship, status = normalized_ship_status(r0)
        if status and not is_pilot_signal_term(status):
            out[status] = out.get(status, 0) + int(r0.get("duplicate_count") or 1)
    return out


def signal_counts(profile: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for r0 in profile.get("recent_sightings", []) or []:
        _ship, status = normalized_ship_status(r0)
        if status and is_pilot_signal_term(status):
            key = status.title() if status.casefold() == "cyno" else status
            out[key] = out.get(key, 0) + int(r0.get("duplicate_count") or 1)
    for x in profile.get("top_ships", []) or []:
        name0 = str(x.get("name") or "").strip()
        if is_pilot_signal_term(name0):
            key = name0.title() if name0.casefold() == "cyno" else name0
            out[key] = max(out.get(key, 0), int(x.get("reports") or x.get("sightings") or 1))
    return out


def latest_sighting(profile: dict) -> dict:
    recent = profile.get("recent_sightings", []) or []
    return recent[0] if recent else {}


def profile_active_flags(profile: dict) -> list[dict]:
    return filter_active_flags(profile.get("flags", []) or [])
