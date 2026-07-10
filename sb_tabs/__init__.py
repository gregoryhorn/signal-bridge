"""Pure channel tab strip state (no Tk)."""

from sb_tabs.models import ALL_CHANNELS_TAB, TabInfo, TabStripState
from sb_tabs.persistence import state_from_settings, state_to_settings_patch
from sb_tabs.state import (
    clear_unread,
    close_all_closable,
    close_others,
    close_tab,
    hidden_count,
    mark_unread,
    move_before,
    normalize,
    overflow_split,
    reorder,
    restore_tab,
    select_tab,
    short_title,
    tab_label,
    visible_tabs,
)

__all__ = [
    "ALL_CHANNELS_TAB",
    "TabInfo",
    "TabStripState",
    "clear_unread",
    "close_all_closable",
    "close_others",
    "close_tab",
    "hidden_count",
    "mark_unread",
    "move_before",
    "normalize",
    "overflow_split",
    "reorder",
    "restore_tab",
    "select_tab",
    "short_title",
    "state_from_settings",
    "state_to_settings_patch",
    "tab_label",
    "visible_tabs",
]
