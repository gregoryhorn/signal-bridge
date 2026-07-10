"""Regression: common English noise is not ESI; capital ships stay ships."""

from signal_bridge_gui import (
    CATALOG,
    EveDb,
    Row,
    discover_ships_in_text,
    esi_message_candidates_for_row,
    extract_intel,
    is_probable_character_candidate,
    is_parser_noise,
)


def test_original_not_character_candidate():
    assert is_parser_noise("original") or "original" in __import__(
        "signal_bridge_gui", fromlist=["COMMON_ESI_NOISE"]
    ).COMMON_ESI_NOISE
    assert is_probable_character_candidate("original") is False
    assert is_probable_character_candidate("Original") is False
    assert is_probable_character_candidate("translation") is False


def test_original_not_in_esi_candidates():
    db = EveDb(__import__("signal_bridge_gui", fromlist=["DB_PATH"]).DB_PATH, use_sqlite=False)
    line = "the original ship was wrong"
    systems, assets, localized, counts, links, intent = extract_intel(line, db)
    row = Row(
        "Corp",
        "2026-01-01 12:00:00",
        "Tester",
        line,
        systems,
        assets,
        localized,
        counts,
        links,
        intent,
        "",
        "",
        "none",
        "x.log",
    )
    cands = [c.casefold() for c in esi_message_candidates_for_row(row)]
    assert "original" not in cands
    assert not any(c == "original" or c.startswith("original ") for c in cands)


def test_capital_ships_detected_as_assets():
    db = EveDb(__import__("signal_bridge_gui", fromlist=["DB_PATH"]).DB_PATH, use_sqlite=False)
    line = "Chimera Minokawa Erebus on gate"
    systems, assets, localized, counts, links, intent = extract_intel(line, db)
    asset_cf = {a.casefold() for a in assets}
    assert "chimera" in asset_cf
    assert "minokawa" in asset_cf
    assert "erebus" in asset_cf
    assert CATALOG.is_ship("Chimera")
    assert CATALOG.is_ship("Minokawa")
    assert CATALOG.is_ship("Erebus")
    # Ships must not become ESI candidates
    row = Row(
        "Corp",
        "2026-01-01 12:00:00",
        "Tester",
        line,
        systems,
        assets,
        localized,
        counts,
        links,
        intent,
        "",
        "",
        "none",
        "x.log",
    )
    cands = {c.casefold() for c in esi_message_candidates_for_row(row)}
    assert "chimera" not in cands
    assert "minokawa" not in cands
    assert "erebus" not in cands


def test_discover_ships_in_english_line():
    ships = {s.casefold() for s in discover_ships_in_text("fax Minokawa and Chimera with Erebus")}
    assert "minokawa" in ships
    assert "chimera" in ships
    assert "erebus" in ships
