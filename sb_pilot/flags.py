"""Pilot flag labels and sorting (no Tk)."""

from __future__ import annotations

# Product-facing flag kinds used in feed quick-actions and card.
FLAG_KINDS = (
    ("Watchlist", "★"),
    ("High Threat", "⚠"),
    ("Do Not Track", "DNT"),
)

_ORDER = {
    "high threat": 0,
    "watchlist": 1,
    "do not track": 2,
}


def flag_label(kind: str) -> str:
    text = str(kind or "").strip()
    if not text:
        return "Flag"
    for name, _icon in FLAG_KINDS:
        if name.casefold() == text.casefold():
            return name
    return text


def flag_icon(kind: str) -> str:
    text = str(kind or "").strip().casefold()
    for name, icon in FLAG_KINDS:
        if name.casefold() == text:
            return icon
    return ""


def sort_flags(flags: list) -> list:
    """Stable sort: High Threat, Watchlist, DNT, then others; active first."""

    def key(f: dict):
        label = str(f.get("label") or f.get("flag") or "").casefold()
        active = 0 if int(f.get("active", 1) or 0) else 1
        return (active, _ORDER.get(label, 50), label)

    return sorted(list(flags or []), key=key)


def active_flags(flags: list) -> list[dict]:
    return [f for f in sort_flags(flags) if int(f.get("active", 0) or 0)]
