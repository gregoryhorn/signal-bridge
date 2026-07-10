"""Tk tab strip with real tab buttons (Void Tactical)."""

from __future__ import annotations

from typing import Callable

from sb_tabs.models import TabInfo
from sb_tabs.state import overflow_split
from sb_ui import theme
from sb_ui.tabs.menu import build_tab_context_menu, popup_menu
from sb_ui.tabs.overflow import build_overflow_button


class TabStrip:
    """Horizontal tab strip. Does not own channel state — parent passes TabInfo list."""

    def __init__(
        self,
        parent,
        *,
        on_select: Callable[[str], None],
        on_close: Callable[[str], None],
        on_close_others: Callable[[str], None],
        on_close_all: Callable[[], None],
        on_copy: Callable[[str], None] | None = None,
        on_restore_hidden: Callable[[], None] | None = None,
        max_visible: int = 6,
    ):
        import tkinter as tk

        self._tk = tk
        self.on_select = on_select
        self.on_close = on_close
        self.on_close_others = on_close_others
        self.on_close_all = on_close_all
        self.on_copy = on_copy
        self.on_restore_hidden = on_restore_hidden
        self.max_visible = max(2, int(max_visible))
        c = theme.COLORS
        self.frame = tk.Frame(parent, bg=c["bg_chrome"])
        self._inner = tk.Frame(self.frame, bg=c["bg_chrome"])
        self._inner.pack(fill="x")
        self._widgets: dict[str, object] = {}
        self._active_id: str | None = None

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        return self

    def set_tabs(
        self,
        tabs: list[TabInfo],
        active_id: str | None,
        *,
        hidden_count: int = 0,
    ) -> None:
        for child in self._inner.winfo_children():
            child.destroy()
        self._widgets.clear()
        self._active_id = active_id
        c = theme.COLORS
        tk = self._tk

        if not tabs:
            empty = tk.Frame(self._inner, bg=c["bg_chrome"])
            empty.pack(fill="x")
            tk.Label(
                empty,
                text="No visible channels",
                bg=c["bg_chrome"],
                fg=c["fg_muted"],
                font=theme.font(9),
            ).pack(side="left", padx=4)
            if self.on_restore_hidden:
                tk.Button(
                    empty,
                    text="Restore…",
                    command=self.on_restore_hidden,
                    relief="flat",
                    bg=c["bg_panel"],
                    fg=c["fg_secondary"],
                    padx=6,
                    pady=2,
                    font=theme.font(9),
                ).pack(side="left", padx=6)
            return

        primary, overflow = overflow_split(tabs, self.max_visible)
        for info in primary:
            self._add_tab_button(info, active=(info.tab_id == active_id))

        if overflow or hidden_count:
            build_overflow_button(
                self._inner,
                overflow,
                on_select=self.on_select,
                hidden_restore_count=hidden_count,
                on_restore_hidden=self.on_restore_hidden,
            ).pack(side="right", padx=(4, 0))

    def _add_tab_button(self, info: TabInfo, *, active: bool) -> None:
        tk = self._tk
        c = theme.COLORS
        cell = tk.Frame(self._inner, bg=c["tab_active_bg"] if active else c["bg_chrome"])
        cell.pack(side="left", padx=(0, 2))

        bg = c["tab_active_bg"] if active else c["bg_chrome"]
        fg = c["fg_bright"] if active else c["fg_secondary"]
        if not active and info.unread:
            fg = c["fg"]

        title = info.title
        btn = tk.Button(
            cell,
            text=title,
            command=lambda t=info.tab_id: self.on_select(t),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=6,
            bg=bg,
            fg=fg,
            activebackground=c["bg_elevated"],
            activeforeground=c["fg_bright"],
            font=theme.font(9, bold=active or bool(info.unread)),
        )
        btn.pack(side="left")

        if info.unread and not active:
            badge = tk.Label(
                cell,
                text=str(info.unread) if info.unread < 100 else "99+",
                bg=c["accent"],
                fg=c["fg_bright"],
                font=theme.mono_font(8, bold=True),
                padx=4,
                pady=0,
            )
            badge.pack(side="left", padx=(0, 4), pady=4)

        if info.closable:
            close = tk.Button(
                cell,
                text="×",
                command=lambda t=info.tab_id: self.on_close(t),
                relief="flat",
                borderwidth=0,
                padx=4,
                pady=2,
                bg=bg,
                fg=c["fg_muted"],
                activebackground=c["error"],
                activeforeground=c["fg_bright"],
                font=theme.font(9),
            )
            close.pack(side="left", padx=(0, 4))
            close.bind("<Button-3>", lambda e, t=info.tab_id: self._context(e, t), add="+")

        # Active underline
        if active:
            under = tk.Frame(cell, bg=c["accent_line"], height=2)
            under.pack(fill="x", side="bottom")
            # keep height
            try:
                under.pack_propagate(False)
                under.configure(height=2)
            except Exception:
                pass

        for w in (cell, btn):
            w.bind("<Button-3>", lambda e, t=info.tab_id: self._context(e, t), add="+")
            if not active:
                w.bind("<Enter>", lambda e, fr=cell, b=btn: self._hover(fr, b, True), add="+")
                w.bind("<Leave>", lambda e, fr=cell, b=btn, i=info: self._hover_leave(fr, b, i), add="+")

        self._widgets[info.tab_id] = cell

    def _hover(self, frame, btn, on: bool) -> None:
        c = theme.COLORS
        bg = c["bg_elevated"] if on else c["bg_chrome"]
        try:
            frame.configure(bg=bg)
            btn.configure(bg=bg)
            for ch in frame.winfo_children():
                if ch is not btn and str(ch.cget("text") if hasattr(ch, "cget") else "") == "×":
                    ch.configure(bg=bg)
        except Exception:
            pass

    def _hover_leave(self, frame, btn, info: TabInfo) -> None:
        if info.tab_id == self._active_id:
            return
        c = theme.COLORS
        try:
            frame.configure(bg=c["bg_chrome"])
            btn.configure(bg=c["bg_chrome"])
            for ch in frame.winfo_children():
                try:
                    if ch.cget("text") == "×":
                        ch.configure(bg=c["bg_chrome"])
                except Exception:
                    pass
        except Exception:
            pass

    def _context(self, event, tab_id: str) -> None:
        menu = build_tab_context_menu(
            self.frame,
            tab_id,
            on_close=self.on_close,
            on_close_others=self.on_close_others,
            on_close_all=self.on_close_all,
            on_copy=self.on_copy,
            on_restore_hidden=self.on_restore_hidden,
        )
        popup_menu(menu, event)
