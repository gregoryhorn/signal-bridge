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

Bundled starter ESI characters are included in `data/default_esi_entities.json` and imported into the local ESI cache on first run.

- The portable package includes starter exclusions, verified ESI characters, and starter translation-cache data. These are seeded locally on first run without overwriting user changes.
## Settings Center

Use **Settings > Settings...** for the main configuration UI. The Settings Center groups channels, appearance, translation, EVE catalog, ESI, exclusions, cache/data, diagnostics, and support into one window with a sidebar and fixed bottom action bar.
## Settings Center

Open **Settings > Settings...** after extracting the portable ZIP. The Settings Center groups General, Channels, Appearance, Translation, EVE Catalog, ESI, Exclusions, Cache & Data, Diagnostics, and About / Support into one dedicated window.
