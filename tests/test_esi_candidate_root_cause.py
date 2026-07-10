"""Root-cause regressions for ESI message candidate over-matching.

Plain English chat words must not become character candidates. Real pilots
still match via handles, Title Case multi-word names, or pilot context words.
"""

from signal_bridge_gui import (
    DB_PATH,
    EveDb,
    Row,
    esi_message_candidates_for_row,
    extract_intel,
    is_probable_character_candidate,
)


def _row(line: str) -> Row:
    db = EveDb(DB_PATH, use_sqlite=False)
    systems, assets, localized, counts, links, intent = extract_intel(line, db)
    return Row(
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


def test_english_chat_words_not_candidates():
    words = [
        "check",
        "useless",
        "happy",
        "fight",
        "honestly",
        "surpised",
        "surprised",
        "people",
        "original",
        "fitting",
        "simulated",
    ]
    for w in words:
        assert is_probable_character_candidate(w) is False, w
        assert is_probable_character_candidate(w.capitalize()) is False, w


def test_english_phrase_not_candidates():
    line = "check useless happy fight honestly surpised"
    cands = [c.casefold() for c in esi_message_candidates_for_row(_row(line))]
    for bad in ("check", "useless", "happy", "fight", "honestly", "surpised", "surprised"):
        assert bad not in cands
        assert not any(bad == c or c.startswith(bad + " ") or c.endswith(" " + bad) for c in cands), (
            bad,
            cands,
        )


def test_handle_with_digits_still_candidate():
    assert is_probable_character_candidate("player123") is True
    line = "player123 on gate"
    cands = esi_message_candidates_for_row(_row(line))
    assert any("player123" in c for c in cands)


def test_title_case_multi_word_name_candidate():
    assert is_probable_character_candidate("Matek Bathana", "saw Matek Bathana", (4, 17)) is True
    line = "Matek Bathana jumped gate"
    cands = esi_message_candidates_for_row(_row(line))
    assert any("matek bathana" == c.casefold() for c in cands)


def test_plain_name_with_context_allowed():
    # Single plain token next to pilot-context word
    assert is_probable_character_candidate(
        "SomePilot",
        "SomePilot jumped",
        (0, 9),
    ) is True or is_probable_character_candidate(
        "SomePilot",
        "spotted SomePilot",
        (8, 17),
    )


def test_sender_plain_single_still_allowed_via_flag():
    assert is_probable_character_candidate("Buffering", allow_plain_single=True) is True
