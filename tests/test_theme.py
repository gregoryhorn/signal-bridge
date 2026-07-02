from sb_ui import theme


def test_colors_match_legacy_literals():
    assert theme.COLORS["bg"] == "#0b0f14"
    assert theme.COLORS["bg_nav"] == "#0f1722"
    assert theme.COLORS["bg_panel"] == "#111821"
    assert theme.COLORS["bg_input"] == "#070b10"
    assert theme.COLORS["bg_editor"] == "#07111d"
    assert theme.COLORS["fg"] == "#d7dde5"
    assert theme.COLORS["fg_muted"] == "#8b98a8"
    assert theme.COLORS["fg_bright"] == "#ffffff"
    assert theme.COLORS["accent"] == "#1f6feb"
    assert theme.COLORS["accent_active"] == "#23405c"
    assert theme.COLORS["border"] == "#1f2f42"
    assert theme.COLORS["warning"] == "#facc15"
    assert theme.COLORS["success"] == "#7ee787"


def test_font_helper():
    assert theme.font() == ("Segoe UI", 10)
    assert theme.font(14, bold=True) == ("Segoe UI", 14, "bold")


def test_kwarg_helpers_return_fresh_dicts():
    a = theme.btn_primary_kw()
    b = theme.btn_primary_kw()
    assert a == b and a is not b
    assert a["bg"] == "#1f6feb" and a["relief"] == "flat"
    assert theme.btn_secondary_kw()["bg"] == "#111821"
    assert theme.label_kw()["fg"] == "#d7dde5"
    assert theme.label_kw(muted=True)["fg"] == "#8b98a8"
    assert theme.entry_kw()["insertbackground"] == "#ffffff"
    assert theme.check_kw()["selectcolor"] == "#111821"
    assert theme.radio_kw()["selectcolor"] == "#111821"
    assert theme.listbox_kw()["selectbackground"] == "#1f6feb"
    assert theme.text_kw()["bg"] == "#07111d"
    assert theme.optionmenu_kw()["bg"] == "#111821"


def test_extended_colors():
    assert theme.COLORS["error"] == "#ff8f8f"
    assert theme.COLORS["gold"] == "#f0c36a"
