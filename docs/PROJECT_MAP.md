# Signal Bridge Project Map

Signal Bridge is currently shipped from the Python/Tk source tree in this repository. A separate Tauri/Rust/SolidJS v3 tree exists as a future/reference architecture, but it is not the currently shipped app.

## Current live app

- Main app: `signal_bridge_gui.py`
- Current release line: `v0.3`
- Portable packaging: PyInstaller-based Windows ZIP scripts/docs in this repo
- Runtime logs: `logs/`
- Local runtime add-ons: `modules/` (not committed)
- Bundled add-ons/source packages: `addons/`
- Bundled data: `data/`

## Future/reference architecture

- Reference tree: `D:\AI\Rift\signal-bridge-v2\signal-bridge-v3`
- Status: future/reference architecture, not current shipped app
- Useful concepts to mirror later: contracts, diagnostics, modules, monitor, translation, settings, CI

## High-level data flow

```text
EVE chatlog file
  -> monitor thread
  -> parse_rows_from_text
  -> extract_intel / build_intel_segments
  -> ESI/cache enrichment queue
  -> translation/cache decision
  -> render display lines
  -> Tk feed / diagnostics / Intel History
```

## Important current areas

| Area | Current location | Notes |
|---|---|---|
| App entry | `signal_bridge_gui.py::main` | Starts Tk GUI or self-test |
| Live monitor | `MonitorThread` in `signal_bridge_gui.py` | Live-only by default; no startup backfill |
| Chat parsing | `parse_rows_from_text` | Builds `Row` records |
| Intel/entity recognition | `extract_intel`, catalog helpers | Uses compact catalog/cache; avoid large DB in live path |
| Segmentation | `IntelSegment`, `build_intel_segments` | Internal-first model; only multi-segment rows split visually |
| Rendering | `_render_row`, `row_display_parts` | Must stay fast/render-only |
| Diagnostics | `record_event`, JSONL logs, Settings > Diagnostics | Black-box recorder for stalls/errors/decisions |
| ESI | ESI cache/resolver classes and UI settings | Cache-first/background-only |
| Translation | Translation cache, Google safe paths, Argos disabled | Render path must not run MT/network |
| Intel History | `addons/intel-history` | Optional add-on loaded in-process with guarded API |
| Packaging | packaging docs/scripts | Portable Windows ZIP, no admin/dev tools |

## Standard validation commands

```powershell
python -X utf8 -m py_compile signal_bridge_gui.py addons/intel-history/intel_history.py
python -X utf8 scripts/check-fixtures.py
```

These commands should stay fast, offline, and deterministic.
