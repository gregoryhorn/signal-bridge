"""Bounded ring buffer of LAN feed payloads (thread-safe)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any


class FeedBuffer:
    def __init__(self, maxlen: int = 400):
        self._maxlen = max(1, int(maxlen))
        self._rows: deque[dict[str, Any]] = deque(maxlen=self._maxlen)
        self._lock = threading.Lock()
        self._seq = 0

    def append(self, row: dict) -> dict:
        with self._lock:
            self._seq += 1
            payload = dict(row)
            payload.setdefault("seq", self._seq)
            self._rows.append(payload)
            return payload

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self._rows)

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()

    @property
    def seq(self) -> int:
        with self._lock:
            return self._seq
