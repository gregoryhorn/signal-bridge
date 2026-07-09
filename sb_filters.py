"""Content and sender feed filters (pure)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class FeedFilter:
    id: str
    kind: str  # keyword | sender
    pattern: str
    enabled: bool = True
    match_mode: str = "contains"  # contains | exact
    case_insensitive: bool = True


def normalize_filters(raw) -> list[FeedFilter]:
    out: list[FeedFilter] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().casefold()
        if kind not in {"keyword", "sender"}:
            continue
        pattern = str(item.get("pattern") or "").strip()
        if not pattern:
            continue
        match_mode = str(item.get("match_mode") or "contains").strip().casefold()
        if match_mode not in {"contains", "exact"}:
            match_mode = "contains"
        fid = str(item.get("id") or "").strip() or uuid.uuid4().hex[:12]
        out.append(
            FeedFilter(
                id=fid,
                kind=kind,
                pattern=pattern,
                enabled=bool(item.get("enabled", True)),
                match_mode=match_mode,
                case_insensitive=bool(item.get("case_insensitive", True)),
            )
        )
    return out


def filters_to_settings(filters: list[FeedFilter]) -> list[dict]:
    return [asdict(f) for f in filters]


def _match(value: str, pattern: str, *, match_mode: str, case_insensitive: bool) -> bool:
    left = value.casefold() if case_insensitive else value
    right = pattern.casefold() if case_insensitive else pattern
    if match_mode == "exact":
        return left == right
    return right in left


def row_is_filtered(sender: str, text: str, filters: list[FeedFilter]) -> tuple[bool, str]:
    """Return (filtered?, reason). First matching enabled filter wins."""
    for f in filters:
        if not f.enabled or not f.pattern:
            continue
        if f.kind == "sender":
            if _match(str(sender or ""), f.pattern, match_mode=f.match_mode, case_insensitive=f.case_insensitive):
                return True, f"filter_sender:{f.id}"
        elif f.kind == "keyword":
            if _match(str(text or ""), f.pattern, match_mode=f.match_mode, case_insensitive=f.case_insensitive):
                return True, f"filter_keyword:{f.id}"
    return False, "allow"
