"""Feed Text widget base colors from Void Tactical theme."""

from __future__ import annotations

from typing import Any

from sb_ui import theme


def default_feed_background() -> str:
    return theme.COLORS["bg_feed"]


def default_feed_foreground() -> str:
    return theme.COLORS["fg"]


def translated_subline_options() -> dict[str, int | str]:
    """Muted, indented supporting line for dual-language feed display."""
    return {
        "foreground": theme.COLORS["fg_secondary"],
        "lmargin1": theme.SPACING["lg"],
        "lmargin2": theme.SPACING["lg"],
        "spacing1": theme.SPACING["xs"],
    }


def apply_base_feed_colors(text_widget: Any, *, bg: str | None = None, fg: str | None = None, font=None) -> None:
    """Apply background/foreground/insert cursor; optional font."""
    background = bg or default_feed_background()
    foreground = fg or default_feed_foreground()
    kwargs = {
        "bg": background,
        "fg": foreground,
        "insertbackground": foreground,
    }
    if font is not None:
        kwargs["font"] = font
    text_widget.configure(**kwargs)
