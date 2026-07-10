"""Toplevel window chrome, stacking, and sizing helpers."""

import tkinter as tk
from typing import Literal

from . import theme


WindowPlacementPolicy = Literal["beside_parent", "center_parent", "remember"]
WINDOW_GAP = 16


def _noop(_msg: str) -> None:
    pass


def place_beside_bounds(parent_bounds, child_size, work_area, preferred=("right", "left", "below")) -> tuple[int, int]:
    """Choose a fully visible sibling position within a monitor work area."""
    px, py, pw, ph = parent_bounds
    width, height = child_size
    wx, wy, ww, wh = work_area

    candidates = {
        "right": (px + pw + WINDOW_GAP, py + max(0, (ph - height) // 2)),
        "left": (px - WINDOW_GAP - width, py + max(0, (ph - height) // 2)),
        "below": (px + max(0, (pw - width) // 2), py + ph + WINDOW_GAP),
    }
    for direction in preferred:
        x, y = candidates[direction]
        if wx <= x and wy <= y and x + width <= wx + ww and y + height <= wy + wh:
            return x, y

    centered_x = px + (pw - width) // 2
    centered_y = py + (ph - height) // 2
    max_x = max(wx, wx + ww - width)
    max_y = max(wy, wy + wh - height)
    return max(wx, min(centered_x, max_x)), max(wy, min(centered_y, max_y))


def polish_window(win, parent, *, width=None, height=None, minsize=None,
                  modal=False, center=True, title=None, icon_path=None,
                  log=None, placement: WindowPlacementPolicy | None = None,
                  preserve_position: bool = False):
    """Apply consistent Signal Bridge chrome, icon, stacking, and placement."""
    log = log or _noop
    if title:
        try:
            win.title(title)
        except Exception as exc:
            log(f"Window title failed: {exc}")
    if icon_path:
        try:
            win.iconbitmap(str(icon_path))
        except Exception as exc:
            log(f"Window icon failed: {exc}")
    try:
        win.configure(bg=theme.COLORS["bg"])
    except Exception as exc:
        log(f"Window bg failed: {exc}")
    if minsize:
        try:
            win.minsize(*minsize)
        except Exception as exc:
            log(f"Window minsize failed: {exc}")
    if width and height:
        try:
            policy = placement or ("center_parent" if center else "remember")
            if preserve_position or policy == "remember":
                win.geometry(f"{width}x{height}")
            elif policy == "beside_parent":
                parent.update_idletasks()
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw = max(1, parent.winfo_width())
                ph = max(1, parent.winfo_height())
                x, y = place_beside_bounds(
                    (px, py, pw, ph), (width, height),
                    (0, 0, win.winfo_screenwidth(), win.winfo_screenheight()),
                )
                win.geometry(f"{width}x{height}+{x}+{y}")
            elif policy == "center_parent":
                parent.update_idletasks()
                win.update_idletasks()
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw = max(1, parent.winfo_width())
                ph = max(1, parent.winfo_height())
                x = max(0, px + (pw - width) // 2)
                y = max(0, py + (ph - height) // 2)
                win.geometry(f"{width}x{height}+{x}+{y}")
            else:
                win.geometry(f"{width}x{height}")
            win.update_idletasks()
        except Exception as exc:
            log(f"Window centering failed: {exc}")
            win.geometry(f"{width}x{height}")
            win.update_idletasks()
    try:
        win.transient(parent)
    except Exception as exc:
        log(f"Window transient failed: {exc}")
    if modal:
        try:
            win.grab_set()
        except Exception as exc:
            log(f"Window grab failed: {exc}")
    try:
        win.lift(parent)
        win.focus_force()
    except Exception as exc:
        log(f"Window lift/focus failed: {exc}")
    return win


def fit_to_content(win, parent=None, min_size=(560, 430), max_size=(1100, 800),
                   pad=(24, 24), preserve_position: bool = False):
    """Size `win` to content request, clamped to bounds and screen."""
    win.update_idletasks()
    req_w = win.winfo_reqwidth() + pad[0]
    req_h = win.winfo_reqheight() + pad[1]
    screen_w = win.winfo_screenwidth() - 80
    screen_h = win.winfo_screenheight() - 120
    width = max(min_size[0], min(req_w, max_size[0], screen_w))
    height = max(min_size[1], min(req_h, max_size[1], screen_h))
    if preserve_position:
        try:
            x, y = win.winfo_x(), win.winfo_y()
            win.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            win.geometry(f"{width}x{height}")
    elif parent is not None:
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw = max(1, parent.winfo_width())
            ph = max(1, parent.winfo_height())
            x = max(0, px + (pw - width) // 2)
            y = max(0, py + (ph - height) // 2)
            win.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            win.geometry(f"{width}x{height}")
    else:
        win.geometry(f"{width}x{height}")
    win.update_idletasks()
    return width, height
