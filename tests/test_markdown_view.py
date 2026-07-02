from sb_ui.markdown_view import parse_markdown


def tags_of(segments):
    return [t for _text, t in segments]


def test_heading_levels():
    segs = parse_markdown("# One\n## Two\n### Three")
    assert segs[0] == ("One\n", "h1")
    assert segs[1] == ("Two\n", "h2")
    assert segs[2] == ("Three\n", "h3")


def test_plain_paragraph_is_body():
    segs = parse_markdown("Just a line of text")
    assert segs == [("Just a line of text", "body"), ("\n", "body")]


def test_bold_inline():
    segs = parse_markdown("before **strong** after")
    assert ("strong", "bold") in segs
    assert ("before ", "body") in segs
    assert (" after", "body") in segs


def test_inline_code():
    segs = parse_markdown("use `pytest -q` here")
    assert ("pytest -q", "code") in segs


def test_bare_url_is_link():
    segs = parse_markdown("see https://example.com/page for more")
    assert ("https://example.com/page", "link") in segs


def test_bullet_line():
    segs = parse_markdown("- first item")
    assert segs[0][1] == "bullet"
    assert ("first item", "body") in segs


def test_blank_line_kept():
    segs = parse_markdown("a\n\nb")
    assert ("\n", "body") in segs


def test_unsupported_markdown_passes_through_as_text():
    segs = parse_markdown("| col1 | col2 |")
    assert segs[0] == ("| col1 | col2 |", "body")


def test_bullet_glyph_is_single_bullet_char():
    segs = parse_markdown("- x")
    assert segs[0][0] == "  • ", "bullet glyph must be U+2022, not mojibake"
