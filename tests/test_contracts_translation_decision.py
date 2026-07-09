from sb_contracts.translation_decision import make_translation_decision, translation_decision_to_dict


def test_skipped_english_decision():
    d = make_translation_decision(
        decision="skipped",
        reason="english_only",
        engine="none",
        source_lang="en",
        target_lang="en",
    )
    out = translation_decision_to_dict(d)
    assert out["decision"] == "skipped"
    assert out["cache_hit"] is False
    assert out["schema_version"] == 1
