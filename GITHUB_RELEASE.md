# Signal Bridge v0.6

## Release summary

Signal Bridge **v0.6** is the public portable Windows build. It includes the UI foundation refresh, modular `sb_*` / contracts architecture, Settings Filters and design pass, multi-language Auto→EN, EVE phrase promotions, compact Pilot Info, and clean-data packaging.

## Assets

- `SignalBridge-v0.6-win64-portable.zip`
- `SignalBridge-v0.6-win64-portable.zip.sha256`
- `SignalBridge.exe.sha256`

## Highlights

- Bumped app/package version to **0.6**.
- Shared `sb_ui` theme/components/window foundation; Settings Center SettingsShell with fixed footer actions and status.
- Offline Help Center under `docs/help/` (10 topics including Filters); dedicated About/Support window.
- Settings **Filters** + Local spam controls; optional startup backlog; **Recognition Rules** nav (was Exclusions).
- Multi-language Auto→EN (CJK + Google auto); English names kept after CJK; durable phrase overrides + `scripts/promote_eve_translations.py`.
- Compact Pilot Info card; modular `sb_contracts` / `sb_*` modules; portable default DB path; module purple off by default.
- Refreshed app icon (transparent 1024 → multi-size ICO).
- Portable packaging: curated starter data and empty runtime folders only.

## Clean-data packaging note

The v0.6 portable package must **not** include local `cache/`, `runtime/`, `logs/`, ESI tokens, zKill cache, translation runtime cache, starter ESI cache rows, legacy broad exclusions, temporary backup files, or local testing state.

## Intended packaged data

The portable `data/` folder should include:

- `eve_catalog.json`
- `catalog_manifest.json`
- `phrase_overrides.json`
- `eve_phrase_promotions.json`
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
