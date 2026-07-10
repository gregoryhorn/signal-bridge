"""Compatibility shim — Pilot Intel lives in sb_ui.pilot + sb_pilot.

Prefer:
  from sb_ui.pilot import open_pilot_card
  from sb_pilot import pilot_info_term_kind, zkill_priority, ...
"""

from sb_pilot import (
    clean_value,
    count_label,
    fmt_isk,
    is_pilot_signal_term,
    is_pilot_status_term,
    normalized_ship_status,
    parse_ztime,
    pilot_info_term_kind,
    zkill_priority,
)
from sb_ui.pilot import open_pilot_card, open_pilot_info_card

__all__ = [
    "clean_value",
    "count_label",
    "fmt_isk",
    "is_pilot_signal_term",
    "is_pilot_status_term",
    "normalized_ship_status",
    "open_pilot_card",
    "open_pilot_info_card",
    "parse_ztime",
    "pilot_info_term_kind",
    "zkill_priority",
]
