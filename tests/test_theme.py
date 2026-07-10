import json

from sb_ui import theme


def test_void_tactical_surface_tokens():
    assert theme.THEME_NAME == "void_tactical"
    assert theme.COLORS["bg"] == "#070a0f"
    assert theme.COLORS["bg_chrome"] == "#0c121a"
    assert theme.COLORS["bg_nav"] == "#0c121a"
    assert theme.COLORS["bg_panel"] == "#121a24"
    assert theme.COLORS["bg_feed"] == "#0a0e14"
    assert theme.COLORS["bg_input"] == "#070b10"
    assert theme.COLORS["bg_editor"] == "#0a0e14"


def test_void_tactical_accent_and_text():
    assert theme.COLORS["fg"] == "#e8eef6"
    assert theme.COLORS["fg_muted"] == "#6b7a8c"
    assert theme.COLORS["fg_secondary"] == "#9aa8b8"
    assert theme.COLORS["fg_bright"] == "#ffffff"
    assert theme.COLORS["accent"] == "#3d9cf0"
    assert theme.COLORS["accent_line"] == "#5ec8ff"
    assert theme.COLORS["accent_active"] == "#1a2838"
    assert theme.COLORS["border"] == "#243041"
    assert theme.COLORS["success"] == "#5ddea0"
    assert theme.COLORS["warning"] == "#e8c547"
    assert theme.COLORS["error"] == "#f07178"


def test_entity_colors():
    assert theme.COLORS["entity_system"] == "#f0d060"
    assert theme.COLORS["entity_ship"] == "#f0a060"
    assert theme.COLORS["entity_pilot"] == "#ff7b72"
    assert theme.COLORS["entity_link"] == "#79c0ff"
    assert theme.COLORS["entity_clear"] == "#7ee787"
    assert theme.COLORS["gold"] == "#f0d060"


def test_spacing_scale():
    assert theme.SPACING == {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


def test_font_helper():
    assert theme.font() == ("Segoe UI", 10)
    assert theme.font(14, bold=True) == ("Segoe UI", 14, "bold")
    assert theme.mono_font(9) == ("Consolas", 9)


def test_kwarg_helpers_return_fresh_dicts():
    a = theme.btn_primary_kw()
    b = theme.btn_primary_kw()
    assert a == b and a is not b
    assert a["bg"] == theme.COLORS["accent"] and a["relief"] == "flat"
    assert theme.btn_secondary_kw()["bg"] == theme.COLORS["bg_panel"]
    assert theme.label_kw()["fg"] == theme.COLORS["fg"]
    assert theme.label_kw(muted=True)["fg"] == theme.COLORS["fg_muted"]
    assert theme.entry_kw()["insertbackground"] == theme.COLORS["fg_bright"]
    assert theme.check_kw()["selectcolor"] == theme.COLORS["bg_panel"]
    assert theme.listbox_kw()["selectbackground"] == theme.COLORS["accent"]
    assert theme.text_kw()["bg"] == theme.COLORS["bg_editor"]


def test_export_theme_dict_json_serializable():
    payload = theme.export_theme_dict()
    raw = json.dumps(payload)
    assert "void_tactical" in raw
    assert payload["entities"]["system"] == "#f0d060"
    assert "system" in theme.feed_tag_styles()


def test_apply_ttk_styles_configures_dark_treeview(tk_root):
    from tkinter import ttk
    theme.apply_ttk_styles(tk_root)
    style = ttk.Style(tk_root)
    assert style.configure("SB.Treeview")["background"] == theme.COLORS["bg_input"]
    assert style.configure("SB.Treeview.Heading")["background"] == theme.COLORS["bg_panel"]
    theme.apply_ttk_styles(tk_root)
