"""Structured logging and diagnostic JSONL (no Tk)."""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

from sb_paths import ERROR_LOG_PATH, EVENT_LOG_PATH, LOG_DIR, LOG_PATH


def write_log(message: str, exc: BaseException | None = None) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
            if exc is not None:
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                f.write("\n")
    except Exception:
        pass


def _safe_json_value(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _redact_context(value):
    """Best-effort secret redaction; upgraded when sb_contracts is available."""
    try:
        from sb_contracts.diagnostic_event import redact_context
        return redact_context(value)
    except Exception:
        return value


def write_jsonl(path: Path, event: dict) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        raw = {str(k): _safe_json_value(v) for k, v in dict(event).items()}
        payload = _redact_context(raw)
        if not isinstance(payload, dict):
            payload = raw
        payload.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


def record_event(event_type: str, **data) -> None:
    payload = {"type": event_type, **data}
    write_jsonl(EVENT_LOG_PATH, payload)


def record_error(context: str, exc: BaseException | None = None, **data) -> None:
    payload = {"type": "error", "context": context, **data}
    if exc is not None:
        payload.update({"error_type": type(exc).__name__, "error": str(exc)})
    write_jsonl(ERROR_LOG_PATH, payload)


def install_exception_logging() -> None:
    def _hook(exc_type, exc, tb):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Uncaught exception\n")
                traceback.print_exception(exc_type, exc, tb, file=f)
                f.write("\n")
        finally:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook
