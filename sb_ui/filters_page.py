"""Settings page body for feed filters and spam hygiene (Tk widgets only)."""

from __future__ import annotations

from sb_ui import components as sb_components
from sb_ui import theme as sb_theme


def render_filters_page(body, *, tk, filters_var_list, spam_vars, on_add_keyword, on_add_sender, on_remove_selected, on_reload_list):
    """Build Filters / Feed Hygiene page.

    filters_var_list: listbox or tree-backed list managed by caller via on_reload_list
    spam_vars: dict of tk variables for spam controls
    """
    card = sb_components.card(body, "Feed filters")
    sb_components.info_label(
        card,
        "Hide messages by keyword or sender. Filters apply to the live feed only and persist across restarts.",
        muted=True,
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
    sb_components.action_button(actions, "Add keyword…", command=lambda: (on_add_keyword(), reload())).pack(side="left", padx=(0, 6))
    sb_components.action_button(actions, "Add sender…", command=lambda: (on_add_sender(), reload())).pack(side="left", padx=(0, 6))
    sb_components.action_button(actions, "Remove selected", command=lambda: (on_remove_selected(lb.curselection()), reload())).pack(side="left")

    spam = sb_components.card(body, "Local spam controls")
    sb_components.info_label(
        spam,
        "Rate-limit noisy Local channels and optional ASCII-art bursts. Intel lines with systems are not suppressed as art.",
        muted=True,
    )
    sb_components.check(spam, "Enable spam controls", variable=spam_vars["enabled"])
    sb_components.check(spam, "Apply only to Local-like channels", variable=spam_vars["local_only"])
    sb_components.check(spam, "Filter ASCII-art / symbol spam", variable=spam_vars["ascii"])

    reload()
    return lb
