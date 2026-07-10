# Signal Bridge - Handoff

**Updated:** 2026-07-10  
**Repo:** `D:\AI\Rift\signal-bridge-live-gui`  
**Branch:** `feature/contracts-and-backlog`  
**PR:** https://github.com/gregoryhorn/signal-bridge/pull/1  
**Public release:** still **v0.6** (`APP_VERSION` unchanged until packaging)

## Current state

Merge candidate is **ready**. Implementation (contracts, modular backlog, Settings design pass, Pilot Info redesign, EVE phrase promotions, icon) is on the feature branch. Docs and `docs/superpowers/MERGE_PREP.md` describe the merge.

- Do **not** bump `APP_VERSION` on merge.
- Public GitHub download remains v0.6 until a deliberate packaging cut.

## Pre-merge validation (last run)

```powershell
python -X utf8 -m py_compile signal_bridge_gui.py sb_paths.py sb_diagnostics.py sb_channels.py sb_monitor.py sb_filters.py sb_spam.py sb_feed_admit.py sb_highlight.py sb_appearance.py sb_text.py
python -X utf8 -m compileall -q sb_contracts sb_translation sb_ui
python -X utf8 scripts/check-fixtures.py
python -m pytest tests/ -q
```

Results:

- compile / compileall: OK  
- fixtures: `Fixture check OK: 6 case(s)`  
- pytest: **114 passed**  
- `APP_VERSION`: **0.6**

## Merge steps

See `docs/superpowers/MERGE_PREP.md`.

```powershell
gh pr merge 1 --merge   # or --squash
git checkout main
git pull origin main
```

## After merge (packaging only)

1. Bump `APP_VERSION` in `signal_bridge_gui.py`  
2. Move CHANGELOG Unreleased under a dated version heading  
3. Update `GITHUB_RELEASE.md` + README download links  
4. `build_portable.ps1` with current `assets/signal_bridge_icon.ico`  
5. Bundle `docs/help/` (10 topics), `data/phrase_overrides.json`, `data/eve_phrase_promotions.json`  
6. Publish ZIP + SHA256  

## Out of scope for this merge

- APP_VERSION / GitHub release asset cut  
- Full ESI / free-text extract from GUI  
- LAN viewer / Argos helper process  
