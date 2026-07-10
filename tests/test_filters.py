from sb_filters import FeedFilter, normalize_filters, row_is_filtered


def test_keyword_contains_casefold():
    filters = [FeedFilter(id="1", kind="keyword", pattern="buy", enabled=True)]
    assert row_is_filtered("A", "WTB buy plex", filters)[0] is True
    assert row_is_filtered("A", "hostile in system", filters)[0] is False


def test_sender_exact():
    filters = [
        FeedFilter(id="2", kind="sender", pattern="SpamBot", match_mode="exact", enabled=True)
    ]
    assert row_is_filtered("SpamBot", "hi", filters)[0] is True
    assert row_is_filtered("SpamBotAlt", "hi", filters)[0] is False


def test_disabled_filter_ignored():
    filters = [FeedFilter(id="3", kind="keyword", pattern="x", enabled=False)]
    assert row_is_filtered("A", "x marks", filters)[0] is False


def test_normalize_filters():
    raw = [{"kind": "keyword", "pattern": "  isk  ", "enabled": True}]
    out = normalize_filters(raw)
    assert len(out) == 1
    assert out[0].pattern == "isk"
