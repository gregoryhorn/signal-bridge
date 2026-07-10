from sb_ui.shell import build_header_bar, build_main_layout, menu_colors
from sb_ui import theme


def test_menu_colors_void_tactical():
    m = menu_colors()
    assert m["bg"] == theme.COLORS["bg_chrome"]
    assert m["fg"] == theme.COLORS["fg"]


def test_build_header_bar(tk_root):
    chrome = build_header_bar(tk_root, title="Signal Bridge v0.7", status="Idle")
    chrome.frame.pack(fill="x")
    assert chrome.title_label.cget("text") == "Signal Bridge v0.7"
    assert chrome.status_label.cget("text") == "Idle"
    assert chrome.frame.cget("bg") == theme.COLORS["bg_chrome"]
    assert chrome.title_label.cget("fg") == theme.COLORS["fg"]


def test_build_main_layout_slots(tk_root):
    layout = build_main_layout(tk_root, create_feed=True, feed_font=theme.font(10))
    assert layout.header_host is not None
    assert layout.tabs_host is not None
    assert layout.feed_host is not None
    assert layout.feed_text is not None
    assert layout.feed_scroll is not None
    assert layout.feed_host.cget("bg") == theme.COLORS["bg_feed"]
