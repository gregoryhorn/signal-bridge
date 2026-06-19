# Signal Bridge Roadmap

Signal Bridge is a lightweight Windows app for translating chat logs CN -> EN and EN -> CN.

## Optional Intel History add-on spec

The first optional add-on is planned as **Intel History / Pilot Intelligence**. LAN Viewer and Argos offline translation remain native/core features; Intel History is optional because it stores long-term local intel and performs deeper analysis.

Planned scope includes local SQLite sightings, ESI-confirmed pilot tracking, Pilot Intelligence Cards, manual and auto flags, zKill enrichment, import/export intel packs, and a read-only Intel Query Service for UI and future LLM queries. See [`docs/INTEL_HISTORY_ADDON_SPEC.md`](docs/INTEL_HISTORY_ADDON_SPEC.md).


This roadmap is planned work, not a guarantee of exact delivery order. The current focus is keeping the app lightweight, portable, low-impact during gameplay, and useful for live chat/intel readability.

## Add-ons foundation implemented

The first add-ons foundation has been added to the app. `Settings > Add-ons` now provides the native UI and local package plumbing for the future optional Intel History / Pilot Intelligence add-on: module folders, user-data folders, manifest inspection, local ZIP install validation, enable/disable state, uninstall-code-only behavior, and diagnostics visibility.

Next work remains the actual Intel History engine: local SQLite sightings, Pilot Intelligence Cards, flags, zKill enrichment, import/export packs, and the Intel Query Service.


## Current v0.2 Baseline

- Portable Windows ZIP release.
- No installer required.
- Dynamic chatlog/channel discovery.
- Active channels shown as tabs.
- All Channels view.
- Live-only monitoring by default; backfill is disabled by default.
- DB-backed EVE localized ship/item translation where available.
- Google free translation primary.
- Argos Translate fallback planned/optional.
- Auto -> EN translation for non-English text.
- EN -> CN translation mode.
- System highlighting in yellow.
- Ship/asset highlighting in red.
- ESS highlighting in light blue.
- Always-on-top support.
- Font size/font selection support.
- Timestamp toggle.
- Custom app icon.
- GitHub release with SHA256 checksums.

- v0.2 UI cleanup: header color legend hidden to keep the live monitor header focused on version, tabs, and status.

## v0.2.1 - UI Hotfix and Interaction Polish

Goal: make the current app feel less prototype-like and remove obvious UI friction.

Planned items:

- Fix tab UX/jank.
- Improve tab active state, hover state, close buttons, and spacing.
- Keep All Channels pinned first when multiple channels are open.
- Add better handling for long channel names and many open tabs.
- Add right-click tab menu:
  - Close Channel
  - Close Other Channels
  - Close All Channels
  - Copy Channel Name
- Add right-click feed row menu.
- Add nice copy/paste actions:
  - Copy visible line
  - Copy original line
  - Copy translated line
  - Copy sender
  - Copy systems
  - Copy ships/assets
  - Copy URLs
- Add auto-link URL support for HTTP/HTTPS links.
- Add startup/error log improvements so launch failures are easy to diagnose.
- Preserve live-only/no-backfill behavior.

## v0.2 - Translation Catalog and DB Updates

Goal: make translation setup easier and avoid requiring users to manually provide the large EVE translation DB.

Planned items:

- Add GitHub-based translation catalog update support.
- Check for updated compact EVE translation catalog from GitHub.
- Download catalog updates automatically after user confirmation.
- Verify downloaded catalog with SHA256 before replacing the local catalog.
- Backup previous catalog before updating.
- Show catalog version/status in Health/About.
- Keep full `translations.db` import as an advanced/manual option.
- Add translation cache viewer/clearer.
- Add manual phrase override support for EVE slang.
- Improve protected terms so Google/Argos do not corrupt systems, ships, names, URLs, counts, or ISK values.
- Add source labels for DB, Google, Argos, cache, and manual overrides.

Preferred catalog approach:

```text
data/eve_catalog.json
data/catalog_manifest.json
data/eve_catalog.previous.json
```

The normal release should use a compact catalog, not the full large SQLite DB.

## v0.2.x - Feed Interaction Polish

Goal: make the feed faster and more practical during gameplay.

Planned items:

- Auto-link URLs in the feed.
- Link styling with underline/light-blue text.
- Hover URL preview in the status bar.
- Left-click to open links.
- Right-click to open/copy links.
- Safety option for external link confirmation.
- Search within visible feed.
- Copy clean intel line.
- Copy selected structured entities.
- Optional original-on-hover for translated text.


## v0.3 implementation note

Optional ESI/OAuth foundation has been implemented with ESI disabled by default, localhost OAuth callback on `127.0.0.1:8080`, cache-first SQLite lookups, 30-day positive TTL, negative caching, right-click refresh/ignore actions, background resolver queue, and no live-feed blocking. Future v0.3.x work can refine entity highlighting and add richer correction UI.

## v0.3 - ESI Entity Recognition

Goal: improve character, corporation, and alliance detection using EVE ESI while keeping the app responsive.

Planned items:

- Optional ESI support for character name detection.
- Corporation and alliance detection.
- Local ESI entity cache.
- Rate limiting and negative caching.
- Background-only resolver queue.
- Offline fallback when ESI is unavailable.
- Manual corrections/ignore list for false positives.

Potential cache location:

```text
cache/esi_entities.sqlite
```

Important rule:

```text
ESI lookups must never block live chat rendering.
```

## v0.3.x - Intel Awareness

Goal: make Signal Bridge more useful as an intel reader, not just a translator.

Planned items:

- Intel classification:
  - hostile
  - clear
  - movement
  - ESS
  - cyno
  - bubble
  - fleet
  - camp
- Watchlist alerts for systems, pilots, ships, or keywords.
- Optional sound alerts.
- Tab flash on watched terms.
- Better count/time parsing such as `+5`, `x3`, `4:30`, and `229m`.
- zKill/EVEWho lookup actions from right-click menus.

## v0.4 - Settings and UX Polish

Goal: centralize configuration and improve overlay usability.

Planned items:

- Proper Settings dialog.
- Theme editor.
- Configurable highlight colors.
- Opacity slider.
- Lock window position.
- Remember window location/monitor.
- Better compact/overlay mode.
- Diagnostics export bundle that avoids including chat logs unless the user explicitly opts in.

## v0.5 - Distribution, Trust, and Release Automation

Goal: make public releases safer and more professional.

Planned items:

- GitHub Actions build pipeline.
- Reproducible release ZIP builds.
- Automatic SHA256 generation.
- Release notes from CHANGELOG.
- Optional VirusTotal scan link/check.
- App version/update check.
- Code signing path to reduce SmartScreen/AV warnings.

Current AV-conscious choices:

- No UPX packing.
- No installer.
- No admin rights.
- Heavy ML packages excluded from the default build.
- Portable ZIP release.
- SHA256 checksums published.



## Planned Feed Interaction / Diagnostics Work

These items are planned next after the tab polish pass. They should preserve the current live-only/no-backfill behavior.

### Feed right-click row menu

Add a context menu on chat feed rows with actions for fast gameplay use.

Planned actions:

- Copy visible line
- Copy original line
- Copy translated line
- Copy sender
- Copy systems
- Copy ships/assets
- Copy URLs

### Nice copy/paste behavior

Copy actions should be clean and predictable:

- Visible line copies exactly what the user sees in the feed.
- Original line copies the raw parsed chat text before translation/display replacement.
- Translated line copies the translated/display text.
- Sender, systems, ships/assets, and URLs copy only those extracted parts.
- Copy actions should work from right-click and later keyboard shortcuts where safe.

### Auto-link URL support

HTTP/HTTPS links in chat rows should be detected and made clickable.

Planned URL behavior:

- Detect `http://` and `https://` links.
- Style links visibly in the feed.
- Open links with the system default browser.
- Provide right-click options to open or copy a URL.
- Avoid unsafe/non-web protocols by default.

### Startup/error log improvements

Launch failures should be easy to diagnose on non-dev Windows machines.

Planned diagnostics:

- Write startup logs to the portable `logs/` folder.
- Capture uncaught exceptions with tracebacks.
- Add an easy way to open logs from the app or package folder.
- Keep release mode windowed/no-console while still preserving useful logs.

### Live-only behavior must be preserved

Backfill should remain disabled by default:

- Existing chatlog files are snapshotted at current end position.
- Opening a tab should not replay old private chats.
- New rows appended after monitoring starts should be shown normally.

## v1.0 Target

Before calling the app v1.0, the goal is to have:

- Stable Windows 10/11 portable build.
- No hard-coded channels or user paths.
- Polished tabs and feed interactions.
- Live-only monitoring by default.
- Stable translation modes.
- GitHub catalog updater.
- Settings dialog.
- Right-click/copy/link support.
- Startup logs and recovery.
- Clear public release process.
- Better AV/signing story.

## Guiding Principles

- Keep the app lightweight.
- Keep gameplay impact low.
- Never block live chat rendering.
- Keep network features optional or clearly visible.
- Prefer local EVE data for EVE terms.
- Use machine translation only for normal free text.
- Avoid surprising users with old/private chat backfill.

- Fixed ESI public lookup to use cache-friendly `universe/ids` exact-name resolution and reduced automatic lookup noise to protect ESI rates.

- Default ESI behavior updated: public cache-first entity recognition is enabled by default, while OAuth/location-aware features remain opt-in.

### Completed v0.3 refinement
- Message-body ESI character candidate detection with system/catalog/link/count exclusion.
- Translation protection for confirmed character names so player names are not translated in EN -> CN mode.
- Color split: ships orange, ESI characters red, non-ship catalog assets/modules purple.
- ESS highlight boundary fix completed: standalone ESS only, no mid-word tagging.
- Feed readability polish completed: clearer sans-serif chat font and improved lowercase pilot-handle ESI detection with plural ship exclusions.
- ESI cache policy updated: negative ESI answers use a 90-day TTL.
- ESI usability refinement completed: visible last-check diagnostics and character exclusion list for false positives/bad names.
- ESI exclusion refinement completed: common individual words such as Link/Jump/Fleet/Gate/ISK/Ship are excluded from character detection and local DB checks.
- ESI UI rendering fix completed: cached/resolved characters hydrate onto rows so logs and screen stay consistent.
- ESI action diagnostics improved: menu checks now show dialogs/logs instead of silently queueing work.
- Live monitor reliability hotfix completed: monitor parsing no longer performs blocking online translation before emitting rows.
- Live monitor DB-stall hotfix completed: runtime monitor uses compact catalog-only enrichment and avoids large SQLite translation DB lookups.
- Feed-render stability hotfix completed: ESS highlighting is Tcl-safe and render errors are logged without stopping queue draining.
- Feed readability hotfix completed: neutral sender names and extra common-word highlight exclusions (`Red`, `enemy`).
- ESI interaction hotfix completed: selected text can be explicitly added as an ESI character and applied to existing rows.
- ESI detection refinement: adjacent chat-name chunks are now split into exact candidates, including uppercase pilot names.
- Exclusion list generalized: one list now suppresses all recognition/highlight colors, not only ESI characters.
- Appearance/display options completed: theme presets, font/color/bold/background controls, preview, reset defaults, and opacity slider.
- Ongoing alias tuning: added shorthand ship aliases for Stabber and Caracal Navy Issue from real intel usage.
- Appearance polish completed: color swatches are shown beside editable hex codes.
- Mobile-style default layout completed: first launch now uses a narrow/tall side-panel window.

### Completed v0.3 display/accessibility polish
- Default window layout is now narrow/tall for side-panel use.
- Appearance / Display Options is implemented with presets, font controls, opacity, swatches plus hex codes, per-category colors, bold toggles, optional background rectangles, and live preview.
- General Exclusion List is implemented and applies globally to recognition/highlight rules.

### Future display ideas
- Optional import/export theme files.
- Optional per-channel appearance presets.
- More colorblind-friendly preset tuning after user feedback.
- Possible click-through overlay mode later, but not planned until normal transparency/overlay use is stable.
- Default exclusion bundling completed: current General Exclusion List entries are shipped as seeded defaults.
- ESI starter-cache bundling completed: verified local character entities are shipped as seeded defaults.

- Completed: bundle starter free-text translation cache for faster first-run/offline reuse of known translations.
- Completed: initial manual review/curation pass for bundled starter translation cache.
- Completed: Appearance dialog fixed footer for mobile-style layouts.
- Completed: non-destructive channel add workflow and automatic newly active channel tabs.
- Completed: compact one-line mobile channel bar replacing stacked tab rows.
### Completed: Settings Center

- Centralized most app configuration into a dedicated Settings Center with sidebar navigation.
- Added pages for General, Channels, Appearance, Translation, EVE Catalog, ESI, Exclusions, Cache & Data, Diagnostics, and About / Support.
- Reduced menu clutter by keeping menus focused on runtime actions and shortcuts into Settings.

Future settings polish:

- Inline editing for channel lists and exclusions directly inside the Settings Center.
- Import/export profile bundles for appearance, exclusions, and starter data.
- More detailed live monitor diagnostics inside the Diagnostics page.
## Must-Have Planned Feature: LAN Web Viewer / Phone View

Signal Bridge should support an optional local LAN web viewer so the app output can be viewed from another device on the same network, such as a phone, tablet, laptop, or second PC.

### User Goal

When enabled, Signal Bridge should serve a lightweight read-only webpage that mirrors the live feed. The app should display:

- a local network URL, for example `http://192.168.x.x:port/`,
- a QR code that can be scanned from a phone,
- basic connection/status information,
- a clear Stop Sharing button.

This lets users keep the main app on the EVE machine while reading translated intel from another screen or phone on the same LAN.

### Required Behavior

- Disabled by default.
- User must explicitly enable LAN sharing.
- Bind to LAN only when enabled; no public internet service by default.
- Show the exact URL and QR code in the app.
- Stream live feed rows to connected browsers.
- Preserve the same selected view/filter when practical, or provide simple browser-side channel filtering.
- Keep the webpage lightweight and mobile-friendly.
- Work on phones and other PCs on the same LAN.
- Continue working if internet is down, because it is local network only.
- Stop the web server cleanly when disabled or when the app exits.

### Security / Privacy Requirements

- Clearly warn that anyone on the same LAN with the URL can view the feed unless a protection option is enabled.
- Prefer a random session token in the URL by default, for example `http://192.168.x.x:port/?token=...`.
- Optional PIN/passphrase protection later.
- Do not expose cache files, settings, logs, ESI tokens, or local filesystem paths through the webpage.
- Read-only viewer only for the first version; no remote control from the phone.
- Localhost/LAN only; no cloud relay.

### Suggested UI Location

Add this under the Settings Center:

```text
Settings > Settings... > LAN Web Viewer
```

Controls:

- Enable LAN Web Viewer
- Port setting, default automatic or `8765`
- Show URL
- Show QR code
- Copy URL
- Regenerate token
- Stop Sharing
- Connected clients count

Add a quick menu shortcut later if useful:

```text
Tools > LAN Web Viewer...
```

### Suggested Implementation

- Use Python standard library or a very small dependency-free HTTP/WebSocket/SSE server.
- Prefer Server-Sent Events for simple live feed streaming if adequate.
- Serve a static mobile-friendly HTML page from memory.
- Keep only a bounded recent-feed buffer, for example last 200-500 rendered rows.
- Send new feed rows to connected clients as JSON.
- Reuse existing sanitized/rendered row data; do not expose raw private internals.
- Generate QR code locally if a small bundled QR implementation is acceptable; otherwise use a simple dependency-light QR module during packaging.

### First Release Scope

Version target: future `v0.4` or `v0.3.x` if small enough.

Initial version should include:

- start/stop LAN viewer,
- URL display,
- QR code display,
- mobile-friendly live feed page,
- read-only streaming,
- tokenized URL,
- basic diagnostics/logging.

Do not include remote control, public internet relay, account login, or ESI/token management through the web page in the first version.
### LAN Web Viewer Theme Matching Requirement

The LAN Web Viewer should visually match the desktop Signal Bridge feed as closely as practical.

Required behavior:

- Reuse the current app appearance settings for the browser view.
- Match normal feed text color, background color, font family, font size, and opacity-friendly contrast where practical.
- Match per-category styles for systems, ESI characters, ships, modules/assets, ESS, translation text, timestamps, links, and sender neutrality.
- Respect user choices for color, bold, and background highlight styles.
- Respect General Exclusion List behavior so hidden/excluded terms are not highlighted in the browser view either.
- Keep the browser view mobile-friendly even when using the same theme.
- Provide a browser fallback theme if a local font is unavailable on the phone.
- Include a refresh/sync mechanism so changing Appearance settings in the app updates or reloads the web viewer theme.

Suggested implementation:

- Export the active appearance settings as a small theme JSON object for the web page.
- Convert Signal Bridge text-tag styles into CSS classes, for example `.system`, `.esi-character`, `.ship`, `.asset`, `.ess`, `.translation`, `.timestamp`, `.link`.
- Send feed rows with semantic spans instead of only plain text so the browser can apply the same colors/backgrounds.
- Use CSS variables generated from the app theme, such as `--feed-bg`, `--text-fg`, `--system-fg`, and `--ship-bg`.
- Keep the first version read-only; theme sync should not allow remote settings edits.

### Intel History add-on MVP foundation — started
- Initial add-on package skeleton exists under `addons/intel-history`.
- Same-EXE guarded loader, event bridge, SQLite sighting storage, dedupe, and health/status display are implemented.
- Next milestones: Pilot Intelligence Card v0.1, manual flags, Hot Drop Risk auto flag, zKill enrichment, import/export packs, and Intel Query Service / LLM entry point.

- Completed first Pilot Info Card and Manual Flags feed slices: feed right-click opens compact pilot summaries, supports manual flag editing/quick flag actions, renders compact badges beside flagged pilots, and Do Not Track prevents future local history recording. Next milestones: richer threat reasons, auto Hot Drop Risk flags, zKill enrichment, import/export intel packs, and Intel Query Service / LLM entry point.

- Completed Intel History Auto Hot Drop Risk v0.1: high-confidence cyno ship classes create temporary explainable flags.
- Future tuning: expose Hot Drop Risk ship classes/duration in settings, add optional watch-only classes such as HICs/Covert Ops, and add dismiss/convert controls for auto flags.
- Completed first UI polish pass covering window chrome/icons, dialog placement, Pilot Info header/date cleanup, context-aware right-click menus, and translation-toggle redraw responsiveness. Remaining polish includes deeper contrast audit, Argos preferred-engine/status flow, more iconography, and optional zKill card integration.


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
