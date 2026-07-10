"""Theme dict → CSS custom properties for the LAN viewer."""

from __future__ import annotations


def theme_to_css_variables(theme: dict) -> str:
    colors = (theme or {}).get("colors") or {}
    entities = (theme or {}).get("entities") or {}
    pairs = {
        "--bg": colors.get("bg_feed") or colors.get("bg") or "#0a0e14",
        "--bg-chrome": colors.get("bg_chrome") or "#0c121a",
        "--bg-surface": colors.get("bg_surface") or colors.get("bg_panel") or "#121a24",
        "--text": colors.get("fg") or "#e8eef6",
        "--text-secondary": colors.get("fg_secondary") or "#9aa8b8",
        "--text-muted": colors.get("fg_muted") or "#6b7a8c",
        "--accent": colors.get("accent") or "#3d9cf0",
        "--accent-line": colors.get("accent_line") or "#5ec8ff",
        "--border": colors.get("border") or "#243041",
        "--system": entities.get("system") or colors.get("entity_system") or "#f0d060",
        "--ship": entities.get("ship") or colors.get("entity_ship") or "#f0a060",
        "--pilot": entities.get("pilot") or colors.get("entity_pilot") or "#ff7b72",
        "--link": entities.get("link") or colors.get("entity_link") or "#79c0ff",
        "--clear": entities.get("clear") or colors.get("entity_clear") or "#7ee787",
        "--count": entities.get("count") or colors.get("entity_count") or "#c4b5fd",
        "--success": colors.get("success") or "#5ddea0",
    }
    lines = [":root {"]
    for k, v in pairs.items():
        lines.append(f"  {k}: {v};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def required_css_var_names() -> list[str]:
    return [
        "--bg",
        "--bg-chrome",
        "--text",
        "--text-muted",
        "--accent",
        "--system",
        "--ship",
        "--pilot",
        "--link",
    ]
