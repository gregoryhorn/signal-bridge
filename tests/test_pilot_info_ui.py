"""Smoke: redesigned Pilot Info card builds without network."""

import tkinter as tk

import pytest

from sb_ui import pilot_info
from sb_ui.pilot import open_pilot_card


def test_term_kind_helpers():
    assert pilot_info.pilot_info_term_kind("nv") == "status"
    assert pilot_info.pilot_info_term_kind("cyno") == "signal"
    assert pilot_info.pilot_info_term_kind("Sabre") == "ship"
    assert pilot_info.normalized_ship_status({"ship_name": "nv"}) == ("Unknown", "No visual")


def test_zkill_priority_not_synced():
    pri, text, _ = pilot_info.zkill_priority({"status": "not_synced"}, "Sabre")
    assert pri == "NONE"
    assert "not synced" in text.lower()


def test_open_pilot_info_card_empty_profile(tk_root, monkeypatch):
    """Open compact empty pilot card and destroy it."""

    class FakeApp:
        def __init__(self):
            self.tk = tk
            self.root = tk_root
            self.messagebox = type("MB", (), {"showwarning": staticmethod(lambda *a, **k: None)})()
            self.diagnostics = {}

        def polish_window(self, win, parent=None, **kw):
            if kw.get("title"):
                win.title(kw["title"])
            if kw.get("width") and kw.get("height"):
                win.geometry(f"{kw['width']}x{kw['height']}")
            return win

        def friendly_datetime(self, v):
            return str(v or "unknown")

        def get_zkill_summary(self, pilot_id):
            return {"status": "not_synced"}

        def set_zkill_summary(self, pilot_id, summary):
            pass

        def start_zkill_sync(self, pilot_id, name, done):
            pass

        def intel_history_call(self, *a, **k):
            return None

        def copy_to_clipboard(self, text):
            pass

        def set_status(self, msg):
            pass

    profile = {
        "pilot": {
            "pilot_id": 2119654837,
            "name": "Buffering",
            "corp_name": "Chaos arbiter",
            "alliance_name": "Fraternity.",
            "first_seen": "",
            "last_seen": "",
        },
        "report_count": 0,
        "recent_sightings": [],
        "top_ships": [],
        "top_systems": [],
        "flags": [],
    }
    app = FakeApp()
    open_pilot_card(app, profile)
    # Find Toplevel children
    tops = [w for w in tk_root.winfo_children() if isinstance(w, tk.Toplevel)]
    assert tops, "Pilot Info window should open"
    win = tops[-1]
    assert "Buffering" in win.title()
    # Geometry should start compact-ish (width set at open)
    win.update_idletasks()
    assert win.winfo_width() <= 600 or int(win.geometry().split("x")[0]) <= 560
    footer = [child for child in win.winfo_children() if isinstance(child, tk.Frame) and child.pack_info().get("side") == "bottom"][0]
    labels = [child.cget("text") for child in footer.winfo_children() if isinstance(child, tk.Button)]
    assert "Sync zKill" in labels
    assert "More..." in labels
    assert "Activity" not in labels
    assert "Copy" not in labels
    win.destroy()
