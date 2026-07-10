"""Smoke: each Settings Center page renderer builds without raising."""

from __future__ import annotations

import tkinter as tk

import pytest

import signal_bridge_gui as gui


def _noop_polish(win, parent=None, **kw):
    if kw.get("title"):
        win.title(kw["title"])
    if kw.get("width") and kw.get("height"):
        win.geometry(f"{kw['width']}x{kw['height']}")
    return win


@pytest.fixture
def app(tk_root):
    """Minimal SignalBridgeGui without starting monitor threads if possible."""
    # SignalBridgeGui always builds full UI; reuse root if construction allows.
    # Construction may be heavy; skip if display issues.
    try:
        # Avoid double mainloop: build instance but use existing root carefully.
        # SignalBridgeGui creates its own Tk — so we only test pure page methods
        # with a lightweight stub shell.
        class StubShell:
            def __init__(self, body):
                self.body = body
                self._status = ""
                self._apply = None

            def set_status(self, msg):
                self._status = msg

            def set_apply_handler(self, fn):
                self._apply = fn

            def render_page(self, name):
                self._status = f"goto:{name}"

        yield StubShell
    except Exception as exc:
        pytest.skip(f"settings smoke unavailable: {exc}")


def test_all_settings_page_renderers_run(tk_root, app):
    """Instantiate GUI once and visit every Settings page renderer."""
    # Building full GUI needs its own Tk; SignalBridgeGui creates root in __init__.
    # Use a lightweight fake that only provides methods each renderer needs.
    pytest.importorskip("tkinter")

    created = []

    class FakeGui:
        def __init__(self):
            self.tk = tk
            self.root = tk_root
            self.messagebox = type("MB", (), {"showwarning": staticmethod(lambda *a, **k: None), "showinfo": staticmethod(lambda *a, **k: None), "askyesno": staticmethod(lambda *a, **k: False)})()
            self.filedialog = None
            self.always_on_top = tk.BooleanVar(master=tk_root, value=True)
            self.compact = tk.BooleanVar(master=tk_root, value=True)
            self.check_updates_on_start = tk.BooleanVar(master=tk_root, value=False)
            self.show_timestamps = tk.BooleanVar(master=tk_root, value=True)
            self.show_channel_names = tk.BooleanVar(master=tk_root, value=False)
            self.show_channel_names_in_all = tk.BooleanVar(master=tk_root, value=True)
            self.enable_hyperlinks = tk.BooleanVar(master=tk_root, value=True)
            self.translated_only = tk.BooleanVar(master=tk_root, value=True)
            self.translate_chinese_text = tk.BooleanVar(master=tk_root, value=True)
            self.translation_direction = tk.StringVar(master=tk_root, value="zh-en")
            self.translation_preferred_engine = tk.StringVar(master=tk_root, value="auto")
            self.translation_fallback_mode = tk.StringVar(master=tk_root, value="online-only")
            self.translation_cache_mode = tk.StringVar(master=tk_root, value="cache-first-auto")
            self.translation_failure_cooldown_minutes = tk.IntVar(master=tk_root, value=60)
            self.argos_status_text = tk.StringVar(master=tk_root, value="Argos status: not checked")
            self.esi_enabled = tk.BooleanVar(master=tk_root, value=False)
            self.esi_oauth_enabled = tk.BooleanVar(master=tk_root, value=False)
            self.font_family = tk.StringVar(master=tk_root, value="Segoe UI")
            self.font_size = tk.IntVar(master=tk_root, value=10)
            self.appearance = {"preset": "Default Dark", "window_opacity": 1.0, "highlight_modules": False}
            self.active_channels = set()
            self.hidden_tab_ids = set()
            self.visible_channel = gui.ALL_CHANNELS_TAB
            self.replay_on_start_var = tk.BooleanVar(master=tk_root, value=False)
            self.backlog_minutes_var = tk.IntVar(master=tk_root, value=10)

        def apply_topmost(self, *_a, **_k):
            pass

        def persist_settings(self, *_a, **_k):
            pass

        def persist_and_redraw(self, *_a, **_k):
            pass

        def persist_and_schedule_redraw(self, *_a, **_k):
            pass

        def save_esi_ui_settings(self, *_a, **_k):
            pass

        def save_translation_engine_settings(self, *_a, **_k):
            pass

        def choose_chatlog_folder(self):
            pass

        def open_app_folder(self):
            pass

        def open_logs_folder(self):
            pass

        def choose_channels(self):
            pass

        def restore_hidden_tabs_dialog(self):
            pass

        def refresh_channel_status(self):
            pass

        def close_selected_channels(self):
            pass

        def show_appearance_dialog(self):
            pass

        def adjust_font_size(self, _d):
            pass

        def check_catalog_updates(self):
            pass

        def restore_previous_catalog(self):
            pass

        def show_health(self):
            pass

        def show_esi_settings(self):
            pass

        def manual_esi_check_dialog(self):
            pass

        def show_esi_diagnostics(self):
            pass

        def clear_esi_cache(self):
            pass

        def show_esi_exclusion_list(self):
            pass

        def clear_translation_cache(self):
            pass

        def copy_diagnostics(self):
            pass

        def show_about_window(self):
            pass

        def show_help_center(self):
            pass

        def refresh_argos_status(self):
            pass

        def install_argos_models(self):
            pass

        def test_translation_engine(self):
            pass

        def show_translation_cache(self):
            pass

        def open_phrase_overrides(self):
            pass

        def channel_catalog(self):
            return {}

        def settings_summary_text(self):
            return "summary"

        def simple_prompt(self, title, prompt):
            return ""

        def _feed_filters(self):
            return []

        def _spam_limiter(self):
            from sb_spam import SpamLimiter
            return SpamLimiter()

        def intel_history_status(self):
            return {"installed": False, "enabled": False, "manifest": {}}

        def intel_history_status_label(self):
            return "disabled"

        def current_intel_history_health(self):
            return {}

        def set_intel_history_enabled(self, _v):
            pass

        def install_intel_history_addon_from_file(self):
            pass

        def show_intel_history_details(self):
            pass

        def open_intel_history_data_folder(self):
            pass

        def uninstall_intel_history_addon_code(self):
            pass

        def polish_window(self, *a, **k):
            return _noop_polish(*a, **k)

        def set_status(self, msg):
            pass

        def redraw_feed(self):
            pass

        def schedule_redraw(self, *_a, **_k):
            pass

        # Bind real methods from SignalBridgeGui that are pure UI builders
        _render_settings_general = gui.SignalBridgeGui._render_settings_general
        _render_settings_channels = gui.SignalBridgeGui._render_settings_channels
        _render_settings_appearance = gui.SignalBridgeGui._render_settings_appearance
        _render_settings_catalog = gui.SignalBridgeGui._render_settings_catalog
        _render_settings_esi = gui.SignalBridgeGui._render_settings_esi
        _render_settings_exclusions = gui.SignalBridgeGui._render_settings_exclusions
        _render_settings_cache_data = gui.SignalBridgeGui._render_settings_cache_data
        _render_settings_diagnostics = gui.SignalBridgeGui._render_settings_diagnostics
        _render_settings_about = gui.SignalBridgeGui._render_settings_about
        _render_settings_translation = gui.SignalBridgeGui._render_settings_translation
        _render_settings_filters = gui.SignalBridgeGui._render_settings_filters
        _render_settings_aliases = gui.SignalBridgeGui._render_settings_aliases
        _render_settings_addons = gui.SignalBridgeGui._render_settings_addons
        # Translation cache page is large; still smoke it
        _render_settings_translation_cache = gui.SignalBridgeGui._render_settings_translation_cache

    g = FakeGui()
    pages = [
        ("General", g._render_settings_general),
        ("Channels", g._render_settings_channels),
        ("Appearance", g._render_settings_appearance),
        ("Translation", g._render_settings_translation),
        ("Filters", g._render_settings_filters),
        ("EVE Catalog", g._render_settings_catalog),
        ("ESI", g._render_settings_esi),
        ("Recognition Rules", g._render_settings_exclusions),
        ("Cache & Data", g._render_settings_cache_data),
        ("Diagnostics", g._render_settings_diagnostics),
        ("About / Support", g._render_settings_about),
        ("Aliases", g._render_settings_aliases),
        ("Add-ons", g._render_settings_addons),
        ("Translation Cache", g._render_settings_translation_cache),
    ]
    for name, renderer in pages:
        body = tk.Frame(tk_root)
        shell = app(body)
        # Bound methods: self is already FakeGui
        renderer(body, shell)
        created.append(name)
        body.destroy()
    assert len(created) == 14
    assert "Recognition Rules" in created
