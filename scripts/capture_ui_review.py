"""Capture named Signal Bridge UI surfaces for visual review on Windows.

The registry is deliberately data-first so tests can prove which product
surfaces require a screenshot without opening a desktop window.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class SurfaceCase:
    key: str
    output_name: str
    target_size: tuple[int, int]
    opener: str


_SETTINGS = (
    "general", "channels", "appearance", "translation", "translation-cache",
    "filters", "eve-catalog", "aliases", "esi", "pilot-intel", "lan-viewer",
    "recognition-rules", "add-ons", "cache-data", "diagnostics", "about-support",
)

REQUIRED_SURFACE_KEYS = {
    "main", "pilot-empty", "pilot-synced", *(f"settings-{name}" for name in _SETTINGS),
    "hidden-tabs", "channel-chooser", "font-chooser", "simple-prompt",
    "appearance-dialog", "esi-oauth", "recognition-rules", "help", "about",
    "lan-connected", "lan-disconnected",
}

SURFACE_CASES = tuple(
    SurfaceCase(key, f"{key}.png", size, opener)
    for key, size, opener in (
        ("main", (860, 620), "main"),
        ("pilot-empty", (480, 420), "pilot_empty"),
        ("pilot-synced", (520, 620), "pilot_synced"),
        *((f"settings-{name}", (860, 620), f"settings:{name}") for name in _SETTINGS),
        ("hidden-tabs", (360, 420), "hidden_tabs"),
        ("channel-chooser", (620, 600), "channel_chooser"),
        ("font-chooser", (420, 520), "font_chooser"),
        ("simple-prompt", (420, 160), "interactive"),
        ("appearance-dialog", (760, 620), "appearance"),
        ("esi-oauth", (560, 460), "esi"),
        ("recognition-rules", (760, 560), "recognition"),
        ("help", (860, 620), "help"),
        ("about", (540, 500), "about"),
        ("lan-connected", (390, 844), "web-only"),
        ("lan-disconnected", (390, 844), "web-only"),
    )
)


def required_surface_keys() -> set[str]:
    return set(REQUIRED_SURFACE_KEYS)


def _pilot_profile() -> dict:
    return {
        "pilot": {
            "pilot_id": 2119654837,
            "name": "Matek Bathana",
            "corp_name": "Some Corp",
            "alliance_name": "Some Alliance",
            "first_seen": "2026-07-10T10:50:00Z",
            "last_seen": "2026-07-10T12:42:00Z",
        },
        "report_count": 3,
        "recent_sightings": [
            {"timestamp": "2026-07-10T12:42:00Z", "system_name": "4-HWWF", "ship_name": "Sabre", "status": "No visual"},
            {"timestamp": "2026-07-10T11:01:00Z", "system_name": "Jita", "ship_name": "Unknown"},
            {"timestamp": "2026-07-10T10:50:00Z", "system_name": "4-HWWF", "ship_name": "Crow"},
        ],
        "top_ships": [{"name": "Sabre", "count": 2}],
        "top_systems": [{"name": "4-HWWF", "count": 3}],
        "flags": [{"label": "Watchlist", "source": "manual"}],
    }


def _top_window(app):
    import tkinter as tk

    tops = [widget for widget in app.root.winfo_children() if isinstance(widget, tk.Toplevel)]
    return tops[-1] if tops else app.root


def _open_case(app, case: SurfaceCase):
    if case.opener == "main":
        return app.root
    if case.opener == "pilot_empty":
        profile = _pilot_profile()
        profile["report_count"] = 0
        profile["recent_sightings"] = []
        profile["top_ships"] = []
        profile["top_systems"] = []
        profile["flags"] = []
        app.show_pilot_info_card(profile)
    elif case.opener == "pilot_synced":
        profile = _pilot_profile()
        app.set_zkill_summary(profile["pilot"]["pilot_id"], {"status": "synced", "recent_kills_30d": 12, "recent_losses_30d": 3, "isk_destroyed_30d": 1_200_000_000, "isk_lost_30d": 400_000_000, "recent_kills": [], "recent_losses": []})
        app.show_pilot_info_card(profile)
    elif case.opener.startswith("settings:"):
        title = case.opener.split(":", 1)[1].replace("-", " ").title()
        aliases = {"Eve Catalog": "EVE Catalog", "Esi": "ESI", "Lan Viewer": "LAN Viewer", "Add Ons": "Add-ons", "Cache Data": "Cache & Data", "About Support": "About / Support"}
        app.show_settings_center(aliases.get(title, title))
    elif case.opener == "hidden_tabs":
        app.hidden_tab_ids = {"Local"}
        app.tab_order = ["__all__", "Local"]
        app.active_channels.add("Local")
        app.restore_hidden_tabs_dialog()
    elif case.opener == "channel_chooser":
        app.choose_channels()
    elif case.opener == "font_chooser":
        app.choose_font()
    elif case.opener == "appearance":
        app.show_appearance_dialog()
    elif case.opener == "esi":
        app.show_esi_settings()
    elif case.opener == "recognition":
        app.show_esi_exclusion_list()
    elif case.opener == "help":
        app.show_help_center("Pilot Info")
    elif case.opener == "about":
        app.show_about_window()
    else:
        return None
    return _top_window(app)


def _capture_widget(widget, path: Path) -> None:
    from PIL import ImageGrab

    widget.deiconify()
    widget.lift()
    try:
        widget.attributes("-topmost", True)
        widget.attributes("-alpha", 1.0)
    except Exception:
        pass
    widget.update_idletasks()
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    width, height = widget.winfo_width(), widget.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True).save(path)


def capture(cases: list[SurfaceCase], output: Path) -> list[str]:
    from signal_bridge_gui import SignalBridgeGui

    output.mkdir(parents=True, exist_ok=True)
    app = SignalBridgeGui()
    results: list[str] = []
    try:
        for case in cases:
            widget = _open_case(app, case)
            if widget is None:
                results.append(f"SKIPPED {case.key}: requires interactive or web-only harness")
                continue
            try:
                _capture_widget(widget, output / case.output_name)
                results.append(f"CAPTURED {case.key}")
            except Exception as exc:
                results.append(f"SKIPPED {case.key}: {type(exc).__name__}: {exc}")
            finally:
                if widget is not app.root:
                    widget.destroy()
                    app.root.update_idletasks()
    finally:
        app.root.destroy()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="capture every desktop surface")
    parser.add_argument("--surface", action="append", default=[], help="capture one registry key")
    parser.add_argument("--output", type=Path, default=Path("docs/images/ui-review/before"))
    parser.add_argument("--list", action="store_true", help="list registry keys and exit")
    args = parser.parse_args(argv)
    by_key = {case.key: case for case in SURFACE_CASES}
    if args.list:
        print("\n".join(sorted(by_key)))
        return 0
    selected = list(SURFACE_CASES) if args.all else [by_key[key] for key in args.surface]
    if not selected:
        parser.error("choose --all or at least one --surface")
    for result in capture(selected, args.output):
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
