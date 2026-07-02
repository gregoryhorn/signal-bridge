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
