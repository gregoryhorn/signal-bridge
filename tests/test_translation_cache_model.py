import sqlite3

import signal_bridge_gui as sb


def test_auto_en_gate_rejects_english_links_counts_and_placeholders():
    rejected = [
        "hello local is clear",
        "https://example.test/intel",
        "www.example.test",
        "dscan.info/v/abc",
        "123",
        "12.5 isk",
        "SBX0 clear",
        "SBX1 SBX2",
    ]

    for source in rejected:
        assert sb.should_cache_translation_source(source, "zh-en", "en", "google") is False


def test_auto_en_gate_allows_non_english_natural_language():
    assert sb.should_cache_translation_source("\u043f\u0440\u0438\u0432\u0435\u0442 \u0432\u0440\u0430\u0433", "zh-en", "en", "google") is True
    assert sb.should_cache_translation_source("\u4ed6\u4eec\u6765\u4e86", "zh-en", "en", "google") is True


def test_auto_en_gate_rejects_protected_term_only_sources():
    protected_terms = ["\u5929\u9e64\u7ea7", "4-HWWF", "Caracal", "Picard X"]

    assert sb.should_cache_translation_source(
        "\u5929\u9e64\u7ea7", "zh-en", "en", "google", protected_terms=protected_terms
    ) is False
    assert sb.should_cache_translation_source(
        "4-HWWF", "zh-en", "en", "google", protected_terms=protected_terms
    ) is False
    assert sb.should_cache_translation_source(
        "Picard X", "zh-en", "en", "google", protected_terms=protected_terms
    ) is False


def test_auto_en_gate_allows_non_english_after_protected_terms_are_removed():
    protected_terms = ["4-HWWF", "\u5929\u9e64\u7ea7"]

    assert sb.should_cache_translation_source(
        "4-HWWF \u5929\u9e64\u7ea7 \u4ed6\u4eec\u6765\u4e86",
        "zh-en",
        "en",
        "google",
        protected_terms=protected_terms,
    ) is True


def test_en_zh_gate_allows_english_only_sources():
    assert sb.should_cache_translation_source("Caracal on gate", "en-zh", "zh-CN", "google") is True
    assert sb.should_cache_translation_source("Caracal on gate", "zh-en", "en", "google") is False


def test_auto_en_worker_does_not_persist_protected_term_only_source(tmp_path, monkeypatch):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    monkeypatch.setattr(sb, "TRANSLATION_CACHE", cache)
    monkeypatch.setattr(sb, "google_translate_free", lambda text, source, target: text)

    result, label = sb.translate_free_text_cached(
        "\u5929\u9e64\u7ea7",
        systems=["\u5929\u9e64\u7ea7"],
        assets=[],
        localized=[],
        counts=[],
        links=[],
        direction="zh-en",
        preferred_engine="google",
        fallback_mode="online-only",
    )

    con = sqlite3.connect(cache.path)
    row_count = con.execute("select count(*) from translation_cache").fetchone()[0]
    con.close()
    assert result == "\u5929\u9e64\u7ea7"
    assert label == "segment:google-uncached"
    assert row_count == 0


def make_cache(tmp_path, monkeypatch):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    monkeypatch.setattr(sb, "TRANSLATION_CACHE", cache)
    sb.FREE_TRANSLATION_CACHE.clear()
    return cache


def cache_rows(cache):
    con = sqlite3.connect(cache.path)
    rows = con.execute(
        "select source_text, source_lang, target_lang, translated_text, engine from translation_cache order by source_text"
    ).fetchall()
    con.close()
    return rows


def test_put_machine_owns_the_cache_write_gate(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")

    assert cache.put_machine(
        "hello local is clear", "auto", "en", "hello local is clear", "google", direction="zh-en"
    ) is False
    assert cache.put_machine(
        "\u4ed6\u4eec\u6765\u4e86", "auto", "en", "They are coming", "google", direction="zh-en"
    ) is True

    assert cache_rows(cache) == [("\u4ed6\u4eec\u6765\u4e86", "auto", "en", "They are coming", "google")]


def test_worker_does_not_persist_protected_term_only_auto_en_source(tmp_path, monkeypatch):
    cache = make_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(sb, "google_translate_free", lambda text, source="auto", target="en": "Crane")

    result, label = sb.translate_free_text_cached(
        "\u5929\u9e64\u7ea7",
        systems=[],
        assets=["\u5929\u9e64\u7ea7"],
        localized=[],
        counts=[],
        links=[],
        direction="zh-en",
        character_names=[],
        preferred_engine="google",
        fallback_mode="online-only",
    )

    assert result == "Crane"
    assert label == "segment:google-uncached"
    assert cache_rows(cache) == []


def test_worker_persists_non_english_auto_en_source_after_protected_terms(tmp_path, monkeypatch):
    cache = make_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(sb, "google_translate_free", lambda text, source="auto", target="en": "They are coming")

    result, label = sb.translate_free_text_cached(
        "4-HWWF \u5929\u9e64\u7ea7 \u4ed6\u4eec\u6765\u4e86",
        systems=["4-HWWF"],
        assets=["\u5929\u9e64\u7ea7"],
        localized=[],
        counts=[],
        links=[],
        direction="zh-en",
        character_names=[],
        preferred_engine="google",
        fallback_mode="online-only",
    )

    assert result == "They are coming"
    assert label == "segment:google-cached"
    assert cache_rows(cache) == [("\u5929\u9e64\u7ea7 \u4ed6\u4eec\u6765\u4e86", "auto", "en", "They are coming", "google")]


def test_worker_persists_english_only_source_for_explicit_en_zh(tmp_path, monkeypatch):
    cache = make_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(sb, "google_translate_free", lambda text, source="en", target="zh-CN": "\u72de\u737e\u5728\u95e8\u53e3")

    result, label = sb.translate_free_text_cached(
        "Caracal on gate",
        systems=[],
        assets=[],
        localized=[],
        counts=[],
        links=[],
        direction="en-zh",
        character_names=[],
        preferred_engine="google",
        fallback_mode="online-only",
    )

    assert result == "\u72de\u737e\u5728\u95e8\u53e3"
    assert label == "segment:google-cached"
    assert cache_rows(cache) == [("Caracal on gate", "en", "zh-CN", "\u72de\u737e\u5728\u95e8\u53e3", "google")]
