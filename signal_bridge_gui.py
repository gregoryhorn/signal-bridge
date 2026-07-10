from __future__ import annotations
import argparse
import base64
import json
import os
import copy
import hashlib
import importlib.util
import queue
import re
import shutil
import secrets
import sqlite3
import sys
import threading
import time
import traceback
import tempfile
import webbrowser
import http.server
import socketserver
import urllib.parse
import urllib.request
import urllib.error
import zipfile
from dataclasses import dataclass, field
import signal_bridge_render_model as render_model
from sb_settings import SettingsStore
import sb_help
import sb_zkill
from sb_paths import (
    APP_DIR,
    CACHE_DIR,
    CATALOG_MANIFEST_PATH,
    CATALOG_PATH,
    CATALOG_PREVIOUS_PATH,
    CONFIG_DIR,
    CONFIG_PATH,
    DATA_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_ESI_ENTITIES_PATH,
    DEFAULT_EXCLUSIONS_PATH,
    DEFAULT_RECOGNITION_RULES_PATH,
    ERROR_LOG_PATH,
    ESI_CACHE_PATH,
    ESI_CONFIG_PATH,
    ESI_TOKENS_PATH,
    EVENT_LOG_PATH,
    JOB_LOG_PATH,
    LOG_DIR,
    LOG_PATH,
    MODEL_DIR,
    MODULE_DATA_DIR,
    MODULES_DIR,
    PHRASE_OVERRIDES_PATH,
    STALL_LOG_PATH,
    TRANSLATION_CACHE_PATH,
    USER_ALIASES_PATH,
    USER_DIR,
    ZKILL_CACHE_PATH,
    ensure_app_dirs,
)
from sb_diagnostics import (
    install_exception_logging,
    record_error,
    record_event,
    write_jsonl,
    write_log,
)
import sb_channels
from sb_filters import FeedFilter, filters_to_settings, normalize_filters
from sb_spam import SpamLimiter, SpamPolicy
from sb_feed_admit import should_admit_row
from sb_ui import components as sb_components
from sb_ui import markdown_view as sb_markdown
from sb_ui import theme as sb_theme
from sb_ui import windows as sb_windows
from sb_ui.feed import apply_base_feed_colors, default_feed_background, default_feed_foreground, translated_subline_options
from sb_ui.settings_center import SettingsShell
from sb_ui.shell import build_header_bar, build_main_layout, menu_colors
from sb_ui.tabs import TabStrip
import sb_tabs
from sb_tabs import TabStripState
import sb_lan
from pathlib import Path
from typing import Callable

APP_NAME = "Signal Bridge"
APP_VERSION = "0.7"
UPDATE_API_URL = "https://api.github.com/repos/gregoryhorn/signal-bridge/releases/latest"
UPDATE_RELEASE_URL = "https://github.com/gregoryhorn/signal-bridge/releases/latest"
GITHUB_REPO_URL = "https://github.com/gregoryhorn/signal-bridge"
ISSUE_REPORT_URL = "https://github.com/gregoryhorn/signal-bridge/issues"
DONATION_TEXT = "If you like this app and want further development, donate me some ISK in game | Mizz Betty"
ALL_CHANNELS_TAB = "__ALL_CHANNELS__"
INTEL_HISTORY_ADDON_ID = "intel-history"
INTEL_HISTORY_ADDON_NAME = "Intel History / Pilot Intelligence"
POLL_SECONDS = 1.0
MAX_CHUNK = 1024 * 1024
MAX_ROWS = 600
REDRAW_ATOMIC_ROW_LIMIT = 220  # render normal live feeds in one Tk update to avoid visible half-redraw flashes
REDRAW_BATCH_SIZE = 25
GOOGLE_TRANSLATE_TIMEOUT = 2.5
FREE_TRANSLATION_CACHE: dict[str, str] = {}
ARGOS_STATUS_CACHE = {"checked": False, "runtime": False, "models": set(), "error": ""}
ESI_DEFAULT_CLIENT_ID = "6d57a179c8764b3aa95cc956f7ad7050"
ESI_CALLBACK_URL = "http://localhost:8080/callback"
ESI_CALLBACK_HOST = "127.0.0.1"
ESI_CALLBACK_PORT = 8080
ESI_POSITIVE_TTL_SECONDS = 30 * 24 * 60 * 60
ESI_NEGATIVE_TTL_SECONDS = 90 * 24 * 60 * 60
ESI_USER_AGENT = f"SignalBridge/{APP_VERSION} contact: github.com/gregoryhorn/signal-bridge"
ESI_SEARCH_URL = "https://esi.evetech.net/latest/universe/ids/"
ESI_SSO_AUTHORIZE_URL = "https://login.eveonline.com/v2/oauth/authorize/"
ESI_SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
ESI_SSO_VERIFY_URL = "https://login.eveonline.com/oauth/verify"
CATALOG_MANIFEST_URL = "https://github.com/gregoryhorn/signal-bridge/releases/download/v0.2/catalog_manifest.json"


def candidate_chatlog_dirs() -> list[Path]:
    home = Path.home()
    return [
        home / "Documents" / "EVE" / "logs" / "Chatlogs",
        home / "OneDrive" / "Documents" / "EVE" / "logs" / "Chatlogs",
    ]


def detect_chatlog_dir() -> Path:
    for path in candidate_chatlog_dirs():
        if path.exists():
            return path
    return candidate_chatlog_dirs()[0]


def _settings_log(message: str) -> None:
    # write_log is defined later in the module; the first load_settings() call
    # happens at import time before it exists, so resolve it lazily.
    logger = globals().get("write_log")
    if logger:
        logger(message)


SETTINGS_SCHEMA = {
    "chatlog_dir": (str, lambda: str(detect_chatlog_dir())),
    "db_path": (str, lambda: str(DEFAULT_DB_PATH if DEFAULT_DB_PATH.exists() else DATA_DIR / "translations.db")),
    "active_channels": (list, []),
    "always_on_top": (bool, True),
    "translated_only": (bool, True),
    "translate_free_text": (bool, True),
    "translation_direction": (str, "zh-en"),
    "translation_preferred_engine": (str, "auto"),
    "translation_fallback_mode": (str, "online-only"),
    "translation_cache_mode": (str, "cache-first-auto"),
    "translation_failure_cooldown_minutes": (int, 60),
    "compact_mode": (bool, True),
    "font_family": (str, "Segoe UI"),
    "font_size": (int, 10),
    "show_timestamps": (bool, True),
    "show_channel_names": (bool, False),
    "show_channel_names_in_all": (bool, True),
    "enable_hyperlinks": (bool, True),
    "active_tab_id": (str, ALL_CHANNELS_TAB),
    "tab_order": (list, [ALL_CHANNELS_TAB]),
    "hidden_tab_ids": (list, []),
    "auto_open_new_channels": (bool, True),
    "auto_switch_to_new_channel": (bool, False),
    "max_tab_rows": (int, 3),
    "check_updates_on_start": (bool, True),
    "addons": (dict, {INTEL_HISTORY_ADDON_ID: {"enabled": True}}),
    "esi_entity_recognition": (bool, True),
    "esi_oauth_enabled": (bool, False),
    "replay_on_start": (bool, False),
    "backlog_minutes": (int, 10),
    "feed_filters": (list, []),
    "spam_control_enabled": (bool, True),
    "spam_local_channels_only": (bool, True),
    "spam_per_channel_max_per_minute": (int, 30),
    "spam_repeat_sender_window_seconds": (int, 8),
    "spam_repeat_sender_max": (int, 3),
    "spam_ascii_art_filter": (bool, True),
    "lan_enabled": (bool, False),
    "lan_port": (int, 8765),
    "lan_token": (str, ""),
    "lan_host": (str, "0.0.0.0"),
}

MAIN_SETTINGS_STORE = SettingsStore(CONFIG_PATH, SETTINGS_SCHEMA, log=_settings_log)


def load_settings() -> dict:
    return MAIN_SETTINGS_STORE.load()


def save_settings(settings: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not MAIN_SETTINGS_STORE.save(settings):
        _settings_log(f"Settings save failed: {CONFIG_PATH}")


def addon_code_dir(addon_id: str) -> Path:
    return MODULES_DIR / addon_id


def addon_data_dir(addon_id: str) -> Path:
    return MODULE_DATA_DIR / addon_id


def load_addon_manifest(addon_id: str) -> dict | None:
    manifest = addon_code_dir(addon_id) / "module.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as exc:
        write_log(f"Add-on manifest load failed for {addon_id}", exc)
        return None


def installed_addon_status(addon_id: str = INTEL_HISTORY_ADDON_ID) -> dict:
    manifest = load_addon_manifest(addon_id)
    addon_settings = (SETTINGS.get("addons") or {}).get(addon_id) or {}
    data_dir = addon_data_dir(addon_id)
    return {
        "id": addon_id,
        "installed": bool(manifest),
        "enabled": bool(addon_settings.get("enabled", False)) and bool(manifest),
        "manifest": manifest or {},
        "code_dir": str(addon_code_dir(addon_id)),
        "data_dir": str(data_dir),
        "data_exists": data_dir.exists(),
    }


def set_addon_enabled(addon_id: str, enabled: bool) -> None:
    addons = SETTINGS.setdefault("addons", {})
    current = dict(addons.get(addon_id) or {})
    current["enabled"] = bool(enabled)
    current["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    addons[addon_id] = current
    save_settings(SETTINGS)


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    dest_resolved = dest.resolve()
    for member in zf.infolist():
        name = member.filename.replace("\\", "/")
        if not name or name.endswith("/"):
            continue
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError(f"Unsafe add-on path: {member.filename}")
        target = (dest / name).resolve()
        if dest_resolved not in target.parents and target != dest_resolved:
            raise ValueError(f"Unsafe add-on target: {member.filename}")
    zf.extractall(dest)


def _find_manifest_root(extracted: Path) -> tuple[Path, dict]:
    candidates = list(extracted.rglob("module.json"))
    if not candidates:
        raise ValueError("Add-on package does not contain module.json")
    candidates.sort(key=lambda p: (len(p.relative_to(extracted).parts), str(p)))
    manifest_path = candidates[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("module.json is not a JSON object")
    return manifest_path.parent, manifest


def install_intel_history_addon_zip(zip_path: Path) -> dict:
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(str(zip_path))
    MODULES_DIR.mkdir(parents=True, exist_ok=True)
    MODULE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="signalbridge-addon-") as tmp:
        tmpdir = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            _safe_extract_zip(zf, tmpdir)
        root, manifest = _find_manifest_root(tmpdir)
        addon_id = str(manifest.get("id") or "").strip()
        if addon_id != INTEL_HISTORY_ADDON_ID:
            raise ValueError(f"Unsupported add-on id: {addon_id or 'missing'}")
        target = addon_code_dir(addon_id)
        backup = target.with_suffix(".backup")
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.rename(backup)
        try:
            shutil.copytree(root, target)
            addon_data_dir(addon_id).mkdir(parents=True, exist_ok=True)
            return manifest
        except Exception:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            if backup.exists():
                backup.rename(target)
            raise
        finally:
            if backup.exists():
                shutil.rmtree(backup, ignore_errors=True)


SETTINGS = load_settings()
if SETTINGS.get("font_family") == "Consolas":
    SETTINGS["font_family"] = "Segoe UI"
    save_settings(SETTINGS)
CHATLOG_DIR = Path(SETTINGS.get("chatlog_dir") or detect_chatlog_dir())
DB_PATH = Path(SETTINGS.get("db_path") or DEFAULT_DB_PATH)
DEFAULT_CHANNELS: set[str] = set(SETTINGS.get("active_channels") or [])

class AddonRuntime:
    """Guarded runtime wrapper for the official Intel History add-on."""
    def __init__(self, addon_id: str, manifest: dict, code_dir: Path, data_dir: Path):
        self.addon_id = addon_id
        self.manifest = manifest
        self.code_dir = code_dir
        self.data_dir = data_dir
        self.instance = None
        self.enabled = False
        self.last_error = ""

    def start(self):
        entry = str(self.manifest.get("entry") or "intel_history.py").strip()
        entry_path = (self.code_dir / entry).resolve()
        root = self.code_dir.resolve()
        if root not in entry_path.parents and entry_path != root:
            raise ValueError(f"Unsafe add-on entry path: {entry}")
        if not entry_path.exists():
            raise FileNotFoundError(str(entry_path))
        module_name = f"signalbridge_addon_{self.addon_id.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load add-on entry: {entry_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        context = {"addon_id": self.addon_id, "manifest": self.manifest, "module_dir": str(self.code_dir), "data_dir": str(self.data_dir), "app_version": APP_VERSION}
        init = getattr(module, "init", None)
        self.instance = init(context) if callable(init) else module
        start = getattr(self.instance, "start", None)
        if callable(start):
            start()
        self.enabled = True

    def safe_call(self, method: str, *args, **kwargs):
        if not self.enabled or self.instance is None:
            return None
        func = getattr(self.instance, method, None)
        if not callable(func):
            return None
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self.last_error = f"{method}: {type(exc).__name__}: {exc}"
            write_log(f"Add-on {self.addon_id} hook failed: {method}", exc)
            return None

    def shutdown(self):
        try:
            self.safe_call("shutdown")
        finally:
            self.enabled = False
            self.instance = None

    def health(self) -> dict:
        data = self.safe_call("get_health_status") or {}
        if not isinstance(data, dict):
            data = {}
        if self.last_error and data.get("last_error") in (None, "", "none"):
            data["last_error"] = self.last_error
        return data


def make_intel_history_event(row) -> dict:
    from sb_contracts.addon_event import row_to_addon_event
    return row_to_addon_event(row)


ensure_app_dirs()

LIVE_INLINE = re.compile(r"^\[\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s*\]\s*(.+?)\s*(?:>|:)\s*(.+)$", re.I)
HEADER_CHANNEL = re.compile(r"^Channel Name:\s*(.+)$", re.I)
SYSTEM_RE = re.compile(r"\b[A-Z0-9]{1,6}-[A-Z0-9]{1,4}\b")
LINK_RE = re.compile(r"https?://\S+|www\.\S+|dscan\.info/\S+", re.I)
HTTP_LINK_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.I)
COUNT_RE = re.compile(r"(?<![A-Za-z0-9-])(?:\+?\d+|\d+\+|x\d+|\d+x|\d+(?:\.\d+)?\s*(?:km|m|b|bil|mil|kk|isk))\b", re.I)
NUMERIC_TOKEN_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")

def is_numeric_or_decimal_token(term: str) -> bool:
    """Return True for plain numeric/security/range tokens that must never be systems."""
    from sb_text import strip_term_punctuation
    value = strip_term_punctuation(term)
    if not value:
        return False
    return bool(NUMERIC_TOKEN_RE.fullmatch(value))

PAREN_RE = re.compile(r"\(([^)]+)\)")
HEADER_KEYS = ("Channel ID:", "Channel Name:", "Listener:", "Session started:")

BUILTIN_ASSETS = {
    "Hound", "Sabre", "Loki", "Flycatcher", "Caracal", "Keres", "Thorax", "Capsule", "Bombers", "Bomber", "No visual", "ESS", "Bubble",
    "Cyno", "Dictor", "Dread", "Tornado", "Purifier", "Stiletto", "Hecate", "Rook", "Heretic", "Svipul", "Naga", "Minmatar Shuttle",
    "Shuttle", "Stabber Fleet Issue", "Crucifier", "Bifrost", "Stabber", "Manticore", "Scalpel", "Cynabal", "Retribution", "Vedmak",
    "Vagabond", "Proteus", "Machariel", "Typhoon", "Kikimora", "Raptor", "Condor", "Garmur", "Cormorant", "Kirin", "Redeemer",
    "Osprey Navy Issue", "Caracal Navy Issue", "Skyhook",
}

CLEAR = re.compile(r"\b(clear|clr|safe|blue only)\b", re.I)
MOVE = re.compile(r"\b(jump|jumped|jumping|gate|warp|undock|dock|moving|status|leaving|going|cyno|beacon)\b", re.I)
HOSTILE = re.compile(r"\b(hostile|neut|neutral|red|tackle|camp|gang|fleet|goons?|bombers?|hound squad|bubble|ess theft|intrusion|refugee)\b", re.I)
HOSTILE_DISPLAY_TERMS = {"refugee"}

@dataclass
class IntelSegment:
    kind: str
    text: str
    systems: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    pilots: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    confidence: str = "medium"


@dataclass
class Row:
    channel: str
    received_at: str
    sender: str
    text: str
    systems: list[str]
    assets: list[str]
    localized: list[dict]
    counts: list[str]
    links: list[str]
    intent: str
    translation: str
    free_translation: str
    translation_source: str
    file: str
    esi_entities: list[dict] = field(default_factory=list)
    esi_candidates: list[str] = field(default_factory=list)
    segments: list[IntelSegment] = field(default_factory=list)


def unique(seq):
    out = []
    seen = set()
    for x in seq:
        if not x:
            continue
        key = str(x).lower()
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def clean(line: str) -> str:
    s = line.strip().lstrip("\ufeff\ufffd?\x00").strip()
    if "[ " in s and not s.startswith("["):
        s = s[s.find("["):]
    return s



def pilot_info_term_kind(value: str) -> str:
    """Classify compact pilot-card terms without changing stored intel rows."""
    key = str(value or "").strip().casefold()
    if not key or key == "-":
        return "empty"
    if key in {"nv", "no visual", "novisual", "no-visual"}:
        return "status"
    if key in {"cyno", "beacon", "ess", "bubble"}:
        return "signal"
    return "ship"


def is_pilot_status_term(value: str) -> bool:
    return pilot_info_term_kind(value) == "status"


def is_pilot_signal_term(value: str) -> bool:
    return pilot_info_term_kind(value) == "signal"

def normalize_feed_text(text: str) -> str:
    """Display-only cleanup for common intel shorthand/noisy punctuation.

    Raw chat text remains stored unchanged; this only affects visible feed and
    copy-visible text to reduce common shorthand/noise.
    """
    s = str(text or "")
    s = re.sub(r"\bclr\b", "clear", s, flags=re.I)
    s = re.sub(r"[()*]", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s


def is_header(line: str) -> bool:
    s = clean(line)
    return (not s) or (set(s) <= {"-"} and len(s) > 8) or any(s.startswith(k) for k in HEADER_KEYS)


def channel_from_filename(path: Path) -> str:
    return sb_channels.channel_from_filename(path)


def channel_sort_key(name: str) -> str:
    return sb_channels.channel_sort_key(name)


def normalize_channel_name(name: str) -> str:
    return sb_channels.normalize_channel_name(name)


def discover_channel_metadata(limit_files: int = 500) -> dict[str, dict]:
    return sb_channels.discover_channel_metadata(CHATLOG_DIR, limit_files)


def discover_channels(limit_files: int = 500) -> list[str]:
    return sb_channels.discover_channels(CHATLOG_DIR, limit_files)


def default_channels() -> set[str]:
    return sb_channels.default_channels(CHATLOG_DIR, DEFAULT_CHANNELS or None)


def decode_bytes(data: bytes) -> str:
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16le", "replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16be", "replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", "replace")
    if data.count(b"\x00") > max(2, len(data) // 20):
        return data.decode("utf-16le", "replace")
    return data.decode("utf-8", "replace")


def word_boundary(term: str) -> str:
    return rf"(?<![\w-]){re.escape(term)}(?:\*|\b|(?=\s|$|[),.:;!?]))"


def candidate_terms(text: str) -> list[str]:
    terms: list[str] = []
    for m in PAREN_RE.finditer(text):
        terms.append(m.group(1))
    # Handles true Chinese and the live log's localization text representation.
    for m in re.finditer(r"[^\s,;:()\[\]{}]+(?:级|舰队型|海军型|ž‹|型|€)?\*?", text):
        terms.append(m.group(0))
    # Chinese ship/version names often appear as several localized tokens inside
    # one mixed intel line. Add explicit CJK ship chunks so catalog lookup can
    # resolve each token independently instead of only testing the whole phrase.
    cjk_ship_chunk = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]+?级(?:舰队型|海军型)?|[\u3400-\u9fff\uf900-\ufaff]+?(?:舰队型|海军型)")
    for m in cjk_ship_chunk.finditer(text):
        chunk = m.group(0)
        terms.append(chunk)
        base = re.sub(r"(?:舰队型|海军型)$", "", chunk)
        if base and base != chunk:
            terms.append(base)
    folded_text = text.casefold()
    if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", text):
        for alias in CJK_SHIP_ALIAS_TERMS:
            if alias and alias.casefold() in folded_text:
                terms.append(alias)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text)
    for n in (4, 3, 2, 1):
        for i in range(0, max(0, len(words) - n + 1)):
            terms.append(" ".join(words[i:i+n]))
    from sb_text import strip_term_punctuation
    return unique([strip_term_punctuation(t) for t in terms])



class EveCatalog:
    def __init__(self, path: Path = CATALOG_PATH):
        self.path = path
        self.manifest_path = CATALOG_MANIFEST_PATH
        self.version = "none"
        self.source = "none"
        self.systems: dict[str, str] = {}
        self.types: dict[str, str] = {}
        self.aliases: dict[str, str] = {}
        self.market_groups: dict[str, str] = {}
        self.ship_names: dict[str, str] = {}
        self.alias_kinds: dict[str, str] = {}
        self.loaded = False
        self.load()

    def load(self):
        self.systems.clear(); self.types.clear(); self.aliases.clear(); self.market_groups.clear(); self.ship_names.clear(); self.alias_kinds.clear()
        self.loaded = False; self.version = "none"; self.source = "none"
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.version = str(data.get("catalog_version") or "unknown")
            self.source = str(data.get("source") or "catalog")
            self.systems = {str(k).casefold(): str(v) for k, v in dict(data.get("systems") or {}).items()}
            self.types = {str(k).casefold(): str(v) for k, v in dict(data.get("types") or {}).items()}
            self.aliases = {str(k).casefold(): str(v) for k, v in dict(data.get("aliases") or {}).items()}
            self.market_groups = {str(k).casefold(): str(v) for k, v in dict(data.get("market_groups") or {}).items()}
            self.ship_names = {str(k).casefold(): str(v) for k, v in dict(data.get("ship_names") or {}).items()}
            self.alias_kinds = {str(k).casefold(): str(v) for k, v in dict(data.get("alias_kinds") or {}).items()}
            self.loaded = True
        except Exception as exc:
            write_log("Catalog load failed", exc)

    def counts(self) -> dict:
        return {"systems": len(self.systems), "types": len(self.types), "aliases": len(self.aliases), "market_groups": len(self.market_groups), "ship_names": len(self.ship_names)}

    def lookup_type(self, term: str) -> str | None:
        from sb_text import strip_term_punctuation
        key = strip_term_punctuation(term).casefold()
        if not key or len(key) < 2:
            return None
        return self.types.get(key) or self.aliases.get(key) or self.market_groups.get(key)

    def lookup_system(self, term: str) -> str | None:
        if is_numeric_or_decimal_token(term):
            return None
        return self.systems.get(term.strip().casefold())

    def is_ship(self, term: str) -> bool:
        from sb_text import strip_term_punctuation
        key = strip_term_punctuation(term).casefold()
        canonical = self.lookup_type(term) or term
        return key in self.ship_names or canonical.casefold() in self.ship_names or self.alias_kinds.get(key) == "ship"



def default_user_aliases() -> list[dict]:
    """Small starter aliases for common intel shorthand/translation artifacts."""
    return [
        {"alias": "Enyu", "canonical": "Enyo", "kind": "ship", "enabled": True, "note": "Common typo/transliteration"},
        {"alias": "Enyu Class", "canonical": "Enyo", "kind": "ship", "enabled": True, "note": "Common typo/transliteration"},
        {"alias": "Enyou", "canonical": "Enyo", "kind": "ship", "enabled": True, "note": "Common typo/transliteration"},
        {"alias": "Enyou Class", "canonical": "Enyo", "kind": "ship", "enabled": True, "note": "Common typo/transliteration"},
        {"alias": "Apocalypse Navy", "canonical": "Apocalypse Navy Issue", "kind": "ship", "enabled": True, "note": "Common intel shorthand"},
        {"alias": "Prophet Class", "canonical": "Prophecy", "kind": "ship", "enabled": True, "note": "Machine translation often says Prophet Class"},
        {"alias": "Stork Class", "canonical": "Stork", "kind": "ship", "enabled": True, "note": "Class suffix shorthand"},
        {"alias": "Widmark-class", "canonical": "Widow", "kind": "ship", "enabled": True, "note": "Machine translation / OCR artifact"},
        {"alias": "Widmark Class", "canonical": "Widow", "kind": "ship", "enabled": True, "note": "Machine translation / OCR artifact"},
        {"alias": "Widmark", "canonical": "Widow", "kind": "ship", "enabled": True, "note": "Machine translation / OCR artifact"},
        {"alias": "Assassin-class", "canonical": "Assassin", "kind": "ship", "enabled": True, "note": "Class suffix shorthand"},
        {"alias": "Assassin Class", "canonical": "Assassin", "kind": "ship", "enabled": True, "note": "Class suffix shorthand"},
        {"alias": "Ocato-class", "canonical": "Osprey Navy Issue", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Ocato Class", "canonical": "Osprey Navy Issue", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Ocato", "canonical": "Osprey Navy Issue", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Black Crow-class", "canonical": "Blackbird", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Black Crow Class", "canonical": "Blackbird", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Black Crow", "canonical": "Blackbird", "kind": "ship", "enabled": True, "note": "Machine translation artifact; editable in Settings > Aliases"},
        {"alias": "Stabber-class", "canonical": "Stabber", "kind": "ship", "enabled": True, "note": "Class suffix shorthand"},
        {"alias": "Stabber Class", "canonical": "Stabber", "kind": "ship", "enabled": True, "note": "Class suffix shorthand"},
    ]


def normalize_user_alias_entry(entry: dict) -> dict | None:
    alias = str((entry or {}).get("alias") or "").strip()
    canonical = str((entry or {}).get("canonical") or "").strip()
    kind = str((entry or {}).get("kind") or "ship").strip().lower()
    if kind not in {"ship", "system"}:
        kind = "ship"
    if not alias or not canonical:
        return None
    return {
        "alias": alias,
        "canonical": canonical,
        "kind": kind,
        "enabled": bool((entry or {}).get("enabled", True)),
        "note": str((entry or {}).get("note") or "").strip(),
    }


def load_user_aliases() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    aliases: list[dict] = []
    if USER_ALIASES_PATH.exists():
        try:
            data = json.loads(USER_ALIASES_PATH.read_text(encoding="utf-8"))
            raw = data.get("aliases") if isinstance(data, dict) else data
            for entry in raw or []:
                norm = normalize_user_alias_entry(entry)
                if norm:
                    aliases.append(norm)
        except Exception as exc:
            write_log("User alias load failed", exc)
    # Seed defaults without overwriting existing user choices.
    seen = {a["alias"].casefold() for a in aliases}
    changed = False
    for entry in default_user_aliases():
        if entry["alias"].casefold() not in seen:
            aliases.append(dict(entry)); seen.add(entry["alias"].casefold()); changed = True
    if changed or not USER_ALIASES_PATH.exists():
        save_user_aliases(aliases)
    return aliases


def save_user_aliases(aliases: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_aliases = []
    seen = set()
    for entry in aliases or []:
        norm = normalize_user_alias_entry(entry)
        if not norm:
            continue
        key = (norm["kind"], norm["alias"].casefold())
        if key in seen:
            continue
        seen.add(key); clean_aliases.append(norm)
    USER_ALIASES_PATH.write_text(json.dumps({"version": 1, "aliases": clean_aliases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_user_aliases_to_catalog(catalog: EveCatalog, aliases: list[dict]) -> None:
    for entry in aliases or []:
        if not entry.get("enabled", True):
            continue
        alias = str(entry.get("alias") or "").strip()
        canonical = str(entry.get("canonical") or "").strip()
        kind = str(entry.get("kind") or "ship").lower()
        if not alias or not canonical:
            continue
        key = alias.casefold()
        if kind == "system":
            if is_numeric_or_decimal_token(alias) or is_numeric_or_decimal_token(canonical):
                continue
            catalog.systems[key] = canonical
        else:
            catalog.aliases[key] = canonical
            catalog.alias_kinds[key] = "ship"
            if isinstance(catalog.ship_names, dict):
                catalog.ship_names.setdefault(canonical.casefold(), canonical)
            elif hasattr(catalog.ship_names, "add"):
                catalog.ship_names.add(canonical.casefold())


ALIAS_RULE_VERSION = 0
ALIAS_REPLACEMENT_RULES: list[tuple[str, str, re.Pattern]] = []
CJK_SHIP_ALIAS_TERMS: list[str] = []


def rebuild_cjk_ship_alias_terms() -> None:
    """Precompute official/user CJK ship aliases for fast row tokenization.

    The compact catalog has hundreds of thousands of aliases, so live parsing
    must not scan it directly per row.  This list is rebuilt only after catalog
    and alias reloads, then candidate_terms() does cheap substring checks over
    known ship aliases only.
    """
    global CJK_SHIP_ALIAS_TERMS
    terms: set[str] = set()
    cjk_re = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
    try:
        for alias, canonical in getattr(CATALOG, "aliases", {}).items():
            alias_s = str(alias or "").strip()
            if len(alias_s) < 2 or not cjk_re.search(alias_s):
                continue
            canon_s = str(canonical or "").strip()
            if getattr(CATALOG, "alias_kinds", {}).get(alias_s.casefold()) == "ship" or CATALOG.is_ship(canon_s):
                terms.add(alias_s)
        for alias_s, canonical_s in globals().get("MANUAL_TYPE_ALIASES", {}).items():
            alias_s = str(alias_s or "").strip()
            if len(alias_s) >= 2 and cjk_re.search(alias_s):
                terms.add(alias_s.casefold())
    except Exception as exc:
        write_log("CJK ship alias index rebuild failed", exc)
    CJK_SHIP_ALIAS_TERMS = sorted(terms, key=len, reverse=True)


def rebuild_alias_replacement_rules() -> None:
    """Precompute display alias rules so feed redraw stays cheap.

    Important: this must use only user/manual aliases, not the full catalog.
    The full compact catalog contains hundreds of thousands of systems/types;
    turning all of them into regex replacements stalls the Tk UI.
    """
    global ALIAS_RULE_VERSION, ALIAS_REPLACEMENT_RULES
    entries: list[tuple[str, str]] = []
    try:
        for entry in USER_ALIASES or []:
            if not entry.get("enabled", True):
                continue
            alias_s = str(entry.get("alias") or "").strip()
            canonical_s = str(entry.get("canonical") or "").strip()
            if alias_s and canonical_s and alias_s.casefold() != canonical_s.casefold():
                entries.append((alias_s, canonical_s))
        for alias_s, canonical_s in MANUAL_TYPE_ALIASES.items():
            if alias_s and canonical_s and str(alias_s).casefold() != str(canonical_s).casefold():
                entries.append((str(alias_s), str(canonical_s)))
    except Exception as exc:
        write_log("Alias rule rebuild failed", exc)
    seen: set[str] = set()
    rules: list[tuple[str, str, re.Pattern]] = []
    for alias, canonical in sorted(entries, key=lambda kv: -len(kv[0])):
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        try:
            # Prevent replacing inside a canonical phrase already produced by an
            # earlier row-specific replacement, e.g. Apocalypse Navy should not
            # turn Apocalypse Navy Issue into Apocalypse Navy Issue Issue.
            suffix_guard = ""
            ckey = canonical.casefold()
            if ckey.startswith(key):
                suffix = canonical[len(alias):]
                if suffix:
                    suffix_guard = r"(?!(?:" + re.escape(suffix) + r")(?=$|[^A-Za-z0-9_-]))"
            pattern = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(alias) + suffix_guard + r"(?![A-Za-z0-9_-])", re.I)
        except Exception:
            continue
        rules.append((key, canonical, pattern))
    ALIAS_REPLACEMENT_RULES = rules
    ALIAS_RULE_VERSION += 1


CATALOG = EveCatalog()
USER_ALIASES = load_user_aliases()
apply_user_aliases_to_catalog(CATALOG, USER_ALIASES)

# User/community shorthand aliases that should override ambiguous machine translation.
# Keep this small and explicit; the compact catalog still provides normal SDE names.
MANUAL_TYPE_ALIASES = {
    "çŸ­å‰‘": "Stabber",
    "æµ·ç‹žç¾": "Caracal Navy Issue",
    '鱼鹰级海军型': 'Osprey Navy Issue',
    '鱼鹰海军型': 'Osprey Navy Issue',
    'Osprey class naval version': 'Osprey Navy Issue',
    'Osprey naval version': 'Osprey Navy Issue',
    '狞獾级海军型': 'Caracal Navy Issue',
    '狞獾海军型': 'Caracal Navy Issue',
    'Caracal-class naval version': 'Caracal Navy Issue',
    'Caracal naval version': 'Caracal Navy Issue',
    '天梯级': 'Skyhook',
    '天梯': 'Skyhook',
    'sky ladder': 'Skyhook',
    '镰刀级舰队型': 'Scythe Fleet Issue',
    '镰刀舰队型': 'Scythe Fleet Issue',
    'Scythe-class fleet type': 'Scythe Fleet Issue',
    'Scythe class fleet type': 'Scythe Fleet Issue',
    'Scythe fleet type': 'Scythe Fleet Issue',
    '启示级海军型': 'Omen Navy Issue',
    '启示海军型': 'Omen Navy Issue',
    'Apocalypse-class naval type': 'Omen Navy Issue',
    'Apocalypse class naval type': 'Omen Navy Issue',
    'Apocalypse naval type': 'Omen Navy Issue',
    '送葬者级海军型': 'Exequror Navy Issue',
    '送葬者海军型': 'Exequror Navy Issue',
    'Undertaker-class naval type': 'Exequror Navy Issue',
    'Undertaker class naval type': 'Exequror Navy Issue',
    'Undertaker naval type': 'Exequror Navy Issue',
    '加达里海军霍克比尔级': 'Caldari Navy Hookbill',
    '加达里海军霍克比尔': 'Caldari Navy Hookbill',
    'Caldari Navy Hawkbill Class': 'Caldari Navy Hookbill',
    'Caldari Navy Hawkbill': 'Caldari Navy Hookbill',
    '娜迦级': 'Naga',
    '洛基级': 'Loki',
    '黑鸦级': 'Blackbird',
    'Black Crow-class': 'Blackbird',
    'Black Crow': 'Blackbird',
    '海神级': 'Poseidon',
    '短剑级': 'Stabber',
    'Stabber level': 'Stabber',
    'Stabber级': 'Stabber',
    '恩尤级': 'Enyo',
    'Enyou class': 'Enyo',
    '恩尤': 'Enyo',
    '阿斯特罗级': 'Astero',
    'Astro Class': 'Astero',
    '赫卡特级': 'Hecate',
    'Heka Class': 'Hecate',
    '咒逐级': 'Curse',
    'Curse level by level': 'Curse',
    '偷天沟': 'Tengu',
    '流浪': 'Vagabond',
    'Widmark-class': 'Widow',
    'Widmark Class': 'Widow',
    'Widmark': 'Widow',
    'Assassin-class': 'Assassin',
    'Assassin Class': 'Assassin',
    'Ocato-class': 'Osprey Navy Issue',
    'Ocato Class': 'Osprey Navy Issue',
    '海鱼': 'Osprey Navy Issue',
    '海鱼鹰': 'Osprey Navy Issue',
    '海鱼鹰级': 'Osprey Navy Issue',
    'Sea fish': 'Osprey Navy Issue',
}
for _alias, _canonical in MANUAL_TYPE_ALIASES.items():
    CATALOG.aliases.setdefault(_alias.casefold(), _canonical)
    CATALOG.alias_kinds.setdefault(_alias.casefold(), "ship")
    if isinstance(CATALOG.ship_names, dict):
        CATALOG.ship_names.setdefault(_canonical.casefold(), _canonical)
    elif hasattr(CATALOG.ship_names, "add"):
        CATALOG.ship_names.add(_canonical.casefold())
rebuild_cjk_ship_alias_terms()
rebuild_alias_replacement_rules()


def reload_user_aliases() -> list[dict]:
    global CATALOG, USER_ALIASES
    USER_ALIASES = load_user_aliases()
    CATALOG.load()
    apply_user_aliases_to_catalog(CATALOG, USER_ALIASES)
    for _alias, _canonical in MANUAL_TYPE_ALIASES.items():
        CATALOG.aliases.setdefault(_alias.casefold(), _canonical)
        CATALOG.alias_kinds.setdefault(_alias.casefold(), "ship")
        if isinstance(CATALOG.ship_names, dict):
            CATALOG.ship_names.setdefault(_canonical.casefold(), _canonical)
        elif hasattr(CATALOG.ship_names, "add"):
            CATALOG.ship_names.add(_canonical.casefold())
    rebuild_cjk_ship_alias_terms()
    rebuild_alias_replacement_rules()
    return USER_ALIASES

class TranslationCache:
    def __init__(self, path: Path = TRANSLATION_CACHE_PATH):
        self.path = path
        self._init()

    def _init(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(self.path)
            con.execute("""create table if not exists translation_cache(
                key text primary key, source_text text not null, source_lang text,
                target_lang text not null, translated_text text not null, engine text not null,
                created_at text not null, last_used_at text not null, hit_count integer not null default 0)""")
            con.execute("""create table if not exists translation_overrides(
                id integer primary key autoincrement, source_text text not null, normalized_source text not null,
                source_lang text, target_lang text not null, translated_text text not null,
                enabled integer not null default 1, note text, created_at text not null, updated_at text not null,
                last_used_at text, hit_count integer not null default 0)""")
            con.execute("create index if not exists idx_translation_overrides_lookup on translation_overrides(normalized_source, target_lang, enabled)")
            con.execute("""create table if not exists translation_failures(
                key text primary key, source_text text not null, target_lang text not null, engine text not null,
                failure_reason text, failed_at text not null, retry_after text not null, fail_count integer not null default 1)""")
            con.commit(); con.close()
        except Exception as exc:
            write_log("Translation cache init failed", exc)

    def get(self, key: str) -> str | None:
        try:
            con = sqlite3.connect(self.path)
            row = con.execute("select translated_text, hit_count from translation_cache where key=?", (key,)).fetchone()
            if row:
                con.execute("update translation_cache set last_used_at=?, hit_count=? where key=?", (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), int(row[1]) + 1, key))
                con.commit(); con.close(); return str(row[0])
            con.close()
        except Exception as exc:
            write_log("Translation cache get failed", exc)
        return None

    def put(self, key: str, source_text: str, source_lang: str, target_lang: str, translated_text: str, engine: str):
        try:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            con = sqlite3.connect(self.path)
            con.execute("""insert or replace into translation_cache
                (key, source_text, source_lang, target_lang, translated_text, engine, created_at, last_used_at, hit_count)
                values (?, ?, ?, ?, ?, ?, ?, ?, coalesce((select hit_count from translation_cache where key=?), 0))""",
                (key, source_text, source_lang, target_lang, translated_text, engine, now, now, key))
            con.commit(); con.close()
        except Exception as exc:
            write_log("Translation cache put failed", exc)

    def put_machine(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        translated_text: str,
        engine: str,
        direction: str = "zh-en",
        protected_terms: list[str] | None = None,
    ) -> bool:
        if not should_cache_translation_source(source_text, direction, target_lang, engine, protected_terms=protected_terms):
            return False
        if self._is_noop_auto_en_machine(source_text, source_lang, target_lang, translated_text):
            return False
        key = self.key_for(source_text, source_lang, target_lang, engine)
        self.put(key, source_text, source_lang, target_lang, translated_text, engine)
        return True

    def seed_entries(self, entries: list[dict]) -> int:
        """Seed bundled starter translations without overwriting local cache rows."""
        if not entries:
            return 0
        inserted = 0
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            con = sqlite3.connect(self.path)
            with con:
                for item in entries:
                    key = str(item.get("key") or "").strip()
                    source_text = str(item.get("source_text") or "")
                    translated_text = str(item.get("translated_text") or "")
                    target_lang = str(item.get("target_lang") or "en") or "en"
                    if not key or not source_text or not translated_text:
                        continue
                    exists = con.execute("select 1 from translation_cache where key=?", (key,)).fetchone()
                    if exists:
                        continue
                    con.execute("""insert into translation_cache
                        (key, source_text, source_lang, target_lang, translated_text, engine, created_at, last_used_at, hit_count)
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            key,
                            source_text,
                            str(item.get("source_lang") or ""),
                            target_lang,
                            translated_text,
                            str(item.get("engine") or "bundled-translation-starter"),
                            str(item.get("created_at") or now),
                            str(item.get("last_used_at") or now),
                            int(item.get("hit_count") or 0),
                        ),
                    )
                    inserted += 1
            con.close()
        except Exception as exc:
            write_log("Translation starter seed failed", exc)
        return inserted

    def normalize_source(self, text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    def _is_noop_auto_en_machine(
        self, source_text: str, source_lang: str, target_lang: str, translated_text: str
    ) -> bool:
        if str(source_lang or "auto").lower() != "auto" or str(target_lang or "en").lower() != "en":
            return False
        source = self.normalize_source(normalize_feed_text(source_text)).casefold()
        translated = self.normalize_source(normalize_feed_text(translated_text)).casefold()
        return bool(source and translated and source == translated)

    def key_for(self, source_text: str, source_lang: str, target_lang: str, engine: str) -> str:
        import hashlib
        norm = self.normalize_source(source_text)
        digest = hashlib.sha256(f"{source_lang}|{target_lang}|{engine}|{norm}".encode("utf-8")).hexdigest()
        return f"{engine}|{source_lang}|{target_lang}|{digest}"

    def get_override(self, source_text: str, target_lang: str) -> str | None:
        norm = self.normalize_source(source_text)
        if not norm:
            return None
        try:
            con = sqlite3.connect(self.path)
            row = con.execute("""select id, translated_text, hit_count from translation_overrides
                where normalized_source=? and target_lang=? and enabled=1 order by updated_at desc, id desc limit 1""", (norm, target_lang)).fetchone()
            if row:
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                con.execute("update translation_overrides set last_used_at=?, hit_count=? where id=?", (now, int(row[2] or 0)+1, int(row[0])))
                con.commit(); con.close(); return str(row[1])
            con.close()
        except Exception as exc:
            write_log("Translation override get failed", exc)
        return None

    def save_override(self, source_text: str, translated_text: str, target_lang: str = "en", source_lang: str = "auto", note: str = "", enabled: bool = True, override_id: int | None = None) -> int | None:
        norm = self.normalize_source(source_text)
        translated = str(translated_text or "").strip()
        if not norm or not translated:
            return None
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            con = sqlite3.connect(self.path)
            if override_id:
                con.execute("update translation_overrides set source_text=?, normalized_source=?, source_lang=?, target_lang=?, translated_text=?, enabled=?, note=?, updated_at=? where id=?", (source_text, norm, source_lang, target_lang, translated, 1 if enabled else 0, note, now, int(override_id)))
                oid = int(override_id)
            else:
                cur = con.execute("""insert into translation_overrides(source_text, normalized_source, source_lang, target_lang, translated_text, enabled, note, created_at, updated_at, hit_count)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""", (source_text, norm, source_lang, target_lang, translated, 1 if enabled else 0, note, now, now))
                oid = int(cur.lastrowid)
            con.commit(); con.close(); return oid
        except Exception as exc:
            write_log("Translation override save failed", exc); return None

    def delete_override(self, override_id: int) -> bool:
        try:
            con = sqlite3.connect(self.path); con.execute("delete from translation_overrides where id=?", (int(override_id),)); con.commit(); con.close(); return True
        except Exception as exc:
            write_log("Translation override delete failed", exc); return False

    def delete_grouped_entry(self, normalized_source: str, target_lang: str = "en") -> dict:
        """Delete one logical Translation Cache Manager row.

        The UI groups manual overrides and machine-cache records by normalized
        source/target. Deleting only a manual override made cache-backed rows
        appear to ignore Delete. This removes the whole grouped row while
        leaving unrelated sources untouched.
        """
        norm = self.normalize_source(normalized_source)
        target = str(target_lang or "en")
        result = {"overrides": 0, "cache": 0, "failures": 0}
        if not norm:
            return result
        try:
            con = sqlite3.connect(self.path)
            with con:
                cur = con.execute("delete from translation_overrides where normalized_source=? and target_lang=?", (norm, target))
                result["overrides"] = int(cur.rowcount if cur.rowcount is not None else 0)
                rows = con.execute("select key, source_text from translation_cache where target_lang=?", (target,)).fetchall()
                doomed = [(str(key),) for key, source_text in rows if self.normalize_source(source_text) == norm]
                if doomed:
                    con.executemany("delete from translation_cache where key=?", doomed)
                result["cache"] = len(doomed)
                failures = con.execute("select key, source_text from translation_failures where target_lang=?", (target,)).fetchall()
                doomed_failures = [(str(key),) for key, source_text in failures if self.normalize_source(source_text) == norm]
                if doomed_failures:
                    con.executemany("delete from translation_failures where key=?", doomed_failures)
                result["failures"] = len(doomed_failures)
            con.close()
        except Exception as exc:
            write_log("Translation grouped entry delete failed", exc)
        return result

    def clear_all_entries(self, include_overrides: bool = True) -> dict:
        """Clear machine cache, failure cooldowns, and optionally manual overrides."""
        result = {"cache": 0, "overrides": 0, "failures": 0}
        try:
            con = sqlite3.connect(self.path)
            with con:
                for table, key in (("translation_cache", "cache"), ("translation_failures", "failures")):
                    row = con.execute(f"select count(*) from {table}").fetchone()
                    result[key] = int((row or [0])[0] or 0)
                    con.execute(f"delete from {table}")
                if include_overrides:
                    row = con.execute("select count(*) from translation_overrides").fetchone()
                    result["overrides"] = int((row or [0])[0] or 0)
                    con.execute("delete from translation_overrides")
            con.close()
        except Exception as exc:
            write_log("Translation cache full clear failed", exc)
        return result

    def recent_entries(self, search: str = "", limit: int = 100) -> list[dict]:
        out=[]; like=f"%{search.strip()}%"
        try:
            con=sqlite3.connect(self.path)
            if search.strip():
                rows=con.execute("select id,source_text,translated_text,target_lang,enabled,hit_count,last_used_at,updated_at,note from translation_overrides where source_text like ? or translated_text like ? order by updated_at desc limit ?",(like,like,limit)).fetchall()
            else:
                rows=con.execute("select id,source_text,translated_text,target_lang,enabled,hit_count,last_used_at,updated_at,note from translation_overrides order by updated_at desc limit ?",(limit,)).fetchall()
            for r in rows:
                out.append({"kind":"manual","id":r[0],"source_text":r[1],"translated_text":r[2],"target_lang":r[3],"enabled":bool(r[4]),"hit_count":r[5],"last_used_at":r[6],"updated_at":r[7],"note":r[8] or ""})
            rem=max(0,limit-len(out))
            if rem:
                if search.strip():
                    rows=con.execute("select key,source_text,translated_text,target_lang,engine,hit_count,last_used_at,created_at from translation_cache where source_text like ? or translated_text like ? order by last_used_at desc limit ?",(like,like,rem)).fetchall()
                else:
                    rows=con.execute("select key,source_text,translated_text,target_lang,engine,hit_count,last_used_at,created_at from translation_cache order by last_used_at desc limit ?",(rem,)).fetchall()
                for r in rows:
                    out.append({"kind":"cache","key":r[0],"source_text":r[1],"translated_text":r[2],"target_lang":r[3],"engine":r[4],"hit_count":r[5],"last_used_at":r[6],"updated_at":r[7],"enabled":True,"note":""})
            con.close()
        except Exception as exc:
            write_log("Translation cache recent entries failed", exc)
        return out

    def grouped_entries(self, original_filter: str = "", translated_filter: str = "", limit: int = 250) -> list[dict]:
        """Return one logical editable row per normalized source.

        Manual overrides are the winning value. Raw engine/cache duplicates are
        folded into metadata so the UI behaves like a correction editor rather
        than a database viewer.
        """
        groups: dict[tuple[str, str], dict] = {}
        orig_f = str(original_filter or "").strip().casefold()
        trans_f = str(translated_filter or "").strip().casefold()
        try:
            con = sqlite3.connect(self.path)
            manual_rows = con.execute("""select id, source_text, normalized_source, translated_text, target_lang, enabled,
                    hit_count, last_used_at, updated_at, note
                from translation_overrides order by updated_at desc, id desc limit ?""", (max(limit * 3, 500),)).fetchall()
            cache_rows = con.execute("""select key, source_text, translated_text, target_lang, engine, hit_count,
                    last_used_at, created_at
                from translation_cache order by last_used_at desc limit ?""", (max(limit * 4, 800),)).fetchall()
            con.close()
            def ensure(norm: str, target: str, source_text: str) -> dict:
                key = (norm, target)
                if key not in groups:
                    groups[key] = {
                        "kind": "group",
                        "source_text": source_text,
                        "normalized_source": norm,
                        "translated_text": "",
                        "target_lang": target,
                        "enabled": True,
                        "manual_id": None,
                        "note": "",
                        "hit_count": 0,
                        "last_used_at": "",
                        "updated_at": "",
                        "duplicate_count": 0,
                        "records": [],
                        "engines": set(),
                        "winning_kind": "cache",
                    }
                return groups[key]
            for r in manual_rows:
                oid, source_text, norm, translated, target, enabled, hits, last_used, updated, note = r
                norm = str(norm or self.normalize_source(source_text))
                target = str(target or "en")
                g = ensure(norm, target, str(source_text or norm))
                g["records"].append({"kind": "manual", "id": oid})
                g["duplicate_count"] += 1
                g["engines"].add("manual")
                g["hit_count"] += int(hits or 0)
                # Newest manual override wins.
                if not g.get("manual_id"):
                    g.update({
                        "kind": "manual",
                        "manual_id": int(oid),
                        "id": int(oid),
                        "source_text": str(source_text or norm),
                        "translated_text": str(translated or ""),
                        "target_lang": target,
                        "enabled": bool(enabled),
                        "note": str(note or ""),
                        "last_used_at": str(last_used or ""),
                        "updated_at": str(updated or ""),
                        "winning_kind": "manual",
                    })
            for r in cache_rows:
                key, source_text, translated, target, engine, hits, last_used, created = r
                norm = self.normalize_source(source_text)
                if not norm:
                    continue
                target = str(target or "en")
                g = ensure(norm, target, str(source_text or norm))
                g["records"].append({"kind": "cache", "key": key, "engine": engine})
                g["duplicate_count"] += 1
                g["engines"].add(str(engine or "cache"))
                g["hit_count"] += int(hits or 0)
                if not g.get("manual_id") and not g.get("translated_text"):
                    g.update({
                        "kind": "cache",
                        "source_text": str(source_text or norm),
                        "translated_text": str(translated or ""),
                        "target_lang": target,
                        "enabled": True,
                        "note": "",
                        "last_used_at": str(last_used or ""),
                        "updated_at": str(created or ""),
                        "winning_kind": "cache",
                    })
            rows = []
            for g in groups.values():
                g["engines"] = ", ".join(sorted(g.get("engines") or []))
                if orig_f and orig_f not in str(g.get("source_text") or "").casefold():
                    continue
                if trans_f and trans_f not in str(g.get("translated_text") or "").casefold():
                    continue
                rows.append(g)
            rows.sort(key=lambda x: (0 if x.get("manual_id") else 1, str(x.get("updated_at") or x.get("last_used_at") or "")), reverse=False)
            # Put most recently changed/used manual rows first, then cache rows.
            rows.sort(key=lambda x: (1 if x.get("manual_id") else 0, str(x.get("updated_at") or x.get("last_used_at") or "")), reverse=True)
            return rows[:limit]
        except Exception as exc:
            write_log("Translation cache grouped entries failed", exc)
            return []

    def cleanup_duplicate_machine_rows(self, dry_run: bool = False) -> int:
        """Remove exact duplicate machine cache rows, keeping newest/highest-hit per normalized source/target/engine."""
        removed = 0
        try:
            con = sqlite3.connect(self.path)
            rows = con.execute("select key, source_text, target_lang, engine, hit_count, last_used_at from translation_cache").fetchall()
            keep: dict[tuple[str, str, str], tuple[str, int, str]] = {}
            doomed: list[str] = []
            for key, source_text, target, engine, hits, last_used in rows:
                gkey = (self.normalize_source(source_text), str(target or "en"), str(engine or ""))
                score = (int(hits or 0), str(last_used or ""))
                if gkey not in keep:
                    keep[gkey] = (str(key), score[0], score[1])
                    continue
                old_key, old_hits, old_last = keep[gkey]
                if score > (old_hits, old_last):
                    doomed.append(old_key)
                    keep[gkey] = (str(key), score[0], score[1])
                else:
                    doomed.append(str(key))
            if doomed and not dry_run:
                with con:
                    con.executemany("delete from translation_cache where key=?", [(k,) for k in doomed])
            con.close()
            removed = len(doomed)
        except Exception as exc:
            write_log("Translation duplicate cache cleanup failed", exc)
        return removed

    def override_count(self) -> int:
        try:
            con=sqlite3.connect(self.path); row=con.execute("select count(*) from translation_overrides where enabled=1").fetchone(); con.close(); return int(row[0] or 0)
        except Exception:
            return 0

    def failure_key(self, source_text: str, target_lang: str, engine: str) -> str:
        import hashlib
        return hashlib.sha256(f"fail|{target_lang}|{engine}|{self.normalize_source(source_text)}".encode("utf-8")).hexdigest()

    def failure_active(self, source_text: str, target_lang: str, engine: str) -> bool:
        try:
            key=self.failure_key(source_text,target_lang,engine); now=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            con=sqlite3.connect(self.path); row=con.execute("select retry_after from translation_failures where key=?",(key,)).fetchone(); con.close()
            return bool(row and str(row[0]) > now)
        except Exception:
            return False

    def record_failure(self, source_text: str, target_lang: str, engine: str, reason: str, cooldown_minutes: int = 60) -> None:
        try:
            import datetime as _dt
            now_dt=_dt.datetime.utcnow(); retry=now_dt+_dt.timedelta(minutes=max(1,int(cooldown_minutes or 60)))
            now=now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"); retry_s=retry.strftime("%Y-%m-%dT%H:%M:%SZ"); key=self.failure_key(source_text,target_lang,engine)
            con=sqlite3.connect(self.path)
            con.execute("""insert into translation_failures(key,source_text,target_lang,engine,failure_reason,failed_at,retry_after,fail_count) values(?,?,?,?,?,?,?,1)
                on conflict(key) do update set failure_reason=excluded.failure_reason, failed_at=excluded.failed_at, retry_after=excluded.retry_after, fail_count=translation_failures.fail_count+1""", (key,source_text,target_lang,engine,str(reason or "")[:240],now,retry_s))
            con.commit(); con.close()
        except Exception as exc:
            write_log("Translation failure record failed", exc)

    def cleanup_polluted_mixed_rows(self, dry_run: bool = False) -> int:
        """Remove engine cache rows that include English intel context plus CJK.

        Manual overrides are intentionally untouched. This only deletes machine cache rows
        whose source_text is larger than the derived translation segment.
        """
        removed = 0
        try:
            con = sqlite3.connect(self.path)
            rows = con.execute("select key, source_text, source_lang, target_lang, engine from translation_cache").fetchall()
            doomed = []
            for key, source_text, source_lang, target_lang, engine in rows:
                if str(source_lang or "auto").lower() != "auto" or str(target_lang or "en").lower() != "en":
                    continue
                src = str(source_text or "")
                if not re.search(r"[\u3400-\u9fff\uf900-\ufaff]", src):
                    continue
                segment = cjk_translation_source(src)
                if segment and segment != normalize_feed_text(src) and len(segment) + 8 < len(normalize_feed_text(src)):
                    doomed.append(str(key))
            if doomed and not dry_run:
                with con:
                    con.executemany("delete from translation_cache where key=?", [(k,) for k in doomed])
            removed = len(doomed)
            con.close()
        except Exception as exc:
            write_log("Translation polluted-cache cleanup failed", exc)
        return removed

    def cleanup_invalid_auto_en_rows(self, dry_run: bool = False, protected_terms: list[str] | None = None) -> int:
        """Remove machine-cache rows that should never be Auto -> EN sources.

        This preserves manual overrides and EN -> CN rows. It targets historical
        pollution from the old low-level Google cache path: SBX placeholders,
        URLs, protected-term-only rows, and English-only Auto -> EN sources.
        """
        removed = 0
        try:
            con = sqlite3.connect(self.path)
            rows = con.execute("select key, source_text, source_lang, target_lang, translated_text, engine from translation_cache").fetchall()
            doomed = []
            for key, source_text, source_lang, target_lang, translated_text, engine in rows:
                target = str(target_lang or "en")
                if str(source_lang or "auto").lower() != "auto" or target.lower() != "en":
                    continue
                src = str(source_text or "")
                if self._is_noop_auto_en_machine(src, str(source_lang or "auto"), target, str(translated_text or "")):
                    doomed.append(str(key))
                elif not should_cache_translation_source(src, "zh-en", target, str(engine or ""), protected_terms=protected_terms):
                    doomed.append(str(key))
            if doomed and not dry_run:
                with con:
                    con.executemany("delete from translation_cache where key=?", [(k,) for k in doomed])
            removed = len(doomed)
            con.close()
        except Exception as exc:
            write_log("Translation invalid Auto->EN cache cleanup failed", exc)
        return removed

    def stats(self):
        try:
            con = sqlite3.connect(self.path)
            row = con.execute("select count(*), coalesce(sum(hit_count),0) from translation_cache").fetchone()
            con.close(); return row or (0, 0)
        except Exception:
            return (0, 0)

    def clear(self) -> bool:
        try:
            con = sqlite3.connect(self.path)
            with con:
                con.execute("delete from translation_cache")
                con.execute("delete from translation_failures")
            con.close(); return True
        except Exception as exc:
            write_log("Translation cache clear failed", exc); return False


TRANSLATION_CACHE = TranslationCache()


def seed_default_translation_cache() -> int:
    """Seed bundled starter machine translations without overwriting user cache."""
    path = DATA_DIR / "default_translation_cache.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("entries") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return 0
        seeded = TRANSLATION_CACHE.seed_entries([x for x in items if isinstance(x, dict)])
        if seeded:
            write_log(f"Seeded {seeded} bundled translation cache entries")
        return seeded
    except Exception as exc:
        write_log("Default translation cache seed failed", exc)
        return 0


seed_default_translation_cache()


def redact_secret(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "..." + value[-4:] if len(value) > 10 else "***"


def load_esi_settings() -> dict:
    defaults = {
        "enabled": bool(SETTINGS.get("esi_entity_recognition", True)),
        "oauth_enabled": bool(SETTINGS.get("esi_oauth_enabled", False)),
        "client_id": ESI_DEFAULT_CLIENT_ID,
        "client_secret": "",
        "callback_url": ESI_CALLBACK_URL,
        "scopes": [],
    }
    try:
        if ESI_CONFIG_PATH.exists():
            loaded = json.loads(ESI_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                defaults.update(loaded)
    except Exception as exc:
        write_log("ESI settings load failed", exc)
    return defaults


def save_esi_settings(settings: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        safe = dict(settings)
        ESI_CONFIG_PATH.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        write_log("ESI settings save failed", exc)


def save_esi_tokens(tokens: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ESI_TOKENS_PATH.write_text(json.dumps(tokens, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        write_log("ESI token save failed", exc)


def load_esi_tokens() -> dict:
    try:
        if ESI_TOKENS_PATH.exists():
            data = json.loads(ESI_TOKENS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        write_log("ESI token load failed", exc)
    return {}


def normalize_esi_query(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


class EsiCache:
    def __init__(self, path: Path = ESI_CACHE_PATH):
        self.path = path
        self._init()

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path, timeout=3, check_same_thread=False)

    def _init(self):
        try:
            con = self._connect()
            con.execute("""create table if not exists esi_entities(
                query text primary key, entity_type text, entity_id integer, name text,
                corporation_id integer, corporation_name text, alliance_id integer, alliance_name text,
                resolved_at real not null, expires_at real not null, hit_count integer not null default 0, source text)""")
            con.execute("""create table if not exists esi_negative_cache(
                query text primary key, reason text, resolved_at real not null, expires_at real not null, hit_count integer not null default 0)""")
            con.execute("""create table if not exists esi_corrections(
                text text primary key, action text not null, entity_type text, entity_id integer,
                canonical_name text, note text, created_at real not null)""")
            con.execute("""create table if not exists exclusion_rules(
                id integer primary key autoincrement,
                text text not null,
                normalized_text text not null,
                scope text not null,
                target_kind text not null default 'any',
                channel text not null default '',
                enabled integer not null default 1,
                note text not null default '',
                source text not null default 'user',
                created_at real not null,
                updated_at real not null,
                unique(normalized_text, scope, target_kind, channel)
            )""")
            con.execute("create index if not exists idx_exclusion_rules_scope on exclusion_rules(scope, enabled)")
            con.execute("""create table if not exists esi_status(key text primary key, value text, updated_at real not null)""")
            con.commit(); con.close()
        except Exception as exc:
            write_log("ESI cache init failed", exc)

    def get_correction(self, query: str) -> dict | None:
        key = normalize_esi_query(query)
        if not key:
            return None
        try:
            con = self._connect()
            row = con.execute("select action, entity_type, entity_id, canonical_name, note from esi_corrections where text=?", (key,)).fetchone()
            con.close()
            if row:
                return {"query": query, "action": row[0], "entity_type": row[1], "entity_id": row[2], "name": row[3], "note": row[4], "source": "manual"}
        except Exception as exc:
            write_log("ESI correction lookup failed", exc)
        return None

    def set_correction(self, text: str, action: str, entity_type: str = "", entity_id: int | None = None, canonical_name: str = "", note: str = "") -> bool:
        key = normalize_esi_query(text)
        if not key:
            return False
        try:
            con = self._connect()
            con.execute("insert or replace into esi_corrections(text, action, entity_type, entity_id, canonical_name, note, created_at) values(?,?,?,?,?,?,?)",
                        (key, action, entity_type, entity_id, canonical_name, note, time.time()))
            con.commit(); con.close(); return True
        except Exception as exc:
            write_log("ESI correction save failed", exc); return False

    def list_corrections(self, action: str | None = None) -> list[dict]:
        try:
            con = self._connect()
            if action:
                rows = con.execute("select text, action, entity_type, entity_id, canonical_name, note, created_at from esi_corrections where action=? order by text", (action,)).fetchall()
            else:
                rows = con.execute("select text, action, entity_type, entity_id, canonical_name, note, created_at from esi_corrections order by action, text").fetchall()
            con.close()
            return [{"text": r[0], "action": r[1], "entity_type": r[2], "entity_id": r[3], "name": r[4], "note": r[5], "created_at": r[6]} for r in rows]
        except Exception as exc:
            write_log("ESI correction list failed", exc)
            return []

    def remove_correction(self, text: str) -> bool:
        key = normalize_esi_query(text)
        if not key:
            return False
        try:
            con = self._connect(); con.execute("delete from esi_corrections where text=?", (key,)); con.commit(); con.close(); return True
        except Exception as exc:
            write_log("ESI correction remove failed", exc); return False

    def set_exclusion_rule(self, text: str, scope: str, target_kind: str = "any", enabled: bool = True, note: str = "", source: str = "user", channel: str = "") -> int | None:
        raw = str(text or "").strip()
        norm = normalize_esi_query(raw)
        scope = str(scope or "").strip()
        target_kind = str(target_kind or "any").strip() or "any"
        channel = str(channel or "").strip()
        if not raw or not norm or scope not in {"pilot_ignore", "highlight_exclude", "noise_word", "chat_filter"}:
            return None
        now = time.time()
        try:
            con = self._connect()
            cur = con.execute("""insert into exclusion_rules(text, normalized_text, scope, target_kind, channel, enabled, note, source, created_at, updated_at)
                values(?,?,?,?,?,?,?,?,?,?)
                on conflict(normalized_text, scope, target_kind, channel) do update set
                    text=excluded.text, enabled=excluded.enabled, note=excluded.note,
                    source=excluded.source, updated_at=excluded.updated_at""",
                (raw, norm, scope, target_kind, channel, 1 if enabled else 0, str(note or ""), str(source or "user"), now, now))
            row = con.execute("select id from exclusion_rules where normalized_text=? and scope=? and target_kind=? and channel=?", (norm, scope, target_kind, channel)).fetchone()
            con.commit(); con.close()
            return int(row[0]) if row else int(cur.lastrowid or 0)
        except Exception as exc:
            write_log("Exclusion rule save failed", exc)
            return None

    def list_exclusion_rules(self, scope: str | None = None, include_disabled: bool = True, include_legacy: bool = True) -> list[dict]:
        out: list[dict] = []
        try:
            con = self._connect()
            where = []
            args: list = []
            if scope:
                where.append("scope=?"); args.append(scope)
            if not include_disabled:
                where.append("enabled=1")
            sql = "select id,text,normalized_text,scope,target_kind,channel,enabled,note,source,created_at,updated_at from exclusion_rules"
            if where:
                sql += " where " + " and ".join(where)
            sql += " order by scope, text"
            rows = con.execute(sql, args).fetchall()
            con.close()
            out.extend({"id": r[0], "text": r[1], "normalized_text": r[2], "scope": r[3], "target_kind": r[4], "channel": r[5], "enabled": bool(r[6]), "note": r[7], "source": r[8], "created_at": r[9], "updated_at": r[10], "legacy": False} for r in rows)
        except Exception as exc:
            write_log("Exclusion rule list failed", exc)
        if include_legacy:
            try:
                legacy_scopes = [scope] if scope in ("pilot_ignore", "highlight_exclude") else (["pilot_ignore", "highlight_exclude"] if scope is None else [])
                for item in self.list_corrections("ignore"):
                    term = item.get("text") or ""
                    for legacy_scope in legacy_scopes:
                        if not any(normalize_esi_query(x.get("text")) == normalize_esi_query(term) and x.get("scope") == legacy_scope for x in out):
                            out.append({"id": None, "text": term, "normalized_text": normalize_esi_query(term), "scope": legacy_scope, "target_kind": "any", "channel": "", "enabled": True, "note": item.get("note") or "legacy broad exclusion", "source": "legacy", "created_at": item.get("created_at"), "updated_at": item.get("created_at"), "legacy": True})
            except Exception as exc:
                write_log("Legacy exclusion list merge failed", exc)
        return out

    def remove_exclusion_rule(self, rule_id: int | None = None, text: str = "", scope: str = "", target_kind: str = "any", channel: str = "") -> bool:
        try:
            con = self._connect()
            if rule_id is not None:
                con.execute("delete from exclusion_rules where id=?", (int(rule_id),))
            else:
                norm = normalize_esi_query(text)
                if not norm or not scope:
                    con.close(); return False
                con.execute("delete from exclusion_rules where normalized_text=? and scope=? and target_kind=? and channel=?", (norm, scope, target_kind or "any", channel or ""))
            con.commit(); con.close(); return True
        except Exception as exc:
            write_log("Exclusion rule remove failed", exc)
            return False

    def rule_matches(self, text: str, scope: str, target_kind: str = "any", channel: str = "") -> bool:
        norm = normalize_esi_query(text)
        if not norm or not scope:
            return False
        try:
            con = self._connect()
            row = con.execute("""select 1 from exclusion_rules
                where normalized_text=? and scope=? and enabled=1
                  and (target_kind in ('any', ?) or ?='any')
                  and (channel='' or channel=?)
                limit 1""", (norm, scope, target_kind or "any", target_kind or "any", channel or "")).fetchone()
            con.close()
            return bool(row)
        except Exception as exc:
            write_log("Exclusion rule match failed", exc)
            return False

    def get_status(self) -> dict:
        try:
            con = self._connect(); rows = con.execute("select key, value, updated_at from esi_status").fetchall(); con.close()
            return {r[0]: {"value": r[1], "updated_at": r[2]} for r in rows}
        except Exception:
            return {}

    def get_entity(self, query: str, force: bool = False) -> dict | None:
        if force:
            return None
        key = normalize_esi_query(query)
        if not key:
            return None
        corr = self.get_correction(query)
        if corr:
            if corr.get("action") == "ignore":
                return {"query": query, "ignored": True, "source": "manual-ignore"}
            return corr
        try:
            now = time.time(); con = self._connect()
            row = con.execute("""select entity_type, entity_id, name, corporation_id, corporation_name, alliance_id, alliance_name, expires_at, hit_count, source
                                 from esi_entities where query=?""", (key,)).fetchone()
            if row and float(row[7]) >= now:
                con.execute("update esi_entities set hit_count=? where query=?", (int(row[8]) + 1, key)); con.commit(); con.close()
                return {"query": query, "entity_type": row[0], "entity_id": row[1], "name": row[2], "corporation_id": row[3], "corporation_name": row[4], "alliance_id": row[5], "alliance_name": row[6], "source": row[9] or "esi-cache"}
            con.close()
        except Exception as exc:
            write_log("ESI cache get failed", exc)
        return None

    def put_entity(self, query: str, data: dict, ttl: int = ESI_POSITIVE_TTL_SECONDS):
        key = normalize_esi_query(query)
        if not key:
            return
        try:
            now = time.time(); con = self._connect()
            con.execute("""insert or replace into esi_entities
                (query, entity_type, entity_id, name, corporation_id, corporation_name, alliance_id, alliance_name, resolved_at, expires_at, hit_count, source)
                values(?,?,?,?,?,?,?,?,?,?,coalesce((select hit_count from esi_entities where query=?),0),?)""",
                (key, data.get("entity_type"), data.get("entity_id"), data.get("name"), data.get("corporation_id"), data.get("corporation_name"), data.get("alliance_id"), data.get("alliance_name"), now, now + ttl, key, data.get("source", "esi")))
            con.commit(); con.close()
        except Exception as exc:
            write_log("ESI cache put failed", exc)

    def is_negative(self, query: str, force: bool = False) -> bool:
        if force:
            return False
        key = normalize_esi_query(query)
        if not key:
            return True
        try:
            now = time.time(); con = self._connect()
            row = con.execute("select expires_at, hit_count from esi_negative_cache where query=?", (key,)).fetchone()
            if row and float(row[0]) >= now:
                con.execute("update esi_negative_cache set hit_count=? where query=?", (int(row[1]) + 1, key)); con.commit(); con.close(); return True
            con.close()
        except Exception as exc:
            write_log("ESI negative cache get failed", exc)
        return False

    def put_negative(self, query: str, reason: str = "not_found", ttl: int = ESI_NEGATIVE_TTL_SECONDS):
        key = normalize_esi_query(query)
        if not key:
            return
        try:
            now = time.time(); con = self._connect()
            con.execute("insert or replace into esi_negative_cache(query, reason, resolved_at, expires_at, hit_count) values(?,?,?,?,coalesce((select hit_count from esi_negative_cache where query=?),0))",
                        (key, reason, now, now + ttl, key))
            con.commit(); con.close()
        except Exception as exc:
            write_log("ESI negative cache put failed", exc)

    def set_status(self, key: str, value: str):
        try:
            con = self._connect(); con.execute("insert or replace into esi_status(key, value, updated_at) values(?,?,?)", (key, value, time.time())); con.commit(); con.close()
        except Exception:
            pass

    def list_entities(self, entity_type: str | None = None, limit: int = 5000) -> list[dict]:
        try:
            con = self._connect()
            if entity_type:
                rows = con.execute("""select query, entity_type, entity_id, name, corporation_id, corporation_name, alliance_id, alliance_name, source
                                      from esi_entities where entity_type=? order by resolved_at desc limit ?""", (entity_type, int(limit))).fetchall()
            else:
                rows = con.execute("""select query, entity_type, entity_id, name, corporation_id, corporation_name, alliance_id, alliance_name, source
                                      from esi_entities order by resolved_at desc limit ?""", (int(limit),)).fetchall()
            con.close()
            return [{"query": r[0], "entity_type": r[1], "entity_id": r[2], "name": r[3], "corporation_id": r[4], "corporation_name": r[5], "alliance_id": r[6], "alliance_name": r[7], "source": r[8] or "esi-cache"} for r in rows]
        except Exception as exc:
            write_log("ESI entity list failed", exc)
            return []

    def stats(self) -> dict:
        try:
            con = self._connect()
            entities = con.execute("select count(*) from esi_entities").fetchone()[0]
            negatives = con.execute("select count(*) from esi_negative_cache").fetchone()[0]
            corrections = con.execute("select count(*) from esi_corrections").fetchone()[0]
            status = dict(con.execute("select key, value from esi_status").fetchall())
            con.close(); return {"entities": entities, "negative": negatives, "corrections": corrections, "status": status}
        except Exception:
            return {"entities": 0, "negative": 0, "corrections": 0, "status": {}}

    def clear(self) -> bool:
        try:
            con = self._connect(); con.execute("delete from esi_entities"); con.execute("delete from esi_negative_cache"); con.commit(); con.close(); return True
        except Exception as exc:
            write_log("ESI cache clear failed", exc); return False


ESI_CACHE = EsiCache()


def seed_default_exclusions(path: Path = DEFAULT_EXCLUSIONS_PATH) -> int:
    """Legacy no-op.

    Signal Bridge used to seed bundled broad exclusions into the ESI correction
    table. Scoped Recognition Rules replace that broad list, and users can now
    start from a clean local rule set. Keep this function as a no-op so older
    startup code paths do not recreate legacy exclusions.
    """
    return 0


def seed_default_recognition_rules(path: Path = DEFAULT_RECOGNITION_RULES_PATH) -> int:
    """Seed bundled scoped recognition rules without overwriting user rules."""
    try:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("rules") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return 0
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            scope = str(item.get("scope") or "noise_word").strip()
            target = str(item.get("target_kind") or "any").strip() or "any"
            note = str(item.get("note") or "bundled default recognition rule")
            if not text:
                continue
            if ESI_CACHE.set_exclusion_rule(text, scope, target, True, note, "bundled-default"):
                added += 1
        if added:
            write_log(f"Seeded {added} bundled scoped recognition rule(s)")
        return added
    except Exception as exc:
        write_log("Default recognition rule seed failed", exc)
        return 0


def seed_default_esi_entities(path: Path = DEFAULT_ESI_ENTITIES_PATH) -> int:
    """Seed bundled verified character entities without overwriting local cache entries."""
    try:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("entities") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return 0
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            query = str(item.get("query") or item.get("name") or "").strip()
            if not query or ESI_CACHE.get_entity(query):
                continue
            payload = {
                "entity_type": item.get("entity_type") or "character",
                "entity_id": item.get("entity_id"),
                "name": item.get("name") or query,
                "corporation_id": item.get("corporation_id"),
                "corporation_name": item.get("corporation_name") or "",
                "alliance_id": item.get("alliance_id"),
                "alliance_name": item.get("alliance_name") or "",
                "source": item.get("source") or "bundled-esi-starter",
            }
            ESI_CACHE.put_entity(query, payload, ttl=365 * 24 * 60 * 60)
            added += 1
        if added:
            write_log(f"Seeded {added} bundled ESI character(s)")
        return added
    except Exception as exc:
        write_log("Default ESI entity seed failed", exc)
        return 0


seed_default_exclusions()
seed_default_recognition_rules()
seed_default_esi_entities()



def is_parser_noise(term: str) -> bool:
    """Return True for built-in or user-added words that should not become ESI candidates."""
    key = normalize_esi_query(term)
    if not key:
        return False
    if "COMMON_ESI_NOISE" in globals() and key in COMMON_ESI_NOISE:
        return True
    try:
        return ESI_CACHE.rule_matches(term, "noise_word")
    except Exception:
        return False


def is_esi_ignored(term: str) -> bool:
    """Return True when scoped or legacy rules say not to resolve a pilot via ESI."""
    key = normalize_esi_query(term)
    if not key:
        return False
    try:
        if ESI_CACHE.rule_matches(term, "pilot_ignore"):
            return True
        corr = ESI_CACHE.get_correction(term)
        return bool(corr and corr.get("action") == "ignore")
    except Exception:
        return False


def is_highlight_excluded(term: str, target_kind: str = "any") -> bool:
    """Return True when a term should not receive visual entity highlighting."""
    key = normalize_esi_query(term)
    if not key:
        return False
    try:
        if ESI_CACHE.rule_matches(term, "highlight_exclude", target_kind):
            return True
    except Exception:
        pass
    # Compatibility: existing broad ignores continue hiding highlights until users split scopes.
    return is_parser_noise(term) or is_esi_ignored(term)


def is_globally_excluded(term: str) -> bool:
    """Backward-compatible broad exclusion check for legacy call sites.

    New code should prefer is_esi_ignored(), is_highlight_excluded(), or
    is_parser_noise() so recognition, rendering, and filtering can diverge.
    """
    return is_highlight_excluded(term)


COMMON_ESI_NOISE = {
    "and", "the", "or", "to", "of", "in", "on", "at", "by", "for", "from", "with",
    "are", "they", "where", "which", "what", "when", "who", "why", "how",
    "again", "almost", "always", "anything", "maybe", "someone", "thanks", "thank",
    "link", "jump", "jumped", "fleet", "gate", "gates", "star", "isk", "ship", "ships",
    "clear", "eyes", "no visual", "nv", "ess", "red", "enemy", "hostile", "neutral", "neut", "neuts",
    "local", "system", "corp", "alliance", "channel", "changed", "channel changed",
    "description", "exclusions", "multiple", "multiple items", "seconds", "status", "version",
    "drone", "drones", "probe", "probes", "scanning probe", "combat scanning probe",
    "dscan", "cyno", "cloak", "cloaky", "bubble", "armor", "caldari", "item exchange",
    # Translation / UI / free-text English — never pilot candidates
    "original", "translation", "translated", "translate", "english", "chinese", "source",
    "target", "message", "text", "string", "language", "auto", "cache", "manual", "override",
    "phrase", "alias", "aliases", "catalog", "unknown", "none", "null", "true", "false",
    "was", "were", "been", "being", "have", "has", "had", "will", "would", "should", "could",
    "about", "just", "only", "really", "still", "already", "before", "after", "more", "most",
    "other", "others", "something", "nothing", "everything", "this", "that", "these", "those",
    "into", "onto", "over", "under", "than", "then", "also", "very", "much", "many", "some",
    "any", "all", "not", "out", "off", "up", "down", "back", "here", "there", "now", "then",
    "yes", "no", "ok", "okay", "please", "sorry", "hello", "hi", "hey", "lol", "lmao", "afk",
    "wait", "hold", "coming", "gone", "left", "right", "north", "south", "east", "west",
    "class", "level", "grade", "type", "types", "item", "items", "module", "modules",
    "capital", "supercarrier", "titan", "fax", "dread", "carrier", "ratting", "mining",
    # Generic people-words (not pilot names)
    "people", "person", "persons", "player", "players", "guy", "guys", "dude", "dudes",
    "man", "men", "woman", "women", "friend", "friends", "group", "groups", "member", "members",
    "hostiles", "friendlies", "blues", "neutrals", "reds",
    # Fitting / client UI / sim words (and common typos)
    "simulated", "simulation", "simulator", "fitting", "fittings", "fit", "fits", "button", "botton",
    "damage", "dps", "hp", "ehp", "resists", "resist", "tank", "tanking", "active", "passive",
    "room", "window", "menu", "option", "options", "settings", "filter", "filters", "tab", "tabs",
    "click", "clicked", "press", "pressed", "select", "selected", "save", "saved", "load", "loaded",
    "apply", "reset", "cancel", "confirm", "export", "import", "browse", "search", "result", "results",
}
NAME_CONTEXT_WORDS = {
    "tackle", "watch", "seen", "spotted", "reported", "report", "by", "from", "with", "kill", "killed",
    "local", "jumped", "jump", "gate", "camp", "hostile", "neut", "neutral", "red", "pilot", "scout",
}
NAME_CHUNK_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Za-z0-9'`-]{1,}(?:\s+[A-Z][A-Za-z0-9'`-]*){0,3})(?![A-Za-z0-9])")


def _span_overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    a, b = span
    return any(a < d and c < b for c, d in spans)


def _mark_term_spans(text: str, terms: list[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for term in sorted(unique([t for t in terms if t]), key=len, reverse=True):
        if len(term) < 2:
            continue
        pattern = re.escape(term) if not re.search(r"^[A-Za-z0-9 _.'`+-]+$", term) else word_boundary(term)
        try:
            for m in re.finditer(pattern, text, re.I):
                spans.append((m.start(), m.end()))
        except re.error:
            folded = text.casefold(); needle = term.casefold(); start = folded.find(needle)
            while start >= 0:
                spans.append((start, start + len(term)))
                start = folded.find(needle, start + len(term))
    return spans


def _term_occurrences(text: str, term: str) -> list[tuple[int, int]]:
    if not text or not term or len(term.strip()) < 2:
        return []
    pattern = re.escape(term) if not re.search(r"^[A-Za-z0-9 _.'`+-]+$", term) else word_boundary(term)
    try:
        return [(m.start(), m.end()) for m in re.finditer(pattern, text, re.I)]
    except re.error:
        out = []
        folded = text.casefold(); needle = term.casefold(); start = folded.find(needle)
        while start >= 0:
            out.append((start, start + len(term)))
            start = folded.find(needle, start + len(term))
        return out


def longest_non_overlapping_terms(text: str, terms: list[str]) -> list[str]:
    """Return display terms whose spans do not overlap stronger/longer terms.

    Used for ESI pilot rendering so a resolved full character like
    ``Matek Bathana`` wins over partial cached matches ``Matek`` and ``Bathana``.
    """
    chosen: list[tuple[int, int, str]] = []
    for term in sorted(unique([str(t or '').strip() for t in terms if str(t or '').strip()]), key=lambda t: (-len(t), t.casefold())):
        if is_esi_ignored(term):
            continue
        spans = _term_occurrences(text, term)
        if not spans:
            continue
        keep = False
        for a, b in spans:
            if not any(a < d and c < b for c, d, _ in chosen):
                chosen.append((a, b, term)); keep = True
        if keep:
            pass
    chosen.sort(key=lambda x: (x[0], -(x[1]-x[0]), x[2].casefold()))
    return unique([term for _, _, term in chosen])


def _looks_like_eve_handle(token: str) -> bool:
    """True for handle-like tokens (digits, camelCase, symbols) rather than plain English."""
    t = str(token or "").strip()
    if not t:
        return False
    if re.search(r"\d", t):
        return True
    if re.search(r"[_]", t):
        return True
    # internal camelCase / mixed case: aB, xxYY, McName-ish with mid caps
    if re.search(r"[a-z]`?[A-Z]", t) or re.search(r"[A-Z]{2,}[a-z]", t):
        return True
    # apostrophe handles uncommon in plain chat words
    if "'" in t or "`" in t:
        return True
    return False


def _is_plain_english_token(token: str) -> bool:
    """Alphabetic chat English (or Titlecase word) without handle signals."""
    t = str(token or "").strip()
    if len(t) < 3 or not t.isalpha():
        return False
    if _looks_like_eve_handle(t):
        return False
    if t.isupper() and len(t) >= 6:
        # long ALLCAPS can be tickers/names; treat as not plain English prose
        return False
    return True


def _has_name_context(text: str, span: tuple[int, int] | None) -> bool:
    if not text or not span:
        return False
    before = text[max(0, span[0] - 18) : span[0]].lower().split()[-3:]
    after = text[span[1] : span[1] + 18].lower().split()[:3]
    return any(w in before or w in after for w in NAME_CONTEXT_WORDS)


def _is_title_case_name(parts: list[str]) -> bool:
    """Matek Bathana / Picard X style — each part capitalised or short suffix."""
    if not parts:
        return False
    for p in parts:
        if len(p) == 1 and p.isalpha():
            continue  # allow X suffix
        if not (p[:1].isupper() and (len(p) == 1 or p[1:].islower() or p[1:].isalpha())):
            # Accept pure Titlecase or single capital letter tokens
            if not (p.istitle() or (p.isupper() and len(p) <= 3)):
                return False
    # At least one part longer than 1
    return any(len(p) > 1 for p in parts)


def is_probable_character_candidate(
    candidate: str,
    text: str = "",
    span: tuple[int, int] | None = None,
    *,
    allow_plain_single: bool = False,
) -> bool:
    """Heuristic ESI name gate.

    Root issue (fixed): message-body extraction used to accept *any* alphabetic
    token ≥5 chars not on a hand list, and every sub-window of contiguous tokens
    (so whole English phrases became candidates). Real names need handle shape,
    Title Case multi-word form, pilot-context words, or (for senders) plain single.
    """
    cand = re.sub(r"\s+", " ", candidate.strip().strip(" ,.;:()[]{}\"'`"))
    key = cand.casefold()
    if len(cand) < 3 or key in COMMON_ESI_NOISE or is_parser_noise(cand):
        return False
    if _catalog_or_plural_catalog_term(cand):
        return False
    if CATALOG.is_ship(cand) or CATALOG.lookup_system(cand):
        return False
    if SYSTEM_RE.fullmatch(cand) or LINK_RE.search(cand) or COUNT_RE.fullmatch(cand):
        return False
    parts = cand.split()
    if len(parts) > 4:
        return False
    for part in parts:
        if part.casefold() in COMMON_ESI_NOISE or is_parser_noise(part) or _catalog_or_plural_catalog_term(part):
            return False
        if CATALOG.is_ship(part) or CATALOG.lookup_system(part):
            return False

    if len(parts) == 1:
        token = parts[0]
        if len(token) < 3 or token.lower() in COMMON_ESI_NOISE or is_parser_noise(token):
            return False
        if token.isupper() and len(token) < 6:
            return False
        # Handle-like single tokens (digits/camelCase) are always OK.
        if _looks_like_eve_handle(token):
            return True
        # Plain English single word: only with pilot context, or sender exception.
        if _is_plain_english_token(token):
            if allow_plain_single:
                return len(token) >= 3
            if _has_name_context(text, span):
                return True
            return False
        # Other single tokens (mixed punctuation already handled) — require length
        return len(token) >= 5

    # Multi-word: reject bags of plain English ("check useless happy fight").
    plain_parts = [_is_plain_english_token(p) for p in parts]
    if all(plain_parts) and not _is_title_case_name(parts):
        # Allow if pilot-context sits on the span; still reject free English phrases.
        if _has_name_context(text, span) and _is_title_case_name(parts):
            return True
        # "seen PilotNameHere" won't be all plain without title case
        return False
    if _is_title_case_name(parts):
        return True
    # Mixed: at least one handle-like part
    if any(_looks_like_eve_handle(p) for p in parts):
        return True
    # Fallback multi-word with context
    if _has_name_context(text, span):
        return True
    return False


def _catalog_or_plural_catalog_term(term: str) -> bool:
    raw = term.strip(" ,.;:()[]{}\"'`")
    if not raw:
        return False
    variants = [raw]
    if raw.lower().endswith("s") and len(raw) > 4:
        variants.append(raw[:-1])
    if raw.lower().endswith("ies") and len(raw) > 5:
        variants.append(raw[:-3] + "y")
    for value in variants:
        if CATALOG.lookup_system(value) or CATALOG.lookup_type(value) or CATALOG.is_ship(value):
            return True
    return False


def _plausible_name_token(token: str) -> bool:
    token = token.strip(" ,.;:()[]{}\"'`")
    if len(token) < 3 or not re.search(r"[A-Za-z]", token):
        return False
    key = token.casefold()
    if key in COMMON_ESI_NOISE or is_parser_noise(token):
        return False
    if SYSTEM_RE.fullmatch(token) or COUNT_RE.fullmatch(token) or LINK_RE.search(token):
        return False
    if _catalog_or_plural_catalog_term(token):
        return False
    # Short all-caps fragments are usually tickers/codes, not enough for an exact ESI name by themselves.
    if token.isupper() and len(token) <= 4:
        return False
    # Drop plain English tokens from grouping unless handle-like — they create
    # phrase candidates ("check useless happy") that spam ESI.
    if _is_plain_english_token(token) and not _looks_like_eve_handle(token):
        return False
    return True


def _candidate_from_tokens(
    tokens: list[str],
    text: str = "",
    span: tuple[int, int] | None = None,
) -> str | None:
    parts = [t.strip(" ,.;:()[]{}\"'`") for t in tokens if t.strip(" ,.;:()[]{}\"'`")]
    while parts and parts[0].casefold() in COMMON_ESI_NOISE:
        parts.pop(0)
    while parts and parts[-1].casefold() in COMMON_ESI_NOISE:
        parts.pop()
    if not parts or len(parts) > 4:
        return None
    cand = " ".join(parts)
    if not is_probable_character_candidate(cand, text, span):
        return None
    return cand


def esi_message_candidates_for_row(row: Row) -> list[str]:
    text = row.text or ""
    blocked: list[tuple[int, int]] = []
    blocked.extend((m.start(), m.end()) for m in LINK_RE.finditer(text))
    blocked.extend((m.start(), m.end()) for m in HTTP_LINK_RE.finditer(text))
    blocked.extend((m.start(), m.end()) for m in COUNT_RE.finditer(text))
    terms: list[str] = []
    terms.extend(row.systems); terms.extend(row.assets); terms.extend(row.counts); terms.extend(row.links)
    for ent in row.localized:
        terms.append(str(ent.get("original", ""))); terms.append(str(ent.get("canonical", "")))
    blocked.extend(_mark_term_spans(text, terms))

    # Work on text with known EVE/system/link/count spans blanked out. This lets
    # "WH-JCA Sennessa Xerogi" still produce "Sennessa Xerogi" instead of dropping
    # the whole chunk because the system overlapped it.
    chars = list(text)
    for a, b in blocked:
        for i in range(max(0, a), min(len(chars), b)):
            chars[i] = " "
    work = "".join(chars)

    out: list[str] = []
    token_matches = list(re.finditer(r"[A-Za-z][A-Za-z0-9'`-]{2,}", work))
    tokens = [(m.group(0), m.start(), m.end()) for m in token_matches if _plausible_name_token(m.group(0))]

    # Group contiguous handle-like tokens only (plain English filtered in _plausible_name_token).
    group: list[tuple[str, int, int]] = []
    last_end: int | None = None

    def flush_group():
        nonlocal group
        if not group:
            return
        max_size = min(4, len(group))
        for start in range(len(group)):
            for size in range(max_size, 0, -1):
                if start + size > len(group):
                    continue
                chunk = group[start : start + size]
                words = [t[0] for t in chunk]
                span = (chunk[0][1], chunk[-1][2])
                cand = _candidate_from_tokens(words, text, span)
                if cand:
                    out.append(cand)
        group = []

    for token, a, b in tokens:
        if last_end is not None and work[last_end:a].strip():
            flush_group()
        group.append((token, a, b))
        last_end = b
        if len(group) >= 4:
            flush_group()
    flush_group()

    # Proper-case chunks can include spaces/punctuation that token grouping misses.
    for m in NAME_CHUNK_RE.finditer(work):
        cand = re.sub(r"\s+", " ", m.group(1).strip())
        parts = cand.split()
        while len(parts) > 1 and parts[-1].casefold() in COMMON_ESI_NOISE:
            parts.pop()
        cand = " ".join(parts)
        if is_probable_character_candidate(cand, text, (m.start(1), m.end(1))):
            out.append(cand)
    # Keep the queue bounded, but prefer longer/full names first so entries like
    # "Picard X" are submitted before shorter overlapping candidates like "Picard".
    candidates = unique(out)
    candidates.sort(key=lambda x: (-len(x), x.casefold()))
    return candidates[:8]


def esi_candidates_for_row(row: Row) -> list[str]:
    out: list[str] = []
    sender = re.sub(r"\s+", " ", row.sender.strip())
    # Senders are already EVE character names on the log line — allow plain singles.
    if sender and sender.lower() != "eve system" and is_probable_character_candidate(
        sender, allow_plain_single=True
    ):
        out.append(sender)
    if getattr(row, "esi_candidates", None):
        out.extend(row.esi_candidates)
    else:
        out.extend(esi_message_candidates_for_row(row))
    return unique(out)[:5]


class EsiResolver(threading.Thread):
    def __init__(self, outq: queue.Queue, enabled_func: Callable[[], bool]):
        super().__init__(daemon=True)
        self.outq = outq
        self.enabled_func = enabled_func
        self.work: queue.Queue = queue.Queue(maxsize=500)
        self.pending: set[str] = set()
        self.stop_event = threading.Event()
        self.last_request_at = 0.0
        self.backoff_until = 0.0

    def submit(self, query: str, force: bool = False):
        query = str(query or "").strip()
        key = normalize_esi_query(query)
        if not key or len(key) < 3 or key in COMMON_ESI_NOISE or is_parser_noise(query):
            return
        # Catalog ships/systems are not character names.
        if not force and (CATALOG.is_ship(query) or CATALOG.lookup_system(query) or _catalog_or_plural_catalog_term(query)):
            return
        if is_esi_ignored(query) and not force:
            ESI_CACHE.set_status("last_check", f"ignored: {query}")
            write_log(f"ESI ignored by exclusion list: {query!r}")
            return
        cached = ESI_CACHE.get_entity(query, force=force)
        if cached:
            if not cached.get("ignored"):
                ESI_CACHE.set_status("last_check", f"cache hit: {query} -> {cached.get('name') or cached.get('entity_type')}")
                write_log(f"ESI cache hit for {query!r}: {cached.get('entity_type')} {cached.get('name')}")
                self.outq.put(("esi_resolved", query, cached))
            return
        if ESI_CACHE.is_negative(query, force=force):
            ESI_CACHE.set_status("last_check", f"negative cache: {query}")
            write_log(f"ESI negative cache hit for {query!r}")
            return
        if key in self.pending:
            return
        try:
            self.pending.add(key)
            self.work.put_nowait((query, force))
            ESI_CACHE.set_status("last_check", f"queued: {query}")
            write_log(f"ESI queued: {query!r} force={force}")
        except queue.Full:
            self.pending.discard(key)
            ESI_CACHE.set_status("last_status", "queue_full")

    def stop(self):
        self.stop_event.set()

    def _rate_wait(self):
        now = time.time()
        if self.backoff_until > now:
            time.sleep(min(5, self.backoff_until - now))
        elapsed = time.time() - self.last_request_at
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self.last_request_at = time.time()

    def _request_json(self, url: str, params: dict | None = None, data: bytes | None = None, method: str | None = None) -> dict:
        if params:
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        self._rate_wait()
        headers = {"User-Agent": ESI_USER_AGENT, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                ESI_CACHE.set_status("last_status", "ok")
                body = resp.read().decode("utf-8", "replace")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
            if exc.code in (420, 429, 500, 502, 503, 504):
                self.backoff_until = time.time() + 30
                ESI_CACHE.set_status("last_status", f"backoff_http_{exc.code}")
            elif exc.code == 404:
                ESI_CACHE.set_status("last_status", "not_found")
            raise

    def _ids_for_name(self, query: str) -> dict:
        payload = json.dumps([query], ensure_ascii=False).encode("utf-8")
        return self._request_json(ESI_SEARCH_URL, data=payload, method="POST")

    def resolve_public(self, query: str) -> dict | None:
        data = self._ids_for_name(query)
        chars = data.get("characters") or []
        corps = data.get("corporations") or []
        alliances = data.get("alliances") or []
        if chars:
            ent = chars[0]
            cid = int(ent.get("id"))
            char = self._request_json(f"https://esi.evetech.net/latest/characters/{cid}/")
            corp_id = char.get("corporation_id")
            alliance_id = char.get("alliance_id")
            corp_name = ""; alliance_name = ""
            if corp_id:
                try:
                    corp_name = str(self._request_json(f"https://esi.evetech.net/latest/corporations/{int(corp_id)}/").get("name") or "")
                except Exception:
                    corp_name = ""
            if alliance_id:
                try:
                    alliance_name = str(self._request_json(f"https://esi.evetech.net/latest/alliances/{int(alliance_id)}/").get("name") or "")
                except Exception:
                    alliance_name = ""
            return {"query": query, "entity_type": "character", "entity_id": cid, "name": char.get("name") or ent.get("name") or query, "corporation_id": corp_id, "corporation_name": corp_name, "alliance_id": alliance_id, "alliance_name": alliance_name, "source": "esi"}
        if corps:
            ent = corps[0]
            eid = int(ent.get("id"))
            corp = self._request_json(f"https://esi.evetech.net/latest/corporations/{eid}/")
            return {"query": query, "entity_type": "corporation", "entity_id": eid, "name": corp.get("name") or ent.get("name") or query, "alliance_id": corp.get("alliance_id"), "source": "esi"}
        if alliances:
            ent = alliances[0]
            eid = int(ent.get("id"))
            ali = self._request_json(f"https://esi.evetech.net/latest/alliances/{eid}/")
            return {"query": query, "entity_type": "alliance", "entity_id": eid, "name": ali.get("name") or ent.get("name") or query, "source": "esi"}
        return None

    def run(self):
        while not self.stop_event.is_set():
            try:
                query, force = self.work.get(timeout=0.5)
            except queue.Empty:
                continue
            key = normalize_esi_query(query)
            try:
                if not self.enabled_func():
                    continue
                if ESI_CACHE.is_negative(query, force=force):
                    continue
                result = self.resolve_public(query)
                if result:
                    ESI_CACHE.put_entity(query, result)
                    ESI_CACHE.set_status("last_check", f"positive: {query} -> {result.get('name') or result.get('entity_type')}")
                    write_log(f"ESI positive answer for {query!r}: {result.get('entity_type')} {result.get('name')} corp={result.get('corporation_name','')} alliance={result.get('alliance_name','')}")
                    self.outq.put(("esi_resolved", query, result))
                else:
                    ESI_CACHE.put_negative(query, "not_found")
                    ESI_CACHE.set_status("last_check", f"negative answer: {query}")
                    write_log(f"ESI negative answer for {query!r}")
            except Exception as exc:
                ESI_CACHE.set_status("last_error", type(exc).__name__)
                ESI_CACHE.set_status("last_check", f"error: {query}: {type(exc).__name__}")
                write_log(f"ESI lookup error for {query!r}: {type(exc).__name__}")
            finally:
                self.pending.discard(key)


def load_phrase_overrides() -> list[dict]:
    try:
        if PHRASE_OVERRIDES_PATH.exists():
            data = json.loads(PHRASE_OVERRIDES_PATH.read_text(encoding="utf-8"))
            return [x for x in data.get("overrides", []) if isinstance(x, dict) and x.get("enabled", True)]
    except Exception as exc:
        write_log("Phrase overrides load failed", exc)
    return []


PHRASE_OVERRIDES = load_phrase_overrides()


def apply_phrase_overrides(text: str, direction: str) -> tuple[str, bool]:
    """Apply curated phrase overrides (durable, not machine-cache).

    Longer sources are applied first so compounds like 旗舰技能 are not
    mangled by a shorter 旗舰 replacement.
    """
    out = text
    changed = False
    items = sorted(
        PHRASE_OVERRIDES,
        key=lambda item: len(str(item.get("source", "") or "")),
        reverse=True,
    )
    for item in items:
        src = str(item.get("source", ""))
        tgt = str(item.get("target", ""))
        idir = str(item.get("direction", "zh-en"))
        if src and tgt and idir in (direction, "auto", "any") and src in out:
            out = out.replace(src, tgt)
            changed = True
    if changed:
        # Avoid gluing English replacements to neighboring latin tokens: "?Buffering"
        out = re.sub(r"([?!.,:;])([A-Za-z0-9])", r"\1 \2", out)
        out = re.sub(r"([A-Za-z0-9])([\u3400-\u9fff\uf900-\ufaff])", r"\1 \2", out)
        out = re.sub(r"([\u3400-\u9fff\uf900-\ufaff])([A-Za-z0-9])", r"\1 \2", out)
        out = re.sub(r"[ \t]{2,}", " ", out).strip()
    return out, changed


class EveDb:
    def __init__(self, path: Path, use_sqlite: bool = True):
        self.path = path
        self.use_sqlite = use_sqlite
        self.con: sqlite3.Connection | None = None
        self.cache: dict[str, str | None] = {}
        if use_sqlite and path.exists():
            self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1, check_same_thread=False)

    def close(self):
        if self.con:
            self.con.close()
            self.con = None

    def lookup_type(self, term: str) -> str | None:
        from sb_text import strip_term_punctuation
        term = strip_term_punctuation(term)
        if not term or len(term) < 2:
            return None
        key = term.lower()
        if key in self.cache:
            return self.cache[key]
        out = CATALOG.lookup_type(term)
        if out:
            self.cache[key] = out
            return out
        if self.con:
            try:
                row = self.con.execute("select typeName from invTypes where typeName=? collate nocase limit 1", (term,)).fetchone()
                if row and row[0]:
                    out = str(row[0])
                if not out:
                    row = self.con.execute("""
                        select invTypes.typeName
                        from trnTranslations
                        join invTypes on invTypes.typeID = trnTranslations.keyID
                        where trnTranslations.tcID=8 and trnTranslations.text=? collate nocase
                        limit 1
                    """, (term,)).fetchone()
                    if row and row[0]:
                        out = str(row[0])
            except sqlite3.Error:
                out = None
        self.cache[key] = out
        return out


def discover_ships_in_text(text: str) -> list[str]:
    """Find catalog ships in free text (including English after translation)."""
    found: list[str] = []
    if not text:
        return found
    for term in sorted(candidate_terms(text), key=lambda s: -len(s)):
        if is_numeric_or_decimal_token(term) or len(term) < 3:
            continue
        if CATALOG.is_ship(term):
            found.append(CATALOG.lookup_type(term) or term)
            continue
        hit = CATALOG.lookup_type(term)
        if hit and CATALOG.is_ship(hit):
            found.append(hit)
    return unique(found)


def extract_intel(text: str, db: EveDb):
    systems = []
    for raw_sys in SYSTEM_RE.findall(text):
        if is_numeric_or_decimal_token(raw_sys):
            continue
        systems.append(CATALOG.lookup_system(raw_sys) or raw_sys)
    assets: list[str] = []
    localized: list[dict] = []
    for term in sorted(candidate_terms(text), key=lambda s: -len(s)):
        if is_numeric_or_decimal_token(term):
            continue
        sys_hit = CATALOG.lookup_system(term)
        if sys_hit:
            systems.append(sys_hit)
            if sys_hit.lower() != term.lower():
                localized.append({"original": term, "canonical": sys_hit})
        hit = db.lookup_type(term)
        if hit:
            assets.append(hit)
            if hit.lower() != term.lower():
                localized.append({"original": term, "canonical": hit})
        elif CATALOG.is_ship(term):
            assets.append(CATALOG.lookup_type(term) or term)
    # Explicit ship pass so capitals (Chimera/Minokawa/Erebus/…) always land as assets.
    assets.extend(discover_ships_in_text(text))
    for term in sorted(BUILTIN_ASSETS, key=lambda s: -len(s)):
        if re.search(word_boundary(term), text, re.I):
            assets.append(term)
    # User/manual aliases may replace localized or bad machine-translation text
    # with canonical English ship/object names for display.  Detect those
    # canonicals as assets too so they highlight and feed Pilot/Intel history.
    try:
        canonical_display = localized_display_from_aliases(text, localized)
    except Exception:
        canonical_display = text
    if canonical_display != text:
        for term in sorted(BUILTIN_ASSETS, key=lambda s: -len(s)):
            if re.search(word_boundary(term), canonical_display, re.I):
                assets.append(term)
        for ent in localized or []:
            canonical = str(ent.get("canonical") or "").strip()
            if canonical and CATALOG.is_ship(canonical):
                assets.append(canonical)
        for canonical in sorted(set(MANUAL_TYPE_ALIASES.values()), key=len, reverse=True):
            if canonical and re.search(word_boundary(canonical), canonical_display, re.I):
                assets.append(canonical)
    if re.search(r"(?<![A-Za-z0-9_-])ess(?![A-Za-z0-9_-])", text, re.I):
        assets.append("ESS")
    if re.search(r"(?<!\w)nv(?!\w)", text, re.I):
        assets.append("No visual")
    # Prefer the longest/canonical asset when a shorthand alias also causes a shorter
    # partial type hit, e.g. Apocalypse Navy -> Apocalypse Navy Issue should not also
    # leave a separate Apocalypse asset in the same row.
    unique_assets = unique(assets)
    filtered_assets: list[str] = []
    localized_pairs = [(str(e.get("original") or "").casefold(), str(e.get("canonical") or "").casefold()) for e in localized]
    for asset in unique_assets:
        akey = str(asset or "").casefold()
        if akey in HOSTILE_DISPLAY_TERMS:
            continue
        if akey and any(akey != str(other or "").casefold() and akey in str(other or "").casefold() for other in unique_assets):
            continue
        # If a shorter catalog hit only appears as part of an alias phrase that
        # produced a different canonical ship, drop the shorter false positive.
        # Example: Black Crow -> Blackbird should not also leave Crow.
        if akey and any(akey != canon and akey in orig and canon in {str(x or "").casefold() for x in unique_assets} for orig, canon in localized_pairs):
            continue
        filtered_assets.append(asset)
    intent = "clear" if CLEAR.search(text) else "movement" if MOVE.search(text) else "hostile" if HOSTILE.search(text) else "unknown"
    return unique(systems), filtered_assets, localized, unique(COUNT_RE.findall(text)), unique(LINK_RE.findall(text)), intent


def translate_text(text: str, localized: list[dict], intent: str) -> str:
    out = text
    changed = False
    for ent in sorted(localized, key=lambda e: -len(e["original"])):
        out = out.replace(ent["original"], ent["canonical"])
        changed = True
    return out if changed else ""


def localized_display_from_aliases(text: str, localized: list[dict] | None = None) -> str:
    """Return display text with current catalog/user aliases applied.

    Uses precompiled alias rules plus cheap lowercase containment checks. This
    keeps aliases dynamic without running every regex against every row during
    redraw.
    """
    out = str(text or "")
    if not out:
        return out
    lower = out.casefold()
    # First apply row-specific localized matches from extraction. These are few
    # and avoid waiting for a full alias-rule rebuild when a row already knows
    # its canonical entity.
    for ent in sorted(localized or [], key=lambda e: -len(str(e.get("original") or ""))):
        original = str(ent.get("original") or "").strip()
        canonical = str(ent.get("canonical") or "").strip()
        if not original or not canonical or original.casefold() not in lower:
            continue
        try:
            pattern = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(original) + r"(?![A-Za-z0-9_-])", re.I)
            out = pattern.sub(canonical, out)
            lower = out.casefold()
        except Exception:
            out = out.replace(original, canonical)
            lower = out.casefold()
    for alias_lower, canonical, pattern in ALIAS_REPLACEMENT_RULES:
        if alias_lower not in lower:
            continue
        try:
            out = pattern.sub(canonical, out)
            lower = out.casefold()
        except Exception:
            pass
    return out


def split_intel_segments(text: str) -> list[tuple[str, str]]:
    """Split one chat message into structured intel pieces without losing raw text."""
    raw = str(text or "").strip()
    if not raw:
        return []
    kill_marker = "击杀："
    pieces: list[tuple[str, str]] = []
    if kill_marker in raw:
        for part in raw.split(kill_marker):
            part = part.strip()
            if part:
                pieces.append(("kill", part))
        if pieces:
            return pieces
    # English kill markers, conservative so normal messages are not over-split.
    m = re.split(r"(?i)\b(?:kill|killed)\s*[:：]\s*", raw)
    if len(m) > 1:
        for part in m:
            part = part.strip()
            if part:
                pieces.append(("kill", part))
        if pieces:
            return pieces
    return [("message", raw)]


def classify_segment_kind(text: str, default: str = "message") -> str:
    if default == "kill":
        return "kill"
    if re.search(r"(?<!\w)nv(?!\w)|no\s+visual", text, re.I):
        return "sighting"
    if CLEAR.search(text):
        return "clear"
    if HOSTILE.search(text):
        return "sighting"
    return default


def infer_segment_pilots(segment_text: str, assets: list[str], systems: list[str]) -> list[str]:
    """Best-effort display candidates only; ESI remains authoritative elsewhere."""
    work = segment_text
    for term in sorted(unique(list(assets) + list(systems)), key=len, reverse=True):
        if term:
            work = re.sub(word_boundary(term), " ", work, flags=re.I)
    work = re.sub(r"https?://\S+|www\.\S+|dscan\.info/\S+", " ", work, flags=re.I)
    work = re.sub(r"(?<!\w)(?:nv|clear|clr|voice|kill|killed)(?!\w)", " ", work, flags=re.I)
    # Names in EVE intel are usually 1-3 chunks with letters/digits/hyphen.
    candidates = []
    words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]{1,24}", work)
    stop = {"basilisk", "nighthawk", "jormungandr", "voice", "clear", "intel", "gate", "jump", "fleet"}
    for n in (3, 2, 1):
        for i in range(max(0, len(words) - n + 1)):
            cand = " ".join(words[i:i+n]).strip()
            if not cand or cand.casefold() in stop:
                continue
            if any(cand.casefold() == a.casefold() for a in assets):
                continue
            candidates.append(cand)
        if candidates:
            break
    return unique(candidates[:4])


def build_intel_segments(text: str, systems: list[str], assets: list[str], localized: list[dict], db: EveDb) -> list[IntelSegment]:
    segments: list[IntelSegment] = []
    for base_kind, raw_part in split_intel_segments(text):
        part = normalize_feed_text(raw_part)
        if not part:
            continue
        seg_systems, seg_assets, seg_localized, _counts, _links, _intent = extract_intel(raw_part, db)
        # Fall back to row-level entities when the segment parser is conservative.
        if not seg_systems:
            seg_systems = [x for x in systems if not is_numeric_or_decimal_token(x) and re.search(word_boundary(x), raw_part, re.I)]
        if not seg_assets:
            seg_assets = [x for x in assets if re.search(word_boundary(x), raw_part, re.I)]
        display = part
        for ent in sorted(seg_localized or localized, key=lambda e: -len(e.get("original", ""))):
            original = ent.get("original", "")
            canonical = ent.get("canonical", "")
            if original and canonical:
                display = normalize_feed_text(display.replace(original, canonical))
        statuses: list[str] = []
        notes: list[str] = []
        if re.search(r"(?<!\w)nv(?!\w)|no\s+visual", raw_part, re.I):
            statuses.append("NV")
        if re.search(r"(?<!\w)voice(?!\w)", raw_part, re.I):
            notes.append("VOICE")
        kind = classify_segment_kind(raw_part, base_kind)
        pilots = infer_segment_pilots(display, seg_assets or assets, seg_systems or systems)
        segments.append(IntelSegment(kind=kind, text=display, systems=unique(seg_systems), assets=unique(seg_assets), pilots=pilots, notes=unique(notes), status=unique(statuses), confidence="high" if kind == "kill" else "medium"))
    if not segments:
        segments.append(IntelSegment(kind="message", text=normalize_feed_text(text), systems=systems, assets=assets))
    return segments


from sb_translation.detect import has_cjk, has_english_letters, has_non_english_signal, pick_google_source_lang


def argos_runtime_status() -> dict:
    """Return safe Argos status without importing Argos in the GUI process.

    Direct Argos integration is currently disabled because the installed runtime
    can hang or take several seconds to import/model-scan. A future Argos add-on
    should do install/probe/translation in a separate managed process.
    """
    status = {
        "runtime": False,
        "models": [],
        "error": "Argos direct integration is disabled pending a safe optional add-on/offline package flow",
    }
    ARGOS_STATUS_CACHE["checked"] = True
    ARGOS_STATUS_CACHE["runtime"] = False
    ARGOS_STATUS_CACHE["models"] = set()
    ARGOS_STATUS_CACHE["error"] = status["error"]
    return status

def format_argos_status() -> str:
    st = argos_runtime_status()
    runtime = "Installed" if st.get("runtime") else "Missing"
    models = set(st.get("models") or [])
    cn_en = "Installed" if "zh->en" in models else "Missing"
    en_cn = "Installed" if "en->zh" in models else "Missing"
    extra = f" | {st.get('error')}" if st.get("error") else ""
    return f"Argos runtime: {runtime}\nCN -> EN model: {cn_en}\nEN -> CN model: {en_cn}{extra}"


def google_translate_free(text: str, source: str = "zh-CN", target: str = "en") -> str | None:
    from sb_translation.google_free import google_translate_free as _google_free
    text = (text or "").strip()
    if not text:
        return None
    key = f"google|{source}|{target}|{text}"
    if key in FREE_TRANSLATION_CACHE:
        return FREE_TRANSLATION_CACHE[key]
    cached = TRANSLATION_CACHE.get(key)
    if cached:
        FREE_TRANSLATION_CACHE[key] = cached
        return cached
    translated = _google_free(text, source=source, target=target, timeout=GOOGLE_TRANSLATE_TIMEOUT)
    if translated:
        FREE_TRANSLATION_CACHE[key] = translated
        # Do not persist here: protected placeholder work is gated higher up.
        return translated
    return None


def argos_pair_ready(source: str, target: str) -> bool:
    # Never import/check Argos from feed redraw or settings redraw. Only trust the
    # status cache populated by Refresh Argos Status or Install/Repair workers.
    if not bool(ARGOS_STATUS_CACHE.get("checked")):
        return False
    if not bool(ARGOS_STATUS_CACHE.get("runtime")):
        return False
    return f"{source}->{target}" in set(ARGOS_STATUS_CACHE.get("models") or [])


def argos_translate_fallback(text: str, source: str = "zh", target: str = "en") -> str | None:
    # Do not import/call Argos in-process. The runtime is currently unsafe in this
    # environment and can hang the Tk UI. Keep Google/curated translation working.
    ARGOS_STATUS_CACHE["checked"] = True
    ARGOS_STATUS_CACHE["runtime"] = False
    ARGOS_STATUS_CACHE["models"] = set()
    ARGOS_STATUS_CACHE["error"] = "Argos direct translation disabled pending safe add-on flow"
    return None

def cjk_translation_source(text: str) -> str:
    """Return the smallest useful source string for CJK translation/cache.

    Live intel often mixes English/EVE context with a short Chinese phrase.
    Cache only the phrase-bearing span so Google/Argos/cache rows are reusable
    and do not include already-English intel words.
    """
    raw = normalize_feed_text(text)
    cjk_re = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
    if not raw or not cjk_re.search(raw):
        return raw
    matches = list(cjk_re.finditer(raw))
    if not matches:
        return raw
    start = matches[0].start()
    end = matches[-1].end()
    # Include adjacent EVE/system tokens directly attached to CJK, e.g. 4H别过YMJG门.
    left = start
    while left > 0 and re.match(r"[A-Za-z0-9_-]", raw[left - 1]):
        left -= 1
    right = end
    while right < len(raw) and re.match(r"[A-Za-z0-9_-]", raw[right]):
        right += 1
    segment = raw[left:right].strip(" \t·|-:,;[]()")
    # If the first CJK phrase is preceded by a pure English intel prefix, discard it.
    # Keep compact attached tokens but do not keep words like gate/red/camp/30+.
    segment = re.sub(r"^(?:gate|red|camp|clear|clr|blue|hostile|neut|neutral|local|fleet|class|on|in|at|from|to|jump|jumping|out|comes?)\b\s*", "", segment, flags=re.I).strip()
    return segment or raw


def translation_source_for_cache(text: str, direction: str) -> str:
    direction = direction or "zh-en"
    if direction == "zh-en":
        return cjk_translation_source(text)
    return normalize_feed_text(text)


def looks_like_translation_pending_source(text: str, direction: str) -> bool:
    """Return true when Translated Only should use a stable pending row.

    This is a display-only guard; it never performs translation.  It prevents a
    non-English row from flashing first and then being replaced by English when
    the background result arrives.
    """
    value = normalize_feed_text(text)
    if not value:
        return False
    direction = direction or "zh-en"
    if direction == "en-zh":
        return bool(re.search(r"[A-Za-z]", value))
    return has_non_english_signal(value)


def looks_like_protected_translation_work(text: str, protected_terms: list[str] | None = None) -> bool:
    """Return True for placeholder/protected-term-only Google work strings."""
    value = normalize_feed_text(text)
    if not value:
        return True
    stripped = HTTP_LINK_RE.sub(" ", value)
    stripped = LINK_RE.sub(" ", stripped)
    stripped = re.sub(r"\bSBX\d+\b", " ", stripped, flags=re.I)
    stripped = COUNT_RE.sub(" ", stripped)
    for term in sorted(unique(protected_terms or []), key=len, reverse=True):
        term_value = normalize_feed_text(term)
        if term_value:
            stripped = re.sub(rf"(?<!\w){re.escape(term_value)}(?!\w)", " ", stripped, flags=re.I)
    stripped = re.sub(r"\b(?:clear|clr|safe|blue only|red|neut|neutral|hostile|local|gate|jump|jumped|camp|ess|no visual|nv)\b", " ", stripped, flags=re.I)
    stripped = re.sub(r"[\s,.;:!?'\"()\[\]{}<>|/\\_-]+", " ", stripped).strip()
    return not stripped


def should_cache_translation_source(source_text: str, direction: str, target_lang: str = "en", engine: str = "", protected_terms: list[str] | None = None) -> bool:
    """Gate persistent machine-cache writes by direction and source language."""
    direction = str(direction or "zh-en")
    target = str(target_lang or "en")
    source = normalize_feed_text(source_text)
    if not source or looks_like_protected_translation_work(source, protected_terms):
        return False
    if HTTP_LINK_RE.fullmatch(source) or LINK_RE.fullmatch(source):
        return False
    if direction == "en-zh" or target.lower().startswith("zh"):
        return has_english_letters(source)
    if direction == "zh-en" or target.lower() == "en":
        return has_non_english_signal(source)
    return has_non_english_signal(source) or has_english_letters(source)


def translation_langs_for_direction(direction: str) -> tuple[str, str, str, str]:
    if direction == "en-zh":
        return "en", "zh-CN", "en", "zh"
    return "auto", "en", "zh", "en"


def translation_engine_order(preferred_engine: str = "auto", fallback_mode: str = "google-argos") -> list[str]:
    pref = str(preferred_engine or "auto").lower()
    fallback = str(fallback_mode or "google-argos").lower()
    if fallback in {"cache-only", "offline-cache"}:
        return []
    if pref == "argos":
        return ["argos"] if fallback == "offline-only" else ["argos", "google"]
    if pref == "google":
        return ["google"] if fallback == "online-only" else ["google", "argos"]
    if fallback == "argos-google":
        return ["argos", "google"]
    if fallback == "offline-only":
        return ["argos"]
    if fallback == "online-only":
        return ["google"]
    return ["google", "argos"]


def translation_cache_lookup(source_text: str, direction: str, preferred_engine: str = "auto", fallback_mode: str = "google-argos") -> tuple[str, str]:
    source, target, _argos_source, _argos_target = translation_langs_for_direction(direction)
    override = TRANSLATION_CACHE.get_override(source_text, target)
    if override:
        return normalize_feed_text(override), "manual-override"
    for engine in translation_engine_order(preferred_engine, fallback_mode):
        hit = TRANSLATION_CACHE.get(TRANSLATION_CACHE.key_for(source_text, source, target, engine))
        if hit:
            return normalize_feed_text(hit), f"cache:{engine}"
    return "", "miss"


def translate_free_text_cached(text: str, systems: list[str], assets: list[str], localized: list[dict], counts: list[str], links: list[str], direction: str = "zh-en", character_names: list[str] | None = None, preferred_engine: str = "auto", fallback_mode: str = "google-argos", cooldown_minutes: int = 60) -> tuple[str, str]:
    direction = direction or "zh-en"
    if direction == "off":
        return "", "off"
    if direction == "zh-en" and not has_non_english_signal(text):
        return "", "not-needed"
    if direction == "en-zh" and not has_english_letters(text):
        return "", "not-needed"
    from sb_translation.protect import reattach_untranslated_source_tokens, restore_protected_translation_tokens
    cache_text = translation_source_for_cache(text, direction)
    cached, label = translation_cache_lookup(cache_text, direction, preferred_engine, fallback_mode)
    if cached:
        # Cache stores CJK-only segments; reattach English names left on the full line.
        return reattach_untranslated_source_tokens(text, cached, cache_text), label
    if str(fallback_mode or "").lower() in {"cache-only", "offline-cache"}:
        return "", "cache-miss-offline"
    source, target, argos_source, argos_target = translation_langs_for_direction(direction)
    override_text, override_changed = apply_phrase_overrides(cache_text, direction)
    if override_changed and direction == "zh-en" and not has_non_english_signal(override_text):
        return reattach_untranslated_source_tokens(text, override_text.strip(), cache_text), "phrase-override"
    protected=[]; work=override_text; terms=[]
    terms.extend(systems); terms.extend(assets); terms.extend(counts); terms.extend(links); terms.extend(HTTP_LINK_RE.findall(text))
    if character_names: terms.extend(character_names)
    # Protect latin tokens still present on the *full* line (not only the CJK cache segment)
    if direction == "zh-en" and text:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9'*.-]{1,}", text))
    terms.extend(re.findall(r"\b\d+(?:\.\d+)?\s*(?:isk|m|mil|b|bil|kk)\b", text, re.I))
    for ent in localized:
        terms.append(ent.get("original", "")); terms.append(ent.get("canonical", ""))
    for idx, term in enumerate(sorted(unique(terms), key=len, reverse=True)):
        if not term or term not in work: continue
        token=f"SBX{idx}"; work=work.replace(term, token); protected.append((token, term))
    protected_terms = [original for _token, original in protected]
    for engine in translation_engine_order(preferred_engine, fallback_mode):
        if TRANSLATION_CACHE.failure_active(cache_text, target, engine):
            continue
        try:
            translated = google_translate_free(work, source=source, target=target) if engine == "google" else argos_translate_fallback(work, source=argos_source, target=argos_target)
        except Exception as exc:
            translated = ""; TRANSLATION_CACHE.record_failure(cache_text, target, engine, f"{type(exc).__name__}: {exc}", cooldown_minutes)
        if not translated:
            TRANSLATION_CACHE.record_failure(cache_text, target, engine, "empty result", cooldown_minutes)
            continue
        # Restore placeholders on the MT segment only; reattach full-line English after cache write
        # so machine cache stays CJK-segment clean (e.g. 能塌吗 -> Can it collapse?).
        mt_out = restore_protected_translation_tokens(translated, protected)
        if mt_out:
            cached_ok = TRANSLATION_CACHE.put_machine(
                cache_text, source, target, mt_out, engine, direction=direction, protected_terms=protected_terms
            )
            display = reattach_untranslated_source_tokens(text, mt_out, cache_text)
            return display, (f"segment:{engine}-cached" if cached_ok else f"segment:{engine}-uncached")
    return "", "fallback-failed"

def translate_free_text(text: str, systems: list[str], assets: list[str], localized: list[dict], counts: list[str], links: list[str], direction: str = "zh-en", character_names: list[str] | None = None, preferred_engine: str = "auto", fallback_mode: str = "google-argos") -> str:
    direction = direction or "zh-en"
    if direction == "off":
        return ""
    if direction == "zh-en":
        if not has_non_english_signal(text):
            return ""
        # CJK uses zh-CN; other non-English uses Google auto-detect (Russian, etc.).
        source, target = pick_google_source_lang(text, "zh-en"), "en"
        argos_source, argos_target = "zh", "en"
    elif direction == "en-zh":
        if not has_english_letters(text):
            return ""
        source, target = "en", "zh-CN"
        argos_source, argos_target = "en", "zh"
    else:
        return ""

    override_text, override_changed = apply_phrase_overrides(text, direction)
    if override_changed and direction == "zh-en" and not has_non_english_signal(override_text):
        return override_text.strip()
    protected: list[tuple[str, str]] = []
    work = override_text
    terms: list[str] = []
    terms.extend(systems)
    terms.extend(assets)
    terms.extend(counts)
    terms.extend(links)
    terms.extend(HTTP_LINK_RE.findall(text))
    if character_names:
        terms.extend(character_names)
    terms.extend(re.findall(r"\b\d+(?:\.\d+)?\s*(?:isk|m|mil|b|bil|kk)\b", text, re.I))
    for ent in localized:
        terms.append(ent.get("original", ""))
        terms.append(ent.get("canonical", ""))
    for idx, term in enumerate(sorted(unique(terms), key=len, reverse=True)):
        if not term or term not in work:
            continue
        token = f"SBX{idx}"
        work = work.replace(term, token)
        protected.append((token, term))
    def via_google():
        return google_translate_free(work, source=source, target=target)
    def via_argos():
        return argos_translate_fallback(work, source=argos_source, target=argos_target)
    preferred_engine = str(preferred_engine or "auto").lower()
    fallback_mode = str(fallback_mode or "google-argos").lower()
    if preferred_engine == "argos":
        engines = [via_argos] if fallback_mode == "offline-only" else [via_argos, via_google]
    elif preferred_engine == "google":
        engines = [via_google] if fallback_mode == "online-only" else [via_google, via_argos]
    elif fallback_mode == "argos-google":
        engines = [via_argos, via_google]
    elif fallback_mode == "offline-only":
        engines = [via_argos]
    elif fallback_mode == "online-only":
        engines = [via_google]
    else:
        engines = [via_google, via_argos]
    translated = None
    for engine in engines:
        translated = engine()
        if translated:
            break
    if not translated:
        return ""
    from sb_translation.protect import reattach_untranslated_source_tokens, restore_protected_translation_tokens
    out = restore_protected_translation_tokens(translated, protected)
    if direction == "zh-en":
        out = reattach_untranslated_source_tokens(text, out, translation_source_for_cache(text, direction))
    return out


def translate_free_chinese_text(text: str, systems: list[str], assets: list[str], localized: list[dict], counts: list[str], links: list[str]) -> str:
    return translate_free_text(text, systems, assets, localized, counts, links, "zh-en")


def parse_rows_from_text(text: str, fallback_channel: str, file_name: str, db: EveDb, allow_free_translation: bool = True) -> list[Row]:
    lines = [x.rstrip("\r") for x in text.splitlines()]
    channel = fallback_channel
    for raw in lines[:24]:
        if m := HEADER_CHANNEL.match(clean(raw)):
            channel = m.group(1).strip() or fallback_channel
            break
    rows: list[Row] = []
    for raw in lines:
        line = clean(raw)
        if is_header(line):
            continue
        if m := LIVE_INLINE.match(line):
            ts, sender, body = m.group(1), clean(m.group(2)), clean(m.group(3))
            if sender.lower() == "eve system" and body.lower().startswith("channel motd:"):
                continue
            systems, assets, localized, counts, links, intent = extract_intel(body, db)
            translation = translate_text(body, localized, intent)
            display_body = translation or body
            segments = build_intel_segments(body, systems, assets, localized, db)
            tmp_row = Row(channel, ts, sender, body, systems, assets, localized, counts, links, intent, translation, "", "none", file_name, [], [], segments)
            msg_candidates = esi_message_candidates_for_row(tmp_row)
            free_translation = translate_free_text(display_body, systems, assets, localized, counts, links, "zh-en", msg_candidates) if allow_free_translation else ""
            rows.append(Row(channel, ts, sender, body, systems, assets, localized, counts, links, intent, translation, free_translation, ("catalog/db+google" if free_translation else "catalog/db" if translation or localized else "none"), file_name, [], msg_candidates, segments))
    return rows


from sb_monitor import MonitorThread as _MonitorThreadImpl


def MonitorThread(outq, stop_event, status, channels, replay_today: bool = False, backlog_minutes: int | None = None):
    """Factory wrapper preserving call sites; logic lives in sb_monitor."""
    minutes = 0
    if backlog_minutes is not None:
        minutes = int(backlog_minutes or 0)
    elif replay_today:
        minutes = 24 * 60
    return _MonitorThreadImpl(
        outq,
        stop_event,
        status,
        channels,
        chatlog_dir=CHATLOG_DIR,
        parse_rows=parse_rows_from_text,
        channel_from_filename=channel_from_filename,
        decode_bytes=decode_bytes,
        make_db=lambda: EveDb(DB_PATH, use_sqlite=False),
        write_log=write_log,
        poll_seconds=POLL_SECONDS,
        max_chunk=MAX_CHUNK,
        backlog_minutes=minutes,
        catalog_loaded=bool(CATALOG.loaded),
        db_exists=bool(DB_PATH.exists()),
    )


# Tab strip colors — Void Tactical (sb_ui.theme); keys kept for existing tab builders.
TAB_THEME = {
    "bar_bg": sb_theme.COLORS["bg"],
    "bar_border": sb_theme.COLORS["border"],
    "tab_bg": sb_theme.COLORS["bg_panel"],
    "tab_fg": sb_theme.COLORS["fg_secondary"],
    "tab_active_bg": sb_theme.COLORS["tab_active_bg"],
    "tab_active_fg": sb_theme.COLORS["fg_bright"],
    "tab_hover_bg": sb_theme.COLORS["bg_elevated"],
    "tab_border": sb_theme.COLORS["border"],
    "tab_active_border": sb_theme.COLORS["accent_line"],
    "tab_unread_bg": sb_theme.COLORS["bg_elevated"],
    "tab_unread_fg": sb_theme.COLORS["fg_bright"],
    "unread_bg": sb_theme.COLORS["accent"],
    "unread_fg": sb_theme.COLORS["fg_bright"],
    "alert_bg": sb_theme.COLORS["error"],
    "close_fg": sb_theme.COLORS["error"],
    "close_hover_bg": "#5c1f28",
    "empty_fg": sb_theme.COLORS["fg_muted"],
    "restore_bg": sb_theme.COLORS["bg_elevated"],
    "restore_fg": sb_theme.COLORS["success"],
}


from sb_appearance import DEFAULT_APPEARANCE, STYLE_TAGS as APPEARANCE_STYLE_TAGS
from sb_appearance import normalize_appearance as _normalize_appearance_pure

APPEARANCE_PRESETS = {
    "Default Dark": {},
    "Soft Dark": {
        "foreground": "#cfd8e3", "background": "#090d12", "highlight_backgrounds": False,
        "system": {"foreground": "#d7bd62", "bold": True, "background": "#26210f"},
        "asset": {"foreground": "#d99a55", "bold": False, "background": "#281f14"},
        "module": {"foreground": "#aa91d9", "bold": False, "background": "#211b2b"},
        "esi": {"foreground": "#dc7777", "bold": True, "background": "#2a1717"},
        "ess": {"foreground": "#74bfd0", "bold": True, "background": "#10252b"},
    },
    "Low Color / Minimal": {
        "highlight_backgrounds": False,
        "system": {"foreground": "#d7dde5", "bold": True, "background": ""},
        "asset": {"foreground": "#d7dde5", "bold": False, "background": ""},
        "module": {"foreground": "#d7dde5", "bold": False, "background": ""},
        "esi": {"foreground": "#d7dde5", "bold": True, "background": ""},
        "ess": {"foreground": "#d7dde5", "bold": True, "background": ""},
    },
    "High Contrast": {
        "foreground": "#ffffff", "background": "#000000", "highlight_backgrounds": True,
        "time": {"foreground": "#b8c7d9", "bold": False, "background": ""},
        "system": {"foreground": "#fff176", "bold": True, "background": "#3a3200"},
        "asset": {"foreground": "#ffb74d", "bold": True, "background": "#3a2400"},
        "module": {"foreground": "#ce93d8", "bold": True, "background": "#311b37"},
        "esi": {"foreground": "#ff8a80", "bold": True, "background": "#3b1111"},
        "ess": {"foreground": "#80deea", "bold": True, "background": "#00343b"},
    },
    "Overlay Transparent": {
        "window_opacity": 0.88, "background": "#05080c", "foreground": "#e3e9f1", "highlight_backgrounds": True,
        "system": {"foreground": "#ffe082", "bold": True, "background": "#2b2509"},
        "asset": {"foreground": "#ffb05f", "bold": True, "background": "#2b1c0b"},
        "module": {"foreground": "#bda4ff", "bold": True, "background": "#211a31"},
        "esi": {"foreground": "#ff7b7b", "bold": True, "background": "#301414"},
        "ess": {"foreground": "#75ddff", "bold": True, "background": "#0b2a36"},
    },
}

STYLE_TAGS = APPEARANCE_STYLE_TAGS


def tab_id_for_channel(channel: str) -> str:
    return channel


def tab_label(tab_id: str) -> str:
    return "All" if tab_id == ALL_CHANNELS_TAB else tab_id


def short_tab_label(label: str, max_chars: int = 28) -> str:
    from sb_text import truncate_label
    return truncate_label(label, max_chars)



def parse_version_tuple(value: str) -> tuple[int, ...]:
    raw = str(value or "").strip().lower().lstrip("v")
    parts = []
    for chunk in re.split(r"[^0-9]+", raw):
        if chunk:
            parts.append(int(chunk))
    return tuple(parts or [0])


def is_newer_version(remote: str, local: str) -> bool:
    r = list(parse_version_tuple(remote))
    l = list(parse_version_tuple(local))
    n = max(len(r), len(l))
    r += [0] * (n - len(r))
    l += [0] * (n - len(l))
    return tuple(r) > tuple(l)

class SignalBridgeGui:
    def __init__(self):
        import tkinter as tk
        from tkinter import messagebox, filedialog
        self.tk = tk
        self.messagebox = messagebox
        self.filedialog = filedialog
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        try:
            ico = APP_DIR / "assets" / "signal_bridge_icon.ico"
            png = APP_DIR / "assets" / "signal_bridge_icon_true_transparent_1024.png"
            if ico.exists():
                self.root.iconbitmap(str(ico))
            # Prefer high-res PNG for title-bar/taskbar where Tk supports it.
            if png.exists():
                try:
                    self._app_icon_photo = self.tk.PhotoImage(file=str(png))
                    self.root.iconphoto(True, self._app_icon_photo)
                except Exception as photo_exc:
                    write_log(f"Root iconphoto failed: {photo_exc}")
        except Exception as exc:
            write_log(f"Root icon failed: {exc}")
        # Mobile-style default: narrow, tall layout suitable for side-panel/overlay use.
        # Users can still resize freely, and their OS/window-manager placement persists normally.
        self.root.geometry("430x720")
        self.root.minsize(360, 420)
        self.root.configure(bg=sb_theme.COLORS["bg"])
        self.always_on_top = tk.BooleanVar(value=bool(SETTINGS.get("always_on_top", True)))
        self.compact = tk.BooleanVar(value=bool(SETTINGS.get("compact_mode", True)))
        # When enabled, DB-localized Chinese ship names are shown as English only.
        # When disabled, original text is shown first with translated text underneath.
        self.translated_only = tk.BooleanVar(value=bool(SETTINGS.get("translated_only", True)))
        self.translate_chinese_text = tk.BooleanVar(value=bool(SETTINGS.get("translate_free_text", True)))
        self.translation_direction = tk.StringVar(value=str(SETTINGS.get("translation_direction", "zh-en")))
        self.translation_preferred_engine = tk.StringVar(value=str(SETTINGS.get("translation_preferred_engine", "auto")))
        self.translation_fallback_mode = tk.StringVar(value=str(SETTINGS.get("translation_fallback_mode", "online-only")))
        self.translation_cache_mode = tk.StringVar(value=str(SETTINGS.get("translation_cache_mode", "cache-first-auto")))
        self.translation_failure_cooldown_minutes = tk.IntVar(value=int(SETTINGS.get("translation_failure_cooldown_minutes", 60) or 60))
        self.argos_status_text = tk.StringVar(value="Argos status: not checked")
        self.appearance = self.normalize_appearance(SETTINGS.get("appearance"))
        self.font_family = tk.StringVar(value=str(self.appearance.get("font_family", SETTINGS.get("font_family", "Segoe UI"))))
        try:
            initial_font_size = int(self.appearance.get("font_size", SETTINGS.get("font_size", 10)))
        except Exception:
            initial_font_size = 10
        self.font_size = tk.IntVar(value=max(8, min(28, initial_font_size)))
        self.show_timestamps = tk.BooleanVar(value=bool(SETTINGS.get("show_timestamps", True)))
        self.show_channel_names = tk.BooleanVar(value=bool(SETTINGS.get("show_channel_names", False)))
        self.show_channel_names_in_all = tk.BooleanVar(value=bool(SETTINGS.get("show_channel_names_in_all", True)))
        self.enable_hyperlinks = tk.BooleanVar(value=bool(SETTINGS.get("enable_hyperlinks", True)))
        self.check_updates_on_start = tk.BooleanVar(value=bool(SETTINGS.get("check_updates_on_start", True)))
        self.esi_settings = load_esi_settings()
        self.esi_enabled = tk.BooleanVar(value=bool(self.esi_settings.get("enabled", False)))
        self.esi_oauth_enabled = tk.BooleanVar(value=bool(self.esi_settings.get("oauth_enabled", False)))
        self.esi_resolver: EsiResolver | None = None
        self.esi_entities: dict[str, dict] = {}
        self.oauth_listener_active = False
        self.root.attributes("-topmost", bool(self.always_on_top.get()))
        self.set_window_opacity(float(self.appearance.get("window_opacity", 1.0)), save=False)
        self.active_channels: set[str] = default_channels()
        self.hidden_tab_ids: set[str] = set(str(x) for x in (SETTINGS.get("hidden_tab_ids") or []))
        self.tab_order: list[str] = [str(x) for x in (SETTINGS.get("tab_order") or [ALL_CHANNELS_TAB])]
        self.unread_counts: dict[str, int] = {}
        self.tab_widgets: dict[str, object] = {}
        self._tab_drag: dict | None = None
        self._tab_drop_target: str | None = None
        self._tab_layout_after = None
        self.visible_channel: str | None = str(SETTINGS.get("active_tab_id") or ALL_CHANNELS_TAB)
        self.normalize_tab_state(prefer_all=True)
        self.queue: queue.Queue = queue.Queue()
        self.translation_queue: queue.Queue = queue.Queue(maxsize=200)
        self.translation_pending: set[tuple[int, str, str]] = set()
        self.translation_stop_event = threading.Event()
        self.stop_event: threading.Event | None = None
        self.monitor: MonitorThread | None = None
        self.row_count = 0
        self.rows: list[Row] = []
        self.rendered_row_map: dict[str, dict] = {}
        self.link_map: dict[str, str] = {}
        self.render_seq = 0
        self.diagnostics: dict = {
            "started_at": time.time(),
            "last_action": "startup",
            "last_action_at": time.time(),
            "last_action_duration_ms": 0,
            "last_status": "",
            "last_redraw_duration_ms": 0,
            "last_redraw_rows": 0,
            "last_visible_rows": 0,
            "redraw_count": 0,
            "last_queue_drain_duration_ms": 0,
            "last_queue_items": 0,
            "last_queue_size": 0,
            "last_ui_heartbeat": time.time(),
            "last_ui_stall": "none",
            "last_ui_stall_seconds": 0,
            "stall_count": 0,
        }
        self._heartbeat_last = time.monotonic()
        self._heartbeat_interval_ms = 500
        self._stall_threshold_seconds = 2.0
        self.intel_history_runtime: AddonRuntime | None = None
        self.intel_history_last_health: dict = {}
        # LAN phone viewer (opt-in; off by default)
        self.lan_enabled = self.tk.BooleanVar(value=bool(SETTINGS.get("lan_enabled", False)))
        self.lan_port = self.tk.IntVar(value=int(SETTINGS.get("lan_port", 8765) or 8765))
        if not str(SETTINGS.get("lan_token") or "").strip():
            SETTINGS["lan_token"] = sb_lan.new_token()
        self.lan_token = str(SETTINGS.get("lan_token") or "")
        self.lan_server = sb_lan.LanServer()
        self.lan_url_var = None
        write_log(f"Starting {APP_NAME} v{APP_VERSION}")
        record_event("app_start", version=APP_VERSION)
        self._build_menu()
        self._build_widgets()
        self.load_enabled_addons()
        if bool(self.lan_enabled.get()):
            try:
                self.start_lan_viewer()
            except Exception as exc:
                write_log("LAN viewer auto-start failed", exc)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.after(150, self.drain_queue)
        threading.Thread(target=self.translation_worker, daemon=True).start()
        self.root.after(self._heartbeat_interval_ms, self.ui_heartbeat)

    def note_action(self, action: str, **data):
        now = time.time()
        self.diagnostics["last_action"] = action
        self.diagnostics["last_action_at"] = now
        if data:
            self.diagnostics["last_action_data"] = data
        record_event("action", action=action, **data)

    def finish_action(self, action: str, started: float, **data):
        duration_ms = int((time.time() - started) * 1000)
        self.diagnostics["last_action"] = action
        self.diagnostics["last_action_duration_ms"] = duration_ms
        record_event("action_done", action=action, duration_ms=duration_ms, **data)

    def ui_heartbeat(self):
        try:
            now = time.monotonic()
            gap = now - getattr(self, "_heartbeat_last", now)
            self._heartbeat_last = now
            self.diagnostics["last_ui_heartbeat"] = time.time()
            if gap > self._stall_threshold_seconds:
                self.diagnostics["stall_count"] = int(self.diagnostics.get("stall_count") or 0) + 1
                self.diagnostics["last_ui_stall_seconds"] = round(gap, 3)
                self.diagnostics["last_ui_stall"] = time.strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    "type": "ui_stall",
                    "duration_seconds": round(gap, 3),
                    "last_action": self.diagnostics.get("last_action", ""),
                    "visible_channel": self.visible_channel,
                    "rows": len(self.rows),
                    "visible_rows": self.diagnostics.get("last_visible_rows", 0),
                    "queue_size": self.queue.qsize() if hasattr(self, "queue") else 0,
                }
                write_jsonl(STALL_LOG_PATH, payload)
                record_event("ui_stall", **{k: v for k, v in payload.items() if k != "type"})
        except Exception as exc:
            write_log("UI heartbeat failed", exc)
        finally:
            try:
                self.root.after(self._heartbeat_interval_ms, self.ui_heartbeat)
            except Exception:
                pass

    def _build_menu(self):
        tk = self.tk
        mc = menu_colors()
        menubar = tk.Menu(self.root, bg=mc["bg"], fg=mc["fg"], tearoff=False)
        file_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        file_menu.add_command(label="Start Monitoring", command=self.start_monitor)
        file_menu.add_command(label="Stop Monitoring", command=self.stop_monitor)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Feed", command=self.clear_feed)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        channels_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        channels_menu.add_command(label="Channel Settings...", command=lambda: self.show_settings_center("Channels"))
        channels_menu.add_command(label="Add / Open Channels...", command=self.choose_channels)
        channels_menu.add_command(label="Restore Hidden Tabs...", command=self.restore_hidden_tabs_dialog)
        channels_menu.add_separator()
        channels_menu.add_command(label="Close All Active Channels", command=self.close_selected_channels)
        menubar.add_cascade(label="Channels", menu=channels_menu)

        # Pilot Intel first-class (v0.7 product IA).
        pilot_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        pilot_menu.add_command(label="Pilot Intel Settings...", command=lambda: self.show_settings_center("Pilot Intel"))
        pilot_menu.add_command(label="Recognition Rules...", command=lambda: self.show_settings_center("Recognition Rules"))
        pilot_menu.add_command(label="Add-ons (package)...", command=lambda: self.show_settings_center("Add-ons"))
        pilot_menu.add_separator()
        pilot_menu.add_command(label="Help: Pilot Info...", command=lambda: self.show_help_center("Pilot Info"))
        menubar.add_cascade(label="Pilot Intel", menu=pilot_menu)

        settings_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        settings_menu.add_command(label="Settings...", command=self.show_settings_center)
        settings_menu.add_separator()
        settings_menu.add_command(label="Appearance...", command=lambda: self.show_settings_center("Appearance"))
        settings_menu.add_command(label="Aliases...", command=lambda: self.show_settings_center("Aliases"))
        settings_menu.add_command(label="ESI...", command=lambda: self.show_settings_center("ESI"))
        settings_menu.add_command(label="Recognition Rules...", command=lambda: self.show_settings_center("Recognition Rules"))
        settings_menu.add_command(label="Add-ons...", command=lambda: self.show_settings_center("Add-ons"))
        menubar.add_cascade(label="Settings", menu=settings_menu)

        view_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        view_menu.add_checkbutton(label="Always on Top", variable=self.always_on_top, command=self.apply_topmost)
        view_menu.add_checkbutton(label="Show Timestamps", variable=self.show_timestamps, command=self.persist_and_redraw)
        view_menu.add_checkbutton(label="Show Channel Names", variable=self.show_channel_names, command=self.persist_and_redraw)
        view_menu.add_separator()
        view_menu.add_command(label="Appearance Settings...", command=lambda: self.show_settings_center("Appearance"))
        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        tools_menu.add_command(label="Manual ESI Character Check...", command=self.manual_esi_check_dialog)
        tools_menu.add_command(label="Copy Diagnostics", command=self.copy_diagnostics)
        tools_menu.add_command(label="Open Logs Folder", command=self.open_logs_folder)
        tools_menu.add_command(label="Open Chatlog Folder", command=self.open_folder)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=False, bg=mc["bg"], fg=mc["fg"])
        help_menu.add_command(label="Help Topics...", command=self.show_help_center)
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=lambda: self.check_for_updates(manual=True))
        help_menu.add_command(label="Report an Issue...", command=lambda: webbrowser.open(ISSUE_REPORT_URL))
        help_menu.add_separator()
        help_menu.add_command(label="About Signal Bridge...", command=self.show_about_window)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_widgets(self):
        layout = build_main_layout(self.root, create_feed=True, feed_font=self.feed_font())
        chrome = build_header_bar(
            layout.header_host,
            title=f"{APP_NAME} v{APP_VERSION}",
            status="Idle",
        )
        chrome.frame.pack(fill="x")
        self.title_label = chrome.title_label
        self.mode_label = chrome.mode_label
        self.status_label = self.tk.Label(
            layout.footer_host,
            text="Idle",
            bg=sb_theme.COLORS["bg_chrome"],
            fg=sb_theme.COLORS["fg_muted"],
            anchor="w",
            font=sb_theme.mono_font(9),
            padx=sb_theme.SPACING["sm"],
            pady=sb_theme.SPACING["xs"],
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.mode_label.configure(text="LIVE FEED")
        self.mode_label.pack(side="left")
        # Color legend intentionally hidden; colors are documented in Help/About.

        self.tab_bar = layout.tabs_host
        self.tab_strip = TabStrip(
            self.tab_bar,
            on_select=self.select_tab,
            on_close=self.hide_tab,
            on_close_others=self.hide_other_tabs,
            on_close_all=self.close_selected_channels,
            on_copy=self.copy_to_clipboard,
            on_restore_hidden=self.restore_hidden_tabs_dialog,
            max_visible=6,
        )
        self.tab_strip.pack(fill="x")
        self.tab_bar.bind("<Configure>", self.on_tab_bar_configure)
        self.update_channel_tabs()

        self.text = layout.feed_text
        self.configure_feed_tags()
        self.text.bind("<Button-3>", self.show_feed_context_menu)
        self.text.configure(state="disabled")

    def _tab_state(self) -> TabStripState:
        return TabStripState(
            order=list(self.tab_order),
            active_id=self.visible_channel,
            hidden=set(self.hidden_tab_ids),
            unread=dict(self.unread_counts),
        )

    def _apply_tab_state(self, state: TabStripState) -> None:
        self.tab_order = list(state.order)
        self.visible_channel = state.active_id
        self.hidden_tab_ids = set(state.hidden)
        self.unread_counts = dict(state.unread)

    def normalize_tab_state(self, prefer_all: bool = False):
        state = sb_tabs.normalize(
            self._tab_state(),
            set(self.active_channels),
            prefer_all=prefer_all,
        )
        self._apply_tab_state(state)

    def visible_tabs(self) -> list[str]:
        infos = sb_tabs.visible_tabs(self._tab_state(), set(self.active_channels))
        return [t.tab_id for t in infos]

    def on_tab_bar_configure(self, _event=None):
        # Real tab strip is pack-managed; width changes may adjust overflow later.
        return

    def tab_style(self, active: bool = False, unread: bool = False) -> dict:
        bg = TAB_THEME["tab_active_bg"] if active else (TAB_THEME["tab_unread_bg"] if unread else TAB_THEME["tab_bg"])
        return {
            "bg": bg,
            "fg": TAB_THEME["tab_active_fg"] if active else (TAB_THEME["tab_unread_fg"] if unread else TAB_THEME["tab_fg"]),
            "activebackground": TAB_THEME["tab_hover_bg"],
            "activeforeground": TAB_THEME["tab_active_fg"],
            "border": TAB_THEME["tab_active_border"] if active else TAB_THEME["tab_border"],
        }

    def tab_display_text(self, tab_id: str, max_chars: int = 28) -> str:
        label = short_tab_label(tab_label(tab_id), max_chars=max_chars)
        unread = self.unread_counts.get(tab_id, 0)
        if unread:
            suffix = str(unread) if unread < 100 else "99+"
            return f"{label} *{suffix}"
        return label

    def update_channel_tabs(self):
        self.normalize_tab_state(prefer_all=True)
        infos = sb_tabs.visible_tabs(self._tab_state(), set(self.active_channels))
        hidden = sb_tabs.hidden_count(self._tab_state(), set(self.active_channels))
        self.tab_strip.set_tabs(
            infos,
            self.visible_channel,
            hidden_count=hidden,
        )
        self.tab_widgets = dict(self.tab_strip._widgets)

    def set_tab_hover(self, tab_id: str, hover: bool):
        return

    def layout_tab_widgets(self):
        return

    def select_tab(self, tab_id: str):
        state = sb_tabs.select_tab(self._tab_state(), tab_id, set(self.active_channels))
        self._apply_tab_state(state)
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()

    def select_channel_tab(self, channel: str):
        self.select_tab(channel)

    def select_all_channels_tab(self):
        self.select_tab(ALL_CHANNELS_TAB)

    def hide_tab(self, tab_id: str):
        state = sb_tabs.close_tab(self._tab_state(), tab_id, set(self.active_channels))
        self._apply_tab_state(state)
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()
        self.set_status(f"Hidden tab: {tab_label(tab_id)}")

    def close_channel(self, channel: str):
        self.hide_tab(channel)

    def restore_tab(self, tab_id: str, focus: bool = False):
        if tab_id != ALL_CHANNELS_TAB and tab_id not in self.active_channels:
            self.active_channels.add(tab_id)
        state = sb_tabs.restore_tab(
            self._tab_state(),
            tab_id,
            set(self.active_channels),
            focus=focus,
        )
        self._apply_tab_state(state)
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()

    def restore_last_hidden_tab(self):
        valid_hidden = [t for t in self.tab_order if t in self.hidden_tab_ids and (t == ALL_CHANNELS_TAB or t in self.active_channels)]
        if not valid_hidden:
            self.set_status("No hidden tabs to restore")
            return
        self.restore_tab(valid_hidden[-1], focus=False)
        self.set_status(f"Restored tab: {tab_label(valid_hidden[-1])}")

    def restore_hidden_tabs_dialog(self):
        tk = self.tk
        hidden = [t for t in self.tab_order if t in self.hidden_tab_ids and (t == ALL_CHANNELS_TAB or t in self.active_channels)]
        if not hidden:
            self.messagebox.showinfo("Restore Hidden Tabs", "No hidden tabs.")
            return
        win = tk.Toplevel(self.root)
        self.polish_window(
            win,
            width=360,
            height=420,
            minsize=(320, 340),
            modal=True,
            title="Restore Hidden Tabs",
        )
        tk.Label(win, text="Select tabs to restore", **sb_theme.label_kw(),
                 font=sb_theme.font(10, bold=True)).pack(anchor="w", padx=10, pady=(10, 4))
        lb = tk.Listbox(win, selectmode="extended", activestyle="none",
                        **sb_theme.listbox_kw())
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for tab_id in hidden:
            lb.insert("end", tab_label(tab_id))
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        btns.pack(fill="x", padx=10, pady=8)
        def restore_selected():
            chosen = [hidden[i] for i in lb.curselection()]
            for tab_id in chosen:
                self.hidden_tab_ids.discard(tab_id)
            if not self.visible_channel and chosen:
                self.visible_channel = chosen[0]
            self.update_channel_tabs(); self.persist_settings(); self.redraw_feed(); win.destroy()
        def restore_all():
            for tab_id in hidden:
                self.hidden_tab_ids.discard(tab_id)
            if not self.visible_channel and hidden:
                self.visible_channel = hidden[0]
            self.update_channel_tabs(); self.persist_settings(); self.redraw_feed(); win.destroy()
        selected = sb_components.primary_button(btns, "Restore Selected", restore_selected)
        selected.pack(side="left", padx=(0, 6))
        sb_components.action_button(btns, "Restore All", restore_all)
        tk.Button(btns, text="Cancel", command=win.destroy,
                  **sb_theme.btn_secondary_kw()).pack(side="right")

    def show_tab_context_menu(self, event, tab_id: str):
        from sb_ui.tabs.menu import build_tab_context_menu, popup_menu
        menu = build_tab_context_menu(
            self.root,
            tab_id,
            on_close=self.hide_tab,
            on_close_others=self.hide_other_tabs,
            on_close_all=self.close_selected_channels,
            on_copy=self.copy_to_clipboard,
            on_restore_hidden=self.restore_hidden_tabs_dialog,
        )
        popup_menu(menu, event)

    def copy_to_clipboard(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status("Copied")

    def hide_other_tabs(self, keep_tab_id: str):
        state = sb_tabs.close_others(self._tab_state(), keep_tab_id, set(self.active_channels))
        self._apply_tab_state(state)
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()

    def begin_tab_drag(self, event, tab_id: str):
        self._tab_drag = {"tab_id": tab_id, "start_x": event.x_root, "start_y": event.y_root, "moved": False}

    def move_tab_drag(self, event):
        if not self._tab_drag:
            return
        if abs(event.x_root - self._tab_drag["start_x"]) + abs(event.y_root - self._tab_drag["start_y"]) > 8:
            self._tab_drag["moved"] = True
            target = self.tab_at_screen_xy(event.x_root, event.y_root)
            if target != self._tab_drop_target:
                self._tab_drop_target = target
                self.update_channel_tabs()

    def end_tab_drag(self, event):
        drag = self._tab_drag
        self._tab_drag = None
        self._tab_drop_target = None
        if not drag or not drag.get("moved"):
            return
        tab_id = drag["tab_id"]
        target = self.tab_at_screen_xy(event.x_root, event.y_root)
        if not target or target == tab_id:
            self.update_channel_tabs()
            return
        visible = self.visible_tabs()
        if tab_id not in visible or target not in visible:
            return
        visible.remove(tab_id)
        visible.insert(visible.index(target), tab_id)
        self.tab_order = visible + [t for t in self.tab_order if t not in visible]
        self.update_channel_tabs(); self.persist_settings()

    def tab_at_screen_xy(self, x: int, y: int) -> str | None:
        for tab_id, widget in self.tab_widgets.items():
            if tab_id in ("__empty__", "__restore__"):
                continue
            try:
                wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
                ww, wh = widget.winfo_width(), widget.winfo_height()
                if wx <= x <= wx + ww and wy <= y <= wy + wh:
                    return tab_id
            except Exception:
                pass
        return None

    def channel_title(self) -> str:
        if not self.active_channels:
            return "No channels selected"
        return f"{len(self.active_channels)} active channel(s), {len(self.hidden_tab_ids)} hidden tab(s)"

    def channel_catalog(self) -> dict[str, dict]:
        return sb_channels.build_channel_catalog(
            chatlog_dir=CHATLOG_DIR,
            active_channels=set(self.active_channels),
            hidden_tab_ids=set(self.hidden_tab_ids),
            tab_order=list(self.tab_order),
            all_channels_tab=ALL_CHANNELS_TAB,
        )

    def refresh_channel_status(self):
        catalog = self.channel_catalog()
        summary = sb_channels.catalog_summary(catalog)
        record_event("channel_catalog_summary", **summary)
        self.set_status(
            f"Channels: {summary['tracking']} tracking, {summary['discovered']} discovered, "
            f"{summary['waiting']} waiting for log, {summary['hidden']} hidden"
        )

    def choose_channels(self):
        tk = self.tk
        catalog = self.channel_catalog()
        order = sorted(catalog, key=lambda c: (0 if catalog[c].get("active") else 1 if catalog[c].get("discovered") else 2, -int(catalog[c].get("last_seen_ns") or 0), channel_sort_key(c)))
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=620, height=600, minsize=(520, 420), modal=True, title="Choose / Open Chat Channels")
        tk.Label(win, text="Choose / Open Chat Channels", **sb_theme.label_kw(),
                 font=sb_theme.font(11, bold=True)).pack(anchor="w", padx=10, pady=(10, 2))
        tk.Label(win, text="Active channels are selected. Saved channels remain listed even if no current chatlog is available, so you do not have to re-add them after restart.", **sb_theme.label_kw(muted=True), font=sb_theme.font(9), wraplength=580, justify="left").pack(anchor="w", padx=10, pady=(0, 6))
        lb = tk.Listbox(win, selectmode="extended", activestyle="none",
                        **sb_theme.listbox_kw())
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for idx, channel in enumerate(order):
            info = catalog[channel]
            status = str(info.get("status") or "")
            latest = str(info.get("latest_file") or "")
            suffix = f" - {status}"
            if latest:
                suffix += f" - {latest}"
            marker = "* " if info.get("active") else "  "
            lb.insert("end", marker + channel + suffix)
            if info.get("active"):
                lb.selection_set(idx)
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        btns.pack(fill="x", padx=10, pady=8)
        def selected_channels():
            return {order[i] for i in lb.curselection()}
        def add_selected():
            selected = selected_channels()
            if selected:
                self.add_channels(selected, manual=True)
            win.destroy()
        def replace_selection():
            selected = selected_channels()
            self.set_channels(selected, manual=True, clear_existing=True)
            win.destroy()
        def select_all():
            lb.selection_set(0, "end")
        def select_none():
            lb.selection_clear(0, "end")
        tk.Button(btns, text="Add / Keep Selected", command=add_selected,
                  **sb_theme.btn_secondary_kw()).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Replace Active", command=replace_selection,
                  **sb_theme.btn_secondary_kw()).pack(side="left", padx=6)
        tk.Button(btns, text="All", command=select_all,
                  **sb_theme.btn_secondary_kw()).pack(side="left", padx=6)
        tk.Button(btns, text="None", command=select_none,
                  **sb_theme.btn_secondary_kw()).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=win.destroy,
                  **sb_theme.btn_secondary_kw()).pack(side="right")

    def add_channels(self, channels: set[str], manual: bool = False):
        channels = {normalize_channel_name(c) for c in channels if normalize_channel_name(c)}
        if not channels:
            self.set_status("No channels selected")
            return
        self.set_channels(self.active_channels | channels, manual=manual, clear_existing=False)

    def set_channels(self, channels: set[str], manual: bool = False, clear_existing: bool = False):
        old_channels = set(self.active_channels)
        self.active_channels = {normalize_channel_name(c) for c in channels if normalize_channel_name(c)}
        added = self.active_channels - old_channels
        removed = old_channels - self.active_channels
        self.hidden_tab_ids -= removed
        self.unread_counts = {k: v for k, v in self.unread_counts.items() if k == ALL_CHANNELS_TAB or k in self.active_channels}
        if manual:
            for channel in self.active_channels:
                self.hidden_tab_ids.discard(channel)
        self.normalize_tab_state(prefer_all=True)
        self.title_label.configure(text=f"{APP_NAME} v{APP_VERSION}")
        self.update_channel_tabs()
        self.persist_settings()
        if clear_existing or removed:
            self.clear_feed()
        self.stop_monitor()
        if self.active_channels:
            self.start_monitor()
            if added and not removed and not clear_existing:
                self.set_status(f"Added {len(added)} channel(s); monitoring {len(self.active_channels)}")
        else:
            self.set_status("No channels selected")

    def close_selected_channels(self):
        self.set_channels(set(), manual=True, clear_existing=True)

    def app_icon_path(self):
        path = APP_DIR / "assets" / "signal_bridge_icon.ico"
        return path if path.exists() else None

    def polish_window(self, win, parent=None, *, width=None, height=None, minsize=None, modal=False,
                      center=True, title=None, placement=None, preserve_position=False):
        """Apply consistent Signal Bridge chrome, icon, stacking, and placement to child windows."""
        return sb_windows.polish_window(
            win, parent or self.root, width=width, height=height, minsize=minsize,
            modal=modal, center=center, title=title,
            icon_path=self.app_icon_path(), log=write_log, placement=placement,
            preserve_position=preserve_position,
        )

    def friendly_datetime(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "unknown"
        import datetime as _dt
        candidates = []
        cleaned = raw.replace("T", " ").replace("Z", "").strip()
        candidates.append(cleaned)
        candidates.append(cleaned.replace(".", "-", 2))
        parsed = None
        for item in candidates:
            for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M"):
                try:
                    parsed = _dt.datetime.strptime(item[:19], fmt)
                    break
                except Exception:
                    pass
            if parsed:
                break
        if not parsed:
            return raw
        now = _dt.datetime.now()
        date = parsed.date()
        if date == now.date():
            prefix = "Today"
        elif date == (now.date() - _dt.timedelta(days=1)):
            prefix = "Yesterday"
        elif parsed.year == now.year:
            prefix = parsed.strftime("%d %B").lstrip("0")
        else:
            prefix = parsed.strftime("%d %B %Y").lstrip("0")
        hour = parsed.strftime("%I").lstrip("0") or "0"
        minute = parsed.strftime("%M")
        ampm = parsed.strftime("%p").lower()
        return f"{prefix} {hour}:{minute}{ampm}"

    def card_frame(self, parent, bg="#121a24", border="#1f2f42", padx=9, pady=8):
        outer = self.tk.Frame(parent, bg=border, padx=1, pady=1)
        outer.pack(fill="x", padx=8, pady=6)
        inner = self.tk.Frame(outer, bg=bg, padx=padx, pady=pady)
        inner.pack(fill="x")
        return inner

    def schedule_redraw(self, delay_ms: int = 80):
        """Coalesce expensive redraw requests so toggles do not block repeatedly."""
        if hasattr(self, "_redraw_after") and self._redraw_after:
            try:
                self.root.after_cancel(self._redraw_after)
            except Exception:
                pass
        def run():
            self._redraw_after = None
            try:
                self.redraw_feed()
            except Exception as exc:
                write_log(f"Scheduled redraw failed: {exc}")
        self._redraw_after = self.root.after(delay_ms, run)

    def feed_at_bottom(self, threshold: float = 0.02) -> bool:
        try:
            _first, last = self.text.yview()
            return last >= (1.0 - threshold)
        except Exception:
            return True

    def restore_feed_scroll(self, was_at_bottom: bool, first_fraction: float = 1.0):
        try:
            if was_at_bottom:
                self.text.see("end")
            else:
                self.text.yview_moveto(max(0.0, min(1.0, first_fraction)))
        except Exception:
            pass

    def persist_and_schedule_redraw(self):
        self.persist_settings()
        self.set_status("Updating display...")
        self.schedule_redraw()

    def is_all_channels_view(self) -> bool:
        return self.visible_channel == ALL_CHANNELS_TAB

    def normalize_appearance(self, raw=None):
        def merge(base, extra):
            out = copy.deepcopy(base)
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if isinstance(v, dict) and isinstance(out.get(k), dict):
                        out[k].update(v)
                    else:
                        out[k] = v
            return out
        appearance = _normalize_appearance_pure(None, settings=SETTINGS)
        if isinstance(raw, dict):
            preset = raw.get("preset")
            if preset in APPEARANCE_PRESETS:
                appearance = merge(appearance, APPEARANCE_PRESETS[preset])
            appearance = merge(appearance, raw)
            if "highlight_modules" not in raw:
                appearance["highlight_modules"] = False
        appearance = _normalize_appearance_pure(appearance, settings=SETTINGS)
        return appearance

    def feed_font(self, bold: bool = False):
        weight = "bold" if bold else "normal"
        return (self.font_family.get() or "Segoe UI", int(self.font_size.get()), weight)

    def tag_font(self, tag: str):
        style = self.appearance.get(tag, {}) if isinstance(self.appearance, dict) else {}
        return self.feed_font(bold=bool(style.get("bold", False)))

    def safe_color(self, value: str, fallback: str) -> str:
        try:
            self.root.winfo_rgb(str(value))
            return str(value)
        except Exception:
            return fallback

    def tag_options(self, tag: str):
        style = self.appearance.get(tag, {}) if isinstance(self.appearance, dict) else {}
        default = DEFAULT_APPEARANCE.get(tag, {})
        opts = {
            "foreground": self.safe_color(style.get("foreground", default.get("foreground", "#d7dde5")), default.get("foreground", "#d7dde5")),
            "font": self.tag_font(tag),
        }
        bg = str(style.get("background", "") or "")
        if bool(self.appearance.get("highlight_backgrounds", False)) and bg:
            opts["background"] = self.safe_color(bg, "")
        else:
            opts["background"] = ""
        if tag == "link":
            opts["underline"] = bool(style.get("underline", True))
        return opts

    def configure_feed_tags(self):
        bg = self.safe_color(
            self.appearance.get("background", default_feed_background()),
            default_feed_background(),
        )
        fg = self.safe_color(
            self.appearance.get("foreground", default_feed_foreground()),
            default_feed_foreground(),
        )
        apply_base_feed_colors(self.text, bg=bg, fg=fg, font=self.feed_font())
        for tag in STYLE_TAGS:
            self.text.tag_configure(tag, **self.tag_options(tag))
        self.text.tag_configure("translation_subline", **translated_subline_options())
        for tag in ("time", "sender", "system", "asset", "module", "ess", "link", "esi", "error"):
            try:
                self.text.tag_raise(tag)
            except Exception:
                pass

    def apply_appearance(self, redraw: bool = False, save: bool = True):
        self.appearance["font_family"] = self.font_family.get() or "Segoe UI"
        self.appearance["font_size"] = int(self.font_size.get())
        self.appearance = self.normalize_appearance(self.appearance)
        if hasattr(self, "text"):
            self.configure_feed_tags()
        self.set_window_opacity(float(self.appearance.get("window_opacity", 1.0)), save=False)
        if save:
            self.persist_settings()
        if redraw and hasattr(self, "text"):
            self.redraw_feed()

    def apply_feed_font(self):
        self.apply_appearance(redraw=True, save=True)

    def adjust_font_size(self, delta: int):
        current = int(self.font_size.get())
        self.font_size.set(max(8, min(28, current + delta)))
        self.appearance["font_size"] = int(self.font_size.get())
        self.apply_feed_font()

    def choose_font(self):
        tk = self.tk
        try:
            import tkinter.font as tkfont
            families = sorted(set(tkfont.families(self.root)))
        except Exception:
            families = ["Segoe UI", "Aptos", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Courier New"]
        common = [f for f in ["Segoe UI", "Aptos", "Arial", "Verdana", "Tahoma", "Calibri", "Segoe UI Variable", "Consolas", "Cascadia Mono", "Courier New"] if f in families]
        ordered = common + [f for f in families if f not in common]
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=420, height=520, minsize=(360, 420), modal=True, title="Choose Feed Font")
        tk.Label(win, text="Feed font", **sb_theme.label_kw(), font=sb_theme.font(10, bold=True)).pack(anchor="w", padx=10, pady=(10, 4))
        lb = tk.Listbox(win, activestyle="none", **sb_theme.listbox_kw())
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        current_index = 0
        for idx, fam in enumerate(ordered):
            lb.insert("end", fam)
            if fam == self.font_family.get():
                current_index = idx
        if ordered:
            lb.selection_set(current_index)
            lb.see(current_index)
        controls = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        controls.pack(fill="x", padx=10, pady=6)
        tk.Label(controls, text="Size:", **sb_theme.label_kw(muted=True)).pack(side="left")
        size_spin = tk.Spinbox(controls, from_=8, to=28, width=5, textvariable=self.font_size, **sb_theme.entry_kw())
        size_spin.pack(side="left", padx=6)
        preview = tk.Label(win, text="Preview: 4-HWWF Loki ESS", bg=sb_theme.COLORS["bg_input"], fg=sb_theme.COLORS["fg"], padx=8, pady=8)
        preview.pack(fill="x", padx=10, pady=6)
        def update_preview(*_):
            fam = ordered[lb.curselection()[0]] if lb.curselection() and ordered else self.font_family.get()
            try:
                sz = int(size_spin.get())
            except Exception:
                sz = int(self.font_size.get())
            preview.configure(font=(fam, sz))
        lb.bind("<<ListboxSelect>>", update_preview)
        size_spin.configure(command=update_preview)
        update_preview()
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        btns.pack(fill="x", padx=10, pady=8)
        def apply_selection():
            if lb.curselection() and ordered:
                self.font_family.set(ordered[lb.curselection()[0]])
            try:
                self.font_size.set(max(8, min(28, int(size_spin.get()))))
            except Exception:
                pass
            self.appearance["font_family"] = self.font_family.get()
            self.appearance["font_size"] = int(self.font_size.get())
            self.apply_feed_font()
            win.destroy()
        tk.Button(btns, text="Apply", command=apply_selection).pack(side="left")
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    def set_window_opacity(self, value: float, save: bool = True):
        try:
            value = max(0.55, min(1.0, float(value)))
        except Exception:
            value = 1.0
        if hasattr(self, "appearance"):
            self.appearance["window_opacity"] = value
        try:
            self.root.attributes("-alpha", value)
        except Exception:
            pass
        if save and hasattr(self, "text"):
            self.persist_settings()

    def apply_appearance_preset(self, preset_name: str):
        base = copy.deepcopy(DEFAULT_APPEARANCE)
        preset = APPEARANCE_PRESETS.get(preset_name, {})
        def merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    dst[k].update(v)
                else:
                    dst[k] = copy.deepcopy(v)
            return dst
        self.appearance = merge(base, preset)
        self.appearance["preset"] = preset_name
        self.font_family.set(str(self.appearance.get("font_family", "Segoe UI")))
        self.font_size.set(int(self.appearance.get("font_size", 10)))
        self.apply_appearance(redraw=False, save=True)

    def settings_summary_text(self) -> str:
        count, hits = TRANSLATION_CACHE.stats()
        esi_stats = ESI_CACHE.stats()
        last_check = ESI_CACHE.get_status().get("last_check") or "none"
        diag = dict(getattr(self, "diagnostics", {}) or {})
        uptime = int(time.time() - float(diag.get("started_at") or time.time()))
        queue_size = self.queue.qsize() if hasattr(self, "queue") else 0
        return (
            f"Signal Bridge v{APP_VERSION}\n"
            f"Uptime: {uptime}s\n"
            f"Chatlogs: {CHATLOG_DIR}\n"
            f"Chatlogs exists: {CHATLOG_DIR.exists()}\n"
            f"Active channels: {len(self.active_channels)} | Hidden: {len(self.hidden_tab_ids)} | Visible: {self.visible_channel}\n"
            f"Rows in memory: {len(self.rows)} | Last visible rows: {diag.get('last_visible_rows', 0)}\n"
            f"Last action: {diag.get('last_action', 'unknown')} | duration: {diag.get('last_action_duration_ms', 0)}ms\n"
            f"Last status: {diag.get('last_status', '')}\n"
            f"UI stalls: {diag.get('stall_count', 0)} | Last stall: {diag.get('last_ui_stall', 'none')} ({diag.get('last_ui_stall_seconds', 0)}s)\n"
            f"Last redraw: {diag.get('last_redraw_duration_ms', 0)}ms | rows rendered: {diag.get('last_redraw_rows', 0)} | redraws: {diag.get('redraw_count', 0)}\n"
            f"Queue: size={queue_size} | last drain={diag.get('last_queue_drain_duration_ms', 0)}ms | items={diag.get('last_queue_items', 0)}\n"
            f"Discovered channels: {len(discover_channels())}\n"
            f"Catalog: {CATALOG.version} | loaded={CATALOG.loaded} | counts={CATALOG.counts()}\n"
            f"Translation cache: {count} entries, {hits} hits\n"
            f"Translation: preferred={self.translation_preferred_engine.get()} fallback={self.translation_fallback_mode.get()} free_text={bool(self.translate_chinese_text.get())}\n"
            f"Argos: disabled direct runtime path; status={self.argos_status_text.get()}\n"
            f"ESI enabled: {bool(self.esi_enabled.get())} | cache={esi_stats}\n"
            f"Last ESI check: {last_check}\n"
            f"Intel History add-on: {self.intel_history_status_label()}\n"
            f"Clickable hyperlinks: {bool(self.enable_hyperlinks.get())}\n"
            f"Config: {CONFIG_PATH}\n"
            f"Logs: {LOG_PATH}\n"
            f"Events: {EVENT_LOG_PATH}\n"
            f"Errors: {ERROR_LOG_PATH}\n"
            f"Stalls: {STALL_LOG_PATH}\n"
            f"Live-only/no-backfill: replay_on_start=False"
        )

    def copy_diagnostics(self):
        self.note_action("copy_diagnostics")
        self.copy_to_clipboard(self.settings_summary_text())
        self.set_status("Diagnostics copied")
        record_event("diagnostics_copied")

    def load_enabled_addons(self):
        status = installed_addon_status(INTEL_HISTORY_ADDON_ID)
        if not status.get("enabled"):
            return
        try:
            runtime = AddonRuntime(INTEL_HISTORY_ADDON_ID, status.get("manifest") or {}, addon_code_dir(INTEL_HISTORY_ADDON_ID), addon_data_dir(INTEL_HISTORY_ADDON_ID))
            runtime.start()
            self.intel_history_runtime = runtime
            self.intel_history_last_health = runtime.health()
            write_log(f"Loaded add-on {INTEL_HISTORY_ADDON_ID} {runtime.manifest.get('version','unknown')}")
        except Exception as exc:
            write_log("Intel History add-on load failed", exc)
            self.intel_history_runtime = None
            self.intel_history_last_health = {"last_error": f"load {type(exc).__name__}: {exc}"}
            try:
                self.status_label.configure(text="Intel History add-on failed to load; see logs")
            except Exception:
                pass

    def unload_intel_history_addon(self):
        if self.intel_history_runtime:
            self.intel_history_runtime.shutdown()
            self.intel_history_runtime = None

    def reload_intel_history_addon(self):
        self.unload_intel_history_addon()
        self.load_enabled_addons()

    def emit_intel_history_row(self, row: Row):
        runtime = self.intel_history_runtime
        if not runtime or not runtime.enabled:
            return
        try:
            event = make_intel_history_event(row)
            if event.get("characters"):
                runtime.safe_call("on_intel_row", event)
        except Exception as exc:
            write_log("Intel History event emit failed", exc)

    def current_intel_history_health(self) -> dict:
        runtime = self.intel_history_runtime
        if runtime and runtime.enabled:
            health = runtime.health()
            if isinstance(health, dict):
                self.intel_history_last_health = health
        return dict(self.intel_history_last_health or {})

    def intel_history_status(self) -> dict:
        return installed_addon_status(INTEL_HISTORY_ADDON_ID)

    def intel_history_status_label(self) -> str:
        status = self.intel_history_status()
        manifest = status.get("manifest") or {}
        if not status.get("installed"):
            return "not installed"
        version = manifest.get("version") or "unknown"
        runtime = self.intel_history_runtime
        if status.get("enabled") and runtime and runtime.enabled:
            return f"enabled/running v{version}"
        if status.get("enabled"):
            return f"enabled, not running v{version}"
        return f"installed, disabled v{version}"

    def open_intel_history_data_folder(self):
        path = addon_data_dir(INTEL_HISTORY_ADDON_ID)
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(path))
        except Exception as exc:
            write_log("Open Intel History data folder failed", exc)
            self.messagebox.showwarning("Intel History", f"Could not open folder:\n{path}\n\n{exc}")

    def set_intel_history_enabled(self, enabled: bool):
        status = self.intel_history_status()
        if enabled and not status.get("installed"):
            self.messagebox.showinfo("Intel History", "Intel History is not installed yet. Install the official add-on ZIP first.")
            set_addon_enabled(INTEL_HISTORY_ADDON_ID, False)
            self.set_status("Intel History is not installed")
            return
        set_addon_enabled(INTEL_HISTORY_ADDON_ID, bool(enabled))
        if enabled:
            self.reload_intel_history_addon()
        else:
            self.unload_intel_history_addon()
        self.set_status(f"Intel History {'enabled' if enabled else 'disabled'}")

    def install_intel_history_addon_from_file(self):
        path = self.filedialog.askopenfilename(title="Install Intel History Add-on", filetypes=[("Signal Bridge add-on ZIP", "*.zip"), ("All files", "*.*")])
        if not path:
            return
        try:
            manifest = install_intel_history_addon_zip(Path(path))
            set_addon_enabled(INTEL_HISTORY_ADDON_ID, False)
            self.messagebox.showinfo("Intel History Installed", f"Installed {manifest.get('name') or INTEL_HISTORY_ADDON_NAME}\nVersion: {manifest.get('version') or 'unknown'}\n\nEnable it from Settings > Add-ons when ready.")
            self.set_status("Intel History add-on installed")
        except Exception as exc:
            write_log("Intel History add-on install failed", exc)
            self.messagebox.showwarning("Intel History Install Failed", str(exc)[:1000])
            self.set_status("Intel History add-on install failed")

    def uninstall_intel_history_addon_code(self):
        status = self.intel_history_status()
        if not status.get("installed"):
            self.messagebox.showinfo("Intel History", "Intel History is not installed.")
            return
        ok = self.messagebox.askyesno("Uninstall Intel History", "Remove the Intel History add-on code?\n\nLocal Intel History data will be kept.\n\nContinue?")
        if not ok:
            return
        try:
            self.unload_intel_history_addon()
            set_addon_enabled(INTEL_HISTORY_ADDON_ID, False)
            shutil.rmtree(addon_code_dir(INTEL_HISTORY_ADDON_ID), ignore_errors=True)
            self.set_status("Intel History add-on code removed; data kept")
            self.messagebox.showinfo("Intel History", "Intel History add-on code was removed. Local data was kept.")
        except Exception as exc:
            write_log("Intel History uninstall failed", exc)
            self.messagebox.showwarning("Intel History", f"Uninstall failed:\n{exc}")

    def show_intel_history_details(self):
        status = self.intel_history_status()
        manifest = status.get("manifest") or {}
        health = self.current_intel_history_health()
        text = (
            f"{INTEL_HISTORY_ADDON_NAME}\n\n"
            f"Status: {self.intel_history_status_label()}\n"
            f"Installed: {status.get('installed')}\n"
            f"Enabled: {status.get('enabled')}\n"
            f"Version: {manifest.get('version') or 'n/a'}\n"
            f"Compatible app: {manifest.get('compatible_app') or 'n/a'}\n\n"
            f"Code folder:\n{status.get('code_dir')}\n\n"
            f"Data folder:\n{status.get('data_dir')}\n\n"
            f"Health:\n{json.dumps(health, indent=2, ensure_ascii=False)}\n\n"
            "MVP capabilities:\n"
            "- ESI-confirmed pilot sighting capture\n"
            "- SQLite storage under user_data/modules/intel-history\n"
            "- 3-minute dedupe buckets\n"
            "- Basic health/status counters\n\n"
            "Planned next capabilities:\n"
            "- Pilot Intelligence Cards\n"
            "- Manual and auto flags\n"
            "- zKill enrichment\n"
            "- Intel import/export packs\n"
            "- Read-only Intel Query Service for future LLM use"
        )
        self.messagebox.showinfo("Intel History Add-on", text)

    def show_alias_editor(self):
        self.show_settings_center("Aliases")

    def _render_settings_filters(self, body, shell):
        import uuid
        from sb_ui import filters_page as sb_filters_page
        tk = self.tk
        spam_vars = {
            "enabled": tk.BooleanVar(value=bool(SETTINGS.get("spam_control_enabled", True))),
            "local_only": tk.BooleanVar(value=bool(SETTINGS.get("spam_local_channels_only", True))),
            "ascii": tk.BooleanVar(value=bool(SETTINGS.get("spam_ascii_art_filter", True))),
        }
        spam_spin_vars = {
            "max_per_min": tk.IntVar(value=int(SETTINGS.get("spam_per_channel_max_per_minute", 30) or 30)),
            "repeat_window": tk.IntVar(value=int(SETTINGS.get("spam_repeat_sender_window_seconds", 8) or 8)),
            "repeat_max": tk.IntVar(value=int(SETTINGS.get("spam_repeat_sender_max", 3) or 3)),
        }

        def list_lines():
            lines = []
            for f in self._feed_filters():
                state = "on" if f.enabled else "off"
                lines.append(f"[{state}] {f.kind}: {f.pattern} ({f.match_mode})")
            return lines

        def add_kind(kind: str):
            title = "Keyword" if kind == "keyword" else "Sender"
            value = self.simple_prompt(f"Add {title} filter", f"{title} to filter:")
            if not value:
                return
            filters = self._feed_filters()
            filters.append(FeedFilter(id=uuid.uuid4().hex[:12], kind=kind, pattern=value.strip(), enabled=True))
            SETTINGS["feed_filters"] = filters_to_settings(filters)
            save_settings(SETTINGS)

        def remove_selected(selection):
            if not selection:
                return
            filters = self._feed_filters()
            idx = int(selection[0])
            if 0 <= idx < len(filters):
                filters.pop(idx)
                SETTINGS["feed_filters"] = filters_to_settings(filters)
                save_settings(SETTINGS)

        sb_filters_page.render_filters_page(
            body,
            tk=tk,
            filters_var_list=None,
            spam_vars=spam_vars,
            spam_spin_vars=spam_spin_vars,
            on_add_keyword=lambda: add_kind("keyword"),
            on_add_sender=lambda: add_kind("sender"),
            on_remove_selected=remove_selected,
            on_reload_list=list_lines,
        )

        def apply_spam():
            SETTINGS["spam_control_enabled"] = bool(spam_vars["enabled"].get())
            SETTINGS["spam_local_channels_only"] = bool(spam_vars["local_only"].get())
            SETTINGS["spam_ascii_art_filter"] = bool(spam_vars["ascii"].get())
            SETTINGS["spam_per_channel_max_per_minute"] = max(5, min(200, int(spam_spin_vars["max_per_min"].get() or 30)))
            SETTINGS["spam_repeat_sender_window_seconds"] = max(2, min(120, int(spam_spin_vars["repeat_window"].get() or 8)))
            SETTINGS["spam_repeat_sender_max"] = max(1, min(50, int(spam_spin_vars["repeat_max"].get() or 3)))
            save_settings(SETTINGS)
            self._spam_limiter()  # refresh policy
            shell.set_status("Filters and spam settings saved.")

        shell.set_apply_handler(apply_spam)

    def simple_prompt(self, title: str, prompt: str) -> str:
        tk = self.tk
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=420, height=160, minsize=(360, 140), modal=True, title=title)
        result = {"value": ""}
        tk.Label(win, text=prompt, **sb_theme.label_kw()).pack(anchor="w", padx=10, pady=(10, 4))
        entry = tk.Entry(win, **sb_theme.entry_kw())
        entry.pack(fill="x", padx=10, pady=4)
        entry.focus_set()
        def ok():
            result["value"] = entry.get().strip()
            win.destroy()
        def cancel():
            result["value"] = ""
            win.destroy()
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        btns.pack(fill="x", padx=10, pady=8)
        sb_components.primary_button(btns, "OK", command=ok).pack(side="right")
        sb_components.action_button(btns, "Cancel", command=cancel).pack(side="right", padx=(0, 6))
        win.bind("<Return>", lambda e: ok())
        win.wait_window()
        return result["value"]

    def _render_settings_general(self, body, shell):
        c = sb_components.card(body, "App Behavior", "Window and feed display options used every session.")
        sb_components.check(c, "Always on top", self.always_on_top, self.apply_topmost)
        sb_components.check(c, "Compact mode", self.compact, self.persist_settings)
        sb_components.check(c, "Check for updates on launch", self.check_updates_on_start, self.persist_settings)
        sb_components.check(c, "Show timestamps", self.show_timestamps, self.persist_and_redraw)
        sb_components.check(c, "Show channel names in feed", self.show_channel_names, self.persist_and_redraw)
        sb_components.check(c, "Show channel names in All", self.show_channel_names_in_all, self.persist_and_redraw)
        sb_components.check(c, "Enable clickable hyperlinks", self.enable_hyperlinks, self.persist_and_redraw)

        bl = sb_components.card(
            body,
            "Startup backlog",
            "Default is live-only (no history on Start Monitoring). Enable only when you want recent chat backfilled first.",
        )
        self.replay_on_start_var = self.tk.BooleanVar(value=bool(SETTINGS.get("replay_on_start", False)))
        self.backlog_minutes_var = self.tk.IntVar(value=int(SETTINGS.get("backlog_minutes", 10) or 10))
        sb_components.check(bl, "Ingest recent backlog on Start Monitoring", self.replay_on_start_var, self.persist_settings)
        sb_components.labeled_spinbox(bl, "Backlog window (minutes):", self.backlog_minutes_var, from_=1, to=360)

        c2 = sb_components.card(body, "Folders", "Chatlog folder is required for monitoring. App and logs folders help troubleshooting.")
        r = sb_components.action_row(c2)
        sb_components.action_button(r, "Choose Chatlog Folder...", self.choose_chatlog_folder)
        sb_components.action_button(r, "Open App Folder", self.open_app_folder)
        sb_components.action_button(r, "Open Logs Folder", self.open_logs_folder)
        sb_components.info_label(c2, f"Current chatlogs: {CHATLOG_DIR}", muted=True)

    def _render_settings_channels(self, body, shell):
        c = sb_components.card(
            body,
            "Channels",
            "Add channels without replacing existing ones. Hidden channels stay hidden until restored. Saved channels wait for new log files after restart.",
        )
        catalog = self.channel_catalog()
        discovered_count = len([x for x in catalog.values() if x.get("discovered")])
        waiting_count = len([x for x in catalog.values() if x.get("active") and not x.get("discovered")])
        sb_components.info_label(
            c,
            f"Tracking: {len(self.active_channels)} | Discovered: {discovered_count} | "
            f"Waiting for log: {waiting_count} | Hidden: {len(self.hidden_tab_ids)}",
        )
        sb_components.info_label(c, f"Visible tab: {self.visible_channel}", muted=True)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Add / Open Channels...", self.choose_channels)
        sb_components.action_button(r, "Restore Hidden Tabs...", self.restore_hidden_tabs_dialog)
        sb_components.action_button(r, "Refresh Status", self.refresh_channel_status)
        danger = sb_components.danger_card(
            body,
            "Stop tracking",
            "Close All Active clears the tracking set. Channels can be re-added from discovery.",
        )
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Close All Active", self.close_selected_channels)

    def _render_settings_appearance(self, body, shell):
        c = sb_components.card(
            body,
            "Appearance",
            "Fonts, colors, opacity, and presets. Purple module highlighting is off by default for new installs.",
        )
        sb_components.info_label(c, f"Font: {self.font_family.get()} {int(self.font_size.get())}")
        modules_on = bool(self.appearance.get("highlight_modules", False)) if isinstance(self.appearance, dict) else False
        sb_components.info_label(
            c,
            f"Preset: {self.appearance.get('preset', 'Default Dark')} | "
            f"Opacity: {int(float(self.appearance.get('window_opacity', 1.0))*100)}% | "
            f"Module purple: {'on' if modules_on else 'off'}",
            muted=True,
        )
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Open Appearance Editor...", self.show_appearance_dialog)
        sb_components.action_button(r, "Increase Font", lambda: self.adjust_font_size(1))
        sb_components.action_button(r, "Decrease Font", lambda: self.adjust_font_size(-1))

    def _render_settings_catalog(self, body, shell):
        c = sb_components.card(
            body,
            "Status",
            "Compact bundled catalog for systems, ships, assets, aliases, and protected terms on the live path.",
        )
        sb_components.info_label(c, f"Loaded: {'yes' if CATALOG.loaded else 'no'} | Version: {CATALOG.version}")
        sb_components.info_label(c, f"Counts: {CATALOG.counts()}", muted=True)
        sb_components.info_label(c, f"Path: {CATALOG_PATH}", muted=True)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Check for Updates", self.check_catalog_updates)
        sb_components.action_button(r, "Health Status", self.show_health)
        r2 = sb_components.action_row(c)
        sb_components.action_button(r2, "Edit Aliases…", lambda: shell.render_page("Aliases"))
        danger = sb_components.danger_card(
            body,
            "Restore previous catalog",
            "Replaces the active catalog with the last backup if one exists. Live recognition may change until the next update.",
        )
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Restore Previous Catalog", self.restore_previous_catalog)

    def _render_settings_esi(self, body, shell):
        c = sb_components.card(
            body,
            "Recognition",
            "Optional cache-first background ESI. Live monitoring works with ESI off. Network work never runs on the render path.",
        )
        sb_components.check(c, "Enable public ESI entity recognition", self.esi_enabled, self.save_esi_ui_settings)
        sb_components.check(c, "Enable OAuth features", self.esi_oauth_enabled, self.save_esi_ui_settings)
        stats = ESI_CACHE.stats()
        status = ESI_CACHE.get_status()
        sb_components.info_label(
            c,
            f"Recognition: {'on' if self.esi_enabled.get() else 'off'} | "
            f"OAuth: {'on' if self.esi_oauth_enabled.get() else 'off'}",
        )
        sb_components.info_label(
            c,
            f"Entities: {stats.get('entities', 0)} | Corrections: {stats.get('corrections', 0)} | "
            f"Negative: {stats.get('negative', 0)} | Last check: {status.get('last_check') or 'none'}",
            muted=True,
        )
        r = sb_components.action_row(c)
        sb_components.action_button(r, "ESI / OAuth Settings…", self.show_esi_settings)
        sb_components.action_button(r, "Manual Character Check…", self.manual_esi_check_dialog)
        r2 = sb_components.action_row(c)
        sb_components.action_button(r2, "ESI Diagnostics", self.show_esi_diagnostics)
        sb_components.action_button(r2, "Recognition Rules…", lambda: shell.render_page("Recognition Rules"))
        danger = sb_components.danger_card(
            body,
            "Clear ESI cache",
            "Removes cached entity lookups. Recognition Rules and OAuth tokens are not deleted here.",
        )
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Clear ESI Cache", self.clear_esi_cache)

    def _render_settings_exclusions(self, body, shell):
        c = sb_components.card(
            body,
            "Recognition Rules",
            "Scoped rules: ignored pilots, highlight exclusions, and parser noise words. Feed keyword/sender filters live under Filters.",
        )
        try:
            pilot_rules = ESI_CACHE.list_exclusion_rules("pilot_ignore")
            highlight_rules = ESI_CACHE.list_exclusion_rules("highlight_exclude")
            noise_rules = ESI_CACHE.list_exclusion_rules("noise_word")
        except Exception:
            pilot_rules, highlight_rules, noise_rules = [], [], []
        sb_components.info_label(
            c,
            f"Ignored pilots: {len(pilot_rules)} | Highlight exclusions: {len(highlight_rules)} | Noise words: {len(noise_rules)}",
        )
        sample = ", ".join((x.get("text") or "") for x in (pilot_rules + highlight_rules + noise_rules)[:12])
        if sample:
            more = len(pilot_rules) + len(highlight_rules) + len(noise_rules) > 12
            sb_components.info_label(c, sample + ("…" if more else ""), muted=True)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Open Recognition Rules...", self.show_esi_exclusion_list)

    def _render_settings_cache_data(self, body, shell):
        c = sb_components.card(
            body,
            "Starter & local data",
            "Bundled starter files seed new installs. Local caches grow while you use the app.",
        )
        count, hits = TRANSLATION_CACHE.stats()
        sb_components.info_label(c, f"Starter recognition rules: {DEFAULT_RECOGNITION_RULES_PATH.exists()} ({DEFAULT_RECOGNITION_RULES_PATH.name})")
        sb_components.info_label(c, f"Starter ESI entities: {DEFAULT_ESI_ENTITIES_PATH.exists()} ({DEFAULT_ESI_ENTITIES_PATH.name})")
        default_translation_cache_path = DATA_DIR / "default_translation_cache.json"
        sb_components.info_label(c, f"Starter translation cache: {default_translation_cache_path.exists()} ({default_translation_cache_path.name})")
        sb_components.info_label(c, f"Local translation cache: {count} entries, {hits} hits", muted=True)
        sb_components.info_label(c, f"Local ESI cache: {ESI_CACHE.stats()}", muted=True)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Open App Folder", self.open_app_folder)
        sb_components.action_button(r, "Open Logs Folder", self.open_logs_folder)

        danger = sb_components.danger_card(
            body,
            "Clear caches",
            "Clearing caches does not delete aliases, Recognition Rules, or manual translation corrections that live in overrides.",
        )
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Clear Translation Cache", self.clear_translation_cache)
        sb_components.action_button(dr, "Clear ESI Cache", self.clear_esi_cache)

    def _render_settings_diagnostics(self, body, shell):
        tk = self.tk
        c = sb_components.card(
            body,
            "Diagnostics",
            "Copy this when reporting bugs. Stalls, slow redraws, and errors also go to JSONL logs.",
        )
        txt = tk.Text(c, height=14, **sb_theme.text_kw())
        txt.pack(fill="both", expand=True, pady=4)
        txt.insert("1.0", self.settings_summary_text())
        txt.configure(state="disabled")
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Copy Diagnostics", self.copy_diagnostics)
        sb_components.action_button(r, "Open Logs Folder", self.open_logs_folder)
        sb_components.action_button(r, "Health Dialog", self.show_health)

    def _render_settings_about(self, body, shell):
        c = sb_components.card(body, "About / Support")
        sb_components.info_label(c, f"Signal Bridge v{APP_VERSION}")
        sb_components.info_label(
            c, "Version details, links, update check, and donation info "
               "live in the About window.", muted=True)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "About & Support...", self.show_about_window)
        sb_components.action_button(r, "Help Topics...", self.show_help_center)

    def _render_settings_translation(self, body, shell):
        tk = self.tk
        c = sb_components.card(
            body,
            "Display",
            "Redraw never blocks on network or offline MT. Free translation runs in the background.",
        )
        sb_components.check(c, "Translated only", self.translated_only, self.persist_and_schedule_redraw)
        sb_components.check(c, "Translate free text", self.translate_chinese_text, self.persist_and_schedule_redraw)
        rr = sb_components.action_row(c)
        tk.Radiobutton(
            rr, text="Auto -> EN", variable=self.translation_direction, value="zh-en",
            command=self.persist_and_schedule_redraw, **sb_theme.radio_kw(),
        ).pack(side="left", padx=(0, 10))
        tk.Radiobutton(
            rr, text="EN -> CN", variable=self.translation_direction, value="en-zh",
            command=self.persist_and_schedule_redraw, **sb_theme.radio_kw(),
        ).pack(side="left")
        sb_components.info_label(c, "Auto → EN uses Chinese when CJK is present, otherwise Google auto-detect for other non-English text.", muted=True)

        c_engine = sb_components.card(
            body,
            "Engine & cache",
            "Google is the default online engine. Argos remains optional/offline and safety-gated.",
        )
        sb_components.info_label(c_engine, "Preferred engine")
        opt1 = tk.OptionMenu(
            c_engine, self.translation_preferred_engine, "auto", "argos", "google",
            command=lambda _=None: self.save_translation_engine_settings(),
        )
        opt1.configure(**sb_theme.optionmenu_kw())
        opt1.pack(anchor="w", pady=(0, 4))
        sb_components.info_label(c_engine, "Cache mode")
        opt0 = tk.OptionMenu(
            c_engine, self.translation_cache_mode, "cache-first-auto", "cache-only",
            command=lambda _=None: self.save_translation_engine_settings(),
        )
        opt0.configure(**sb_theme.optionmenu_kw())
        opt0.pack(anchor="w", pady=(0, 4))
        sb_components.info_label(c_engine, "Fallback mode")
        opt2 = tk.OptionMenu(
            c_engine, self.translation_fallback_mode,
            "online-only", "google-argos", "argos-google", "offline-only", "cache-only",
            command=lambda _=None: self.save_translation_engine_settings(),
        )
        opt2.configure(**sb_theme.optionmenu_kw())
        opt2.pack(anchor="w", pady=(0, 4))
        tk.Label(
            c_engine, textvariable=self.argos_status_text, wraplength=640, justify="left",
            **sb_theme.label_kw(muted=True),
        ).pack(anchor="w", fill="x", pady=2)
        count, hits = TRANSLATION_CACHE.stats()
        sb_components.info_label(c_engine, f"Translation cache: {count} entries, {hits} hits", muted=True)
        r = sb_components.action_row(c_engine)
        sb_components.action_button(r, "Refresh Argos Status", self.refresh_argos_status)
        sb_components.action_button(r, "Install / Repair Argos", self.install_argos_models)
        sb_components.action_button(r, "Test Translation", self.test_translation_engine)
        r2 = sb_components.action_row(c_engine)
        sb_components.action_button(r2, "Open Translation Corrections…", lambda: shell.render_page("Translation Cache"))
        sb_components.action_button(r2, "Cache Status", self.show_translation_cache)
        sb_components.action_button(r2, "Open Phrase Overrides", self.open_phrase_overrides)
        danger = sb_components.danger_card(body, "Clear translation cache", "Machine cache only; manual corrections are preserved by the cleaner path.")
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Clear Cache", self.clear_translation_cache)

    def _render_settings_translation_cache(self, body, shell):
        tk = self.tk
        c = sb_components.card(body, "Translation Corrections", "Fix what appears in chat. Manual corrections override automatic translation.")
        count, hits = TRANSLATION_CACHE.stats(); overrides = TRANSLATION_CACHE.override_count()
        # Keep the raw SQLite path out of the normal correction workflow; diagnostics/cache pages expose it when needed.

        state = {"items": [], "selected_index": None, "autosave_after": None, "loading": False, "saving": False}
        original_filter = tk.StringVar()
        translated_filter = tk.StringVar()
        target_var = tk.StringVar(value="en")
        enabled_var = tk.BooleanVar(value=True)
        note_var = tk.StringVar()
        status_var = tk.StringVar(value="Select a row, edit the English correction, and it auto-saves.")
        show_internals_var = tk.BooleanVar(value=False)
        advanced_visible_var = tk.BooleanVar(value=False)

        meta = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        meta.pack(fill="x", pady=(0, 8))
        for pill in (f"Cache {count}", f"Hits {hits}", f"Manual {overrides}", f"Mode {self.translation_cache_mode.get()}"):
            tk.Label(meta, text=pill, bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_muted"], padx=8, pady=2).pack(side="left", padx=(0, 6))

        toolbar = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        toolbar.pack(fill="x", pady=(0, 8))
        primary_buttons = tk.Frame(toolbar, bg=sb_theme.COLORS["bg"])
        primary_buttons.pack(side="left", anchor="w")
        maintenance_buttons = tk.Frame(toolbar, bg=sb_theme.COLORS["bg"])
        maintenance_buttons.pack(side="right", anchor="e")

        instruction = tk.Label(
            c,
            text="Workflow: choose a grouped translation, correct the English text, and let auto-save update the live feed.",
            anchor="w", justify="left", wraplength=680, **sb_theme.label_kw(muted=True),
        )
        instruction.pack(anchor="w", fill="x", pady=(0, 6))

        advanced_settings = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        advanced_actions = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        def toggle_advanced_settings():
            if advanced_visible_var.get():
                advanced_settings.pack(fill="x", pady=(0, 6), before=instruction)
                advanced_actions.pack(fill="x", pady=(0, 8), before=instruction)
            else:
                advanced_settings.pack_forget()
                advanced_actions.pack_forget()
        tk.Checkbutton(
            maintenance_buttons,
            text="Advanced settings",
            variable=advanced_visible_var,
            command=toggle_advanced_settings,
            **sb_theme.check_kw(),
        ).pack(side="left", padx=(0, 6))

        tk.Label(advanced_settings, text="Mode", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(0,4))
        tk.OptionMenu(advanced_settings, self.translation_cache_mode, "cache-first-auto", "cache-only", command=lambda _=None: self.save_translation_engine_settings()).pack(side="left", padx=(0,8))
        tk.Label(advanced_settings, text="Fallback", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(0,4))
        tk.OptionMenu(advanced_settings, self.translation_fallback_mode, "online-only", "google-argos", "argos-google", "offline-only", "cache-only", command=lambda _=None: self.save_translation_engine_settings()).pack(side="left", padx=(0,8))
        tk.Label(advanced_settings, text="Failure cooldown min", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(0,4))
        tk.Spinbox(advanced_settings, from_=5, to=1440, increment=5, textvariable=self.translation_failure_cooldown_minutes, width=6, command=self.save_translation_engine_settings, bg=sb_theme.COLORS["bg_input"], fg=sb_theme.COLORS["fg"], insertbackground=sb_theme.COLORS["fg_bright"]).pack(side="left", padx=(0,8))
        tk.Checkbutton(advanced_settings, text="Show cache internals", variable=show_internals_var, command=lambda: refresh_rows(keep_selection=True), **sb_theme.check_kw()).pack(side="left", padx=6)

        filters = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        filters.pack(fill="x", pady=(0, 4))
        tk.Label(filters, text="Find original", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(0, 4))
        tk.Entry(filters, textvariable=original_filter, width=24, **sb_theme.entry_kw()).pack(side="left", padx=(0, 12))
        tk.Label(filters, text="Find English", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(0, 4))
        tk.Entry(filters, textvariable=translated_filter, width=24, **sb_theme.entry_kw()).pack(side="left")

        table_frame, tree = sb_components.preview_table(
            c, [("original", "Original"), ("english", "English")], height=9)
        table_frame.pack(fill="both", expand=True, pady=(2, 8))

        editor = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        editor.pack(fill="x", pady=(0, 6))
        editor.grid_columnconfigure(0, weight=2)
        editor.grid_columnconfigure(1, weight=3)
        tk.Label(editor, text="Original / source phrase", font=sb_theme.font(9, bold=True),
                 bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["warning"]).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(4, 2))
        tk.Label(editor, text="English correction (primary)", font=sb_theme.font(10, bold=True),
                 bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["success"]).grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(4, 2))
        src_text = tk.Text(editor, height=4, **sb_theme.text_kw())
        src_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6), ipady=3)
        dst_text = tk.Text(editor, height=4, **sb_theme.text_kw())
        dst_text.grid(row=1, column=1, sticky="nsew", padx=(6, 0), ipady=3)
        tk.Label(editor, text="Use only if the captured source segment is wrong.",
                 anchor="w", **sb_theme.label_kw(muted=True)).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(2, 0))
        tk.Label(editor, text="Edit this text to fix what appears in live chat.",
                 anchor="w", **sb_theme.label_kw(muted=True)).grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(2, 0))

        opts = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        opts.pack(fill="x", pady=(0, 6))
        tk.Label(opts, text="Target", **sb_theme.label_kw(muted=True)).pack(side="left")
        tk.OptionMenu(opts, target_var, "en", "zh-CN", command=lambda _=None: schedule_autosave()).pack(side="left", padx=6)
        tk.Checkbutton(opts, text="Enabled", variable=enabled_var, command=lambda: schedule_autosave(), **sb_theme.check_kw()).pack(side="left", padx=6)
        tk.Label(opts, text="Note", **sb_theme.label_kw(muted=True)).pack(side="left", padx=(10, 2))
        tk.Entry(opts, textvariable=note_var, **sb_theme.entry_kw()).pack(side="left", fill="x", expand=True, padx=6)
        tk.Label(c, textvariable=status_var, anchor="w", justify="left", wraplength=680, **sb_theme.label_kw(muted=True)).pack(anchor="w", fill="x", pady=(2, 0))

        def preview(text, n=64):
            text = str(text or "").replace("\r", " ").replace("\n", " ").strip()
            return text[:n-1] + "…" if len(text) > n else text

        def set_text(widget, value):
            state["loading"] = True
            widget.delete("1.0", "end"); widget.insert("1.0", str(value or ""))
            state["loading"] = False

        def get_text(widget):
            return widget.get("1.0", "end").strip()

        def selected_item():
            idx = state.get("selected_index")
            if idx is None or idx < 0 or idx >= len(state["items"]):
                return None
            return state["items"][idx]

        def refresh_rows(keep_selection=True):
            old_src = get_text(src_text) if keep_selection else ""
            src_filter = original_filter.get().strip().casefold()
            dst_filter = translated_filter.get().strip().casefold()
            rows = TRANSLATION_CACHE.grouped_entries(src_filter, dst_filter, 250)
            state["items"] = rows
            tree.delete(*tree.get_children())
            for i, item in enumerate(rows):
                if show_internals_var.get():
                    prefix = "M" if item.get("manual_id") else "C"
                    dup = int(item.get("duplicate_count") or 1)
                    meta_tag = f" d{dup}" if dup > 1 else ""
                    orig_label = f"[{prefix}{meta_tag}] {preview(item.get('source_text'))}"
                else:
                    orig_label = preview(item.get('source_text'))
                tree.insert("", "end", iid=str(i),
                            values=(orig_label, preview(item.get("translated_text"))))
            new_idx = None
            if keep_selection and old_src:
                for i, item in enumerate(rows):
                    if str(item.get("source_text") or "") == old_src:
                        new_idx = i; break
            state["selected_index"] = new_idx
            if new_idx is not None:
                tree.selection_set(str(new_idx)); tree.see(str(new_idx))
            hidden = sum(max(0, int(r.get("duplicate_count") or 1) - 1) for r in rows)
            status_var.set(f"Showing {len(rows)} grouped row(s). Hidden duplicate records: {hidden}. Manual edits auto-save as overrides.")

        def select_index(idx):
            if idx is None or idx < 0 or idx >= len(state["items"]):
                return
            state["selected_index"] = idx
            tree.selection_set(str(idx)); tree.see(str(idx))
            item = state["items"][idx]
            set_text(src_text, item.get("source_text") or "")
            set_text(dst_text, item.get("translated_text") or "")
            target_var.set(str(item.get("target_lang") or "en"))
            enabled_var.set(bool(item.get("enabled", True)))
            note_var.set(str(item.get("note") or ""))
            status_var.set(f"Editing selected row. Type in the English correction box to save a manual override. Source: {item.get('winning_kind','cache')}; duplicates hidden: {max(0, int(item.get('duplicate_count') or 1)-1)}; engines: {item.get('engines','')}")

        def on_select(_event=None):
            sel = tree.selection()
            if sel:
                try:
                    select_index(int(sel[0]))
                except (ValueError, tk.TclError):
                    pass

        tree.bind("<<TreeviewSelect>>", on_select)

        def save_now():
            state["autosave_after"] = None
            if state.get("loading") or state.get("saving"):
                return
            source = get_text(src_text); translated = get_text(dst_text)
            if not source or not translated:
                status_var.set("Source and translated text are required before auto-save."); return
            item = selected_item()
            override_id = item.get("manual_id") if item and item.get("manual_id") else None
            state["saving"] = True
            oid = TRANSLATION_CACHE.save_override(source, translated, target_var.get(), "auto" if target_var.get()=="en" else "en", note_var.get(), enabled_var.get(), override_id)
            state["saving"] = False
            if not oid:
                status_var.set("Auto-save failed: source and translation are required."); return
            FREE_TRANSLATION_CACHE.clear()
            if item:
                item.update({"kind":"manual", "manual_id": oid, "id": oid, "source_text": source, "normalized_source": TRANSLATION_CACHE.normalize_source(source), "translated_text": translated, "target_lang": target_var.get(), "enabled": enabled_var.get(), "note": note_var.get(), "winning_kind": "manual"})
            status_var.set("Saved manual override. Feed update scheduled.")
            self.set_status("Manual translation override saved")
            self.schedule_redraw(80)
            refresh_rows(keep_selection=True)

        def schedule_autosave(event=None):
            if state.get("loading") or state.get("saving"):
                return
            if state.get("autosave_after"):
                try: c.after_cancel(state["autosave_after"])
                except Exception: pass
            state["autosave_after"] = c.after(700, save_now)
            status_var.set("Editing... auto-save pending")

        def live_filter(*_args):
            if state.get("autosave_after"):
                try: c.after_cancel(state["autosave_after"])
                except Exception: pass
                state["autosave_after"] = None
            refresh_rows(keep_selection=True)

        src_text.bind("<KeyRelease>", schedule_autosave)
        dst_text.bind("<KeyRelease>", schedule_autosave)
        note_var.trace_add("write", lambda *_: schedule_autosave())
        original_filter.trace_add("write", live_filter)
        translated_filter.trace_add("write", live_filter)

        def clean_duplicate_rows():
            protected_terms = []
            try:
                protected_terms.extend(CATALOG.systems.values())
                protected_terms.extend(CATALOG.ship_names.values())
                protected_terms.extend(BUILTIN_ASSETS)
                protected_terms.extend([str(x.get("original") or "") for x in USER_ALIASES])
                protected_terms.extend([str(x.get("canonical") or "") for x in USER_ALIASES])
                protected_terms.extend([str(e.get("name") or "") for e in ESI_CACHE.list_entities("character", limit=2000)])
            except Exception as exc:
                write_log("Translation protected-term cleanup list failed", exc)
            dup_removed = TRANSLATION_CACHE.cleanup_duplicate_machine_rows(False)
            invalid_removed = TRANSLATION_CACHE.cleanup_invalid_auto_en_rows(False, protected_terms=protected_terms)
            mixed_removed = TRANSLATION_CACHE.cleanup_polluted_mixed_rows(False)
            status_var.set(f"Cleaned {dup_removed} duplicate cache record(s), {invalid_removed} invalid Auto -> EN source row(s), and {mixed_removed} mixed-source row(s). Manual overrides were not deleted.")
            self.set_status(f"Cleaned translation cache: {dup_removed} duplicates, {invalid_removed} invalid, {mixed_removed} mixed")
            refresh_rows(False)

        sb_components.action_button(primary_buttons, "New correction", lambda: (state.update({"selected_index": None}), tree.selection_remove(tree.selection()), set_text(src_text, ""), set_text(dst_text, ""), note_var.set(""), enabled_var.set(True), target_var.set("en"), status_var.set("New correction: enter Original on the left and English on the right; it will auto-save.")))
        sb_components.action_button(primary_buttons, "Save now", save_now)
        def delete_selected():
            item = selected_item()
            if not item:
                status_var.set("Select a row before deleting."); return
            source = str(item.get("normalized_source") or item.get("source_text") or "")
            target = str(item.get("target_lang") or target_var.get() or "en")
            if not source:
                status_var.set("Selected row has no source key to delete."); return
            msg = "Delete this grouped translation entry?\n\nThis removes the manual override, machine-cache rows, and failure cooldowns for the selected source/target."
            if self.messagebox.askyesno("Translation Cache", msg):
                result = TRANSLATION_CACHE.delete_grouped_entry(source, target)
                FREE_TRANSLATION_CACHE.clear(); self.schedule_redraw(80); refresh_rows(keep_selection=False)
                status_var.set(f"Deleted selected entry: {result.get('overrides',0)} override(s), {result.get('cache',0)} cache row(s), {result.get('failures',0)} cooldown(s).")
                self.set_status("Translation cache entry deleted")

        def clear_all_translation_entries():
            msg = "Delete ALL translation cache manager entries?\n\nThis removes machine cache, manual overrides, and failure cooldowns. Aliases, exclusions, and phrase overrides are not affected."
            if self.messagebox.askyesno("Translation Cache", msg):
                result = TRANSLATION_CACHE.clear_all_entries(include_overrides=True)
                FREE_TRANSLATION_CACHE.clear(); self.schedule_redraw(80); refresh_rows(keep_selection=False)
                status_var.set(f"Deleted all translation entries: {result.get('cache',0)} cache, {result.get('overrides',0)} overrides, {result.get('failures',0)} cooldowns.")
                self.set_status("Translation cache manager entries cleared")

        sb_components.action_button(maintenance_buttons, "Delete selected", delete_selected)
        sb_components.action_button(advanced_actions, "Clean cache issues", clean_duplicate_rows)
        sb_components.action_button(advanced_actions, "Cache status", self.show_translation_cache)
        sb_components.action_button(advanced_actions, "Delete all entries", clear_all_translation_entries)
        refresh_rows(keep_selection=False)

    def _render_settings_aliases(self, body, shell):
        tk = self.tk
        aliases_state = {"items": [dict(x) for x in USER_ALIASES]}
        c = sb_components.card(
            body,
            "Ship & system aliases",
            "Replace chat shorthand with the canonical ship or system name in the feed. Not for pilots (use Recognition Rules / ESI).",
        )
        sb_components.info_label(c, f"{len(aliases_state['items'])} alias(es) · {USER_ALIASES_PATH.name}", muted=True)
        form = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        form.pack(fill="x", pady=4)
        alias_var = tk.StringVar()
        canonical_var = tk.StringVar()
        kind_var = tk.StringVar(value="ship")
        enabled_var = tk.BooleanVar(value=True)
        note_var = tk.StringVar()
        left = tk.Frame(form, bg=sb_theme.COLORS["bg"])
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right = tk.Frame(form, bg=sb_theme.COLORS["bg"])
        right.pack(side="left", fill="x", expand=True)
        sb_components.info_label(left, "Alias seen in chat", muted=True)
        tk.Entry(left, textvariable=alias_var, **sb_theme.entry_kw()).pack(fill="x")
        sb_components.info_label(right, "Canonical display name", muted=True)
        tk.Entry(right, textvariable=canonical_var, **sb_theme.entry_kw()).pack(fill="x")
        opts = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        opts.pack(fill="x", pady=4)
        kind_menu = tk.OptionMenu(opts, kind_var, "ship", "system")
        kind_menu.configure(**sb_theme.optionmenu_kw())
        kind_menu.pack(side="left", padx=(0, 8))
        tk.Checkbutton(opts, text="Enabled", variable=enabled_var, **sb_theme.check_kw()).pack(side="left")
        sb_components.info_label(opts, "Note", muted=True)
        tk.Entry(opts, textvariable=note_var, **sb_theme.entry_kw()).pack(side="left", fill="x", expand=True, padx=(8, 0))
        list_frame = tk.Frame(c, bg=sb_theme.COLORS["bg"])
        list_frame.pack(fill="both", expand=True, pady=6)
        lb = tk.Listbox(list_frame, height=10, **sb_theme.listbox_kw())
        lb.pack(side="left", fill="both", expand=True)
        lb_scroll = tk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb_scroll.pack(side="right", fill="y")
        lb.configure(yscrollcommand=lb_scroll.set)

        def fmt_alias(entry):
            status = "on" if entry.get("enabled", True) else "off"
            return f"[{entry.get('kind', 'ship')}/{status}] {entry.get('alias', '')}  →  {entry.get('canonical', '')}"

        def reload_list():
            lb.delete(0, "end")
            for entry in aliases_state["items"]:
                lb.insert("end", fmt_alias(entry))

        def selected_index():
            sel = lb.curselection()
            return int(sel[0]) if sel else None

        def load_selected(_event=None):
            idx = selected_index()
            if idx is None:
                return
            entry = aliases_state["items"][idx]
            alias_var.set(entry.get("alias", ""))
            canonical_var.set(entry.get("canonical", ""))
            kind_var.set(entry.get("kind", "ship"))
            enabled_var.set(bool(entry.get("enabled", True)))
            note_var.set(entry.get("note", ""))

        def persist_aliases():
            save_user_aliases(aliases_state["items"])
            reload_user_aliases()
            self.redraw_feed()
            self.set_status("Aliases saved and feed refreshed")

        def add_or_update():
            entry = normalize_user_alias_entry({
                "alias": alias_var.get(),
                "canonical": canonical_var.get(),
                "kind": kind_var.get(),
                "enabled": enabled_var.get(),
                "note": note_var.get(),
            })
            if not entry:
                self.messagebox.showwarning("Aliases", "Alias and canonical name are required.")
                return
            idx = selected_index()
            if idx is None:
                aliases_state["items"].append(entry)
            else:
                aliases_state["items"][idx] = entry
            persist_aliases()
            reload_list()

        def delete_selected():
            idx = selected_index()
            if idx is None:
                return
            del aliases_state["items"][idx]
            persist_aliases()
            reload_list()
            alias_var.set("")
            canonical_var.set("")
            note_var.set("")

        def test_alias():
            sample = alias_var.get().strip() or "Apocalypse Navy"
            kind = kind_var.get()
            hit = CATALOG.lookup_system(sample) if kind == "system" else CATALOG.lookup_type(sample)
            self.messagebox.showinfo("Alias Test", f"{sample}\n=> {hit or 'no match'}")

        btns = sb_components.action_row(c)
        sb_components.action_button(btns, "Add / Update", add_or_update)
        sb_components.action_button(btns, "Test", test_alias)
        sb_components.action_button(btns, "Reload", lambda: (aliases_state.update(items=[dict(x) for x in reload_user_aliases()]), reload_list()))
        danger = sb_components.danger_card(body, "Remove alias", "Deletes the selected alias from the list and saves immediately.")
        dr = sb_components.action_row(danger)
        sb_components.action_button(dr, "Delete selected", delete_selected)
        lb.bind("<<ListboxSelect>>", load_selected)
        reload_list()

    def _render_settings_addons(self, body, shell):
        c = sb_components.card(
            body,
            "Add-ons foundation",
            "Optional modules keep the core app light. Intel History is bundled for portable installs; you can still disable it.",
        )
        sb_components.info_label(c, f"Code: {MODULES_DIR}", muted=True)
        sb_components.info_label(c, f"Data: {MODULE_DATA_DIR}", muted=True)
        ih = self.intel_history_status()
        manifest = ih.get("manifest") or {}
        c2 = sb_components.card(
            body,
            INTEL_HISTORY_ADDON_NAME,
            "Local pilot sightings and flags. Fails isolated — never blocks the live feed.",
        )
        sb_components.info_label(c2, f"Status: {self.intel_history_status_label()}")
        if ih.get("installed"):
            sb_components.info_label(
                c2,
                f"Version: {manifest.get('version') or 'unknown'} | Compatible app: {manifest.get('compatible_app') or 'n/a'}",
                muted=True,
            )
            health = self.current_intel_history_health()
            if health:
                sb_components.info_label(
                    c2,
                    f"Health: pilots {health.get('pilots', 0)} | sightings {health.get('sightings', 0)} | queue {health.get('queue_size', 0)}",
                    muted=True,
                )
                sb_components.info_label(c2, f"Last sighting: {health.get('last_sighting', 'none')}", muted=True)
                if health.get("last_error") and health.get("last_error") != "none":
                    sb_components.info_label(c2, f"Last error: {str(health.get('last_error'))[:160]}", fg=sb_theme.COLORS["error"])
        else:
            sb_components.info_label(c2, "Not installed. Use Install from ZIP for the official package.", muted=True)
        enabled_var = self.tk.BooleanVar(value=bool(ih.get("enabled")))
        sb_components.check(
            c2,
            "Enable Intel History",
            enabled_var,
            lambda v=enabled_var: self.set_intel_history_enabled(bool(v.get())),
        )
        r = sb_components.action_row(c2)
        sb_components.action_button(r, "Install from ZIP…", self.install_intel_history_addon_from_file)
        sb_components.action_button(r, "Details", self.show_intel_history_details)
        sb_components.action_button(r, "Open Data Folder", self.open_intel_history_data_folder)
        if ih.get("installed"):
            danger = sb_components.danger_card(
                body,
                "Uninstall add-on code",
                "Removes module code only. Local SQLite data under user_data is kept by default.",
            )
            dr = sb_components.action_row(danger)
            sb_components.action_button(dr, "Uninstall Code", self.uninstall_intel_history_addon_code)

    def show_settings_center(self, initial_page: str = "General"):
        pages = [
            "General", "Channels", "Appearance", "Translation", "Translation Cache", "Filters",
            "EVE Catalog", "Aliases", "ESI", "Pilot Intel", "LAN Viewer", "Recognition Rules",
            "Add-ons", "Cache & Data", "Diagnostics", "About / Support",
        ]
        descriptions = {
            "General": "Window options, optional startup backlog, and folders.",
            "Channels": "Track, restore, and stop monitoring EVE chat channels.",
            "Appearance": "Fonts, colors, opacity, and highlight toggles.",
            "Translation": "Display mode, engines, and cache shortcuts.",
            "Translation Cache": "Correct live translations and manage cache-backed rows.",
            "Filters": "Keyword/sender filters and Local spam rate limits.",
            "EVE Catalog": "Bundled catalog status and updates.",
            "Aliases": "Ship and system shorthand replacements for the feed.",
            "ESI": "Optional pilot recognition, OAuth, and ESI cache.",
            "Pilot Intel": "Pilot cards, local history, flags, and zKill — core fleet workflow.",
            "LAN Viewer": "Optional phone/LAN read-only feed mirror (tokenized URL).",
            "Recognition Rules": "Ignored pilots, highlight exclusions, and noise words.",
            "Add-ons": "Package install/enable for bundled modules (Intel History code).",
            "Cache & Data": "Starter files and local cache maintenance.",
            "Diagnostics": "Copy-friendly health summary and log access.",
            "About / Support": "Version window, help topics, and support links.",
        }
        renderers = {
            "General": self._render_settings_general,
            "Channels": self._render_settings_channels,
            "Appearance": self._render_settings_appearance,
            "Translation": self._render_settings_translation,
            "Translation Cache": self._render_settings_translation_cache,
            "Filters": self._render_settings_filters,
            "EVE Catalog": self._render_settings_catalog,
            "Aliases": self._render_settings_aliases,
            "ESI": self._render_settings_esi,
            "Pilot Intel": self._render_settings_pilot_intel,
            "LAN Viewer": self._render_settings_lan,
            "Recognition Rules": self._render_settings_exclusions,
            "Add-ons": self._render_settings_addons,
            "Cache & Data": self._render_settings_cache_data,
            "Diagnostics": self._render_settings_diagnostics,
            "About / Support": self._render_settings_about,
        }
        groups = {
            "General": "Monitor", "Channels": "Monitor", "Appearance": "Monitor",
            "Translation": "Translation", "Translation Cache": "Translation", "Filters": "Translation",
            "EVE Catalog": "Intel", "Aliases": "Intel", "ESI": "Intel", "Pilot Intel": "Intel",
            "LAN Viewer": "Intel", "Recognition Rules": "Intel", "Add-ons": "Intel",
            "Cache & Data": "Data", "Diagnostics": "Support", "About / Support": "Support",
        }
        # Back-compat: old deep links / call sites may still pass "Exclusions".
        if initial_page == "Exclusions":
            initial_page = "Recognition Rules"

        def apply_settings() -> bool:
            self.persist_settings()
            ok = MAIN_SETTINGS_STORE.save(SETTINGS)
            if ok:
                self.set_status("Settings saved")
            return ok

        warnings = list(MAIN_SETTINGS_STORE.warnings)
        startup_status = (f"{len(warnings)} settings warning(s) on load — see logs folder"
                          if warnings else "")
        shell = SettingsShell(
            self.root, pages=pages, descriptions=descriptions, renderers=renderers,
            on_apply=apply_settings, polish=self.polish_window,
            initial_page=initial_page, startup_status=startup_status, groups=groups,
        )
        shell.open()

    def show_appearance_dialog(self):
        tk = self.tk
        from tkinter import colorchooser
        original = copy.deepcopy(self.appearance)
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=760, height=620, minsize=(520, 420), modal=True, title="Appearance / Display Options")
        vars = {}

        # Keep action buttons visible on narrow/mobile-style layouts by making
        # only the settings body scroll while the footer stays fixed.
        outer = tk.Frame(win, bg=sb_theme.COLORS["bg"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=sb_theme.COLORS["bg"], highlightthickness=0, bd=0)
        body_scroll = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=sb_theme.COLORS["bg"])
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=body_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        body_scroll.pack(side="right", fill="y")
        def _appearance_body_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            try:
                canvas.itemconfigure(body_window, width=canvas.winfo_width())
            except Exception:
                pass
        body.bind("<Configure>", _appearance_body_configure)
        canvas.bind("<Configure>", _appearance_body_configure)
        def _appearance_wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind("<MouseWheel>", _appearance_wheel)
        body.bind("<MouseWheel>", _appearance_wheel)
        def make_var(value):
            v = tk.StringVar(value=str(value))
            return v
        fam_var = tk.StringVar(value=self.font_family.get())
        size_var = tk.IntVar(value=int(self.font_size.get()))
        opacity_var = tk.DoubleVar(value=float(self.appearance.get("window_opacity", 1.0)) * 100.0)
        preset_var = tk.StringVar(value=str(self.appearance.get("preset", "Default Dark")))
        bg_enabled = tk.BooleanVar(value=bool(self.appearance.get("highlight_backgrounds", False)))
        modules_enabled = tk.BooleanVar(value=bool(self.appearance.get("highlight_modules", False)))
        try:
            import tkinter.font as tkfont
            families = sorted(set(tkfont.families(self.root)))
        except Exception:
            families = ["Segoe UI", "Aptos", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Courier New"]
        top = tk.LabelFrame(body, text="General", bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg"], padx=10, pady=8)
        top.pack(fill="x", padx=12, pady=(10, 8))
        tk.Label(top, text="Preset", **sb_theme.label_kw(muted=True)).grid(row=0, column=0, sticky="w", pady=3)
        preset_menu = tk.OptionMenu(top, preset_var, *APPEARANCE_PRESETS.keys())
        preset_menu.configure(**sb_theme.optionmenu_kw(), highlightthickness=0)
        preset_menu.grid(row=0, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Label(top, text="Font", **sb_theme.label_kw(muted=True)).grid(row=1, column=0, sticky="w", pady=3)
        font_menu = tk.OptionMenu(top, fam_var, *families)
        font_menu.configure(**sb_theme.optionmenu_kw(), highlightthickness=0)
        font_menu.grid(row=1, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Label(top, text="Size", **sb_theme.label_kw(muted=True)).grid(row=1, column=2, sticky="w", pady=3)
        tk.Spinbox(top, from_=8, to=28, width=6, textvariable=size_var,
                   bg=sb_theme.COLORS["bg_input"], fg=sb_theme.COLORS["fg"],
                   insertbackground=sb_theme.COLORS["fg"], buttonbackground=sb_theme.COLORS["bg_panel"]).grid(row=1, column=3, sticky="w", padx=8, pady=3)
        tk.Label(top, text="Opacity", **sb_theme.label_kw(muted=True)).grid(row=2, column=0, sticky="w", pady=3)
        tk.Scale(top, from_=55, to=100, orient="horizontal", variable=opacity_var,
                 bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg"],
                 troughcolor=sb_theme.COLORS["bg_panel"], activebackground="#5ad7ff",
                 highlightthickness=0, length=230).grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Checkbutton(top, text="Background highlight rectangles", variable=bg_enabled,
                       **sb_theme.check_kw()).grid(row=2, column=2, columnspan=2, sticky="w", pady=3)
        tk.Checkbutton(top, text="Highlight modules/assets (purple)", variable=modules_enabled,
                       **sb_theme.check_kw()).grid(row=3, column=0, columnspan=4, sticky="w", pady=3)
        top.columnconfigure(1, weight=1)

        grid = tk.LabelFrame(body, text="Highlight Colors", bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg"], padx=8, pady=6)
        grid.pack(fill="x", padx=12, pady=4)
        tk.Label(grid, text="Category", **sb_theme.label_kw(muted=True), font=sb_theme.font(9, bold=True)).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 4))
        tk.Label(grid, text="Text", **sb_theme.label_kw(muted=True), font=sb_theme.font(9, bold=True)).grid(row=0, column=1, columnspan=3, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Bold", **sb_theme.label_kw(muted=True), font=sb_theme.font(9, bold=True)).grid(row=0, column=4, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Background", **sb_theme.label_kw(muted=True), font=sb_theme.font(9, bold=True)).grid(row=0, column=5, columnspan=3, sticky="w", pady=(0, 4))
        rows = [("time","Timestamp"),("sender","Sender"),("system","Systems"),("esi","Characters / ESI"),("asset","Ships"),("module","Modules / Assets"),("ess","ESS"),("translation","Translation"),("link","Links")]
        # Module purple off by default; expose toggle near color table.
        swatches: list[tk.Widget] = []
        def normalized_color(value: str, fallback: str = "#070b10") -> str:
            value = (value or "").strip()
            try:
                win.winfo_rgb(value)
                return value
            except Exception:
                return fallback
        def swatch_fg(color: str) -> str:
            try:
                r, g, b = [x // 256 for x in win.winfo_rgb(color)]
                return "#000000" if (r * 299 + g * 587 + b * 114) > 150000 else "#ffffff"
            except Exception:
                return "#ffffff"
        def update_swatches():
            for widget in swatches:
                var = getattr(widget, "color_var", None)
                fallback = getattr(widget, "fallback_color", "#070b10")
                color = normalized_color(var.get() if var else "", fallback)
                try:
                    widget.configure(bg=color, activebackground=color, fg=swatch_fg(color), activeforeground=swatch_fg(color), text="   ")
                except Exception:
                    pass
        def choose_color(var):
            color = colorchooser.askcolor(color=normalized_color(var.get(), "#070b10"), parent=win)[1]
            if color:
                var.set(color.upper())
                update_swatches()
                update_preview()
        def make_color_control(row: int, col: int, var, fallback: str):
            swatch = tk.Button(grid, text="   ", width=3, relief="groove", bd=1, command=lambda v=var: choose_color(v))
            swatch.color_var = var
            swatch.fallback_color = fallback
            swatch.grid(row=row, column=col, sticky="w", padx=(0, 4), pady=2)
            swatches.append(swatch)
            entry = tk.Entry(grid, textvariable=var, width=11, **sb_theme.entry_kw())
            entry.grid(row=row, column=col + 1, sticky="w", padx=(0, 4), pady=2)
            tk.Button(grid, text="Pick", command=lambda v=var: choose_color(v),
                      padx=6, **sb_theme.btn_secondary_kw()).grid(row=row, column=col + 2, sticky="w", pady=2)
        for r, (key, label) in enumerate(rows, start=1):
            style = self.appearance.get(key, DEFAULT_APPEARANCE.get(key, {}))
            fg = tk.StringVar(value=str(style.get("foreground", "#d7dde5")))
            bold = tk.BooleanVar(value=bool(style.get("bold", False)))
            bg = tk.StringVar(value=str(style.get("background", "")))
            vars[key] = {"foreground": fg, "bold": bold, "background": bg}
            tk.Label(grid, text=label, **sb_theme.label_kw()).grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)
            make_color_control(r, 1, fg, "#d7dde5")
            tk.Checkbutton(grid, variable=bold, command=lambda: update_preview(),
                           **sb_theme.check_kw()).grid(row=r, column=4, sticky="w", padx=(8, 8), pady=2)
            make_color_control(r, 5, bg, "#070b10")
        grid.columnconfigure(0, minsize=135)
        grid.columnconfigure(2, minsize=92)
        grid.columnconfigure(6, minsize=92)

        preview_box = tk.LabelFrame(body, text="Preview", bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg"], padx=8, pady=6)
        preview_box.pack(fill="x", padx=12, pady=8)
        preview = tk.Text(preview_box, height=4, relief="flat", wrap="word", padx=8, pady=8)
        preview.pack(fill="x", expand=False)
        def collect():
            app = copy.deepcopy(self.appearance)
            app["preset"] = preset_var.get()
            app["font_family"] = fam_var.get() or "Segoe UI"
            app["font_size"] = max(8, min(28, int(size_var.get())))
            app["window_opacity"] = max(0.55, min(1.0, float(opacity_var.get()) / 100.0))
            app["highlight_backgrounds"] = bool(bg_enabled.get())
            app["highlight_modules"] = bool(modules_enabled.get())
            for key, data in vars.items():
                app.setdefault(key, {})
                app[key]["foreground"] = data["foreground"].get().strip() or DEFAULT_APPEARANCE[key]["foreground"]
                app[key]["bold"] = bool(data["bold"].get())
                app[key]["background"] = data["background"].get().strip()
            return self.normalize_appearance(app)
        def apply_to_widget(widget, app):
            fam = app.get("font_family", "Segoe UI"); size = int(app.get("font_size", 10))
            widget.configure(bg=app.get("background", "#070b10"), fg=app.get("foreground", "#d7dde5"), font=(fam, size), insertbackground=app.get("foreground", "#d7dde5"))
            for tag in STYLE_TAGS:
                st = app.get(tag, DEFAULT_APPEARANCE.get(tag, {}))
                opts = {"foreground": st.get("foreground", "#d7dde5"), "font": (fam, size, "bold" if st.get("bold") else "normal")}
                opts["background"] = st.get("background", "") if app.get("highlight_backgrounds") else ""
                if tag == "link": opts["underline"] = True
                widget.tag_configure(tag, **opts)
        def render_preview(app):
            preview.configure(state="normal")
            preview.delete("1.0", "end")
            apply_to_widget(preview, app)
            preview.insert("end", "[12:42] ", ("time",))
            preview.insert("end", "Scout > ", ("sender",))
            preview.insert("end", "Abraxas Shaw", ("esi",))
            preview.insert("end", " in ")
            preview.insert("end", "1DQ1-A", ("system",))
            preview.insert("end", " Loki", ("asset",))
            preview.insert("end", " Large Armor Repairer", ("module",))
            preview.insert("end", " ESS", ("ess",))
            preview.insert("end", " https://example.invalid", ("link",))
            preview.insert("end", "\nEN: Hostile scout in system", ("translation",))
            preview.configure(state="disabled")
        def update_preview(*_):
            try:
                app = collect()
                update_swatches()
                render_preview(app)
            except Exception as exc:
                write_log(f"Appearance preview failed: {exc}")
        def apply_now(close=False):
            self.appearance = collect()
            self.font_family.set(self.appearance["font_family"])
            self.font_size.set(self.appearance["font_size"])
            self.apply_appearance(redraw=False, save=True)
            self.set_status("Appearance updated")
            if close:
                win.destroy()
        def cancel():
            self.appearance = original
            self.font_family.set(original.get("font_family", "Segoe UI"))
            self.font_size.set(int(original.get("font_size", 10)))
            self.apply_appearance(redraw=False, save=False)
            win.destroy()
        def reset_defaults():
            self.appearance = copy.deepcopy(DEFAULT_APPEARANCE)
            self.font_family.set(self.appearance["font_family"])
            self.font_size.set(self.appearance["font_size"])
            win.destroy()
            self.show_appearance_dialog()
        def preset_changed(*_):
            name = preset_var.get()
            base = copy.deepcopy(DEFAULT_APPEARANCE)
            for k, v in APPEARANCE_PRESETS.get(name, {}).items():
                if isinstance(v, dict) and isinstance(base.get(k), dict): base[k].update(v)
                else: base[k] = copy.deepcopy(v)
            base["preset"] = name
            fam_var.set(base.get("font_family", "Segoe UI")); size_var.set(int(base.get("font_size", 10))); opacity_var.set(float(base.get("window_opacity", 1.0))*100); bg_enabled.set(bool(base.get("highlight_backgrounds", False))); modules_enabled.set(bool(base.get("highlight_modules", False)))
            for key, data in vars.items():
                st = base.get(key, DEFAULT_APPEARANCE[key])
                data["foreground"].set(st.get("foreground", "#d7dde5")); data["bold"].set(bool(st.get("bold", False))); data["background"].set(st.get("background", ""))
            update_swatches()
            update_preview()
        update_swatches()
        for v in (fam_var, size_var, opacity_var, bg_enabled, modules_enabled):
            try: v.trace_add("write", lambda *_: update_preview())
            except Exception: pass
        for data in vars.values():
            for v in data.values():
                try: v.trace_add("write", lambda *_: update_preview())
                except Exception: pass
        preset_var.trace_add("write", preset_changed)
        render_preview(collect())
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg_panel"], highlightthickness=1, highlightbackground=sb_theme.COLORS["border"])
        btns.pack(fill="x", side="bottom")
        tk.Button(btns, text="Reset Defaults", command=reset_defaults,
                  **sb_theme.btn_secondary_kw()).pack(side="left", padx=(12, 6), pady=10)
        tk.Button(btns, text="Apply", command=lambda: apply_now(False),
                  **sb_theme.btn_primary_kw()).pack(side="left", padx=6, pady=10)
        tk.Button(btns, text="OK", command=lambda: apply_now(True),
                  **sb_theme.btn_primary_kw()).pack(side="right", padx=(6, 12), pady=10)
        tk.Button(btns, text="Cancel", command=cancel,
                  **sb_theme.btn_secondary_kw()).pack(side="right", padx=6, pady=10)
        win.protocol("WM_DELETE_WINDOW", cancel)

    def persist_settings(self):
        SETTINGS.update({
            "chatlog_dir": str(CHATLOG_DIR),
            "db_path": str(DB_PATH),
            "active_channels": sorted(self.active_channels),
            "always_on_top": bool(self.always_on_top.get()),
            "translated_only": bool(self.translated_only.get()),
            "translate_free_text": bool(self.translate_chinese_text.get()),
            "translation_direction": self.translation_direction.get(),
            "translation_preferred_engine": self.translation_preferred_engine.get(),
            "translation_fallback_mode": self.translation_fallback_mode.get(),
            "compact_mode": bool(self.compact.get()),
            "font_family": self.font_family.get(),
            "font_size": int(self.font_size.get()),
            "appearance": self.normalize_appearance(getattr(self, "appearance", None)),
            "show_timestamps": bool(self.show_timestamps.get()),
            "show_channel_names": bool(self.show_channel_names.get()),
            "show_channel_names_in_all": bool(self.show_channel_names_in_all.get()),
            "enable_hyperlinks": bool(self.enable_hyperlinks.get()),
            "active_tab_id": self.visible_channel or ALL_CHANNELS_TAB,
            "tab_order": list(self.tab_order),
            "hidden_tab_ids": sorted(self.hidden_tab_ids),
            "auto_open_new_channels": True,
            "auto_switch_to_new_channel": False,
            "max_tab_rows": int(SETTINGS.get("max_tab_rows", 3) or 3),
            "replay_on_start": bool(getattr(self, "replay_on_start_var", None).get()) if getattr(self, "replay_on_start_var", None) is not None else bool(SETTINGS.get("replay_on_start", False)),
            "backlog_minutes": int(getattr(self, "backlog_minutes_var", None).get()) if getattr(self, "backlog_minutes_var", None) is not None else int(SETTINGS.get("backlog_minutes", 10) or 10),
            "feed_filters": list(SETTINGS.get("feed_filters") or []),
            "spam_control_enabled": bool(SETTINGS.get("spam_control_enabled", True)),
            "spam_local_channels_only": bool(SETTINGS.get("spam_local_channels_only", True)),
            "spam_ascii_art_filter": bool(SETTINGS.get("spam_ascii_art_filter", True)),
            "lan_enabled": bool(self.lan_enabled.get()) if getattr(self, "lan_enabled", None) is not None else bool(SETTINGS.get("lan_enabled", False)),
            "lan_port": int(self.lan_port.get()) if getattr(self, "lan_port", None) is not None else int(SETTINGS.get("lan_port", 8765) or 8765),
            "lan_token": str(getattr(self, "lan_token", "") or SETTINGS.get("lan_token") or ""),
            "lan_host": str(SETTINGS.get("lan_host") or "0.0.0.0"),
        })
        save_settings(SETTINGS)

    def persist_and_redraw(self):
        self.persist_settings()
        self.redraw_feed()

    def choose_chatlog_folder(self):
        global CHATLOG_DIR
        selected = self.filedialog.askdirectory(title="Choose EVE Chatlogs Folder", initialdir=str(CHATLOG_DIR if CHATLOG_DIR.exists() else Path.home()))
        if not selected:
            return
        CHATLOG_DIR = Path(selected)
        self.active_channels = set()
        self.hidden_tab_ids = set()
        self.tab_order = [ALL_CHANNELS_TAB]
        self.visible_channel = ALL_CHANNELS_TAB
        self.title_label.configure(text=f"{APP_NAME} v{APP_VERSION}")
        self.persist_settings()
        self.clear_feed()
        self.stop_monitor()
        self.set_status("Chatlog folder changed. Choose channels to monitor.")

    def choose_db_file(self):
        global DB_PATH
        selected = self.filedialog.askopenfilename(title="Choose EVE translations.db", filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")])
        if not selected:
            return
        DB_PATH = Path(selected)
        self.persist_settings()
        self.set_status("Translation DB updated")

    def open_app_folder(self):
        import os
        os.startfile(str(USER_DIR))

    def open_logs_folder(self):
        import os
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(LOG_DIR))

    def refresh_argos_status(self):
        """Check Argos runtime/model status without blocking the Tk UI thread."""
        self.argos_status_text.set("Argos status: checking...")
        self.set_status("Checking Argos status...")
        threading.Thread(target=self._refresh_argos_status_worker, daemon=True).start()
        return "checking"

    def _refresh_argos_status_worker(self):
        try:
            status = format_argos_status()
        except Exception as exc:
            write_log("Argos status check failed", exc)
            status = "Argos status check failed: " + str(exc)[:160]
        self.queue.put(("argos_status", status))

    def save_translation_engine_settings(self):
        SETTINGS["translation_preferred_engine"] = self.translation_preferred_engine.get()
        SETTINGS["translation_fallback_mode"] = self.translation_fallback_mode.get()
        SETTINGS["translation_cache_mode"] = self.translation_cache_mode.get()
        SETTINGS["translation_failure_cooldown_minutes"] = int(self.translation_failure_cooldown_minutes.get() or 60)
        save_settings(SETTINGS)
        self.persist_settings()
        pref = self.translation_preferred_engine.get()
        fallback = self.translation_fallback_mode.get()
        if pref == "argos" or fallback in ("argos-google", "google-argos", "offline-only"):
            self.argos_status_text.set("Argos is temporarily disabled because the current runtime/probe path can hang the app. Use Google/Auto for now; Argos will return as a safe optional add-on/offline package.")
        self.set_status(f"Translation engine: {pref} / {fallback}")
        self.schedule_redraw()

    def test_translation_engine(self):
        sample = chr(0x5929) + chr(0x9e64) + chr(0x7ea7) + " " + chr(0x77ed) + chr(0x5251) + chr(0x7ea7)
        pref = self.translation_preferred_engine.get()
        if pref == "argos" or self.translation_fallback_mode.get() in ("argos-google", "google-argos", "offline-only"):
            result = "Argos is temporarily disabled because the current runtime/probe path can hang the app. Use Auto/Google for now."
        else:
            # Do not run network MT from this dialog. Keep the UI nonblocking.
            result = TRANSLATION_CACHE.get("google|auto|en|" + sample) or ""
        if not result:
            result = "No blocking machine translation test was run. Curated EVE cache still handles known ship aliases in live rows."
        self.messagebox.showinfo("Translation Test", f"Preferred engine: {self.translation_preferred_engine.get()}\nFallback: {self.translation_fallback_mode.get()}\n\nInput:\n{sample}\n\nOutput:\n{result}\n\nArgos status is shown on the Translation settings page. Use Refresh Argos Status to check it without blocking the app.")

    def install_argos_models(self):
        msg = (
            "Argos install/repair is temporarily disabled. The current Argos runtime/probe path can hang Signal Bridge. "
            "Use Auto/Google for now; Argos should be reintroduced as a safe optional add-on/offline package with isolated install and model checks."
        )
        self.argos_status_text.set(msg)
        self.set_status("Argos installer disabled for safety")
        self.messagebox.showwarning("Argos Temporarily Disabled", msg)

    def _install_argos_models_worker(self):
        msg = "Argos installer disabled for safety; no install attempted."
        self.queue.put(("argos_status", msg))

    def esi_is_enabled(self) -> bool:
        return bool(self.esi_enabled.get())

    def save_esi_ui_settings(self):
        self.esi_settings["enabled"] = bool(self.esi_enabled.get())
        self.esi_settings["oauth_enabled"] = bool(self.esi_oauth_enabled.get())
        save_esi_settings(self.esi_settings)
        SETTINGS["esi_entity_recognition"] = bool(self.esi_enabled.get())
        SETTINGS["esi_oauth_enabled"] = bool(self.esi_oauth_enabled.get())
        save_settings(SETTINGS)
        if self.esi_is_enabled():
            self.ensure_esi_resolver()
        self.set_status("ESI settings saved")

    def ensure_esi_resolver(self):
        if self.esi_resolver and self.esi_resolver.is_alive():
            return
        self.esi_resolver = EsiResolver(self.queue, self.esi_is_enabled)
        self.esi_resolver.start()

    def show_esi_settings(self):
        tk = self.tk
        self.esi_settings = load_esi_settings()
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=560, height=460, minsize=(480, 400), modal=True, title="ESI / OAuth Settings")
        tk.Label(win, text="Optional ESI support", **sb_theme.label_kw(), font=sb_theme.font(11, bold=True)).pack(anchor="w", padx=10, pady=(10, 4))
        tk.Label(win, text="Signal Bridge works normally with ESI disabled. OAuth is only needed for future character-aware features.", **sb_theme.label_kw(muted=True), wraplength=520, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
        tk.Checkbutton(win, text="Enable ESI entity recognition", variable=self.esi_enabled, **sb_theme.check_kw()).pack(anchor="w", padx=10)
        tk.Checkbutton(win, text="Enable OAuth features", variable=self.esi_oauth_enabled, **sb_theme.check_kw()).pack(anchor="w", padx=10)
        form = tk.Frame(win, bg=sb_theme.COLORS["bg"]); form.pack(fill="x", padx=10, pady=8)
        tk.Label(form, text="Client ID", **sb_theme.label_kw(muted=True)).grid(row=0, column=0, sticky="w", pady=3)
        client_id = tk.Entry(form, width=52, **sb_theme.entry_kw())
        client_id.insert(0, str(self.esi_settings.get("client_id") or ESI_DEFAULT_CLIENT_ID)); client_id.grid(row=0, column=1, sticky="ew", padx=8, pady=3)
        tk.Label(form, text="Client Secret", **sb_theme.label_kw(muted=True)).grid(row=1, column=0, sticky="w", pady=3)
        client_secret = tk.Entry(form, show="*", width=52, **sb_theme.entry_kw())
        client_secret.insert(0, str(self.esi_settings.get("client_secret") or "")); client_secret.grid(row=1, column=1, sticky="ew", padx=8, pady=3)
        tk.Label(form, text="Callback", **sb_theme.label_kw(muted=True)).grid(row=2, column=0, sticky="w", pady=3)
        callback = tk.Entry(form, width=52, **sb_theme.entry_kw())
        callback.insert(0, str(self.esi_settings.get("callback_url") or ESI_CALLBACK_URL)); callback.grid(row=2, column=1, sticky="ew", padx=8, pady=3)
        form.columnconfigure(1, weight=1)
        stats = ESI_CACHE.stats()
        status_text = f"Cache: {stats.get('entities',0)} entities, {stats.get('negative',0)} negative, {stats.get('corrections',0)} corrections\nCallback listener: {'listening' if self.oauth_listener_active else 'closed'}\nToken file: {'present' if ESI_TOKENS_PATH.exists() else 'not authorized'}"
        tk.Label(win, text=status_text, **sb_theme.label_kw(muted=True), justify="left").pack(anchor="w", padx=10, pady=8)
        btns = tk.Frame(win, bg=sb_theme.COLORS["bg"]); btns.pack(fill="x", padx=10, pady=10)
        def apply():
            self.esi_settings["client_id"] = client_id.get().strip() or ESI_DEFAULT_CLIENT_ID
            self.esi_settings["client_secret"] = client_secret.get().strip()
            self.esi_settings["callback_url"] = callback.get().strip() or ESI_CALLBACK_URL
            self.save_esi_ui_settings()
        sb_components.primary_button(btns, "Save", apply).pack(side="left", padx=(0, 6))
        sb_components.action_button(btns, "Authorize Character", lambda: (apply(), self.authorize_esi_character())).pack(side="left", padx=6)
        sb_components.action_button(btns, "Check ESI", self.check_esi_status).pack(side="left", padx=6)
        sb_components.action_button(btns, "Close", win.destroy).pack(side="right")

    def check_esi_status(self):
        write_log("ESI status check requested from UI")
        self.status_label.configure(text="Checking ESI status...")
        def worker():
            try:
                req = urllib.request.Request("https://esi.evetech.net/latest/status/", headers={"User-Agent": ESI_USER_AGENT, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                ESI_CACHE.set_status("last_status", "ok")
                ESI_CACHE.set_status("last_check", f"status ok: {data.get('players','?')} players online")
                self.queue.put(("status", f"ESI OK: {data.get('players','?')} players online"))
                self.queue.put(("esi_status_result", True, data))
                write_log(f"ESI status check OK: {data.get('players','?')} players online")
            except Exception as exc:
                ESI_CACHE.set_status("last_status", "offline")
                ESI_CACHE.set_status("last_check", "status check failed")
                write_log("ESI status check failed", exc)
                self.queue.put(("status", "ESI status check failed; see logs"))
                self.queue.put(("esi_status_result", False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def show_esi_cache_status(self):
        stats = ESI_CACHE.stats(); status = stats.get("status", {})
        self.messagebox.showinfo("ESI Cache", f"Cache file: {ESI_CACHE_PATH}\nEntities: {stats.get('entities',0)}\nNegative entries: {stats.get('negative',0)}\nCorrections: {stats.get('corrections',0)}\nLast status: {status.get('last_status','unknown')}\nLast error: {status.get('last_error','none')}\nPositive TTL: 30 days")

    def clear_esi_cache(self):
        if self.messagebox.askyesno("ESI Cache", "Clear cached ESI entities and negative lookups? Manual corrections are kept."):
            if ESI_CACHE.clear():
                self.esi_entities.clear(); self.set_status("ESI cache cleared")

    def selected_feed_text(self) -> str:
        try:
            return re.sub(r"\s+", " ", self.text.get("sel.first", "sel.last").strip())
        except Exception:
            return ""

    def show_esi_diagnostics(self):
        stats = ESI_CACHE.stats()
        statuses = ESI_CACHE.get_status()
        def fmt_status(key: str) -> str:
            item = statuses.get(key)
            if not item:
                return ""
            ts = item.get("updated_at") or 0
            try:
                stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
            except Exception:
                stamp = ""
            return f"{item.get('value','')} ({stamp})"
        resolver_state = "not running"
        if self.esi_resolver and self.esi_resolver.is_alive():
            resolver_state = f"running, queue={self.esi_resolver.work.qsize()}, pending={len(self.esi_resolver.pending)}"
        text = (
            f"ESI enabled: {self.esi_is_enabled()}\n"
            f"Resolver: {resolver_state}\n"
            f"Cache file: {ESI_CACHE_PATH}\n"
            f"Entities: {stats.get('entities',0)}\n"
            f"Negative answers: {stats.get('negative',0)}\n"
            f"Exclusions/corrections: {stats.get('corrections',0)}\n"
            f"Last check: {fmt_status('last_check')}\n"
            f"Last status: {fmt_status('last_status')}\n"
            f"Last error: {fmt_status('last_error')}\n"
        )
        self.messagebox.showinfo("ESI Last Check / Diagnostics", text)

    def translation_trace_for_row(self, row: Row | None) -> str:
        if not row:
            return "No row detected under the cursor."
        try:
            parts = self.row_display_parts(row)
        except Exception as exc:
            record_error("translation_trace", exc)
            return f"Translation trace failed: {type(exc).__name__}: {exc}"
        decision = getattr(row, "_last_translation_decision", "not rendered yet")
        lines = [
            "Translation Decision Trace",
            "--------------------------",
            f"Channel: {row.channel}",
            f"Sender: {row.sender}",
            f"Raw text: {row.text}",
            f"Normalized original: {parts.get('original_text','')}",
            f"Catalog/localized display: {parts.get('display_text','')}",
            f"Free translation: {parts.get('free_text','') or '(empty)'}",
            f"Visible translated: {parts.get('translated','')}",
            f"Source label: {parts.get('source_label','') or '(none)'}",
            f"Decision: {decision}",
            f"Preferred engine: {self.translation_preferred_engine.get()}",
            f"Fallback mode: {self.translation_fallback_mode.get()}",
            f"Translate free text enabled: {bool(self.translate_chinese_text.get())}",
            f"Translated only: {bool(self.translated_only.get())}",
        ]
        record_event("translation_trace", sender=row.sender, channel=row.channel, decision=decision, localized=len(row.localized), assets=len(row.assets), systems=len(row.systems), has_free=bool(row.free_translation))
        return "\n".join(lines)

    def entity_trace_for_row(self, row: Row | None) -> str:
        if not row:
            return "No row detected under the cursor."
        try:
            candidates = candidate_terms(row.text)[:80]
        except Exception:
            candidates = []
        try:
            esi_candidates = esi_candidates_for_row(row)[:80]
        except Exception:
            esi_candidates = []
        unknown_cjk = []
        try:
            known = set(row.systems) | set(row.assets) | set(str(x.get("original", "")) for x in row.localized) | set(str(x.get("canonical", "")) for x in row.localized)
            for cand in candidates:
                if re.search(r"[^\x00-\x7f]", cand) and cand not in known:
                    unknown_cjk.append(cand)
        except Exception:
            pass
        lines = [
            "Entity Recognition Trace",
            "------------------------",
            f"Channel: {row.channel}",
            f"Sender: {row.sender}",
            f"Raw text: {row.text}",
            f"Normalized display: {normalize_feed_text(row.text)}",
            f"Systems: {', '.join(row.systems) or '(none)'}",
            f"Assets/modules: {', '.join(row.assets) or '(none)'}",
            "Localized aliases:",
        ]
        if row.localized:
            for ent in row.localized:
                lines.append(f"- {ent.get('original','')} -> {ent.get('canonical','')} ({ent.get('kind','')})")
        else:
            lines.append("- (none)")
        seg_lines = []
        for idx, seg in enumerate(getattr(row, "segments", []) or [], 1):
            seg_lines.append(f"{idx}. {seg.kind}: {seg.text} | systems={','.join(seg.systems) or '-'} assets={','.join(seg.assets) or '-'} pilots={','.join(seg.pilots) or '-'} notes={','.join(seg.notes + seg.status) or '-'}")
        lines.extend([
            "Segments:",
            *(seg_lines or ["- (none)"]),
            f"Candidate terms: {', '.join(candidates[:30]) or '(none)'}",
            f"ESI candidates: {', '.join(esi_candidates[:30]) or '(none)'}",
            f"Unknown non-ASCII terms: {', '.join(unique(unknown_cjk)[:30]) or '(none)'}",
        ])
        record_event("entity_trace", sender=row.sender, channel=row.channel, systems=len(row.systems), assets=len(row.assets), localized=len(row.localized), esi_candidates=len(esi_candidates), unknown_cjk=len(unknown_cjk))
        return "\n".join(lines)

    def show_translation_trace_for_row(self, row: Row | None):
        text = self.translation_trace_for_row(row)
        self.copy_to_clipboard(text)
        self.messagebox.showinfo("Translation Trace", text[:5000])
        self.set_status("Translation trace copied")

    def show_entity_trace_for_row(self, row: Row | None):
        text = self.entity_trace_for_row(row)
        self.copy_to_clipboard(text)
        self.messagebox.showinfo("Entity Recognition Trace", text[:5000])
        self.set_status("Entity recognition trace copied")

    def show_click_context_trace(self, ctx: dict, row: Row | None, url: str | None = None):
        lines = [
            "Right-Click Context Trace",
            "-------------------------",
            f"Kind: {ctx.get('kind')}",
            f"Clicked text: {ctx.get('text') or ''}",
            f"URL: {url or '(none)'}",
        ]
        ent = ctx.get("entity") if isinstance(ctx, dict) else None
        if ent:
            lines.append(f"Pilot entity: {ent.get('name') or ent.get('query')} id={ent.get('entity_id')}")
        if row:
            lines.extend([
                f"Row channel: {row.channel}",
                f"Row sender: {row.sender}",
                f"Row text: {row.text}",
                f"Systems: {', '.join(row.systems) or '(none)'}",
                f"Assets: {', '.join(row.assets) or '(none)'}",
                f"ESI entities: {', '.join(str(e.get('name') or e.get('query')) for e in getattr(row, 'esi_entities', []) or []) or '(none)'}",
            ])
        text = "\n".join(lines)
        record_event("click_context_trace", kind=ctx.get("kind"), text=ctx.get("text"), has_url=bool(url), sender=getattr(row, "sender", ""), channel=getattr(row, "channel", ""))
        self.copy_to_clipboard(text)
        self.messagebox.showinfo("Click Context Trace", text[:5000])
        self.set_status("Click context trace copied")

    def show_esi_candidates_for_row(self, row: Row | None):
        if not row:
            self.messagebox.showinfo("ESI Candidates", "No chat row detected under the cursor. Select text and use Resolve Selected Text with ESI.")
            return
        candidates = esi_candidates_for_row(row)
        if not candidates:
            self.messagebox.showinfo("ESI Candidates", "No ESI candidates detected for this row.\n\nKnown systems/EVE entities/counts/links are excluded before name detection.")
            return
        lines = []
        for cand in candidates:
            cached = ESI_CACHE.get_entity(cand)
            neg = ESI_CACHE.is_negative(cand)
            corr = ESI_CACHE.get_correction(cand)
            if corr and corr.get("action") == "ignore":
                state = "excluded"
            elif cached:
                state = f"cached: {cached.get('name')}"
            elif neg:
                state = "negative-cache"
            else:
                state = "candidate"
            lines.append(f"{cand} [{state}]")
        self.messagebox.showinfo("ESI Candidates", "\n".join(lines))

    def resolve_selected_esi_text(self):
        text = self.selected_feed_text()
        write_log(f"ESI resolve selected invoked: {text!r}")
        if not text:
            self.messagebox.showinfo("ESI", "No selected text. Highlight a character name first, or use Tools > Manual ESI Character Check...")
            self.set_status("No selected text for ESI")
            return
        self.direct_esi_check(text, force=True, show_dialog=True, add_to_feed=True)

    def add_selected_esi_character(self):
        text = self.selected_feed_text()
        write_log(f"ESI add selected invoked: {text!r}")
        if not text:
            self.messagebox.showinfo("ESI Add", "No selected text. Highlight a character name first.")
            self.set_status("No selected text for ESI add")
            return
        self.direct_esi_check(text, force=True, show_dialog=True, add_to_feed=True, action_label="Add")

    def manual_esi_check_dialog(self):
        name = self.simpledialog.askstring("Manual ESI Character Check", "Character name to check with ESI:", parent=self.root)
        if not name:
            return
        self.direct_esi_check(name.strip(), force=True, show_dialog=True, add_to_feed=True)

    def direct_esi_check(self, query: str, force: bool = False, show_dialog: bool = False, add_to_feed: bool = False, action_label: str = "Resolve"):
        query = re.sub(r"\s+", " ", str(query or "").strip())
        if not query:
            self.set_status("No ESI query")
            return
        if not self.esi_is_enabled():
            self.esi_enabled.set(True); self.save_esi_ui_settings()
        self.ensure_esi_resolver()
        write_log(f"ESI direct check requested: {query!r} force={force}")
        self.status_label.configure(text=f"Checking ESI: {query}")
        def worker():
            try:
                if is_esi_ignored(query) and not force:
                    ESI_CACHE.set_status("last_check", f"ignored: {query}")
                    self.queue.put(("esi_direct_result", query, {"ignored": True, "query": query, "source": "manual-ignore"}, None, show_dialog, add_to_feed, action_label))
                    return
                cached = ESI_CACHE.get_entity(query, force=force)
                if cached and not cached.get("ignored"):
                    ESI_CACHE.set_status("last_check", f"cache hit: {query} -> {cached.get('name')}")
                    write_log(f"ESI direct cache hit: {query!r} -> {cached.get('name')}")
                    self.queue.put(("esi_direct_result", query, cached, None, show_dialog, add_to_feed, action_label))
                    return
                resolver = self.esi_resolver or EsiResolver(self.queue, self.esi_is_enabled)
                data = resolver.resolve_public(query)
                ESI_CACHE.put_entity(query, data)
                ESI_CACHE.set_status("last_check", f"positive: {query} -> {data.get('name')}")
                write_log(f"ESI direct positive: {query!r} -> {data.get('name')}")
                self.queue.put(("esi_direct_result", query, data, None, show_dialog, add_to_feed, action_label))
            except Exception as exc:
                ESI_CACHE.put_negative(query, reason="direct_negative_or_error")
                ESI_CACHE.set_status("last_check", f"negative: {query}")
                ESI_CACHE.set_status("last_error", type(exc).__name__)
                write_log(f"ESI direct negative/error for {query!r}: {type(exc).__name__}", exc)
                self.queue.put(("esi_direct_result", query, None, exc, show_dialog, add_to_feed, action_label))
        threading.Thread(target=worker, daemon=True).start()

    def ignore_selected_esi_text(self):
        text = self.selected_feed_text()
        if not text:
            self.set_status("No selected text to exclude from ESI")
            return
        self.ignore_esi_entity(text)

    def show_esi_exclusion_list(self):
        win = self.tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=760, height=560, minsize=(620, 420), modal=True, title="Recognition Rules")
        def open_rules_help():
            # The dialog's modal grab would swallow clicks in the Help window.
            try:
                win.grab_release()
            except Exception:
                pass
            self.show_help_center("Recognition Rules")
        help_btn = self.tk.Button(win, text="?", width=2,
                                  **sb_theme.btn_secondary_kw(),
                                  command=open_rules_help)
        help_btn.place(relx=1.0, x=-14, y=10, anchor="ne")
        self.tk.Label(win, text="Recognition rules", **sb_theme.label_kw(),
                      font=sb_theme.font(10, bold=True)).pack(anchor="w", padx=12, pady=(12, 4))
        self.tk.Label(win, text="Use scoped rules when Signal Bridge recognizes, highlights, or checks the wrong text. Each scope changes a different part of the parser/rendering pipeline.", **sb_theme.label_kw(muted=True), wraplength=720, justify="left").pack(anchor="w", fill="x", padx=12, pady=(0, 6))

        scope_labels = {
            "pilot_ignore": "Ignored pilots",
            "highlight_exclude": "Highlight exclusions",
            "noise_word": "Noise words",
        }
        scope_help = {
            "pilot_ignore": "Stops a term from being sent to ESI or shown as a pilot. Use for false pilot names or bad partial names.",
            "highlight_exclude": "Keeps the text visible but removes colors/tags for matching highlights. Use when a real word is being colored as a ship, system, module, ESS, or pilot.",
            "noise_word": "Prevents common chat words/phrases from becoming pilot candidates. Use for phrases like 'thanks fc', 'ship on gate', or 'channel changed'.",
        }
        scope_examples = {
            "pilot_ignore": "Example: a random word keeps resolving as a pilot -> add it here.",
            "highlight_exclude": "Example: correct chat text gets the wrong color -> add it here, target 'any' unless you know the highlight type.",
            "noise_word": "Example: repeated non-name phrases clutter candidate checks -> add the phrase here.",
        }
        label_to_scope = {v: k for k, v in scope_labels.items()}
        scope_var = self.tk.StringVar(value="Ignored pilots")
        target_var = self.tk.StringVar(value="any")
        note_var = self.tk.StringVar()
        status_var = self.tk.StringVar(value="Choose the rule type first, then enter the term or phrase to control.")
        help_var = self.tk.StringVar()
        example_var = self.tk.StringVar()
        target_help_var = self.tk.StringVar()

        help_box = self.tk.Frame(win, bg=sb_theme.COLORS["bg_panel"], highlightthickness=1, highlightbackground=sb_theme.COLORS["border"])
        help_box.pack(fill="x", padx=12, pady=(0, 8))
        self.tk.Label(help_box, text="What should this rule do?", bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg"], font=sb_theme.font(9, bold=True)).pack(anchor="w", padx=8, pady=(6, 2))
        self.tk.Label(help_box, textvariable=help_var, bg=sb_theme.COLORS["bg_panel"], fg="#cfd8e3", wraplength=700, justify="left").pack(anchor="w", fill="x", padx=8)
        self.tk.Label(help_box, textvariable=example_var, bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_muted"], wraplength=700, justify="left").pack(anchor="w", fill="x", padx=8, pady=(2, 2))
        self.tk.Label(help_box, text="Quick guide: bad pilot match -> Ignored pilots | wrong color -> Highlight exclusions | common phrase -> Noise words | unsure -> use Test term", bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["success"], wraplength=700, justify="left").pack(anchor="w", fill="x", padx=8, pady=(0, 6))

        top = self.tk.Frame(win, bg=sb_theme.COLORS["bg"]); top.pack(fill="x", padx=12, pady=(0, 6))
        self.tk.Label(top, text="Scope", **sb_theme.label_kw(muted=True)).pack(side="left")
        scope_menu = self.tk.OptionMenu(top, scope_var, *scope_labels.values())
        scope_menu.configure(**sb_theme.optionmenu_kw())
        scope_menu.pack(side="left", padx=(6, 14))
        self.tk.Label(top, text="Target", **sb_theme.label_kw(muted=True)).pack(side="left")
        target_menu = self.tk.OptionMenu(top, target_var, "any", "pilot", "ship", "system", "module", "ess")
        target_menu.configure(**sb_theme.optionmenu_kw())
        target_menu.pack(side="left", padx=(6, 14))
        self.tk.Label(top, textvariable=status_var, **sb_theme.label_kw(muted=True), anchor="w").pack(side="left", fill="x", expand=True)
        self.tk.Label(win, textvariable=target_help_var, **sb_theme.label_kw(muted=True), anchor="w", justify="left", wraplength=720).pack(anchor="w", fill="x", padx=12, pady=(0, 4))

        frame = self.tk.Frame(win, bg=sb_theme.COLORS["bg"]); frame.pack(fill="both", expand=True, padx=12, pady=6)
        lb = self.tk.Listbox(frame, font=("Consolas", 9), **sb_theme.listbox_kw())
        sb = self.tk.Scrollbar(frame, command=lb.yview); lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")

        form = self.tk.Frame(win, bg=sb_theme.COLORS["bg"]); form.pack(fill="x", padx=12, pady=(4, 4))
        self.tk.Label(form, text="Term", **sb_theme.label_kw(muted=True)).grid(row=0, column=0, sticky="w")
        entry = self.tk.Entry(form, bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg"], insertbackground=sb_theme.COLORS["fg"], relief="flat")
        entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.tk.Label(form, text="Note", **sb_theme.label_kw(muted=True)).grid(row=0, column=1, sticky="w")
        note_entry = self.tk.Entry(form, textvariable=note_var, bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg"], insertbackground=sb_theme.COLORS["fg"], relief="flat")
        note_entry.grid(row=1, column=1, sticky="ew")
        form.grid_columnconfigure(0, weight=2); form.grid_columnconfigure(1, weight=1)

        state = {"rules": []}
        def current_scope():
            return label_to_scope.get(scope_var.get(), "pilot_ignore")
        def update_scope_help(*_args):
            scope = current_scope()
            help_var.set(scope_help.get(scope, ""))
            example_var.set(scope_examples.get(scope, ""))
            if scope == "highlight_exclude":
                target_help_var.set("Target applies only to Highlight exclusions. Use 'any' unless you only want to suppress one type, such as ship, system, module, ESS, or pilot.")
                try: target_menu.configure(state="normal")
                except Exception: pass
            else:
                target_var.set("any")
                target_help_var.set("Target is fixed to 'any' for this rule type.")
                try: target_menu.configure(state="disabled")
                except Exception: pass
        def rule_label(rule: dict) -> str:
            legacy = " legacy" if rule.get("legacy") else ""
            enabled = "" if rule.get("enabled", True) else " disabled"
            target = rule.get("target_kind") or "any"
            source = rule.get("source") or "user"
            return f"{rule.get('text',''):<34} | {scope_labels.get(rule.get('scope'), rule.get('scope')):<22} | {target:<8} | {source}{legacy}{enabled}"
        def reload_list(*_args):
            update_scope_help()
            scope = current_scope()
            rules = ESI_CACHE.list_exclusion_rules(scope)
            state["rules"] = rules
            lb.delete(0, "end")
            for rule in rules:
                lb.insert("end", rule_label(rule))
            status_var.set(f"Showing {len(rules)} {scope_labels.get(scope, scope).lower()} rule(s).")
        def add_rule():
            raw = entry.get().strip()
            if not raw:
                return
            scope = current_scope()
            target = target_var.get() if scope == "highlight_exclude" else "any"
            rid = ESI_CACHE.set_exclusion_rule(raw, scope, target, True, note_var.get(), "user")
            if rid:
                if scope == "pilot_ignore":
                    self.esi_entities.pop(normalize_esi_query(raw), None)
                entry.delete(0, "end"); note_var.set(""); reload_list(); self.set_status(f"Added recognition rule: {raw}")
        def remove_selected():
            sel = list(lb.curselection())
            if not sel:
                return
            removed = 0
            for idx in reversed(sel):
                if idx < 0 or idx >= len(state["rules"]):
                    continue
                rule = state["rules"][idx]
                if rule.get("legacy"):
                    # Remove the old broad ignore only when the selected row is legacy.
                    if ESI_CACHE.remove_correction(rule.get("text") or ""):
                        removed += 1
                else:
                    if ESI_CACHE.remove_exclusion_rule(rule.get("id")):
                        removed += 1
            reload_list(); self.set_status(f"Removed {removed} recognition rule(s)")
        def import_rules():
            raw = self.simpledialog.askstring("Import recognition rules", "Paste one term per line:", parent=win)
            if not raw:
                return
            scope = current_scope(); target = target_var.get() if scope == "highlight_exclude" else "any"; count = 0
            for line in raw.splitlines():
                term = line.strip()
                if term and ESI_CACHE.set_exclusion_rule(term, scope, target, True, "bulk import", "user"):
                    count += 1
            reload_list(); self.set_status(f"Imported {count} recognition rule(s)")
        def test_term():
            raw = entry.get().strip()
            if not raw:
                return
            pilot_blocked = is_esi_ignored(raw)
            highlight_hidden = is_highlight_excluded(raw)
            noise_blocked = is_parser_noise(raw)
            meaning = []
            if pilot_blocked:
                meaning.append("- will not be resolved through ESI as a pilot")
            if highlight_hidden:
                meaning.append("- will not receive entity highlight colors")
            if noise_blocked:
                meaning.append("- will not be considered as a parser/name candidate")
            if not meaning:
                meaning.append("- no scoped rule currently affects this term")
            msg = (
                f"Term: {raw}\n\n"
                f"Pilot recognition: {'blocked' if pilot_blocked else 'allowed'}\n"
                f"Highlighting: {'hidden' if highlight_hidden else 'allowed'}\n"
                f"Parser candidate: {'blocked' if noise_blocked else 'allowed'}\n\n"
                "Meaning:\n" + "\n".join(meaning)
            )
            self.messagebox.showinfo("Recognition Rule Test", msg)
        try:
            entry.bind("<Return>", lambda _event=None: add_rule())
            scope_var.trace_add("write", reload_list)
        except Exception:
            pass
        buttons = self.tk.Frame(win, bg=sb_theme.COLORS["bg"]); buttons.pack(fill="x", padx=12, pady=(0, 12))
        self.tk.Button(buttons, text="Add rule", command=add_rule,
                       **sb_theme.btn_secondary_kw()).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Remove selected", command=remove_selected,
                       **sb_theme.btn_secondary_kw()).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Import...", command=import_rules,
                       **sb_theme.btn_secondary_kw()).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Test term", command=test_term,
                       **sb_theme.btn_secondary_kw()).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Close", command=win.destroy,
                       **sb_theme.btn_secondary_kw()).pack(side="right")
        reload_list()

    def authorize_esi_character(self):
        settings = load_esi_settings()
        if not bool(self.esi_oauth_enabled.get()):
            self.messagebox.showinfo("ESI OAuth", "Enable OAuth features first in ESI settings."); return
        client_id = str(settings.get("client_id") or ESI_DEFAULT_CLIENT_ID).strip()
        client_secret = str(settings.get("client_secret") or "").strip()
        callback_url = str(settings.get("callback_url") or ESI_CALLBACK_URL).strip()
        if not client_secret:
            self.messagebox.showwarning("ESI OAuth", "Client secret is not configured. It is stored only in local config and is not committed to GitHub."); return
        if self.oauth_listener_active:
            self.messagebox.showinfo("ESI OAuth", "OAuth listener is already waiting for a callback."); return
        state = secrets.token_urlsafe(24)
        scopes = " ".join(settings.get("scopes") or [])
        params = {"response_type": "code", "redirect_uri": callback_url, "client_id": client_id, "state": state}
        if scopes:
            params["scope"] = scopes
        auth_url = ESI_SSO_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
        self.oauth_listener_active = True
        self.set_status("Opening ESI OAuth browser flow on localhost:8080...")
        threading.Thread(target=self._oauth_listener_worker, args=(state, client_id, client_secret, callback_url), daemon=True).start()
        webbrowser.open(auth_url)

    def _oauth_listener_worker(self, expected_state: str, client_id: str, client_secret: str, callback_url: str):
        result: dict = {}
        app = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != "/callback":
                    self.send_response(404); self.end_headers(); return
                qs = urllib.parse.parse_qs(parsed.query)
                result["code"] = (qs.get("code") or [""])[0]
                result["state"] = (qs.get("state") or [""])[0]
                ok = bool(result.get("code")) and result.get("state") == expected_state
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                msg = "Signal Bridge ESI authorization complete. You can close this browser tab." if ok else "Signal Bridge ESI authorization failed. Return to the app."
                self.wfile.write(msg.encode("utf-8"))
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        try:
            with socketserver.TCPServer((ESI_CALLBACK_HOST, ESI_CALLBACK_PORT), Handler) as httpd:
                httpd.timeout = 120
                end = time.time() + 120
                while time.time() < end and not result:
                    httpd.handle_request()
                if not result:
                    raise TimeoutError("OAuth callback timed out")
            if not result.get("code") or result.get("state") != expected_state:
                raise RuntimeError("OAuth state validation failed")
            token_data = self._exchange_esi_code(result["code"], client_id, client_secret, callback_url)
            save_esi_tokens({"updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "characters": token_data})
            ESI_CACHE.set_status("oauth", "authorized")
            app.queue.put(("status", "ESI OAuth authorization saved"))
        except OSError as exc:
            write_log("ESI OAuth listener failed; port may be busy", exc)
            app.queue.put(("esi_oauth_failed", "Could not listen on localhost:8080. Another app may be using the port."))
        except Exception as exc:
            write_log("ESI OAuth failed", exc)
            app.queue.put(("esi_oauth_failed", str(exc)))
        finally:
            app.oauth_listener_active = False

    def _exchange_esi_code(self, code: str, client_id: str, client_secret: str, callback_url: str) -> dict:
        body = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "redirect_uri": callback_url}).encode("utf-8")
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        req = urllib.request.Request(ESI_SSO_TOKEN_URL, data=body, headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": ESI_USER_AGENT, "Accept": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            token = json.loads(resp.read().decode("utf-8", "replace"))
        verify_req = urllib.request.Request(ESI_SSO_VERIFY_URL, headers={"Authorization": "Bearer " + str(token.get("access_token", "")), "User-Agent": ESI_USER_AGENT, "Accept": "application/json"})
        character = {}
        try:
            with urllib.request.urlopen(verify_req, timeout=12) as resp:
                character = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception:
            character = {}
        expires_in = int(token.get("expires_in") or 0)
        char_id = str(character.get("CharacterID") or "unknown")
        return {char_id: {"character_id": character.get("CharacterID"), "character_name": character.get("CharacterName"), "scopes": character.get("Scopes", ""), "access_token": token.get("access_token"), "refresh_token": token.get("refresh_token"), "expires_at": time.time() + expires_in}}

    def refresh_esi_entity(self, query: str):
        if not query:
            self.messagebox.showinfo("ESI", "No ESI name was available for this action.")
            return
        write_log(f"ESI refresh invoked: {query!r}")
        self.direct_esi_check(query, force=True, show_dialog=True, add_to_feed=True)

    def ignore_esi_entity(self, query: str):
        if query and ESI_CACHE.set_exclusion_rule(query, "pilot_ignore", note="user ignored", source="context menu"):
            self.esi_entities.pop(normalize_esi_query(query), None)
            self.set_status(f"Ignored as pilot: {query}")

    def set_status(self, msg: str):
        self.queue.put(("status", msg))

    def apply_topmost(self):
        self.root.attributes("-topmost", bool(self.always_on_top.get()))
        self.persist_settings()

    def start_monitor(self):
        if self.monitor and self.monitor.is_alive():
            self.set_status("Already monitoring")
            return
        self.stop_event = threading.Event()
        if not self.active_channels:
            self.set_status("No channels selected; use Channels > Choose / Open Channels...")
            return
        backlog_minutes = 0
        if bool(SETTINGS.get("replay_on_start", False)):
            backlog_minutes = max(1, min(360, int(SETTINGS.get("backlog_minutes", 10) or 10)))
        self.monitor = MonitorThread(
            self.queue,
            self.stop_event,
            self.set_status,
            set(self.active_channels),
            backlog_minutes=backlog_minutes,
        )
        self.monitor.start()
        write_log(
            f"Monitor starting for {len(self.active_channels)} channel(s); backlog_minutes={backlog_minutes}"
        )
        self.set_status("Starting monitor...")

    def stop_monitor(self):
        if self.stop_event:
            self.stop_event.set()
        write_log("Monitor stopped")
        self.set_status("Stopped")

    def clear_feed(self):
        self.rows.clear()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.row_count = 0
        self.rendered_row_map.clear()
        self.link_map.clear()

    def open_folder(self):
        import os
        if CHATLOG_DIR.exists():
            os.startfile(str(CHATLOG_DIR))
        else:
            self.set_status("Chatlog folder does not exist; use Settings > Choose Chatlog Folder...")

    def check_catalog_updates(self):
        def worker():
            try:
                req = urllib.request.Request(CATALOG_MANIFEST_URL, headers={"User-Agent": f"SignalBridge/{APP_VERSION}"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    remote = json.loads(resp.read().decode("utf-8", "replace"))
                local_sha = hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest().upper() if CATALOG_PATH.exists() else ""
                if str(remote.get("sha256", "")).upper() == local_sha:
                    self.queue.put(("catalog_current", remote.get("catalog_version", "current")))
                    return
                self.queue.put(("catalog_available", remote))
            except Exception as exc:
                write_log("Catalog update check failed", exc); self.queue.put(("catalog_failed", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def download_catalog_update(self, manifest: dict):
        def worker():
            try:
                url = manifest.get("download_url") or manifest.get("url")
                expected = str(manifest.get("sha256", "")).upper()
                if not url or not expected:
                    raise RuntimeError("Manifest missing download_url or sha256")
                tmp = DATA_DIR / "eve_catalog.download.json"
                urllib.request.urlretrieve(url, tmp)
                actual = hashlib.sha256(tmp.read_bytes()).hexdigest().upper()
                if actual != expected:
                    tmp.unlink(missing_ok=True); raise RuntimeError(f"Catalog SHA256 mismatch: {actual}")
                if CATALOG_PATH.exists():
                    CATALOG_PREVIOUS_PATH.write_bytes(CATALOG_PATH.read_bytes())
                tmp.replace(CATALOG_PATH)
                CATALOG_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
                CATALOG.load()
                self.queue.put(("catalog_updated", manifest.get("catalog_version", "updated")))
            except Exception as exc:
                write_log("Catalog update failed", exc); self.queue.put(("catalog_failed", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def restore_previous_catalog(self):
        if not CATALOG_PREVIOUS_PATH.exists():
            self.messagebox.showinfo("Translation Catalog", "No previous catalog backup found."); return
        if not self.messagebox.askyesno("Translation Catalog", "Restore previous EVE catalog?"):
            return
        CATALOG_PATH.write_bytes(CATALOG_PREVIOUS_PATH.read_bytes())
        CATALOG.load(); self.set_status("Previous catalog restored")

    def show_translation_cache(self):
        count, hits = TRANSLATION_CACHE.stats()
        self.messagebox.showinfo("Translation Cache", f"Cache file: {TRANSLATION_CACHE_PATH}\nEntries: {count}\nHits: {hits}\nManual overrides: {TRANSLATION_CACHE.override_count()}\nMode: {self.translation_cache_mode.get()}\nFallback: {self.translation_fallback_mode.get()}")

    def clear_translation_cache(self):
        if self.messagebox.askyesno("Translation Cache", "Clear cached machine translations? Manual overrides are kept."):
            if TRANSLATION_CACHE.clear():
                FREE_TRANSLATION_CACHE.clear(); self.set_status("Translation cache cleared")

    def open_phrase_overrides(self):
        import os
        PHRASE_OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not PHRASE_OVERRIDES_PATH.exists():
            PHRASE_OVERRIDES_PATH.write_text(json.dumps({"schema_version": 1, "overrides": []}, indent=2), encoding="utf-8")
        os.startfile(str(PHRASE_OVERRIDES_PATH))

    def check_for_updates(self, manual: bool = False):
        def worker():
            try:
                req = urllib.request.Request(
                    UPDATE_API_URL,
                    headers={"User-Agent": f"SignalBridge/{APP_VERSION}", "Accept": "application/vnd.github+json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                tag = str(data.get("tag_name") or "").strip()
                html_url = str(data.get("html_url") or UPDATE_RELEASE_URL)
                if tag and is_newer_version(tag, APP_VERSION):
                    self.queue.put(("update_available", tag, html_url))
                    write_log(f"Update available: {tag} {html_url}")
                else:
                    write_log(f"Update check OK: current={APP_VERSION} latest={tag or 'unknown'}")
                    if manual:
                        self.queue.put(("update_current", tag or APP_VERSION))
            except Exception as exc:
                write_log("Update check failed", exc)
                if manual:
                    self.queue.put(("update_failed", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def show_update_available(self, tag: str, url: str):
        if self.messagebox.askyesno("Signal Bridge Update Available", f"A newer Signal Bridge release is available: {tag}\n\nOpen the GitHub release page?"):
            self.open_url(url)

    def show_help_center(self, topic: str | None = None):
        titles = [t for t, _f in sb_help.HELP_TOPICS]

        def make_renderer(filename):
            def render(body, shell):
                text = self.tk.Text(body, wrap="word", relief="flat", bd=0,
                                    bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg"],
                                    highlightthickness=0, padx=4, pady=4, height=26)
                text.pack(fill="both", expand=True)
                sb_markdown.render_into(
                    text, sb_markdown.parse_markdown(sb_help.load_topic(APP_DIR, filename)))
            return render

        shell = SettingsShell(
            self.root,
            pages=titles,
            descriptions={t: "" for t in titles},
            renderers={t: make_renderer(f) for t, f in sb_help.HELP_TOPICS},
            on_apply=lambda: True,
            polish=self.polish_window,
            initial_page=topic if topic in titles else titles[0],
            title="Help - Signal Bridge",
            nav_title="Help",
            show_apply=False,
        )
        shell.open()
        record_event("help_center_opened", topic=topic or titles[0])

    def show_about_window(self):
        tk = self.tk
        win = tk.Toplevel(self.root)
        self.polish_window(win, self.root, width=540, height=500, minsize=(500, 440),
                           title="About Signal Bridge")
        footer = tk.Frame(win, bg=sb_theme.COLORS["bg_panel"])
        footer.pack(fill="x", side="bottom")
        tk.Button(footer, text="Close", command=win.destroy, padx=16,
                  **sb_theme.btn_primary_kw()).pack(side="right", padx=12, pady=8)
        body = tk.Frame(win, bg=sb_theme.COLORS["bg"], padx=14, pady=10)
        body.pack(fill="both", expand=True)

        def link(parent, text, url):
            lbl = tk.Label(parent, text=text, bg=parent.cget("bg"), fg="#5ad7ff",
                           cursor="hand2", anchor="w")
            lbl.pack(anchor="w", pady=1)
            lbl.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))

        c = sb_components.card(body, f"Signal Bridge v{APP_VERSION}")
        sb_components.info_label(
            c, "Lightweight Windows app for live EVE chat monitoring, "
               "CN <-> EN translation, and intel highlighting.", muted=True,
            wraplength=440)
        link(c, "GitHub: github.com/gregoryhorn/signal-bridge", GITHUB_REPO_URL)
        link(c, "Latest release", UPDATE_RELEASE_URL)
        link(c, "Report an issue", ISSUE_REPORT_URL)
        r = sb_components.action_row(c)
        sb_components.action_button(r, "Copy Diagnostics", self.copy_diagnostics)
        sb_components.action_button(r, "Check for Updates",
                                    lambda: self.check_for_updates(manual=True))

        c2 = sb_components.card(body, "Support Development",
                                "If you like this app and want further development, "
                                "you can donate some ISK in game.")
        sb_components.info_label(c2, "Donate ISK to: Mizz Betty",
                                 fg=sb_theme.COLORS["gold"])
        sb_components.info_label(c2, DONATION_TEXT, muted=True, wraplength=440)
        r2 = sb_components.action_row(c2)
        sb_components.action_button(r2, "Copy Character Name",
                                    lambda: self.copy_to_clipboard("Mizz Betty"))
        sb_components.action_button(r2, "Copy Donation Message",
                                    lambda: self.copy_to_clipboard(DONATION_TEXT))
        record_event("about_window_opened")

    def show_about(self):
        self.show_about_window()

    def show_support(self):
        self.show_about_window()

    def show_health(self):
        active = ', '.join(sorted(self.active_channels)) or 'none'
        discovered = len(discover_channels())
        self.messagebox.showinfo(
            "Signal Bridge Health",
            f"Version: {APP_VERSION}\n"
            f"Chatlogs: {CHATLOG_DIR}\n"
            f"Chatlogs exists: {CHATLOG_DIR.exists()}\n"
            f"Catalog: {CATALOG_PATH}\n"
            f"Catalog loaded: {CATALOG.loaded}\n"
            f"Catalog version: {CATALOG.version}\n"
            f"Catalog counts: {CATALOG.counts()}\n"
            f"Previous catalog backup: {CATALOG_PREVIOUS_PATH.exists()}\n"
            f"Advanced DB fallback exists: {DB_PATH.exists()}\n"
            f"Discovered channels: {discovered}\n"
            f"Active channels: {active}\n"
            f"Visible tab: {self.visible_channel}\n"
            f"Hidden tabs: {len(self.hidden_tab_ids)}\n"
            f"Config: {CONFIG_PATH}\n"
            f"App folder: {USER_DIR}\n"
            f"Log file: {LOG_PATH}\n"
            f"Font: {self.font_family.get()} {int(self.font_size.get())}\n"
            f"Show timestamps: {bool(self.show_timestamps.get())}\n"
            "Free MT: Google primary, Argos fallback\n"
            "Directions: Auto -> EN / EN -> CN\n"
            f"Update check on launch: {bool(self.check_updates_on_start.get())}\n"
            f"ESI enabled: {bool(self.esi_enabled.get())}\n"
            f"ESI OAuth token file: {ESI_TOKENS_PATH.exists()}\n"
            f"ESI cache: {ESI_CACHE.stats()}"
        )


    def on_exit(self):
        record_event("app_exit", uptime_seconds=int(time.time() - float(self.diagnostics.get("started_at", time.time()))))
        self.persist_settings()
        try:
            self.stop_lan_viewer()
        except Exception:
            pass
        if self.esi_resolver:
            self.esi_resolver.stop()
        try:
            self.translation_stop_event.set()
        except Exception:
            pass
        self.stop_monitor()
        self.root.after(100, self.root.destroy)

    def _lan_config(self) -> sb_lan.LanConfig:
        token = str(getattr(self, "lan_token", "") or SETTINGS.get("lan_token") or "")
        if not token:
            token = sb_lan.new_token()
            self.lan_token = token
        try:
            port = int(self.lan_port.get())
        except Exception:
            port = 8765
        return sb_lan.LanConfig(
            enabled=bool(self.lan_enabled.get()),
            host=str(SETTINGS.get("lan_host") or "0.0.0.0"),
            port=port,
            token=token,
        )

    def lan_public_url(self) -> str:
        if not bool(self.lan_enabled.get()):
            return ""
        try:
            return self.lan_server.public_url()
        except Exception:
            cfg = self._lan_config()
            return f"http://{sb_lan.discover_lan_ip()}:{cfg.port}/?token={cfg.token}"

    def start_lan_viewer(self) -> str:
        cfg = self._lan_config()
        cfg = sb_lan.LanConfig(True, cfg.host, cfg.port, cfg.token)
        self.lan_enabled.set(True)
        self.lan_token = cfg.token
        theme = sb_theme.export_theme_dict()
        url = self.lan_server.start(cfg, theme=theme)
        self.persist_settings()
        self.set_status("LAN viewer sharing")
        record_event("lan_viewer_start", port=cfg.port)
        if getattr(self, "lan_url_var", None) is not None:
            self.lan_url_var.set(url)
        return url

    def stop_lan_viewer(self) -> None:
        try:
            self.lan_server.stop()
        except Exception:
            pass
        if getattr(self, "lan_enabled", None) is not None:
            # do not force-clear user preference on exit-only stop; only clear if toggled off
            pass
        record_event("lan_viewer_stop")
        if getattr(self, "lan_url_var", None) is not None:
            self.lan_url_var.set(self.lan_public_url() or "(disabled)")

    def toggle_lan_viewer(self) -> None:
        if bool(self.lan_enabled.get()):
            try:
                self.start_lan_viewer()
            except Exception as exc:
                self.lan_enabled.set(False)
                write_log("LAN viewer start failed", exc)
                self.messagebox.showerror("LAN Viewer", f"Could not start LAN viewer:\n{exc}")
        else:
            self.stop_lan_viewer()
            self.persist_settings()
            self.set_status("LAN viewer stopped")
            if getattr(self, "lan_url_var", None) is not None:
                self.lan_url_var.set("(disabled)")

    def regen_lan_token(self) -> None:
        self.lan_token = sb_lan.new_token()
        SETTINGS["lan_token"] = self.lan_token
        if bool(self.lan_enabled.get()):
            self.start_lan_viewer()
        else:
            self.persist_settings()
        if getattr(self, "lan_url_var", None) is not None:
            self.lan_url_var.set(self.lan_public_url() or "(disabled)")
        self.set_status("LAN token regenerated")

    def apply_lan_port(self) -> None:
        self.persist_settings()
        if bool(self.lan_enabled.get()):
            self.start_lan_viewer()
        self.set_status("LAN port updated")

    def copy_lan_url(self) -> None:
        url = self.lan_public_url()
        if not url:
            self.set_status("LAN viewer is disabled")
            return
        self.copy_to_clipboard(url)

    def _render_settings_lan(self, body, shell=None):
        from sb_ui.lan_page import render_lan_page
        render_lan_page(
            body,
            self,
            get_url=self.lan_public_url,
            get_clients=lambda: self.lan_server.client_count() if bool(self.lan_enabled.get()) else 0,
            on_toggle=self.toggle_lan_viewer,
            on_regen_token=self.regen_lan_token,
            on_copy_url=self.copy_lan_url,
            on_apply_port=self.apply_lan_port,
        )

    def publish_lan_row(self, row: "Row", visible_text: str, row_id: str = "") -> None:
        if not bool(getattr(self, "lan_enabled", None) and self.lan_enabled.get()):
            return
        try:
            payload = sb_lan.payload_from_row_object(row, visible_text=visible_text, row_id=row_id)
            self.lan_server.publish(payload)
        except Exception as exc:
            write_log("LAN publish failed", exc)

    def segment_display_lines(self, row: Row, translated_text: str) -> list[str]:
        return render_model.segment_display_lines(row, translated_text, normalize_feed_text)

    def row_visible_body_lines(self, row: Row, parts: dict) -> list[str]:
        # Normal feed should show catalog/user alias canonical replacements, not raw aliases.
        # Copy Original still preserves the unmodified chat text via parts["original_text"].
        return render_model.visible_body_lines(row, parts["translated"], parts["display_text"], bool(self.translated_only.get()), normalize_feed_text)

    def row_uses_multiline_segments(self, row: Row) -> bool:
        return render_model.row_uses_multiline_segments(row)

    def row_display_parts(self, row: Row) -> dict:
        original_text = normalize_feed_text(row.text)
        display_text = self.localized_display_text(row)
        free_text = normalize_feed_text(self.display_free_translation(row, display_text))
        translated = free_text or display_text
        show_channel = bool(self.show_channel_names.get()) or (self.visible_channel == ALL_CHANNELS_TAB and bool(self.show_channel_names_in_all.get()))
        prefix = ""
        if bool(self.show_timestamps.get()):
            prefix += f"[{row.received_at.split()[-1]}] "
        if show_channel:
            prefix += f"[{row.channel}] "
        sender_prefix = f"{row.sender} > "
        visible_text = translated if bool(self.translated_only.get()) else display_text
        visible_line = prefix + sender_prefix + visible_text
        original_line = prefix + sender_prefix + original_text
        translated_line = prefix + sender_prefix + translated
        return {
            "original_text": original_text,
            "display_text": display_text,
            "free_text": free_text,
            "translated": translated,
            "visible_line": visible_line,
            "original_line": original_line,
            "translated_line": translated_line,
            "source_label": row.translation_source,
        }

    def row_at_event(self, event) -> tuple[str | None, dict | None]:
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            for tag in self.text.tag_names(index):
                if tag.startswith("row_"):
                    return tag, self.rendered_row_map.get(tag)
        except Exception:
            pass
        return None, None

    def link_at_event(self, event) -> str | None:
        if not bool(getattr(self, "enable_hyperlinks", None).get() if getattr(self, "enable_hyperlinks", None) is not None else SETTINGS.get("enable_hyperlinks", True)):
            return None
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            for tag in self.text.tag_names(index):
                if tag.startswith("link_"):
                    return self.link_map.get(tag)
        except Exception:
            pass
        return None


    def intel_history_call(self, method: str, *args, notify: bool = False, **kwargs):
        runtime = self.intel_history_runtime
        if not runtime or not runtime.enabled:
            self.intel_history_last_health = dict(self.intel_history_last_health or {})
            self.intel_history_last_health.setdefault("last_error", "Intel History is not installed/enabled")
            if notify:
                self.messagebox.showinfo("Intel History", "Intel History is not installed/enabled yet.\n\nInstall and enable it from Settings > Add-ons.")
            return None
        return runtime.safe_call(method, *args, **kwargs)

    def first_character_for_row(self, row: Row | None) -> dict | None:
        if not row:
            return None
        self.hydrate_esi_entities_for_row(row)
        for ent in row.esi_entities:
            if ent.get("entity_type") == "character" and ent.get("entity_id"):
                return ent
        return None


    def intel_history_active_flags(self, pilot_id: int) -> list[dict]:
        flags = self.intel_history_call("get_active_flags", int(pilot_id))
        return flags if isinstance(flags, list) else []

    def pilot_flag_badges(self, flags: list[dict], limit: int = 2) -> str:
        priority = {
            "extreme threat": 10,
            "high threat": 20,
            "hot dropper": 30,
            "watchlist": 40,
            "fc": 50,
            "scout": 60,
            "friendly": 70,
            "do not track": 80,
        }
        compact = {
            "extreme threat": "☠",
            "high threat": "⚠",
            "hot dropper": "🔥",
            "watchlist": "⭐",
            "fc": "👑",
            "scout": "👁",
            "friendly": "✓",
            "do not track": "DNT",
        }
        def key(item):
            label = str(item.get("label") or item.get("flag") or "").casefold()
            return (priority.get(label, 500), label)
        out = []
        seen = set()
        for flag in sorted(flags, key=key):
            label = str(flag.get("label") or flag.get("flag") or "").strip()
            if not label or label.casefold() in seen:
                continue
            seen.add(label.casefold())
            out.append(str(flag.get("icon") or compact.get(label.casefold()) or label[:3]).strip())
            if len(out) >= limit:
                break
        return " ".join([x for x in out if x])

    def pilot_flag_badges_for_row(self, row: Row) -> dict[str, str]:
        badges: dict[str, str] = {}
        for ent in getattr(row, "esi_entities", []) or []:
            if ent.get("entity_type") != "character" or not ent.get("entity_id"):
                continue
            flags = self.intel_history_active_flags(int(ent.get("entity_id")))
            badge = self.pilot_flag_badges(flags)
            if badge:
                for key in (ent.get("name"), ent.get("query")):
                    if key:
                        badges[str(key)] = badge
        return badges

    def apply_pilot_flag_badges(self, row: Row, text: str) -> str:
        badges = self.pilot_flag_badges_for_row(row)
        if not badges or not text:
            return text
        result = text
        for name, badge in sorted(badges.items(), key=lambda kv: len(kv[0]), reverse=True):
            if not name or badge in name:
                continue
            # Simple literal replacement keeps this dependency-free and predictable.
            result = result.replace(name, f"{name} {badge}")
        return result

    def quick_set_pilot_flag(self, ent: dict | None, label: str, icon: str = ""):
        if not ent or not ent.get("entity_id"):
            self.messagebox.showinfo("Pilot Flags", "No ESI-confirmed pilot was found at the clicked text.")
            return
        pilot_id = int(ent.get("entity_id"))
        current = self.intel_history_active_flags(pilot_id)
        manual = []
        exists = False
        for flag in current:
            if flag.get("source") == "manual":
                item_label = str(flag.get("label") or flag.get("flag") or "")
                manual.append({"flag": item_label, "label": item_label, "icon": flag.get("icon") or "", "reason": flag.get("reason") or ""})
                if item_label.casefold() == label.casefold():
                    exists = True
        if not exists:
            manual.append({"flag": label, "label": label, "icon": icon, "reason": "quick flag from feed"})
        result = self.intel_history_call("set_manual_flags", pilot_id, manual, notify=True)
        if result and result.get("ok"):
            self.set_status(f"Pilot flag set: {ent.get('name') or ent.get('query')} -> {label}")
            self.redraw_feed()
        else:
            self.messagebox.showwarning("Pilot Flags", f"Could not save flag: {result}")

    def quick_set_pilot_flag_for_row(self, row: Row | None, label: str, icon: str = ""):
        self.quick_set_pilot_flag(self.first_character_for_row(row), label, icon)

    def open_pilot_info_for_row(self, row: Row | None):
        ent = self.first_character_for_row(row)
        if not ent:
            self.messagebox.showinfo("Pilot Info", "No ESI-confirmed pilot was found for this row yet.")
            return
        self.open_pilot_info(ent)

    def open_pilot_info(self, ent: dict):
        import sb_pilot
        ref = sb_pilot.resolve_from_entity(ent)
        if not ref:
            return
        profile = self.intel_history_call(
            "get_pilot_profile",
            pilot_id=ref.entity_id,
            name=ref.name or ref.query,
        )
        if not profile:
            profile = sb_pilot.empty_profile_for_ref(ref)
        elif not profile.get("found"):
            profile = sb_pilot.empty_profile_for_ref(ref)
        self.show_pilot_info_card(profile)

    def load_zkill_cache(self) -> dict:
        try:
            if ZKILL_CACHE_PATH.exists():
                data = json.loads(ZKILL_CACHE_PATH.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            write_log("zKill cache load failed", exc)
        return {}

    def save_zkill_cache(self, data: dict) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            ZKILL_CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            write_log("zKill cache save failed", exc)

    def get_zkill_summary(self, pilot_id: int) -> dict:
        cache = self.load_zkill_cache()
        return cache.get(str(int(pilot_id))) or {"status": "not_synced"}

    def set_zkill_summary(self, pilot_id: int, summary: dict) -> None:
        cache = self.load_zkill_cache()
        cache[str(int(pilot_id))] = summary
        self.save_zkill_cache(cache)

    def zkill_type_name(self, type_id: int | None, type_cache: dict) -> str:
        if not type_id:
            return ""
        key = str(int(type_id))
        if key in type_cache:
            return str(type_cache.get(key) or "")
        try:
            url = f"https://esi.evetech.net/latest/universe/types/{int(type_id)}/?datasource=tranquility&language=en"
            req = urllib.request.Request(url, headers={"User-Agent": f"SignalBridge/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
            name = str(payload.get("name") or "") if isinstance(payload, dict) else ""
        except Exception:
            name = f"type {int(type_id)}"
        type_cache[key] = name
        return name

    def zkill_api_list(self, kind: str, pilot_id: int) -> tuple[list[dict], str, str]:
        """Fetch a zKill list, falling back when modifier URLs return an error dict."""
        headers = {"User-Agent": f"SignalBridge/{APP_VERSION} contact=github.com/gregoryhorn/signal-bridge"}
        urls = [
            (f"https://zkillboard.com/api/{kind}/characterID/{int(pilot_id)}/pastSeconds/2592000/", "30d"),
            (f"https://zkillboard.com/api/{kind}/characterID/{int(pilot_id)}/", "latest"),
        ]
        last_error = ""
        for url, scope in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                if isinstance(payload, list):
                    return payload, scope, ""
                if isinstance(payload, dict):
                    last_error = str(payload.get("error") or payload.get("message") or payload)[:240]
                    record_event("zkill_api_nonlist", pilot_id=int(pilot_id), kind=kind, scope=scope, error=last_error)
                else:
                    last_error = f"unexpected payload: {type(payload).__name__}"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                record_event("zkill_api_failed", pilot_id=int(pilot_id), kind=kind, scope=scope, error=last_error[:240])
            time.sleep(1.1)
        return [], "failed", last_error

    def zkill_hydrate_killmail(self, item: dict, detail_cache: dict) -> dict:
        """Hydrate zKill list rows with ESI killmail details when possible."""
        if not isinstance(item, dict):
            return {}
        killmail_id = int(item.get("killmail_id") or 0)
        zkb = item.get("zkb") or {}
        km_hash = str(zkb.get("hash") or item.get("hash") or "")
        if not killmail_id or not km_hash:
            return item
        key = str(killmail_id)
        cached = detail_cache.get(key)
        if isinstance(cached, dict) and cached.get("killmail_id"):
            merged = dict(cached)
            merged["zkb"] = zkb or merged.get("zkb") or {}
            return merged
        try:
            url = f"https://esi.evetech.net/latest/killmails/{killmail_id}/{km_hash}/?datasource=tranquility"
            req = urllib.request.Request(url, headers={"User-Agent": f"SignalBridge/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                detail = json.loads(resp.read().decode("utf-8", "replace"))
            if isinstance(detail, dict):
                detail["zkb"] = zkb
                detail_cache[key] = detail
                return detail
        except Exception as exc:
            record_event("zkill_killmail_hydrate_failed", killmail_id=killmail_id, error=f"{type(exc).__name__}: {exc}"[:240])
        return item

    def zkill_event_from_killmail(self, item: dict, kind: str, pilot_id: int, type_cache: dict) -> dict:
        victim = item.get("victim") or {}
        attackers = item.get("attackers") or []
        role = "loss" if kind == "losses" else "kill"
        ship_type_id = victim.get("ship_type_id")
        if kind == "kills":
            for attacker in attackers:
                try:
                    if int(attacker.get("character_id") or 0) == int(pilot_id):
                        ship_type_id = attacker.get("ship_type_id") or ship_type_id
                        break
                except Exception:
                    pass
        ship = self.zkill_type_name(ship_type_id, type_cache)
        return {
            "type": "loss" if kind == "losses" else "kill",
            "time": str(item.get("killmail_time") or ""),
            "ship": ship,
            "ship_type_id": int(ship_type_id or 0),
            "system_id": int(item.get("solar_system_id") or 0),
            "value": float(((item.get("zkb") or {}).get("totalValue") or 0)),
            "killmail_id": int(item.get("killmail_id") or 0),
            "role": role,
            "participants": len(attackers),
        }

    def start_zkill_sync(self, pilot_id: int, pilot_name: str, callback):
        def worker():
            started = time.time()
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            summary = {"status": "failed", "synced_at": now, "last_error": "unknown"}
            ok = False
            try:
                cache = self.load_zkill_cache()
                type_cache = dict(cache.get("type_names") or {})
                detail_cache = dict(cache.get("killmail_details") or {})
                out = {}
                scopes = {}
                errors = {}
                for kind in ("kills", "losses"):
                    payload, scope, err = self.zkill_api_list(kind, int(pilot_id))
                    out[kind] = payload
                    scopes[kind] = scope
                    if err:
                        errors[kind] = err
                kills = out.get("kills") or []
                losses = out.get("losses") or []
                if not kills and not losses and errors:
                    raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
                all_items = kills + losses
                latest = ""
                try:
                    latest = max(str(x.get("killmail_time") or "") for x in all_items) if all_items else ""
                except Exception:
                    latest = ""
                recent_events = []
                for kind, items in (("kills", kills), ("losses", losses)):
                    for item in items[:8]:
                        try:
                            detail = self.zkill_hydrate_killmail(item, detail_cache)
                            recent_events.append(self.zkill_event_from_killmail(detail, kind, int(pilot_id), type_cache))
                            time.sleep(0.25)
                        except Exception as exc:
                            write_log("zKill event parse failed", exc)
                recent_events.sort(key=lambda x: str(x.get("time") or ""), reverse=True)
                recent_events = recent_events[:16]
                isk_destroyed = sum(float(((x.get("zkb") or {}).get("totalValue") or 0)) for x in kills[:50])
                isk_lost = sum(float(((x.get("zkb") or {}).get("totalValue") or 0)) for x in losses[:50])
                danger = []
                if len(kills) >= 10:
                    danger.append("active killer")
                if any(float(((x.get("zkb") or {}).get("totalValue") or 0)) >= 1_000_000_000 for x in kills[:20]):
                    danger.append("high-value kills")
                if len(losses) >= 10:
                    danger.append("frequent losses")
                if recent_events:
                    newest = recent_events[0]
                    if str(newest.get("time") or "")[:10] == time.strftime("%Y-%m-%d", time.gmtime()):
                        danger.append("active today")
                summary = {
                    "status": "synced",
                    "pilot_id": int(pilot_id),
                    "pilot_name": pilot_name,
                    "synced_at": now,
                    "latest_killmail": latest,
                    "recent_kills_30d": len(kills),
                    "recent_losses_30d": len(losses),
                    "zkill_scopes": scopes,
                    "zkill_scope_note": "30d when available; latest-page fallback when zKill rejects time-filtered API modifiers",
                    "isk_destroyed_30d": round(isk_destroyed),
                    "isk_lost_30d": round(isk_lost),
                    "danger_tags": sorted(set(danger)),
                    "recent_events": recent_events,
                    "recent_kills": sb_zkill.rank_kills(recent_events, 5),
                    "recent_losses": sb_zkill.pick_losses(recent_events, 5),
                    "duration_ms": int((time.time() - started) * 1000),
                    "last_error": "",
                }
                # Bound the detail cache so the JSON cache remains lightweight.
                if len(detail_cache) > 400:
                    detail_cache = dict(list(detail_cache.items())[-400:])
                cache[str(int(pilot_id))] = summary
                cache["type_names"] = type_cache
                cache["killmail_details"] = detail_cache
                self.save_zkill_cache(cache)
                ok = True
                record_event("zkill_sync_completed", pilot_id=int(pilot_id), kills=len(kills), losses=len(losses), events=len(recent_events), duration_ms=summary["duration_ms"])
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                summary = {"status": "failed", "pilot_id": int(pilot_id), "pilot_name": pilot_name, "synced_at": now, "last_error": err, "duration_ms": int((time.time() - started) * 1000)}
                self.set_zkill_summary(int(pilot_id), summary)
                write_log("zKill sync failed", exc)
                record_event("zkill_sync_failed", pilot_id=int(pilot_id), error=err[:240], duration_ms=summary["duration_ms"])
            self.queue.put(("zkill_sync_result", ok, summary, pilot_id, callback))
        record_event("zkill_sync_started", pilot_id=int(pilot_id))
        threading.Thread(target=worker, daemon=True).start()


    def _render_settings_pilot_intel(self, body, shell=None):
        from sb_ui.pilot.settings_page import render_pilot_intel_page
        render_pilot_intel_page(
            body,
            self,
            open_addons=lambda: self.show_settings_center("Add-ons"),
            open_help=lambda: self.show_help_center("Pilot Info"),
            open_recognition=lambda: self.show_settings_center("Recognition Rules"),
        )

    def show_pilot_info_card(self, profile: dict):
        from sb_ui.pilot import open_pilot_card
        open_pilot_card(self, profile)

    def clicked_context(self, event, row: Row | None) -> dict:
        """Resolve the exact clicked token/span for the context menu.

        Do not fall back to the sender/first ESI entity unless the clicked text
        is actually inside that pilot name. This prevents right-clicking systems
        or ships from opening Pilot Info for the sender.
        """
        text = ""
        line_text = ""
        clicked_col = -1
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            start = self.text.index(f"{index} wordstart")
            end = self.text.index(f"{index} wordend")
            text = self.text.get(start, end).strip(" [](),;:>\n\t")
            line_start = self.text.index(f"{index} linestart")
            line_end = self.text.index(f"{index} lineend")
            line_text = self.text.get(line_start, line_end)
            count = self.text.count(line_start, index, "chars")
            clicked_col = int(count[0]) if count else -1
        except Exception:
            text = ""
        if not row:
            return {"kind": "none", "text": text}

        def clicked_span(term: str) -> tuple[int, int] | None:
            if clicked_col < 0 or not term or not line_text:
                return None
            hay = line_text.casefold()
            needle = str(term).casefold()
            pos = hay.find(needle)
            while pos >= 0:
                end_pos = pos + len(str(term))
                if pos <= clicked_col < end_pos:
                    return (pos, end_pos)
                pos = hay.find(needle, pos + 1)
            return None

        def clicked_inside(term: str) -> bool:
            return clicked_span(term) is not None

        self.hydrate_esi_entities_for_row(row)
        pilot_matches = []
        for ent in row.esi_entities:
            if ent.get("entity_type") != "character" or not ent.get("entity_id"):
                continue
            for candidate in unique([str(ent.get("name") or ""), str(ent.get("query") or "")]):
                span = clicked_span(candidate)
                if candidate and span:
                    pilot_matches.append((len(candidate), span[0], candidate, ent))
        if pilot_matches:
            # Prefer the longest clicked pilot span so a shorter cached entity
            # such as "Picard" cannot steal a click intended for "Picard X".
            pilot_matches.sort(key=lambda x: (-x[0], x[1]))
            _length, _pos, candidate, ent = pilot_matches[0]
            record_event("pilot_click_resolved", clicked=text, selected=candidate, pilot_id=ent.get("entity_id"), row_sender=getattr(row, "sender", ""))
            return {"kind": "pilot", "text": candidate, "entity": ent}

        for sysname in row.systems:
            if clicked_inside(str(sysname)):
                return {"kind": "system", "text": str(sysname)}
        for asset in row.assets:
            if clicked_inside(str(asset)):
                return {"kind": "asset", "text": str(asset)}
        return {"kind": "row", "text": text}

    def show_feed_context_menu(self, event):
        self.note_action("show_feed_context_menu")
        row_tag, info = self.row_at_event(event)
        url = self.link_at_event(event)
        selected = self.selected_feed_text()
        row = info["row"] if info else None
        ctx = self.clicked_context(event, row)
        record_event("context_menu", kind=ctx.get("kind"), text=ctx.get("text"), has_row=bool(row), has_url=bool(url), sender=getattr(row, "sender", ""), channel=getattr(row, "channel", ""))
        menu = self.tk.Menu(self.root, tearoff=False, bg="#111821", fg="#d7dde5")
        if url:
            menu.add_command(label="Open URL", command=lambda u=url: self.open_url(u))
            menu.add_command(label="Copy URL", command=lambda u=url: self.copy_to_clipboard(u))
            menu.add_separator()
        if row and ctx.get("kind") == "pilot" and ctx.get("entity"):
            ent = ctx.get("entity")
            menu.add_command(label="Open Pilot Info", command=lambda e=ent: self.open_pilot_info(e))
            menu.add_command(label="Mark Watchlist", command=lambda e=ent: self.quick_set_pilot_flag(e, "Watchlist", "★"))
            menu.add_command(label="Mark High Threat", command=lambda e=ent: self.quick_set_pilot_flag(e, "High Threat", "⚠"))
            menu.add_command(label="Mark Do Not Track", command=lambda e=ent: self.quick_set_pilot_flag(e, "Do Not Track", "DNT"))
            menu.add_command(label="Copy Pilot Name", command=lambda e=ent: self.copy_to_clipboard(str(e.get("name") or e.get("query") or "")))
            menu.add_separator()
        elif row and ctx.get("kind") == "system" and ctx.get("text"):
            menu.add_command(label="Copy System", command=lambda t=ctx.get("text"): self.copy_to_clipboard(t))
            menu.add_separator()
        elif row and ctx.get("kind") == "asset" and ctx.get("text"):
            menu.add_command(label="Copy Ship / Item", command=lambda t=ctx.get("text"): self.copy_to_clipboard(t))
            menu.add_separator()
        if info:
            menu.add_command(label="Copy Visible Line", command=lambda i=info: self.copy_to_clipboard(i["visible_line"]))
            menu.add_command(label="Copy Original Line", command=lambda i=info: self.copy_to_clipboard(i["original_line"]))
            menu.add_command(label="Copy Translated Line", command=lambda i=info: self.copy_to_clipboard(i["translated_line"]))
            if row and row.systems:
                menu.add_command(label="Copy Systems", command=lambda r=row: self.copy_to_clipboard(", ".join(r.systems)))
            if row and row.assets:
                menu.add_command(label="Copy Ships / Assets", command=lambda r=row: self.copy_to_clipboard(", ".join(r.assets)))
            links = self.http_links_for_row(row) if row else []
            if links:
                menu.add_command(label="Copy URLs", command=lambda r=row: self.copy_to_clipboard("\n".join(self.http_links_for_row(r))))
        else:
            menu.add_command(label="Copy Selected Text", command=self.copy_selected_text)
            menu.add_command(label="Copy Visible Feed", command=self.copy_visible_feed)
        if selected:
            menu.add_separator()
            menu.add_command(label="Resolve Selected Text with ESI", command=self.resolve_selected_esi_text)
            menu.add_command(label="Add Selected Text as ESI Character", command=self.add_selected_esi_character)
            menu.add_command(label="Add Selected Text to Exclusion List", command=self.ignore_selected_esi_text)
        if row:
            menu.add_separator()
            menu.add_command(label="Show ESI Candidates", command=lambda r=row: self.show_esi_candidates_for_row(r))
            menu.add_command(label="Show Translation Trace", command=lambda r=row: self.show_translation_trace_for_row(r))
            menu.add_command(label="Show Entity Recognition Trace", command=lambda r=row: self.show_entity_trace_for_row(r))
            menu.add_command(label="Show Click Context Trace", command=lambda c=ctx, r=row, u=url: self.show_click_context_trace(c, r, u))
        menu.add_separator()
        menu.add_command(label="Diagnostics / Tools...", command=self.show_esi_diagnostics)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_selected_text(self):
        try:
            self.copy_to_clipboard(self.text.get("sel.first", "sel.last"))
        except Exception:
            self.set_status("No text selected")

    def copy_visible_feed(self):
        self.copy_to_clipboard(self.text.get("1.0", "end-1c"))

    def http_links_for_row(self, row: Row) -> list[str]:
        terms = []
        for value in list(row.links) + HTTP_LINK_RE.findall(row.text):
            if value and value.lower().startswith(("http://", "https://")):
                terms.append(value.rstrip('.,;:)]}'))
        return unique(terms)

    def open_url(self, url: str):
        if not url.lower().startswith(("http://", "https://")):
            self.set_status("Blocked non-web URL")
            return
        try:
            webbrowser.open(url)
            self.set_status("Opened URL")
        except Exception as exc:
            write_log("Failed to open URL", exc)
            self.set_status("Failed to open URL")

    def tag_urls(self, start: str, end: str, source_text: str):
        if not bool(getattr(self, "enable_hyperlinks", None).get() if getattr(self, "enable_hyperlinks", None) is not None else SETTINGS.get("enable_hyperlinks", True)):
            return
        for url in unique(HTTP_LINK_RE.findall(source_text)):
            clean_url = url.rstrip('.,;:)]}')
            if not clean_url.lower().startswith(("http://", "https://")):
                continue
            pos = start
            while True:
                pos = self.text.search(clean_url, pos, end, nocase=True)
                if not pos:
                    break
                last = f"{pos}+{len(clean_url)}c"
                tag = f"link_{len(self.link_map)}"
                self.link_map[tag] = clean_url
                self.text.tag_add("link", pos, last)
                self.text.tag_add(tag, pos, last)
                self.text.tag_bind(tag, "<Button-1>", lambda e, u=clean_url: self.open_url(u))
                self.text.tag_bind(tag, "<Enter>", lambda e, u=clean_url: self.status_label.configure(text=u[:180]))
                self.text.tag_bind(tag, "<Leave>", lambda e: self.status_label.configure(text="Ready"))
                pos = last

    def add_entity_separators(self, text: str, systems: list[str], assets: list[str], pilots: list[str] | None = None) -> str:
        """Display-only readability: separate adjacent distinct entity tokens.

        Pilot terms are reduced to longest non-overlapping spans first so a full
        ESI character such as ``Matek Bathana`` is never split by partial cached
        matches like ``Matek`` and ``Bathana``.
        """
        out = str(text or "")
        pilot_terms = longest_non_overlapping_terms(out, list(pilots or []))
        terms = []
        for term in list(systems or []) + list(assets or []) + pilot_terms:
            t = str(term or "").strip()
            if t and not is_highlight_excluded(t):
                terms.append(re.escape(t))
        if not terms:
            return out
        alt = "|".join(sorted(set(terms), key=len, reverse=True))
        # Put a subtle middle-dot separator only between adjacent recognized entities.
        pat = re.compile(rf"(?i)\b({alt})\b\s+(?=({alt})\b)")
        for _ in range(3):
            newer = pat.sub(lambda m: m.group(1) + "  ·  ", out)
            if newer == out:
                break
            out = newer
        return out

    def insert_tagged_text(self, text: str, systems: list[str], assets: list[str], pilots: list[str] | None = None):
        # Re-scan the visible line for catalog ships so English names after Auto→EN
        # still highlight even when assets were extracted from CJK/original only.
        merged_assets = unique(list(assets or []) + discover_ships_in_text(text))
        text = self.add_entity_separators(text, systems, merged_assets, pilots)
        start_index = self.text.index("end-1c")
        self.text.insert("end", text)
        # Tag exact spans inside the inserted region.
        region_start = start_index
        region_end = self.text.index("end-1c")
        for hostile_term in sorted(HOSTILE_DISPLAY_TERMS, key=len, reverse=True):
            self.tag_term(hostile_term, "esi", region_start, region_end)
        from sb_highlight import term_is_ship
        system_terms = set(str(x).casefold() for x in unique(systems))
        ship_terms = set()
        try:
            ship_terms = set(CATALOG.ship_names.values()) | set(CATALOG.ship_names.keys())
        except Exception:
            ship_terms = set()
        highlight_modules = bool(self.appearance.get("highlight_modules", False)) if isinstance(self.appearance, dict) else False
        for term in sorted(unique(merged_assets), key=len, reverse=True):
            if is_parser_noise(term) or is_highlight_excluded(term):
                continue
            # System aliases/canonicals must stay yellow.  If extraction produced
            # a duplicate module/asset hit for the same visible text, skip it so
            # module purple cannot override the system tag.
            if str(term or "").casefold() in system_terms or CATALOG.lookup_system(str(term or "")):
                continue
            is_ship = bool(CATALOG.is_ship(term)) or term_is_ship(term, ship_terms)
            if term.lower() == "ess":
                self.tag_term_whole_word(term, "ess", region_start, region_end)
            elif is_ship:
                # Ships always use ship/asset color — never purple module on first paint.
                self.tag_term(term, "asset", region_start, region_end)
            elif highlight_modules:
                self.tag_term(term, "module", region_start, region_end)
            # else: purple module highlighting disabled by default
        # Apply systems after assets/modules so system yellow wins any overlap.
        for term in sorted(unique(systems), key=len, reverse=True):
            if is_highlight_excluded(term):
                continue
            self.tag_term(term, "system", region_start, region_end)
        # Defensive: highlight standalone literal ESS unless excluded by the user.
        if not is_highlight_excluded("ESS"):
            self.tag_term_whole_word("ESS", "ess", region_start, region_end)

    def tag_term_whole_word(self, term: str, tag: str, start: str, end: str):
        if not term:
            return
        # Tk's regexp engine does not support Python lookbehind/lookahead used by
        # word_boundary(). Search literal text and verify boundaries in Python so
        # ESS highlighting cannot crash the feed renderer.
        pos = start
        needle_len = len(term)
        while True:
            pos = self.text.search(term, pos, end, nocase=True)
            if not pos:
                break
            last = f"{pos}+{needle_len}c"
            try:
                before = self.text.get(f"{pos}-1c", pos) if self.text.compare(pos, ">", "1.0") else ""
                after = self.text.get(last, f"{last}+1c") if self.text.compare(last, "<", end) else ""
                before_word = bool(before) and (before.isalnum() or before == "_")
                after_word = bool(after) and (after.isalnum() or after == "_")
                if not before_word and not after_word:
                    self.text.tag_add(tag, pos, last)
            except Exception as exc:
                write_log(f"Tag whole-word failed for {term!r}: {type(exc).__name__}")
            pos = last

    def tag_term(self, term: str, tag: str, start: str, end: str):
        if not term:
            return
        pos = start
        while True:
            pos = self.text.search(term, pos, end, nocase=True)
            if not pos:
                break
            last = f"{pos}+{len(term)}c"
            self.text.tag_add(tag, pos, last)
            pos = last

    def localized_display_text(self, row: Row) -> str:
        try:
            cache_key = (ALIAS_RULE_VERSION, row.text, tuple((str(e.get("original", "")), str(e.get("canonical", ""))) for e in (row.localized or [])))
            if getattr(row, "_display_alias_cache_key", None) == cache_key:
                return getattr(row, "_display_alias_cache", "")
            started = time.time()
            display = normalize_feed_text(localized_display_from_aliases(row.text, row.localized))
            setattr(row, "_display_alias_cache_key", cache_key)
            setattr(row, "_display_alias_cache", display)
            alias_ms = int((time.time() - started) * 1000)
            if alias_ms > 50:
                record_event("slow_alias_display", duration_ms=alias_ms, alias_rules=len(ALIAS_REPLACEMENT_RULES), text_len=len(row.text or ""))
            return display
        except Exception as exc:
            write_log("Alias display cache failed", exc)
            return normalize_feed_text(row.text)

    def redraw_feed(self):
        """Cancellable, chunked feed redraw.

        Redraw requests used to rebuild every visible row synchronously, which could
        freeze Tk for several seconds.  This version clears the feed immediately,
        snapshots visible rows, and renders them in small batches via after().
        A newer redraw request cancels any older in-flight batch sequence.
        """
        started = time.time()
        was_at_bottom = self.feed_at_bottom()
        try:
            old_first_fraction = float(self.text.yview()[0])
        except Exception:
            old_first_fraction = 1.0
        gen = int(getattr(self, "_redraw_generation", 0) or 0) + 1
        self._redraw_generation = gen
        try:
            if getattr(self, "_redraw_chunk_after", None):
                self.root.after_cancel(self._redraw_chunk_after)
        except Exception:
            pass
        self._redraw_chunk_after = None
        try:
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.configure(state="disabled")
            self.rendered_row_map.clear()
            self.link_map.clear()
            self.row_count = 0
            old_rows = list(self.rows[-MAX_ROWS:])
            visible_rows = [row for row in old_rows if self.row_visible(row)]
            total = len(visible_rows)
            self.diagnostics["redraw_in_progress"] = True
            self.diagnostics["last_visible_rows"] = total
            self.diagnostics["redraw_batch_size"] = REDRAW_BATCH_SIZE
            self.diagnostics["redraw_generation"] = gen
            self.diagnostics["last_redraw_rows"] = 0

            def finish(rendered: int):
                if gen != getattr(self, "_redraw_generation", None):
                    return
                duration_ms = int((time.time() - started) * 1000)
                self.diagnostics["redraw_in_progress"] = False
                self.diagnostics["last_redraw_duration_ms"] = duration_ms
                self.diagnostics["last_redraw_rows"] = rendered
                self.diagnostics["last_visible_rows"] = total
                self.diagnostics["redraw_count"] = int(self.diagnostics.get("redraw_count") or 0) + 1
                self.diagnostics["last_redraw_cancelled"] = False
                if duration_ms > 500:
                    record_event("slow_redraw", duration_ms=duration_ms, rendered=rendered, visible=total, rows=len(self.rows), channel=self.visible_channel, chunked=True, batch_size=REDRAW_BATCH_SIZE)

            def render_atomic() -> None:
                """Render normal-sized redraws in one UI turn to avoid half-redraw flashes.

                The chunked redraw intentionally keeps Tk responsive for very large feeds,
                but for typical live-feed sizes the intermediate state is more annoying
                than useful: the widget is cleared, old snapshot rows appear, and only at
                the end does scroll restoration return the user to the expected view.
                Rendering a bounded number of rows atomically keeps the visible feed from
                briefly reverting when new chat/translation events trigger a redraw.
                """
                batch_started = time.time()
                for row in visible_rows:
                    self._render_row(row, auto_scroll=False)
                batch_ms = int((time.time() - batch_started) * 1000)
                self.diagnostics["last_redraw_batch_ms"] = batch_ms
                self.diagnostics["last_redraw_rows"] = total
                self.diagnostics["last_redraw_mode"] = "atomic"
                self._redraw_chunk_after = None
                self.restore_feed_scroll(was_at_bottom, old_first_fraction)
                if batch_ms > 250:
                    record_event("slow_redraw_atomic", duration_ms=batch_ms, rendered=total, visible=total, channel=self.visible_channel)
                finish(total)

            def render_batch(index: int, rendered: int):
                if gen != getattr(self, "_redraw_generation", None):
                    self.diagnostics["last_redraw_cancelled"] = True
                    return
                batch_started = time.time()
                end_index = min(index + REDRAW_BATCH_SIZE, total)
                for row in visible_rows[index:end_index]:
                    self._render_row(row, auto_scroll=False)
                rendered = end_index
                batch_ms = int((time.time() - batch_started) * 1000)
                self.diagnostics["last_redraw_batch_ms"] = batch_ms
                self.diagnostics["last_redraw_rows"] = rendered
                self.diagnostics["last_redraw_mode"] = "chunked"
                if was_at_bottom:
                    try:
                        self.text.see("end")
                    except Exception:
                        pass
                if batch_ms > 250:
                    record_event("slow_redraw_batch", duration_ms=batch_ms, rendered=rendered, visible=total, batch_start=index, batch_end=end_index, channel=self.visible_channel)
                if end_index < total:
                    self._redraw_chunk_after = self.root.after(1, lambda: render_batch(end_index, rendered))
                else:
                    self._redraw_chunk_after = None
                    self.restore_feed_scroll(was_at_bottom, old_first_fraction)
                    finish(rendered)

            if not visible_rows:
                self.restore_feed_scroll(was_at_bottom, old_first_fraction)
                finish(0)
            elif total <= REDRAW_ATOMIC_ROW_LIMIT:
                render_atomic()
            else:
                render_batch(0, 0)
        except Exception as exc:
            self.diagnostics["redraw_in_progress"] = False
            record_error("redraw_feed", exc)
            raise

    def row_visible(self, row: Row) -> bool:
        if self.visible_channel == ALL_CHANNELS_TAB:
            return row.channel in self.active_channels and row.channel not in self.hidden_tab_ids
        return row.channel == self.visible_channel

    def ensure_row_channel_tab(self, channel: str):
        if not channel:
            return
        if channel not in self.active_channels:
            self.active_channels.add(channel)
        if channel not in self.tab_order:
            self.tab_order.append(channel)
        if channel not in self.hidden_tab_ids:
            self.update_channel_tabs()
        if not self.visible_channel and self.visible_tabs():
            self.visible_channel = self.visible_tabs()[0]

    def mark_unread_for_row(self, row: Row):
        if row.channel in self.hidden_tab_ids:
            return
        if self.visible_channel == ALL_CHANNELS_TAB and ALL_CHANNELS_TAB not in self.hidden_tab_ids:
            return
        state = self._tab_state()
        state = sb_tabs.mark_unread(state, row.channel, delta=1)
        if ALL_CHANNELS_TAB not in self.hidden_tab_ids and self.visible_channel != ALL_CHANNELS_TAB:
            state = sb_tabs.mark_unread(state, ALL_CHANNELS_TAB, delta=1)
        self._apply_tab_state(state)
        self.update_channel_tabs()

    def add_discovered_channel(self, channel: str):
        if not channel or channel in self.active_channels:
            return
        self.active_channels.add(channel)
        if channel not in self.tab_order:
            self.tab_order.append(channel)
        # Do not steal focus and do not auto-restore channels the user explicitly hid.
        if channel not in self.hidden_tab_ids:
            self.unread_counts[channel] = self.unread_counts.get(channel, 0) + 1
        self.normalize_tab_state(prefer_all=True)
        self.update_channel_tabs()
        self.persist_settings()
        self.status_label.configure(text=f"New channel opened: {channel}")

    def _feed_filters(self) -> list[FeedFilter]:
        return normalize_filters(SETTINGS.get("feed_filters") or [])

    def _spam_limiter(self) -> SpamLimiter:
        limiter = getattr(self, "_spam_limiter_instance", None)
        policy = SpamPolicy(
            enabled=bool(SETTINGS.get("spam_control_enabled", True)),
            local_channels_only=bool(SETTINGS.get("spam_local_channels_only", True)),
            per_channel_max_per_minute=int(SETTINGS.get("spam_per_channel_max_per_minute", 30) or 30),
            repeat_sender_window_seconds=int(SETTINGS.get("spam_repeat_sender_window_seconds", 8) or 8),
            repeat_sender_max=int(SETTINGS.get("spam_repeat_sender_max", 3) or 3),
            ascii_art_min_lines=6 if bool(SETTINGS.get("spam_ascii_art_filter", True)) else 9999,
            ascii_art_symbol_ratio=0.45,
        )
        if limiter is None:
            self._spam_limiter_instance = SpamLimiter(policy)
        else:
            limiter.update_policy(policy)
        return self._spam_limiter_instance

    def append_row(self, row: Row):
        admit = should_admit_row(
            row.sender,
            row.text,
            row.channel,
            self._feed_filters(),
            self._spam_limiter(),
            systems=list(row.systems or []),
        )
        if not admit.admit:
            self.diagnostics["filtered_count"] = int(self.diagnostics.get("filtered_count") or 0) + 1
            if str(admit.reason).startswith("spam_"):
                self.diagnostics["spam_suppressed_count"] = int(self.diagnostics.get("spam_suppressed_count") or 0) + 1
            record_event("row_filtered", reason=admit.reason, channel=row.channel, text_len=len(row.text or ""))
            return
        self.rows.append(row)
        if self.esi_is_enabled():
            self.ensure_esi_resolver()
            self.hydrate_esi_entities_for_row(row)
            if self.esi_resolver:
                for candidate in esi_candidates_for_row(row):
                    self.esi_resolver.submit(candidate)
        self.emit_intel_history_row(row)
        self.ensure_row_channel_tab(row.channel)
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[-MAX_ROWS:]
        if self.row_visible(row):
            was_at_bottom = self.feed_at_bottom()
            self._render_row(row, auto_scroll=was_at_bottom)
        else:
            self.mark_unread_for_row(row)

    def hydrate_esi_entities_for_row(self, row: Row) -> bool:
        """Attach cached/resolved ESI character entities that appear in this row.

        ESI can resolve asynchronously or from cache before/after the row is drawn.
        This method makes rendering cache-backed, so the screen reflects resolved
        characters even when the resolver event did not exactly match a candidate
        string or the row was rendered before the cache hit arrived.
        """
        changed = False
        existing = {normalize_esi_query(e.get("query") or e.get("name") or "") for e in row.esi_entities}
        text_blob = f"{row.sender} {row.text}"
        for cand in esi_candidates_for_row(row):
            cached = self.esi_entities.get(normalize_esi_query(cand)) or ESI_CACHE.get_entity(cand)
            if cached and not cached.get("ignored") and not is_esi_ignored(cand) and cached.get("entity_type") == "character":
                key = normalize_esi_query(cached.get("query") or cached.get("name") or cand)
                if key and key not in existing:
                    row.esi_entities.append(cached); existing.add(key); changed = True
        # Also scan known cached characters by exact displayed name/query. This fixes rows
        # whose message candidate was too broad, e.g. "threeleggedweasel Abraxas Shaw",
        # while individual names are already in the cache.
        for ent in ESI_CACHE.list_entities("character", limit=1000):
            if ent.get("ignored"):
                continue
            names = unique([str(ent.get("name") or ""), str(ent.get("query") or "")])
            if any(is_esi_ignored(n) for n in names if n):
                continue
            if not any(n and re.search(word_boundary(n), text_blob, re.I) for n in names):
                continue
            key = normalize_esi_query(ent.get("query") or ent.get("name") or "")
            if key and key not in existing:
                row.esi_entities.append(ent); existing.add(key); changed = True
        return changed

    def character_names_for_row(self, row: Row) -> list[str]:
        names: list[str] = []
        text_blob = f"{row.sender} {row.text}"
        sender = re.sub(r"\s+", " ", row.sender.strip())
        if sender and sender.lower() != "eve system":
            names.append(sender)
        for cand in getattr(row, "esi_candidates", []) or []:
            cached = self.esi_entities.get(normalize_esi_query(cand)) or ESI_CACHE.get_entity(cand)
            if cached and not cached.get("ignored") and not is_esi_ignored(cand) and cached.get("entity_type") == "character":
                names.append(str(cached.get("name") or cand))
                names.append(cand)
        for ent in row.esi_entities:
            if ent.get("entity_type") == "character":
                ent_name = str(ent.get("name") or ent.get("query") or "")
                ent_query = str(ent.get("query") or "")
                if is_esi_ignored(ent_name) or is_esi_ignored(ent_query):
                    continue
                names.append(ent_name)
                names.append(ent_query)
        return longest_non_overlapping_terms(text_blob, names)

    def row_translation_cache(self, row: Row) -> dict:
        cache = getattr(row, "_free_translation_by_direction", None)
        if not isinstance(cache, dict):
            cache = {}
            try:
                if row.free_translation:
                    cache["zh-en"] = row.free_translation
            except Exception:
                pass
            try:
                row._free_translation_by_direction = cache
            except Exception:
                pass
        return cache

    def schedule_translation_for_row(self, row: Row, display_text: str) -> None:
        if not bool(self.translate_chinese_text.get()):
            return
        direction_var = getattr(self, "translation_direction", None)
        direction = str(direction_var.get() if direction_var is not None else "zh-en") or "zh-en"
        source_text = display_text if direction == "en-zh" else (display_text or row.text)
        if not hasattr(self, "translation_queue") or not hasattr(self, "translation_pending"):
            try:
                row._last_translation_decision = f"skipped: no background translation queue available for {direction}"
            except Exception:
                pass
            return
        if not source_text.strip():
            return
        if not looks_like_translation_pending_source(source_text, direction):
            try:
                row._last_translation_decision = f"skipped: no translatable signal for {direction}"
            except Exception:
                pass
            return
        cache = self.row_translation_cache(row)
        if cache.get(direction):
            return
        pref_var = getattr(self, "translation_preferred_engine", None)
        fallback_var = getattr(self, "translation_fallback_mode", None)
        mode_var = getattr(self, "translation_cache_mode", None)
        pref = pref_var.get() if pref_var is not None else "auto"
        fallback = fallback_var.get() if fallback_var is not None else "online-only"
        mode = mode_var.get() if mode_var is not None else "cache-first-auto"
        if mode == "cache-only":
            fallback = "cache-only"
        cache_source_text = translation_source_for_cache(source_text, direction)
        cached, source_label = translation_cache_lookup(cache_source_text, direction, pref, fallback)
        if cached:
            cache[direction] = normalize_feed_text(cached)
            if direction == "zh-en": row.free_translation = cache[direction]
            row.translation_source = source_label
            self.diagnostics["translation_cache_hits"] = int(self.diagnostics.get("translation_cache_hits") or 0) + 1
            try: row._last_translation_decision = f"used: {source_label}"
            except Exception: pass
            return
        self.diagnostics["translation_cache_misses"] = int(self.diagnostics.get("translation_cache_misses") or 0) + 1
        if fallback == "cache-only":
            self.diagnostics["translation_background_skipped_offline"] = int(self.diagnostics.get("translation_background_skipped_offline") or 0) + 1
            try: row._last_translation_decision = "skipped: cache-only translation miss"
            except Exception: pass
            return
        key = (id(row), direction, cache_source_text)
        if key in self.translation_pending:
            return
        if len(self.translation_pending) >= 24:
            try:
                row._last_translation_decision = "skipped: background translation queue is busy"
            except Exception:
                pass
            return
        self.translation_pending.add(key)
        try:
            self.translation_queue.put_nowait((key, row, cache_source_text, list(row.systems), list(row.assets), list(row.localized), list(row.counts), list(row.links), list(row.esi_candidates), direction, pref, fallback))
            self.diagnostics["translation_pending"] = len(self.translation_pending)
            try:
                row._last_translation_decision = f"queued: background {direction} translation segment"
            except Exception:
                pass
            record_event("translation_queued", direction=direction, sender=row.sender, channel=row.channel)
        except queue.Full:
            self.translation_pending.discard(key)
            try:
                row._last_translation_decision = "skipped: background translation queue full"
            except Exception:
                pass

    def translation_worker(self):
        while not getattr(self, "translation_stop_event", threading.Event()).is_set():
            try:
                item = self.translation_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            key, row, text, systems, assets, localized, counts, links, names, direction, pref, fallback = item
            started = time.time()
            result = ""
            error = ""
            source_label = ""
            try:
                cooldown_var = getattr(self, "translation_failure_cooldown_minutes", None)
                cooldown = int(cooldown_var.get() if cooldown_var is not None else 60)
                result, source_label = translate_free_text_cached(text, systems, assets, localized, counts, links, direction, names, pref, fallback, cooldown)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                write_log("Background translation failed", exc)
            duration_ms = int((time.time() - started) * 1000)
            self.queue.put(("translation_result", key, row, direction, result or "", error, duration_ms, source_label))

    def handle_translation_result(self, key, row: Row, direction: str, result: str, error: str, duration_ms: int, source_label: str = ""):
        from sb_contracts.translation_decision import make_translation_decision
        self.translation_pending.discard(key)
        self.diagnostics["translation_pending"] = len(self.translation_pending)
        self.diagnostics["last_translation_ms"] = duration_ms
        if error:
            self.diagnostics["last_translation_error"] = error[:240]
            record_event("translation_failed", direction=direction, duration_ms=duration_ms, error=error[:240])
            try:
                row._last_translation_decision = f"failed: {error[:120]}"
                row.translation_decision = make_translation_decision(
                    decision="error", reason="background_failed", engine="google",
                    duration_ms=duration_ms, error=error[:240],
                )
            except Exception:
                pass
            return
        if not result:
            record_event("translation_empty", direction=direction, duration_ms=duration_ms)
            try:
                row._last_translation_decision = f"skipped: no {direction} translation result"
                row.translation_decision = make_translation_decision(
                    decision="skipped", reason="empty_result", engine="none", duration_ms=duration_ms,
                )
            except Exception:
                pass
            return
        cache = self.row_translation_cache(row)
        cache[direction] = normalize_feed_text(result)
        if direction == "zh-en":
            row.free_translation = cache[direction]
        row.translation_source = source_label or ("catalog/db+background-mt" if (row.translation or row.localized) else "background-mt")
        engine = "cache" if "cache" in str(source_label or "").lower() else ("google" if "google" in str(source_label or "").lower() else "background")
        try:
            row._last_translation_decision = f"used: {source_label or 'background'} {direction} translation ({duration_ms}ms)"
            row.translation_decision = make_translation_decision(
                decision="used",
                reason=str(source_label or "background-mt"),
                engine=engine,
                duration_ms=duration_ms,
                cache_hit=("cache" in engine),
            )
        except Exception:
            pass
        record_event("translation_completed", direction=direction, duration_ms=duration_ms, sender=row.sender, channel=row.channel)
        if row in self.rows:
            self.schedule_redraw(40)

    def display_free_translation(self, row: Row, display_text: str) -> str:
        # Rendering/redraw must never perform network, DB-heavy, or MT work.
        # Missing free-text translation is queued for a background worker instead.
        if not bool(self.translate_chinese_text.get()):
            try:
                row._last_translation_decision = "skipped: free-text translation display disabled"
            except Exception:
                pass
            return ""
        direction_var = getattr(self, "translation_direction", None)
        direction = str(direction_var.get() if direction_var is not None else "zh-en") or "zh-en"
        cache = self.row_translation_cache(row)
        if cache.get(direction):
            try:
                row._last_translation_decision = f"used: cached/background {direction} translation"
            except Exception:
                pass
            return cache[direction]
        before_decision = getattr(row, "_last_translation_decision", "")
        self.schedule_translation_for_row(row, display_text)
        try:
            after_decision = getattr(row, "_last_translation_decision", "")
            if not str(after_decision).startswith("skipped: no translatable signal"):
                if row.localized:
                    row._last_translation_decision = f"queued/skipped: no cached {direction} free translation; localized catalog replacements available"
                else:
                    row._last_translation_decision = f"queued/skipped: no cached {direction} free translation yet"
        except Exception:
            pass
        # In Translated Only mode, do not flash the original non-English row and
        # then swap it to English.  Show a stable pending state until the
        # background/cache result arrives.  This keeps the feed calmer and makes
        # the async state explicit without blocking rendering.
        try:
            if bool(self.translated_only.get()):
                cache_source_text = translation_source_for_cache(display_text or row.text, direction)
                source_text = display_text or row.text
                if looks_like_translation_pending_source(source_text, direction):
                    return "Translating..."
        except Exception:
            pass
        return ""

    def _render_row(self, row: Row, auto_scroll: bool = True):
        # Render must stay fast: ESI/cache hydration is done when rows arrive or resolver events update rows.
        # Display lines come from pure RenderRow (contracts); no network/MT/ESI work here.
        from sb_contracts.render_row import build_render_row
        self.text.configure(state="normal")
        row_tag = f"row_{self.render_seq}"
        self.render_seq += 1
        row_start = self.text.index("end-1c")
        parts = self.row_display_parts(row)
        rr = build_render_row(
            row,
            translated_only=bool(self.translated_only.get()),
            normalize=normalize_feed_text,
        )
        # Prefer alias-aware display body from row_display_parts for single-line chat;
        # multi-segment rows use contract visible_lines (kill splits, etc.).
        if self.row_uses_multiline_segments(row):
            display_lines = list(rr.visible_lines)
        else:
            display_lines = self.row_visible_body_lines(row, parts)
        # LAN mirror uses the same visible body text the desktop shows.
        try:
            lan_body = " ".join(display_lines).strip()
            if lan_body:
                self.publish_lan_row(row, lan_body, row_id=rr.row_id)
        except Exception:
            pass
        ts = row.received_at.split()[-1]
        if bool(self.show_timestamps.get()):
            self.text.insert("end", f"[{ts}] ", "time")
        show_channel = bool(self.show_channel_names.get()) or (self.visible_channel == ALL_CHANNELS_TAB and bool(self.show_channel_names_in_all.get()))
        if show_channel:
            self.text.insert("end", f"[{row.channel}] ", "muted")
        sender_prefix = f"{row.sender} > "
        self.text.insert("end", sender_prefix, "sender")
        body_start = self.text.index("end-1c")
        tag_assets = row.assets + [
            normalize_feed_text(x.get("original", ""))
            for x in row.localized
            if not CATALOG.lookup_system(str(x.get("canonical", "") or x.get("original", "")))
        ]
        multiline = self.row_uses_multiline_segments(row)
        for idx, line in enumerate(display_lines):
            if idx > 0:
                self.text.insert("end", " " * max(4, len(sender_prefix)), "muted")
            body = self.apply_pilot_flag_badges(row, line)
            self.insert_tagged_text(body + "\n", row.systems, tag_assets, self.character_names_for_row(row))
            self.tag_urls(body_start, self.text.index("end-1c"), body)
        if not bool(self.translated_only.get()) and not multiline:
            if parts["free_text"] and parts["free_text"] != parts["original_text"]:
                self.text.insert("end", "    translated: ", ("muted", "translation_subline"))
                t_start = self.text.index("end-1c")
                self.insert_tagged_text(parts["free_text"] + "\n", row.systems, row.assets, self.character_names_for_row(row))
                self.text.tag_add("translation_subline", t_start, self.text.index("end-1c"))
                self.tag_urls(t_start, self.text.index("end-1c"), parts["free_text"])
            elif parts["display_text"] != parts["original_text"]:
                self.text.insert("end", "    translated: ", ("muted", "translation_subline"))
                t_start = self.text.index("end-1c")
                self.insert_tagged_text(parts["display_text"] + "\n", row.systems, row.assets, self.character_names_for_row(row))
                self.text.tag_add("translation_subline", t_start, self.text.index("end-1c"))
                self.tag_urls(t_start, self.text.index("end-1c"), parts["display_text"])
        row_end = self.text.index("end-1c")
        for ent in row.esi_entities:
            name = str(ent.get("name") or ent.get("query") or "")
            if not name or is_parser_noise(name) or is_esi_ignored(name):
                continue
            # Never paint ships/systems as ESI characters.
            if CATALOG.is_ship(name) or CATALOG.lookup_system(name) or _catalog_or_plural_catalog_term(name):
                continue
            self.tag_term(name, "esi", body_start, row_end)
        for name in self.character_names_for_row(row):
            if not name or is_parser_noise(name) or is_esi_ignored(name):
                continue
            if CATALOG.is_ship(name) or CATALOG.lookup_system(name) or _catalog_or_plural_catalog_term(name):
                continue
            self.tag_term(name, "esi", body_start, row_end)
        self.text.tag_add(row_tag, row_start, row_end)
        self.rendered_row_map[row_tag] = {
            "row": row,
            **parts,
            "render_row_id": rr.row_id,
            "render": rr,
            "segments": rr.segments or [getattr(seg, "__dict__", {}) for seg in getattr(row, "segments", [])],
        }
        self.text.tag_bind(row_tag, "<Button-3>", self.show_feed_context_menu)
        if auto_scroll:
            self.restore_feed_scroll(True)
        self.text.configure(state="disabled")
        self.row_count += 1
        if self.row_count > MAX_ROWS:
            self.trim_feed()
    def trim_feed(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "80.0")
        self.text.configure(state="disabled")
        self.row_count = max(0, self.row_count - 40)

    def drain_queue(self):
        started = time.time()
        drained = 0
        try:
            while True:
                item = self.queue.get_nowait()
                drained += 1
                if isinstance(item, tuple) and item[0] == "status":
                    try:
                        self.diagnostics["last_status"] = str(item[1])[:240]
                    except Exception:
                        pass
                    self.status_label.configure(text=item[1][:180])
                elif isinstance(item, tuple) and item[0] == "catalog_available":
                    manifest = item[1]
                    if self.messagebox.askyesno("Translation Catalog", f"New EVE catalog available: {manifest.get('catalog_version','unknown')}\n\nDownload and install it now?"):
                        self.download_catalog_update(manifest)
                elif isinstance(item, tuple) and item[0] == "catalog_current":
                    self.status_label.configure(text=f"Catalog current: {item[1]}")
                elif isinstance(item, tuple) and item[0] == "catalog_updated":
                    self.status_label.configure(text=f"Catalog updated: {item[1]}")
                    self.redraw_feed()
                elif isinstance(item, tuple) and item[0] == "catalog_failed":
                    self.status_label.configure(text="Catalog update failed; see logs")
                    self.messagebox.showwarning("Translation Catalog", "Catalog update failed. See logs for details.")
                elif isinstance(item, tuple) and item[0] == "update_available":
                    self.status_label.configure(text=f"Update available: {item[1]}")
                    self.show_update_available(item[1], item[2])
                elif isinstance(item, tuple) and item[0] == "update_current":
                    self.status_label.configure(text=f"Signal Bridge is current ({item[1]})")
                    self.messagebox.showinfo("Signal Bridge Updates", f"Signal Bridge is up to date.\n\nCurrent version: v{APP_VERSION}\nLatest release: {item[1]}")
                elif isinstance(item, tuple) and item[0] == "update_failed":
                    self.status_label.configure(text="Update check failed; see logs")
                    self.messagebox.showwarning("Signal Bridge Updates", "Could not check for updates. This can happen if the GitHub repo is private or offline.\n\nSee logs for details.")
                elif isinstance(item, tuple) and item[0] == "translation_result":
                    self.handle_translation_result(item[1], item[2], item[3], item[4], item[5], item[6], item[7] if len(item) > 7 else "")
                elif isinstance(item, tuple) and item[0] == "zkill_sync_result":
                    handler = item[4] if len(item) > 4 else None
                    if callable(handler):
                        handler(item[1], item[2], item[3])
                elif isinstance(item, tuple) and item[0] == "argos_status":
                    status = str(item[1])
                    self.argos_status_text.set(status)
                    self.status_label.configure(text="Argos status refreshed")
                elif isinstance(item, tuple) and item[0] == "esi_resolved":
                    self.handle_esi_resolved(item[1], item[2])
                elif isinstance(item, tuple) and item[0] == "esi_direct_result":
                    add_to_feed = item[5] if len(item) > 5 else False
                    action_label = item[6] if len(item) > 6 else "Resolve"
                    self.handle_esi_direct_result(item[1], item[2], item[3], item[4], add_to_feed, action_label)
                elif isinstance(item, tuple) and item[0] == "esi_status_result":
                    ok, data = item[1], item[2]
                    if ok:
                        msg = "ESI is reachable.\n\nPlayers online: {}\nServer version: {}".format(data.get('players','?'), data.get('server_version','?'))
                        self.messagebox.showinfo("ESI Status", msg)
                    else:
                        msg = "ESI status check failed.\n\n{}\n\nSee logs for details.".format(data)
                        self.messagebox.showwarning("ESI Status", msg)
                elif isinstance(item, tuple) and item[0] == "esi_oauth_failed":
                    self.status_label.configure(text="ESI OAuth failed")
                    self.messagebox.showwarning("ESI OAuth", str(item[1])[:500])
                elif isinstance(item, tuple) and item[0] == "channel_discovered":
                    self.add_discovered_channel(str(item[1]))
                elif isinstance(item, Row):
                    try:
                        self.append_row(item)
                    except Exception as exc:
                        write_log(f"GUI render/append failed for sender={getattr(item, 'sender', '')!r}: {type(exc).__name__}", exc)
                        self.status_label.configure(text="Render error; see logs")
        except queue.Empty:
            pass
        except Exception as exc:
            write_log("GUI queue drain failed", exc)
            record_error("drain_queue", exc)
            self.status_label.configure(text="Queue error; see logs")
        finally:
            try:
                self.diagnostics["last_queue_drain_duration_ms"] = int((time.time() - started) * 1000)
                self.diagnostics["last_queue_items"] = drained
                self.diagnostics["last_queue_size"] = self.queue.qsize()
                if self.diagnostics["last_queue_drain_duration_ms"] > 500:
                    record_event("slow_queue_drain", duration_ms=self.diagnostics["last_queue_drain_duration_ms"], items=drained, queue_size=self.queue.qsize())
            except Exception:
                pass
            self.root.after(150, self.drain_queue)

    def handle_esi_resolved(self, query: str, data: dict):
        if is_esi_ignored(query) or is_esi_ignored(str(data.get("name") or "")):
            self.status_label.configure(text=f"Excluded: {data.get('name') or query}")
            return
        key = normalize_esi_query(query)
        self.esi_entities[key] = data
        changed = False
        for row in self.rows:
            candidates = [normalize_esi_query(x) for x in esi_candidates_for_row(row)]
            text_blob = f"{row.sender} {row.text}"
            names = unique([str(data.get("name") or ""), str(data.get("query") or query)])
            appears = any(n and re.search(word_boundary(n), text_blob, re.I) for n in names)
            if (key in candidates or appears) and not any(normalize_esi_query(e.get("query") or e.get("name") or "") == key for e in row.esi_entities):
                row.esi_entities.append(data)
                changed = True
        self.status_label.configure(text=f"ESI resolved: {data.get('name') or query}")
        if changed:
            self.redraw_feed()

    def handle_esi_direct_result(self, query: str, data: dict | None, error: BaseException | None, show_dialog: bool, add_to_feed: bool = False, action_label: str = "Resolve"):
        if data and not data.get("ignored"):
            ESI_CACHE.put_entity(query, data)
            self.handle_esi_resolved(query, data)
            canonical = str(data.get("name") or query)
            key = normalize_esi_query(canonical)
            if key:
                self.esi_entities[key] = data
            matched = 0
            for row in self.rows:
                if self.hydrate_esi_entities_for_row(row):
                    matched += 1
            self.redraw_feed()
            write_log(f"ESI {action_label.lower()} applied: {query!r} -> {canonical!r}; matched_rows={matched}")
            text = (
                f"ESI character {'added' if add_to_feed else 'found'}:\n\n"
                "Query: {}\n"
                "Name: {}\n"
                "Character ID: {}\n"
                "Corp: {}\n"
                "Alliance: {}\n"
                "Source: {}"
            ).format(
                query,
                data.get('name') or '',
                data.get('entity_id') or '',
                data.get('corporation_name') or '',
                data.get('alliance_name') or '',
                data.get('source', 'esi'),
            )
            self.status_label.configure(text=f"ESI {'added' if add_to_feed else 'found'}: {data.get('name') or query}")
            if show_dialog:
                self.messagebox.showinfo("ESI Result", text)
            return
        if data and data.get("ignored"):
            self.status_label.configure(text=f"ESI ignored: {query}")
            if show_dialog:
                self.messagebox.showinfo("ESI Result", f"{query} is excluded from recognition/highlighting.")
            return
        msg = f"ESI did not find a character for: {query}"
        if error:
            msg += f"\n\nResult: {type(error).__name__}"
        self.status_label.configure(text=msg[:180])
        if show_dialog:
            self.messagebox.showwarning("ESI Result", msg)

    def esi_details_for_row(self, row: Row) -> str:
        entities = list(row.esi_entities)
        for candidate in esi_candidates_for_row(row):
            cached = self.esi_entities.get(normalize_esi_query(candidate)) or ESI_CACHE.get_entity(candidate)
            if cached and not cached.get("ignored") and cached not in entities:
                entities.append(cached)
        if not entities:
            return "No ESI entities resolved for this row."
        lines = []
        for ent in entities:
            bits = [f"{ent.get('entity_type','entity')}: {ent.get('name') or ent.get('query')} ({ent.get('entity_id','')})"]
            if ent.get("corporation_name"):
                bits.append(f"corp={ent.get('corporation_name')}")
            if ent.get("alliance_name"):
                bits.append(f"alliance={ent.get('alliance_name')}")
            bits.append(f"source={ent.get('source','esi-cache')}")
            lines.append(" | ".join(bits))
        return "\n".join(lines)

    def run(self):
        if self.esi_is_enabled():
            self.ensure_esi_resolver()
        self.start_monitor()
        if bool(self.check_updates_on_start.get()):
            self.root.after(1500, lambda: self.check_for_updates(manual=False))
        self.root.mainloop()


def self_test(limit: int = 20):
    db = EveDb(DB_PATH)
    rows = []
    channels = default_channels() or set(discover_channels()[:1])
    files = []
    for channel in channels:
        files.extend(CHATLOG_DIR.glob(channel + "_*.txt"))
    for p in sorted(files, key=lambda x: x.stat().st_mtime_ns, reverse=True)[:3]:
        try:
            rows.extend(parse_rows_from_text(decode_bytes(p.read_bytes()), channel_from_filename(p), p.name, db)[-20:])
        except OSError:
            pass
    db.close()
    print(json.dumps({"chatlog_dir_exists": CHATLOG_DIR.exists(), "db_exists": DB_PATH.exists(), "rows_found": len(rows)}, indent=2, ensure_ascii=False))
    for row in rows[-limit:]:
        data = dict(row.__dict__)
        data["segments"] = [seg.__dict__ for seg in getattr(row, "segments", [])]
        print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    return 0 if CHATLOG_DIR.exists() and rows else 1


def main(argv=None):
    install_exception_logging()
    write_log("Process entry")
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test(args.limit)
    try:
        SignalBridgeGui().run()
        return 0
    except Exception as exc:
        write_log("Fatal GUI error", exc)
        raise

if __name__ == "__main__":
    raise SystemExit(main())
