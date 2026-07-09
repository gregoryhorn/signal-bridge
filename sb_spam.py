"""Local-channel spam and ASCII-art rate limiting (pure, in-memory)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class SpamPolicy:
    enabled: bool = True
    local_channels_only: bool = True
    per_channel_max_per_minute: int = 30
    repeat_sender_window_seconds: int = 8
    repeat_sender_max: int = 3
    ascii_art_min_lines: int = 6
    ascii_art_symbol_ratio: float = 0.45


def is_local_like_channel(channel: str) -> bool:
    key = str(channel or "").casefold()
    return "local" in key or "本地" in key


def looks_like_ascii_art(text: str, *, min_lines: int = 6, symbol_ratio: float = 0.45) -> bool:
    raw = str(text or "")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if len(lines) < min_lines and raw.count("\n") + 1 < min_lines:
        # Also treat very long single-line symbol spam
        sample = raw.replace(" ", "")
        if len(sample) < 40:
            return False
        symbols = sum(1 for ch in sample if not ch.isalnum())
        return (symbols / max(1, len(sample))) >= symbol_ratio and len(sample) >= 80
    if len(lines) < min_lines:
        return False
    sample = "".join(lines)
    if not sample:
        return False
    symbols = sum(1 for ch in sample if not ch.isalnum() and not ch.isspace())
    return (symbols / max(1, len(sample))) >= symbol_ratio


class SpamLimiter:
    def __init__(self, policy: SpamPolicy | None = None):
        self.policy = policy or SpamPolicy()
        self._channel_times: dict[str, deque] = defaultdict(deque)
        self._sender_times: dict[tuple[str, str], deque] = defaultdict(deque)

    def update_policy(self, policy: SpamPolicy) -> None:
        self.policy = policy

    def allow(
        self,
        channel: str,
        sender: str,
        text: str,
        *,
        systems: list[str] | None = None,
        now: float | None = None,
    ) -> tuple[bool, str]:
        policy = self.policy
        if not policy.enabled:
            return True, "allow"
        if policy.local_channels_only and not is_local_like_channel(channel):
            return True, "allow"
        ts = time.time() if now is None else float(now)
        # Preserve intel with systems
        if systems:
            return True, "allow"
        if looks_like_ascii_art(
            text,
            min_lines=policy.ascii_art_min_lines,
            symbol_ratio=policy.ascii_art_symbol_ratio,
        ):
            return False, "spam_ascii_art"
        ch_key = str(channel or "").casefold()
        ch_q = self._channel_times[ch_key]
        while ch_q and ts - ch_q[0] > 60.0:
            ch_q.popleft()
        if len(ch_q) >= max(1, int(policy.per_channel_max_per_minute)):
            return False, "spam_rate_channel"
        sk = (ch_key, str(sender or "").casefold())
        sq = self._sender_times[sk]
        window = max(1, int(policy.repeat_sender_window_seconds))
        while sq and ts - sq[0] > window:
            sq.popleft()
        if len(sq) >= max(1, int(policy.repeat_sender_max)):
            return False, "spam_rate_sender"
        ch_q.append(ts)
        sq.append(ts)
        return True, "allow"
