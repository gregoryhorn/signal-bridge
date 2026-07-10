import tkinter as tk

from sb_ui import components


def test_void_tactical_components_expose_clear_hierarchy(tk_root):
    host = tk.Frame(tk_root)
    host.pack()
    section = components.section(host, "Local sightings", "Three most recent reports")
    ribbon = components.status_ribbon(host, "HIGH THREAT", tone="threat_high")
    chip = components.chip(host, "4-HWWF ×3", kind="system")
    empty = components.empty_state(host, "No local sightings", "Sync zKill for 30-day activity.")
    toolbar = components.toolbar(host)
    footer = components.footer(host)
    table_frame, table = components.data_table(host, [("time", "Time"), ("system", "System")], [("12:42", "4-HWWF")])

    assert section.cget("text") == "Local sightings"
    assert ribbon.cget("text") == "HIGH THREAT"
    assert chip.cget("text") == "4-HWWF ×3"
    assert any(isinstance(child, tk.Label) and child.cget("text") == "No local sightings" for child in empty.winfo_children())
    assert toolbar.winfo_manager() == "pack"
    assert footer.winfo_manager() == "pack"
    assert table.item(table.get_children()[0])["values"] == ["12:42", "4-HWWF"]
    table_frame.destroy()
