import json

from sb_settings import SettingsStore

SCHEMA = {
    "font_size": (int, 10),
    "always_on_top": (bool, True),
    "font_family": (str, "Segoe UI"),
    "tab_order": (list, ["__all__"]),
    "chatlog_dir": (str, lambda: "computed-default"),
}


def make_store(tmp_path, name="settings.json"):
    return SettingsStore(tmp_path / name, SCHEMA)


def test_missing_file_returns_defaults(tmp_path):
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 10
    assert settings["chatlog_dir"] == "computed-default"
    assert store.warnings == []


def test_defaults_are_fresh_copies(tmp_path):
    store = make_store(tmp_path)
    a, b = store.defaults(), store.defaults()
    a["tab_order"].append("x")
    assert b["tab_order"] == ["__all__"]


def test_valid_values_load_and_unknown_keys_survive(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"font_size": 14, "future_key": {"a": 1}}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 14
    assert settings["future_key"] == {"a": 1}
    assert store.warnings == []


def test_wrong_type_is_coerced_with_warning(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"font_size": "12"}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 12
    assert any("font_size" in w for w in store.warnings)


def test_uncoercible_value_falls_back_to_default(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"font_size": "huge"}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 10
    assert any("font_size" in w for w in store.warnings)


def test_bool_int_confusion_is_flagged(tmp_path):
    (tmp_path / "settings.json").write_text(
        json.dumps({"always_on_top": 1, "font_size": True}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["always_on_top"] is True
    assert settings["font_size"] == 10
    assert len(store.warnings) >= 1


def test_corrupt_file_returns_defaults_and_logs(tmp_path):
    (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
    logged = []
    store = SettingsStore(tmp_path / "settings.json", SCHEMA, log=logged.append)
    settings = store.load()
    assert settings["font_size"] == 10
    assert logged


def test_save_roundtrip_and_failure_reporting(tmp_path):
    store = make_store(tmp_path)
    assert store.save({"font_size": 11}) is True
    assert json.loads((tmp_path / "settings.json").read_text(encoding="utf-8")) == {"font_size": 11}

    logged = []
    bad = SettingsStore(tmp_path / "no_dir_perms" / "\0bad" / "x.json", SCHEMA, log=logged.append)
    assert bad.save({"a": 1}) is False
    assert logged
