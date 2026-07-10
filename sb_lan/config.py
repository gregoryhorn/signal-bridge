"""LAN viewer configuration (no Tk, no network bind)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass
class LanConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8765
    token: str = ""

    def with_token(self, token: str) -> "LanConfig":
        return LanConfig(enabled=self.enabled, host=self.host, port=self.port, token=token)


def new_token(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)


def config_from_settings(settings: dict) -> LanConfig:
    port = settings.get("lan_port", 8765)
    try:
        port = int(port)
    except Exception:
        port = 8765
    port = max(1, min(port, 65535))
    token = str(settings.get("lan_token") or "").strip()
    if not token:
        token = new_token()
    return LanConfig(
        enabled=bool(settings.get("lan_enabled", False)),
        host=str(settings.get("lan_host") or "0.0.0.0"),
        port=port,
        token=token,
    )


def config_to_settings_patch(config: LanConfig) -> dict:
    return {
        "lan_enabled": bool(config.enabled),
        "lan_port": int(config.port),
        "lan_token": str(config.token or ""),
        "lan_host": str(config.host or "0.0.0.0"),
    }
