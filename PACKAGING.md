# Build and Packaging Notes

Signal Bridge is currently packaged with PyInstaller.

Recommended command:

```powershell
pyinstaller --noconfirm --clean --noupx --windowed --icon .\assets\signal_bridge_icon.ico --name SignalBridge signal_bridge_gui.py
```

Important:

- Use `--noupx` to avoid packed executable heuristics.
- Use `--windowed` for native GUI behavior.
- Do not require administrator rights.
- Do not silently download translation models.
- Publish SHA256 checksums.
- Prefer code signing before broad public distribution.

If PyInstaller hangs or produces a huge build because of Argos/Torch dependencies, build a first release without bundling Argos and keep Argos as an optional source/dev feature or separate advanced package.

## Bundled user documentation

The portable ZIP should include the current README, distribution notes, changelog, roadmap, packaging notes, release notes, compact EVE catalog, catalog manifest, phrase overrides, and checksum files. Keep these aligned whenever UI/display behavior, release assets, or catalog metadata changes.

The default packaged app opens in a mobile-style side-panel layout and includes Appearance / Display Options documentation in the bundled README files.
Include `data/default_exclusions.json` in every portable build so default General Exclusion List entries are seeded for new installs.

Include `data/default_esi_entities.json` and its checksum in portable builds so new installs start with verified ESI character cache entries.
