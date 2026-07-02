import sqlite3
import tkinter as tk

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
        "4-HWWF someone get shot?",
        "Morena Aresis loc ?",
        "T-GCGL \u00d1\u0081lr",
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


def test_put_machine_rejects_noop_auto_en_machine_translation(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")

    assert cache.put_machine("T-GCGL \u0441lr", "auto", "en", "T-GCGL \u0441lr", "google", direction="zh-en") is False

    assert cache_rows(cache) == []


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


def put_raw_machine(cache, source, translated, target="en", source_lang="auto", engine="google"):
    key = cache.key_for(source, source_lang, target, engine)
    cache.put(key, source, source_lang, target, translated, engine)
    return key


def test_cleanup_invalid_auto_en_rows_preserves_manual_overrides_and_en_zh(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "hello local is clear", "hello local is clear", target="en", source_lang="auto")
    put_raw_machine(cache, "\u043f\u0440\u0438\u0432\u0435\u0442 \u0432\u0440\u0430\u0433", "hello enemy", target="en", source_lang="auto")
    put_raw_machine(cache, "Caracal on gate", "\u72de\u737e\u5728\u95e8\u53e3", target="zh-CN", source_lang="en")
    manual_id = cache.save_override("hello local is clear", "manual correction", target_lang="en")

    assert cache.cleanup_invalid_auto_en_rows(False) == 1

    rows = cache.grouped_entries("", "", 20)
    sources = {(row["source_text"], row["target_lang"], row["winning_kind"]) for row in rows}
    assert ("\u043f\u0440\u0438\u0432\u0435\u0442 \u0432\u0440\u0430\u0433", "en", "cache") in sources
    assert ("Caracal on gate", "zh-CN", "cache") in sources
    assert ("hello local is clear", "en", "manual") in sources
    assert any(row.get("manual_id") == manual_id for row in rows)


def test_cleanup_invalid_auto_en_rows_removes_noop_machine_translation(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "T-GCGL \u0441lr", "T-GCGL \u0441lr", target="en", source_lang="auto")
    put_raw_machine(cache, "\u043f\u0440\u0438\u0432\u0435\u0442 \u0432\u0440\u0430\u0433", "hello enemy", target="en", source_lang="auto")

    assert cache.cleanup_invalid_auto_en_rows(False) == 1

    assert cache_rows(cache) == [("\u043f\u0440\u0438\u0432\u0435\u0442 \u0432\u0440\u0430\u0433", "auto", "en", "hello enemy", "google")]


def test_cleanup_invalid_auto_en_rows_preserves_noop_en_zh_machine_translation(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "T-GCGL \u0441lr", "T-GCGL \u0441lr", target="zh-CN", source_lang="en")

    assert cache.cleanup_invalid_auto_en_rows(False) == 0

    assert cache_rows(cache) == [("T-GCGL \u0441lr", "en", "zh-CN", "T-GCGL \u0441lr", "google")]


def test_cleanup_invalid_auto_en_rows_rejects_configured_protected_terms(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "\u5929\u9e64\u7ea7", "Crane", target="en", source_lang="auto")
    put_raw_machine(cache, "\u4ed6\u4eec\u6765\u4e86", "They are coming", target="en", source_lang="auto")

    assert cache.cleanup_invalid_auto_en_rows(False, protected_terms=["\u5929\u9e64\u7ea7"]) == 1

    rows = cache.grouped_entries("", "", 20)
    assert [row["source_text"] for row in rows] == ["\u4ed6\u4eec\u6765\u4e86"]


def test_settings_cache_cleanup_includes_cached_esi_pilot_names(tk_root, monkeypatch):
    captured = {}

    class FakeEsiCache:
        def list_entities(self, entity_type, limit=5000):
            assert entity_type == "character"
            assert limit == 2000
            return [{"name": "Mizz Betty"}]

    class FakeTranslationCache:
        def stats(self):
            return (0, 0)

        def override_count(self):
            return 0

        def grouped_entries(self, source_filter="", translated_filter="", limit=250):
            return []

        def cleanup_duplicate_machine_rows(self, dry_run):
            return 0

        def cleanup_invalid_auto_en_rows(self, dry_run, protected_terms=None):
            captured["protected_terms"] = list(protected_terms or [])
            return 0

        def cleanup_polluted_mixed_rows(self, dry_run):
            return 0

    original_action_button = sb.sb_components.action_button

    def capture_action_button(parent, text, command=None, **kwargs):
        button = original_action_button(parent, text, command, **kwargs)
        if text == "Clean cache issues":
            captured["clean_command"] = command
        return button

    monkeypatch.setattr(sb, "ESI_CACHE", FakeEsiCache())
    monkeypatch.setattr(sb, "TRANSLATION_CACHE", FakeTranslationCache())
    monkeypatch.setattr(sb.sb_components, "action_button", capture_action_button)

    app = type("SettingsOnlyApp", (), {})()
    app.tk = tk
    app.translation_cache_mode = tk.StringVar(master=tk_root, value="cache-first-auto")
    app.translation_fallback_mode = tk.StringVar(master=tk_root, value="online-only")
    app.translation_failure_cooldown_minutes = tk.IntVar(master=tk_root, value=60)
    app.set_status = lambda _text: None
    app.schedule_redraw = lambda _delay: None
    app.save_translation_engine_settings = lambda *_args: None
    app.show_translation_cache = lambda: None
    app.messagebox = type("MessageBox", (), {"askyesno": staticmethod(lambda *_args, **_kwargs: False)})

    sb.SignalBridgeGui._render_settings_translation_cache(app, tk_root, object())
    captured["clean_command"]()

    assert "Mizz Betty" in captured["protected_terms"]


def test_cleanup_polluted_mixed_rows_removes_old_mixed_source_rows(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "gate 4-HWWF red \u5929\u9e64\u7ea7 3", "Crane", target="en", source_lang="auto")
    put_raw_machine(cache, "\u5929\u9e64\u7ea7", "Crane", target="en", source_lang="auto")

    assert cache.cleanup_polluted_mixed_rows(False) == 1

    rows = cache.grouped_entries("", "", 20)
    assert [row["source_text"] for row in rows] == ["\u5929\u9e64\u7ea7"]


def test_cleanup_polluted_mixed_rows_preserves_en_zh_machine_rows(tmp_path):
    cache = sb.TranslationCache(tmp_path / "translation_cache.sqlite")
    put_raw_machine(cache, "gate 4-HWWF red \u5929\u9e64\u7ea7 3", "Crane", target="en", source_lang="auto")
    put_raw_machine(cache, "Caracal on gate \u5929\u9e64\u7ea7", "\u72de\u737e\u5728\u95e8\u53e3", target="zh-CN", source_lang="en")

    assert cache.cleanup_polluted_mixed_rows(False) == 1

    rows = cache_rows(cache)
    assert rows == [("Caracal on gate \u5929\u9e64\u7ea7", "en", "zh-CN", "\u72de\u737e\u5728\u95e8\u53e3", "google")]
