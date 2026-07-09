"""Google free translate edge (network, timeout)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

DEFAULT_TIMEOUT = 2.5


def google_translate_free(
    text: str,
    source: str = "zh-CN",
    target: str = "en",
    *,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = "Mozilla/5.0 SignalBridge/1.0",
) -> str | None:
    if not text or not str(text).strip():
        return None
    params = urllib.parse.urlencode(
        {"client": "gtx", "sl": source or "auto", "tl": target, "dt": "t", "q": text}
    )
    url = "https://translate.googleapis.com/translate_a/single?" + params
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
        data = json.loads(raw)
        parts = []
        for chunk in data[0] or []:
            if chunk and chunk[0]:
                parts.append(str(chunk[0]))
        out = "".join(parts).strip()
        return out or None
    except Exception:
        return None
