from sb_tabs.models import ALL_CHANNELS_TAB, TabInfo
from sb_ui.tabs import TabStrip


def test_tab_strip_builds(tk_root):
    selected = []
    closed = []

    strip = TabStrip(
        tk_root,
        on_select=lambda t: selected.append(t),
        on_close=lambda t: closed.append(t),
        on_close_others=lambda t: None,
        on_close_all=lambda: None,
        max_visible=4,
    )
    strip.pack(fill="x")
    tabs = [
        TabInfo(ALL_CHANNELS_TAB, "All", closable=False),
        TabInfo("Corp", "Corp", unread=3),
        TabInfo("Fleet", "Fleet"),
        TabInfo("Local", "Local"),
        TabInfo("Intel", "Intel"),
        TabInfo("Mining", "Mining"),
    ]
    strip.set_tabs(tabs, active_id=ALL_CHANNELS_TAB, hidden_count=1)
    assert strip.frame.winfo_exists()
    # All + overflow for extras
    children = strip._inner.winfo_children()
    assert len(children) >= 2
