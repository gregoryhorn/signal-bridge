"""Single admit pipeline for feed rows (filters + spam)."""

from __future__ import annotations

from dataclasses import dataclass

from sb_filters import FeedFilter, row_is_filtered
from sb_spam import SpamLimiter


@dataclass
class AdmitResult:
    admit: bool
    reason: str


def should_admit_row(
    sender: str,
    text: str,
    channel: str,
    filters: list[FeedFilter],
    spam_limiter: SpamLimiter | None = None,
    *,
    systems: list[str] | None = None,
    now: float | None = None,
) -> AdmitResult:
    filtered, reason = row_is_filtered(sender, text, filters)
    if filtered:
        return AdmitResult(admit=False, reason=reason)
    if spam_limiter is not None:
        ok, spam_reason = spam_limiter.allow(
            channel, sender, text, systems=systems, now=now
        )
        if not ok:
            return AdmitResult(admit=False, reason=spam_reason)
    return AdmitResult(admit=True, reason="allow")
