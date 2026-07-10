"""Overflow control for tab strip when many channels are open."""

from __future__ import annotations

from typing import Callable

from sb_tabs.models import TabInfo
from sb_ui import theme


def build_overflow_button(
    parent,
    overflow_tabs: list[TabInfo],
    *,
    on_select: Callable[[str], None],
    hidden_restore_count: int = 0,
    on_restore_hidden: Callable[[], None] | None = None,
):
    """Button that opens a menu of overflow tab ids (+ optional restore)."""
    import tkinter as tk

    c = theme.COLORS
    label = "›"
    if overflow_tabs:
        label = f"›{len(overflow_tabs)}"
    btn = tk.Button(
        parent,
        text=label,
        relief="flat",
        borderwidth=0,
        padx=8,
        pady=4,
        bg=c["bg_elevated"],
        fg=c["fg_secondary"],
        activebackground=c["tab_active_bg"],
        activeforeground=c["fg_bright"],
        font=theme.font(10, bold=True),
    )

    def open_menu(_event=None):
        menu = tk.Menu(
            parent,
            tearoff=False,
            bg=c["bg_chrome"],
            fg=c["fg"],
            activebackground=c["accent_active"],
            activeforeground=c["fg_bright"],
        )
        for info in overflow_tabs:
            text = info.title
            if info.unread:
                n = info.unread if info.unread < 100 else "99+"
                text = f"{text}  ({n})"
            menu.add_command(label=text, command=lambda t=info.tab_id: on_select(t))
        if hidden_restore_count and on_restore_hidden:
            if overflow_tabs:
                menu.add_separator()
            menu.add_command(
                label=f"Restore hidden ({hidden_restore_count})…",
                command=on_restore_hidden,
            )
        try:
            menu.tk_popup(
                btn.winfo_rootx(),
                btn.winfo_rooty() + btn.winfo_height(),
            )
        finally:
            menu.grab_release()

    btn.configure(command=open_menu)
    return btn
