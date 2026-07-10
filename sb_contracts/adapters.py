"""Legacy row/object → contract adapters."""

from __future__ import annotations

from typing import Any, Callable

from sb_contracts.intel_segment import IntelSegment, intel_segment_from_legacy
from sb_contracts.render_row import RenderRow, build_render_row


def segments_from_row(row: Any) -> list[IntelSegment]:
    return [intel_segment_from_legacy(s) for s in (getattr(row, "segments", None) or [])]


def render_row_from_legacy(row: Any, *, translated_only: bool, normalize: Callable[[str], str]) -> RenderRow:
    return build_render_row(row, translated_only=translated_only, normalize=normalize)
