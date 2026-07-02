"""Reusable Signal Bridge widget builders. All styling comes from sb_ui.theme."""

import tkinter as tk

from . import theme


def card(parent, heading: str, note: str | None = None) -> tk.LabelFrame:
    frame = tk.LabelFrame(parent, text=heading, bg=theme.COLORS["bg"],
                          fg=theme.COLORS["fg"], padx=10, pady=8)
    frame.pack(fill="x", padx=6, pady=8)
    if note:
        tk.Label(frame, text=note, wraplength=590, justify="left",
                 **theme.label_kw(muted=True)).pack(anchor="w", pady=(0, 6))
    return frame


def action_row(parent) -> tk.Frame:
    row = tk.Frame(parent, bg=theme.COLORS["bg"])
    row.pack(fill="x", pady=4)
    return row


def action_button(parent, text: str, command) -> tk.Button:
    btn = tk.Button(parent, text=text, command=command, padx=10,
                    **theme.btn_secondary_kw())
    btn.pack(side="left", padx=(0, 8), pady=4)
    return btn


def primary_button(parent, text: str, command) -> tk.Button:
    return tk.Button(parent, text=text, command=command, padx=16,
                     **theme.btn_primary_kw())


def check(parent, text: str, var, command=None) -> tk.Checkbutton:
    cb = tk.Checkbutton(parent, text=text, variable=var, command=command,
                        **theme.check_kw())
    cb.pack(anchor="w", pady=2)
    return cb


def info_label(parent, text: str, muted: bool = False, wraplength: int = 600) -> tk.Label:
    lbl = tk.Label(parent, text=text, justify="left", anchor="w",
                   wraplength=wraplength, **theme.label_kw(muted=muted))
    lbl.pack(anchor="w", fill="x", pady=2)
    return lbl


def balanced_paned(parent, left_min: int = 260, right_min: int = 260,
                   fraction: float = 0.5):
    """Return a PanedWindow whose sash tracks the configured fraction until drag."""
    paned = tk.PanedWindow(parent, orient="horizontal", bg=theme.COLORS["bg"],
                           sashwidth=8, sashrelief="flat", bd=0, showhandle=False)
    left = tk.Frame(paned, bg=theme.COLORS["bg"])
    right = tk.Frame(paned, bg=theme.COLORS["bg"])
    paned.add(left, minsize=left_min, stretch="always")
    paned.add(right, minsize=right_min, stretch="always")
    state = {"user_moved": False, "last_width": 0, "after_id": None}

    def place_sash():
        state["after_id"] = None
        if state["user_moved"]:
            return
        width = paned.winfo_width()
        if width <= 1 or width == state["last_width"]:
            return
        state["last_width"] = width
        x = max(left_min, min(int(width * fraction), width - right_min))
        try:
            paned.sash_place(0, x, 0)
        except tk.TclError:
            pass

    def schedule_sash(_event=None):
        if state["user_moved"] or state["after_id"] is not None:
            return
        state["after_id"] = paned.after_idle(place_sash)

    def mark_user_moved(_event):
        state["user_moved"] = True

    paned.bind("<Configure>", schedule_sash)
    paned.bind("<ButtonRelease-1>", mark_user_moved, add="+")
    return paned, left, right
