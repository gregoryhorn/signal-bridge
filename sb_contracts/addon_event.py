"""AddonEvent helpers — pure stdlib, duck-typed rows."""

from __future__ import annotations

import time
from typing import Any


def make_addon_event(*, type: str, data: dict | None = None, timestamp: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "type": type,
        "timestamp": timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": dict(data or {}),
    }


def row_to_addon_event(row: Any) -> dict:
    """Flat payload matching existing Intel History consumer + schema_version."""
    chars = []
    for ent in getattr(row, "esi_entities", []) or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("entity_type") != "character" or not ent.get("entity_id"):
            continue
        chars.append({
            "entity_type": "character",
            "entity_id": ent.get("entity_id"),
            "name": ent.get("name") or ent.get("query") or "",
            "query": ent.get("query") or ent.get("name") or "",
            "corporation_id": ent.get("corporation_id"),
            "corporation_name": ent.get("corporation_name") or "",
            "alliance_id": ent.get("alliance_id"),
            "alliance_name": ent.get("alliance_name") or "",
            "confidence": ent.get("confidence") or "high",
        })
    return {
        "schema_version": 1,
        "type": "intel_row",
        "timestamp": getattr(row, "received_at", "") or getattr(row, "time", "") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel": getattr(row, "channel", "") or "",
        "sender": getattr(row, "sender", "") or "",
        "text": getattr(row, "text", "") or "",
        "systems": list(getattr(row, "systems", []) or []),
        "ships": list(getattr(row, "ships", []) or getattr(row, "assets", []) or []),
        "assets": list(getattr(row, "assets", []) or []),
        "links": list(getattr(row, "links", []) or []),
        "characters": chars,
        "raw_text_available": False,
    }
