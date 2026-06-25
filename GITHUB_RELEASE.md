# Signal Bridge v0.5

## Release summary

Signal Bridge v0.5 focuses on recognition cleanup, cleaner first-run defaults, and package hygiene. New portable installs start with clean runtime/cache state, scoped Recognition Rules, and bundled parser-noise defaults instead of the old broad legacy exclusion list.

## Assets

- `SignalBridge-v0.5-win64-portable.zip`
- `SignalBridge-v0.5-win64-portable.zip.sha256`
- `SignalBridge.exe.sha256`

## Highlights

- Bumped app/package version to **0.5**.
- Added scoped **Recognition Rules** for:
  - ignored pilots
  - highlight exclusions
  - parser noise words
- Added inline help and clearer test-term output for Recognition Rules.
- Added bundled `data/default_recognition_rules.json` with scoped default parser-noise rules for common chat false positives.
- Disabled legacy broad exclusion reseeding so clean installs do not inherit dirty local exclusions.
- Improved the Translation Corrections layout with aligned panes, clearer button hierarchy, and advanced controls hidden behind a toggle.
- Updated packaging so portable builds copy only curated starter data and empty runtime folders.

## Clean-data packaging note

The v0.5 portable package should include curated starter data only. It must **not** include local `cache/`, `runtime/`, `logs/`, ESI tokens, zKill cache, translation runtime cache, starter ESI cache rows, legacy broad exclusions, temporary backup files, or local testing state.

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

## Verification commands

```powershell
Get-Item .\SignalBridge-v0.5-win64-portable.zip
Get-FileHash .\SignalBridge-v0.5-win64-portable.zip -Algorithm SHA256
Get-FileHash .\dist\SignalBridge\SignalBridge.exe -Algorithm SHA256
```

## Install

Download and extract `SignalBridge-v0.5-win64-portable.zip`, then run `SignalBridge.exe`.

No installer or admin rights are required.
