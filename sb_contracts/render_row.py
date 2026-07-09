"""RenderRow contract builder — pure; may use signal_bridge_render_model only."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable

import signal_bridge_render_model as render_model
from sb_contracts.intel_segment import intel_segment_from_legacy, intel_segment_to_dict


@dataclass
class RenderRow:
    row_id: str
    channel: str
    timestamp: str
    sender: str
    visible_lines: list[str]
    original_line: str
    translated_line: str
    segments: list[dict] = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    spans: list[dict] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    schema_version: int = 1


def _stable_row_id(row: Any) -> str:
    parts = [
        str(getattr(row, "channel", "") or ""),
        str(getattr(row, "received_at", "") or ""),
        str(getattr(row, "sender", "") or ""),
        str(getattr(row, "text", "") or ""),
        str(getattr(row, "file", "") or ""),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"r_{digest}"


def build_render_row(row: Any, *, translated_only: bool, normalize: Callable[[str], str]) -> RenderRow:
    original = str(getattr(row, "text", "") or "")
    translated = str(getattr(row, "free_translation", "") or getattr(row, "translation", "") or "")
    visible = render_model.visible_body_lines(row, translated, original, translated_only, normalize)
    raw_segments = getattr(row, "segments", None) or []
    segments = [intel_segment_to_dict(intel_segment_from_legacy(s)) for s in raw_segments]
    entities = {
        "systems": list(getattr(row, "systems", []) or []),
        "assets": list(getattr(row, "assets", []) or []),
        "links": list(getattr(row, "links", []) or []),
        "counts": list(getattr(row, "counts", []) or []),
        "esi": list(getattr(row, "esi_entities", []) or []),
    }
    diagnostics = {
        "translation_source": str(getattr(row, "translation_source", "") or ""),
        "segment_count": len(segments),
    }
    return RenderRow(
        row_id=_stable_row_id(row),
        channel=str(getattr(row, "channel", "") or ""),
        timestamp=str(getattr(row, "received_at", "") or ""),
        sender=str(getattr(row, "sender", "") or ""),
        visible_lines=list(visible),
        original_line=original,
        translated_line=translated,
        segments=segments,
        entities=entities,
        spans=[],
        diagnostics=diagnostics,
    )
