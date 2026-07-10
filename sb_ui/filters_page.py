"""Settings page body for feed filters and spam hygiene (Tk widgets only)."""

from __future__ import annotations

from sb_ui import components as sb_components
from sb_ui import theme as sb_theme


def render_filters_page(
    body,
    *,
    tk,
    filters_var_list,
    spam_vars,
    on_add_keyword,
    on_add_sender,
    on_remove_selected,
    on_reload_list,
    spam_spin_vars=None,
):
    """Build Filters / Feed Hygiene page.

    spam_vars: enabled, local_only, ascii (BooleanVar)
    spam_spin_vars: optional dict with max_per_min, repeat_window, repeat_max (IntVar)
    """
    card = sb_components.card(
        body,
        "Feed filters",
        "Hide messages by keyword or sender. Filters apply to the live feed only and persist across restarts.",
    )
    list_frame = tk.Frame(card, bg=sb_theme.COLORS["bg_panel"])
    list_frame.pack(fill="both", expand=True, pady=6)
    lb = tk.Listbox(list_frame, height=10, activestyle="none", **sb_theme.listbox_kw())
    lb.pack(side="left", fill="both", expand=True)
    scroll = tk.Scrollbar(list_frame, command=lb.yview)
    scroll.pack(side="right", fill="y")
    lb.configure(yscrollcommand=scroll.set)

    def reload():
        lb.delete(0, "end")
        for line in on_reload_list():
            lb.insert("end", line)

    actions = tk.Frame(card, bg=sb_theme.COLORS["bg_panel"])
    actions.pack(fill="x", pady=4)
    sb_components.action_button(actions, "Add keyword…", command=lambda: (on_add_keyword(), reload())).pack(
        side="left", padx=(0, 6)
    )
    sb_components.action_button(actions, "Add sender…", command=lambda: (on_add_sender(), reload())).pack(
        side="left", padx=(0, 6)
    )
    sb_components.action_button(
        actions, "Remove selected", command=lambda: (on_remove_selected(lb.curselection()), reload())
    ).pack(side="left")
    sb_components.info_label(
        card,
        "Tip: Use Apply in the footer after changing spam controls. Keyword/sender changes save immediately.",
        muted=True,
    )

    spam = sb_components.card(
        body,
        "Local spam controls",
        "Rate-limit noisy Local channels and optional ASCII-art bursts. Intel lines with systems are not suppressed as art.",
    )
    sb_components.check(spam, "Enable spam controls", spam_vars["enabled"])
    sb_components.check(spam, "Apply only to Local-like channels", spam_vars["local_only"])
    sb_components.check(spam, "Filter ASCII-art / symbol spam", spam_vars["ascii"])
    if spam_spin_vars:
        sb_components.labeled_spinbox(
            spam,
            "Max messages per channel / minute:",
            spam_spin_vars["max_per_min"],
            from_=5,
            to=200,
        )
        sb_components.labeled_spinbox(
            spam,
            "Repeat-sender window (seconds):",
            spam_spin_vars["repeat_window"],
            from_=2,
            to=120,
        )
        sb_components.labeled_spinbox(
            spam,
            "Repeat-sender max in window:",
            spam_spin_vars["repeat_max"],
            from_=1,
            to=50,
        )

    reload()
    return lb
