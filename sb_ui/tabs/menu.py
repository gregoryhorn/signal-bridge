"""Tab context menu builders (Void Tactical)."""

from __future__ import annotations

from typing import Callable

from sb_tabs.models import ALL_CHANNELS_TAB
from sb_ui import theme


def build_tab_context_menu(
    root,
    tab_id: str,
    *,
    on_close: Callable[[str], None],
    on_close_others: Callable[[str], None],
    on_close_all: Callable[[], None],
    on_copy: Callable[[str], None] | None = None,
    on_restore_hidden: Callable[[], None] | None = None,
):
    import tkinter as tk

    c = theme.COLORS
    menu = tk.Menu(
        root,
        tearoff=False,
        bg=c["bg_chrome"],
        fg=c["fg"],
        activebackground=c["accent_active"],
        activeforeground=c["fg_bright"],
    )
    close_label = "Hide All Tab" if tab_id == ALL_CHANNELS_TAB else "Close Channel"
    menu.add_command(label=close_label, command=lambda: on_close(tab_id))
    menu.add_command(label="Close Other Channels", command=lambda: on_close_others(tab_id))
    menu.add_command(label="Close All Channels", command=on_close_all)
    if tab_id != ALL_CHANNELS_TAB and on_copy:
        menu.add_separator()
        menu.add_command(label="Copy Channel Name", command=lambda: on_copy(tab_id))
    if on_restore_hidden:
        menu.add_separator()
        menu.add_command(label="Restore Hidden Tabs...", command=on_restore_hidden)
    return menu


def popup_menu(menu, event) -> None:
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
