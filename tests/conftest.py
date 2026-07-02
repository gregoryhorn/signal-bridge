import pytest
import tkinter as tk


@pytest.fixture(scope="session")
def _tk_root_session():
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


@pytest.fixture()
def tk_root(_tk_root_session):
    root = _tk_root_session
    for child in root.winfo_children():
        child.destroy()
    root.withdraw()
    yield root
    for child in root.winfo_children():
        child.destroy()
    root.withdraw()
