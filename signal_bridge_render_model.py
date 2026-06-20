from __future__ import annotations

from typing import Any, Callable


def _segment_kind(seg: Any) -> str:
    return str(getattr(seg, "kind", "") or "message")


def _segment_text(seg: Any) -> str:
    return str(getattr(seg, "text", "") or "")


def row_uses_multiline_segments(row: Any) -> bool:
    """Return true when a row should visually split into multiple feed lines."""
    return len(getattr(row, "segments", None) or []) > 1


def segment_display_lines(row: Any, translated_text: str, normalize: Callable[[str], str]) -> list[str]:
    """Return compact feed display lines for a row.

    Segmentation is internal-first: normal/single-segment rows remain chat-like.
    Only genuinely multi-segment rows split for readability.
    This module is intentionally pure and must not touch Tk, network, ESI, DBs,
    or external engines.
    """
    segments = getattr(row, "segments", None) or []
    if len(segments) <= 1:
        return [translated_text]
    lines: list[str] = []
    for seg in segments:
        if _segment_kind(seg) == "kill":
            lines.append(f"[KILL] {_segment_text(seg)}")
        else:
            lines.append(_segment_text(seg))
    cleaned = [normalize(line) for line in lines if normalize(line)]
    return cleaned or [translated_text]


def visible_body_lines(row: Any, translated_text: str, original_text: str, translated_only: bool, normalize: Callable[[str], str]) -> list[str]:
    """Return final body lines before Tk-specific tagging/highlighting."""
    text = translated_text if translated_only else original_text
    return segment_display_lines(row, text, normalize)
