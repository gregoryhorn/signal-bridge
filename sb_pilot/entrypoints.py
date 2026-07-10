"""Resolve pilot targets from feed click / entity lists (no Tk)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PilotRef:
    entity_id: int
    name: str
    query: str = ""
    corporation_name: str = ""
    alliance_name: str = ""

    def as_entity_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "query": self.query or self.name,
            "corporation_name": self.corporation_name,
            "alliance_name": self.alliance_name,
            "entity_type": "character",
        }


def _entity_to_ref(ent: dict) -> PilotRef | None:
    if not ent:
        return None
    try:
        eid = int(ent.get("entity_id") or ent.get("pilot_id") or 0)
    except Exception:
        eid = 0
    if not eid:
        return None
    name = str(ent.get("name") or ent.get("query") or "").strip()
    if not name:
        name = f"Pilot {eid}"
    return PilotRef(
        entity_id=eid,
        name=name,
        query=str(ent.get("query") or name),
        corporation_name=str(ent.get("corporation_name") or ent.get("corp_name") or ""),
        alliance_name=str(ent.get("alliance_name") or ""),
    )


def resolve_from_entity(ent: dict | None) -> PilotRef | None:
    return _entity_to_ref(ent or {})


def resolve_pilot_target(
    click_text: str,
    row_entities: list | None,
    *,
    prefer_exact_name: bool = True,
) -> PilotRef | None:
    """
    Pick the best ESI character entity for a click/selection.

    Prefer exact / substring name match on click_text; else first character entity.
    """
    entities = [e for e in (row_entities or []) if isinstance(e, dict)]
    characters = [
        e
        for e in entities
        if str(e.get("entity_type") or "character").casefold() == "character"
        and not e.get("ignored")
    ]
    if not characters:
        return None
    needle = str(click_text or "").strip().casefold()
    if needle and prefer_exact_name:
        for e in characters:
            for key in (e.get("name"), e.get("query")):
                name = str(key or "").strip()
                if not name:
                    continue
                if name.casefold() == needle or needle in name.casefold() or name.casefold() in needle:
                    ref = _entity_to_ref(e)
                    if ref:
                        return ref
    return _entity_to_ref(characters[0])


def empty_profile_for_ref(ref: PilotRef) -> dict[str, Any]:
    """Local profile shell when Intel History has no sightings yet."""
    return {
        "found": True,
        "pilot": {
            "pilot_id": ref.entity_id,
            "name": ref.name,
            "corp_name": ref.corporation_name,
            "alliance_name": ref.alliance_name,
            "first_seen": "",
            "last_seen": "",
        },
        "report_count": 0,
        "recent_sightings": [],
        "top_ships": [],
        "top_systems": [],
        "flags": [],
    }
