"""Application and user data paths (portable-safe, no Tk)."""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
USER_DIR = (
    Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
CONFIG_DIR = USER_DIR / "config"
CACHE_DIR = USER_DIR / "cache"
MODEL_DIR = USER_DIR / "models" / "argos"
LOG_DIR = USER_DIR / "logs"
LOG_PATH = LOG_DIR / "signal_bridge.log"
EVENT_LOG_PATH = LOG_DIR / "events.jsonl"
ERROR_LOG_PATH = LOG_DIR / "errors.jsonl"
STALL_LOG_PATH = LOG_DIR / "stalls.jsonl"
JOB_LOG_PATH = LOG_DIR / "jobs.jsonl"
CONFIG_PATH = CONFIG_DIR / "settings.json"
DATA_DIR = USER_DIR / "data"
MODULES_DIR = USER_DIR / "modules"
MODULE_DATA_DIR = USER_DIR / "user_data" / "modules"

# Optional local SQLite translations DB. Live path prefers the compact catalog.
DEFAULT_DB_PATH = DATA_DIR / "translations.db"

CATALOG_PATH = DATA_DIR / "eve_catalog.json"
CATALOG_MANIFEST_PATH = DATA_DIR / "catalog_manifest.json"
CATALOG_PREVIOUS_PATH = DATA_DIR / "eve_catalog.previous.json"
PHRASE_OVERRIDES_PATH = DATA_DIR / "phrase_overrides.json"
USER_ALIASES_PATH = DATA_DIR / "user_aliases.json"
DEFAULT_EXCLUSIONS_PATH = DATA_DIR / "default_exclusions.json"
DEFAULT_RECOGNITION_RULES_PATH = DATA_DIR / "default_recognition_rules.json"
DEFAULT_ESI_ENTITIES_PATH = DATA_DIR / "default_esi_entities.json"
TRANSLATION_CACHE_PATH = CACHE_DIR / "translation_cache.sqlite"
ZKILL_CACHE_PATH = CACHE_DIR / "zkill_cache.json"
ESI_CONFIG_PATH = CONFIG_DIR / "esi_settings.json"
ESI_TOKENS_PATH = CONFIG_DIR / "esi_tokens.json"
ESI_CACHE_PATH = CACHE_DIR / "esi_cache.sqlite"


def ensure_app_dirs() -> None:
    for path in (CONFIG_DIR, CACHE_DIR, MODEL_DIR, LOG_DIR, DATA_DIR, MODULES_DIR, MODULE_DATA_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
