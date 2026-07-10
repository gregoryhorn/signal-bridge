"""Settings > LAN Web Viewer page."""

from __future__ import annotations

from typing import Any, Callable

from sb_ui import components as sb_components
from sb_ui import theme as sb_theme


def render_lan_page(
    body,
    app: Any,
    *,
    get_url: Callable[[], str],
    get_clients: Callable[[], int],
    on_toggle: Callable[[], None],
    on_regen_token: Callable[[], None],
    on_copy_url: Callable[[], None],
    on_apply_port: Callable[[], None],
) -> None:
    import tkinter as tk

    warn = sb_components.card(
        body,
        "Security",
        "Anyone on your LAN with the URL can read the live feed. Sharing is off by default.",
    )
    sb_components.info_label(
        warn,
        "Read-only. No remote control. No settings, tokens, or logs are exposed. "
        "Use Stop Sharing when finished.",
        muted=True,
    )

    c = sb_components.card(body, "LAN Web Viewer")
    sb_components.check(
        c,
        "Enable LAN phone viewer",
        app.lan_enabled,
        on_toggle,
    )

    port_row = tk.Frame(c, bg=sb_theme.COLORS["bg_panel"])
    port_row.pack(fill="x", pady=(8, 4))
    tk.Label(port_row, text="Port", **sb_theme.label_kw()).pack(side="left")
    tk.Spinbox(
        port_row,
        from_=1024,
        to=65535,
        textvariable=app.lan_port,
        width=8,
        bg=sb_theme.COLORS["bg_input"],
        fg=sb_theme.COLORS["fg"],
        buttonbackground=sb_theme.COLORS["bg_panel"],
        relief="flat",
    ).pack(side="left", padx=(8, 8))
    sb_components.action_button(port_row, "Apply port", on_apply_port).pack(side="left")

    url_card = sb_components.card(body, "Connection")
    url_var = getattr(app, "lan_url_var", None)
    if url_var is None:
        url_var = tk.StringVar(value=get_url() or "(disabled)")
        app.lan_url_var = url_var
    else:
        url_var.set(get_url() or "(disabled)")

    tk.Label(
        url_card,
        textvariable=url_var,
        bg=sb_theme.COLORS["bg_panel"],
        fg=sb_theme.COLORS["accent_line"],
        font=sb_theme.mono_font(9),
        wraplength=480,
        justify="left",
        anchor="w",
    ).pack(fill="x", pady=(4, 6))

    clients = get_clients()
    sb_components.info_label(url_card, f"Connected viewers: {clients}", muted=True)

    row = sb_components.action_row(url_card)
    sb_components.primary_button(row, "Copy URL", on_copy_url).pack(side="left", padx=(0, 6))
    sb_components.action_button(row, "Regenerate token", on_regen_token).pack(side="left", padx=(0, 6))

    tip = sb_components.card(body, "Phone use")
    sb_components.info_label(
        tip,
        "On the same Wi‑Fi as this PC, open the URL in a mobile browser. "
        "The feed mirrors desktop highlights and the current translation display. "
        "Use the channel filter on the phone to focus one channel.",
    )
