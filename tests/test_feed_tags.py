from sb_ui.feed.text_tags import translated_subline_options
from sb_ui import theme


def test_translated_subline_uses_a_muted_indented_scan_edge():
    options = translated_subline_options()

    assert options["foreground"] == theme.COLORS["fg_secondary"]
    assert options["lmargin1"] == theme.SPACING["lg"]
    assert options["spacing1"] == theme.SPACING["xs"]
