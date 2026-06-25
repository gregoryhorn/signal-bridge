# Signal Bridge Portable Build Notes

Goal: no-install Windows 10/11 x64 portable ZIP.

AV-conscious guidelines:
- Build on a clean Windows VM with a stable Python release.
- Avoid UPX compression; packed executables are more likely to trigger AV heuristics.
- Use PyInstaller --clean --noupx --windowed.
- Keep network access transparent: Google Translate only when user enables Translate Free Text; Argos model download only after prompt.
- Sign the EXE later if distributing broadly.
- Publish checksums for ZIP releases.
- Do not bundle the 507 MB full translations.db by default; use compact catalog later.

Build:
```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

## First Launch Layout

Signal Bridge opens in a narrow mobile-style side-panel layout by default. Resize it like a normal Windows app if you prefer a wider layout.

## Appearance

Use `View > Appearance / Display Options...` to change fonts, colors, bold styles, opacity, highlight backgrounds, and presets. The dialog shows color swatches next to editable hex codes.
Bundled default exclusions are included in `data/default_exclusions.json` and are imported into the local General Exclusion List on first run.


- The portable package includes starter scoped recognition rules, catalog data, phrase overrides, default aliases, and starter translation-cache data. ESI/translation runtime caches start clean and are created locally on first run.
## Settings Center

Use **Settings > Settings...** for the main configuration UI. The Settings Center groups channels, appearance, translation, EVE catalog, ESI, exclusions, cache/data, diagnostics, and support into one window with a sidebar and fixed bottom action bar.
## Settings Center

Open **Settings > Settings...** after extracting the portable ZIP. The Settings Center groups General, Channels, Appearance, Translation, EVE Catalog, ESI, Exclusions, Cache & Data, Diagnostics, and About / Support into one dedicated window.

## Current packaged data notes

- `data/default_translation_cache.json` is intentionally empty so new installs do not inherit polluted mixed English/CJK translation cache rows.
- `data/user_aliases.json` and `data/default_exclusions.json` are bundled from the maintained source lists.
- Runtime folders such as `cache/`, `logs/`, `config/`, `runtime/`, and local add-on state should not be published as user data.
- See `ISSUES.md` for the public known-issues/follow-up list.


## v0.4 package note

The v0.4 portable package includes `ISSUES.md`, `docs/images/signal-bridge-v0.4-screenshot.png`, the maintained `data/user_aliases.json`, scoped `data/default_recognition_rules.json`, and an empty `data/default_translation_cache.json` so new installs start with a clean translation cache.

## v0.5 clean-data package note

The v0.5 portable package must start with clean local runtime state. Include curated starter files such as `data/default_recognition_rules.json`, `data/default_translation_cache.json`, catalog data, phrase overrides, and committed default aliases. Do not include local cache files, runtime folders, logs, ESI tokens, zKill cache, translation runtime cache, temporary legacy-exclusion backups, or local testing state.
