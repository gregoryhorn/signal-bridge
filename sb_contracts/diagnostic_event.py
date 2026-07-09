"""Diagnostic event helpers and secret redaction — pure stdlib."""

from __future__ import annotations

import time
from typing import Any

SECRET_KEY_FRAGMENTS = (
    "token",
    "secret",
    "authorization",
    "password",
    "client_secret",
    "refresh_token",
    "access_token",
)


def _is_secret_key(key: str) -> bool:
    k = str(key).casefold()
    return any(frag in k for frag in SECRET_KEY_FRAGMENTS)


def redact_context(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _is_secret_key(str(k)):
                out[k] = "[redacted]"
            else:
                out[k] = redact_context(v)
        return out
    if isinstance(value, list):
        return [redact_context(v) for v in value]
    return value


def make_diagnostic_event(event_type: str, **context) -> dict:
    payload = {"type": event_type, **context}
    redacted = redact_context(payload)
    if not isinstance(redacted, dict):
        redacted = {"type": event_type}
    redacted.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    redacted.setdefault("schema_version", 1)
    return redacted
