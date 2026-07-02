"""Settings Center shell: nav rail, scrollable body, fixed footer, status line.

Page content is supplied by renderer callables with signature
(body_frame, shell); the shell owns window chrome, page switching, and
Apply/Close plumbing.
"""

import tkinter as tk
from typing import Callable

from . import theme


class SettingsShell:
    def __init__(self, root, *, pages: list[str],
                 descriptions: dict[str, str],
                 renderers: dict[str, Callable[[tk.Frame, "SettingsShell"], None]],
                 on_apply: Callable[[], bool],
                 polish: Callable, initial_page: str = "General",
                 title: str = "Signal Bridge Settings",
                 startup_status: str = ""):
        self.root = root
        self.pages = list(pages)
        self.descriptions = dict(descriptions)
        self.renderers = dict(renderers)
        self.on_apply = on_apply
        self.polish = polish
        self.initial_page = initial_page if initial_page in self.pages else self.pages[0]
        self.title_text = title
        self.startup_status = startup_status
        self.win: tk.Toplevel | None = None
        self.body: tk.Frame | None = None
        self._nav_buttons = {}
        self._status_var: tk.StringVar | None = None
        self._title: tk.Label | None = None
        self._subtitle: tk.Label | None = None
        self._body_configure = lambda _event=None: None

    def open(self) -> tk.Toplevel:
        win = tk.Toplevel(self.root)
        self.win = win
        self.polish(win, self.root, width=860, height=620, minsize=(640, 480),
                    title=self.title_text)

        nav = tk.Frame(win, bg=theme.COLORS["bg_nav"], width=190)
        nav.pack(side="left", fill="y")
        main = tk.Frame(win, bg=theme.COLORS["bg"])
        main.pack(side="left", fill="both", expand=True)

        self._title = tk.Label(main, text="", bg=theme.COLORS["bg"],
                               fg=theme.COLORS["fg_bright"],
                               font=theme.font(14, bold=True))
        self._title.pack(anchor="w", padx=18, pady=(16, 2))
        self._subtitle = tk.Label(main, text="", wraplength=610, justify="left",
                                  **theme.label_kw(muted=True))
        self._subtitle.pack(anchor="w", padx=18, pady=(0, 10))

        footer = tk.Frame(main, bg=theme.COLORS["bg_panel"], highlightthickness=1,
                          highlightbackground=theme.COLORS["border"])
        footer.pack(fill="x", side="bottom")
        tk.Button(footer, text="Close", command=win.destroy, padx=16,
                  **theme.btn_primary_kw()).pack(side="right", padx=12, pady=10)
        tk.Button(footer, text="Apply", command=self._apply, padx=14,
                  **theme.btn_secondary_kw()).pack(side="right", padx=6, pady=10)
        self._status_var = tk.StringVar(master=win, value=self.startup_status)
        tk.Label(footer, textvariable=self._status_var, bg=theme.COLORS["bg_panel"],
                 fg=theme.COLORS["fg_muted"], anchor="w").pack(
            side="left", fill="x", expand=True, padx=12)

        outer = tk.Frame(main, bg=theme.COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=12)
        canvas = tk.Canvas(outer, bg=theme.COLORS["bg"], highlightthickness=0, bd=0)
        scroll = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.body = tk.Frame(canvas, bg=theme.COLORS["bg"])
        body_window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def body_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            try:
                canvas.itemconfigure(body_window, width=canvas.winfo_width())
            except tk.TclError:
                pass

        self._body_configure = body_configure
        self.body.bind("<Configure>", body_configure)
        canvas.bind("<Configure>", body_configure)

        def wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

        canvas.bind("<MouseWheel>", wheel)
        self.body.bind("<MouseWheel>", wheel)

        tk.Label(nav, text="Settings", bg=theme.COLORS["bg_nav"],
                 fg=theme.COLORS["fg_bright"], font=theme.font(12, bold=True)).pack(
            anchor="w", padx=12, pady=(14, 8))
        for page in self.pages:
            btn = tk.Button(nav, text=page, command=lambda name=page: self.render_page(name))
            btn.pack(fill="x", padx=8, pady=1)
            self._nav_buttons[page] = btn

        self.render_page(self.initial_page)
        return win

    def _style_nav_button(self, btn, selected):
        btn.configure(
            bg=theme.COLORS["accent"] if selected else theme.COLORS["bg_nav"],
            fg=theme.COLORS["fg_bright"] if selected else theme.COLORS["fg"],
            activebackground=theme.COLORS["accent_active"],
            activeforeground=theme.COLORS["fg_bright"],
            relief="flat", anchor="w", padx=12, pady=8)

    def render_page(self, name: str):
        if name not in self.renderers:
            name = self.pages[0]
        for child in self.body.winfo_children():
            child.destroy()
        self._title.configure(text=name)
        self._subtitle.configure(text=self.descriptions.get(name, ""))
        for page, btn in self._nav_buttons.items():
            self._style_nav_button(btn, page == name)
        self.renderers[name](self.body, self)
        self._body_configure()

    def set_status(self, text: str):
        if self._status_var is not None:
            self._status_var.set(text)

    def _apply(self):
        ok = False
        try:
            ok = bool(self.on_apply())
        except Exception:
            ok = False
        self.set_status("Settings saved" if ok
                        else "Settings save FAILED — see logs folder")
