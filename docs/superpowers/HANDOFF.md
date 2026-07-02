# Signal Bridge UI Overhaul — Session Handoff

**Written:** 2026-07-03
**Repo:** `d:\AI\Rift\signal-bridge-live-gui` (branch `main`)
**For:** any agent (Claude session, Codex, or subagent) or human resuming this work.

## What this project is doing

Executing a phased UI overhaul of the Tkinter monolith `signal_bridge_gui.py` per the approved roadmap:
`docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md`. Direction decided by the owner: keep Python/Tkinter, rebuild the UI foundation properly (no web/Tauri migration); foundation first, then per-batch dialog rebuilds, then functional issues.

## Status by phase

| Phase | Status | Plan file | Closing commits |
|---|---|---|---|
| 1 — UI foundation (`sb_ui/` theme/components/windows, `sb_settings.py`, pytest suite, sash P1 fix) | ✅ complete | `2026-07-02-phase1-ui-foundation.md` | `bb9a52d` |
| 2.1 — Settings Center shell rebuild (SettingsShell, 13 pages → `_render_settings_*` methods, save failures surfaced) | ✅ complete | `2026-07-03-phase2.1-settings-shell.md` | `5361df6` |
| 2.2 — Translation Corrections single-table redesign | ✅ complete | `2026-07-03-phase2.2-translation-corrections.md` | `ec3f724` |
| 2.3 — Pilot Info card + zKill usefulness (last open P1) | ✅ complete (final review: ready to merge) | `2026-07-03-phase2.3-pilot-info-zkill.md` | `40a8a5b`, `35a6048`, `f34fb48`, `d59a89a` |
| 2.4 — Help menu + About/Support | ✅ complete (final review: ready to merge, fix applied) | `2026-07-03-phase2.4-help-about.md` (spec: `specs/2026-07-03-help-about-design.md`) | Codex: `8c31cb2`, `8f5431e`, `8f28f20`, `0483784`, `322f6df`, `29dbe09`; review fixes: `781634a`, `f6695ef` |
| 2.5 — Remaining dialogs (Appearance, Recognition Rules, channel picker, hidden tabs) onto foundation | 📋 plan committed (`4edc878`), 3-commit Codex batch handed to owner, not yet executed | `2026-07-03-phase2.5-dialog-migration.md` | — |
| 3.x — Functional issues (cache data model P1, language auto-detect, filters, spam limiting, backlog ingest, highlight fixes) | scoped in roadmap only | — | — |

## Execution model (owner directive, 2026-07-03 — supersedes earlier cost split)

**ALL repo changes are made by Codex.** Claude's role is: write specs/plans/dispatch prompts, review every Codex commit (re-run gates, read the diff against the plan, screenshot-verify UI work), and turn review findings into NEW Codex fix prompts — Claude does not edit the repo directly, including for small fixes. Dispatch prompts live in per-phase dispatch/plan files (pattern: `2026-07-03-phase2.4-codex-dispatch.md`, and the prompts embedded in the 2.5 plan). One commit per plan task, plan's commit message.

**Codex lesson (hit in 2.4):** Codex double-encodes non-ASCII output (bullets/em-dashes became mojibake in 8 files). Every dispatch prompt must include the byte-check:
`python -c "t=open('<file>',encoding='utf-8').read(); print(t.count(chr(0xE2)))"` — for `signal_bridge_gui.py` the pre-existing count is 13 and must not change; new files must be 0. Regression tests now pin this for help docs (`test_docs_contain_no_mojibake`) and the bullet glyph.

## Immediate next steps (in order)

1. **Owner pastes the Phase 2.5 batch prompt into Codex** (three commits; the prompt is in the Claude session log and reconstructible from `2026-07-03-phase2.5-dialog-migration.md` — plan tasks 1-3 plus the encoding byte-check and deviation-reporting rules).
   ⚠️ Codex must start from `f6695ef` or later — commit `f6695ef` touched `show_esi_exclusion_list`, which 2.5 Task 2 also edits.
2. **Claude reviews** per the plan's reviewer protocol: one commit per task, gates (49 tests), style-only diffs, mojibake count still 13, then a screenshot pass over all four dialogs.
3. Then plan Phase 3 batches (functional issues) — Claude writes the plans, Codex executes.

Open follow-ups (owner to prioritize): pre-existing monolith mojibake (new ISSUES.md "Code health" entry, low); About card-note clips at forced 500x440 minimum (cosmetic, fix = wraplength on `card()` note); markdown link regex includes trailing punctuation if help prose ever puts `.`/`)` right after a URL (no live case); untracked icon PNG still undecided.

Phase 2.3 notes: executed 2026-07-03 via subagent-driven development (ledger: `.superpowers/sdd/progress.md`, git-ignored). One approved deviation from the plan's Task 3 snippet: `canvas.configure(height=body.winfo_reqheight())` before `fit_to_content`, because a Canvas never propagates its child's requested height — without it the card always clamped to the 520 min. Deferred cosmetic minors (final review triage): bare `list` type hints in `sb_zkill.py`; duplicate `int()` cast in `zkill_event_row` (optional cleanup: expose `sb_zkill.participants()` and reuse); unused `width` unpack in the autosize block; loss rows' gang label shows the killing fleet's size, which reads ambiguously ("[large fleet]" on a loss = died to a blob) — possible future wording polish.

## Working agreements (owner's explicit preferences)

- **Execution model above is binding:** Codex makes all changes; Claude plans and reviews only (owner corrected Claude for directly committing review fixes in 2.4 — do not repeat).
- **Unsupervised mode:** owner authorized autonomous planning/review progress; stop for Codex handoffs (owner pastes prompts) or genuine blockers; when the owner says "pause"/"stop", stop cleanly and summarize.
- One commit per plan task, using the plan's commit message, `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.
- Review discipline: after every Codex task, independently re-run the gates and read the diff before clearing the next dispatch (caught in this mode: missing mouse-wheel binding in 2.1; double-encoded UTF-8 across 8 files in 2.4; modal-grab freeze on the 2.4 "?" deep link via the final whole-phase review).

## Validation gates (run after every task)

```powershell
python -m py_compile signal_bridge_gui.py     # exit 0
python scripts/check-fixtures.py              # "Fixture check OK: 6 case(s)"
python -m pytest tests/ -q                    # 49 passing as of f6695ef
```

## Automated visual verification (replaces "run the app and look")

Proven pattern (used to verify 2.1/2.2; script kept at the session scratchpad, easy to recreate):
`SignalBridgeGui()` builds the entire UI in `__init__` **without** starting threads/mainloop — only `.run()` does that. So: instantiate the app, call the dialog method under test, drive it (`btn.invoke()`, `win.update()`), screenshot the Toplevel via PIL `ImageGrab.grab(bbox=win.winfo_rootx()/rooty()/width/height)` (call `SetProcessDPIAware` first), then read the PNGs. For Pilot Info, seed data first: `app.set_zkill_summary(pid, {...synthetic synced summary...})` and pass a synthetic `profile` dict to `show_pilot_info_card`.

## Architecture facts a fresh agent needs

- `signal_bridge_gui.py` (~7,4xx lines): business logic (parsing/translation/ESI/threads) lives above ~line 3200 and is healthy — do not refactor it. UI = `SignalBridgeGui` class. Settings pages are `_render_settings_*(self, body, shell)` methods (~line 4346+) rendered by `SettingsShell`.
- Foundation modules (all tested): `sb_ui/theme.py` (colors/fonts/ttk styles — never hardcode hex in new code), `sb_ui/components.py` (`card`, `action_row`, `action_button`, `primary_button`, `check`, `info_label`, `balanced_paned`, `preview_table`), `sb_ui/windows.py` (`polish_window`, `fit_to_content`), `sb_ui/settings_center.py` (`SettingsShell`), `sb_settings.py` (`SettingsStore`).
- Gotcha: `SETTINGS = load_settings()` runs at import time BEFORE `write_log` is defined — `_settings_log` resolves it lazily via `globals().get`. Don't "simplify" that.
- Gotcha: Tk pack order = clip priority. Footers/action bars must be packed BEFORE the expanding body (`side="bottom"` early). This was the root cause of the Pilot Info hidden-buttons P1 (2.3 Task 3 fixes it).
- `docs/INVARIANTS.md` is binding: no network/MT/ESI in render paths, UI thread never blocks, zKill/ESI work stays in worker threads, portable ZIP stays stdlib-light.
- `ISSUES.md` is the public bug tracker — update statuses when fixing; P1 UI fixes require before/after visual verification (automated screenshots acceptable, note it in the fix summary).
- `CHANGELOG.md` has an `## Unreleased` section — append user-facing bullets there.
- pytest is dev-only; never add runtime deps or touch `SignalBridge.spec` excludes.

## Untracked/local files (intentional, do not commit)

`assets/signal_bridge_icon_true_transparent_1024.png` (owner's asset, undecided), `modules/`, `runtime/`, `data/*_backup_*.json`, `build_portable_*.log` (all gitignored since `fcfef5e`), session scratchpad scripts/screenshots (outside repo).

## Release checkpoint

After Phase 2 batches complete: candidate **v0.6** — refresh README screenshots, CHANGELOG version heading, ISSUES statuses, rebuild portable ZIP via `build_portable.ps1` (it must copy the new `sb_ui/`/`sb_*.py` modules — PyInstaller picks them up as imports automatically, but VERIFY the built exe opens Settings before publishing), publish `.sha256`.
