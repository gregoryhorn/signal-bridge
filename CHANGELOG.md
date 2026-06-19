
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
- Added ESI diagnostics, visible right-click ESI actions, selected-text ESI resolve/ignore, and a character exclusion list for badly named characters.
- Added built-in and local-DB ESI individual-word exclusions for `Link`, `Jump`, `Fleet`, `and`, `the`, `Gate`, `Star`, `ISK`, and `Ship`.
- Fixed ESI screen rendering so cached/resolved characters are hydrated onto rows and visibly highlighted red even when the resolver result arrives after render or the candidate text was broad.
- Made ESI menu actions visibly report results: Check ESI now opens a status dialog, manual/selected/sender checks show result dialogs, and every action writes to the ESI log.
- Fixed live monitoring stalls by preventing online/free-text translation from blocking the monitor thread; chat rows now emit immediately and monitor activity is logged.
- Fixed live monitor stalls from large `translations.db` lookups by using compact catalog-only enrichment in the monitor thread.
- Fixed a Tkinter ESS-highlight regex crash that could stop the GUI feed from rendering new live rows even though the monitor was reading them.
- Made sender names neutral/uncolored and excluded `Red`/`enemy` from distracting asset/ESI highlighting.
- Added right-click `Add Selected Text as ESI Character` and made selected/manual ESI resolves cache and redraw matching rows.
- Improved ESI candidate detection for adjacent names and valid uppercase single-name pilots such as `MADRICO`.
- ESI detection now handles short-prefix character names such as `LT Shax`.
- Generalized the exclusion list so ignored terms suppress red ESI, orange ship, purple asset/module, ESS, and system highlights.
- Added Appearance / Display Options with theme presets, font/color/bold/background controls, preview, reset defaults, and window opacity.
- Added Chinese shorthand ship aliases: `短剑` -> `Stabber` and `海狞獾` -> `Caracal Navy Issue`, preventing MT from translating them as common words.
- Polished the Appearance / Display Options dialog with clearer sections and visible color swatches next to hex color codes.
- Changed the default startup window to a narrow mobile-style layout instead of a wide desktop layout.

### v0.3 UI/display documentation refresh
- Documented the mobile-style default window layout, Appearance / Display Options dialog, color swatches, opacity, presets, sender-neutral styling, and General Exclusion List behavior.
- Bundled docs now describe how display styling interacts with system, ESI character, ship, asset/module, ESS, translation, and link highlights.
- Bundled the maintainer/user General Exclusion List as `data/default_exclusions.json` and seed it into new local caches without overwriting user edits.
- Bundled verified ESI character starter cache as `data/default_esi_entities.json` and seed it into new local caches without overwriting user entries.

- Bundled a starter translation cache exported from the maintainer client and seeded it idempotently for new installs.
