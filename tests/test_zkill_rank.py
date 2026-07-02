import sb_zkill


def ev(kind, time, participants=None):
    e = {"type": kind, "time": time}
    if participants is not None:
        e["participants"] = participants
    return e


def test_gang_label_bands():
    assert sb_zkill.gang_label(0) == "solo"
    assert sb_zkill.gang_label(1) == "solo"
    assert sb_zkill.gang_label(2) == "small gang"
    assert sb_zkill.gang_label(5) == "small gang"
    assert sb_zkill.gang_label(6) == "fleet"
    assert sb_zkill.gang_label(10) == "fleet"
    assert sb_zkill.gang_label(11) == "large fleet"
    assert sb_zkill.gang_label(150) == "large fleet"


def test_rank_kills_prefers_recent_small_gang():
    events = [
        ev("kill", "2026-07-01T10:00:00Z", 40),   # large, newest
        ev("kill", "2026-06-30T10:00:00Z", 3),    # small
        ev("kill", "2026-06-28T10:00:00Z", 1),    # solo
        ev("loss", "2026-07-02T10:00:00Z", 2),    # not a kill
        ev("kill", "2026-06-29T10:00:00Z", 12),   # large
    ]
    ranked = sb_zkill.rank_kills(events, cap=3)
    assert [e["time"][:10] for e in ranked] == ["2026-06-30", "2026-06-28", "2026-07-01"]


def test_rank_kills_falls_back_to_large_when_few_small():
    events = [ev("kill", "2026-07-01T10:00:00Z", 40), ev("kill", "2026-06-30T10:00:00Z", 30)]
    assert len(sb_zkill.rank_kills(events, cap=5)) == 2


def test_rank_kills_missing_participants_counts_as_solo():
    events = [ev("kill", "2026-06-30T10:00:00Z"), ev("kill", "2026-07-01T10:00:00Z", 40)]
    ranked = sb_zkill.rank_kills(events, cap=2)
    assert ranked[0]["time"].startswith("2026-06-30")


def test_pick_losses_newest_first_capped():
    events = [ev("loss", f"2026-06-{d:02d}T00:00:00Z") for d in range(1, 9)] + [ev("kill", "2026-06-30T00:00:00Z", 1)]
    losses = sb_zkill.pick_losses(events, cap=5)
    assert len(losses) == 5
    assert losses[0]["time"].startswith("2026-06-08")
    assert all(e["type"] == "loss" for e in losses)
