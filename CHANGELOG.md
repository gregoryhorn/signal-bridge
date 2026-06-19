
### v0.3 - message character detection refinement
- Added conservative ESI character-name candidate detection inside chat message text, not only sender names.
- Excludes known solar systems, ships, modules, catalog entities, links, counts, and localized EVE aliases before ESI lookup.
- Confirmed ESI character names are protected from machine translation, including EN -> CN mode.
- Changed ship highlighting to orange and ESI character highlighting to red; non-ship modules/assets remain purple.

## v0.3 - 2026-06-19

- ESI public entity recognition is now enabled by default for new installs; OAuth remains disabled and optional.
- Fixed ESI public lookup to use cache-friendly `universe/ids` exact-name resolution and reduced automatic lookup noise to protect ESI rates.
### Optional ESI / OAuth foundation
- Added optional ESI entity recognition settings; ESI remains disabled by default and is never required for normal chat monitoring or translation.
- Added cache-first ESI resolver foundation with SQLite cache at `cache/esi_cache.sqlite`.
- Added 30-day positive ESI entity cache, negative cache, manual ignore/correction storage, and background resolver queue.
- Added right-click feed actions to resolve/refresh sender ESI data, copy ESI details, and ignore sender for ESI.
- Added optional EVE OAuth foundation using a temporary `127.0.0.1:8080` callback listener for `http://localhost:8080/callback`; the listener is only opened during authorization and closes after success/failure/timeout.
- Added ESI status/cache entries to Health and Tools menus.
- Client secret and OAuth tokens are stored only in ignored local config files and are not committed or bundled.
- Preserved live-only/no-backfill behavior.

﻿# Changelog

All notable Signal Bridge changes will be documented here.

## v0.2 - 2026-06-19

- Removed the header color legend to keep the live UI cleaner.
### Feed interaction and diagnostics
- Added a simple nonblocking GitHub update check on launch, with Help > Check for Updates and an on-launch toggle.
- Added right-click feed row menu.
- Added copy actions for visible line, original line, translated line, sender, systems, ships/assets, and URLs.
- Added HTTP/HTTPS URL auto-linking with click-to-open and right-click copy/open support.
- Added startup/error logging to the portable `logs/` folder.
- Added Settings > Open Logs Folder.
- Preserved live-only monitoring with backfill disabled by default.


### Tab visual polish
- Fixed tab label encoding issues so unread markers and close buttons render cleanly.
- Added hover styling for tabs and close buttons.
- Added a visible drag/drop target highlight while reordering tabs.
- Added a `+ Hidden (N)` restore button on the tab bar when hidden tabs exist.
- Improved tab spacing and theme tokens for future theme customization.


### Tab system refactor
- Replaced the janky tab strip with a managed tab model.
- Added default All tab support with combined chat view.
- All and channel tabs can now be hidden and restored.
- New chat tabs auto-open only when they were not manually hidden.
- New messages never steal focus from the current tab.
- Inactive tabs show unread indicators that clear when focused.
- Tabs wrap/stack when the window is narrowed instead of clipping off screen.
- Tabs can be drag-reordered and the order persists.
- Tab styling now uses centralized theme tokens for future theme work.


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
- Fixed ESS highlighting so only standalone `ESS` is colored, not the letters inside longer words.
- Changed the default chat feed font to a clearer sans-serif typeface (`Segoe UI`) and improved ESI message-name detection for lowercase pilot handles after systems while excluding plural ship names.
- Changed negative ESI answer cache TTL to 90 days to prevent unnecessary rechecks and protect ESI rate limits.
