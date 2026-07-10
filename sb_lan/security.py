"""Token and path safety for LAN viewer."""

from __future__ import annotations

import hmac
from pathlib import Path

from sb_lan.config import LanConfig


def check_token(config: LanConfig, query_token: str | None) -> bool:
    expected = str(config.token or "")
    if not expected:
        return False
    got = str(query_token or "")
    return hmac.compare_digest(expected, got)


def safe_static_path(web_root: Path, request_path: str) -> Path | None:
    """
    Resolve request_path under web_root. Rejects traversal and non-files.
    request_path is URL path without query (e.g. /app.js or /).
    """
    raw = (request_path or "/").split("?", 1)[0]
    if ".." in raw or "\\" in raw:
        return None
    rel = raw.lstrip("/")
    if not rel or rel.endswith("/"):
        rel = (rel + "index.html") if rel else "index.html"
    root = web_root.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate
