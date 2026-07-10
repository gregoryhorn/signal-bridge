"""Main window shell builders (chrome + layout slots)."""

from sb_ui.shell.layout import LayoutHandles, build_main_layout
from sb_ui.shell.main_chrome import ChromeHandles, build_header_bar, menu_colors

__all__ = [
    "ChromeHandles",
    "LayoutHandles",
    "build_header_bar",
    "build_main_layout",
    "menu_colors",
]
