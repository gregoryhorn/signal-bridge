- Fixed alias display so user ship/system aliases replace shorthand in the normal chat feed, not only translated/copy paths.
- Added a dedicated ship/system Alias page and user alias file so shorthand like Enyou Class and Apocalypse Navy is displayed as the canonical ship name.
- Improved Pilot Info/feed readability: status/signal terms no longer show as ships, the card avoids default scrolling, feed entities get subtle separators, and cyno intel can temporarily flag likely hotdroppers.

- Added Diagnostics & Observability Phase 1/2: structured JSONL event/error/stall logs, last-action tracking, queue/redraw timing, and a UI stall watchdog so freezes can be traced instead of guessed.



- Added a focused UI polish pass: Signal Bridge icons now apply to the main window and key child windows, Settings/Appearance/Pilot Info dialogs are centered/stacked over their parent, Pilot Info uses the cleaner `Character, Corporation` + `Alliance` header without visible character IDs, Pilot Info dates are friendlier, right-click menus are more context-aware, flag icons are cleaned up, and translation display toggles use a coalesced redraw path to reduce UI stalls.


- Corrected the Chinese EVE ship translation `短剑级` from literal `Stabber grade` style output to `Stabber` in the bundled starter translation cache.


- Corrected the Chinese EVE ship translation `天鹤级` from literal `Tianhe class` to `Crane` in the bundled starter translation cache.


- Added Intel History Auto Hot Drop Risk v0.1: likely cyno ships now create temporary auto flags that reuse the live-feed badge path.
- Corrected hot-drop detection so default inline triggers are Force Recon Cruisers and Expedition Frigates only; Black Ops battleships such as Redeemer/Widow/Sin/Panther are treated as drop-fleet context, not default hot-drop caller flags.
- Auto Hot Drop Risk reasons now include ship, class, system, timestamp, and expiry context.


### Intel History add-on MVP foundation
- Added Manual Flags v0.1 feed integration: active Intel History flags now render as compact badges beside ESI-confirmed pilot names in the feed, right-click quick actions can mark Watchlist/High Threat/Do Not Track, and Do Not Track prevents future Intel History recordings for that pilot.
- Added Intel History Pilot Info Card v0.1 planning implementation: feed right-click `Open Pilot Info`, compact pilot summary, recent sightings/top ships/top systems drill-downs, direct manual flag editing, copyable pilot summaries, and automatic add-on worker startup.
- Added the first installable `Intel History / Pilot Intelligence` add-on skeleton under `addons/intel-history`.
- Added guarded same-EXE module loading for the official Intel History add-on.
- Added live row event emission to the add-on without blocking feed rendering.
- Added local SQLite MVP storage for ESI-confirmed pilot sightings with 3-minute dedupe buckets.
- Added Settings > Add-ons health/status counters for pilots, sightings, queue size, last sighting, and errors.

### v0.3 - message character detection refinement
- Added conservative ESI character-name candidate detection inside chat message text, not only sender names.

## Planned - Intel History add-on spec

- Added planning spec for the future optional Intel History / Pilot Intelligence add-on.
- Clarified that LAN Viewer and Argos offline translation support are native/core planned features, while Intel History is the first optional add-on.
- Captured planned local SQLite sighting history, Pilot Intelligence Cards, manual/auto flags, zKill enrichment, import/export intel packs, and a read-only Intel Query Service / LLM entry point.
- See `docs/INTEL_HISTORY_ADDON_SPEC.md`.

- Excludes known solar systems, ships, modules, catalog entities, links, counts, and localized EVE aliases before ESI lookup.

## Changed - Add-ons foundation

- Added a native Add-ons page to the Settings Center.
- Added Intel History / Pilot Intelligence placeholder/status controls.
- Added local add-on folders: `modules/` for add-on code and `user_data/modules/` for user data.
- Added local ZIP install validation for the planned official Intel History add-on, including unsafe path rejection and manifest checks.
- Added enable/disable state, add-on details, data-folder access, and code-only uninstall behavior that preserves user data.
- Added Intel History add-on status to diagnostics.
- The actual Intel History storage/analysis engine remains planned in `docs/INTEL_HISTORY_ADDON_SPEC.md`.

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
- Reviewed and curated bundled starter translation cache entries for common EVE terminology mistakes such as Stabber, Caracal Navy Issue, Pacifier, Draugur, Sabre, Sisters Combat Scanner Probe, MTUs, and ISK.
- Fixed Appearance / Display Options so Apply/OK/Cancel remain visible on smaller mobile-style windows.
- Improved channel UX: Choose / Open Channels now adds selected channels by default, keeps Replace All explicit, and live monitoring auto-opens newly active chat channels without stealing focus.
- Reworked the channel area into a compact mobile-style one-line bar with All, current-channel dropdown, close-current, and hidden restore controls instead of stacked wrapped tabs.
### UI Polish

- Added a dedicated **Settings Center** with sidebar pages for General, Channels, Appearance, Translation, EVE Catalog, ESI, Exclusions, Cache & Data, Diagnostics, and About / Support.
- Cleaned up top-level menus so configuration is centralized instead of scattered across View/Tools/Settings.
- Added a copyable diagnostics summary from the Settings Center and Tools menu.
### Planning

- Documented the planned must-have LAN Web Viewer / Phone View feature: optional local webpage streaming, LAN URL, QR code, read-only mobile-friendly viewer, and privacy/security requirements.
### Planning

- Added LAN Web Viewer appearance requirements: the future phone/browser stream should mirror the desktop app theme, colors, fonts, bold/background highlight styles, and General Exclusion List behavior where practical.


### Settings flow polish
- Added Translation settings controls for preferred engine and fallback mode: Auto, Argos Offline, Google Online, Google then Argos, Argos then Google, Offline only, and Online only.
- Added visible Argos runtime/model status, Install / Repair Argos, Refresh Argos Status, and Test Translation controls.
- Simplified the ESI settings page by replacing noisy raw cache output with friendly recognition, OAuth, known entity, exclusion, negative-answer, and last-check status rows.
- Added an About / Support donation section with copy buttons for the in-game ISK recipient and donation message.


### Argos safe-mode update
- Temporarily disabled direct in-process Argos status probing, install/repair, and translation calls after the current Argos runtime path was found to hang/crash the Tk app.
- Translation defaults now stay on Auto/Google (`online-only`) until Argos is reintroduced through a safe optional add-on/offline package flow with isolated install, model checks, and translation execution.
- Settings still explains the disabled Argos state instead of silently hanging.

### UI hang hardening and local data refresh
- Hardened feed redraw so rendering never performs blocking machine translation, network calls, or offline MT work on the Tk UI thread.
- `Translated only` and redraw now show only precomputed row translations instead of triggering live translation work during display.
- Synced current local General Exclusion List and local translation cache into bundled starter data files with refreshed SHA256 checksums.
- This keeps the app responsive and improves first-run defaults without overwriting existing user cache/settings.

### Feed text normalization polish
- Normalized common shorthand `clr` to `clear` in visible feed/copy-visible text.
- Removed noisy display punctuation `(`, `)`, and `*` from rendered feed text while keeping raw stored chat rows unchanged.

### Right-click Pilot Info targeting fix
- Fixed context-menu targeting so Pilot Info and pilot flag actions use the exact clicked pilot text span, not the sender or first ESI entity on the row.
- Right-clicking systems, ships/items, or generic row text no longer falls back to Pilot Info for the sender.
- Added stricter clicked-span detection for multi-word pilot names such as `Bigus Dingus DOI`.
- Added diagnostic traces for feed rows: translation decisions, entity recognition summaries, and right-click context traces available from the feed context menu.
- Added a general intel segmentation/render-safety refactor: rows can now carry structured segments, repeated kill reports split into separate feed lines, segment diagnostics are visible, and feed rendering no longer hydrates ESI in the render path.
- Corrected segmented feed display so single-event rows stay compact and only multi-event rows split into aligned lines.
- Added an LLM-friendly architecture foundation with project map, invariants, architecture/Argos plans, contract docs, feed fixtures, and a fast fixture checker.
- Added chunked/cancellable feed redraw so large display updates yield back to Tk instead of rebuilding all rows synchronously.
- Extracted feed display-line logic into a pure render-model helper to reduce GUI-file complexity and protect fixture-tested output.
- Reactivated CN/EN free-text direction toggles through a safe background translation queue instead of render-thread MT calls.
- Redesigned Pilot Info as a compact normalized local snapshot card and added manual cache-backed zKill sync.
- Cleaned up Pilot Info tactical display so No Visual is treated as status, zKill recent events drive HIGH/MED/QUIET priority, and card body scrolls while footer buttons stay visible.

- Fixed alias display so current ship/system aliases are applied dynamically in the normal chat feed, including rows parsed before the alias was added. Added starter cleanup aliases for common bad translation artifacts such as Widmark-class, Black Crow-class, Ocato-class, Assassin-class, and Stabber-class.

- Fixed an alias feed stall by limiting dynamic alias replacement to user/manual aliases, caching per-row display text, and precompiling a small alias rule set instead of the full EVE catalog. Fixed system aliases such as 4-H -> 4-HWWF so they display canonically and keep system highlighting instead of purple module styling.

- Fixed ship/system aliases next to Chinese text so short Latin aliases like YMJG and 4H trigger even when immediately followed by CJK characters, while preserving protection against replacements inside longer Latin tokens.
- Added a cache-first Translation Cache Manager MVP with manual exact overrides, cache-only mode, fallback controls, and failure cooldowns so repeated/corrected translations reduce reliance on Google/Argos.
