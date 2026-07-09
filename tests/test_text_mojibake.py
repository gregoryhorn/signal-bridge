from pathlib import Path

from sb_text import strip_term_punctuation, truncate_label


def test_strip_curly_quotes():
    assert strip_term_punctuation("\u201cCaracal\u201d") == "Caracal"
    assert strip_term_punctuation("  Basilisk  ") == "Basilisk"


def test_truncate_ellipsis():
    out = truncate_label("abcdefghijklmnopqrstuvwxyz0123456789", 10)
    assert out.endswith("\u2026")
    assert len(out) == 10


def test_no_double_encoded_marker_in_new_modules():
    for path in [
        Path("sb_text.py"),
        Path("sb_paths.py"),
        Path("sb_channels.py"),
        Path("sb_monitor.py"),
        Path("sb_filters.py"),
        Path("sb_spam.py"),
        Path("sb_highlight.py"),
        Path("sb_appearance.py"),
    ]:
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text
        assert "â€" not in text
