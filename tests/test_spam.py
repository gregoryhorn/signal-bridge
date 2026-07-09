from sb_spam import SpamLimiter, SpamPolicy, looks_like_ascii_art


def test_ascii_art_detection():
    art = "\n".join(["@" * 20 for _ in range(8)])
    assert looks_like_ascii_art(art) is True
    assert looks_like_ascii_art("Jita Caracal") is False


def test_rate_sender_burst():
    limiter = SpamLimiter(
        SpamPolicy(
            enabled=True,
            local_channels_only=True,
            repeat_sender_window_seconds=8,
            repeat_sender_max=3,
            per_channel_max_per_minute=100,
        )
    )
    now = 1000.0
    for i in range(3):
        ok, _ = limiter.allow("Local", "Bob", f"hi {i}", now=now + i)
        assert ok
    ok, reason = limiter.allow("Local", "Bob", "hi again", now=now + 3)
    assert ok is False
    assert reason == "spam_rate_sender"


def test_intel_with_system_not_ascii_suppressed():
    art = "\n".join(["#" * 20 for _ in range(8)])
    limiter = SpamLimiter(SpamPolicy(enabled=True, local_channels_only=False))
    ok, reason = limiter.allow("Intel", "Scout", art, systems=["Jita"])
    assert ok is True
    assert reason == "allow"


def test_non_local_skipped_when_local_only():
    limiter = SpamLimiter(SpamPolicy(enabled=True, local_channels_only=True, repeat_sender_max=1))
    ok1, _ = limiter.allow("Intel", "Bob", "a", now=1.0)
    ok2, _ = limiter.allow("Intel", "Bob", "b", now=1.1)
    assert ok1 and ok2
