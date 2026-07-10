import time

from sb_monitor import BoundedSeen, row_in_backlog_window


def test_bounded_seen_evicts():
    s = BoundedSeen(limit=3)
    assert s.add(("a",)) is True
    assert s.add(("b",)) is True
    assert s.add(("c",)) is True
    assert s.add(("a",)) is False
    assert s.add(("d",)) is True
    assert ("a",) not in s
    assert len(s) == 3


def test_backlog_window_recent():
    # Build a timestamp ~2 minutes ago
    import datetime as dt
    past = dt.datetime.fromtimestamp(time.time() - 120)
    stamp = past.strftime("%Y.%m.%d %H:%M:%S")
    assert row_in_backlog_window(stamp, now_ts=time.time(), backlog_minutes=10) is True
    assert row_in_backlog_window(stamp, now_ts=time.time(), backlog_minutes=1) is False
