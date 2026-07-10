import json
import urllib.error
import urllib.request

from sb_lan import FeedBuffer, LanConfig, LanServer, new_token
from sb_ui import theme as sb_theme


def test_lan_server_snapshot_requires_token(tmp_path):
    # use real web_lan if present
    server = LanServer()
    token = new_token()
    cfg = LanConfig(enabled=True, host="127.0.0.1", port=18765, token=token)
    buf = FeedBuffer()
    buf.append({"id": "1", "visible_text": "hello", "channel": "Corp", "spans": []})
    url = server.start(cfg, buffer=buf, theme=sb_theme.export_theme_dict())
    assert "token=" in url
    try:
        # wrong token
        try:
            urllib.request.urlopen(f"http://127.0.0.1:18765/api/snapshot?token=bad", timeout=2)
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401
        # good token
        with urllib.request.urlopen(
            f"http://127.0.0.1:18765/api/snapshot?token={token}", timeout=2
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["rows"][0]["visible_text"] == "hello"
        with urllib.request.urlopen(
            f"http://127.0.0.1:18765/api/theme.css?token={token}", timeout=2
        ) as resp:
            css = resp.read().decode("utf-8")
        assert "--system:" in css
    finally:
        server.stop()
