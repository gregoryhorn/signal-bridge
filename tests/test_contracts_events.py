from sb_contracts.addon_event import row_to_addon_event
from sb_contracts.diagnostic_event import make_diagnostic_event
from sb_contracts.pilot_info_snapshot import empty_pilot_info_snapshot


def test_diagnostic_redacts_tokens():
    ev = make_diagnostic_event("oauth_test", access_token="abc", nested={"refresh_token": "xyz"})
    assert "abc" not in str(ev)
    assert "xyz" not in str(ev)
    assert ev["type"] == "oauth_test"
    assert "ts" in ev


def test_addon_event_row_shape():
    class R:
        received_at = "t"
        channel = "c"
        sender = "s"
        text = "Jita"
        systems = ["Jita"]
        assets = []
        ships = []
        links = []
        esi_entities = [{"entity_type": "character", "entity_id": 1, "name": "Pilot"}]

    ev = row_to_addon_event(R())
    assert ev["schema_version"] == 1
    assert ev["type"] == "intel_row"
    assert ev["characters"][0]["entity_id"] == 1


def test_pilot_snapshot_empty():
    snap = empty_pilot_info_snapshot("Pilot", 42)
    assert snap["schema_version"] == 1
    assert snap["pilot"]["pilot_id"] == 42
    assert snap["zkill"]["status"] == "not_synced"
