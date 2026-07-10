"""Central Signal Bridge UI theme: every color/font used by widgets lives here.

v0.7 approved palette: **Void Tactical** (Mockup A).
Spec: docs/superpowers/specs/2026-07-10-v0.7-void-tactical-theme.md
Mockup: docs/images/signal-bridge-v0.7-theme-mockup-a.png
"""

from __future__ import annotations

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

# Spacing scale (px): prefer these over one-off padding
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

# Void Tactical tokens (canonical)
COLORS = {
    # Surfaces
    "bg": "#070a0f",
    "bg_chrome": "#0c121a",
    "bg_nav": "#0c121a",
    "bg_panel": "#121a24",
    "bg_surface": "#121a24",
    "bg_elevated": "#182230",
    "bg_feed": "#0a0e14",
    "bg_input": "#070b10",
    "bg_editor": "#0a0e14",
    # Text
    "fg": "#e8eef6",
    "fg_secondary": "#9aa8b8",
    "fg_muted": "#6b7a8c",
    "fg_bright": "#ffffff",
    # Accent (cyan scan)
    "accent": "#3d9cf0",
    "accent_active": "#1a2838",
    "accent_line": "#5ec8ff",
    "accent_soft": "#3d9cf024",  # ~14% — use sparingly; Tk often needs solid
    "border": "#243041",
    "border_strong": "#334155",
    # Status
    "warning": "#e8c547",
    "success": "#5ddea0",
    "error": "#f07178",
    "gold": "#f0d060",
    # Entities (feed highlights)
    "entity_system": "#f0d060",
    "entity_ship": "#f0a060",
    "entity_pilot": "#ff7b72",
    "entity_link": "#79c0ff",
    "entity_clear": "#7ee787",
    "entity_count": "#c4b5fd",
    "tab_active_bg": "#1a2838",
}

THEME_NAME = "void_tactical"
THEME_VERSION = "0.7"


def font(size: int = 10, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def mono_font(size: int = 10, bold: bool = False) -> tuple:
    return (FONT_MONO, size, "bold") if bold else (FONT_MONO, size)


def feed_tag_styles() -> dict[str, dict]:
    """Kwargs for Text.tag_configure for feed entity classes."""
    return {
        "system": {"foreground": COLORS["entity_system"], "font": font(10, bold=True)},
        "ship": {"foreground": COLORS["entity_ship"], "font": font(10, bold=True)},
        "pilot": {"foreground": COLORS["entity_pilot"], "font": font(10, bold=True)},
        "link": {"foreground": COLORS["entity_link"], "underline": True},
        "clear": {"foreground": COLORS["entity_clear"]},
        "count": {"foreground": COLORS["entity_count"], "font": font(10, bold=True)},
        "timestamp": {"foreground": COLORS["fg_muted"], "font": mono_font(9)},
        "sender": {"foreground": COLORS["fg_secondary"]},
        "body": {"foreground": COLORS["fg"]},
    }


def export_theme_dict() -> dict:
    """JSON-serializable theme for LAN viewer CSS variables."""
    return {
        "name": THEME_NAME,
        "version": THEME_VERSION,
        "colors": dict(COLORS),
        "spacing": dict(SPACING),
        "fonts": {
            "ui": FONT_FAMILY,
            "mono": FONT_MONO,
        },
        "entities": {
            "system": COLORS["entity_system"],
            "ship": COLORS["entity_ship"],
            "pilot": COLORS["entity_pilot"],
            "link": COLORS["entity_link"],
            "clear": COLORS["entity_clear"],
            "count": COLORS["entity_count"],
        },
    }


def btn_primary_kw() -> dict:
    return dict(bg=COLORS["accent"], fg=COLORS["fg_bright"],
                activebackground=COLORS["accent_line"],
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
    return dict(bg=COLORS["bg_editor"], fg=COLORS["fg"],
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
