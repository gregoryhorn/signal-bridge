from sb_lan import required_css_var_names, theme_to_css_variables
from sb_ui import theme as sb_theme
from pathlib import Path


def test_theme_export_css_vars():
    css = theme_to_css_variables(sb_theme.export_theme_dict())
    for name in required_css_var_names():
        assert name + ":" in css


def test_lan_theme_link_does_not_request_a_protected_stylesheet_before_token_setup():
    index_html = (Path(__file__).resolve().parents[1] / "web_lan" / "index.html").read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="api/theme.css"' not in index_html
    assert 'data-theme-href="api/theme.css"' in index_html
