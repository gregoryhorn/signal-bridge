# Changelog

All notable Signal Bridge changes will be documented here.

## v0.1 - 2026-06-19

- Added an All Channels tab and a global View option to show/hide channel names in feed rows. Channel names are hidden by default in normal per-channel tabs.

- Backfill is disabled by default; channels open live-only to avoid showing old private chat history.

Initial portable Windows preview release.

### Added

- Portable Windows GUI package.
- Dynamic EVE chat channel discovery; no hard-coded channel.
- Active channel tabs with per-tab x close buttons.
- Offset-based live log monitoring.
- Solar system highlighting in yellow.
- Ships/assets highlighting in red.
- ESS highlighting in light blue.
- EVE DB localization for localized ship/item names.
- Google free auto-detect translation to English.
- Optional EN -> CN mode.
- Optional Argos offline fallback install hook.
- Configurable feed font, font size, and timestamp visibility.
- Always-on-top option.
- Portable config/cache/data/logs/models folders.
- GitHub-ready README, packaging notes, release checklist, and SHA256 output.

### Packaging Notes

- Default EXE excludes heavy Argos/Torch/spaCy stacks to reduce package size and AV false-positive risk.
- Built with PyInstaller using --noupx and --windowed.
- Argos remains optional rather than bundled in the default release.



