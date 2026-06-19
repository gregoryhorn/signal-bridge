from __future__ import annotations
import argparse
import base64
import json
import copy
import hashlib
import queue
import re
import secrets
import sqlite3
import sys
import threading
import time
import traceback
import webbrowser
import http.server
import socketserver
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

APP_NAME = "Signal Bridge"
APP_VERSION = "0.3"
UPDATE_API_URL = "https://api.github.com/repos/gregoryhorn/signal-bridge/releases/latest"
UPDATE_RELEASE_URL = "https://github.com/gregoryhorn/signal-bridge/releases/latest"
DONATION_TEXT = "If you like this app and want further development, donate me some ISK in game | Mizz Betty"
ALL_CHANNELS_TAB = "__ALL_CHANNELS__"
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
USER_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_DIR = USER_DIR / "config"
CACHE_DIR = USER_DIR / "cache"
MODEL_DIR = USER_DIR / "models" / "argos"
LOG_DIR = USER_DIR / "logs"
LOG_PATH = LOG_DIR / "signal_bridge.log"
CONFIG_PATH = CONFIG_DIR / "settings.json"
DATA_DIR = USER_DIR / "data"
DEFAULT_DB_PATH = Path(r"D:\AI\Rift\signal-bridge-v2\signal-bridge-v3\src-tauri\bundle-resources\translations.db")
POLL_SECONDS = 1.0
MAX_CHUNK = 1024 * 1024
MAX_ROWS = 600
GOOGLE_TRANSLATE_TIMEOUT = 2.5
FREE_TRANSLATION_CACHE: dict[str, str] = {}
CATALOG_PATH = DATA_DIR / "eve_catalog.json"
CATALOG_MANIFEST_PATH = DATA_DIR / "catalog_manifest.json"
CATALOG_PREVIOUS_PATH = DATA_DIR / "eve_catalog.previous.json"
PHRASE_OVERRIDES_PATH = DATA_DIR / "phrase_overrides.json"
DEFAULT_EXCLUSIONS_PATH = DATA_DIR / "default_exclusions.json"
DEFAULT_ESI_ENTITIES_PATH = DATA_DIR / "default_esi_entities.json"
TRANSLATION_CACHE_PATH = CACHE_DIR / "translation_cache.sqlite"
ESI_CONFIG_PATH = CONFIG_DIR / "esi_settings.json"
ESI_TOKENS_PATH = CONFIG_DIR / "esi_tokens.json"
ESI_CACHE_PATH = CACHE_DIR / "esi_cache.sqlite"
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


def load_settings() -> dict:
    defaults = {
        "chatlog_dir": str(detect_chatlog_dir()),
        "db_path": str(DEFAULT_DB_PATH if DEFAULT_DB_PATH.exists() else DATA_DIR / "translations.db"),
        "active_channels": [],
        "always_on_top": True,
        "translated_only": True,
        "translate_free_text": True,
        "translation_direction": "zh-en",
        "compact_mode": True,
        "font_family": "Segoe UI",
        "font_size": 10,
        "show_timestamps": True,
        "show_channel_names": False,
        "show_channel_names_in_all": True,
        "active_tab_id": ALL_CHANNELS_TAB,
        "tab_order": [ALL_CHANNELS_TAB],
        "hidden_tab_ids": [],
        "auto_open_new_channels": True,
        "auto_switch_to_new_channel": False,
        "max_tab_rows": 3,
        "check_updates_on_start": True,
        "esi_entity_recognition": True,
        "esi_oauth_enabled": False,
        "replay_on_start": False,
    }
    try:
        if CONFIG_PATH.exists():
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                defaults.update(loaded)
    except Exception:
        pass
    return defaults


def save_settings(settings: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


SETTINGS = load_settings()
if SETTINGS.get("font_family") == "Consolas":
    SETTINGS["font_family"] = "Segoe UI"
    save_settings(SETTINGS)
CHATLOG_DIR = Path(SETTINGS.get("chatlog_dir") or detect_chatlog_dir())
DB_PATH = Path(SETTINGS.get("db_path") or DEFAULT_DB_PATH)
DEFAULT_CHANNELS: set[str] = set(SETTINGS.get("active_channels") or [])

def ensure_app_dirs() -> None:
    for path in (CONFIG_DIR, CACHE_DIR, MODEL_DIR, LOG_DIR, DATA_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass


ensure_app_dirs()


def write_log(message: str, exc: BaseException | None = None) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
            if exc is not None:
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                f.write("\n")
    except Exception:
        pass


def install_exception_logging() -> None:
    def _hook(exc_type, exc, tb):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Uncaught exception\n")
                traceback.print_exception(exc_type, exc, tb, file=f)
                f.write("\n")
        finally:
            sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _hook

LIVE_INLINE = re.compile(r"^\[\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s*\]\s*(.+?)\s*(?:>|:)\s*(.+)$", re.I)
HEADER_CHANNEL = re.compile(r"^Channel Name:\s*(.+)$", re.I)
SYSTEM_RE = re.compile(r"\b[A-Z0-9]{1,6}-[A-Z0-9]{1,4}\b")
LINK_RE = re.compile(r"https?://\S+|www\.\S+|dscan\.info/\S+", re.I)
HTTP_LINK_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.I)
COUNT_RE = re.compile(r"(?<![A-Za-z0-9-])(?:\+?\d+|\d+\+|x\d+|\d+x|\d+(?:\.\d+)?\s*(?:km|m|b|bil|mil|kk|isk))\b", re.I)
PAREN_RE = re.compile(r"\(([^)]+)\)")
HEADER_KEYS = ("Channel ID:", "Channel Name:", "Listener:", "Session started:")

BUILTIN_ASSETS = {
    "Hound", "Sabre", "Loki", "Flycatcher", "Caracal", "Keres", "Thorax", "Capsule", "Bombers", "Bomber", "No visual", "ESS", "Bubble",
    "Cyno", "Dictor", "Dread", "Tornado", "Purifier", "Stiletto", "Hecate", "Rook", "Heretic", "Svipul", "Naga", "Minmatar Shuttle",
    "Shuttle", "Stabber Fleet Issue", "Crucifier", "Bifrost", "Stabber", "Manticore", "Scalpel", "Cynabal", "Retribution", "Vedmak",
    "Vagabond", "Proteus", "Machariel", "Typhoon", "Kikimora", "Raptor", "Condor", "Garmur", "Cormorant", "Kirin", "Redeemer",
}

CLEAR = re.compile(r"\b(clear|clr|safe|blue only)\b", re.I)
MOVE = re.compile(r"\b(jump|jumped|jumping|gate|warp|undock|dock|moving|status|leaving|going|cyno|beacon)\b", re.I)
HOSTILE = re.compile(r"\b(hostile|neut|neutral|red|tackle|camp|gang|fleet|goons?|bombers?|hound squad|bubble|ess theft|intrusion)\b", re.I)

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


def is_header(line: str) -> bool:
    s = clean(line)
    return (not s) or (set(s) <= {"-"} and len(s) > 8) or any(s.startswith(k) for k in HEADER_KEYS)


def channel_from_filename(path: Path) -> str:
    return path.stem.split("_", 1)[0] or path.stem


def discover_channels(limit_files: int = 500) -> list[str]:
    if not CHATLOG_DIR.exists():
        return []
    channels: dict[str, int] = {}
    files = sorted(CHATLOG_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime_ns, reverse=True)[:limit_files]
    for path in files:
        try:
            channel = channel_from_filename(path)
            channels[channel] = max(channels.get(channel, 0), path.stat().st_mtime_ns)
        except OSError:
            continue
    return [name for name, _ in sorted(channels.items(), key=lambda kv: kv[1], reverse=True)]


def default_channels() -> set[str]:
    if DEFAULT_CHANNELS:
        return set(DEFAULT_CHANNELS)
    channels = discover_channels()
    # Default to most recently active channel only; user can add/remove from Channels menu.
    return set(channels[:1])


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
    for m in re.finditer(r"[^\s,;:()\[\]{}]+(?:级|型|çº§|åž‹)\*?", text):
        terms.append(m.group(0))
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text)
    for n in (4, 3, 2, 1):
        for i in range(0, max(0, len(words) - n + 1)):
            terms.append(" ".join(words[i:i+n]))
    return unique([t.strip().strip("* ,.;:()[]{}\"'`“”‘’") for t in terms])


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
        key = term.strip().strip("* ,.;:()[]{}\"'`“”‘’").casefold()
        if not key or len(key) < 2:
            return None
        return self.types.get(key) or self.aliases.get(key) or self.market_groups.get(key)

    def lookup_system(self, term: str) -> str | None:
        return self.systems.get(term.strip().casefold())

    def is_ship(self, term: str) -> bool:
        key = term.strip().strip("* ,.;:()[]{}\"'`“”‘’").casefold()
        canonical = self.lookup_type(term) or term
        return key in self.ship_names or canonical.casefold() in self.ship_names or self.alias_kinds.get(key) == "ship"


CATALOG = EveCatalog()

# User/community shorthand aliases that should override ambiguous machine translation.
# Keep this small and explicit; the compact catalog still provides normal SDE names.
MANUAL_TYPE_ALIASES = {
    "短剑": "Stabber",
    "海狞獾": "Caracal Navy Issue",
}
for _alias, _canonical in MANUAL_TYPE_ALIASES.items():
    CATALOG.aliases.setdefault(_alias.casefold(), _canonical)
    CATALOG.alias_kinds.setdefault(_alias.casefold(), "ship")
    if isinstance(CATALOG.ship_names, dict):
        CATALOG.ship_names.setdefault(_canonical.casefold(), _canonical)
    elif hasattr(CATALOG.ship_names, "add"):
        CATALOG.ship_names.add(_canonical.casefold())

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

    def stats(self):
        try:
            con = sqlite3.connect(self.path)
            row = con.execute("select count(*), coalesce(sum(hit_count),0) from translation_cache").fetchone()
            con.close(); return row or (0, 0)
        except Exception:
            return (0, 0)

    def clear(self) -> bool:
        try:
            con = sqlite3.connect(self.path); con.execute("delete from translation_cache"); con.commit(); con.close(); return True
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
    """Seed bundled general exclusions into the local cache without overwriting user edits."""
    try:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("exclusions") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return 0
        added = 0
        for item in items:
            if isinstance(item, str):
                text, note = item, "bundled default exclusion"
            elif isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                note = str(item.get("note") or "bundled default exclusion")
            else:
                continue
            if not text or ESI_CACHE.get_correction(text):
                continue
            if ESI_CACHE.set_correction(text, "ignore", note=note):
                added += 1
        if added:
            write_log(f"Seeded {added} bundled default exclusion(s)")
        return added
    except Exception as exc:
        write_log("Default exclusion seed failed", exc)
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
seed_default_esi_entities()



def is_globally_excluded(term: str) -> bool:
    """Return True when a user exclusion should suppress all recognition/highlights.

    The exclusion list started as an ESI character ignore list, but users expect
    anything in it to be neutral everywhere: no red ESI character, no orange ship,
    no purple asset/module, no ESS special color, and no system highlight.
    """
    key = normalize_esi_query(term)
    if not key:
        return False
    # Built-in noise words are also global visual exclusions.
    if "COMMON_ESI_NOISE" in globals() and key in COMMON_ESI_NOISE:
        return True
    try:
        corr = ESI_CACHE.get_correction(term)
        return bool(corr and corr.get("action") == "ignore")
    except Exception:
        return False


COMMON_ESI_NOISE = {
    "and", "the", "link", "jump", "jumped", "fleet", "gate", "star", "isk", "ship",
    "clear", "eyes", "no visual", "nv", "ess", "red", "enemy", "hostile", "neutral", "neut",
    "local", "system", "corp", "alliance",
}
NAME_CONTEXT_WORDS = {
    "tackle", "watch", "seen", "spotted", "reported", "report", "by", "from", "with", "kill", "killed",
    "local", "jumped", "jump", "gate", "camp", "hostile", "neut", "neutral", "red", "pilot", "scout",
}
NAME_CHUNK_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Za-z0-9'`-]{1,}(?:\s+[A-Z][A-Za-z0-9'`-]{1,}){0,3})(?![A-Za-z0-9])")


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


def is_probable_character_candidate(candidate: str, text: str = "", span: tuple[int, int] | None = None) -> bool:
    cand = re.sub(r"\s+", " ", candidate.strip().strip(" ,.;:()[]{}\"'`"))
    key = cand.casefold()
    if len(cand) < 3 or key in COMMON_ESI_NOISE:
        return False
    if _catalog_or_plural_catalog_term(cand):
        return False
    if SYSTEM_RE.fullmatch(cand) or LINK_RE.search(cand) or COUNT_RE.fullmatch(cand):
        return False
    parts = cand.split()
    if len(parts) > 4:
        return False
    if len(parts) == 1:
        token = parts[0]
        if len(token) < 5 or token.lower() in COMMON_ESI_NOISE:
            return False
        # Single-token EVE character names can be lowercase handles or even all-uppercase
        # exact names (for example MADRICO).  System/code/catalog checks above catch the
        # common non-name cases; the ESI negative cache absorbs remaining false positives.
        if token.isupper() and len(token) < 6:
            return False
        if text and span:
            before = text[max(0, span[0]-18):span[0]].lower().split()[-3:]
            after = text[span[1]:span[1]+18].lower().split()[:3]
            if not any(w in before or w in after for w in NAME_CONTEXT_WORDS):
                return False
    for part in parts:
        if part.casefold() in COMMON_ESI_NOISE or _catalog_or_plural_catalog_term(part):
            return False
    return True


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
    if key in COMMON_ESI_NOISE:
        return False
    if SYSTEM_RE.fullmatch(token) or COUNT_RE.fullmatch(token) or LINK_RE.search(token):
        return False
    if _catalog_or_plural_catalog_term(token):
        return False
    # Short all-caps fragments are usually tickers/codes, not enough for an exact ESI name by themselves.
    if token.isupper() and len(token) <= 4:
        return False
    return True


def _candidate_from_tokens(tokens: list[str], text: str = "") -> str | None:
    parts = [t.strip(" ,.;:()[]{}\"'`") for t in tokens if t.strip(" ,.;:()[]{}\"'`")]
    while parts and parts[0].casefold() in COMMON_ESI_NOISE:
        parts.pop(0)
    while parts and parts[-1].casefold() in COMMON_ESI_NOISE:
        parts.pop()
    if not parts or len(parts) > 4:
        return None
    cand = " ".join(parts)
    if not is_probable_character_candidate(cand, text):
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

    # Group contiguous plausible tokens separated only by whitespace. Emit the longest
    # conservative chunk first, but also allow a single lowercase/mixed token because
    # EVE pilot names often are lowercase handles.
    group: list[str] = []
    last_end: int | None = None
    def flush_group():
        nonlocal group
        if not group:
            return
        # Do not only emit the longest chunk. Intel often writes multiple adjacent
        # character names, or a name followed by a shorthand/ship/free word, e.g.
        # "Potderillettes MADRICO", "Prometeus22 CASPULE", "Shax HerooooMvP".
        # Submit bounded sub-windows so exact ESI names can resolve independently.
        max_size = min(4, len(group))
        for start in range(len(group)):
            for size in range(max_size, 0, -1):
                if start + size > len(group):
                    continue
                cand = _candidate_from_tokens(group[start:start+size], text)
                if cand:
                    out.append(cand)
        group = []

    for token, a, b in tokens:
        if last_end is not None and work[last_end:a].strip():
            flush_group()
        group.append(token)
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
    # Keep the queue bounded, but allow enough candidates for split adjacent names.
    return unique(out)[:8]


def esi_candidates_for_row(row: Row) -> list[str]:
    out: list[str] = []
    sender = re.sub(r"\s+", " ", row.sender.strip())
    if sender and sender.lower() != "eve system" and is_probable_character_candidate(sender):
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
        if not key or len(key) < 3 or key in COMMON_ESI_NOISE:
            return
        if is_globally_excluded(query) and not force:
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
    out = text; changed = False
    for item in PHRASE_OVERRIDES:
        src = str(item.get("source", "")); tgt = str(item.get("target", "")); idir = str(item.get("direction", "zh-en"))
        if src and tgt and idir in (direction, "auto", "any") and src in out:
            out = out.replace(src, tgt); changed = True
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
        term = term.strip().strip("* ,.;:()[]{}\"'`“”‘’")
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


def extract_intel(text: str, db: EveDb):
    systems = unique(SYSTEM_RE.findall(text) + [CATALOG.lookup_system(t) for t in candidate_terms(text) if CATALOG.lookup_system(t)])
    assets: list[str] = []
    localized: list[dict] = []
    for term in sorted(candidate_terms(text), key=lambda s: -len(s)):
        hit = db.lookup_type(term)
        if hit:
            assets.append(hit)
            if hit.lower() != term.lower():
                localized.append({"original": term, "canonical": hit})
    for term in sorted(BUILTIN_ASSETS, key=lambda s: -len(s)):
        if re.search(word_boundary(term), text, re.I):
            assets.append(term)
    if re.search(r"(?<!\w)nv(?!\w)", text, re.I):
        assets.append("No visual")
    intent = "clear" if CLEAR.search(text) else "movement" if MOVE.search(text) else "hostile" if HOSTILE.search(text) else "unknown"
    return systems, unique(assets), localized, unique(COUNT_RE.findall(text)), unique(LINK_RE.findall(text)), intent


def translate_text(text: str, localized: list[dict], intent: str) -> str:
    out = text
    changed = False
    for ent in sorted(localized, key=lambda e: -len(e["original"])):
        out = out.replace(ent["original"], ent["canonical"])
        changed = True
    return out if changed else ""


def has_cjk(text: str) -> bool:
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def has_english_letters(text: str) -> bool:
    return any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in text)


def has_non_english_signal(text: str) -> bool:
    if has_cjk(text):
        return True
    # Cyrillic covers Russian/Ukrainian/etc. This avoids fragile literal Cyrillic regex text.
    if any("\u0400" <= ch <= "\u04ff" for ch in text):
        return True
    # Common accented Latin letters used by Spanish/French/German/etc.
    if re.search(r"[????????????????????????????????]", text, re.I):
        return True
    # Conservative Latin-language hints. Avoid broad English-like words to prevent translating normal intel.
    lowered = " " + text.lower() + " "
    latin_hints = (
        " enemigo ", " enemigos ", " neutro ", " neutros ", " rojo ", " rojos ",
        " puerta ", " entrando ", " entrada ", " salta ", " saltando ",
        " avec ", " sans ", " rouge ", " porte ", " bonjour ",
    )
    return any(hint in lowered for hint in latin_hints)


def google_translate_free(text: str, source: str = "zh-CN", target: str = "en") -> str | None:
    text = text.strip()
    if not text:
        return None
    key = f"google|{source}|{target}|{text}"
    if key in FREE_TRANSLATION_CACHE:
        return FREE_TRANSLATION_CACHE[key]
    cached = TRANSLATION_CACHE.get(key)
    if cached:
        FREE_TRANSLATION_CACHE[key] = cached
        return cached
    params = urllib.parse.urlencode({"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text})
    url = "https://translate.googleapis.com/translate_a/single?" + params
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SignalBridge/1.0"})
        with urllib.request.urlopen(req, timeout=GOOGLE_TRANSLATE_TIMEOUT) as response:
            payload = response.read().decode("utf-8", "replace")
        data = json.loads(payload)
        translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
        if translated:
            FREE_TRANSLATION_CACHE[key] = translated
            TRANSLATION_CACHE.put(key, text, source, target, translated, "google")
            return translated
    except Exception:
        return None
    return None


def argos_translate_fallback(text: str, source: str = "zh", target: str = "en") -> str | None:
    try:
        import argostranslate.translate  # type: ignore
        translated = argostranslate.translate.translate(text, source, target).strip()
        return translated or None
    except Exception:
        return None


def translate_free_text(text: str, systems: list[str], assets: list[str], localized: list[dict], counts: list[str], links: list[str], direction: str = "zh-en", character_names: list[str] | None = None) -> str:
    direction = direction or "zh-en"
    if direction == "off":
        return ""
    if direction == "zh-en":
        if not has_non_english_signal(text):
            return ""
        # Google auto-detects Chinese, Russian, Spanish, etc. Argos fallback remains Chinese-only unless Google fails on CJK.
        source, target = "auto", "en"
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
    translated = google_translate_free(work, source=source, target=target) or argos_translate_fallback(work, source=argos_source, target=argos_target)
    if not translated:
        return ""
    out = translated
    for token, original in protected:
        out = re.sub(rf"\b{re.escape(token)}\b", original, out)
    return out.strip()


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
            tmp_row = Row(channel, ts, sender, body, systems, assets, localized, counts, links, intent, translation, "", "none", file_name)
            msg_candidates = esi_message_candidates_for_row(tmp_row)
            free_translation = translate_free_text(display_body, systems, assets, localized, counts, links, "zh-en", msg_candidates) if allow_free_translation else ""
            rows.append(Row(channel, ts, sender, body, systems, assets, localized, counts, links, intent, translation, free_translation, ("catalog/db+google" if free_translation else "catalog/db" if translation or localized else "none"), file_name, [], msg_candidates))
    return rows


class MonitorThread(threading.Thread):
    def __init__(self, outq: queue.Queue, stop_event: threading.Event, status: Callable[[str], None], channels: set[str], replay_today: bool = True):
        super().__init__(daemon=True)
        self.outq = outq
        self.stop_event = stop_event
        self.status = status
        self.channels = set(channels)
        self.replay_today = replay_today
        self.offsets: dict[str, int] = {}
        self.seen: set[tuple[str, str, str]] = set()
        # Live monitoring must never block gameplay/chat display on the large optional translations.db.
        # Use compact catalog-only lookups here; manual/self-test paths can still open SQLite explicitly.
        self.db = EveDb(DB_PATH, use_sqlite=False)

    def chat_files(self):
        files: list[Path] = []
        if self.channels:
            for channel in sorted(self.channels):
                files.extend(CHATLOG_DIR.glob(channel + "_*.txt"))
        # Also watch discovered chatlogs so newly active channels can open tabs
        # automatically without forcing the user through a destructive chooser.
        try:
            files.extend(CHATLOG_DIR.glob("*.txt"))
        except Exception:
            pass
        return sorted(set(files), key=lambda p: p.stat().st_mtime_ns)

    def emit_row(self, row: Row):
        if row.channel not in self.channels:
            self.channels.add(row.channel)
            self.outq.put(("channel_discovered", row.channel))
            write_log(f"Monitor discovered active channel={row.channel!r}")
        key = (row.channel.lower(), row.sender.lower(), row.text.lower())
        if key in self.seen:
            return
        self.seen.add(key)
        self.outq.put(row)
        write_log(f"Monitor emitted row channel={row.channel!r} sender={row.sender!r} text={row.text[:120]!r}")

    def run(self):
        try:
            if not CHATLOG_DIR.exists():
                self.status(f"Missing chatlog folder: {CHATLOG_DIR}")
                return
            if not CATALOG.loaded and not DB_PATH.exists():
                self.status("Warning: no compact catalog or DB available")
            if self.replay_today:
                recent = sorted(self.chat_files(), key=lambda x: x.stat().st_mtime_ns, reverse=True)[:max(3, len(self.channels) * 3)]
                replay_rows = []
                for p in recent:
                    try:
                        text = decode_bytes(p.read_bytes())
                    except OSError:
                        continue
                    replay_rows.extend(parse_rows_from_text(text, channel_from_filename(p), p.name, self.db, allow_free_translation=False)[-40:])
                for row in replay_rows[-80:]:
                    self.emit_row(row)
            for p in self.chat_files():
                try:
                    self.offsets[str(p)] = p.stat().st_size
                except OSError:
                    pass
            self.status(f"Monitoring live: {len(self.channels)} channel(s), existing files snapshotted; Catalog={'yes' if CATALOG.loaded else 'no'}")
            while not self.stop_event.is_set():
                for p in self.chat_files():
                    sp = str(p)
                    try:
                        size = p.stat().st_size
                    except OSError:
                        continue
                    old = self.offsets.get(sp, 0)
                    if size < old:
                        old = 0
                    if size == old:
                        self.offsets[sp] = size
                        continue
                    if size - old > MAX_CHUNK:
                        old = max(0, size - MAX_CHUNK)
                    try:
                        with p.open("rb") as f:
                            f.seek(old)
                            data = f.read(size - old)
                        self.offsets[sp] = size
                    except OSError:
                        continue
                    rows = parse_rows_from_text(decode_bytes(data), channel_from_filename(p), p.name, self.db, allow_free_translation=False)
                    if rows:
                        write_log(f"Monitor read {len(rows)} row(s) from {p.name} bytes={size-old}")
                    for row in rows:
                        self.emit_row(row)
                time.sleep(POLL_SECONDS)
        except Exception:
            self.status(traceback.format_exc())
        finally:
            self.db.close()


TAB_THEME = {
    "bar_bg": "#0b0f14",
    "bar_border": "#162231",
    "tab_bg": "#111821",
    "tab_fg": "#c9d2dc",
    "tab_active_bg": "#23405c",
    "tab_active_fg": "#ffffff",
    "tab_hover_bg": "#1a2b3c",
    "tab_border": "#314257",
    "tab_active_border": "#5ad7ff",
    "tab_unread_bg": "#1b2735",
    "tab_unread_fg": "#ffffff",
    "unread_bg": "#ffb84d",
    "unread_fg": "#0b0f14",
    "alert_bg": "#ff5a5f",
    "close_fg": "#ff8a8f",
    "close_hover_bg": "#5c1f28",
    "empty_fg": "#8b98a8",
    "restore_bg": "#162231",
    "restore_fg": "#9be28f",
}


DEFAULT_APPEARANCE = {
    "preset": "Default Dark",
    "font_family": "Segoe UI",
    "font_size": 10,
    "window_opacity": 1.0,
    "background": "#070b10",
    "foreground": "#d7dde5",
    "highlight_backgrounds": False,
    "time": {"foreground": "#778493", "bold": False, "background": ""},
    "sender": {"foreground": "#d7dde5", "bold": False, "background": ""},
    "system": {"foreground": "#ffd54a", "bold": True, "background": "#332900"},
    "asset": {"foreground": "#ff9d2e", "bold": True, "background": "#332000"},
    "module": {"foreground": "#b388ff", "bold": True, "background": "#241b35"},
    "ess": {"foreground": "#5ad7ff", "bold": True, "background": "#0b2a33"},
    "esi": {"foreground": "#ff5c5c", "bold": True, "background": "#351719"},
    "translation": {"foreground": "#9be28f", "bold": False, "background": ""},
    "muted": {"foreground": "#8b98a8", "bold": False, "background": ""},
    "error": {"foreground": "#ff5a5f", "bold": True, "background": ""},
    "link": {"foreground": "#5ad7ff", "bold": False, "background": "", "underline": True},
}

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

STYLE_TAGS = ("time", "sender", "system", "asset", "module", "ess", "esi", "translation", "muted", "error", "link")


def tab_id_for_channel(channel: str) -> str:
    return channel


def tab_label(tab_id: str) -> str:
    return "All" if tab_id == ALL_CHANNELS_TAB else tab_id


def short_tab_label(label: str, max_chars: int = 28) -> str:
    label = str(label)
    return label if len(label) <= max_chars else label[: max_chars - 1] + "…"



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
        # Mobile-style default: narrow, tall layout suitable for side-panel/overlay use.
        # Users can still resize freely, and their OS/window-manager placement persists normally.
        self.root.geometry("430x720")
        self.root.minsize(360, 420)
        self.root.configure(bg="#0b0f14")
        self.always_on_top = tk.BooleanVar(value=bool(SETTINGS.get("always_on_top", True)))
        self.compact = tk.BooleanVar(value=bool(SETTINGS.get("compact_mode", True)))
        # When enabled, DB-localized Chinese ship names are shown as English only.
        # When disabled, original text is shown first with translated text underneath.
        self.translated_only = tk.BooleanVar(value=bool(SETTINGS.get("translated_only", True)))
        self.translate_chinese_text = tk.BooleanVar(value=bool(SETTINGS.get("translate_free_text", True)))
        self.translation_direction = tk.StringVar(value=str(SETTINGS.get("translation_direction", "zh-en")))
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
        self.stop_event: threading.Event | None = None
        self.monitor: MonitorThread | None = None
        self.row_count = 0
        self.rows: list[Row] = []
        self.rendered_row_map: dict[str, dict] = {}
        self.link_map: dict[str, str] = {}
        self.render_seq = 0
        write_log(f"Starting {APP_NAME} v{APP_VERSION}")
        self._build_menu()
        self._build_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.after(150, self.drain_queue)

    def _build_menu(self):
        tk = self.tk
        menubar = tk.Menu(self.root, bg="#111821", fg="#d7dde5", tearoff=False)
        file_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        file_menu.add_command(label="Start Monitoring", command=self.start_monitor)
        file_menu.add_command(label="Stop Monitoring", command=self.stop_monitor)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Feed", command=self.clear_feed)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        channels_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        channels_menu.add_command(label="Choose / Open Channels...", command=self.choose_channels)
        channels_menu.add_command(label="Restore Hidden Tabs...", command=self.restore_hidden_tabs_dialog)
        channels_menu.add_command(label="Restore Last Hidden Tab", command=self.restore_last_hidden_tab)
        channels_menu.add_separator()
        channels_menu.add_command(label="Close All Active Channels", command=self.close_selected_channels)
        channels_menu.add_command(label="Refresh Channel List", command=self.refresh_channel_status)
        menubar.add_cascade(label="Channels", menu=channels_menu)
        settings_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        settings_menu.add_command(label="Choose Chatlog Folder...", command=self.choose_chatlog_folder)
        settings_menu.add_separator()
        settings_menu.add_command(label="Install Argos Offline Fallback", command=self.install_argos_models)
        settings_menu.add_command(label="Open App Folder", command=self.open_app_folder)
        settings_menu.add_command(label="Open Logs Folder", command=self.open_logs_folder)
        settings_menu.add_separator()
        settings_menu.add_command(label="ESI / OAuth...", command=self.show_esi_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        view_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        view_menu.add_checkbutton(label="Always on Top", variable=self.always_on_top, command=self.apply_topmost)
        view_menu.add_checkbutton(label="Translated Only", variable=self.translated_only, command=self.persist_and_redraw)
        view_menu.add_checkbutton(label="Translate Free Text", variable=self.translate_chinese_text, command=self.persist_and_redraw)
        view_menu.add_separator()
        view_menu.add_radiobutton(label="Auto -> EN", variable=self.translation_direction, value="zh-en", command=self.persist_and_redraw)
        view_menu.add_radiobutton(label="EN -> CN", variable=self.translation_direction, value="en-zh", command=self.persist_and_redraw)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Compact Mode", variable=self.compact, command=self.persist_settings)
        view_menu.add_checkbutton(label="Show Timestamps", variable=self.show_timestamps, command=self.persist_and_redraw)
        view_menu.add_checkbutton(label="Show Channel Names in Feed", variable=self.show_channel_names, command=self.persist_and_redraw)
        view_menu.add_checkbutton(label="Show Channel Names in All", variable=self.show_channel_names_in_all, command=self.persist_and_redraw)
        view_menu.add_separator()
        view_menu.add_command(label="Appearance / Display Options...", command=self.show_appearance_dialog)
        view_menu.add_command(label="Choose Font...", command=self.choose_font)
        view_menu.add_command(label="Increase Font Size", command=lambda: self.adjust_font_size(1))
        view_menu.add_command(label="Decrease Font Size", command=lambda: self.adjust_font_size(-1))
        menubar.add_cascade(label="View", menu=view_menu)
        tools_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        tools_menu.add_command(label="Health / Catalog Status", command=self.show_health)
        tools_menu.add_command(label="Check Catalog Updates", command=self.check_catalog_updates)
        tools_menu.add_command(label="Restore Previous Catalog", command=self.restore_previous_catalog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Translation Cache Status", command=self.show_translation_cache)
        tools_menu.add_command(label="Clear Translation Cache", command=self.clear_translation_cache)
        tools_menu.add_command(label="Open Phrase Overrides", command=self.open_phrase_overrides)
        tools_menu.add_separator()
        tools_menu.add_command(label="ESI Cache Status", command=self.show_esi_cache_status)
        tools_menu.add_command(label="ESI Last Check / Diagnostics", command=self.show_esi_diagnostics)
        tools_menu.add_command(label="Manual ESI Character Check...", command=self.manual_esi_check_dialog)
        tools_menu.add_command(label="General Exclusion List...", command=self.show_esi_exclusion_list)
        tools_menu.add_command(label="Clear ESI Cache", command=self.clear_esi_cache)
        tools_menu.add_separator()
        tools_menu.add_command(label="Open Chatlog Folder", command=self.open_folder)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        help_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        help_menu.add_command(label="Check for Updates", command=lambda: self.check_for_updates(manual=True))
        help_menu.add_checkbutton(label="Check for Updates on Launch", variable=self.check_updates_on_start, command=self.persist_settings)
        help_menu.add_separator()
        help_menu.add_command(label="About Signal Bridge", command=self.show_about)
        help_menu.add_command(label="Support / Donate ISK", command=self.show_support)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_widgets(self):
        tk = self.tk
        top = tk.Frame(self.root, bg="#111821")
        top.pack(fill="x")
        self.title_label = tk.Label(top, text=f"{APP_NAME} v{APP_VERSION}", bg="#111821", fg="#d7dde5", font=("Consolas", 11, "bold"), padx=8, pady=5)
        self.title_label.pack(side="left")
        # Color legend intentionally hidden; colors are documented in Help/About and should not clutter the header.
        self.mode_label = tk.Label(top, text="", bg="#111821", fg="#5ad7ff", font=("Segoe UI", 9), padx=8)
        self.status_label = tk.Label(top, text="Idle", bg="#111821", fg="#8b98a8", font=("Segoe UI", 9), padx=8)
        self.status_label.pack(side="right")
        self.tab_bar = tk.Frame(self.root, bg=TAB_THEME["bar_bg"], padx=6, pady=4)
        self.tab_bar.pack(fill="x")
        self.tab_bar.bind("<Configure>", self.on_tab_bar_configure)
        self.update_channel_tabs()
        frame = tk.Frame(self.root, bg="#0b0f14")
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, relief="flat", wrap="word", font=self.feed_font(), padx=8, pady=8, undo=False)
        scroll = tk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.configure_feed_tags()
        self.text.bind("<Button-3>", self.show_feed_context_menu)
        self.text.configure(state="disabled")

    def normalize_tab_state(self, prefer_all: bool = False):
        valid = set(self.active_channels)
        valid.add(ALL_CHANNELS_TAB)
        self.hidden_tab_ids = {x for x in self.hidden_tab_ids if x in valid}
        ordered: list[str] = []
        for tab_id in self.tab_order:
            if tab_id in valid and tab_id not in ordered:
                ordered.append(tab_id)
        if ALL_CHANNELS_TAB not in ordered:
            ordered.insert(0, ALL_CHANNELS_TAB)
        for channel in sorted(self.active_channels):
            if channel not in ordered:
                ordered.append(channel)
        self.tab_order = ordered
        visible = self.visible_tabs()
        if self.visible_channel not in visible:
            if prefer_all and ALL_CHANNELS_TAB in visible:
                self.visible_channel = ALL_CHANNELS_TAB
            else:
                self.visible_channel = visible[0] if visible else None

    def visible_tabs(self) -> list[str]:
        valid_channels = set(self.active_channels)
        tabs = []
        if ALL_CHANNELS_TAB not in self.hidden_tab_ids:
            tabs.append(ALL_CHANNELS_TAB)
        for tab_id in self.tab_order:
            if tab_id == ALL_CHANNELS_TAB:
                continue
            if tab_id in valid_channels and tab_id not in self.hidden_tab_ids:
                tabs.append(tab_id)
        return tabs

    def on_tab_bar_configure(self, _event=None):
        if self._tab_layout_after:
            try:
                self.root.after_cancel(self._tab_layout_after)
            except Exception:
                pass
        self._tab_layout_after = self.root.after(80, self.layout_tab_widgets)

    def tab_style(self, active: bool = False, unread: bool = False) -> dict:
        bg = TAB_THEME["tab_active_bg"] if active else (TAB_THEME["tab_unread_bg"] if unread else TAB_THEME["tab_bg"])
        return {
            "bg": bg,
            "fg": TAB_THEME["tab_active_fg"] if active else (TAB_THEME["tab_unread_fg"] if unread else TAB_THEME["tab_fg"]),
            "activebackground": TAB_THEME["tab_hover_bg"],
            "activeforeground": TAB_THEME["tab_active_fg"],
            "border": TAB_THEME["tab_active_border"] if active else TAB_THEME["tab_border"],
        }

    def tab_display_text(self, tab_id: str) -> str:
        label = short_tab_label(tab_label(tab_id))
        unread = self.unread_counts.get(tab_id, 0)
        if unread:
            suffix = str(unread) if unread < 100 else "99+"
            return f"{label}  •{suffix}"
        return label

    def update_channel_tabs(self):
        tk = self.tk
        for child in self.tab_bar.winfo_children():
            child.destroy()
        self.tab_widgets = {}
        self.normalize_tab_state(prefer_all=True)
        tabs = self.visible_tabs()
        if not tabs:
            container = tk.Frame(self.tab_bar, bg=TAB_THEME["bar_bg"])
            label = tk.Label(container, text="No visible tabs - restore hidden tabs or choose channels", bg=TAB_THEME["bar_bg"], fg=TAB_THEME["empty_fg"], font=("Segoe UI", 9))
            label.pack(side="left", padx=4)
            btn = tk.Button(container, text="Restore...", command=self.restore_hidden_tabs_dialog, bg=TAB_THEME["tab_bg"], fg=TAB_THEME["tab_fg"], relief="flat", padx=6, pady=1)
            btn.pack(side="left", padx=6)
            self.tab_widgets["__empty__"] = container
            self.layout_tab_widgets()
            return
        for tab_id in tabs:
            active = tab_id == self.visible_channel
            unread = self.unread_counts.get(tab_id, 0) > 0
            style = self.tab_style(active, unread)
            border = TAB_THEME["alert_bg"] if tab_id == self._tab_drop_target else style["border"]
            frame = tk.Frame(self.tab_bar, bg=style["bg"], bd=0, relief="flat", highlightthickness=1, highlightbackground=border, highlightcolor=border)
            frame._tab_id = tab_id  # type: ignore[attr-defined]
            btn = tk.Button(
                frame,
                text=self.tab_display_text(tab_id),
                command=lambda t=tab_id: self.select_tab(t),
                bg=style["bg"], fg=style["fg"],
                activebackground=style["activebackground"], activeforeground=style["activeforeground"],
                relief="flat", borderwidth=0, padx=10, pady=3,
                font=("Segoe UI", 9, "bold" if active or unread else "normal")
            )
            btn.pack(side="left")
            close = tk.Button(
                frame, text="x", command=lambda t=tab_id: self.hide_tab(t),
                bg=style["bg"], fg=TAB_THEME["close_fg"], activebackground=TAB_THEME["close_hover_bg"], activeforeground="#ffffff",
                relief="flat", borderwidth=0, padx=6, pady=3, font=("Segoe UI", 9, "bold")
            )
            close.pack(side="left")
            for widget in (frame, btn):
                widget.bind("<Enter>", lambda e, t=tab_id: self.set_tab_hover(t, True), add="+")
                widget.bind("<Leave>", lambda e, t=tab_id: self.set_tab_hover(t, False), add="+")
                widget.bind("<ButtonPress-1>", lambda e, t=tab_id: self.begin_tab_drag(e, t), add="+")
                widget.bind("<B1-Motion>", self.move_tab_drag, add="+")
                widget.bind("<ButtonRelease-1>", self.end_tab_drag, add="+")
                widget.bind("<Button-3>", lambda e, t=tab_id: self.show_tab_context_menu(e, t), add="+")
            close.bind("<Enter>", lambda e, w=close: w.configure(bg=TAB_THEME["close_hover_bg"], fg="#ffffff"), add="+")
            close.bind("<Leave>", lambda e, w=close, bg=style["bg"]: w.configure(bg=bg, fg=TAB_THEME["close_fg"]), add="+")
            close.bind("<Button-3>", lambda e, t=tab_id: self.show_tab_context_menu(e, t), add="+")
            self.tab_widgets[tab_id] = frame
        hidden_count = len([t for t in self.tab_order if t in self.hidden_tab_ids and (t == ALL_CHANNELS_TAB or t in self.active_channels)])
        if hidden_count:
            restore = tk.Button(
                self.tab_bar, text=f"+ Hidden ({hidden_count})", command=self.restore_hidden_tabs_dialog,
                bg=TAB_THEME["restore_bg"], fg=TAB_THEME["restore_fg"], activebackground=TAB_THEME["tab_hover_bg"], activeforeground="#ffffff",
                relief="flat", borderwidth=0, padx=9, pady=3, font=("Segoe UI", 9)
            )
            self.tab_widgets["__restore__"] = restore
        self.layout_tab_widgets()

    def set_tab_hover(self, tab_id: str, hover: bool):
        if tab_id == self.visible_channel:
            return
        widget = self.tab_widgets.get(tab_id)
        if not widget:
            return
        unread = self.unread_counts.get(tab_id, 0) > 0
        style = self.tab_style(False, unread)
        bg = TAB_THEME["tab_hover_bg"] if hover else style["bg"]
        try:
            widget.configure(bg=bg)
            for child in widget.winfo_children():
                child.configure(bg=bg)
        except Exception:
            pass

    def layout_tab_widgets(self):
        if not hasattr(self, "tab_bar"):
            return
        for child in self.tab_bar.winfo_children():
            child.grid_forget()
        widgets = [self.tab_widgets[t] for t in self.visible_tabs() if t in self.tab_widgets]
        if "__restore__" in self.tab_widgets:
            widgets.append(self.tab_widgets["__restore__"])
        if not widgets and "__empty__" in self.tab_widgets:
            widgets = [self.tab_widgets["__empty__"]]
        width = max(1, self.tab_bar.winfo_width() - 16)
        x = 0
        row = 0
        col = 0
        max_rows = max(1, int(SETTINGS.get("max_tab_rows", 3) or 3))
        for widget in widgets:
            try:
                req = max(85, min(240, widget.winfo_reqwidth() + 8))
            except Exception:
                req = 140
            if col > 0 and x + req > width and row + 1 < max_rows:
                row += 1
                col = 0
                x = 0
            widget.grid(row=row, column=col, sticky="w", padx=4, pady=3)
            x += req + 10
            col += 1

    def select_tab(self, tab_id: str):
        if tab_id != ALL_CHANNELS_TAB and tab_id not in self.active_channels:
            return
        if tab_id in self.hidden_tab_ids:
            return
        self.visible_channel = tab_id
        self.unread_counts.pop(tab_id, None)
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()

    def select_channel_tab(self, channel: str):
        self.select_tab(channel)

    def select_all_channels_tab(self):
        self.select_tab(ALL_CHANNELS_TAB)

    def hide_tab(self, tab_id: str):
        if tab_id != ALL_CHANNELS_TAB and tab_id not in self.active_channels:
            return
        self.hidden_tab_ids.add(tab_id)
        self.unread_counts.pop(tab_id, None)
        if self.visible_channel == tab_id:
            visible = [t for t in self.visible_tabs() if t != tab_id]
            self.visible_channel = visible[0] if visible else None
        self.update_channel_tabs()
        self.persist_settings()
        self.redraw_feed()
        self.set_status(f"Hidden tab: {tab_label(tab_id)}")

    def close_channel(self, channel: str):
        self.hide_tab(channel)

    def restore_tab(self, tab_id: str, focus: bool = False):
        if tab_id != ALL_CHANNELS_TAB and tab_id not in self.active_channels:
            self.active_channels.add(tab_id)
        self.hidden_tab_ids.discard(tab_id)
        if tab_id not in self.tab_order:
            if tab_id == ALL_CHANNELS_TAB:
                self.tab_order.insert(0, tab_id)
            else:
                self.tab_order.append(tab_id)
        if focus or not self.visible_channel or not self.visible_tabs():
            self.visible_channel = tab_id
            self.unread_counts.pop(tab_id, None)
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
        win.title("Restore Hidden Tabs")
        win.geometry("360x420")
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        tk.Label(win, text="Select tabs to restore", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        lb = tk.Listbox(win, selectmode="extended", bg="#070b10", fg="#d7dde5", selectbackground="#23405c", activestyle="none")
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for tab_id in hidden:
            lb.insert("end", tab_label(tab_id))
        btns = tk.Frame(win, bg="#0b0f14")
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
        tk.Button(btns, text="Restore Selected", command=restore_selected).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Restore All", command=restore_all).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    def show_tab_context_menu(self, event, tab_id: str):
        menu = self.tk.Menu(self.root, tearoff=False, bg="#111821", fg="#d7dde5")
        label = "Close / Hide All Tab" if tab_id == ALL_CHANNELS_TAB else "Close Channel"
        menu.add_command(label=label, command=lambda: self.hide_tab(tab_id))
        menu.add_command(label="Close Other Channels", command=lambda: self.hide_other_tabs(tab_id))
        menu.add_command(label="Close All Channels", command=self.close_selected_channels)
        if tab_id != ALL_CHANNELS_TAB:
            menu.add_separator()
            menu.add_command(label="Copy Channel Name", command=lambda: self.copy_to_clipboard(tab_id))
        menu.add_separator()
        menu.add_command(label="Restore Hidden Tabs...", command=self.restore_hidden_tabs_dialog)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_to_clipboard(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status("Copied")

    def hide_other_tabs(self, keep_tab_id: str):
        for tab_id in list(self.visible_tabs()):
            if tab_id != keep_tab_id:
                self.hidden_tab_ids.add(tab_id)
                self.unread_counts.pop(tab_id, None)
        self.visible_channel = keep_tab_id
        self.update_channel_tabs(); self.persist_settings(); self.redraw_feed()

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

    def refresh_channel_status(self):
        channels = discover_channels()
        self.set_status(f"Found {len(channels)} chat channels. Active: {len(self.active_channels)} Hidden tabs: {len(self.hidden_tab_ids)}")

    def choose_channels(self):
        tk = self.tk
        channels = discover_channels()
        win = tk.Toplevel(self.root)
        win.title("Choose / Open Chat Channels")
        win.geometry("460x560")
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        tk.Label(win, text="Select channels to add/open", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        tk.Label(win, text="Add Selected keeps current channels. Replace All is explicit.", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0, 6))
        lb = tk.Listbox(win, selectmode="extended", bg="#070b10", fg="#d7dde5", selectbackground="#23405c", activestyle="none")
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for idx, channel in enumerate(channels):
            marker = "✓ " if channel in self.active_channels else "  "
            lb.insert("end", marker + channel)
            if channel in self.active_channels:
                lb.selection_set(idx)
        btns = tk.Frame(win, bg="#0b0f14")
        btns.pack(fill="x", padx=10, pady=8)
        def selected_channels():
            return {channels[i] for i in lb.curselection()}
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
        tk.Button(btns, text="Add Selected", command=add_selected).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Replace All", command=replace_selection).pack(side="left", padx=6)
        tk.Button(btns, text="All", command=select_all).pack(side="left", padx=6)
        tk.Button(btns, text="None", command=select_none).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    def add_channels(self, channels: set[str], manual: bool = False):
        channels = {str(c) for c in channels if str(c).strip()}
        if not channels:
            self.set_status("No channels selected")
            return
        self.set_channels(self.active_channels | channels, manual=manual, clear_existing=False)

    def set_channels(self, channels: set[str], manual: bool = False, clear_existing: bool = False):
        old_channels = set(self.active_channels)
        self.active_channels = set(channels)
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
        appearance = copy.deepcopy(DEFAULT_APPEARANCE)
        preset = None
        if isinstance(raw, dict):
            preset = raw.get("preset")
            if preset in APPEARANCE_PRESETS:
                appearance = merge(appearance, APPEARANCE_PRESETS[preset])
            appearance = merge(appearance, raw)
        else:
            appearance["font_family"] = SETTINGS.get("font_family", appearance["font_family"])
            appearance["font_size"] = SETTINGS.get("font_size", appearance["font_size"])
        try:
            appearance["font_size"] = max(8, min(28, int(appearance.get("font_size", 10))))
        except Exception:
            appearance["font_size"] = 10
        try:
            appearance["window_opacity"] = max(0.55, min(1.0, float(appearance.get("window_opacity", 1.0))))
        except Exception:
            appearance["window_opacity"] = 1.0
        for key in STYLE_TAGS:
            if not isinstance(appearance.get(key), dict):
                appearance[key] = copy.deepcopy(DEFAULT_APPEARANCE[key])
            else:
                base = copy.deepcopy(DEFAULT_APPEARANCE[key])
                base.update(appearance[key])
                appearance[key] = base
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
        bg = self.safe_color(self.appearance.get("background", "#070b10"), "#070b10")
        fg = self.safe_color(self.appearance.get("foreground", "#d7dde5"), "#d7dde5")
        self.text.configure(bg=bg, fg=fg, insertbackground=fg, font=self.feed_font())
        for tag in STYLE_TAGS:
            self.text.tag_configure(tag, **self.tag_options(tag))
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
        win.title("Choose Feed Font")
        win.geometry("420x520")
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        tk.Label(win, text="Feed font", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        lb = tk.Listbox(win, bg="#070b10", fg="#d7dde5", selectbackground="#23405c", activestyle="none")
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        current_index = 0
        for idx, fam in enumerate(ordered):
            lb.insert("end", fam)
            if fam == self.font_family.get():
                current_index = idx
        if ordered:
            lb.selection_set(current_index)
            lb.see(current_index)
        controls = tk.Frame(win, bg="#0b0f14")
        controls.pack(fill="x", padx=10, pady=6)
        tk.Label(controls, text="Size:", bg="#0b0f14", fg="#d7dde5").pack(side="left")
        size_spin = tk.Spinbox(controls, from_=8, to=28, width=5, textvariable=self.font_size)
        size_spin.pack(side="left", padx=6)
        preview = tk.Label(win, text="Preview: 4-HWWF Loki ESS", bg="#070b10", fg="#d7dde5", padx=8, pady=8)
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
        btns = tk.Frame(win, bg="#0b0f14")
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

    def show_appearance_dialog(self):
        tk = self.tk
        from tkinter import colorchooser
        original = copy.deepcopy(self.appearance)
        win = tk.Toplevel(self.root)
        win.title("Appearance / Display Options")
        win.geometry("760x620")
        win.minsize(520, 420)
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        win.grab_set()
        vars = {}

        # Keep action buttons visible on narrow/mobile-style layouts by making
        # only the settings body scroll while the footer stays fixed.
        outer = tk.Frame(win, bg="#0b0f14")
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg="#0b0f14", highlightthickness=0, bd=0)
        body_scroll = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg="#0b0f14")
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
        try:
            import tkinter.font as tkfont
            families = sorted(set(tkfont.families(self.root)))
        except Exception:
            families = ["Segoe UI", "Aptos", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Courier New"]
        top = tk.LabelFrame(body, text="General", bg="#0b0f14", fg="#d7dde5", padx=10, pady=8)
        top.pack(fill="x", padx=12, pady=(10, 8))
        tk.Label(top, text="Preset", bg="#0b0f14", fg="#8b98a8").grid(row=0, column=0, sticky="w", pady=3)
        preset_menu = tk.OptionMenu(top, preset_var, *APPEARANCE_PRESETS.keys())
        preset_menu.configure(bg="#111821", fg="#d7dde5", activebackground="#23405c", activeforeground="#ffffff", highlightthickness=0)
        preset_menu.grid(row=0, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Label(top, text="Font", bg="#0b0f14", fg="#8b98a8").grid(row=1, column=0, sticky="w", pady=3)
        font_menu = tk.OptionMenu(top, fam_var, *families)
        font_menu.configure(bg="#111821", fg="#d7dde5", activebackground="#23405c", activeforeground="#ffffff", highlightthickness=0)
        font_menu.grid(row=1, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Label(top, text="Size", bg="#0b0f14", fg="#8b98a8").grid(row=1, column=2, sticky="w", pady=3)
        tk.Spinbox(top, from_=8, to=28, width=6, textvariable=size_var, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", buttonbackground="#111821").grid(row=1, column=3, sticky="w", padx=8, pady=3)
        tk.Label(top, text="Opacity", bg="#0b0f14", fg="#8b98a8").grid(row=2, column=0, sticky="w", pady=3)
        tk.Scale(top, from_=55, to=100, orient="horizontal", variable=opacity_var, bg="#0b0f14", fg="#d7dde5", troughcolor="#111821", activebackground="#5ad7ff", highlightthickness=0, length=230).grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=3)
        tk.Checkbutton(top, text="Background highlight rectangles", variable=bg_enabled, bg="#0b0f14", fg="#d7dde5", selectcolor="#111821", activebackground="#0b0f14", activeforeground="#ffffff").grid(row=2, column=2, columnspan=2, sticky="w", pady=3)
        top.columnconfigure(1, weight=1)

        grid = tk.LabelFrame(body, text="Highlight Colors", bg="#0b0f14", fg="#d7dde5", padx=8, pady=6)
        grid.pack(fill="x", padx=12, pady=4)
        tk.Label(grid, text="Category", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 4))
        tk.Label(grid, text="Text", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, columnspan=3, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Bold", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Background", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9, "bold")).grid(row=0, column=5, columnspan=3, sticky="w", pady=(0, 4))
        rows = [("time","Timestamp"),("sender","Sender"),("system","Systems"),("esi","Characters / ESI"),("asset","Ships"),("module","Modules / Assets"),("ess","ESS"),("translation","Translation"),("link","Links")]
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
            entry = tk.Entry(grid, textvariable=var, width=11, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", relief="flat")
            entry.grid(row=row, column=col + 1, sticky="w", padx=(0, 4), pady=2)
            tk.Button(grid, text="Pick", command=lambda v=var: choose_color(v), bg="#111821", fg="#d7dde5", activebackground="#23405c", activeforeground="#ffffff", relief="flat", padx=6).grid(row=row, column=col + 2, sticky="w", pady=2)
        for r, (key, label) in enumerate(rows, start=1):
            style = self.appearance.get(key, DEFAULT_APPEARANCE.get(key, {}))
            fg = tk.StringVar(value=str(style.get("foreground", "#d7dde5")))
            bold = tk.BooleanVar(value=bool(style.get("bold", False)))
            bg = tk.StringVar(value=str(style.get("background", "")))
            vars[key] = {"foreground": fg, "bold": bold, "background": bg}
            tk.Label(grid, text=label, bg="#0b0f14", fg="#d7dde5").grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)
            make_color_control(r, 1, fg, "#d7dde5")
            tk.Checkbutton(grid, variable=bold, bg="#0b0f14", selectcolor="#111821", activebackground="#0b0f14", command=lambda: update_preview()).grid(row=r, column=4, sticky="w", padx=(8, 8), pady=2)
            make_color_control(r, 5, bg, "#070b10")
        grid.columnconfigure(0, minsize=135)
        grid.columnconfigure(2, minsize=92)
        grid.columnconfigure(6, minsize=92)

        preview_box = tk.LabelFrame(body, text="Preview", bg="#0b0f14", fg="#d7dde5", padx=8, pady=6)
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
            fam_var.set(base.get("font_family", "Segoe UI")); size_var.set(int(base.get("font_size", 10))); opacity_var.set(float(base.get("window_opacity", 1.0))*100); bg_enabled.set(bool(base.get("highlight_backgrounds", False)))
            for key, data in vars.items():
                st = base.get(key, DEFAULT_APPEARANCE[key])
                data["foreground"].set(st.get("foreground", "#d7dde5")); data["bold"].set(bool(st.get("bold", False))); data["background"].set(st.get("background", ""))
            update_swatches()
            update_preview()
        update_swatches()
        for v in (fam_var, size_var, opacity_var, bg_enabled):
            try: v.trace_add("write", lambda *_: update_preview())
            except Exception: pass
        for data in vars.values():
            for v in data.values():
                try: v.trace_add("write", lambda *_: update_preview())
                except Exception: pass
        preset_var.trace_add("write", preset_changed)
        render_preview(collect())
        btns = tk.Frame(win, bg="#111821", highlightthickness=1, highlightbackground="#1f2f42")
        btns.pack(fill="x", side="bottom")
        tk.Button(btns, text="Reset Defaults", command=reset_defaults).pack(side="left", padx=(12, 6), pady=10)
        tk.Button(btns, text="Apply", command=lambda: apply_now(False)).pack(side="left", padx=6, pady=10)
        tk.Button(btns, text="OK", command=lambda: apply_now(True)).pack(side="right", padx=(6, 12), pady=10)
        tk.Button(btns, text="Cancel", command=cancel).pack(side="right", padx=6, pady=10)
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
            "compact_mode": bool(self.compact.get()),
            "font_family": self.font_family.get(),
            "font_size": int(self.font_size.get()),
            "appearance": self.normalize_appearance(getattr(self, "appearance", None)),
            "show_timestamps": bool(self.show_timestamps.get()),
            "show_channel_names": bool(self.show_channel_names.get()),
            "show_channel_names_in_all": bool(self.show_channel_names_in_all.get()),
            "active_tab_id": self.visible_channel or ALL_CHANNELS_TAB,
            "tab_order": list(self.tab_order),
            "hidden_tab_ids": sorted(self.hidden_tab_ids),
            "auto_open_new_channels": True,
            "auto_switch_to_new_channel": False,
            "max_tab_rows": int(SETTINGS.get("max_tab_rows", 3) or 3),
            "replay_on_start": False,
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

    def install_argos_models(self):
        if not self.messagebox.askyesno("Install Argos Offline Fallback", "Download and install Argos offline translation models into this portable app folder?\n\nThis may take time and uses internet once."):
            return
        self.set_status("Installing Argos models in background...")
        threading.Thread(target=self._install_argos_models_worker, daemon=True).start()

    def _install_argos_models_worker(self):
        try:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            try:
                import argostranslate.package  # type: ignore
            except Exception:
                self.set_status("Argos package is not bundled/installed. Release build should include argostranslate.")
                return
            argostranslate.package.update_package_index()
            packages = argostranslate.package.get_available_packages()
            wanted = [("zh", "en"), ("en", "zh")]
            installed = []
            for src, dst in wanted:
                pkg = next((p for p in packages if p.from_code == src and p.to_code == dst), None)
                if not pkg:
                    continue
                path = pkg.download()
                argostranslate.package.install_from_path(path)
                installed.append(f"{src}->{dst}")
            self.set_status("Argos models installed: " + (", ".join(installed) or "none found"))
        except Exception as exc:
            self.set_status("Argos install failed: " + str(exc)[:160])

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
        win.title("ESI / OAuth Settings")
        win.geometry("560x460")
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        tk.Label(win, text="Optional ESI support", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        tk.Label(win, text="Signal Bridge works normally with ESI disabled. OAuth is only needed for future character-aware features.", bg="#0b0f14", fg="#8b98a8", wraplength=520, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
        tk.Checkbutton(win, text="Enable ESI entity recognition", variable=self.esi_enabled, bg="#0b0f14", fg="#d7dde5", selectcolor="#111821", activebackground="#0b0f14", activeforeground="#ffffff").pack(anchor="w", padx=10)
        tk.Checkbutton(win, text="Enable OAuth features", variable=self.esi_oauth_enabled, bg="#0b0f14", fg="#d7dde5", selectcolor="#111821", activebackground="#0b0f14", activeforeground="#ffffff").pack(anchor="w", padx=10)
        form = tk.Frame(win, bg="#0b0f14"); form.pack(fill="x", padx=10, pady=8)
        tk.Label(form, text="Client ID", bg="#0b0f14", fg="#d7dde5").grid(row=0, column=0, sticky="w", pady=3)
        client_id = tk.Entry(form, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", width=52)
        client_id.insert(0, str(self.esi_settings.get("client_id") or ESI_DEFAULT_CLIENT_ID)); client_id.grid(row=0, column=1, sticky="ew", padx=8, pady=3)
        tk.Label(form, text="Client Secret", bg="#0b0f14", fg="#d7dde5").grid(row=1, column=0, sticky="w", pady=3)
        client_secret = tk.Entry(form, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", show="*", width=52)
        client_secret.insert(0, str(self.esi_settings.get("client_secret") or "")); client_secret.grid(row=1, column=1, sticky="ew", padx=8, pady=3)
        tk.Label(form, text="Callback", bg="#0b0f14", fg="#d7dde5").grid(row=2, column=0, sticky="w", pady=3)
        callback = tk.Entry(form, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", width=52)
        callback.insert(0, str(self.esi_settings.get("callback_url") or ESI_CALLBACK_URL)); callback.grid(row=2, column=1, sticky="ew", padx=8, pady=3)
        form.columnconfigure(1, weight=1)
        stats = ESI_CACHE.stats()
        status_text = f"Cache: {stats.get('entities',0)} entities, {stats.get('negative',0)} negative, {stats.get('corrections',0)} corrections\nCallback listener: {'listening' if self.oauth_listener_active else 'closed'}\nToken file: {'present' if ESI_TOKENS_PATH.exists() else 'not authorized'}"
        tk.Label(win, text=status_text, bg="#0b0f14", fg="#8b98a8", justify="left").pack(anchor="w", padx=10, pady=8)
        btns = tk.Frame(win, bg="#0b0f14"); btns.pack(fill="x", padx=10, pady=10)
        def apply():
            self.esi_settings["client_id"] = client_id.get().strip() or ESI_DEFAULT_CLIENT_ID
            self.esi_settings["client_secret"] = client_secret.get().strip()
            self.esi_settings["callback_url"] = callback.get().strip() or ESI_CALLBACK_URL
            self.save_esi_ui_settings()
        tk.Button(btns, text="Save", command=apply).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Authorize Character", command=lambda: (apply(), self.authorize_esi_character())).pack(side="left", padx=6)
        tk.Button(btns, text="Check ESI", command=self.check_esi_status).pack(side="left", padx=6)
        tk.Button(btns, text="Close", command=win.destroy).pack(side="right")

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
                if is_globally_excluded(query) and not force:
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
        win.title("General Exclusion List")
        win.configure(bg="#0b0f14")
        win.geometry("520x420")
        self.tk.Label(win, text="Names excluded from ESI character detection", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        frame = self.tk.Frame(win, bg="#0b0f14"); frame.pack(fill="both", expand=True, padx=12, pady=6)
        lb = self.tk.Listbox(frame, bg="#070b10", fg="#d7dde5", selectbackground="#1f6feb", relief="flat")
        sb = self.tk.Scrollbar(frame, command=lb.yview); lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        entry = self.tk.Entry(win, bg="#111821", fg="#d7dde5", insertbackground="#d7dde5", relief="flat")
        entry.pack(fill="x", padx=12, pady=(4, 8))
        def reload_list():
            lb.delete(0, "end")
            for item in ESI_CACHE.list_corrections("ignore"):
                lb.insert("end", item.get("text") or "")
        def add_name():
            raw = entry.get().strip()
            if not raw:
                return
            if ESI_CACHE.set_correction(raw, "ignore", note="user exclusion list"):
                self.esi_entities.pop(normalize_esi_query(raw), None)
                entry.delete(0, "end"); reload_list(); self.set_status(f"Excluded from ESI: {raw}")
        def remove_selected():
            sel = list(lb.curselection())
            if not sel:
                return
            for idx in reversed(sel):
                val = lb.get(idx)
                ESI_CACHE.remove_correction(val)
            reload_list(); self.set_status("Exclusion removed")
        def import_names():
            raw = self.simpledialog.askstring("Import exclusions", "Paste one name per line:", parent=win)
            if not raw:
                return
            count = 0
            for line in raw.splitlines():
                name = line.strip()
                if name and ESI_CACHE.set_correction(name, "ignore", note="bulk import"):
                    count += 1
            reload_list(); self.set_status(f"Imported {count} exclusions")
        buttons = self.tk.Frame(win, bg="#0b0f14"); buttons.pack(fill="x", padx=12, pady=(0, 12))
        self.tk.Button(buttons, text="Add", command=add_name).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Remove Selected", command=remove_selected).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Import...", command=import_names).pack(side="left", padx=(0, 6))
        self.tk.Button(buttons, text="Close", command=win.destroy).pack(side="right")
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
        if query and ESI_CACHE.set_correction(query, "ignore", note="user ignored"):
            self.esi_entities.pop(normalize_esi_query(query), None)
            self.set_status(f"Excluded: {query}")

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
        self.monitor = MonitorThread(self.queue, self.stop_event, self.set_status, set(self.active_channels), replay_today=False)
        self.monitor.start()
        write_log(f"Monitor starting live-only for {len(self.active_channels)} channel(s); replay_today=False")
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
        self.messagebox.showinfo("Translation Cache", f"Cache file: {TRANSLATION_CACHE_PATH}\nEntries: {count}\nHits: {hits}")

    def clear_translation_cache(self):
        if self.messagebox.askyesno("Translation Cache", "Clear all cached machine translations?"):
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

    def show_about(self):
        self.messagebox.showinfo(
            "About Signal Bridge",
            f"Signal Bridge v{APP_VERSION}\n"
            "EVE Online live chat intel translator\n\n"
            "Highlights:\n"
            "- Systems: yellow\n"
            "- Ships: red\n"
            "- Non-ship assets/modules: purple\n"
            "- ESS: light blue\n"
            "- Active chats appear as hideable/reorderable tabs\n"
            "- All tab shows combined chat view\n"
            "- Unread indicators appear on inactive tabs\n"
            "- Right-click feed copy actions and HTTP/HTTPS links\n"
            "- Configurable feed font and timestamp display\n\n"
            "Translation:\n"
            f"- Compact EVE catalog: {CATALOG.version}\n"
            "- Google free auto-detect to English\n"
            "- Argos fallback when available\n"
            "- Simple nonblocking GitHub update check on launch\n"
            "- Optional cache-first ESI entity recognition/OAuth foundation"
        )

    def show_support(self):
        self.messagebox.showinfo("Support Signal Bridge", DONATION_TEXT)

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
        self.persist_settings()
        if self.esi_resolver:
            self.esi_resolver.stop()
        self.stop_monitor()
        self.root.after(100, self.root.destroy)

    def row_display_parts(self, row: Row) -> dict:
        display_text = self.localized_display_text(row)
        free_text = self.display_free_translation(row, display_text)
        translated = free_text or display_text
        show_channel = bool(self.show_channel_names.get()) or (self.visible_channel == ALL_CHANNELS_TAB and bool(self.show_channel_names_in_all.get()))
        prefix = ""
        if bool(self.show_timestamps.get()):
            prefix += f"[{row.received_at.split()[-1]}] "
        if show_channel:
            prefix += f"[{row.channel}] "
        sender_prefix = f"{row.sender} > "
        visible_text = translated if bool(self.translated_only.get()) else row.text
        visible_line = prefix + sender_prefix + visible_text
        original_line = prefix + sender_prefix + row.text
        translated_line = prefix + sender_prefix + translated
        return {
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
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            for tag in self.text.tag_names(index):
                if tag.startswith("link_"):
                    return self.link_map.get(tag)
        except Exception:
            pass
        return None

    def show_feed_context_menu(self, event):
        row_tag, info = self.row_at_event(event)
        url = self.link_at_event(event)
        selected = self.selected_feed_text()
        row = info["row"] if info else None
        menu = self.tk.Menu(self.root, tearoff=False, bg="#111821", fg="#d7dde5")
        if url:
            menu.add_command(label="Open URL", command=lambda u=url: self.open_url(u))
            menu.add_command(label="Copy URL", command=lambda u=url: self.copy_to_clipboard(u))
            menu.add_separator()
        if info:
            menu.add_command(label="Copy Visible Line", command=lambda i=info: self.copy_to_clipboard(i["visible_line"]))
            menu.add_command(label="Copy Original Line", command=lambda i=info: self.copy_to_clipboard(i["original_line"]))
            menu.add_command(label="Copy Translated Line", command=lambda i=info: self.copy_to_clipboard(i["translated_line"]))
            menu.add_separator()
            menu.add_command(label="Copy Sender", command=lambda r=row: self.copy_to_clipboard(r.sender))
            menu.add_command(label="Copy Systems", command=lambda r=row: self.copy_to_clipboard(", ".join(r.systems)))
            menu.add_command(label="Copy Ships / Assets", command=lambda r=row: self.copy_to_clipboard(", ".join(r.assets)))
            menu.add_command(label="Copy URLs", command=lambda r=row: self.copy_to_clipboard("\n".join(self.http_links_for_row(r))))
            menu.add_command(label="Copy Translation Details", command=lambda i=info: self.copy_to_clipboard(f"source={i.get('source_label','none')}"))
            menu.add_separator()
        else:
            menu.add_command(label="Copy Selected Text", command=self.copy_selected_text)
            menu.add_command(label="Copy Visible Feed", command=self.copy_visible_feed)
            menu.add_separator()
        # Keep ESI actions visible even when row detection misses, so users can diagnose and use selected text.
        if selected:
            menu.add_command(label="Resolve Selected Text with ESI", command=self.resolve_selected_esi_text)
            menu.add_command(label="Add Selected Text as ESI Character", command=self.add_selected_esi_character)
            menu.add_command(label="Add Selected Text to Exclusion List", command=self.ignore_selected_esi_text)
        else:
            menu.add_command(label="Resolve Selected Text with ESI", command=self.resolve_selected_esi_text, state="disabled")
            menu.add_command(label="Add Selected Text as ESI Character", command=self.add_selected_esi_character, state="disabled")
            menu.add_command(label="Add Selected Text to Exclusion List", command=self.ignore_selected_esi_text, state="disabled")
        if row:
            menu.add_command(label="Resolve Sender with ESI", command=lambda r=row: self.refresh_esi_entity(r.sender))
            menu.add_command(label="Refresh Sender ESI Data", command=lambda r=row: self.refresh_esi_entity(r.sender))
            menu.add_command(label="Show ESI Candidates for Message", command=lambda r=row: self.show_esi_candidates_for_row(r))
            menu.add_command(label="Copy ESI Details", command=lambda r=row: self.copy_to_clipboard(self.esi_details_for_row(r)))
            menu.add_command(label="Add Sender to Exclusion List", command=lambda r=row: self.ignore_esi_entity(r.sender))
        else:
            menu.add_command(label="Show ESI Candidates for Message", command=lambda: self.show_esi_candidates_for_row(None), state="disabled")
        menu.add_command(label="ESI Last Check / Diagnostics", command=self.show_esi_diagnostics)
        menu.add_command(label="Manual ESI Character Check...", command=self.manual_esi_check_dialog)
        menu.add_command(label="General Exclusion List...", command=self.show_esi_exclusion_list)
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

    def insert_tagged_text(self, text: str, systems: list[str], assets: list[str]):
        start_index = self.text.index("end-1c")
        self.text.insert("end", text)
        # Tag exact spans inside the inserted region.
        region_start = start_index
        region_end = self.text.index("end-1c")
        for term in sorted(unique(systems), key=len, reverse=True):
            if is_globally_excluded(term):
                continue
            self.tag_term(term, "system", region_start, region_end)
        for term in sorted(unique(assets), key=len, reverse=True):
            term_key = normalize_esi_query(term)
            if term_key in COMMON_ESI_NOISE or is_globally_excluded(term):
                continue
            if term.lower() == "ess":
                self.tag_term_whole_word(term, "ess", region_start, region_end)
            elif CATALOG.is_ship(term):
                self.tag_term(term, "asset", region_start, region_end)
            else:
                self.tag_term(term, "module", region_start, region_end)
        # Defensive: highlight standalone literal ESS unless excluded by the user.
        if not is_globally_excluded("ESS"):
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
        display = row.text
        for ent in sorted(row.localized, key=lambda e: -len(e.get("original", ""))):
            original = ent.get("original", "")
            canonical = ent.get("canonical", "")
            if original and canonical:
                display = display.replace(original, canonical)
        return display

    def redraw_feed(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.rendered_row_map.clear()
        self.link_map.clear()
        old_rows = list(self.rows[-MAX_ROWS:])
        self.row_count = 0
        for row in old_rows:
            if self.row_visible(row):
                self._render_row(row)

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
        if self.visible_channel == row.channel:
            return
        if self.visible_channel == ALL_CHANNELS_TAB and ALL_CHANNELS_TAB not in self.hidden_tab_ids:
            return
        self.unread_counts[row.channel] = self.unread_counts.get(row.channel, 0) + 1
        if ALL_CHANNELS_TAB not in self.hidden_tab_ids and self.visible_channel != ALL_CHANNELS_TAB:
            self.unread_counts[ALL_CHANNELS_TAB] = self.unread_counts.get(ALL_CHANNELS_TAB, 0) + 1
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

    def append_row(self, row: Row):
        self.rows.append(row)
        if self.esi_is_enabled():
            self.ensure_esi_resolver()
            self.hydrate_esi_entities_for_row(row)
            if self.esi_resolver:
                for candidate in esi_candidates_for_row(row):
                    self.esi_resolver.submit(candidate)
        self.ensure_row_channel_tab(row.channel)
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[-MAX_ROWS:]
        if self.row_visible(row):
            self._render_row(row)
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
            if cached and not cached.get("ignored") and not is_globally_excluded(cand) and cached.get("entity_type") == "character":
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
            if any(is_globally_excluded(n) for n in names if n):
                continue
            if not any(n and re.search(word_boundary(n), text_blob, re.I) for n in names):
                continue
            key = normalize_esi_query(ent.get("query") or ent.get("name") or "")
            if key and key not in existing:
                row.esi_entities.append(ent); existing.add(key); changed = True
        return changed

    def character_names_for_row(self, row: Row) -> list[str]:
        names: list[str] = []
        sender = re.sub(r"\s+", " ", row.sender.strip())
        if sender and sender.lower() != "eve system":
            names.append(sender)
        for cand in getattr(row, "esi_candidates", []) or []:
            cached = self.esi_entities.get(normalize_esi_query(cand)) or ESI_CACHE.get_entity(cand)
            if cached and not cached.get("ignored") and not is_globally_excluded(cand) and cached.get("entity_type") == "character":
                names.append(str(cached.get("name") or cand))
                names.append(cand)
        for ent in row.esi_entities:
            if ent.get("entity_type") == "character":
                ent_name = str(ent.get("name") or ent.get("query") or "")
                ent_query = str(ent.get("query") or "")
                if is_globally_excluded(ent_name) or is_globally_excluded(ent_query):
                    continue
                names.append(ent_name)
                names.append(ent_query)
        return unique([n for n in names if n])

    def display_free_translation(self, row: Row, display_text: str) -> str:
        if not bool(self.translate_chinese_text.get()):
            return ""
        direction = self.translation_direction.get()
        if direction == "zh-en":
            if row.free_translation:
                return row.free_translation
            return translate_free_text(display_text, row.systems, row.assets, row.localized, row.counts, row.links, "zh-en", self.character_names_for_row(row))
        if direction == "en-zh":
            return translate_free_text(display_text, row.systems, row.assets, row.localized, row.counts, row.links, "en-zh", self.character_names_for_row(row))
        return ""

    def _render_row(self, row: Row):
        if self.esi_is_enabled():
            self.hydrate_esi_entities_for_row(row)
        self.text.configure(state="normal")
        row_tag = f"row_{self.render_seq}"
        self.render_seq += 1
        row_start = self.text.index("end-1c")
        parts = self.row_display_parts(row)
        ts = row.received_at.split()[-1]
        translated_only = bool(self.translated_only.get())
        if bool(self.show_timestamps.get()):
            self.text.insert("end", f"[{ts}] ", "time")
        show_channel = bool(self.show_channel_names.get()) or (self.visible_channel == ALL_CHANNELS_TAB and bool(self.show_channel_names_in_all.get()))
        if show_channel:
            self.text.insert("end", f"[{row.channel}] ", "muted")
        self.text.insert("end", f"{row.sender} > ", "sender")
        body_start = self.text.index("end-1c")
        if translated_only:
            body = parts["translated"]
            self.insert_tagged_text(body + "\n", row.systems, row.assets)
            self.tag_urls(body_start, self.text.index("end-1c"), body)
        else:
            self.insert_tagged_text(row.text + "\n", row.systems, row.assets + [x.get("original", "") for x in row.localized])
            self.tag_urls(body_start, self.text.index("end-1c"), row.text)
            if parts["free_text"] and parts["free_text"] != row.text:
                self.text.insert("end", "    translated: ", "muted")
                t_start = self.text.index("end-1c")
                self.insert_tagged_text(parts["free_text"] + "\n", row.systems, row.assets)
                self.tag_urls(t_start, self.text.index("end-1c"), parts["free_text"])
            elif parts["display_text"] != row.text:
                self.text.insert("end", "    translated: ", "muted")
                t_start = self.text.index("end-1c")
                self.insert_tagged_text(parts["display_text"] + "\n", row.systems, row.assets)
                self.tag_urls(t_start, self.text.index("end-1c"), parts["display_text"])
        row_end = self.text.index("end-1c")
        # Keep sender names visually neutral; only ESI-highlight names inside the message body/translation.
        for ent in row.esi_entities:
            name = str(ent.get("name") or ent.get("query") or "")
            if name and normalize_esi_query(name) not in COMMON_ESI_NOISE and not is_globally_excluded(name):
                self.tag_term(name, "esi", body_start, row_end)
        for name in self.character_names_for_row(row):
            if normalize_esi_query(name) not in COMMON_ESI_NOISE and not is_globally_excluded(name):
                self.tag_term(name, "esi", body_start, row_end)
        self.text.tag_add(row_tag, row_start, row_end)
        self.rendered_row_map[row_tag] = {"row": row, **parts}
        self.text.tag_bind(row_tag, "<Button-3>", self.show_feed_context_menu)
        self.text.see("end")
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
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "status":
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
            self.status_label.configure(text="Queue error; see logs")
        self.root.after(150, self.drain_queue)

    def handle_esi_resolved(self, query: str, data: dict):
        if is_globally_excluded(query) or is_globally_excluded(str(data.get("name") or "")):
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
        print(json.dumps(row.__dict__, ensure_ascii=False, sort_keys=True))
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





