- Translation Cache Manager deletion fix: deleting a selected row now removes the grouped entry, including manual override, machine-cache records, and failure cooldowns for that source/target.
- Added `Delete All Entries` for Translation Cache Manager reset. This intentionally leaves aliases, exclusions, phrase overrides, ESI cache, zKill cache, settings, and logs alone.
- Removed the bundled starter translation cache for now; packaged builds start with an empty translation cache to avoid shipping polluted mixed English/CJK cache rows.
- Updated packaged alias and default exclusion data from the current maintained local lists.
- Added `ISSUES.md` for public known issues and follow-up work.

- Fixed normal feed rendering so Alias entries display their canonical names in chat while Copy Original keeps raw text.
- Translation Cache Manager now groups duplicate cache records, shows editable Original and English correction boxes below the tables, and saves edits as manual overrides.
- Added additional Chinese intel translation fixes and cache/manual overrides for reported bad translations, including several ship-name corrections and tactical phrase fixes.
- Translation cache now stores cleaner CJK/natural-language segments instead of full mixed intel rows; existing polluted machine-cache rows can be cleaned without touching manual overrides.
- Added Settings > Aliases for ship/system aliases; aliases replace visible shorthand with canonical names and refresh recognition without app restart.
- Pilot Info/feed readability cleanup: No Visual/Cyno classification, compact no-scroll summary behavior, entity separators, and cyno-based temporary Hot Drop Risk flagging.
- Intel History Manual Flags v0.1 has landed in source: compact feed badges for flagged ESI pilots, quick right-click Watchlist/High Threat/Do Not Track actions, and Do Not Track suppression for future local history recording.
- Intel History Pilot Info Card v0.1 has landed in source: right-click `Open Pilot Info` for ESI-confirmed pilots, view compact local history summaries, drill into recent sightings/top ships/top systems, edit manual flags, and copy summaries.
﻿# GitHub Release Checklist

## Before Release

## Planned optional Intel History add-on

Planning has started for the first optional Signal Bridge add-on: **Intel History / Pilot Intelligence**. The core app keeps LAN Viewer and Argos support native, while Intel History is planned as an optional module for local pilot memory, Pilot Intelligence Cards, manual/auto flags, zKill enrichment, import/export intel packs, and a read-only Intel Query Service for future LLM-assisted questions.

Spec: [`docs/INTEL_HISTORY_ADDON_SPEC.md`](docs/INTEL_HISTORY_ADDON_SPEC.md).


1. Verify app runs from source:

## Add-ons foundation

This build includes the first native add-ons foundation under **Settings > Add-ons**. It prepares Signal Bridge for the future optional **Intel History / Pilot Intelligence** module while keeping LAN Viewer and Argos offline translation support as native/core planned features.

The current foundation supports local add-on status, module/data folder separation, official/local ZIP validation, enable/disable state, code-only uninstall behavior, and diagnostics text. The Intel History engine itself remains planned in [`docs/INTEL_HISTORY_ADDON_SPEC.md`](docs/INTEL_HISTORY_ADDON_SPEC.md).


   ```powershell
   python -X utf8 -m py_compile .\signal_bridge_gui.py
   python -X utf8 .\signal_bridge_gui.py --self-test --limit 5
   ```

2. Build portable package:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
   ```

3. Verify package exists:

   ```powershell
   Get-Item .\SignalBridge-v0.3-win64-portable.zip
   Get-FileHash .\SignalBridge-v0.3-win64-portable.zip -Algorithm SHA256
   ```

4. Extract ZIP to a clean folder and run:

   ```text
   SignalBridge.exe
   ```

5. Test on a non-dev Windows 10/11 machine if possible.

## Release Assets

Upload:

- `SignalBridge-v0.3-win64-portable.zip`
- SHA256 checksum in release notes

## Suggested Release Notes

```markdown
# Signal Bridge v0.3

- ESI public entity recognition is now enabled by default for new installs; OAuth remains disabled and optional.

- Fixed ESI public lookup to use cache-friendly `universe/ids` exact-name resolution and reduced automatic lookup noise to protect ESI rates.

- Optional ESI/OAuth foundation, disabled by default.
- Cache-first ESI resolver with 30-day positive cache, negative cache, and right-click refresh/ignore sender actions.
- Temporary localhost OAuth callback listener on `127.0.0.1:8080` only during authorization.
- Client secret and tokens are local-only and not committed/bundled.

- Header color legend removed for a cleaner live UI.
Backfill is disabled by default, so opened channel tabs start live-only and do not display old chat history.

Portable Windows release for EVE Online chat intel monitoring and translation.

## Highlights

- No installer required.
- Dynamic channel selection, no hard-coded channel.
- Channel tabs with close buttons.
- Systems highlighted yellow, ships/assets red, ESS light blue.
- EVE localization DB support.
- Google free auto-detect translation to English.
- Optional Argos offline fallback.
- Configurable font and timestamp display.

## Install

Download and extract `SignalBridge-v0.3-win64-portable.zip`, then run `SignalBridge.exe`.

## SHA256

`PASTE_HASH_HERE`
```

## AV / SmartScreen Note

Unsigned portable EXEs can trigger Windows SmartScreen or antivirus warnings. This does not necessarily mean malware; it is common for new unsigned PyInstaller apps. Long-term mitigation is code signing and reputation building.

### v0.3 message character detection update
- ESI now detects likely character names inside message bodies using a cache-first, conservative candidate extractor.
- System names and EVE catalog entities are excluded before ESI checks to protect API rate limits.
- Detected character names are preserved during translation and are not translated into Chinese.
- Ship highlights are orange; message/sender ESI characters are red; non-ship modules/assets remain purple.
- Fixed ESS highlighting so it no longer tags `ess` inside normal words.
- Updated the chat feed to use a clearer sans-serif default font and fixed ESI message-name detection for lowercase pilot handles while excluding plural ship names.
- Negative ESI answers now stay in the negative cache for 90 days to prevent repeat lookups from burning ESI rates.
- Added ESI diagnostics, selected-text ESI resolve/ignore, always-visible ESI context actions, and a character exclusion list for badly named characters.
- Added built-in and local-DB ESI individual-word exclusions: `Link`, `Jump`, `Fleet`, `and`, `the`, `Gate`, `Star`, `ISK`, and `Ship`.
- Fixed ESI screen rendering: resolved/cached characters now hydrate onto visible rows and highlight red reliably.
- ESI menu actions now show visible result dialogs and logs for manual, selected-text, sender, and status checks.
- Fixed live monitoring stalls by preventing online/free-text translation from blocking chat-log parsing; new rows now emit immediately with monitor diagnostics.
- Fixed live monitor stalls from large optional `translations.db` lookups; live monitoring now uses the compact catalog path so new chat rows are not delayed by DB scans.
- Fixed a GUI render crash in ESS highlighting that could make live chat appear stuck after the first row while the monitor kept reading logs.
- Sender names are now neutral/uncolored; common words like `Red` and `enemy` are excluded from distracting highlights.
- Added explicit right-click `Add Selected Text as ESI Character`; selected/manual ESI checks now cache the character and redraw matching rows immediately.
- Improved ESI detection for manually resolved names by splitting adjacent candidate chunks and allowing valid uppercase single-token pilots.
- The exclusion list is now general: ignored terms suppress ESI character, ship, asset/module, ESS, and system highlighting.
- Added Appearance / Display Options with configurable colors, bold styles, background highlights, presets, live preview, and window opacity.
- Added shorthand ship aliases: `短剑` -> `Stabber` and `海狞獾` -> `Caracal Navy Issue`.
- Polished Appearance / Display Options with visible color swatches beside hex color codes.
- Default startup window now opens in a narrow mobile-style layout instead of a wide layout.

### Display and appearance polish
- Default startup window now opens in a narrow mobile-style side-panel layout (`430x720`, minimum `360x420`).
- Added `View > Appearance / Display Options...` with presets, font controls, opacity, live preview, per-category colors, bold toggles, and optional background highlight rectangles.
- Appearance color controls show both visible swatches and editable hex color codes.
- Sender names are neutral by default to reduce visual noise.
- The General Exclusion List suppresses all recognition/highlighting for ignored terms, including ESI character, ship, module/asset, system, and ESS highlights.
- Bundled default General Exclusion List entries in `data/default_exclusions.json` for new installs.
- Bundled a verified ESI character starter cache in `data/default_esi_entities.json` for new installs.

- Added bundled starter translation-cache data so new installs can reuse known free-text translations without waiting for online translation.
- Curated starter translation-cache entries to correct common EVE terminology before first run.
- Fixed the Appearance / Display Options footer so action buttons stay visible without resizing the window.
- Improved channel workflow: Add Selected no longer replaces current channels, Replace All is explicit, and newly active chat channels can auto-open as tabs.
- Reworked channel tabs into a compact one-line mobile channel bar so many channels no longer stack over the feed.
### Settings Center and Menu Cleanup

- Added a dedicated **Settings > Settings...** window with sidebar pages for General, Channels, Appearance, Translation, EVE Catalog, ESI, Exclusions, Cache & Data, Diagnostics, and About / Support.
- Cleaned up the menu bar so advanced configuration no longer pollutes every menu.
- Added a copyable diagnostics summary for easier bug reports.
### Planned Must-Have: LAN Web Viewer / Phone View

A future release should add an optional LAN web viewer that streams Signal Bridge output to a local read-only webpage. When enabled, the app should show a LAN URL and QR code so users can view translated chat from a phone or another PC on the same network. This is documented in the roadmap and should remain local-first, disabled by default, and read-only for the first version.
### Planned LAN Viewer Theme Matching

The planned LAN Web Viewer should mirror the desktop app's appearance settings where practical, including feed colors, fonts, bold/background highlight styles, sender-neutral styling, and exclusion behavior, while remaining mobile-friendly on phones.

### Intel History add-on MVP foundation
- Added the first optional Intel History add-on skeleton and runtime loader foundation.
- The MVP add-on records ESI-confirmed pilot sightings into a local SQLite database, dedupes repeated reports, and exposes health/status counters in Settings > Add-ons.
- This is an early foundation only; Pilot Intelligence Cards, flags, zKill enrichment, import/export, and LLM query support remain planned next steps.

### Intel History Auto Hot Drop Risk

- Adds temporary `Hot Drop Risk` auto flags for ESI-confirmed pilots reported in likely cyno ships.
- Default high-confidence triggers: Force Recon Cruisers and Expedition Frigates.
- Black Ops battleships such as Redeemer, Widow, Sin, and Panther no longer trigger default hot-drop caller flags; they remain useful profile/context data.
- Feed badges reuse the existing compact flag display, while Pilot Info exposes the underlying reason.
- Translation cache fix: `天鹤级` now resolves to `Crane` instead of the literal `Tianhe class`.
- Translation cache fix: `短剑级` now resolves to `Stabber` instead of literal `Stabber grade` style output.
- UI polish pass: consistent Signal Bridge window icons, better child-window placement/stacking, cleaner Pilot Info header/date display, more context-aware right-click menus, clearer flag icons, and a less blocking redraw path for translation display toggles.


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
- Diagnostics polish: added structured event/error/stall logs, last-action tracking, redraw/queue timing, and a UI stall watchdog to help diagnose intermittent hangs.
- Diagnostics: feed right-click menu now includes translation, entity-recognition, and click-context traces to explain skipped translations and wrong-target menu behavior.
- General stability/readability refactor: added structured intel segments, separated repeated kill reports, segment diagnostics, and safer render-only feed drawing with ESI hydration moved out of the row render path.
- Corrected the segmentation display: normal rows remain compact while repeated/back-to-back intel rows split cleanly without noisy duplicated chips.
- Added maintainability/LLM-friendly project docs, contracts, fixture cases, and a fast offline fixture checker for safer future changes.
- Added chunked/cancellable feed redraw to reduce UI stalls during channel switches and display-setting changes.
- Extracted feed display-line logic into a small pure render-model helper, keeping fixture-tested output stable while improving maintainability.
- Reactivated Auto -> EN and EN -> CN free-text translation toggles using a safe background queue; rendering still never performs blocking MT.
- Pilot Info card now uses a compact normalized layout with manual Sync zKill support and cached zKill summary state.
- Pilot Info card tactical cleanup: No Visual is no longer shown as a ship, zKill sync stores recent event summaries for priority signals, and the card uses a scrollable body with fixed footer actions.

- Alias display now updates the normal chat feed with canonical names instead of leaving raw aliases visible; short system aliases and translated ship-class artifacts are handled more reliably.

- Fixed alias-related feed stalls and system-alias coloring: user aliases now render from a small cached rule set, and system aliases like 4-H -> 4-HWWF stay highlighted as systems.

- Aliases now trigger when adjacent to Chinese text, e.g. YMJG星门 and 4H别过 correctly render as YMJG-4 and 4-HWWF.
- Translation Cache Manager MVP: dedicated settings page for cache-first behavior, manual exact translation overrides, cache-only/offline mode, fallback controls, and failure cooldowns.
- Translation Cache Manager UI polish: split Original/Translated tables, live filters, click-to-edit, and auto-saving manual overrides.
- Fixes recent Chinese intel detection for Osprey Navy Issue, Caracal Navy Issue, Skyhook, and treats Refugee as hostile/red instead of an asset/module.
- Adds broader Chinese ship alias coverage for Navy/Fleet Issue variants and common literal machine translations so corrected ships detect/highlight from live intel.
- Improves Chinese ship detection in mixed intel lines, including Eris, Thrasher Fleet Issue, Vedmak, and catalog-verified Navy/Fleet variants.
- Adds catalog-wide Chinese ship alias extraction for official ship names plus curated shorthand such as 海鱼 -> Osprey Navy Issue, reducing reliance on Google/Argos literal translations.

- Translation Cache editor usability fix: side-by-side editable Original/English boxes are now directly under the cache lists, with internal cache labels hidden unless explicitly enabled.

- Pilot Info/zKill fix: more accurate clicked-pilot identity, visible character ID/zKill URL, zKill API fallback for rejected time filters, and hydrated recent kill/loss details.

