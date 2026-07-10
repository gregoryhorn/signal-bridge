# Signal Bridge release notes

## Next cut (draft — after `feature/contracts-and-backlog` merges)

**Do not publish until APP_VERSION is bumped.** Source is still labeled **0.6** until packaging.

Planned highlights (from CHANGELOG Unreleased):

- Modular `sb_*` / `sb_contracts` architecture; portable default DB path  
- Settings Filters + spam controls; optional startup backlog  
- Multi-language Auto→EN; CJK lines keep trailing English names  
- EVE phrase promotions + `scripts/promote_eve_translations.py`  
- Settings design pass; Recognition Rules nav  
- Compact Pilot Info redesign  
- Module purple off by default; refreshed app icon  

See `docs/superpowers/MERGE_PREP.md` for merge and packaging steps.

---

# Signal Bridge v0.6

## Release summary

Signal Bridge v0.6 focuses on the UI foundation refresh, offline help, and Translation Cache data hygiene. New portable installs keep the v0.5 clean-runtime packaging model while adding the Settings Center shell, themed shared controls, redesigned Translation Corrections, dedicated About/Support, offline Help Center topics, and safer machine-cache cleanup.

## Assets

- `SignalBridge-v0.6-win64-portable.zip`
- `SignalBridge-v0.6-win64-portable.zip.sha256`
- `SignalBridge.exe.sha256`

## Highlights

- Bumped app/package version to **0.6**.
- Added the shared `sb_ui` theme/components/window foundation used by Settings, Help, and About surfaces.
- Rebuilt the Settings Center on a shared SettingsShell with consistent navigation, scrolling, fixed footer actions, status text, and visible settings-load/save failures.
- Redesigned Translation Corrections as a balanced Original/English table with a focused correction editor.
- Added offline in-app Help Center topics under `docs/help/`, plus a dedicated About/Support window with project links, diagnostics copy, update check, and donation info.
- Fixed Auto to EN Translation Cache source pollution and added Settings cleanup for invalid machine rows while preserving manual corrections and explicit EN to CN rows.
- Kept portable packaging clean: curated starter data and empty runtime folders only.

## Clean-data packaging note

The v0.6 portable package should include curated starter data only. It must **not** include local `cache/`, `runtime/`, `logs/`, ESI tokens, zKill cache, translation runtime cache, starter ESI cache rows, legacy broad exclusions, temporary backup files, or local testing state.

## Intended packaged data

The portable `data/` folder should include:

- `eve_catalog.json`
- `catalog_manifest.json`
- `phrase_overrides.json`
- `user_aliases.json` from the committed clean default
- `default_recognition_rules.json`
- `default_recognition_rules.json.sha256`
- `default_translation_cache.json`
- `default_translation_cache.json.sha256`

The portable package must also include the `docs/help/` folder (offline in-app help topics).

## Verification commands

```powershell
Get-Item .\SignalBridge-v0.6-win64-portable.zip
Get-FileHash .\SignalBridge-v0.6-win64-portable.zip -Algorithm SHA256
Get-FileHash .\dist\SignalBridge\SignalBridge.exe -Algorithm SHA256
```

## Install

Download and extract `SignalBridge-v0.6-win64-portable.zip`, then run `SignalBridge.exe`.

No installer or admin rights are required.
