from pathlib import Path
import inspect

from scripts.capture_ui_review import REQUIRED_SURFACE_KEYS, REPO_ROOT, SURFACE_CASES, _capture_widget, required_surface_keys


def test_surface_registry_covers_every_planned_ui_surface():
    expected = {
        "main",
        "pilot-empty",
        "pilot-synced",
        "settings-general",
        "settings-channels",
        "settings-appearance",
        "settings-translation",
        "settings-translation-cache",
        "settings-filters",
        "settings-eve-catalog",
        "settings-aliases",
        "settings-esi",
        "settings-pilot-intel",
        "settings-lan-viewer",
        "settings-recognition-rules",
        "settings-add-ons",
        "settings-cache-data",
        "settings-diagnostics",
        "settings-about-support",
        "hidden-tabs",
        "channel-chooser",
        "font-chooser",
        "simple-prompt",
        "appearance-dialog",
        "esi-oauth",
        "recognition-rules",
        "help",
        "about",
        "lan-connected",
        "lan-disconnected",
    }

    assert REQUIRED_SURFACE_KEYS == expected
    assert required_surface_keys() == expected
    assert {case.key for case in SURFACE_CASES} == expected
    assert all(case.output_name.endswith(".png") for case in SURFACE_CASES)
    assert all(case.target_size[0] > 0 and case.target_size[1] > 0 for case in SURFACE_CASES)


def test_capture_script_declares_the_repository_root_for_direct_execution():
    assert REPO_ROOT == Path(__file__).resolve().parents[1]


def test_capture_harness_forces_opaque_windows_for_reliable_visual_review():
    source = inspect.getsource(_capture_widget)
    assert 'attributes("-alpha", 1.0)' in source
    assert 'attributes("-topmost", True)' in source
