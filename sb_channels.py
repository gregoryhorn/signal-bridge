"""Chat channel discovery, normalize, and catalog merge (no Tk)."""

from __future__ import annotations

import re
from pathlib import Path


def channel_from_filename(path: Path) -> str:
    return path.stem.split("_", 1)[0] or path.stem


def channel_sort_key(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip()).casefold()


def normalize_channel_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip())


def discover_channel_metadata(chatlog_dir: Path, limit_files: int = 500) -> dict[str, dict]:
    """Return recent chatlog-backed channel metadata keyed by display channel name."""
    chatlog_dir = Path(chatlog_dir)
    if not chatlog_dir.exists():
        return {}
    channels: dict[str, dict] = {}
    try:
        files = sorted(chatlog_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime_ns, reverse=True)[:limit_files]
    except Exception:
        return {}
    for path in files:
        try:
            channel = normalize_channel_name(channel_from_filename(path))
            if not channel:
                continue
            st = path.stat()
            info = channels.setdefault(
                channel,
                {"channel": channel, "last_seen_ns": 0, "files": 0, "latest_file": ""},
            )
            info["files"] = int(info.get("files", 0)) + 1
            if st.st_mtime_ns >= int(info.get("last_seen_ns", 0)):
                info["last_seen_ns"] = st.st_mtime_ns
                info["latest_file"] = path.name
        except OSError:
            continue
    return channels


def discover_channels(chatlog_dir: Path, limit_files: int = 500) -> list[str]:
    channels = discover_channel_metadata(chatlog_dir, limit_files)
    return [
        name
        for name, _ in sorted(channels.items(), key=lambda kv: kv[1].get("last_seen_ns", 0), reverse=True)
    ]


def default_channels(chatlog_dir: Path, persisted: set[str] | list[str] | None = None) -> set[str]:
    if persisted:
        return {normalize_channel_name(c) for c in persisted if normalize_channel_name(c)}
    channels = discover_channels(chatlog_dir)
    return set(channels[:1])


def build_channel_catalog(
    *,
    chatlog_dir: Path,
    active_channels: set[str],
    hidden_tab_ids: set[str],
    tab_order: list[str],
    discovered: dict[str, dict] | None = None,
    all_channels_tab: str = "__ALL_CHANNELS__",
) -> dict[str, dict]:
    """Merge discovered files with persisted active/hidden channels and label status."""
    discovered = discovered if discovered is not None else discover_channel_metadata(chatlog_dir)
    catalog: dict[str, dict] = {name: dict(info) for name, info in discovered.items()}
    active = {normalize_channel_name(c) for c in active_channels if normalize_channel_name(c)}
    hidden = {normalize_channel_name(c) for c in hidden_tab_ids if normalize_channel_name(c) and c != all_channels_tab}
    # Keep All-tab id out of channel catalog keys.
    hidden = {h for h in hidden if h != all_channels_tab}
    persisted = set(active) | {normalize_channel_name(c) for c in tab_order if c != all_channels_tab and normalize_channel_name(c)} | hidden
    for channel in persisted:
        if not channel:
            continue
        catalog.setdefault(channel, {"channel": channel, "last_seen_ns": 0, "files": 0, "latest_file": ""})
    for channel, info in catalog.items():
        is_active = channel in active
        is_hidden = channel in hidden_tab_ids or channel in hidden
        discovered_now = channel in discovered
        if is_active and discovered_now:
            status = "tracking"
        elif is_active:
            status = "tracking, waiting for log"
        elif is_hidden:
            status = "hidden"
        elif discovered_now:
            status = "discovered"
        else:
            status = "saved, missing log"
        info["active"] = is_active
        info["hidden"] = is_hidden
        info["discovered"] = discovered_now
        info["status"] = status
    return catalog


def catalog_summary(catalog: dict[str, dict]) -> dict:
    discovered = sum(1 for info in catalog.values() if info.get("discovered"))
    tracking = sum(1 for info in catalog.values() if info.get("active"))
    waiting = sum(1 for info in catalog.values() if info.get("active") and not info.get("discovered"))
    hidden = sum(1 for info in catalog.values() if info.get("hidden"))
    missing = sum(1 for info in catalog.values() if not info.get("discovered") and not info.get("active"))
    return {
        "discovered": discovered,
        "tracking": tracking,
        "waiting": waiting,
        "hidden": hidden,
        "saved_missing_log": missing,
        "total": len(catalog),
    }
