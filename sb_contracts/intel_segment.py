"""IntelSegment contract — pure stdlib."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IntelSegment:
    kind: str
    text: str
    systems: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    pilots: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    confidence: str = "medium"
    schema_version: int = 1


def intel_segment_to_dict(seg: IntelSegment) -> dict:
    return asdict(seg)


def intel_segment_from_legacy(obj: Any) -> IntelSegment:
    if isinstance(obj, IntelSegment):
        return obj
    if isinstance(obj, dict):
        return IntelSegment(
            kind=str(obj.get("kind") or "message"),
            text=str(obj.get("text") or ""),
            systems=list(obj.get("systems") or []),
            assets=list(obj.get("assets") or []),
            pilots=list(obj.get("pilots") or []),
            notes=list(obj.get("notes") or []),
            status=list(obj.get("status") or []),
            confidence=str(obj.get("confidence") or "medium"),
            schema_version=int(obj.get("schema_version") or 1),
        )
    return IntelSegment(
        kind=str(getattr(obj, "kind", "") or "message"),
        text=str(getattr(obj, "text", "") or ""),
        systems=list(getattr(obj, "systems", []) or []),
        assets=list(getattr(obj, "assets", []) or []),
        pilots=list(getattr(obj, "pilots", []) or []),
        notes=list(getattr(obj, "notes", []) or []),
        status=list(getattr(obj, "status", []) or []),
        confidence=str(getattr(obj, "confidence", "") or "medium"),
    )
