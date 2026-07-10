"""Pilot Intel card — compact tactical layout (Void Tactical).

Opened from feed right-click / Pilot Intel entry points. Local history + cached zKill only.
"""

from __future__ import annotations

import time
import webbrowser
from typing import Any, Callable

import sb_zkill
from sb_pilot import (
    clean_value,
    count_label,
    filtered_top_ships,
    fmt_isk,
    is_pilot_signal_term,
    latest_sighting,
    normalized_ship_status,
    pilot_info_term_kind,
    profile_active_flags,
    signal_counts,
    zkill_priority,
)
from sb_ui import components as sb_components
from sb_ui import theme as sb_theme
from sb_ui import windows as sb_windows
from sb_ui.pilot.sections import chip, section


def open_pilot_card(app: Any, profile: dict) -> None:
    """Build and show the redesigned Pilot Info window."""
    import tkinter as tk

    from sb_diagnostics import record_event

    profile = dict(profile or {})
    pilot = profile.get("pilot") or {}
    pilot_id = int(pilot.get("pilot_id") or 0)
    name = pilot.get("name") or "Unknown Pilot"
    opened = time.time()

    win = tk.Toplevel(app.root)
    app.polish_window(
        win, app.root, width=480, height=420, minsize=(400, 320),
        title=f"Pilot Info — {name}", placement="beside_parent",
    )

    header = tk.Frame(win, bg=sb_theme.COLORS["bg_panel"], padx=10, pady=8)
    header.pack(fill="x")
    header_right = tk.Frame(header, bg=sb_theme.COLORS["bg_panel"])
    header_right.pack(side="right", anchor="ne")
    header_left = tk.Frame(header, bg=sb_theme.COLORS["bg_panel"])
    header_left.pack(side="left", fill="x", expand=True)

    footer = tk.Frame(win, bg=sb_theme.COLORS["bg_panel"], padx=8, pady=6)
    footer.pack(fill="x", side="bottom")

    scroll_outer = tk.Frame(win, bg=sb_theme.COLORS["bg"])
    scroll_outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(scroll_outer, bg=sb_theme.COLORS["bg"], highlightthickness=0, bd=0)
    vscroll = tk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    body = tk.Frame(canvas, bg=sb_theme.COLORS["bg"], padx=8, pady=6)
    body_window = canvas.create_window((0, 0), window=body, anchor="nw")

    def _sync_scroll(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        try:
            canvas.itemconfigure(body_window, width=event.width)
        except Exception:
            pass

    def _update_scrollbar(_event=None):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
            bbox = canvas.bbox("all")
            needs = bool(bbox and (bbox[3] - bbox[1]) > canvas.winfo_height() + 2)
            mapped = bool(vscroll.winfo_ismapped())
            if needs and not mapped:
                vscroll.pack(side="right", fill="y")
            elif not needs and mapped:
                vscroll.pack_forget()
        except Exception:
            pass

    def _on_mousewheel(event):
        try:
            bbox = canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > canvas.winfo_height() + 2:
                delta = -1 * int((event.delta / 120) if getattr(event, "delta", 0) else 0)
                canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    body.bind("<Configure>", lambda e: (_sync_scroll(e), _update_scrollbar(e)))
    canvas.bind("<Configure>", lambda e: (_sync_width(e), _update_scrollbar(e)))
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _unbind_mousewheel_once(event):
        try:
            if event.widget is win:
                canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    win.bind("<Destroy>", _unbind_mousewheel_once)

    state = {"view": "summary"}  # summary | sightings | flags

    def clear_body():
        for child in body.winfo_children():
            child.destroy()

    def clear_header():
        for child in header_left.winfo_children():
            child.destroy()
        for child in header_right.winfo_children():
            child.destroy()

    def clear_footer():
        for child in footer.winfo_children():
            child.destroy()

    def fit_window():
        try:
            win.update_idletasks()
            canvas.configure(height=max(120, body.winfo_reqheight()))
            w, h = sb_windows.fit_to_content(
                win, app.root, min_size=(400, 320), max_size=(560, 680), pad=(20, 20),
                preserve_position=True,
            )
            record_event("pilot_card_layout_autosized", pilot_id=pilot_id, height=h, width=w)
        except Exception:
            pass

    def render_header(show_back: bool = False, back_cmd: Callable | None = None):
        clear_header()
        zks = app.get_zkill_summary(pilot_id)
        last = latest_sighting(profile)
        ship, status = normalized_ship_status(last)
        pri, pri_text, _notes = zkill_priority(zks, ship)

        # Threat ribbon
        if zks.get("status") != "synced":
            ribbon, rfg = "NOT SYNCED", sb_theme.COLORS["fg_muted"]
            rbg = sb_theme.COLORS["bg_input"]
        elif pri == "HIGH":
            ribbon, rfg, rbg = f"HIGH · {pri_text}", sb_theme.COLORS["error"], "#2a1414"
        elif pri == "MED":
            ribbon, rfg, rbg = f"MED · {pri_text}", sb_theme.COLORS["warning"], "#2a2410"
        elif pri == "QUIET":
            ribbon, rfg, rbg = "QUIET", sb_theme.COLORS["fg_muted"], sb_theme.COLORS["bg_input"]
        else:
            ribbon, rfg, rbg = pri, sb_theme.COLORS["fg"], sb_theme.COLORS["bg_input"]

        top = tk.Frame(header_left, bg=sb_theme.COLORS["bg_panel"])
        top.pack(fill="x")
        tk.Label(
            top, text=name, bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_bright"],
            font=sb_theme.font(14, bold=True), wraplength=320, justify="left", anchor="w",
        ).pack(side="left", anchor="w")
        tk.Label(
            top, text=ribbon, bg=rbg, fg=rfg, padx=8, pady=2,
            font=sb_theme.font(8, bold=True),
        ).pack(side="right", padx=(8, 0))

        corp = clean_value(pilot.get("corp_name"), "Unknown corporation")
        alliance = clean_value(pilot.get("alliance_name"), "No alliance")
        tk.Label(
            header_left, text=f"{corp}  ·  {alliance}",
            bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_muted"],
            font=sb_theme.font(9), wraplength=420, justify="left", anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        if last:
            bits = [
                app.friendly_datetime(last.get("timestamp")).replace("Today ", ""),
                clean_value(last.get("system_name")),
                ship if ship != "Unknown" else "",
                status or "",
            ]
            line = " · ".join(b for b in bits if b)
            tk.Label(
                header_left, text=line,
                bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["accent_line"],
                font=sb_theme.font(9), wraplength=420, justify="left", anchor="w",
            ).pack(anchor="w", pady=(3, 0))
        else:
            reports = int(profile.get("report_count") or 0)
            msg = "No local sightings yet" if reports == 0 else f"{reports} report(s)"
            tk.Label(
                header_left, text=msg,
                bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_muted"],
                font=sb_theme.font(9),
            ).pack(anchor="w", pady=(3, 0))

        if pilot_id:
            id_row = tk.Frame(header_left, bg=sb_theme.COLORS["bg_panel"])
            id_row.pack(anchor="w", pady=(2, 0))
            tk.Label(
                id_row, text=f"ID {pilot_id}",
                bg=sb_theme.COLORS["bg_panel"], fg=sb_theme.COLORS["fg_muted"],
                font=sb_theme.font(8),
            ).pack(side="left")

        if show_back and back_cmd:
            tk.Button(
                header_right, text="← Summary", command=back_cmd,
                **sb_theme.btn_secondary_kw(), padx=8, pady=2,
            ).pack(anchor="ne")

    def render_snapshot():
        """One strip: flags + hot systems/ships/signals — omit empty groups."""
        strip = tk.Frame(body, bg=sb_theme.COLORS["bg"])
        strip.pack(fill="x", pady=(0, 6))

        def group(label: str, items: list[tuple[str, str]]):
            if not items:
                return
            row = tk.Frame(strip, bg=sb_theme.COLORS["bg"])
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=label, bg=sb_theme.COLORS["bg"], fg=sb_theme.COLORS["fg_muted"],
                font=sb_theme.font(8), width=7, anchor="w",
            ).pack(side="left")
            chips = tk.Frame(row, bg=sb_theme.COLORS["bg"])
            chips.pack(side="left", fill="x")
            for text, kind in items:
                chip(chips, text, kind)

        flags = profile_active_flags(profile)
        if flags:
            group("Flags", [
                (((f.get("icon") or "") + " " + (f.get("label") or f.get("flag") or "")).strip(), "flag")
                for f in flags[:5]
            ])

        systems = [
            (f"{x.get('name')} {count_label(x.get('reports') or x.get('sightings') or 1)}".strip(), "system")
            for x in (profile.get("top_systems") or [])[:3]
            if x.get("name")
        ]
        group("Systems", systems)

        ships = [
            (f"{x.get('name')} {count_label(x.get('reports') or x.get('sightings') or 1)}".strip(), "ship")
            for x in filtered_top_ships(profile)[:3]
            if x.get("name")
        ]
        group("Ships", ships)

        signals = [
            (f"{k} {count_label(n)}".strip(), "signal")
            for k, n in list(signal_counts(profile).items())[:3]
        ]
        group("Signals", signals)

    def render_local_timeline(limit: int = 4):
        recent = profile.get("recent_sightings", []) or []
        if not recent:
            return
        box = section(body, "Local")
        for r0 in recent[:limit]:
            tm = app.friendly_datetime(r0.get("timestamp")).replace("Today ", "")
            sysname = clean_value(r0.get("system_name"), "—")
            ship, status = normalized_ship_status(r0)
            ship_s = ship if ship != "Unknown" else "—"
            cnt = count_label(r0.get("duplicate_count", 1))
            tail = f"  {status}" if status else ""
            line = f"{tm}   {sysname}   {ship_s}{tail}  {cnt}".rstrip()
            tk.Label(
                box, text=line, bg=box.cget("bg"), fg=sb_theme.COLORS["fg"],
                font=sb_theme.font(9), anchor="w", justify="left",
            ).pack(anchor="w")

    def render_zkill():
        box = section(body, "zKill")
        zks = app.get_zkill_summary(pilot_id)
        status = zks.get("status") or "not_synced"

        if status == "syncing":
            tk.Label(
                box, text="Syncing in background…",
                bg=box.cget("bg"), fg=sb_theme.COLORS["accent_line"], font=sb_theme.font(9),
            ).pack(anchor="w")
            return

        if status == "failed":
            tk.Label(
                box, text=f"Sync failed: {zks.get('last_error', 'unknown')}",
                bg=box.cget("bg"), fg=sb_theme.COLORS["error"], font=sb_theme.font(9),
                wraplength=440, justify="left",
            ).pack(anchor="w")
            sb_components.action_button(box, "Retry Sync", sync_zkill).pack(anchor="w", pady=(6, 0))
            return

        if status != "synced":
            tk.Label(
                box, text="No cached zKill summary. Sync for 30-day kills/losses (local cache only).",
                bg=box.cget("bg"), fg=sb_theme.COLORS["fg_muted"], font=sb_theme.font(9),
                wraplength=440, justify="left",
            ).pack(anchor="w")
            sb_components.primary_button(box, "Sync zKill", sync_zkill).pack(anchor="w", pady=(8, 0))
            return

        ship, _st = normalized_ship_status(latest_sighting(profile))
        pri, pri_text, pri_notes = zkill_priority(zks, ship)
        pri_fg = sb_theme.COLORS["error"] if pri == "HIGH" else (
            sb_theme.COLORS["warning"] if pri == "MED" else sb_theme.COLORS["fg"]
        )
        stats = (
            f"{pri} · {pri_text}   ·   "
            f"K {zks.get('recent_kills_30d', 0)} / L {zks.get('recent_losses_30d', 0)}   ·   "
            f"ISK {fmt_isk(zks.get('isk_destroyed_30d'))} / {fmt_isk(zks.get('isk_lost_30d'))}"
        )
        tk.Label(
            box, text=stats, bg=box.cget("bg"), fg=pri_fg,
            font=sb_theme.font(9, bold=True), wraplength=440, justify="left",
        ).pack(anchor="w")
        if pri_notes:
            tk.Label(
                box, text=" · ".join(pri_notes[:3]),
                bg=box.cget("bg"), fg=sb_theme.COLORS["fg_muted"], font=sb_theme.font(8),
                wraplength=440, justify="left",
            ).pack(anchor="w")

        events = zks.get("recent_events") or []
        recent_kills = zks.get("recent_kills")
        if recent_kills is None:
            recent_kills = sb_zkill.rank_kills(events, 3)
        else:
            recent_kills = list(recent_kills)[:3]
        recent_losses = zks.get("recent_losses")
        if recent_losses is None:
            recent_losses = sb_zkill.pick_losses(events, 3)
        else:
            recent_losses = list(recent_losses)[:3]

        def event_row(parent, ev, accent):
            row = tk.Frame(parent, bg=parent.cget("bg"))
            row.pack(fill="x", anchor="w")
            tm = app.friendly_datetime(ev.get("time")).replace("Today ", "")
            gang = sb_zkill.gang_label(int(ev.get("participants") or 0))
            text = f"{tm}  {clean_value(ev.get('ship'), '—')}  {fmt_isk(ev.get('value'))} ISK  [{gang}]"
            tk.Label(row, text=text, bg=row.cget("bg"), fg=accent, font=sb_theme.font(8)).pack(side="left")
            km_id = int(ev.get("killmail_id") or 0)
            if km_id:
                link = tk.Label(row, text="↗", bg=row.cget("bg"), fg=sb_theme.COLORS["accent_line"], cursor="hand2", font=sb_theme.font(9, bold=True))
                link.pack(side="left", padx=(6, 0))
                link.bind("<Button-1>", lambda _e, k=km_id: webbrowser.open(f"https://zkillboard.com/kill/{k}/"))

        tk.Label(
            box, text="Kills (small gang first)", bg=box.cget("bg"),
            fg=sb_theme.COLORS["success"], font=sb_theme.font(8, bold=True),
        ).pack(anchor="w", pady=(5, 0))
        if recent_kills:
            for ev in recent_kills:
                event_row(box, ev, sb_theme.COLORS["fg"])
        else:
            tk.Label(box, text="No recent kills", bg=box.cget("bg"), fg=sb_theme.COLORS["fg_muted"], font=sb_theme.font(8)).pack(anchor="w")

        tk.Label(
            box, text="Losses", bg=box.cget("bg"),
            fg=sb_theme.COLORS["error"], font=sb_theme.font(8, bold=True),
        ).pack(anchor="w", pady=(4, 0))
        if recent_losses:
            for ev in recent_losses:
                event_row(box, ev, sb_theme.COLORS["fg"])
        else:
            tk.Label(box, text="No recent losses", bg=box.cget("bg"), fg=sb_theme.COLORS["fg_muted"], font=sb_theme.font(8)).pack(anchor="w")

    def render_footer(view: str):
        clear_footer()
        zks = app.get_zkill_summary(pilot_id)
        synced = zks.get("status") == "synced"

        def open_more():
            menu = tk.Menu(
                footer, tearoff=False, bg=sb_theme.COLORS["bg_chrome"],
                fg=sb_theme.COLORS["fg"], activebackground=sb_theme.COLORS["accent_active"],
                activeforeground=sb_theme.COLORS["fg_bright"],
            )
            menu.add_command(label="Activity", command=render_sightings)
            menu.add_command(label="Copy summary", command=copy_summary)
            menu.add_separator()
            menu.add_command(label="Close", command=win.destroy)
            try:
                menu.tk_popup(footer.winfo_rootx(), footer.winfo_rooty() - 4)
            finally:
                menu.grab_release()

        if view == "summary":
            if not synced:
                sb_components.primary_button(footer, "Sync zKill", sync_zkill).pack(side="left", padx=(0, 6))
                sb_components.action_button(footer, "Open zKill", open_zkill).pack(side="left", padx=(0, 4))
            else:
                sb_components.primary_button(footer, "Open zKill", open_zkill).pack(side="left", padx=(0, 6))
                sb_components.action_button(footer, "Sync", sync_zkill).pack(side="left", padx=(0, 4))
            sb_components.action_button(footer, "Flags", render_flags).pack(side="left", padx=(0, 4))
            sb_components.action_button(footer, "More...", open_more).pack(side="left", padx=(0, 4))
            sb_components.action_button(footer, "Close", win.destroy).pack(side="right")
        else:
            sb_components.action_button(footer, "Close", win.destroy).pack(side="right")

    def render_summary():
        nonlocal profile, pilot
        state["view"] = "summary"
        clear_body()
        render_header(show_back=False)
        render_snapshot()
        render_local_timeline(4)
        render_zkill()
        render_footer("summary")
        try:
            app.diagnostics["last_pilot_card_open_ms"] = int((time.time() - opened) * 1000)
            record_event(
                "pilot_card_rendered",
                pilot_id=pilot_id,
                duration_ms=app.diagnostics["last_pilot_card_open_ms"],
                reports=profile.get("report_count", 0),
            )
        except Exception:
            pass
        fit_window()

    def render_sightings():
        state["view"] = "sightings"
        clear_body()
        render_header(show_back=True, back_cmd=render_summary)
        box = section(body, "Recent sightings")
        recent = profile.get("recent_sightings", []) or []
        if not recent:
            tk.Label(box, text="No local sightings yet.", bg=box.cget("bg"), fg=sb_theme.COLORS["fg_muted"]).pack(anchor="w")
        for r0 in recent[:25]:
            ship, status = normalized_ship_status(r0)
            tail = f"  {status}" if status else ""
            line = (
                f"{app.friendly_datetime(r0.get('timestamp'))}  "
                f"{clean_value(r0.get('system_name'))}  "
                f"{ship}{tail}{count_label(r0.get('duplicate_count', 1))}  "
                f"[{r0.get('source', 'local')}]"
            )
            tk.Label(box, text=line, bg=box.cget("bg"), fg=sb_theme.COLORS["fg"], font=sb_theme.font(9), anchor="w").pack(anchor="w")
        render_footer("sub")
        fit_window()

    def render_flags():
        state["view"] = "flags"
        clear_body()
        render_header(show_back=True, back_cmd=render_summary)
        box = section(body, "Manual flags")
        choices = [
            ("Watchlist", "★"), ("FC", "FC"), ("Scout", "Scout"), ("Hot Dropper", "🔥"),
            ("High Threat", "⚠"), ("Extreme Threat", "☠"), ("Friendly", ""), ("Do Not Track", "DNT"),
        ]
        current = {f.get("label") or f.get("flag") for f in profile_active_flags(profile) if f.get("source") == "manual"}
        vars_list = []
        for label_text, icon in choices:
            var = tk.BooleanVar(value=label_text in current)
            tk.Checkbutton(
                box, text=f"{icon} {label_text}".strip(), variable=var, **sb_theme.check_kw(),
            ).pack(anchor="w")
            # Fix check bg for nav section
            for w in box.winfo_children()[-1:]:
                try:
                    w.configure(bg=box.cget("bg"), activebackground=box.cget("bg"))
                except Exception:
                    pass
            vars_list.append((label_text, icon, var))
        notes = tk.Entry(box, **sb_theme.entry_kw())
        notes.pack(fill="x", pady=(6, 4))

        def save_flags():
            selected = [
                {"flag": label_text, "label": label_text, "icon": icon, "reason": notes.get().strip()}
                for label_text, icon, var in vars_list if var.get()
            ]
            result = app.intel_history_call("set_manual_flags", pilot_id, selected, notify=True)
            if result and result.get("ok"):
                app.set_status(f"Pilot flags saved: {name}")
                refresh_profile()
            else:
                app.messagebox.showwarning("Pilot Flags", f"Could not save flags: {result}")

        row = tk.Frame(box, bg=box.cget("bg"))
        row.pack(anchor="w", pady=(4, 0))
        sb_components.primary_button(row, "Save flags", save_flags).pack(side="left", padx=(0, 6))
        render_footer("sub")
        fit_window()

    def refresh_profile():
        nonlocal profile, pilot
        fresh = app.intel_history_call("get_pilot_profile", pilot_id=pilot_id)
        if fresh and fresh.get("found"):
            profile = fresh
            pilot = profile.get("pilot") or pilot
        render_summary()

    def copy_summary():
        text = app.intel_history_call("copyable_pilot_summary", pilot_id, notify=True)
        if text:
            app.copy_to_clipboard(text)
            app.set_status(f"Copied pilot summary: {name}")

    def open_zkill():
        webbrowser.open(f"https://zkillboard.com/character/{pilot_id}/")

    def sync_zkill():
        app.set_zkill_summary(
            pilot_id,
            {
                "status": "syncing",
                "pilot_id": pilot_id,
                "pilot_name": name,
                "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        render_summary()
        app.set_status(f"Syncing zKill: {name}")

        def done(ok, summary, pid):
            render_summary()
            app.set_status(("zKill synced" if ok else "zKill sync failed") + f": {name}")

        app.start_zkill_sync(pilot_id, name, done)

    render_summary()
