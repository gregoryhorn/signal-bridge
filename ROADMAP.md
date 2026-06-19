# Signal Bridge Roadmap

Signal Bridge is a lightweight Windows app for translating chat logs CN -> EN and EN -> CN.

This roadmap is planned work, not a guarantee of exact delivery order. The current focus is keeping the app lightweight, portable, low-impact during gameplay, and useful for live chat/intel readability.

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
