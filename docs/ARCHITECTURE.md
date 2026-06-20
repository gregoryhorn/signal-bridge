# Signal Bridge Architecture

## Current architecture

The current live app is a Python/Tk Windows app centered around `signal_bridge_gui.py`. It monitors EVE chatlog files, parses chat rows, performs local EVE entity recognition, optionally uses ESI/cache enrichment, renders a compact feed, and loads the optional Intel History add-on.

The app has grown feature-rich, so the architectural goal is now separation of concerns and UI safety rather than adding more features directly into the GUI path.

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
