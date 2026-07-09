"""Pilot Info snapshot shape — pure stdlib."""

from __future__ import annotations


def empty_pilot_info_snapshot(name: str = "", pilot_id: int = 0) -> dict:
    return {
        "schema_version": 1,
        "pilot": {
            "pilot_id": int(pilot_id or 0),
            "name": str(name or ""),
            "corp_name": "",
            "alliance_name": "",
        },
        "report_count": 0,
        "recent_sightings": [],
        "top_ships": [],
        "top_systems": [],
        "flags": [],
        "zkill": {"status": "not_synced", "synced_at": None},
    }
