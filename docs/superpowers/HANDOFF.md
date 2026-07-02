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
| 2.3 — Pilot Info card + zKill usefulness (last open P1) | 📋 plan written, **uncommitted**, execution not started | `2026-07-03-phase2.3-pilot-info-zkill.md` | — |
| 2.4 — Help menu + About/Support | not planned yet | write via superpowers:writing-plans | — |
| 2.5 — Remaining dialogs (Appearance, ESI exclusion list, channel picker, alias editor) onto foundation | not planned yet | — | — |
| 3.x — Functional issues (cache data model P1, language auto-detect, filters, spam limiting, backlog ingest, highlight fixes) | scoped in roadmap only | — | — |

## Immediate next steps (in order)

1. **Commit the Phase 2.3 plan file** (`docs/superpowers/plans/2026-07-03-phase2.3-pilot-info-zkill.md` is written in the working tree but uncommitted; this HANDOFF.md is also uncommitted).
2. **Execute Phase 2.3** per its "Execution assignment" section:
   - Task 1 (`sb_zkill.py` pure ranking + tests) → Codex or Sonnet subagent. Handoff prompt: *"Execute Task 1 from `docs/superpowers/plans/2026-07-03-phase2.3-pilot-info-zkill.md`. Create only `sb_zkill.py` and `tests/test_zkill_rank.py`; do not touch any other file. TDD order as written; interfaces verbatim. Commit with the plan's message. Report commit hash and test count (34 expected)."*
   - Task 2 (sync enrichment, 3 small located edits in `signal_bridge_gui.py`) → Sonnet subagent, then review the diff.
   - Task 3 (card layout surgery + rebuilt zKill section) → strongest available model; verify with the automated screenshot method (below).
   - Task 4 (ISSUES/CHANGELOG closure) → Haiku subagent.
3. After 2.3: write the 2.4 plan (Help/About) via superpowers:writing-plans, consuming `SettingsShell`/`sb_ui` patterns.

## Working agreements (owner's explicit preferences)

- **Cost split:** Codex or cheap subagents (Sonnet/Haiku) execute well-specified plan tasks; the expensive model does monolith surgery, plan writing, and reviews every delegated commit before proceeding.
- **Unsupervised mode:** owner authorized autonomous progress; stop only for Codex handoffs or genuine blockers. Commits of code the owner hasn't asked to pause are fine; when the owner says "pause", stop cleanly and summarize.
- One commit per plan task, using the plan's commit message, `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.
- Review discipline: after any delegated task, independently re-run the gates and read the diff before dispatching the next task (a Codex omission — missing mouse-wheel binding — was caught this way in 2.1).

## Validation gates (run after every task)

```powershell
python -m py_compile signal_bridge_gui.py     # exit 0
python scripts/check-fixtures.py              # "Fixture check OK: 6 case(s)"
python -m pytest tests/ -q                    # 29 passing as of ec3f724; 34 after 2.3 Task 1
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
