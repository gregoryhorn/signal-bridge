from sb_lan import row_to_lan_payload


def test_row_to_lan_payload_spans():
    p = row_to_lan_payload(
        row_id="r1",
        channel="Corp",
        timestamp="21:04",
        sender="Elko",
        visible_text="WBR5-R clear Sabre",
        systems=["WBR5-R"],
        ships=["Sabre"],
        pilots=[],
    )
    assert p["channel"] == "Corp"
    assert p["visible_text"].startswith("WBR5")
    classes = {s["cls"] for s in p["spans"]}
    assert "system" in classes
    assert "ship" in classes
