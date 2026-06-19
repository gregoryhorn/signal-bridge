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
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

APP_NAME = "Signal Bridge"
APP_VERSION = "0.1"
DONATION_TEXT = "If you like this app and want further development, donate me some ISK in game | Mizz Betty"
ALL_CHANNELS_TAB = "__ALL_CHANNELS__"
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
USER_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_DIR = USER_DIR / "config"
CACHE_DIR = USER_DIR / "cache"
MODEL_DIR = USER_DIR / "models" / "argos"
LOG_DIR = USER_DIR / "logs"
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

LIVE_INLINE = re.compile(r"^\[\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s*\]\s*(.+?)\s*(?:>|:)\s*(.+)$", re.I)
HEADER_CHANNEL = re.compile(r"^Channel Name:\s*(.+)$", re.I)
SYSTEM_RE = re.compile(r"\b[A-Z0-9]{1,6}-[A-Z0-9]{1,4}\b")
LINK_RE = re.compile(r"https?://\S+|www\.\S+|dscan\.info/\S+", re.I)
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
        self.root.attributes("-topmost", bool(self.always_on_top.get()))
        self.active_channels: set[str] = default_channels()
        self.visible_channel: str | None = sorted(self.active_channels)[0] if self.active_channels else None
        self.channel_tab_buttons: dict[str, object] = {}
        self.queue: queue.Queue = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.monitor: MonitorThread | None = None
        self.row_count = 0
        self.rows: list[Row] = []
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
        channels_menu.add_command(label="Close All Active Channels", command=self.close_selected_channels)
        channels_menu.add_command(label="Refresh Channel List", command=self.refresh_channel_status)
        menubar.add_cascade(label="Channels", menu=channels_menu)
        settings_menu = tk.Menu(menubar, tearoff=False, bg="#111821", fg="#d7dde5")
        settings_menu.add_command(label="Choose Chatlog Folder...", command=self.choose_chatlog_folder)
        settings_menu.add_command(label="Choose Translation DB...", command=self.choose_db_file)
        settings_menu.add_separator()
        settings_menu.add_command(label="Install Argos Offline Fallback", command=self.install_argos_models)
        settings_menu.add_command(label="Open App Folder", command=self.open_app_folder)
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
        self.tab_bar = tk.Frame(self.root, bg="#0b0f14", padx=6, pady=4)
        self.tab_bar.pack(fill="x")
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
        self.text.configure(state="disabled")

    def update_channel_tabs(self):
        tk = self.tk
        # Lightweight custom tab bar: each active channel gets a tab button plus an X close button.
        for child in self.tab_bar.winfo_children():
            child.destroy()
        self.channel_tab_buttons = {}
        if not self.active_channels:
            self.visible_channel = None
            label = self.tk.Label(self.tab_bar, text="No active channels - use Channels > Choose / Open Channels...", bg="#0b0f14", fg="#8b98a8", font=("Segoe UI", 9))
            label.pack(side="left", padx=4)
            return
        if self.visible_channel not in self.active_channels:
            self.visible_channel = sorted(self.active_channels)[0]
        if len(self.active_channels) > 1:
            all_frame = tk.Frame(self.tab_bar, bg=("#24384f" if self.visible_channel == ALL_CHANNELS_TAB else "#111821"), bd=1, relief="solid")
            all_frame.pack(side="left", padx=(0, 6), pady=2)
            all_btn = tk.Button(all_frame, text="All Channels", command=self.select_all_channels_tab, bg=all_frame["bg"], fg="#d7dde5", relief="flat", padx=8, pady=2, font=("Segoe UI", 9, "bold"))
            all_btn.pack(side="left")

        for channel in sorted(self.active_channels):
            active = channel == self.visible_channel
            tab = self.tk.Frame(self.tab_bar, bg="#23405c" if active else "#111821", bd=1, relief="solid")
            tab.pack(side="left", padx=3, pady=1)
            btn = self.tk.Button(
                tab,
                text=channel,
                command=lambda c=channel: self.select_channel_tab(c),
                bg="#23405c" if active else "#111821",
                fg="#ffffff" if active else "#c9d2dc",
                activebackground="#2e557a",
                activeforeground="#ffffff",
                relief="flat",
                padx=8,
                pady=2,
                font=("Segoe UI", 9, "bold" if active else "normal"),
            )
            btn.pack(side="left")
            close = self.tk.Button(
                tab,
                text="x",
                command=lambda c=channel: self.close_channel(c),
                bg="#23405c" if active else "#111821",
                fg="#ff8a8f",
                activebackground="#5c1f28",
                activeforeground="#ffffff",
                relief="flat",
                padx=5,
                pady=2,
                font=("Segoe UI", 9, "bold"),
            )
            close.pack(side="left")
            self.channel_tab_buttons[channel] = tab

    def select_channel_tab(self, channel: str):
        if channel not in self.active_channels:
            return
        self.visible_channel = channel
        self.title_label.configure(text=f"{APP_NAME} v{APP_VERSION}")
        self.update_channel_tabs()
        self.redraw_feed()

    def close_channel(self, channel: str):
        if channel not in self.active_channels:
            return
        remaining = set(self.active_channels)
        remaining.discard(channel)
        self.set_channels(remaining)

    def channel_title(self) -> str:
        if not self.active_channels:
            return "No channels selected"
        if self.visible_channel:
            extra = len(self.active_channels) - 1
            return self.visible_channel if extra <= 0 else f"{self.visible_channel}  (+{extra} active)"
        names = sorted(self.active_channels)
        if len(names) <= 3:
            return " | ".join(names)
        return " | ".join(names[:3]) + f" +{len(names)-3}"

    def refresh_channel_status(self):
        channels = discover_channels()
        self.set_status(f"Found {len(channels)} chat channels. Active: {len(self.active_channels)}")

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
            self.set_channels(selected)
            win.destroy()
        def select_all():
            lb.selection_set(0, "end")
        def select_none():
            lb.selection_clear(0, "end")
        tk.Button(btns, text="Apply", command=apply_selection).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="All", command=select_all).pack(side="left", padx=6)
        tk.Button(btns, text="None", command=select_none).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")

    def set_channels(self, channels: set[str]):
        self.active_channels = set(channels)
        if self.visible_channel != ALL_CHANNELS_TAB and self.visible_channel not in self.active_channels:
            self.visible_channel = sorted(self.active_channels)[0] if self.active_channels else None
        if self.visible_channel == ALL_CHANNELS_TAB and not self.active_channels:
            self.visible_channel = None
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
        self.set_channels(set())

    def is_all_channels_view(self) -> bool:
        return self.visible_channel == ALL_CHANNELS_TAB

    def select_all_channels_tab(self):
        if not self.active_channels:
            return
        self.visible_channel = ALL_CHANNELS_TAB
        self.update_channel_tabs()
        self.redraw_feed()

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
        self.set_status("Starting monitor...")

    def stop_monitor(self):
        if self.stop_event:
            self.stop_event.set()
        self.set_status("Stopped")

    def clear_feed(self):
        self.rows.clear()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.row_count = 0

    def open_folder(self):
        import os
        if CHATLOG_DIR.exists():
            os.startfile(str(CHATLOG_DIR))
        else:
            self.set_status("Chatlog folder does not exist; use Settings > Choose Chatlog Folder...")

    def show_about(self):
        self.messagebox.showinfo(
            "About Signal Bridge",
            f"Signal Bridge v{APP_VERSION}\n"
            "EVE Online live chat intel translator\n\n"
            "Highlights:\n"
            "- Systems: yellow\n"
            "- Ships/assets: red\n"
            "- ESS: light blue\n"
            "- Active channels appear as tabs with x close buttons\n"
            "- Configurable feed font and timestamp display\n\n"
            "Translation:\n"
            "- EVE DB localization\n"
            "- Google free auto-detect to English\n"
            "- Argos fallback when available"
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
            f"Config: {CONFIG_PATH}\n"
            f"App folder: {USER_DIR}\n"
            f"Font: {self.font_family.get()} {int(self.font_size.get())}\n"
            f"Show timestamps: {bool(self.show_timestamps.get())}\n"
            "Free MT: Google primary, Argos fallback\n"
            "Directions: Auto -> EN / EN -> CN"
        )


    def on_exit(self):
        self.persist_settings()
        self.stop_monitor()
        self.root.after(100, self.root.destroy)

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
        old_rows = list(self.rows[-MAX_ROWS:])
        self.row_count = 0
        for row in old_rows:
            if self.visible_channel == ALL_CHANNELS_TAB or self.visible_channel is None or row.channel == self.visible_channel:
                self._render_row(row)

    def append_row(self, row: Row):
        self.rows.append(row)
        if row.channel in self.active_channels and row.channel not in self.channel_tab_buttons:
            self.update_channel_tabs()
        if self.visible_channel is None and row.channel in self.active_channels:
            self.visible_channel = row.channel
            self.title_label.configure(text=f"{APP_NAME} v{APP_VERSION}")
            self.update_channel_tabs()
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[-MAX_ROWS:]
        if self.visible_channel == ALL_CHANNELS_TAB or self.visible_channel is None or row.channel == self.visible_channel:
            self._render_row(row)

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
        ts = row.received_at.split()[-1]
        display_text = self.localized_display_text(row)
        free_text = self.display_free_translation(row, display_text)
        translated_only = bool(self.translated_only.get())
        if bool(self.show_timestamps.get()):
            self.text.insert("end", f"[{ts}] ", "time")
        if bool(self.show_channel_names.get()) or self.visible_channel == ALL_CHANNELS_TAB:
            self.text.insert("end", f"[{row.channel}] ", "muted")
        self.text.insert("end", f"{row.sender} > ", "sender")
        if translated_only:
            # Main row displays English: DB-localized EVE terms plus optional free Chinese sentence translation.
            self.insert_tagged_text((free_text or display_text) + "\n", row.systems, row.assets)
        else:
            # Review mode: show original first, then translated line only when actual DB/free translation changed text.
            self.insert_tagged_text(row.text + "\n", row.systems, row.assets + [x.get("original", "") for x in row.localized])
            if free_text and free_text != row.text:
                self.text.insert("end", "    translated: ", "muted")
                self.insert_tagged_text(free_text + "\n", row.systems, row.assets)
            elif display_text != row.text:
                self.text.insert("end", "    translated: ", "muted")
                self.insert_tagged_text(display_text + "\n", row.systems, row.assets)
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
                elif isinstance(item, Row):
                    self.append_row(item)
        except queue.Empty:
            pass
        self.root.after(150, self.drain_queue)

    def run(self):
        self.start_monitor()
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test(args.limit)
    SignalBridgeGui().run()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

