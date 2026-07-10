"""Pilot Intel UI package."""

from sb_ui.pilot.card import open_pilot_card

# Back-compat alias used by older call sites / tests
open_pilot_info_card = open_pilot_card

__all__ = ["open_pilot_card", "open_pilot_info_card"]
