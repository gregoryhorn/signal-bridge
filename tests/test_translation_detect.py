from sb_translation.detect import has_non_english_signal, pick_google_source_lang


def test_russian_is_non_english_signal():
    assert has_non_english_signal("враг в системе")
    assert not has_non_english_signal("hostile in system")


def test_pick_source_lang():
    assert pick_google_source_lang("天鹤级", "zh-en") == "zh-CN"
    assert pick_google_source_lang("враг", "zh-en") == "auto"
    assert pick_google_source_lang("hello", "en-zh") == "en"
