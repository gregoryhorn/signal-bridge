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
    # Resize again - the sash must follow (this is what the old code never did).
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
