import tkinter as tk

from sb_ui import components, theme


def test_card_builds_labelframe_with_note(tk_root):
    c = components.card(tk_root, "Heading", note="help text")
    assert isinstance(c, tk.LabelFrame)
    assert c.cget("text") == "Heading"
    notes = [w for w in c.winfo_children() if isinstance(w, tk.Label)]
    assert notes and notes[0].cget("text") == "help text"


def test_danger_card_uses_error_title_color(tk_root):
    c = components.danger_card(tk_root, "Danger", note="be careful")
    assert c.cget("fg") == theme.COLORS["error"]
    notes = [w for w in c.winfo_children() if isinstance(w, tk.Label)]
    assert notes and "be careful" in notes[0].cget("text")


def test_labeled_spinbox_packs_row(tk_root):
    var = tk.IntVar(master=tk_root, value=10)
    row, box = components.labeled_spinbox(tk_root, "Minutes", var, from_=1, to=60)
    assert row.winfo_manager() == "pack"
    assert int(box.cget("to")) == 60


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


def test_info_label_fg_override(tk_root):
    lbl = components.info_label(tk_root, "boom", fg=theme.COLORS["error"])
    assert lbl.cget("fg") == "#ff8f8f"


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


def test_preview_table_builds_styled_treeview(tk_root):
    frame, tree = components.preview_table(
        tk_root, [("original", "Original"), ("english", "English")])
    assert not frame.winfo_manager(), "caller packs the frame"
    assert str(tree.cget("selectmode")) == "browse"
    assert list(tree.cget("columns")) == ["original", "english"]
    assert str(tree.cget("show")[0]) == "headings"
    assert str(tree.cget("style")) == "SB.Treeview"
    iid = tree.insert("", "end", values=("ä½ å¥½", "hello"))
    assert tree.item(iid, "values") == ("ä½ å¥½", "hello")
