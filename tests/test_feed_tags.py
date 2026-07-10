from sb_ui.feed import apply_base_feed_colors, default_feed_background, default_feed_foreground
from sb_ui import theme


def test_default_feed_colors():
    assert default_feed_background() == theme.COLORS["bg_feed"]
    assert default_feed_foreground() == theme.COLORS["fg"]


def test_apply_base_feed_colors(tk_root):
    import tkinter as tk
    t = tk.Text(tk_root)
    apply_base_feed_colors(t)
    assert t.cget("bg") == theme.COLORS["bg_feed"]
    assert t.cget("fg") == theme.COLORS["fg"]
