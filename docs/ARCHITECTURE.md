# Signal Bridge Architecture

## Current architecture

The current live app is a Python/Tk Windows app. `signal_bridge_gui.py` is the Tk wiring shell; subsystem logic lives in focused modules so features do not require editing a single god file.

It monitors EVE chatlog files, parses chat rows, performs local EVE entity recognition, optionally uses ESI/cache enrichment, renders a compact feed, and loads the optional Intel History add-on.

### Module map (v0.7 direction)

| Module | Responsibility |
|---|---|
| `sb_paths.py` | Portable app/user dirs, `DEFAULT_DB_PATH` |
| `sb_diagnostics.py` | Logs, JSONL events (secret redaction via contracts) |
| `sb_contracts/` | Pure contracts: RenderRow, IntelSegment, TranslationDecision, AddonEvent, diagnostics redaction |
| `sb_channels.py` | Channel discover + catalog status merge |
| `sb_monitor.py` | Live monitor, backlog window, bounded dedupe |
| `sb_translation/` | Language detect + Google free edge |
| `sb_filters.py` / `sb_spam.py` / `sb_feed_admit.py` | Feed filters + spam policy + single admit path |
| `sb_highlight.py` | Ship vs module highlight kind |
| `sb_appearance.py` | Appearance defaults (`highlight_modules` off by default) |
| `sb_text.py` | Normalize/strip/truncate (no mojibake) |
| `sb_ui/` | Theme, components, settings shell, filters page |

**Rule:** library modules must not import `signal_bridge_gui`.

## UI foundation (Phase 1, 2026-07)

New shared UI infrastructure that all dialog/page work must build on:

- `sb_ui/theme.py`: every color/font constant. No hex literals in new widget code.
- `sb_ui/components.py`: `card`, `action_row`, `action_button`, `primary_button`, `check`, `info_label`, `balanced_paned`. New pages compose these instead of hand-rolling per-dialog closures.
- `sb_ui/windows.py`: `polish_window` (chrome/stacking) and `fit_to_content` (content-driven sizing clamped to min/max/screen). New dialogs must not hardcode a fixed width/height without a reason.
- `sb_settings.py`: `SettingsStore` — typed schema, validation warnings, atomic non-silent saves. Main settings use it; ESI settings/tokens migrate in Phase 2.
- `tests/`: pytest suite covering the above with real Tk widgets. Run `pytest tests/ -v`.

Overhaul roadmap: `docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md`.

## Target architecture direction

```text
RawChatRow
  -> ParsedRow
  -> IntelSegment[]
  -> EntityResolution / TranslationDecision
  -> RenderRow
  -> UI feed / LAN viewer / diagnostics / add-ons
```

The UI should draw `RenderRow`-like prepared data. Parsing, translation, ESI, zKill, Argos, catalog updates, and heavy SQLite work should live outside the render path.

## Current key contracts

- `Row`: current row object used by the Tk app
- `IntelSegment`: structured event pieces extracted from a row
- Diagnostics JSONL events: machine-readable status/error/stall records

These will gradually evolve toward explicit contracts documented in `docs/contracts/`.

## Render safety

Rendering must be fast and predictable. Current safeguards include:

- feed display uses precomputed `row.free_translation` only
- direct Argos is disabled
- `_render_row` no longer hydrates ESI
- diagnostics record slow redraw/queue/stall events

Next recommended safety steps:

- build explicit `RenderRow` objects
- chunk/cancel large redraws
- store explicit render spans for right-click targeting
- keep all background jobs bounded with timeout/circuit breaker state

## Diagnostics architecture

Diagnostics use JSONL logs under `logs/`:

- `events.jsonl`
- `errors.jsonl`
- `stalls.jsonl`
- `jobs.jsonl`
- `signal_bridge.log`

Settings > Diagnostics should remain the user-facing summary. Future diagnostic bundles should redact secrets and raw chat by default.

## Future Tauri/Rust v3 boundary

The Tauri/Rust/SolidJS v3 tree is a future/reference architecture, not the current shipped app. Shared contracts should be documented first, then mirrored into TypeScript/Rust later.
