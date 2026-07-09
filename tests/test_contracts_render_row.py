from sb_contracts.render_row import build_render_row


class FakeSeg:
    def __init__(self):
        self.kind = "message"
        self.text = "Jita Caracal"
        self.systems = ["Jita"]
        self.assets = ["Caracal"]
        self.pilots = []
        self.notes = []
        self.status = []
        self.confidence = "medium"


class FakeRow:
    channel = "Intel"
    received_at = "2026-07-10 12:00:00"
    sender = "Scout"
    text = "Jita Caracal"
    free_translation = "Jita Caracal"
    translation = "Jita Caracal"
    systems = ["Jita"]
    assets = ["Caracal"]
    links = []
    counts = []
    esi_entities = []
    segments = [FakeSeg()]
    translation_source = "catalog"
    file = "Intel_20260710_120000.txt"


def test_build_render_row_no_network_fields():
    rr = build_render_row(FakeRow(), translated_only=True, normalize=lambda s: s.strip())
    assert rr.channel == "Intel"
    assert rr.sender == "Scout"
    assert rr.visible_lines
    assert rr.original_line == "Jita Caracal"
    assert "Jita" in rr.entities.get("systems", [])
    assert rr.schema_version == 1
    assert isinstance(rr.row_id, str) and rr.row_id.startswith("r_")
