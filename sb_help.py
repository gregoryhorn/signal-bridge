"""Help topic manifest and loader for the in-app Help viewer.

The fixed manifest (not directory scanning) drives the nav: ordering and
titles stay stable, and a stray file cannot appear in the UI. Pure module —
no Tk, no network.
"""

from pathlib import Path

HELP_TOPICS: list[tuple[str, str]] = [
    ("Getting Started", "01-getting-started.md"),
    ("Chatlog Folder", "02-chatlog-folder.md"),
    ("Channels", "03-channels.md"),
    ("Translation", "04-translation.md"),
    ("Aliases", "05-aliases.md"),
    ("Recognition Rules", "06-recognition-rules.md"),
    ("Filters", "10-filters.md"),
    ("Pilot Info", "07-pilot-info.md"),
    ("Intel History", "08-intel-history.md"),
    ("LAN Phone Viewer", "11-lan-viewer.md"),
    ("Diagnostics", "09-diagnostics.md"),
]

FALLBACK_TEXT = (
    "# Topic unavailable\n"
    "\n"
    "This help topic is missing from this build.\n"
    "\n"
    "Read the full documentation online:\n"
    "https://github.com/gregoryhorn/signal-bridge\n"
)


def help_dir(base_dir) -> Path:
    return Path(base_dir) / "docs" / "help"


def load_topic(base_dir, filename: str) -> str:
    path = help_dir(base_dir) / filename
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_TEXT
