from pathlib import Path

from sb_lan import LanConfig, check_token, safe_static_path


def test_check_token():
    cfg = LanConfig(token="secret-token")
    assert check_token(cfg, "secret-token") is True
    assert check_token(cfg, "wrong") is False
    assert check_token(cfg, None) is False
    assert check_token(LanConfig(token=""), "x") is False


def test_safe_static_path(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("ok", encoding="utf-8")
    assert safe_static_path(tmp_path, "/").name == "index.html"
    assert safe_static_path(tmp_path, "/app.js").name == "app.js"
    assert safe_static_path(tmp_path, "/../etc/passwd") is None
    assert safe_static_path(tmp_path, "/nope.js") is None
