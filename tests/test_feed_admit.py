from sb_feed_admit import should_admit_row
from sb_filters import FeedFilter
from sb_spam import SpamLimiter, SpamPolicy


def test_admit_allows_clean():
    r = should_admit_row("Scout", "Jita Caracal", "Intel", [])
    assert r.admit and r.reason == "allow"


def test_admit_filter_blocks():
    filters = [FeedFilter(id="1", kind="keyword", pattern="plex")]
    r = should_admit_row("A", "sell plex", "Local", filters)
    assert not r.admit
    assert r.reason.startswith("filter_keyword")


def test_admit_spam_blocks():
    limiter = SpamLimiter(SpamPolicy(local_channels_only=True, repeat_sender_max=1, per_channel_max_per_minute=100))
    assert should_admit_row("Bob", "a", "Local", [], limiter, now=1.0).admit
    r = should_admit_row("Bob", "b", "Local", [], limiter, now=1.1)
    assert not r.admit
