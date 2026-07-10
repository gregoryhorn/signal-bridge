"""Reusable Pilot Intel card chrome (chips, section frames)."""

from __future__ import annotations

from sb_ui import theme as sb_theme

CHIP = {
    "flag": (sb_theme.COLORS["bg_panel"], "#ffd1dc"),
    "system": ("#1a2412", sb_theme.COLORS["entity_system"]),
    "ship": ("#2a1c10", sb_theme.COLORS["entity_ship"]),
    "signal": ("#2a1810", "#ff9d5a"),
    "status": ("#14202d", "#a7c7e7"),
    "muted": (sb_theme.COLORS["bg_panel"], sb_theme.COLORS["fg_muted"]),
}


def chip(parent, text: str, kind: str = "muted"):
    import tkinter as tk

    bg, fg = CHIP.get(kind, CHIP["muted"])
    tk.Label(
        parent,
        text=str(text),
        bg=bg,
        fg=fg,
        padx=6,
        pady=1,
        font=sb_theme.font(8),
    ).pack(side="left", padx=(0, 3), pady=1)


def section(parent, title: str):
    import tkinter as tk

    f = tk.Frame(parent, bg=sb_theme.COLORS["bg_chrome"], padx=8, pady=6)
    f.pack(fill="x", pady=(0, 5))
    tk.Label(
        f,
        text=title.upper(),
        bg=f.cget("bg"),
        fg=sb_theme.COLORS["fg_muted"],
        font=sb_theme.font(8, bold=True),
    ).pack(anchor="w", pady=(0, 3))
    return f
