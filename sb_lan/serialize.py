"""Serialize feed rows to LAN JSON payloads with entity spans."""

from __future__ import annotations

from typing import Any


def _match_spans(text: str, terms: list[str], cls: str) -> list[dict]:
    """Longest-first non-overlapping matches for highlighting."""
    spans: list[tuple[int, int, str, str]] = []
    hay = text
    used = [False] * len(hay)
    ordered = sorted({str(t) for t in terms if t}, key=len, reverse=True)
    lower = hay.casefold()
    for term in ordered:
        needle = term.casefold()
        if not needle:
            continue
        start = 0
        while True:
            pos = lower.find(needle, start)
            if pos < 0:
                break
            end = pos + len(term)
            if end <= len(used) and not any(used[pos:end]):
                for i in range(pos, end):
                    used[i] = True
                spans.append((pos, end, hay[pos:end], cls))
            start = pos + 1
    spans.sort(key=lambda s: s[0])
    return [{"start": a, "end": b, "text": t, "cls": c} for a, b, t, c in spans]


def _spans_to_segments(text: str, spans: list[dict]) -> list[dict]:
    """Convert absolute spans into sequential {text, cls} segments for the browser."""
    if not text:
        return []
    if not spans:
        return [{"text": text, "cls": "body"}]
    out: list[dict] = []
    cursor = 0
    for sp in sorted(spans, key=lambda s: s["start"]):
        start, end = int(sp["start"]), int(sp["end"])
        if start < cursor:
            continue
        if start > cursor:
            out.append({"text": text[cursor:start], "cls": "body"})
        out.append({"text": text[start:end], "cls": sp.get("cls") or "body"})
        cursor = end
    if cursor < len(text):
        out.append({"text": text[cursor:], "cls": "body"})
    return out


def row_to_lan_payload(
    *,
    row_id: str,
    channel: str,
    timestamp: str,
    sender: str,
    visible_text: str,
    systems: list[str] | None = None,
    ships: list[str] | None = None,
    pilots: list[str] | None = None,
    links: list[str] | None = None,
    counts: list[str] | None = None,
) -> dict[str, Any]:
    """Build a browser-ready payload mirroring the desktop visible line."""
    body = str(visible_text or "")
    spans: list[dict] = []
    spans.extend(_match_spans(body, list(systems or []), "system"))
    spans.extend(_match_spans(body, list(ships or []), "ship"))
    spans.extend(_match_spans(body, list(pilots or []), "pilot"))
    spans.extend(_match_spans(body, list(links or []), "link"))
    spans.extend(_match_spans(body, [str(c) for c in (counts or [])], "count"))
    # de-dupe overlaps preferring longer (already longest-first per class; re-merge)
    spans = _dedupe_spans(spans)
    segments = _spans_to_segments(body, spans)
    return {
        "id": str(row_id or ""),
        "channel": str(channel or ""),
        "ts": str(timestamp or ""),
        "sender": str(sender or ""),
        "visible_text": body,
        "spans": segments,
        "entities": {
            "systems": list(systems or []),
            "ships": list(ships or []),
            "pilots": list(pilots or []),
            "links": list(links or []),
        },
    }


def _dedupe_spans(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda s: (s["start"], -(s["end"] - s["start"])))
    out: list[dict] = []
    last_end = -1
    for sp in spans:
        if sp["start"] < last_end:
            continue
        out.append(sp)
        last_end = sp["end"]
    return out


def payload_from_row_object(row: Any, *, visible_text: str, row_id: str = "") -> dict[str, Any]:
    """Convenience for live Row duck-types."""
    pilots = []
    for e in getattr(row, "esi_entities", []) or []:
        if isinstance(e, dict):
            name = e.get("name") or e.get("query")
            if name:
                pilots.append(str(name))
    ships = list(getattr(row, "assets", []) or [])
    for loc in getattr(row, "localized", []) or []:
        if isinstance(loc, dict):
            can = loc.get("canonical") or loc.get("original")
            if can:
                ships.append(str(can))
    ts = str(getattr(row, "received_at", "") or "")
    if " " in ts:
        ts = ts.split()[-1]
    return row_to_lan_payload(
        row_id=row_id or str(id(row)),
        channel=str(getattr(row, "channel", "") or ""),
        timestamp=ts,
        sender=str(getattr(row, "sender", "") or ""),
        visible_text=visible_text,
        systems=list(getattr(row, "systems", []) or []),
        ships=ships,
        pilots=pilots,
        links=list(getattr(row, "links", []) or []),
        counts=[str(c) for c in (getattr(row, "counts", []) or [])],
    )
