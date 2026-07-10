"""Pilot ship/status term classification and formatting (no Tk)."""

from __future__ import annotations


def pilot_info_term_kind(value: str) -> str:
    key = str(value or "").strip().casefold()
    if not key or key == "-":
        return "empty"
    if key in {"nv", "no visual", "novisual", "no-visual"}:
        return "status"
    if key in {"cyno", "beacon", "ess", "bubble"}:
        return "signal"
    return "ship"


def is_pilot_status_term(value: str) -> bool:
    return pilot_info_term_kind(value) == "status"


def is_pilot_signal_term(value: str) -> bool:
    return pilot_info_term_kind(value) == "signal"


def clean_value(value, empty="—"):
    text = str(value or "").strip()
    return text if text and text != "-" else empty


def count_label(value) -> str:
    try:
        n = int(value or 0)
    except Exception:
        n = 0
    return f"×{n}" if n > 1 else ""


def fmt_isk(value) -> str:
    try:
        n = float(value or 0)
    except Exception:
        return "—"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}b"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.0f}m"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{n:.0f}"


def normalized_ship_status(row: dict) -> tuple[str, str]:
    raw = str((row or {}).get("ship_name") or "").strip()
    kind = pilot_info_term_kind(raw)
    if kind == "status":
        return "Unknown", "No visual"
    if kind == "signal":
        return "Unknown", raw.title() if raw.casefold() == "cyno" else raw
    if kind == "empty":
        return "Unknown", ""
    return raw, ""


def parse_ztime(value: str):
    import datetime as _dt

    raw = str(value or "").replace("T", " ").replace("Z", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return _dt.datetime.strptime(raw[:19], fmt)
        except Exception:
            pass
    return None


def zkill_priority(zks: dict, current_ship: str) -> tuple[str, str, list[str]]:
    import datetime as _dt

    if zks.get("status") != "synced":
        return "NONE", "zKill not synced", []
    events = zks.get("recent_events") or []
    if not events:
        return "QUIET", "No recent zKill activity", []
    now_dt = _dt.datetime.utcnow()
    high, med = [], []
    cur = str(current_ship or "").strip().casefold()
    for ev in events:
        ev_time = parse_ztime(ev.get("time"))
        ship = str(ev.get("ship") or "").strip()
        if ev_time:
            age_days = (now_dt.date() - ev_time.date()).days
            if age_days <= 0:
                high.append(f"{ev.get('type', 'event')} today")
            elif age_days <= 7:
                med.append(f"{ev.get('type', 'event')} this week")
        if cur and cur != "unknown" and ship and ship.casefold() == cur:
            high.append(f"same ship: {ship}")
    if high:
        return "HIGH", high[0], sorted(set(high + med))[:4]
    if med:
        return "MED", med[0], sorted(set(med))[:4]
    return "LOW", "Older zKill activity", []
