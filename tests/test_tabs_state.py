from sb_tabs import (
    ALL_CHANNELS_TAB,
    TabStripState,
    clear_unread,
    close_all_closable,
    close_others,
    close_tab,
    mark_unread,
    move_before,
    normalize,
    overflow_split,
    reorder,
    select_tab,
    state_from_settings,
    state_to_settings_patch,
    visible_tabs,
)


def _state(open_ch=None):
    open_ch = open_ch or {"Corp", "Fleet"}
    s = TabStripState(
        order=[ALL_CHANNELS_TAB, "Corp", "Fleet", "Local"],
        active_id=ALL_CHANNELS_TAB,
        hidden=set(),
        unread={},
    )
    return normalize(s, open_ch), open_ch


def test_all_pinned_first():
    s, open_ch = _state()
    s.order = ["Corp", ALL_CHANNELS_TAB, "Fleet"]
    s = normalize(s, open_ch)
    assert s.order[0] == ALL_CHANNELS_TAB


def test_select_clears_unread():
    s, open_ch = _state()
    s.unread["Corp"] = 3
    s = select_tab(s, "Corp", open_ch)
    assert s.active_id == "Corp"
    assert "Corp" not in s.unread


def test_close_selects_neighbor():
    s, open_ch = _state({"Corp", "Fleet", "Local"})
    s = select_tab(s, "Fleet", open_ch)
    s = close_tab(s, "Fleet", open_ch)
    assert "Fleet" in s.hidden
    assert s.active_id in ("Local", "Corp", ALL_CHANNELS_TAB)
    assert s.active_id != "Fleet"


def test_close_others():
    s, open_ch = _state({"Corp", "Fleet", "Local"})
    s = close_others(s, "Corp", open_ch)
    vis = visible_tabs(s, open_ch)
    ids = [t.tab_id for t in vis]
    assert ids == [ALL_CHANNELS_TAB, "Corp"] or ids == ["Corp"] or ALL_CHANNELS_TAB in ids
    assert "Corp" in ids
    assert "Fleet" not in ids


def test_close_all_closable_keeps_all():
    s, open_ch = _state()
    s = close_all_closable(s, open_ch)
    vis = visible_tabs(s, open_ch)
    assert [t.tab_id for t in vis] == [ALL_CHANNELS_TAB]
    assert s.active_id == ALL_CHANNELS_TAB


def test_reorder_channels_all_stays_first():
    s, open_ch = _state({"Corp", "Fleet", "Local"})
    s = normalize(s, open_ch)
    # visible channel indices: Corp=0, Fleet=1, Local=2 among non-All
    s = reorder(s, 0, 2, open_ch)
    channels = [t for t in s.order if t != ALL_CHANNELS_TAB]
    assert s.order[0] == ALL_CHANNELS_TAB
    assert channels[0] == "Fleet"
    assert "Corp" in channels


def test_move_before():
    s, open_ch = _state({"Corp", "Fleet", "Local"})
    s = move_before(s, "Local", "Corp", open_ch)
    channels = [t for t in s.order if t != ALL_CHANNELS_TAB]
    assert channels.index("Local") < channels.index("Corp")


def test_mark_unread_skips_active():
    s, open_ch = _state()
    s = select_tab(s, "Corp", open_ch)
    s = mark_unread(s, "Corp", delta=1)
    assert "Corp" not in s.unread
    s = mark_unread(s, "Fleet", delta=2)
    assert s.unread["Fleet"] == 2
    s = clear_unread(s, "Fleet")
    assert "Fleet" not in s.unread


def test_overflow_split():
    s, open_ch = _state({"A", "B", "C", "D"})
    s = normalize(s, open_ch)
    vis = visible_tabs(s, open_ch)
    primary, overflow = overflow_split(vis, 3)
    assert len(primary) == 3
    assert len(overflow) == len(vis) - 3


def test_persistence_roundtrip():
    s = TabStripState(
        order=[ALL_CHANNELS_TAB, "Corp"],
        active_id="Corp",
        hidden={"Fleet"},
        unread={"Corp": 1},
    )
    patch = state_to_settings_patch(s)
    loaded = state_from_settings(patch)
    assert loaded.order == s.order
    assert loaded.active_id == "Corp"
    assert loaded.hidden == {"Fleet"}
    # unread is runtime-only
    assert loaded.unread == {}


def test_visible_tabs_titles_and_closable():
    s, open_ch = _state()
    vis = visible_tabs(s, open_ch, titles={"Corp": "Very Long Corporation Channel Name"})
    all_tab = next(t for t in vis if t.tab_id == ALL_CHANNELS_TAB)
    assert all_tab.closable is False
    assert all_tab.title == "All"
    corp = next(t for t in vis if t.tab_id == "Corp")
    assert corp.closable is True
    assert len(corp.title) <= 28
