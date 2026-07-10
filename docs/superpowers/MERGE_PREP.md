# Merge prep — feature/contracts-and-backlog → main

**Status:** MERGED + v0.6 published (2026-07-10)  
**PR:** https://github.com/gregoryhorn/signal-bridge/pull/1  
**Branch:** `feature/contracts-and-backlog`  
**Base:** `main`

## Scope summary

Modular contracts + backlog product work + Settings design pass + Pilot Info redesign + EVE phrase promotion tooling. **APP_VERSION remains 0.6** until a deliberate packaging cut.

### Product

- Settings Filters + Local spam rate limits  
- Optional startup backlog (General)  
- Multi-language Auto→EN (CJK / Google auto)  
- English names preserved after CJK translation  
- EVE phrase promotions → durable `phrase_overrides` + purge script  
- Recognition Rules nav (was Exclusions)  
- Compact Pilot Info card  
- Module purple highlight off by default; ships not purple  
- Portable `DEFAULT_DB_PATH`; bounded monitor dedupe  
- App icon refresh (transparent 1024 → multi-size ICO)

### Architecture

- `sb_contracts/`, `sb_paths`, `sb_diagnostics`, `sb_channels`, `sb_monitor`  
- `sb_translation/` (detect, google, protect)  
- `sb_filters` / `sb_spam` / `sb_feed_admit`  
- `sb_highlight`, `sb_appearance`, `sb_text`  
- `sb_ui/pilot_info.py`, Settings design pass components  

### Docs / Help

- README Unreleased section; ARCHITECTURE, PROJECT_MAP, INVARIANTS  
- Contracts “Implemented in …” notes  
- Help: 10 topics including Filters; updated Channels/Translation/Pilot Info  
- `scripts/promote_eve_translations.py` + `data/eve_phrase_promotions.json`  

## Pre-merge validation

```powershell
python -X utf8 -m py_compile signal_bridge_gui.py sb_paths.py sb_diagnostics.py sb_channels.py sb_monitor.py sb_filters.py sb_spam.py sb_feed_admit.py sb_highlight.py sb_appearance.py sb_text.py
python -X utf8 -m compileall sb_contracts sb_translation sb_ui
python -X utf8 scripts/check-fixtures.py
python -m pytest tests/ -q
```

Expected: all green (114+ tests at prep time).

## Merge steps (maintainer)

```powershell
# From a clean worktree on the feature branch:
gh pr checks 1
gh pr merge 1 --merge   # or --squash if preferred
git checkout main
git pull origin main
```

Do **not** bump `APP_VERSION` in this merge unless packaging the next public release the same day.

## Post-merge (when packaging)

1. Bump `APP_VERSION` in `signal_bridge_gui.py`  
2. Move `CHANGELOG.md` Unreleased bullets under a dated version heading  
3. Update `GITHUB_RELEASE.md` + README download links  
4. `build_portable.ps1` with `assets/signal_bridge_icon.ico`  
5. Include `data/phrase_overrides.json`, `data/eve_phrase_promotions.json`, full `docs/help/`  
6. Publish SHA256  

## Manual smoke (optional before merge)

- Settings → Filters / General backlog / Recognition Rules  
- Auto→EN mixed CJK + English name (e.g. 能塌吗？ + pilot)  
- Pilot Info open (empty + with data)  
- Restart channel restore  

## Out of scope for this merge

- APP_VERSION / GitHub release asset cut  
- ESI / full parse extraction from GUI  
- LAN viewer / Argos helper process  
