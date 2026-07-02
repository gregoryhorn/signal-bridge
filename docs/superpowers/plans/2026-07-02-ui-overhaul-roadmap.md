# Signal Bridge UI Overhaul & Issue-Fix Roadmap

**Date:** 2026-07-02
**Status:** Approved direction — rebuild UI foundation in Tkinter, phased execution
**Decision record:** User chose (a) keep Python/Tkinter stack, rebuild the UI foundation properly; (b) phased plans: foundation first, then issue batches. A web/Tauri migration remains a future v3 direction only (see `docs/ARCHITECTURE.md`).

## Why this roadmap exists

An investigation on 2026-07-02 found the business logic (parsing, translation, ESI, threading) is sound, but the UI layer has structural debt that causes the recurring bugs logged in `ISSUES.md`:

1. **No shared layout/style system** — colors/fonts/pixel constants copy-pasted inline hundreds of times (e.g. `#0b0f14` in nearly every widget constructor).
2. **God object** — `SignalBridgeGui` (`signal_bridge_gui.py:3205-7740`, ~4,535 lines) contains all UI construction; the 13 Settings pages are near-identical nested closures inside one 497-line method (`show_settings_center`, line 4387).
3. **Geometry-timing bug pattern** — e.g. `signal_bridge_gui.py:4538` reads `winfo_width()` in `after_idle` before layout settles and never rebinds `<Configure>` → the squeezed Translation Corrections columns.
4. **Fixed dialog sizes vs variable content** — Settings hardcoded at 860x620 for 13 pages of wildly different density → hidden buttons / wrong sizing bugs.
5. **Three hand-rolled JSON settings stores** with no schema/validation and silent `except Exception: pass` on load AND save (`signal_bridge_gui.py:105-156`, ESI settings/tokens near lines 1475-1520).
6. **Zero UI test coverage** — only `scripts/check-fixtures.py` (text formatting via a stubbed object); every layout fix relies on manual visual inspection.

Fixing issues one-by-one inside this structure keeps producing regressions. Therefore: build the foundation first (Phase 1), rebuild the problem dialogs on it (Phase 2), then land functional features/fixes (Phase 3).

## How to execute this roadmap (instructions for the coordinating agent)

- **Phase 1 plan is written and ready:** `docs/superpowers/plans/2026-07-02-phase1-ui-foundation.md`. Execute it with `superpowers:subagent-driven-development` (fresh subagent per task) or `superpowers:executing-plans`.
- **Phase 2 and Phase 3 detailed plans are generated AFTER Phase 1 merges**, using the `superpowers:writing-plans` skill, one plan per batch listed below. Each plan must consume the exact interfaces Phase 1 delivered (import from `sb_ui/`, `SettingsStore`), and must include the "visual inspection before/after" steps that `ISSUES.md` requires for P1 UI bugs.
- Tasks within a phase are sequential unless marked parallel-safe. Phases are strictly sequential.
- Standard validation for every task: `python -m py_compile signal_bridge_gui.py`, `python scripts/check-fixtures.py`, `pytest tests/ -v` (pytest infra added in Phase 1), plus manual app launch (`python -X utf8 signal_bridge_gui.py`) for anything touching visible UI.
- Update `ISSUES.md` status lines when an issue is fixed (this repo uses it as the public tracker) and add entries to `CHANGELOG.md` under the next version heading.
- **Invariants:** every task must respect `docs/INVARIANTS.md` (no blocking the Tk thread, no network/MT in render path, ESI cache-first, add-ons fail isolated, portable ZIP stays lightweight).

## Phase 1 — UI foundation & safety nets (plan ready)

Plan file: `docs/superpowers/plans/2026-07-02-phase1-ui-foundation.md`

| Task | Deliverable |
|---|---|
| 1.0 | Repo hygiene: `.gitignore` entries for `modules/`, `runtime/`, `data/*_backup_*.json`, `build_portable_*.log`; pytest dev dependency documented |
| 1.1 | `sb_ui/theme.py` — central colors/fonts/spacing + style-kwarg helpers (single source for every hex literal currently copy-pasted) |
| 1.2 | `sb_ui/components.py` — reusable `card/action_row/action_button/check/info_label` builders + `balanced_paned` (a `PanedWindow` whose sash tracks a fraction via `<Configure>` binding until the user drags it — the permanent fix for the geometry-timing bug class) |
| 1.3 | `sb_ui/windows.py` — `polish_window` extracted from the God class + `fit_to_content` (content-driven window sizing clamped to min/max/screen — the permanent fix for the fixed-size-vs-content bug class) |
| 1.4 | `sb_settings.py` — `SettingsStore` with typed schema, per-key validation/coercion, warning log instead of silent swallow, atomic save that reports failure; main settings wired through it |
| 1.5 | UI test harness: pytest + `tests/test_theme.py`, `tests/test_components.py`, `tests/test_windows.py`, `tests/test_settings_store.py` (real Tk widgets, skip-if-no-display guard) |
| 1.6 | First integration: `SignalBridgeGui.polish_window` delegates to `sb_ui.windows`; Translation Corrections sash bug (`signal_bridge_gui.py:4530-4538`) replaced with `balanced_paned` at 50/50 — closes the open P1 "Translation Corrections layout" issue |

## Phase 2 — Rebuild dialogs/pages on the foundation (plans to be written after Phase 1)

Each batch below becomes one plan file `docs/superpowers/plans/YYYY-MM-DD-phase2-<batch>.md`.

| Batch | Scope | Closes ISSUES.md items |
|---|---|---|
| 2.1 Settings shell | Extract `show_settings_center` into `sb_ui/settings_center.py`: nav + scroll + footer shell using components; per-page render functions become small modules/functions; `fit_to_content` sizing policy per page; surface `SettingsStore` load warnings and save failures in the UI (status bar / dialog) | "Dedicated settings tab and sub-page design pass" (open, medium); "Translation Cache page layout hides controls" (open P1 — layout half) |
| 2.2 Translation Corrections page | Rebuild the corrections editor on components: balanced Original/English panes, editor visually primary, advanced internals behind toggle, before/after visual inspection | "Translation Corrections layout gives too much width to Original" (open P1) — Phase 1.6 patches the sash; this batch finishes the design |
| 2.3 Pilot Info card | Redesign `show_pilot_info_card` (~365 lines) as `sb_ui/pilot_info.py`: `fit_to_content` auto-sizing so footer buttons are always visible; zKill section shows capped lists of recent kills and recent losses, each linked, kills ranked to prefer small-gang (de-prioritize >10 participants), labels `solo/small gang/fleet/large fleet`; fallback to large killmails when few small ones exist | "Pilot Info card layout and zKill usefulness" (open P1); "Pilot Info card size still incorrect on load" (open, medium); the committed "Pilot Info zKill layout issue" (073e2c4) |
| 2.4 Help & About/Support | New Help menu window (setup, chatlog folder, channels, translation modes, aliases, recognition rules, Pilot Info, Intel History, diagnostics; offline-readable from portable ZIP) + dedicated About/Support section (version, links, issue-report, diagnostics copy, support info); extend the inline-help pattern started with Recognition Rules | "Help menu needs a proper help system" (open, medium); "About and Support need a dedicated menu" (open, medium) |
| 2.5 Remaining dialogs | Migrate `show_appearance_dialog` (~222 lines), `show_esi_exclusion_list` (~169 lines), channel picker, alias editor onto theme/components; delete then-dead inline style literals | consistency follow-through; no direct issue |

## Phase 3 — Functional issues & features (plans to be written after Phase 2 starts; 3.x batches are parallel-safe with each other except where noted)

| Batch | Scope | Closes ISSUES.md items |
|---|---|---|
| 3.1 Translation cache data model | Design review first (ISSUES.md demands it): central `should_cache_translation_source()` gate — reject English-only/URL-only/entity-only sources for Auto→EN, allow EN source only for explicit EN→CN; cleanup/dedupe migration for polluted rows preserving manual overrides; before/after visual inspection of the cache UI | "Translation Cache still contains English in Original and English fields" (open P1) |
| 3.2 Language auto-detect | Google default engine translates any detected non-English (e.g. Russian) → EN, not only Chinese; keep protected EVE terms; skip pure-English lines; background-only per invariants | "Google default translation should auto-detect all non-English languages" (open, high) |
| 3.3 Content/sender filters | New Settings page (built on 2.1 shell): keyword + sender filters, per-filter enable, case-insensitive default, persisted, diagnostics counts | "Add content and sender filter/block settings" (open, high) |
| 3.4 Spam/rate limiting | Per-channel (esp. Local) rate limiting, repeat-sender suppression window, ASCII-art/symbol-heavy detection, optional burst-collapse row, tunable in Settings, diagnostics counts. Depends on 3.3's filter plumbing | "Add local-channel spam and ASCII-art rate limiting" (open, high) |
| 3.5 Backlog ingest | Settings option (default off): startup backlog window default 10 min, manual override up to hours; dedupe still applies; live monitoring continues after ingest | "Backlog chat ingest option" (open, medium) |
| 3.6 First-render classification | Fix first-load ordering so ships (Retribution, Caracal) never render with asset/module color before catalog hydration; reproduce on clean portable profile first | "Ships initially highlighted purple on first load" (open, medium) |
| 3.7 Highlight default | Purple non-ship asset/module highlighting off by default for fresh installs; toggle stays in Appearance; existing users keep their preference | "Purple asset/module highlighting should be off by default" (open, medium) |

## Release checkpoints

- After Phase 1: internal build only; run full manual smoke of Settings + feed.
- After Phase 2: candidate **v0.6** (UI overhaul release) — update README screenshots, CHANGELOG, ISSUES.md statuses, rebuild portable ZIP via `build_portable.ps1`, publish checksum.
- After Phase 3: candidate **v0.7** (feature/hygiene release).

## Out of scope (explicitly)

- Web/Tauri/v3 migration.
- Refactoring business-logic modules (`EveCatalog`, `TranslationCache` internals beyond 3.1's gate, `EsiResolver`, `MonitorThread`) — they work; leave them.
- Bundling Argos/ML dependencies (see `docs/INVARIANTS.md` packaging rules).
