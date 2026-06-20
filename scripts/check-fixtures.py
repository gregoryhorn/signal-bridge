from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import signal_bridge_gui as sb  # noqa: E402


class V:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value


def make_app_stub():
    app = sb.SignalBridgeGui.__new__(sb.SignalBridgeGui)
    app.translated_only = V(False)
    app.translate_chinese_text = V(True)
    app.show_channel_names = V(False)
    app.show_channel_names_in_all = V(False)
    app.show_timestamps = V(False)
    app.visible_channel = "fixture"
    for name in [
        "display_free_translation",
        "localized_display_text",
        "row_display_parts",
        "segment_display_lines",
        "row_visible_body_lines",
        "row_uses_multiline_segments",
    ]:
        setattr(app, name, getattr(sb.SignalBridgeGui, name).__get__(app))
    return app


def build_case(app, db, case):
    text = case["text"]
    systems, assets, localized, counts, links, intent = sb.extract_intel(text, db)
    translation = sb.translate_text(text, localized, intent)
    segments = sb.build_intel_segments(text, systems, assets, localized, db)
    row = sb.Row(
        "fixture",
        "2026.06.20 00:00:00",
        case.get("sender", "Fixture"),
        text,
        systems,
        assets,
        localized,
        counts,
        links,
        intent,
        translation,
        "",
        "catalog/db" if translation or localized else "none",
        "fixture",
        [],
        [],
        segments,
    )
    parts = app.row_display_parts(row)
    return row, app.row_visible_body_lines(row, parts)


def main() -> int:
    fixture_path = ROOT / "tests" / "fixtures" / "feed_cases.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    app = make_app_stub()
    db = sb.EveDb(sb.DB_PATH, use_sqlite=False)
    failures = []
    try:
        for case in data["cases"]:
            row, display_lines = build_case(app, db, case)
            expected = case.get("expected", {})
            if "display_lines" in expected and display_lines != expected["display_lines"]:
                failures.append(f"{case['name']}: display_lines {display_lines!r} != {expected['display_lines']!r}")
            if "segment_count" in expected and len(row.segments) != expected["segment_count"]:
                failures.append(f"{case['name']}: segment_count {len(row.segments)} != {expected['segment_count']}")
            for system in expected.get("systems", []):
                if system not in row.systems:
                    failures.append(f"{case['name']}: missing system {system!r} in {row.systems!r}")
            for asset in expected.get("assets_contains", []):
                if asset not in row.assets:
                    failures.append(f"{case['name']}: missing asset {asset!r} in {row.assets!r}")
    finally:
        db.close()
    if failures:
        print("Fixture check FAILED")
        for failure in failures:
            print("-", failure)
        return 1
    print(f"Fixture check OK: {len(data['cases'])} case(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
