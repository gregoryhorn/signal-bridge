# Phase 1: UI Foundation & Safety Nets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared theme/component/window/settings foundation for Signal Bridge's Tkinter UI, add the first automated UI tests, and prove the foundation by fixing the open P1 Translation Corrections sash bug.

**Architecture:** New `sb_ui/` package (theme constants, widget component builders, window helpers) and `sb_settings.py` (typed settings store), consumed by the existing monolith `signal_bridge_gui.py`. The monolith is only touched at three integration points in this phase; dialog rebuilds happen in Phase 2 (see `docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md`).

**Tech Stack:** Python 3 stdlib (tkinter, json, pathlib), pytest for tests. No new runtime dependencies (portable-ZIP invariant).

## Global Constraints

- Respect `docs/INVARIANTS.md`: the Tk UI thread must not block; the render path must not do network/MT/ESI work; the portable ZIP stays lightweight (stdlib only at runtime).
- Windows is the target platform; fonts default to `Segoe UI`.
- Do not refactor business logic (`EveCatalog`, `TranslationCache`, `EsiResolver`, `MonitorThread`) or any dialog not named in a task.
- Match existing code style in `signal_bridge_gui.py` when editing it (compact, minimal comments).
- Every task ends with: `python -m py_compile signal_bridge_gui.py` passing, `python scripts/check-fixtures.py` passing, `pytest tests/ -v` passing (once Task 2 introduces tests), and a commit.
- Line numbers cited below were verified on commit `073e2c4`. If the file has drifted, locate the code by the quoted snippet, not the number.
- pytest may not be installed: `pip install pytest` once at start (dev-only; never add to runtime deps or the PyInstaller bundle).

---

### Task 0: Repo hygiene

**Files:**
- Modify: `.gitignore`

**Interfaces:** none.

- [ ] **Step 1: Inspect current state**

Run: `git status --short` and open `.gitignore`.
Expected untracked noise: `build_portable_v05.log`, `data/legacy_exclusions_backup_20260625-073630.json`, `data/user_aliases_local_backup_20260625-084916.json`, `modules/`, `runtime/`.

- [ ] **Step 2: Append ignore rules**

Add these lines to the end of `.gitignore` (keep existing content untouched):

```gitignore
# local runtime add-on copies and dev/session artifacts
modules/
runtime/
data/*_backup_*.json
build_portable_*.log
```

- [ ] **Step 3: Verify**

Run: `git status --short`
Expected: the five items above no longer appear (only the new `.gitignore` modification and any plan docs).

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore local runtime copies, dev backups, versioned build logs"
```

---

### Task 1: Theme module (`sb_ui/theme.py`)

**Files:**
- Create: `sb_ui/__init__.py` (empty)
- Create: `sb_ui/theme.py`
- Test: `tests/test_theme.py`

**Interfaces:**
- Produces: `COLORS: dict[str, str]`, `FONT_FAMILY: str`, `font(size:int=10, bold:bool=False) -> tuple`, and kwarg helpers `btn_primary_kw()`, `btn_secondary_kw()`, `label_kw(muted:bool=False)`, `entry_kw()`, `check_kw()`, `radio_kw()`, `listbox_kw()`, `text_kw()`, `optionmenu_kw()` — each returns a fresh `dict` of Tk widget constructor kwargs. All later UI work imports styles ONLY from here.

The color values are extracted verbatim from the literals currently copy-pasted through `signal_bridge_gui.py` (e.g. lines 4392-4581): do not invent new colors in this phase.

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_theme.py`:

```python
from sb_ui import theme


def test_colors_match_legacy_literals():
    assert theme.COLORS["bg"] == "#0b0f14"
    assert theme.COLORS["bg_nav"] == "#0f1722"
    assert theme.COLORS["bg_panel"] == "#111821"
    assert theme.COLORS["bg_input"] == "#070b10"
    assert theme.COLORS["bg_editor"] == "#07111d"
    assert theme.COLORS["fg"] == "#d7dde5"
    assert theme.COLORS["fg_muted"] == "#8b98a8"
    assert theme.COLORS["fg_bright"] == "#ffffff"
    assert theme.COLORS["accent"] == "#1f6feb"
    assert theme.COLORS["accent_active"] == "#23405c"
    assert theme.COLORS["border"] == "#1f2f42"
    assert theme.COLORS["warning"] == "#facc15"
    assert theme.COLORS["success"] == "#7ee787"


def test_font_helper():
    assert theme.font() == ("Segoe UI", 10)
    assert theme.font(14, bold=True) == ("Segoe UI", 14, "bold")


def test_kwarg_helpers_return_fresh_dicts():
    a = theme.btn_primary_kw()
    b = theme.btn_primary_kw()
    assert a == b and a is not b
    assert a["bg"] == "#1f6feb" and a["relief"] == "flat"
    assert theme.btn_secondary_kw()["bg"] == "#111821"
    assert theme.label_kw()["fg"] == "#d7dde5"
    assert theme.label_kw(muted=True)["fg"] == "#8b98a8"
    assert theme.entry_kw()["insertbackground"] == "#ffffff"
    assert theme.check_kw()["selectcolor"] == "#111821"
    assert theme.radio_kw()["selectcolor"] == "#111821"
    assert theme.listbox_kw()["selectbackground"] == "#1f6feb"
    assert theme.text_kw()["bg"] == "#07111d"
    assert theme.optionmenu_kw()["bg"] == "#111821"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_theme.py -v`
Expected: FAIL / error `ModuleNotFoundError: No module named 'sb_ui'`

- [ ] **Step 3: Write the implementation**

Create empty `sb_ui/__init__.py`, then `sb_ui/theme.py`:

```python
"""Central Signal Bridge UI theme: every color/font used by widgets lives here.

Values are the canonical versions of the literals historically copy-pasted
through signal_bridge_gui.py. Change a color here, it changes everywhere.
"""

FONT_FAMILY = "Segoe UI"

COLORS = {
    "bg": "#0b0f14",          # main window / page background
    "bg_nav": "#0f1722",      # settings nav rail
    "bg_panel": "#111821",    # secondary buttons, pills, footers
    "bg_input": "#070b10",    # Entry/Listbox/Spinbox background
    "bg_editor": "#07111d",   # multi-line Text editor background
    "fg": "#d7dde5",          # normal text
    "fg_muted": "#8b98a8",    # help/secondary text
    "fg_bright": "#ffffff",   # emphasized text, active-state text
    "accent": "#1f6feb",      # primary buttons, selection highlight
    "accent_active": "#23405c",  # hover/active button background
    "border": "#1f2f42",      # thin frame borders
    "warning": "#facc15",     # warning/source labels
    "success": "#7ee787",     # success/correction labels
}


def font(size: int = 10, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def btn_primary_kw() -> dict:
    return dict(bg=COLORS["accent"], fg=COLORS["fg_bright"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")


def btn_secondary_kw() -> dict:
    return dict(bg=COLORS["bg_panel"], fg=COLORS["fg"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")


def label_kw(muted: bool = False) -> dict:
    return dict(bg=COLORS["bg"], fg=COLORS["fg_muted"] if muted else COLORS["fg"])


def entry_kw() -> dict:
    return dict(bg=COLORS["bg_input"], fg=COLORS["fg"],
                insertbackground=COLORS["fg_bright"], relief="flat")


def check_kw() -> dict:
    return dict(bg=COLORS["bg"], fg=COLORS["fg"], selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg"], activeforeground=COLORS["fg_bright"])


def radio_kw() -> dict:
    return check_kw()


def listbox_kw() -> dict:
    return dict(bg=COLORS["bg_input"], fg=COLORS["fg"],
                selectbackground=COLORS["accent"], relief="flat", exportselection=False)


def text_kw() -> dict:
    return dict(bg=COLORS["bg_editor"], fg="#e6edf3",
                insertbackground=COLORS["fg_bright"], relief="flat", wrap="word", undo=True)


def optionmenu_kw() -> dict:
    return dict(bg=COLORS["bg_panel"], fg=COLORS["fg"],
                activebackground=COLORS["accent_active"],
                activeforeground=COLORS["fg_bright"], relief="flat")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_theme.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sb_ui/__init__.py sb_ui/theme.py tests/__init__.py tests/test_theme.py
git commit -m "feat: add central UI theme module (sb_ui.theme)"
```

---

### Task 2: Component library (`sb_ui/components.py`)

**Files:**
- Create: `sb_ui/components.py`
- Test: `tests/test_components.py`
- Create: `tests/conftest.py` (shared Tk root fixture with no-display skip)

**Interfaces:**
- Consumes: `sb_ui.theme` (Task 1).
- Produces (all take a Tk parent as first arg):
  - `card(parent, heading: str, note: str | None = None) -> tk.LabelFrame` — packed `fill="x"` section frame.
  - `action_row(parent) -> tk.Frame` — packed horizontal row for buttons.
  - `action_button(parent, text: str, command) -> tk.Button` — secondary-style, packed `side="left"`.
  - `primary_button(parent, text: str, command) -> tk.Button` — primary-style, NOT packed (caller places it).
  - `check(parent, text: str, var, command=None) -> tk.Checkbutton` — packed `anchor="w"`.
  - `info_label(parent, text: str, muted: bool = False, wraplength: int = 600) -> tk.Label` — packed `anchor="w"`.
  - `balanced_paned(parent, left_min: int = 260, right_min: int = 260, fraction: float = 0.5) -> tuple[tk.PanedWindow, tk.Frame, tk.Frame]` — NOT packed (caller packs the PanedWindow). Sash auto-tracks `fraction` of current width on every `<Configure>` until the user clicks/drags the paned window, then user placement wins.

These mirror (and will eventually replace) the `card/row/action/check/label` closures inside `show_settings_center` (`signal_bridge_gui.py:4425-4436`) — keep behavior equivalent so Phase 2 migration is mechanical.

- [ ] **Step 1: Write the shared Tk fixture**

Create `tests/conftest.py`:

```python
import pytest
import tkinter as tk


@pytest.fixture()
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display available for Tk: {exc}")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_components.py`:

```python
import tkinter as tk

from sb_ui import components, theme


def test_card_builds_labelframe_with_note(tk_root):
    c = components.card(tk_root, "Heading", note="help text")
    assert isinstance(c, tk.LabelFrame)
    assert c.cget("text") == "Heading"
    notes = [w for w in c.winfo_children() if isinstance(w, tk.Label)]
    assert notes and notes[0].cget("text") == "help text"


def test_action_button_uses_secondary_style(tk_root):
    row = components.action_row(tk_root)
    btn = components.action_button(row, "Do It", lambda: None)
    assert btn.cget("bg") == theme.COLORS["bg_panel"]
    assert btn.cget("relief") == "flat"


def test_primary_button_is_not_packed(tk_root):
    btn = components.primary_button(tk_root, "Save", lambda: None)
    assert btn.cget("bg") == theme.COLORS["accent"]
    assert not btn.winfo_manager()


def test_check_and_info_label_pack_west(tk_root):
    var = tk.BooleanVar(master=tk_root, value=True)
    cb = components.check(tk_root, "opt", var)
    lbl = components.info_label(tk_root, "hello", muted=True)
    assert cb.winfo_manager() == "pack"
    assert lbl.cget("fg") == theme.COLORS["fg_muted"]


def test_balanced_paned_places_sash_at_fraction(tk_root):
    paned, left, right = components.balanced_paned(tk_root, left_min=100, right_min=100, fraction=0.5)
    paned.pack(fill="both", expand=True)
    # Simulate the real-world resize the old after_idle hack missed:
    tk_root.deiconify()
    tk_root.geometry("800x300")
    tk_root.update_idletasks()
    tk_root.update()
    x = paned.sash_coord(0)[0]
    width = paned.winfo_width()
    assert abs(x - width // 2) <= 20, f"sash at {x}, expected ~{width // 2}"
    # Resize again — the sash must follow (this is what the old code never did).
    tk_root.geometry("600x300")
    tk_root.update_idletasks()
    tk_root.update()
    x2 = paned.sash_coord(0)[0]
    width2 = paned.winfo_width()
    assert abs(x2 - width2 // 2) <= 20, f"sash at {x2} after resize, expected ~{width2 // 2}"


def test_balanced_paned_respects_user_placement(tk_root):
    paned, left, right = components.balanced_paned(tk_root, left_min=50, right_min=50, fraction=0.5)
    paned.pack(fill="both", expand=True)
    tk_root.deiconify()
    tk_root.geometry("800x300")
    tk_root.update()
    paned.event_generate("<ButtonRelease-1>", x=400, y=10)
    paned.sash_place(0, 200, 0)
    tk_root.geometry("700x300")
    tk_root.update()
    assert paned.sash_coord(0)[0] <= 300, "auto-placement must stop after user interaction"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_components.py -v`
Expected: FAIL with `cannot import name 'components'` (or ModuleNotFoundError)

- [ ] **Step 4: Write the implementation**

Create `sb_ui/components.py`:

```python
"""Reusable Signal Bridge widget builders. All styling comes from sb_ui.theme."""

import tkinter as tk

from . import theme


def card(parent, heading: str, note: str | None = None) -> tk.LabelFrame:
    frame = tk.LabelFrame(parent, text=heading, bg=theme.COLORS["bg"],
                          fg=theme.COLORS["fg"], padx=10, pady=8)
    frame.pack(fill="x", padx=6, pady=8)
    if note:
        tk.Label(frame, text=note, wraplength=590, justify="left",
                 **theme.label_kw(muted=True)).pack(anchor="w", pady=(0, 6))
    return frame


def action_row(parent) -> tk.Frame:
    row = tk.Frame(parent, bg=theme.COLORS["bg"])
    row.pack(fill="x", pady=4)
    return row


def action_button(parent, text: str, command) -> tk.Button:
    btn = tk.Button(parent, text=text, command=command, padx=10,
                    **theme.btn_secondary_kw())
    btn.pack(side="left", padx=(0, 8), pady=4)
    return btn


def primary_button(parent, text: str, command) -> tk.Button:
    return tk.Button(parent, text=text, command=command, padx=16,
                     **theme.btn_primary_kw())


def check(parent, text: str, var, command=None) -> tk.Checkbutton:
    cb = tk.Checkbutton(parent, text=text, variable=var, command=command,
                        **theme.check_kw())
    cb.pack(anchor="w", pady=2)
    return cb


def info_label(parent, text: str, muted: bool = False, wraplength: int = 600) -> tk.Label:
    lbl = tk.Label(parent, text=text, justify="left", anchor="w",
                   wraplength=wraplength, **theme.label_kw(muted=muted))
    lbl.pack(anchor="w", fill="x", pady=2)
    return lbl


def balanced_paned(parent, left_min: int = 260, right_min: int = 260,
                   fraction: float = 0.5):
    """Two-pane horizontal PanedWindow whose sash tracks `fraction` of the
    current width on every <Configure> until the user interacts with it.

    Fixes the read-geometry-before-layout-settles bug class: the old pattern
    (`after_idle` + one-shot `winfo_width()`) captured a stale width and never
    adjusted on resize.
    """
    paned = tk.PanedWindow(parent, orient="horizontal", bg=theme.COLORS["bg"],
                           sashwidth=8, sashrelief="flat", bd=0, showhandle=False)
    left = tk.Frame(paned, bg=theme.COLORS["bg"])
    right = tk.Frame(paned, bg=theme.COLORS["bg"])
    paned.add(left, minsize=left_min, stretch="always")
    paned.add(right, minsize=right_min, stretch="always")
    state = {"user_moved": False, "last_width": 0}

    def place_sash(_event=None):
        if state["user_moved"]:
            return
        width = paned.winfo_width()
        if width <= 1 or width == state["last_width"]:
            return
        state["last_width"] = width
        x = max(left_min, min(int(width * fraction), width - right_min))
        try:
            paned.sash_place(0, x, 0)
        except tk.TclError:
            pass

    def mark_user_moved(_event):
        state["user_moved"] = True

    paned.bind("<Configure>", place_sash)
    paned.bind("<ButtonRelease-1>", mark_user_moved, add="+")
    return paned, left, right
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_components.py -v`
Expected: all PASS (or SKIP only if no display — on the Windows dev machine they must PASS)

- [ ] **Step 6: Commit**

```bash
git add sb_ui/components.py tests/conftest.py tests/test_components.py
git commit -m "feat: add reusable UI component builders with self-correcting paned layout"
```

---

### Task 3: Window helpers (`sb_ui/windows.py`)

**Files:**
- Create: `sb_ui/windows.py`
- Test: `tests/test_windows.py`

**Interfaces:**
- Consumes: `sb_ui.theme`.
- Produces:
  - `polish_window(win, parent, *, width=None, height=None, minsize=None, modal=False, center=True, title=None, icon_path=None, log=None) -> win` — behavior-compatible extraction of `SignalBridgeGui.polish_window` (`signal_bridge_gui.py:3870-3923`), with two changes: `icon_path` is passed in (no `self`), and every swallowed exception now calls `log(message)` when a `log` callable is given.
  - `fit_to_content(win, parent=None, min_size=(560, 430), max_size=(1100, 800), pad=(24, 24)) -> tuple[int, int]` — sizes a Toplevel to its content's requested size (after `update_idletasks`), clamped to `min_size`, `max_size`, and the usable screen area; centers over `parent` when given; returns the final `(width, height)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_windows.py`:

```python
import tkinter as tk

from sb_ui import windows, theme


def test_polish_window_applies_chrome_and_geometry(tk_root):
    win = tk.Toplevel(tk_root)
    logged = []
    out = windows.polish_window(win, tk_root, width=400, height=300,
                                minsize=(200, 150), title="Test Window",
                                log=logged.append)
    assert out is win
    assert win.title() == "Test Window"
    assert win.cget("bg") == theme.COLORS["bg"]
    tk_root.update_idletasks()
    assert win.winfo_width() == 400 and win.winfo_height() == 300
    win.destroy()


def test_polish_window_logs_instead_of_swallowing(tk_root):
    win = tk.Toplevel(tk_root)
    logged = []
    windows.polish_window(win, tk_root, icon_path="Z:/does/not/exist.ico",
                          log=logged.append)
    assert any("icon" in msg.lower() for msg in logged)
    win.destroy()


def test_fit_to_content_clamps_to_bounds(tk_root):
    win = tk.Toplevel(tk_root)
    tk.Frame(win, width=2000, height=2000).pack()
    w, h = windows.fit_to_content(win, tk_root, min_size=(300, 200),
                                  max_size=(800, 600))
    assert (w, h) == (800, 600)
    win.destroy()

    win2 = tk.Toplevel(tk_root)
    tk.Frame(win2, width=50, height=40).pack()
    w2, h2 = windows.fit_to_content(win2, tk_root, min_size=(300, 200),
                                    max_size=(800, 600))
    assert (w2, h2) == (300, 200)
    win2.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_windows.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write the implementation**

Create `sb_ui/windows.py`:

```python
"""Toplevel window chrome, stacking, and sizing helpers."""

import tkinter as tk

from . import theme


def _noop(_msg: str) -> None:
    pass


def polish_window(win, parent, *, width=None, height=None, minsize=None,
                  modal=False, center=True, title=None, icon_path=None,
                  log=None):
    """Apply consistent Signal Bridge chrome, icon, stacking, and placement."""
    log = log or _noop
    if title:
        try:
            win.title(title)
        except Exception as exc:
            log(f"Window title failed: {exc}")
    if icon_path:
        try:
            win.iconbitmap(str(icon_path))
        except Exception as exc:
            log(f"Window icon failed: {exc}")
    try:
        win.configure(bg=theme.COLORS["bg"])
    except Exception as exc:
        log(f"Window bg failed: {exc}")
    if minsize:
        try:
            win.minsize(*minsize)
        except Exception as exc:
            log(f"Window minsize failed: {exc}")
    if width and height:
        try:
            if center:
                parent.update_idletasks()
                win.update_idletasks()
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw = max(1, parent.winfo_width())
                ph = max(1, parent.winfo_height())
                x = max(0, px + (pw - width) // 2)
                y = max(0, py + (ph - height) // 2)
                win.geometry(f"{width}x{height}+{x}+{y}")
            else:
                win.geometry(f"{width}x{height}")
        except Exception as exc:
            log(f"Window centering failed: {exc}")
            win.geometry(f"{width}x{height}")
    try:
        win.transient(parent)
    except Exception as exc:
        log(f"Window transient failed: {exc}")
    if modal:
        try:
            win.grab_set()
        except Exception as exc:
            log(f"Window grab failed: {exc}")
    try:
        win.lift(parent)
        win.focus_force()
    except Exception as exc:
        log(f"Window lift/focus failed: {exc}")
    return win


def fit_to_content(win, parent=None, min_size=(560, 430), max_size=(1100, 800),
                   pad=(24, 24)):
    """Size `win` to its content's requested size, clamped to bounds and screen.

    Returns the final (width, height). Call AFTER the window's content is built.
    """
    win.update_idletasks()
    req_w = win.winfo_reqwidth() + pad[0]
    req_h = win.winfo_reqheight() + pad[1]
    screen_w = win.winfo_screenwidth() - 80
    screen_h = win.winfo_screenheight() - 120
    width = max(min_size[0], min(req_w, max_size[0], screen_w))
    height = max(min_size[1], min(req_h, max_size[1], screen_h))
    if parent is not None:
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw = max(1, parent.winfo_width())
            ph = max(1, parent.winfo_height())
            x = max(0, px + (pw - width) // 2)
            y = max(0, py + (ph - height) // 2)
            win.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            win.geometry(f"{width}x{height}")
    else:
        win.geometry(f"{width}x{height}")
    win.update_idletasks()
    return width, height
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_windows.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sb_ui/windows.py tests/test_windows.py
git commit -m "feat: add window chrome and content-driven sizing helpers"
```

---

### Task 4: Typed settings store (`sb_settings.py`)

**Files:**
- Create: `sb_settings.py` (repo root, alongside `signal_bridge_gui.py` — matches the flat-module pattern of `signal_bridge_render_model.py`)
- Test: `tests/test_settings_store.py`

**Interfaces:**
- Produces: `class SettingsStore`:
  - `SettingsStore(path, schema: dict[str, tuple[type, object]], log=None)` — `schema` maps key → `(expected_type, default)`; a default may be a zero-arg callable (evaluated at `defaults()` time) for computed values like the detected chatlog dir.
  - `.defaults() -> dict` — fresh deep-copied defaults.
  - `.load() -> dict` — defaults overlaid with the JSON file. Per-key: matching type accepted; mismatched type coerced via `expected_type(value)` when possible, else default kept; every coercion/rejection appends to `.warnings` and calls `log(msg)`. Unknown keys are preserved as-is (forward compatibility). A missing file returns defaults silently; a corrupt file returns defaults and logs.
  - `.save(settings: dict) -> bool` — atomic write (temp file + `os.replace`); `True` on success, `False` + `log(msg)` on failure. Never raises.
  - `.warnings: list[str]` — populated by the most recent `load()`.
- Consumed by: Task 6 wires `signal_bridge_gui.py`'s main settings through it; Phase 2 batch 2.1 surfaces `.warnings`/save failures in the Settings UI; the ESI settings/token stores migrate to it in Phase 2.

Note `bool` is a subclass of `int` in Python — the type check must test `bool` before `int` so `True` is rejected for an `int` field and `1` is rejected for a `bool` field (then coerced).

- [ ] **Step 1: Write the failing test**

Create `tests/test_settings_store.py`:

```python
import json

from sb_settings import SettingsStore

SCHEMA = {
    "font_size": (int, 10),
    "always_on_top": (bool, True),
    "font_family": (str, "Segoe UI"),
    "tab_order": (list, ["__all__"]),
    "chatlog_dir": (str, lambda: "computed-default"),
}


def make_store(tmp_path, name="settings.json"):
    return SettingsStore(tmp_path / name, SCHEMA)


def test_missing_file_returns_defaults(tmp_path):
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 10
    assert settings["chatlog_dir"] == "computed-default"
    assert store.warnings == []


def test_defaults_are_fresh_copies(tmp_path):
    store = make_store(tmp_path)
    a, b = store.defaults(), store.defaults()
    a["tab_order"].append("x")
    assert b["tab_order"] == ["__all__"]


def test_valid_values_load_and_unknown_keys_survive(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"font_size": 14, "future_key": {"a": 1}}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 14
    assert settings["future_key"] == {"a": 1}
    assert store.warnings == []


def test_wrong_type_is_coerced_with_warning(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"font_size": "12"}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 12
    assert any("font_size" in w for w in store.warnings)


def test_uncoercible_value_falls_back_to_default(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({"font_size": "huge"}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["font_size"] == 10
    assert any("font_size" in w for w in store.warnings)


def test_bool_int_confusion_is_flagged(tmp_path):
    (tmp_path / "settings.json").write_text(
        json.dumps({"always_on_top": 1, "font_size": True}), encoding="utf-8")
    store = make_store(tmp_path)
    settings = store.load()
    assert settings["always_on_top"] is True
    assert settings["font_size"] == 10  # bool must not silently satisfy int
    assert len(store.warnings) >= 1


def test_corrupt_file_returns_defaults_and_logs(tmp_path):
    (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
    logged = []
    store = SettingsStore(tmp_path / "settings.json", SCHEMA, log=logged.append)
    settings = store.load()
    assert settings["font_size"] == 10
    assert logged


def test_save_roundtrip_and_failure_reporting(tmp_path):
    store = make_store(tmp_path)
    assert store.save({"font_size": 11}) is True
    assert json.loads((tmp_path / "settings.json").read_text(encoding="utf-8")) == {"font_size": 11}

    logged = []
    bad = SettingsStore(tmp_path / "no_dir_perms" / "\0bad" / "x.json", SCHEMA, log=logged.append)
    assert bad.save({"a": 1}) is False
    assert logged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sb_settings'`

- [ ] **Step 3: Write the implementation**

Create `sb_settings.py`:

```python
"""Typed JSON settings store with per-key validation and non-silent failures."""

import copy
import json
import os
from pathlib import Path


def _noop(_msg: str) -> None:
    pass


class SettingsStore:
    def __init__(self, path, schema, log=None):
        self.path = Path(path)
        self.schema = schema
        self.log = log or _noop
        self.warnings: list[str] = []

    def defaults(self) -> dict:
        out = {}
        for key, (_type, default) in self.schema.items():
            out[key] = default() if callable(default) else copy.deepcopy(default)
        return out

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.log(msg)

    def _validate(self, key, value, expected_type, default):
        # bool is a subclass of int: check bool identity explicitly both ways.
        if expected_type is bool:
            if isinstance(value, bool):
                return value
        elif expected_type is int:
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        elif isinstance(value, expected_type):
            return value
        try:
            coerced = expected_type(value)
            if expected_type is int and isinstance(value, bool):
                raise TypeError("bool is not an int setting")
            self._warn(f"settings: coerced {key}={value!r} to {expected_type.__name__}")
            return coerced
        except Exception:
            self._warn(f"settings: invalid {key}={value!r}, using default {default!r}")
            return default

    def load(self) -> dict:
        self.warnings = []
        settings = self.defaults()
        if not self.path.exists():
            return settings
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._warn(f"settings: failed to read {self.path.name}: {exc}; using defaults")
            return settings
        if not isinstance(loaded, dict):
            self._warn(f"settings: {self.path.name} is not a JSON object; using defaults")
            return settings
        for key, value in loaded.items():
            if key in self.schema:
                expected_type, _ = self.schema[key]
                settings[key] = self._validate(key, value, expected_type, settings[key])
            else:
                settings[key] = value  # forward compatibility
        return settings

    def save(self, settings: dict) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, self.path)
            return True
        except Exception as exc:
            self.log(f"settings: save to {self.path} failed: {exc}")
            return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings_store.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest tests/ -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add sb_settings.py tests/test_settings_store.py
git commit -m "feat: add typed SettingsStore with validation and non-silent save failures"
```

---

### Task 5: Wire main settings through SettingsStore

**Files:**
- Modify: `signal_bridge_gui.py:105-156` (`load_settings` / `save_settings`)

**Interfaces:**
- Consumes: `SettingsStore` from Task 4; existing module globals `CONFIG_PATH`, `CONFIG_DIR`, `CACHE_DIR`, `MODEL_DIR`, `LOG_DIR`, `write_log`, `detect_chatlog_dir`, `DEFAULT_DB_PATH`, `DATA_DIR`, `ALL_CHANNELS_TAB`, `INTEL_HISTORY_ADDON_ID`.
- Produces: `load_settings() -> dict` and `save_settings(settings) -> None` keep their exact existing signatures (they have call sites throughout the 7,778-line file — do NOT change callers in this phase). New module global `MAIN_SETTINGS_STORE` for Phase 2 to reach `.warnings`.

- [ ] **Step 1: Add the import**

Near the top of `signal_bridge_gui.py` with the other local imports (search for `import signal_bridge_render_model` or the stdlib import block) add:

```python
from sb_settings import SettingsStore
```

- [ ] **Step 2: Replace load_settings/save_settings**

Replace the whole block at `signal_bridge_gui.py:105-156` (the current `load_settings` and `save_settings` shown below) — the schema keys/defaults are copied exactly from the current `defaults` dict:

Current code being replaced (for locating it):

```python
def load_settings() -> dict:
    defaults = {
        "chatlog_dir": str(detect_chatlog_dir()),
        ...
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
        ...
        CONFIG_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
```

New code:

```python
SETTINGS_SCHEMA = {
    "chatlog_dir": (str, lambda: str(detect_chatlog_dir())),
    "db_path": (str, lambda: str(DEFAULT_DB_PATH if DEFAULT_DB_PATH.exists() else DATA_DIR / "translations.db")),
    "active_channels": (list, []),
    "always_on_top": (bool, True),
    "translated_only": (bool, True),
    "translate_free_text": (bool, True),
    "translation_direction": (str, "zh-en"),
    "translation_preferred_engine": (str, "auto"),
    "translation_fallback_mode": (str, "online-only"),
    "translation_cache_mode": (str, "cache-first-auto"),
    "translation_failure_cooldown_minutes": (int, 60),
    "compact_mode": (bool, True),
    "font_family": (str, "Segoe UI"),
    "font_size": (int, 10),
    "show_timestamps": (bool, True),
    "show_channel_names": (bool, False),
    "show_channel_names_in_all": (bool, True),
    "enable_hyperlinks": (bool, True),
    "active_tab_id": (str, ALL_CHANNELS_TAB),
    "tab_order": (list, [ALL_CHANNELS_TAB]),
    "hidden_tab_ids": (list, []),
    "auto_open_new_channels": (bool, True),
    "auto_switch_to_new_channel": (bool, False),
    "max_tab_rows": (int, 3),
    "check_updates_on_start": (bool, True),
    "addons": (dict, {INTEL_HISTORY_ADDON_ID: {"enabled": True}}),
    "esi_entity_recognition": (bool, True),
    "esi_oauth_enabled": (bool, False),
    "replay_on_start": (bool, False),
}

MAIN_SETTINGS_STORE = SettingsStore(CONFIG_PATH, SETTINGS_SCHEMA, log=lambda msg: write_log(msg))


def load_settings() -> dict:
    return MAIN_SETTINGS_STORE.load()


def save_settings(settings: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not MAIN_SETTINGS_STORE.save(settings):
        write_log(f"Settings save failed: {CONFIG_PATH}")
```

**Caution:** `SETTINGS_SCHEMA` references `detect_chatlog_dir`, `DEFAULT_DB_PATH`, `ALL_CHANNELS_TAB`, `INTEL_HISTORY_ADDON_ID`, `write_log`, `CONFIG_PATH` — all must already be defined above line 105. Verify each with a quick search; if any is defined later in the file, place the schema/store block immediately after the last of those definitions instead, keeping `load_settings`/`save_settings` where they are. Also confirm the `mkdir` calls for `CACHE_DIR`/`MODEL_DIR`/`LOG_DIR` stay (the old `save_settings` created them as a side effect other code may rely on; `SettingsStore.save` only creates `CONFIG_DIR`).

- [ ] **Step 3: Verify**

Run: `python -m py_compile signal_bridge_gui.py` — expected: exit 0, no output.
Run: `python scripts/check-fixtures.py` — expected: same pass output as before the change.
Run: `python -X utf8 signal_bridge_gui.py`, open Settings, toggle a checkbox (e.g. "Show timestamps"), close the app, confirm `config/settings.json` still contains the toggled value and the app restarts with it applied.

- [ ] **Step 4: Commit**

```bash
git add signal_bridge_gui.py
git commit -m "refactor: route main settings through typed SettingsStore, stop swallowing save failures"
```

---

### Task 6: First integration — delegate polish_window, fix the P1 sash bug

**Files:**
- Modify: `signal_bridge_gui.py:3870-3923` (`SignalBridgeGui.polish_window`)
- Modify: `signal_bridge_gui.py:4530-4542` (Translation Corrections `PanedWindow` block inside `render_translation_cache`)
- Modify: `ISSUES.md` (status update)

**Interfaces:**
- Consumes: `sb_ui.windows.polish_window`, `sb_ui.components.balanced_paned` (Tasks 2-3).
- Produces: no new interfaces; `SignalBridgeGui.polish_window(...)` keeps its exact signature (8 call sites at lines 3645, 3792, 4117, 4392, 4888, 5250, 5556, 6441 must keep working unchanged).

- [ ] **Step 1: Add imports**

Next to the Task 5 import in `signal_bridge_gui.py`:

```python
from sb_ui import components as sb_components
from sb_ui import windows as sb_windows
```

- [ ] **Step 2: Delegate the method**

Replace the entire body of `SignalBridgeGui.polish_window` (`signal_bridge_gui.py:3870-3923`) with:

```python
    def polish_window(self, win, parent=None, *, width=None, height=None, minsize=None, modal=False, center=True, title=None):
        """Apply consistent Signal Bridge chrome, icon, stacking, and placement to child windows."""
        return sb_windows.polish_window(
            win, parent or self.root, width=width, height=height, minsize=minsize,
            modal=modal, center=center, title=title,
            icon_path=self.app_icon_path(), log=write_log,
        )
```

- [ ] **Step 3: Replace the buggy sash block**

In `render_translation_cache`, replace this block (`signal_bridge_gui.py:4530-4538`):

```python
            tables = tk.PanedWindow(c, orient="horizontal", bg="#0b0f14", sashwidth=8, sashrelief="flat", bd=0, showhandle=False)
            tables.pack(fill="both", expand=True, pady=(2, 8))
            left = tk.Frame(tables, bg="#0b0f14")
            right = tk.Frame(tables, bg="#0b0f14")
            # Translation corrections are primarily edited on the English side,
            # so give it a slightly larger default share while keeping Original readable.
            tables.add(left, minsize=260, stretch="always", padx=0, pady=0)
            tables.add(right, minsize=320, stretch="always", padx=0, pady=0)
            tables.after_idle(lambda: tables.sash_place(0, max(260, int(tables.winfo_width() * 0.43)), 0))
```

with:

```python
            # Balanced 50/50 Original/English split that self-corrects on resize
            # instead of reading winfo_width() once before layout settles.
            tables, left, right = sb_components.balanced_paned(c, left_min=260, right_min=320, fraction=0.5)
            tables.pack(fill="both", expand=True, pady=(2, 8))
```

The following `for pane in (left, right):` grid-config lines and all `left`/`right` children (lines 4540 onward) stay exactly as they are.

- [ ] **Step 4: Verify (visual inspection required — this is a P1 UI bug per ISSUES.md)**

Run: `python -m py_compile signal_bridge_gui.py` — exit 0.
Run: `pytest tests/ -v` — all pass.
Run: `python scripts/check-fixtures.py` — passes.
Run: `python -X utf8 signal_bridge_gui.py`, then:
1. Open Settings > Translation Cache at the default Settings size (860x620).
2. Confirm the Original and English panes are approximately balanced (sash near the middle), the English list/editor is readable, not a narrow strip.
3. Resize the Settings window wider and narrower — the sash keeps tracking ~50% until you drag it, after which your placement sticks.
4. Open two other dialogs that use `polish_window` (e.g. Settings itself and the Appearance editor) — confirm icon, dark background, centering, and stacking are unchanged.
5. Record a short before/after note (the "before" behavior is documented in ISSUES.md "Translation Corrections layout gives too much width to Original").

- [ ] **Step 5: Update ISSUES.md**

Change the heading `## Open: Translation Corrections layout gives too much width to Original and squeezes English` to `## Fixed: Translation Corrections layout gives too much width to Original and squeezes English`, change `- Status: open` to `- Status: fixed in source (Phase 1 UI foundation)`, and append under it:

```markdown
### Fix summary

- Replaced the one-shot `after_idle` sash placement (which read `winfo_width()` before layout settled) with a shared `balanced_paned` component that tracks a 50/50 split on every `<Configure>` until the user drags the sash.
- Visual inspection performed at default Settings size and across resizes.
```

- [ ] **Step 6: Commit**

```bash
git add signal_bridge_gui.py ISSUES.md
git commit -m "fix: balanced self-correcting Translation Corrections split via sb_ui foundation"
```

---

### Task 7: Document the foundation

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PROJECT_MAP.md`
- Modify: `CHANGELOG.md`

**Interfaces:** none.

- [ ] **Step 1: ARCHITECTURE.md**

Add this section after "## Current architecture":

```markdown
## UI foundation (Phase 1, 2026-07)

New shared UI infrastructure that all dialog/page work must build on:

- `sb_ui/theme.py`: every color/font constant. No hex literals in new widget code.
- `sb_ui/components.py`: `card`, `action_row`, `action_button`, `primary_button`, `check`, `info_label`, `balanced_paned`. New pages compose these instead of hand-rolling per-dialog closures.
- `sb_ui/windows.py`: `polish_window` (chrome/stacking) and `fit_to_content` (content-driven sizing clamped to min/max/screen). New dialogs must not hardcode a fixed width/height without a reason.
- `sb_settings.py`: `SettingsStore` — typed schema, validation warnings, atomic non-silent saves. Main settings use it; ESI settings/tokens migrate in Phase 2.
- `tests/`: pytest suite covering the above with real Tk widgets. Run `pytest tests/ -v`.

Overhaul roadmap: `docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md`.
```

- [ ] **Step 2: PROJECT_MAP.md**

Add rows to the area/location table for `sb_ui/theme.py`, `sb_ui/components.py`, `sb_ui/windows.py`, `sb_settings.py`, `tests/` (pytest UI/unit tests), and add `pytest tests/ -v` to the standard validation commands list. Also correct the stale "Current release line: v0.3" to v0.5.

- [ ] **Step 3: CHANGELOG.md**

Under a new `## Unreleased` heading at the top (create it if absent), add:

```markdown
- Added shared UI foundation (`sb_ui` theme/components/window helpers) and typed settings store with validation warnings and non-silent save failures.
- Fixed Translation Corrections Original/English split: balanced 50/50 layout that self-corrects on resize (was P1).
- Added pytest test suite for UI components and settings store.
```

- [ ] **Step 4: Verify and commit**

Run: `pytest tests/ -v` and `python -m py_compile signal_bridge_gui.py` one final time — all pass.

```bash
git add docs/ARCHITECTURE.md docs/PROJECT_MAP.md CHANGELOG.md
git commit -m "docs: document sb_ui foundation, settings store, and test suite"
```

---

## Completion criteria for Phase 1

- All 8 tasks committed; `pytest tests/ -v`, `python -m py_compile signal_bridge_gui.py`, `python scripts/check-fixtures.py` all pass.
- App launches and behaves identically except: Translation Corrections panes are balanced, settings save failures appear in `logs/`, malformed settings values produce logged warnings instead of silent misbehavior.
- ISSUES.md "Translation Corrections layout" marked fixed with visual-inspection note.
- Next step: write the Phase 2 batch plans per the roadmap (`superpowers:writing-plans`, one plan per batch 2.1-2.5).
