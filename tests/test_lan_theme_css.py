from sb_lan import required_css_var_names, theme_to_css_variables
from sb_ui import theme as sb_theme


def test_theme_export_css_vars():
    css = theme_to_css_variables(sb_theme.export_theme_dict())
    for name in required_css_var_names():
        assert name + ":" in css
