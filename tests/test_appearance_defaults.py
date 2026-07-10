from sb_appearance import DEFAULT_APPEARANCE, normalize_appearance


def test_default_modules_highlight_off():
    assert DEFAULT_APPEARANCE.get("highlight_modules") is False
    app = normalize_appearance(None)
    assert app["highlight_modules"] is False


def test_missing_key_defaults_false():
    app = normalize_appearance({"font_size": 12})
    assert app["highlight_modules"] is False
    app2 = normalize_appearance({"highlight_modules": True})
    assert app2["highlight_modules"] is True
