import json
import re
from pathlib import Path

from sb_ui import theme


def test_semantic_color_contract_is_exported_for_desktop_and_lan():
    required = {
        "focus", "disabled", "info", "success", "warning", "error",
        "threat_high", "threat_medium", "system", "ship", "pilot", "link", "count",
    }

    assert required <= set(theme.SEMANTIC_COLORS)
    assert all(theme.semantic_color(role).startswith("#") for role in required)

    exported = theme.export_theme_dict()
    assert required <= set(exported["semantic"])
    json.dumps(exported)


def test_shared_ui_modules_do_not_embed_hex_literals():
    root = Path(__file__).resolve().parents[1]
    for relative in ("sb_ui/components.py", "sb_ui/markdown_view.py"):
        source = (root / relative).read_text(encoding="utf-8")
        assert not re.search(r"#[0-9a-fA-F]{3,8}\\b", source)
