from sb_translation.protect import (
    reattach_untranslated_source_tokens,
    restore_protected_translation_tokens,
)


def test_restore_keeps_token_when_present():
    out = restore_protected_translation_tokens("Can it collapse? SBX0", [("SBX0", "Buffering")])
    assert out == "Can it collapse? Buffering"


def test_restore_appends_dropped_english_name():
    # Google dropped the placeholder entirely — classic mixed CJK + pilot line
    out = restore_protected_translation_tokens("Can it collapse?", [("SBX0", "Buffering")])
    assert "Can it collapse?" in out
    assert "Buffering" in out
    assert out.strip() == "Can it collapse? Buffering"


def test_restore_space_split_token():
    out = restore_protected_translation_tokens("hostile SBX 1 gate", [("SBX1", "Jita")])
    assert "Jita" in out
    assert "SBX" not in out.upper() or "Jita" in out


def test_restore_does_not_duplicate_existing_name():
    out = restore_protected_translation_tokens("Buffering is hostile", [("SBX0", "Buffering")])
    assert out.count("Buffering") == 1


def test_reattach_buffering_after_cjk_only_cache_hit():
    original = "\u80fd\u584c\u5417\uff1fBuffering"  # 能塌吗？Buffering
    extracted = "\u80fd\u584c\u5417"  # 能塌吗
    out = reattach_untranslated_source_tokens(original, "Can it collapse?", extracted)
    assert out == "Can it collapse? Buffering"


def test_reattach_skips_when_already_present():
    original = "\u80fd\u584c\u5417\uff1fBuffering"
    out = reattach_untranslated_source_tokens(original, "Can it collapse? Buffering", "\u80fd\u584c\u5417")
    assert out.count("Buffering") == 1
