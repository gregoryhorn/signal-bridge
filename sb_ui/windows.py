"""Toplevel window chrome, stacking, and sizing helpers."""

import tkinter as tk

from . import theme


def _noop(_msg: str) -> None:
    pass


def polish_window(win, parent, *, width=None, height=None, minsize=None,
                  modal=False, center=True, title=None, icon_path=None,
                  log=None):
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
            if center:
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
                   pad=(24, 24)):
    """Size `win` to content request, clamped to bounds and screen."""
    win.update_idletasks()
    req_w = win.winfo_reqwidth() + pad[0]
    req_h = win.winfo_reqheight() + pad[1]
    screen_w = win.winfo_screenwidth() - 80
    screen_h = win.winfo_screenheight() - 120
    width = max(min_size[0], min(req_w, max_size[0], screen_w))
    height = max(min_size[1], min(req_h, max_size[1], screen_h))
    if parent is not None:
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
