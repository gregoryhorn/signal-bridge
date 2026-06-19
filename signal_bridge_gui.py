from __future__ import annotations
import argparse
import json
import queue
import re
import sqlite3
import sys
import threading
import time
import traceback
import webbrowser
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

APP_NAME = "Signal Bridge"
APP_VERSION = "0.1"
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
        "font_family": "Consolas",
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
    file: str


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


class EveDb:
    def __init__(self, path: Path):
        self.path = path
        self.con: sqlite3.Connection | None = None
        self.cache: dict[str, str | None] = {}
        if path.exists():
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
        out = None
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
    systems = unique(SYSTEM_RE.findall(text))
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


def translate_free_text(text: str, systems: list[str], assets: list[str], localized: list[dict], counts: list[str], links: list[str], direction: str = "zh-en") -> str:
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

    protected: list[tuple[str, str]] = []
    work = text
    terms: list[str] = []
    terms.extend(systems)
    terms.extend(assets)
    terms.extend(counts)
    terms.extend(links)
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


def parse_rows_from_text(text: str, fallback_channel: str, file_name: str, db: EveDb) -> list[Row]:
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
            free_translation = translate_free_text(display_body, systems, assets, localized, counts, links, "zh-en")
            rows.append(Row(channel, ts, sender, body, systems, assets, localized, counts, links, intent, translation, free_translation, file_name))
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
        self.db = EveDb(DB_PATH)

    def chat_files(self):
        if not self.channels:
            return []
        files: list[Path] = []
        for channel in sorted(self.channels):
            files.extend(CHATLOG_DIR.glob(channel + "_*.txt"))
        return sorted(set(files), key=lambda p: p.stat().st_mtime_ns)

    def emit_row(self, row: Row):
        if row.channel not in self.channels:
            return
        key = (row.channel.lower(), row.sender.lower(), row.text.lower())
        if key in self.seen:
            return
        self.seen.add(key)
        self.outq.put(row)

    def run(self):
        try:
            if not CHATLOG_DIR.exists():
                self.status(f"Missing chatlog folder: {CHATLOG_DIR}")
                return
            if not DB_PATH.exists():
                self.status(f"Warning: DB missing: {DB_PATH}")
            if self.replay_today:
                recent = sorted(self.chat_files(), key=lambda x: x.stat().st_mtime_ns, reverse=True)[:max(3, len(self.channels) * 3)]
                replay_rows = []
                for p in recent:
                    try:
                        text = decode_bytes(p.read_bytes())
                    except OSError:
                        continue
                    replay_rows.extend(parse_rows_from_text(text, channel_from_filename(p), p.name, self.db)[-40:])
                for row in replay_rows[-80:]:
                    self.emit_row(row)
            for p in self.chat_files():
                try:
                    self.offsets[str(p)] = p.stat().st_size
                except OSError:
                    pass
            self.status(f"Monitoring live: {len(self.channels)} channel(s), existing files snapshotted; DB={'yes' if DB_PATH.exists() else 'no'}")
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
                    for row in parse_rows_from_text(decode_bytes(data), channel_from_filename(p), p.name, self.db):
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
        self.root.geometry("920x560")
        self.root.minsize(540, 300)
        self.root.configure(bg="#0b0f14")
        self.always_on_top = tk.BooleanVar(value=bool(SETTINGS.get("always_on_top", True)))
        self.compact = tk.BooleanVar(value=bool(SETTINGS.get("compact_mode", True)))
        # When enabled, DB-localized Chinese ship names are shown as English only.
        # When disabled, original text is shown first with translated text underneath.
        self.translated_only = tk.BooleanVar(value=bool(SETTINGS.get("translated_only", True)))
        self.translate_chinese_text = tk.BooleanVar(value=bool(SETTINGS.get("translate_free_text", True)))
        self.translation_direction = tk.StringVar(value=str(SETTINGS.get("translation_direction", "zh-en")))
        self.font_family = tk.StringVar(value=str(SETTINGS.get("font_family", "Consolas")))
        try:
            initial_font_size = int(SETTINGS.get("font_size", 10))
        except Exception:
            initial_font_size = 10
        self.font_size = tk.IntVar(value=max(8, min(28, initial_font_size)))
        self.show_timestamps = tk.BooleanVar(value=bool(SETTINGS.get("show_timestamps", True)))
        self.show_channel_names = tk.BooleanVar(value=bool(SETTINGS.get("show_channel_names", False)))
        self.show_channel_names_in_all = tk.BooleanVar(value=bool(SETTINGS.get("show_channel_names_in_all", True)))
        self.check_updates_on_start = tk.BooleanVar(value=bool(SETTINGS.get("check_updates_on_start", True)))
        self.root.attributes("-topmost", bool(self.always_on_top.get()))
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
        settings_menu.add_command(label="Choose Translation DB...", command=self.choose_db_file)
        settings_menu.add_separator()
        settings_menu.add_command(label="Install Argos Offline Fallback", command=self.install_argos_models)
        settings_menu.add_command(label="Open App Folder", command=self.open_app_folder)
        settings_menu.add_command(label="Open Logs Folder", command=self.open_logs_folder)
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
        view_menu.add_command(label="Choose Font...", command=self.choose_font)
        view_menu.add_command(label="Increase Font Size", command=lambda: self.adjust_font_size(1))
        view_menu.add_command(label="Decrease Font Size", command=lambda: self.adjust_font_size(-1))
        menubar.add_cascade(label="View", menu=view_menu)
        tools_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        tools_menu.add_command(label="Backend / DB Health", command=self.show_health)
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
        self.mode_label = tk.Label(top, text="  Systems yellow | Ships red | ESS blue", bg="#111821", fg="#5ad7ff", font=("Segoe UI", 9), padx=8)
        self.mode_label.pack(side="left")
        self.status_label = tk.Label(top, text="Idle", bg="#111821", fg="#8b98a8", font=("Segoe UI", 9), padx=8)
        self.status_label.pack(side="right")
        self.tab_bar = tk.Frame(self.root, bg=TAB_THEME["bar_bg"], padx=6, pady=4)
        self.tab_bar.pack(fill="x")
        self.tab_bar.bind("<Configure>", self.on_tab_bar_configure)
        self.update_channel_tabs()
        frame = tk.Frame(self.root, bg="#0b0f14")
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, bg="#070b10", fg="#d7dde5", insertbackground="#d7dde5", relief="flat", wrap="word", font=self.feed_font(), padx=8, pady=8, undo=False)
        scroll = tk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.text.tag_configure("time", foreground="#778493")
        self.text.tag_configure("sender", foreground="#c9d2dc")
        self.text.tag_configure("system", foreground="#ffd54a", font=self.feed_font(bold=True))
        self.text.tag_configure("asset", foreground="#ff5a5f", font=self.feed_font(bold=True))
        self.text.tag_configure("ess", foreground="#5ad7ff", font=self.feed_font(bold=True))
        self.text.tag_configure("translation", foreground="#9be28f")
        self.text.tag_configure("muted", foreground="#8b98a8")
        self.text.tag_configure("error", foreground="#ff5a5f")
        self.text.tag_configure("link", foreground="#5ad7ff", underline=True)
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
        win.title("Choose Chat Channels")
        win.geometry("420x520")
        win.configure(bg="#0b0f14")
        win.transient(self.root)
        tk.Label(win, text="Select channels to monitor", bg="#0b0f14", fg="#d7dde5", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        lb = tk.Listbox(win, selectmode="extended", bg="#070b10", fg="#d7dde5", selectbackground="#23405c", activestyle="none")
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for idx, channel in enumerate(channels):
            lb.insert("end", channel)
            if channel in self.active_channels:
                lb.selection_set(idx)
        btns = tk.Frame(win, bg="#0b0f14")
        btns.pack(fill="x", padx=10, pady=8)
        def apply_selection():
            selected = {channels[i] for i in lb.curselection()}
            self.set_channels(selected, manual=True)
            win.destroy()
        def select_all():
            lb.selection_set(0, "end")
        def select_none():
            lb.selection_clear(0, "end")
        tk.Button(btns, text="Apply", command=apply_selection).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="All", command=select_all).pack(side="left", padx=6)
        tk.Button(btns, text="None", command=select_none).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    def set_channels(self, channels: set[str], manual: bool = False):
        old_channels = set(self.active_channels)
        self.active_channels = set(channels)
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
        self.clear_feed()
        self.stop_monitor()
        if self.active_channels:
            self.start_monitor()
        else:
            self.set_status("No channels selected")

    def close_selected_channels(self):
        self.set_channels(set(), manual=True)

    def is_all_channels_view(self) -> bool:
        return self.visible_channel == ALL_CHANNELS_TAB

    def feed_font(self, bold: bool = False):
        weight = "bold" if bold else "normal"
        return (self.font_family.get() or "Consolas", int(self.font_size.get()), weight)

    def apply_feed_font(self):
        self.text.configure(font=self.feed_font())
        self.text.tag_configure("system", font=self.feed_font(bold=True))
        self.text.tag_configure("asset", font=self.feed_font(bold=True))
        self.text.tag_configure("ess", font=self.feed_font(bold=True))
        self.persist_settings()
        self.redraw_feed()

    def adjust_font_size(self, delta: int):
        current = int(self.font_size.get())
        self.font_size.set(max(8, min(28, current + delta)))
        self.apply_feed_font()

    def choose_font(self):
        tk = self.tk
        try:
            import tkinter.font as tkfont
            families = sorted(set(tkfont.families(self.root)))
        except Exception:
            families = ["Consolas", "Courier New", "Segoe UI", "Arial", "Tahoma"]
        common = [f for f in ["Consolas", "Cascadia Mono", "Courier New", "Segoe UI", "Arial", "Tahoma", "Verdana"] if f in families]
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
            self.apply_feed_font()
            win.destroy()
        tk.Button(btns, text="Apply", command=apply_selection).pack(side="left")
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

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
            "- Ships/assets: red\n"
            "- ESS: light blue\n"
            "- Active chats appear as hideable/reorderable tabs\n"
            "- All tab shows combined chat view\n"
            "- Unread indicators appear on inactive tabs\n"
            "- Right-click feed copy actions and HTTP/HTTPS links\n"
            "- Configurable feed font and timestamp display\n\n"
            "Translation:\n"
            "- EVE DB localization\n"
            "- Google free auto-detect to English\n"
            "- Argos fallback when available\n"
            "- Simple nonblocking GitHub update check on launch"
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
            f"DB: {DB_PATH}\n"
            f"DB exists: {DB_PATH.exists()}\n"
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
            f"Update check on launch: {bool(self.check_updates_on_start.get())}"
        )


    def on_exit(self):
        self.persist_settings()
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
        menu = self.tk.Menu(self.root, tearoff=False, bg="#111821", fg="#d7dde5")
        if url:
            menu.add_command(label="Open URL", command=lambda u=url: self.open_url(u))
            menu.add_command(label="Copy URL", command=lambda u=url: self.copy_to_clipboard(u))
            menu.add_separator()
        if info:
            row = info["row"]
            menu.add_command(label="Copy Visible Line", command=lambda i=info: self.copy_to_clipboard(i["visible_line"]))
            menu.add_command(label="Copy Original Line", command=lambda i=info: self.copy_to_clipboard(i["original_line"]))
            menu.add_command(label="Copy Translated Line", command=lambda i=info: self.copy_to_clipboard(i["translated_line"]))
            menu.add_separator()
            menu.add_command(label="Copy Sender", command=lambda r=row: self.copy_to_clipboard(r.sender))
            menu.add_command(label="Copy Systems", command=lambda r=row: self.copy_to_clipboard(", ".join(r.systems)))
            menu.add_command(label="Copy Ships / Assets", command=lambda r=row: self.copy_to_clipboard(", ".join(r.assets)))
            menu.add_command(label="Copy URLs", command=lambda r=row: self.copy_to_clipboard("\n".join(self.http_links_for_row(r))))
        else:
            menu.add_command(label="Copy Selected Text", command=self.copy_selected_text)
            menu.add_command(label="Copy Visible Feed", command=self.copy_visible_feed)
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
            self.tag_term(term, "system", region_start, region_end)
        for term in sorted(unique(assets), key=len, reverse=True):
            if term.lower() == "ess":
                self.tag_term(term, "ess", region_start, region_end)
            else:
                self.tag_term(term, "asset", region_start, region_end)
        # Defensive: highlight literal ESS even if it was not classified as an asset.
        self.tag_term("ESS", "ess", region_start, region_end)

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

    def append_row(self, row: Row):
        self.rows.append(row)
        self.ensure_row_channel_tab(row.channel)
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[-MAX_ROWS:]
        if self.row_visible(row):
            self._render_row(row)
        else:
            self.mark_unread_for_row(row)

    def display_free_translation(self, row: Row, display_text: str) -> str:
        if not bool(self.translate_chinese_text.get()):
            return ""
        direction = self.translation_direction.get()
        if direction == "zh-en":
            if row.free_translation:
                return row.free_translation
            return translate_free_text(display_text, row.systems, row.assets, row.localized, row.counts, row.links, "zh-en")
        if direction == "en-zh":
            return translate_free_text(display_text, row.systems, row.assets, row.localized, row.counts, row.links, "en-zh")
        return ""

    def _render_row(self, row: Row):
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
                elif isinstance(item, tuple) and item[0] == "update_available":
                    self.status_label.configure(text=f"Update available: {item[1]}")
                    self.show_update_available(item[1], item[2])
                elif isinstance(item, tuple) and item[0] == "update_current":
                    self.status_label.configure(text=f"Signal Bridge is current ({item[1]})")
                    self.messagebox.showinfo("Signal Bridge Updates", f"Signal Bridge is up to date.\n\nCurrent version: v{APP_VERSION}\nLatest release: {item[1]}")
                elif isinstance(item, tuple) and item[0] == "update_failed":
                    self.status_label.configure(text="Update check failed; see logs")
                    self.messagebox.showwarning("Signal Bridge Updates", "Could not check for updates. This can happen if the GitHub repo is private or offline.\n\nSee logs for details.")
                elif isinstance(item, Row):
                    self.append_row(item)
        except queue.Empty:
            pass
        self.root.after(150, self.drain_queue)

    def run(self):
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

