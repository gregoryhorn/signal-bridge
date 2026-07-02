import tkinter as tk

from sb_ui.settings_center import SettingsShell
from sb_ui import theme


def _noop_polish(win, parent=None, **kw):
    if kw.get("title"):
        win.title(kw["title"])
    if kw.get("width") and kw.get("height"):
        win.geometry(f"{kw['width']}x{kw['height']}")
    return win


def make_shell(tk_root, rendered, on_apply=lambda: True, startup_status=""):
    pages = ["Alpha", "Beta"]
    return SettingsShell(
        tk_root,
        pages=pages,
        descriptions={"Alpha": "first page", "Beta": "second page"},
        renderers={
            "Alpha": lambda body, shell: rendered.append(("Alpha", body, shell)),
            "Beta": lambda body, shell: rendered.append(("Beta", body, shell)),
        },
        on_apply=on_apply,
        polish=_noop_polish,
        initial_page="Alpha",
        startup_status=startup_status,
    )


def test_open_renders_initial_page_and_title(tk_root):
    rendered = []
    shell = make_shell(tk_root, rendered)
    win = shell.open()
    assert rendered and rendered[0][0] == "Alpha"
    assert win.title() == "Signal Bridge Settings"
    assert rendered[0][2] is shell
    win.destroy()


def test_render_page_switches_and_clears_body(tk_root):
    rendered = []
    shell = make_shell(tk_root, rendered)
    shell.open()
    tk.Label(shell.body, text="stale").pack()
    shell.render_page("Beta")
    assert rendered[-1][0] == "Beta"
    stale = [w for w in shell.body.winfo_children()
             if isinstance(w, tk.Label) and w.cget("text") == "stale"]
    assert not stale, "render_page must clear previous page widgets"
    shell.win.destroy()


def test_unknown_page_falls_back_to_first(tk_root):
    rendered = []
    shell = make_shell(tk_root, rendered)
    shell.open()
    shell.render_page("Nope")
    assert rendered[-1][0] == "Alpha"
    shell.win.destroy()


def test_apply_success_and_failure_status(tk_root):
    rendered = []
    results = iter([True, False])
    shell = make_shell(tk_root, rendered, on_apply=lambda: next(results))
    shell.open()
    shell._apply()
    assert "saved" in shell._status_var.get().lower()
    shell._apply()
    assert "failed" in shell._status_var.get().lower()
    shell.win.destroy()


def test_startup_status_shown(tk_root):
    rendered = []
    shell = make_shell(tk_root, rendered, startup_status="2 settings warnings - see logs")
    shell.open()
    assert "warnings" in shell._status_var.get()
    shell.win.destroy()


def _descendants(widget):
    out = []
    stack = [widget]
    while stack:
        w = stack.pop()
        out.append(w)
        stack.extend(w.winfo_children())
    return out


def test_nav_title_custom_and_apply_hidden(tk_root):
    rendered = []
    shell = SettingsShell(
        tk_root, pages=["Alpha"], descriptions={"Alpha": ""},
        renderers={"Alpha": lambda body, shell: rendered.append("Alpha")},
        on_apply=lambda: True, polish=_noop_polish, initial_page="Alpha",
        nav_title="Help", show_apply=False)
    win = shell.open()
    widgets = _descendants(win)
    assert any(isinstance(w, tk.Label) and w.cget("text") == "Help" for w in widgets)
    assert not any(isinstance(w, tk.Button) and w.cget("text") == "Apply" for w in widgets)
    win.destroy()


def test_defaults_keep_settings_nav_and_apply(tk_root):
    rendered = []
    shell = make_shell(tk_root, rendered)
    win = shell.open()
    widgets = _descendants(win)
    assert any(isinstance(w, tk.Label) and w.cget("text") == "Settings" for w in widgets)
    assert any(isinstance(w, tk.Button) and w.cget("text") == "Apply" for w in widgets)
    win.destroy()
