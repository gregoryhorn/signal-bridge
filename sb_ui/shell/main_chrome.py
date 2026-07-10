"""Header / status strip for the main Signal Bridge window (Void Tactical)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sb_ui import theme


@dataclass
class ChromeHandles:
    frame: Any
    title_label: Any
    mode_label: Any
    status_label: Any
    scan_line: Any


def menu_colors() -> dict[str, str]:
    """Colors for tk.Menu construction."""
    return {
        "bg": theme.COLORS["bg_chrome"],
        "fg": theme.COLORS["fg"],
    }


def build_header_bar(parent, *, title: str, status: str = "Idle") -> ChromeHandles:
    """Build title + status row. Caller packs the returned frame."""
    import tkinter as tk
    c = theme.COLORS
    frame = tk.Frame(parent, bg=c["bg_chrome"])
    title_label = tk.Label(
        frame,
        text=title,
        bg=c["bg_chrome"],
        fg=c["fg"],
        font=theme.font(11, bold=True),
        padx=theme.SPACING["sm"],
        pady=theme.SPACING["xs"] + 1,
    )
    title_label.pack(side="left")
    mode_label = tk.Label(
        frame,
        text="",
        bg=c["bg_chrome"],
        fg=theme.COLORS["accent_line"],
        font=theme.font(9),
        padx=theme.SPACING["sm"],
    )
    # mode_label packed when text is non-empty by caller if desired
    status_label = tk.Label(
        frame,
        text=status,
        bg=c["bg_chrome"],
        fg=c["fg_muted"],
        font=theme.font(9),
        padx=theme.SPACING["sm"],
    )
    # The live status itself lives in the shell footer; retain this handle for
    # callers that need a compact header status in a future embedded layout.
    scan_line = tk.Frame(frame, bg=c["accent_line"], height=2)
    scan_line.pack(side="bottom", fill="x")
    scan_line.pack_propagate(False)
    return ChromeHandles(
        frame=frame,
        title_label=title_label,
        mode_label=mode_label,
        status_label=status_label,
        scan_line=scan_line,
    )
