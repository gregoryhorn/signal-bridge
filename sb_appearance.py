"""Appearance defaults and normalization (no Tk)."""

from __future__ import annotations

import copy

DEFAULT_APPEARANCE = {
    "preset": "Default Dark",
    "font_family": "Segoe UI",
    "font_size": 10,
    "window_opacity": 1.0,
    "background": "#070b10",
    "foreground": "#d7dde5",
    "highlight_backgrounds": False,
    "highlight_modules": False,
    "time": {"foreground": "#778493", "bold": False, "background": ""},
    "sender": {"foreground": "#d7dde5", "bold": False, "background": ""},
    "system": {"foreground": "#ffd54a", "bold": True, "background": "#332900"},
    "asset": {"foreground": "#ff9d2e", "bold": True, "background": "#332000"},
    "module": {"foreground": "#b388ff", "bold": True, "background": "#241b35"},
    "ess": {"foreground": "#5ad7ff", "bold": True, "background": "#0b2a33"},
    "esi": {"foreground": "#ff5c5c", "bold": True, "background": "#351719"},
    "translation": {"foreground": "#9be28f", "bold": False, "background": ""},
    "muted": {"foreground": "#8b98a8", "bold": False, "background": ""},
    "error": {"foreground": "#ff5a5f", "bold": True, "background": ""},
    "link": {"foreground": "#5ad7ff", "bold": False, "background": "", "underline": True},
}

STYLE_TAGS = ("time", "sender", "system", "asset", "module", "ess", "esi", "translation", "muted", "error", "link")


def normalize_appearance(raw=None, *, settings: dict | None = None) -> dict:
    appearance = copy.deepcopy(DEFAULT_APPEARANCE)
    settings = settings or {}

    def merge(base, override):
        if not isinstance(override, dict):
            return base
        out = copy.deepcopy(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = merge(out[k], v)
            else:
                out[k] = v
        return out

    if isinstance(raw, dict):
        appearance = merge(appearance, raw)
    if "highlight_modules" not in (raw or {}):
        appearance["highlight_modules"] = False
    if "font_family" in settings and not (isinstance(raw, dict) and "font_family" in raw):
        appearance["font_family"] = settings.get("font_family", appearance["font_family"])
    try:
        appearance["font_size"] = max(8, min(28, int(appearance.get("font_size", 10))))
    except Exception:
        appearance["font_size"] = 10
    try:
        appearance["window_opacity"] = max(0.55, min(1.0, float(appearance.get("window_opacity", 1.0))))
    except Exception:
        appearance["window_opacity"] = 1.0
    for key in STYLE_TAGS:
        if not isinstance(appearance.get(key), dict):
            appearance[key] = copy.deepcopy(DEFAULT_APPEARANCE[key])
        else:
            base = copy.deepcopy(DEFAULT_APPEARANCE[key])
            base.update(appearance[key])
            appearance[key] = base
    appearance["highlight_modules"] = bool(appearance.get("highlight_modules", False))
    return appearance
