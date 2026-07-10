# Signal Bridge Architecture

## Current architecture

The current live app is a Python/Tk Windows app. `signal_bridge_gui.py` is the **Tk wiring shell**; subsystem logic lives in focused modules so features do not require editing a single god file for every change.

It monitors EVE chatlog files, parses chat rows, performs local EVE entity recognition, optionally uses ESI/cache enrichment, renders a compact feed, and loads the optional Intel History add-on.

### Module map

| Module | Responsibility |
|---|---|
| `sb_paths.py` | Portable app/user dirs, `DEFAULT_DB_PATH` under `data/` |
| `sb_diagnostics.py` | Logs, JSONL events (secret redaction via contracts) |
| `sb_contracts/` | Pure contracts: RenderRow, IntelSegment, TranslationDecision, AddonEvent, PilotInfoSnapshot, diagnostics redaction |
| `sb_channels.py` | Channel discover + persisted catalog status merge |
| `sb_monitor.py` | Live monitor, optional backlog window, bounded dedupe |
| `sb_translation/` | Language detect + Google free edge |
| `sb_filters.py` / `sb_spam.py` / `sb_feed_admit.py` | Feed filters + spam policy + single admit path |
| `sb_highlight.py` | Ship vs module highlight kind |
| `sb_appearance.py` | Appearance defaults (`highlight_modules` off by default) |
| `sb_text.py` | Normalize/strip/truncate (no mojibake) |
| `sb_settings.py` | Typed `SettingsStore` |
| `sb_help.py` | Offline help topic manifest + loader |
| `sb_zkill.py` | zKill ranking helpers |
| `sb_ui/` | Theme, components (`card`, `danger_card`, `labeled_spinbox`, …), windows, settings shell, filters page |
| `signal_bridge_render_model.py` | Pure visible-line helpers for feed display |
| `signal_bridge_gui.py` | Tk app lifecycle, remaining ESI/catalog/cache, Settings page methods |

**Rule:** library modules must not import `signal_bridge_gui`.

Still concentrated in the GUI module (extract when next touched): full `EveCatalog` / `EsiResolver` / `TranslationCache` classes and chat parse pipeline.

## UI foundation

Shared UI infrastructure:

- `sb_ui/theme.py`: every color/font constant. No hex literals in new widget code.
- `sb_ui/components.py`: `card`, `danger_card`, `action_row`, `action_button`, `primary_button`, `check`, `info_label`, `labeled_spinbox`, `balanced_paned`, `preview_table`.
- `sb_ui/windows.py`: `polish_window`, `fit_to_content`.
- `sb_ui/settings_center.py`: SettingsShell (nav + scroll body + fixed footer).
- `sb_settings.py`: typed schema, validation warnings, atomic non-silent saves.
- `tests/`: pytest for pure modules and real Tk widgets. Run `pytest tests/ -v`.

Plans: `docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md`, `docs/superpowers/plans/2026-07-10-contracts-and-backlog.md` (implemented on `feature/contracts-and-backlog`).

## Data flow

```text
EVE chatlog file
  -> sb_monitor.MonitorThread (optional backlog, then live tail)
  -> parse_rows_from_text / extract_intel / segments
  -> queue to UI
  -> sb_feed_admit (filters + spam)
  -> ESI queue / translation worker (background)
  -> build_render_row (sb_contracts) + _render_row
  -> Tk feed / diagnostics / AddonEvent -> Intel History
```

## Contracts

Documented under `docs/contracts/`. **Runtime implementations** live in `sb_contracts/`:

| Contract | Module | Status |
|---|---|---|
| IntelSegment | `sb_contracts/intel_segment.py` | Implemented (legacy `Row.segments` still used) |
| TranslationDecision | `sb_contracts/translation_decision.py` | Implemented; attached off render path |
| RenderRow | `sb_contracts/render_row.py` | Implemented; feed builds RenderRow (`spans` still empty) |
| DiagnosticEvent redaction | `sb_contracts/diagnostic_event.py` | Implemented via diagnostics write path |
| AddonEvent | `sb_contracts/addon_event.py` | Implemented (`row_to_addon_event`) |
| PilotInfoSnapshot | `sb_contracts/pilot_info_snapshot.py` | Empty snapshot helper; card still uses mixed sources |

## Render safety

- Feed display uses precomputed `row.free_translation` / RenderRow visible lines only on the UI thread.
- Direct Argos is disabled in-process.
- `_render_row` does not hydrate ESI or call network/MT.
- Diagnostics record slow redraw/queue/stall events.
- Atomic redraw for normal feed sizes; chunked redraw for very large feeds.

Remaining: explicit click `spans` on RenderRow; further ESI/catalog extraction.

## Diagnostics architecture

JSONL under `logs/`: `events.jsonl`, `errors.jsonl`, `stalls.jsonl`, `jobs.jsonl`, `signal_bridge.log`.

Secret-like keys are redacted on write (`sb_contracts.diagnostic_event.redact_context`). Settings > Diagnostics is the user-facing summary.

## Future Tauri/Rust v3 boundary

The Tauri/Rust/SolidJS v3 tree is a future/reference architecture, not the current shipped app. Shared contracts should stay documented first, then mirrored into TypeScript/Rust later.
