"""Central Signal Bridge UI theme: every color/font used by widgets lives here.

Values are the canonical versions of the literals historically copy-pasted
through signal_bridge_gui.py. Change a color here, it changes everywhere.
"""

FONT_FAMILY = "Segoe UI"

COLORS = {
    "bg": "#0b0f14",
    "bg_nav": "#0f1722",
    "bg_panel": "#111821",
    "bg_input": "#070b10",
    "bg_editor": "#07111d",
    "fg": "#d7dde5",
    "fg_muted": "#8b98a8",
    "fg_bright": "#ffffff",
    "accent": "#1f6feb",
    "accent_active": "#23405c",
    "border": "#1f2f42",
    "warning": "#facc15",
    "success": "#7ee787",
    "error": "#ff8f8f",
    "gold": "#f0c36a",
}


def font(size: int = 10, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def btn_primary_kw() -> dict:
    return dict(bg=COLORS["accent"], fg=COLORS["fg_bright"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")


def btn_secondary_kw() -> dict:
    return dict(bg=COLORS["bg_panel"], fg=COLORS["fg"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")


def label_kw(muted: bool = False) -> dict:
    return dict(bg=COLORS["bg"], fg=COLORS["fg_muted"] if muted else COLORS["fg"])


def entry_kw() -> dict:
    return dict(bg=COLORS["bg_input"], fg=COLORS["fg"],
                insertbackground=COLORS["fg_bright"], relief="flat")


def check_kw() -> dict:
    return dict(bg=COLORS["bg"], fg=COLORS["fg"], selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg"], activeforeground=COLORS["fg_bright"])


def radio_kw() -> dict:
    return check_kw()


def listbox_kw() -> dict:
    return dict(bg=COLORS["bg_input"], fg=COLORS["fg"],
                selectbackground=COLORS["accent"], relief="flat", exportselection=False)


def text_kw() -> dict:
    return dict(bg=COLORS["bg_editor"], fg="#e6edf3",
                insertbackground=COLORS["fg_bright"], relief="flat", wrap="word", undo=True)


def optionmenu_kw() -> dict:
    return dict(bg=COLORS["bg_panel"], fg=COLORS["fg"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")


def apply_ttk_styles(root) -> None:
    """Configure dark SB.* ttk styles. Safe to call repeatedly."""
    from tkinter import ttk
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("SB.Treeview",
                    background=COLORS["bg_input"],
                    fieldbackground=COLORS["bg_input"],
                    foreground=COLORS["fg"],
                    borderwidth=0, rowheight=22)
    style.configure("SB.Treeview.Heading",
                    background=COLORS["bg_panel"],
                    foreground=COLORS["fg"], relief="flat")
    style.map("SB.Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", COLORS["fg_bright"])])
