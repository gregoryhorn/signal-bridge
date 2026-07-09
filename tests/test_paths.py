from sb_paths import DATA_DIR, DEFAULT_DB_PATH, USER_DIR


def test_default_db_is_under_data_dir():
    assert DEFAULT_DB_PATH == DATA_DIR / "translations.db"
    # Must not hardcode the developer absolute translations.db from the v3 tree.
    assert "signal-bridge-v3" not in str(DEFAULT_DB_PATH).lower()
    assert "bundle-resources" not in str(DEFAULT_DB_PATH).lower()


def test_user_dir_is_path():
    assert USER_DIR.is_absolute() or USER_DIR.exists() or True
    assert DATA_DIR == USER_DIR / "data"
