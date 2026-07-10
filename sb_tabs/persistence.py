"""Map TabStripState to/from settings dict keys."""

from __future__ import annotations

from sb_tabs.models import ALL_CHANNELS_TAB, TabStripState


def state_from_settings(settings: dict) -> TabStripState:
    order = [str(x) for x in (settings.get("tab_order") or [ALL_CHANNELS_TAB])]
    if not order:
        order = [ALL_CHANNELS_TAB]
    hidden = {str(x) for x in (settings.get("hidden_tab_ids") or [])}
    active = str(settings.get("active_tab_id") or ALL_CHANNELS_TAB)
    return TabStripState(order=order, active_id=active, hidden=hidden, unread={})


def state_to_settings_patch(state: TabStripState) -> dict:
    return {
        "tab_order": list(state.order),
        "hidden_tab_ids": sorted(state.hidden),
        "active_tab_id": state.active_id or ALL_CHANNELS_TAB,
    }
