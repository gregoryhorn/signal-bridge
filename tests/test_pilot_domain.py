from sb_pilot import (
    FLAG_KINDS,
    PilotRef,
    empty_profile_for_ref,
    flag_label,
    resolve_from_entity,
    resolve_pilot_target,
    sort_flags,
    zkill_priority,
)


def test_flag_label_and_sort():
    assert flag_label("high threat") == "High Threat"
    flags = sort_flags(
        [
            {"label": "Watchlist", "active": 1},
            {"label": "High Threat", "active": 1},
            {"label": "Do Not Track", "active": 0},
        ]
    )
    assert flags[0]["label"] == "High Threat"
    assert {n for n, _i in FLAG_KINDS} >= {"Watchlist", "High Threat"}


def test_resolve_pilot_target_exact():
    ents = [
        {"entity_id": 1, "name": "Alpha", "entity_type": "character"},
        {"entity_id": 2, "name": "Buffering", "entity_type": "character"},
    ]
    ref = resolve_pilot_target("Buffering", ents)
    assert ref is not None
    assert ref.entity_id == 2
    assert ref.name == "Buffering"


def test_resolve_from_entity_and_empty_profile():
    ref = resolve_from_entity({"entity_id": 99, "name": "Test Pilot", "corporation_name": "Corp"})
    assert isinstance(ref, PilotRef)
    prof = empty_profile_for_ref(ref)
    assert prof["pilot"]["pilot_id"] == 99
    assert prof["report_count"] == 0


def test_zkill_priority_none():
    pri, text, _ = zkill_priority({"status": "not_synced"}, "Sabre")
    assert pri == "NONE"
