import tkinter as tk
import inspect

from sb_ui import windows, theme
from signal_bridge_gui import SignalBridgeGui


def test_beside_parent_prefers_right_then_left_then_below():
    right = windows.place_beside_bounds((400, 200, 500, 600), (300, 400), (0, 0, 1600, 1000))
    left = windows.place_beside_bounds((1100, 200, 400, 600), (300, 400), (0, 0, 1600, 1000))
    below = windows.place_beside_bounds((400, 300, 800, 300), (700, 250), (0, 0, 1200, 1000))

    assert right == (916, 300)
    assert left == (784, 300)
    assert below == (450, 616)


def test_gui_window_wrapper_accepts_placement_policy():
    assert "placement" in inspect.signature(SignalBridgeGui.polish_window).parameters


def test_hidden_tabs_dialog_uses_shared_window_chrome():
    source = inspect.getsource(SignalBridgeGui.restore_hidden_tabs_dialog)
    assert "self.polish_window(" in source


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


def test_fit_to_content_preserves_existing_window_position(tk_root):
    win = tk.Toplevel(tk_root)
    win.geometry("300x200+175+225")
    tk.Frame(win, width=450, height=350).pack()
    tk_root.update_idletasks()
    before = (win.winfo_x(), win.winfo_y())

    width, height = windows.fit_to_content(
        win, tk_root, min_size=(300, 200), max_size=(800, 600), preserve_position=True,
    )

    assert (width, height) == (474, 374)
    assert (win.winfo_x(), win.winfo_y()) == before
    win.destroy()
