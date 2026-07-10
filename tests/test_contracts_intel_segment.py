from sb_contracts.intel_segment import IntelSegment, intel_segment_from_legacy, intel_segment_to_dict


def test_segment_defaults_and_dict():
    seg = IntelSegment(kind="kill", text="Akai Basilisk", systems=[], assets=["Basilisk"], pilots=["Akai"])
    d = intel_segment_to_dict(seg)
    assert d["kind"] == "kill"
    assert d["assets"] == ["Basilisk"]
    assert d["confidence"] == "medium"
    assert d["schema_version"] == 1


def test_from_legacy_duck_type():
    class Legacy:
        kind = "sighting"
        text = "Jita nv"
        systems = ["Jita"]
        assets = []
        pilots = []
        notes = ["VOICE"]
        status = ["NV"]
        confidence = "high"

    seg = intel_segment_from_legacy(Legacy())
    assert seg.kind == "sighting"
    assert seg.status == ["NV"]
