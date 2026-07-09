"""Live chatlog monitor with optional backlog window and bounded dedupe."""

from __future__ import annotations

import queue
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Callable


class BoundedSeen:
    """FIFO-bounded set for monitor dedupe keys."""

    def __init__(self, limit: int = 5000):
        self.limit = max(1, int(limit))
        self._order: deque = deque()
        self._set: set = set()

    def __contains__(self, key) -> bool:
        return key in self._set

    def add(self, key) -> bool:
        """Return True if newly added, False if already present."""
        if key in self._set:
            return False
        self._set.add(key)
        self._order.append(key)
        while len(self._order) > self.limit:
            old = self._order.popleft()
            self._set.discard(old)
        return True

    def __len__(self) -> int:
        return len(self._set)


def row_in_backlog_window(row_timestamp: str, *, now_ts: float, backlog_minutes: int) -> bool:
    """Best-effort parse of EVE chat timestamps; unknown times are kept (caller may cap count)."""
    if backlog_minutes <= 0:
        return False
    raw = str(row_timestamp or "").strip().replace("T", " ").replace("Z", "")
    if not raw:
        return True
    import datetime as _dt
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt = _dt.datetime.strptime(raw[:19], fmt)
            age_sec = now_ts - dt.timestamp()
            return 0 <= age_sec <= backlog_minutes * 60
        except Exception:
            continue
    return True


class MonitorThread(threading.Thread):
    def __init__(
        self,
        outq: queue.Queue,
        stop_event: threading.Event,
        status: Callable[[str], None],
        channels: set[str],
        *,
        chatlog_dir: Path,
        parse_rows: Callable,
        channel_from_filename: Callable,
        decode_bytes: Callable,
        make_db: Callable,
        write_log: Callable,
        poll_seconds: float = 1.0,
        max_chunk: int = 1024 * 1024,
        backlog_minutes: int = 0,
        backlog_row_cap: int = 200,
        seen_limit: int = 5000,
        catalog_loaded: bool = False,
        db_exists: bool = False,
    ):
        super().__init__(daemon=True)
        self.outq = outq
        self.stop_event = stop_event
        self.status = status
        self.channels = set(channels)
        self.chatlog_dir = Path(chatlog_dir)
        self.parse_rows = parse_rows
        self.channel_from_filename = channel_from_filename
        self.decode_bytes = decode_bytes
        self.write_log = write_log
        self.poll_seconds = poll_seconds
        self.max_chunk = max_chunk
        self.backlog_minutes = max(0, int(backlog_minutes or 0))
        self.backlog_row_cap = max(1, int(backlog_row_cap or 200))
        self.offsets: dict[str, int] = {}
        self.seen = BoundedSeen(seen_limit)
        self.db = make_db()
        self.catalog_loaded = catalog_loaded
        self.db_exists = db_exists

    def chat_files(self):
        files: list[Path] = []
        if self.channels:
            for channel in sorted(self.channels):
                files.extend(self.chatlog_dir.glob(channel + "_*.txt"))
        try:
            files.extend(self.chatlog_dir.glob("*.txt"))
        except Exception:
            pass
        return sorted(set(files), key=lambda p: p.stat().st_mtime_ns)

    def emit_row(self, row) -> None:
        channel = getattr(row, "channel", "") or ""
        if channel not in self.channels:
            self.channels.add(channel)
            self.outq.put(("channel_discovered", channel))
            self.write_log(f"Monitor discovered active channel={channel!r}")
        key = (channel.lower(), str(getattr(row, "sender", "")).lower(), str(getattr(row, "text", "")).lower())
        if not self.seen.add(key):
            return
        self.outq.put(row)
        text = str(getattr(row, "text", "") or "")
        self.write_log(f"Monitor emitted row channel={channel!r} sender={getattr(row, 'sender', '')!r} text={text[:120]!r}")

    def _emit_backlog(self) -> None:
        if self.backlog_minutes <= 0:
            return
        now_ts = time.time()
        recent = sorted(self.chat_files(), key=lambda x: x.stat().st_mtime_ns, reverse=True)[
            : max(3, len(self.channels) * 3)
        ]
        collected = []
        for p in recent:
            try:
                # Prefer tail of file to avoid full-history replay
                data = p.read_bytes()
                if len(data) > 64 * 1024:
                    data = data[-64 * 1024 :]
                text = self.decode_bytes(data)
            except OSError:
                continue
            rows = self.parse_rows(
                text,
                self.channel_from_filename(p),
                p.name,
                self.db,
                allow_free_translation=False,
            )
            for row in rows:
                if row_in_backlog_window(getattr(row, "received_at", ""), now_ts=now_ts, backlog_minutes=self.backlog_minutes):
                    collected.append(row)
        for row in collected[-self.backlog_row_cap :]:
            self.emit_row(row)

    def run(self):
        try:
            if not self.chatlog_dir.exists():
                self.status(f"Missing chatlog folder: {self.chatlog_dir}")
                return
            if not self.catalog_loaded and not self.db_exists:
                self.status("Warning: no compact catalog or DB available")
            if self.backlog_minutes > 0:
                self.status(f"Ingesting backlog ({self.backlog_minutes} min)...")
                self._emit_backlog()
            for p in self.chat_files():
                try:
                    self.offsets[str(p)] = p.stat().st_size
                except OSError:
                    pass
            mode = f"backlog={self.backlog_minutes}m + live" if self.backlog_minutes > 0 else "live-only"
            self.status(
                f"Monitoring {mode}: {len(self.channels)} channel(s); Catalog={'yes' if self.catalog_loaded else 'no'}"
            )
            while not self.stop_event.is_set():
                for p in self.chat_files():
                    sp = str(p)
                    try:
                        size = p.stat().st_size
                    except OSError:
                        continue
                    old = self.offsets.get(sp, 0)
                    if size < old:
                        old = 0
                    if size == old:
                        self.offsets[sp] = size
                        continue
                    if size - old > self.max_chunk:
                        old = max(0, size - self.max_chunk)
                    try:
                        with p.open("rb") as f:
                            f.seek(old)
                            data = f.read(size - old)
                        self.offsets[sp] = size
                    except OSError:
                        continue
                    rows = self.parse_rows(
                        self.decode_bytes(data),
                        self.channel_from_filename(p),
                        p.name,
                        self.db,
                        allow_free_translation=False,
                    )
                    if rows:
                        self.write_log(f"Monitor read {len(rows)} row(s) from {p.name} bytes={size - old}")
                    for row in rows:
                        self.emit_row(row)
                time.sleep(self.poll_seconds)
        except Exception:
            self.status(traceback.format_exc())
        finally:
            close = getattr(self.db, "close", None)
            if callable(close):
                close()
