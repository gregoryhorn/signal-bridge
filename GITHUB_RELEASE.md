# Signal Bridge v0.7

## Release summary

Signal Bridge **v0.7** is the public portable Windows build. It delivers the approved Void Tactical interface across the desktop app and LAN viewer while preserving the local-first monitoring, translation, ESI, and Pilot Info workflows.

## Assets

- `SignalBridge-v0.7-win64-portable.zip`
- `SignalBridge-v0.7-win64-portable.zip.sha256`
- `SignalBridge.exe.sha256`

## Highlights

- Bumped app/package version to **0.7**.
- Applied Void Tactical shell, feed, tab, settings, dialog, Help, About, and Pilot Info treatment.
- Added semantic theme roles and shared components to keep desktop and phone views aligned.
- Grouped Settings navigation and stabilized page-specific Apply behavior.
- Added translated feed sublines, compact Pilot Info actions, and reliable child-window placement.
- Brought the tokenized LAN viewer to phone density with matching colors, filters, empty states, and reconnect status.
- Added reviewed UI capture evidence under `docs/images/ui-review/`.

## Clean-data packaging note

The v0.7 portable package must **not** include local `cache/`, `runtime/`, `logs/`, ESI tokens, zKill cache, translation runtime cache, starter ESI cache rows, legacy broad exclusions, temporary backup files, browser automation traces, or local testing state.

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
Get-Item .\SignalBridge-v0.7-win64-portable.zip
Get-FileHash .\SignalBridge-v0.7-win64-portable.zip -Algorithm SHA256
Get-FileHash .\dist\SignalBridge\SignalBridge.exe -Algorithm SHA256
```

## Install

Download and extract `SignalBridge-v0.7-win64-portable.zip`, then run `SignalBridge.exe`.

No installer or admin rights are required.
