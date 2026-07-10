"""Settings > Pilot Intel — first-class product page (not only Add-ons plumbing)."""

from __future__ import annotations

from typing import Any, Callable

from sb_ui import components as sb_components
from sb_ui import theme as sb_theme


def render_pilot_intel_page(
    body,
    app: Any,
    *,
    open_addons: Callable[[], None] | None = None,
    open_help: Callable[[], None] | None = None,
    open_recognition: Callable[[], None] | None = None,
) -> None:
    """Render Pilot Intel status and shortcuts into a Settings body frame."""
    import tkinter as tk

    c = sb_components.card(body, "Pilot Intel")
    sb_components.info_label(
        c,
        "Pilot Intel is a core feature: open pilots from the feed, view local history, "
        "flags, and zKill (cache-first). Intel History storage is bundled by default.",
    )

    # Runtime status
    status_card = sb_components.card(body, "Status")
    try:
        label = app.intel_history_status_label()
    except Exception:
        label = "unavailable"
    try:
        health = getattr(app, "intel_history_last_health", {}) or {}
    except Exception:
        health = {}
    sb_components.info_label(status_card, f"Intel History: {label}")
    if health:
        bits = []
        for key in ("pilots", "sightings", "queue_size", "last_sighting", "errors", "last_error"):
            if key in health and health.get(key) not in (None, ""):
                bits.append(f"{key}={health.get(key)}")
        if bits:
            sb_components.info_label(status_card, " · ".join(bits[:6]), muted=True)

    # How to use
    how = sb_components.card(body, "How to use")
    sb_components.info_label(
        how,
        "1. Enable ESI character recognition (Settings > ESI) for pilot names in chat.\n"
        "2. Right-click a highlighted pilot in the feed → Open Pilot Info.\n"
        "3. Use quick flags: Watchlist, High Threat, Do Not Track.\n"
        "4. Sync zKill from the card when you need 30-day kill/loss context.",
    )

    # Shortcuts
    actions = sb_components.card(body, "Shortcuts")
    row = sb_components.action_row(actions)
    if open_help:
        sb_components.action_button(row, "Help: Pilot Info", open_help).pack(side="left", padx=(0, 6))
    if open_recognition:
        sb_components.action_button(row, "Recognition Rules", open_recognition).pack(side="left", padx=(0, 6))
    if open_addons:
        sb_components.action_button(row, "Add-ons (package)", open_addons).pack(side="left", padx=(0, 6))

    note = sb_components.card(body, "Data")
    sb_components.info_label(
        note,
        "Local sightings and flags stay on this machine under the app data folder. "
        "Uninstalling add-on code does not delete pilot SQLite data by default.",
        muted=True,
    )
