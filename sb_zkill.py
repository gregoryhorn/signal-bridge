"""Pure zKill event ranking helpers: gang-size labels, kill ranking, loss picking.

Small-gang engagements are more informative for judging a pilot than large
fleet killmails, so kills are ranked small-gang-first with large-fleet
fallback. No I/O here; callers pass event dicts.
"""

SMALL_GANG_MAX = 10


def _participants(event: dict) -> int:
    try:
        return int(event.get("participants") or 0)
    except (TypeError, ValueError):
        return 0


def _time_key(event: dict) -> str:
    return str(event.get("time") or "")


def gang_label(participants: int) -> str:
    if participants <= 1:
        return "solo"
    if participants <= 5:
        return "small gang"
    if participants <= SMALL_GANG_MAX:
        return "fleet"
    return "large fleet"


def rank_kills(events: list, cap: int = 5) -> list:
    kills = [e for e in events or [] if e.get("type") == "kill"]
    small = sorted((e for e in kills if _participants(e) <= SMALL_GANG_MAX),
                   key=_time_key, reverse=True)
    large = sorted((e for e in kills if _participants(e) > SMALL_GANG_MAX),
                   key=_time_key, reverse=True)
    return (small + large)[:cap]


def pick_losses(events: list, cap: int = 5) -> list:
    losses = [e for e in events or [] if e.get("type") == "loss"]
    losses.sort(key=_time_key, reverse=True)
    return losses[:cap]
