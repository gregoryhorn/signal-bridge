# Signal Bridge Project Map

Signal Bridge is currently shipped from the Python/Tk source tree in this repository. A separate Tauri/Rust/SolidJS v3 tree exists as a future/reference architecture, but it is not the currently shipped app.

## Current live app

- Main app / Tk shell: `signal_bridge_gui.py`
- Current public release: **v0.7** (`APP_VERSION` 0.7; portable ZIP on GitHub Releases)
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
  -> sb_monitor.MonitorThread
  -> parse_rows_from_text
  -> extract_intel / build_intel_segments
  -> ESI/cache enrichment queue
  -> translation (sb_translation detect + free path)
  -> sb_feed_admit (filters + spam)
  -> build_render_row (sb_contracts)
  -> Tk feed / diagnostics / Intel History (AddonEvent)
```

## Module map

| Area | Location | Notes |
|---|---|---|
| App entry / Tk shell | `signal_bridge_gui.py` | Wiring only for new work; still holds ESI/catalog/cache |
| Paths | `sb_paths.py` | Portable dirs; `DEFAULT_DB_PATH = data/translations.db` |
| Diagnostics | `sb_diagnostics.py` | JSONL + redaction bridge |
| Contracts | `sb_contracts/` | RenderRow, IntelSegment, TranslationDecision, AddonEvent, etc. |
| Channels | `sb_channels.py` | Discover + persisted catalog merge |
| Monitor | `sb_monitor.py` | Live tail, optional backlog, bounded dedupe |
| Translation detect / Google | `sb_translation/` | Pure detect + network edge |
| Filters / spam / admit | `sb_filters.py`, `sb_spam.py`, `sb_feed_admit.py` | Settings > Filters |
| Highlight | `sb_highlight.py` | Ship vs module kind |
| Appearance defaults | `sb_appearance.py` | `highlight_modules` default off |
| Text helpers | `sb_text.py` | Strip/truncate without mojibake |
| Render helpers | `signal_bridge_render_model.py` | Pure visible lines |
| Settings store | `sb_settings.py` | Typed `SettingsStore` |
| UI foundation | `sb_ui/*` | theme, components, windows, settings shell, filters page, **pilot_info** card |
| Intel History | `addons/intel-history` | Optional add-on, fail-isolated |
| Help | `sb_help.py` + `docs/help/` | Offline topics (10), including Filters |
| Contracts docs | `docs/contracts/` | Specs; runtime under `sb_contracts/` |
| EVE phrase promotions | `data/eve_phrase_promotions.json` + `scripts/promote_eve_translations.py` | Promote durable EVE fixes; purge machine cache |
| zKill helpers | `sb_zkill.py` | Ranking pure helpers |
| Tests | `tests/` | pytest; pure modules + Tk widgets + settings page smoke |

## Standard validation commands

```powershell
python -X utf8 -m py_compile signal_bridge_gui.py sb_paths.py sb_diagnostics.py sb_channels.py sb_monitor.py
python -X utf8 -m compileall sb_contracts sb_translation
python -X utf8 scripts/check-fixtures.py
python -m pytest tests/ -v
```

These commands should stay fast, offline, and deterministic.
