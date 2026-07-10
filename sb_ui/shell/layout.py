"""Main window layout slots: header host, tabs host, feed host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sb_ui import theme


@dataclass
class LayoutHandles:
    """Slots for main shell regions. Widgets are created empty for the app to fill."""

    root: Any
    header_host: Any
    tabs_host: Any
    feed_host: Any
    footer_host: Any
    feed_text: Any | None = None
    feed_scroll: Any | None = None


def build_main_layout(root, *, create_feed: bool = True, feed_font=None) -> LayoutHandles:
    """
    Pack vertical shell: header_host, tabs_host, feed_host.
    Does not build header contents or tabs — only hosts and optional Text+scrollbar.
    """
    import tkinter as tk
    c = theme.COLORS
    header_host = tk.Frame(root, bg=c["bg_chrome"])
    header_host.pack(fill="x")
    tabs_host = tk.Frame(
        root,
        bg=c["bg"],
        padx=theme.SPACING["sm"] - 2,
        pady=theme.SPACING["xs"],
    )
    tabs_host.pack(fill="x")
    footer_host = tk.Frame(root, bg=c["bg_chrome"], highlightthickness=1,
                           highlightbackground=c["border"])
    footer_host.pack(fill="x", side="bottom")
    feed_host = tk.Frame(root, bg=c["bg_feed"])
    feed_host.pack(fill="both", expand=True)

    feed_text = None
    feed_scroll = None
    if create_feed:
        font = feed_font or theme.font(10)
        feed_text = tk.Text(
            feed_host,
            relief="flat",
            wrap="word",
            font=font,
            padx=theme.SPACING["sm"],
            pady=theme.SPACING["sm"],
            undo=False,
            bg=c["bg_feed"],
            fg=c["fg"],
            insertbackground=c["fg"],
        )
        feed_scroll = tk.Scrollbar(feed_host, orient="vertical", command=feed_text.yview)
        feed_text.configure(yscrollcommand=feed_scroll.set)
        feed_text.pack(side="left", fill="both", expand=True)
        feed_scroll.pack(side="right", fill="y")

    return LayoutHandles(
        root=root,
        header_host=header_host,
        tabs_host=tabs_host,
        feed_host=feed_host,
        footer_host=footer_host,
        feed_text=feed_text,
        feed_scroll=feed_scroll,
    )
