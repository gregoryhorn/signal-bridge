"""Shared text normalize / strip helpers (no mojibake)."""

from __future__ import annotations

import re

# Curly quotes and common punctuation for term stripping
_TERM_STRIP = "* ,.;:()[]{}\"'`\u201c\u201d\u2018\u2019"


def strip_term_punctuation(value: str) -> str:
    return str(value or "").strip().strip(_TERM_STRIP)


def truncate_label(label: str, max_chars: int = 28) -> str:
    text = str(label or "")
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return "\u2026"
    return text[: max_chars - 1] + "\u2026"


def normalize_feed_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()
