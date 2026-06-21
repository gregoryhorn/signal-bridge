## v0.4 publication note

Signal Bridge v0.4 published the current known issue list alongside the refreshed README, screenshot, packaged alias/exclusion data, and clean translation-cache release assets. Continue using this file for concise public issue tracking.

# Signal Bridge Public Issue List

This list tracks current known issues and follow-up work for the public GitHub repo. It is intentionally concise so users can see what is known without reading the full roadmap.

## Active issues

### 1. Translation Cache Manager usability and deletion

Status: improved in the current source branch.

- The Translation Cache Manager previously allowed deleting manual overrides only, which made cache-backed rows appear impossible to delete.
- The current source branch changes deletion to operate on the selected grouped translation entry: manual override, machine-cache rows, and failure cooldowns for that source/target are removed together.
- A new all-entry reset action clears machine cache, manual overrides, and failure cooldowns while leaving aliases, exclusions, phrase overrides, ESI cache, zKill cache, and settings untouched.

### 2. Translation cache pollution from mixed English/CJK intel

Status: mitigated; cache reset performed for the current source/package data.

- Older cache entries could contain English intel context in the source field.
- The bundled starter translation cache has been removed for now so new portable installs start with an empty translation cache.
- Live translation still uses aliases, phrase overrides, and segment extraction before creating new cache entries.

### 3. Chinese/localized ship coverage

Status: ongoing.

- Catalog-driven CJK ship alias extraction is now used for official localized ship names.
- Curated shorthand aliases are still needed for player slang such as `æµ·é±¼`.
- Report additional bad translations or missed ship shorthand with the original line and the displayed translation.

### 4. Pilot Info and zKill accuracy

Status: recently improved; needs continued live verification.

- Pilot Info now prefers exact character identity and displays the character ID/zKill URL.
- zKill sync falls back when zKill rejects long `pastSeconds` requests.
- Please report examples where a clicked name opens the wrong pilot or zKill activity is missing.

### 5. Release automation and packaging hygiene

Status: planned.

- Keep packaged alias, exclusion, phrase override, and catalog assets aligned with the source branch.
- Avoid shipping local logs, settings, tokens, runtime cache, or personal runtime state.
- Continue improving checksums and release documentation before public builds.

## Reporting template

When reporting an intel parsing or translation issue, include:

```text
Original chat line:
Displayed translation:
Expected output:
What was highlighted wrong or missing:
```

For Pilot Info or zKill issues, include:

```text
Clicked pilot name:
Expected character ID or zKill URL:
What Pilot Info showed instead:
```


## Fixed: Intel History missing-module modal loop

- Status: fixed in v0.4 source refresh.
- Symptom: users without the optional Intel History module could see repeated dialogs when passive Pilot Info/feed code queried Intel History data.
- Fix: passive calls are silent and record health state; explicit user actions still show one install/enable notice.
- Packaging follow-up: the official Intel History add-on code is now bundled in the portable ZIP by default.

## User feedback: Backlog chat ingest option

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: Settings / chatlog monitor startup

Users need an option to ingest recent backlog chat on app load.

Requested behavior:

- Add a dedicated setting under Settings.
- Default behavior remains live-only unless enabled.
- When enabled, default backlog window should be 10 minutes.
- Add a manual override allowing users to select several hours.
- Must avoid replaying old private messages or overwhelming the feed.
- Should clearly label this as startup backlog ingest / recent chat backfill.

Acceptance notes:

- Setting is visible in a dedicated Settings spot, not hidden in diagnostics.
- Startup ingest respects selected minutes/hours.
- Deduplication still prevents duplicate rows across clients/logs.
- Live monitoring continues after initial backlog ingest.

## User feedback: Ships initially highlighted purple on first load

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: entity detection / first render / catalog hydration

On a user PC, some ships were highlighted as purple assets/modules when the app first loaded.

Reported examples:

- Retribution
- Caracal

Expected behavior:

- Ships should highlight with the ship color, not purple asset/module color.
- First render should use the same ship/category classification as subsequent renders.

Investigation notes:

- Likely first-load ordering issue where catalog/category hydration is not complete before initial render.
- Could also be stale cache/classification metadata or alias-corrected asset detection running before ship-type classification.
- Need reproduce on clean portable profile and compare first render vs redraw after catalog load.

## User feedback: Pilot Info card size still incorrect on load

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: Pilot Info UI / window sizing

The Pilot Info card still opens at the wrong size on load.

Expected behavior:

- Pilot Info should open compactly by default.
- Footer actions should remain visible.
- The card should not require unnecessary scrolling for normal profile content.
- Window size should be stable and appropriate on first open, not only after manual resize/reopen.

Investigation notes:

- Recheck initial geometry calculation, minsize/maxsize, update_idletasks timing, and content-frame requested size.
- Verify behavior on normal, high-DPI, and narrow/mobile-style layouts.

## User feedback: Channel add/open menu not showing channels correctly

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: channel discovery / Add/Open Channels menu / tracking startup

A user reported that chat channels are not showing properly in the Add/Open Channels menu. They also had to add channels again before the app started tracking those chats properly.

Reported symptoms:

- Add/Open Channels menu does not list available channels correctly.
- Previously known/selected channels may not appear as expected.
- The app may not begin tracking some channels until the user manually adds them again.
- Screenshot provided by user for UI context.

Expected behavior:

- The Add/Open Channels menu should show discovered EVE chat channels clearly and consistently.
- Previously selected channels should persist across restarts.
- Tracking should resume automatically for persisted/enabled channels without requiring the user to re-add them.
- Missing/closed channels should be marked clearly rather than silently dropped.
- The menu should distinguish discovered, active, hidden, closed, and unavailable channels.

Investigation notes:

- Check channel discovery from chatlog filenames vs persisted channel state.
- Verify startup ordering between chatlog scan, settings load, channel tab restore, and monitor start.
- Check whether persisted channels are being filtered out if no current-session log exists yet.
- Check whether dynamic channels are only activated after manual Add/Open action.
- Validate behavior on a clean portable profile and an upgraded profile with existing channel settings.
- Ensure multi-client logs and channel names with punctuation/plus signs still dedupe and map correctly.

Acceptance notes:

- Fresh install lists channels found in the configured EVE chatlog folder.
- Existing install restores previously selected channels after restart.
- Tracking starts for enabled channels without manual re-add.
- Add/Open Channels menu accurately shows channel state.
- Diagnostics should include channel discovery count, active tracking count, and any channels skipped with reason.

## User feedback: Purple asset/module highlighting should be off by default

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: Appearance / Display Options / entity highlighting

Users report that purple text for non-ship assets/modules is visually distracting and should be disabled by default.

Requested behavior:

- Turn purple non-ship asset/module highlighting off by default for new installs.
- Keep a Settings option to re-enable it.
- Preserve ship, system, ESS, hostile, and ESI pilot highlighting defaults.
- Existing users should keep their explicit display preference where possible.

Acceptance notes:

- Fresh portable profile starts with purple asset/module highlighting disabled.
- Appearance/Display settings clearly expose the toggle.
- Ships still use the ship color, not purple.

## User feedback: Help menu needs a proper help system

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: Help menu / documentation UX

The current Help menu is not sufficient. Users need an in-app help system rather than only scattered docs or About text.

Requested behavior:

- Add a proper Help menu section/window.
- Include quick help for setup, chatlog folder selection, channel tracking, translation modes, aliases, exclusions, Pilot Info, Intel History, and diagnostics.
- Include links to README, ISSUES.md, releases, and GitHub documentation.
- Help should be readable offline from the portable ZIP where possible.

Acceptance notes:

- Help menu has clear user-facing entries, not just debug/about actions.
- New users can find setup and troubleshooting steps without visiting GitHub first.

## User feedback: About and Support need a dedicated menu

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: menus / About / Support UX

About and Support should have a dedicated menu or clearly separated menu section.

Requested behavior:

- Add a dedicated About/Support menu or top-level menu item.
- Include version, release link, GitHub link, issue-report link, diagnostics copy action, and donation/support information.
- Keep support information easy to find and separate from general Help documentation.

Acceptance notes:

- Users can quickly find the app version, support links, and donation/support details.
- About/Support is not buried inside unrelated settings.

## User feedback: Google default translation should auto-detect all non-English languages

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: translation engine / language detection

If Google translation is the default engine, the app should automatically detect and translate any non-English language, not only Chinese.

Reported expectation:

- Russian and other non-English languages should translate by default when translation is enabled.

Requested behavior:

- Auto-detect non-English source text when Google is selected/default.
- Translate detected non-English content to English by default.
- Continue protecting EVE terms, systems, ship names, pilot names, URLs, and known aliases.
- Avoid sending pure English lines unnecessarily.
- Show translation source/status clearly in diagnostics or Translation Cache.

Acceptance notes:

- Russian sample text translates to English with Google/default mode enabled.
- Chinese still translates correctly.
- Mixed EVE intel lines preserve protected EVE terms.
- Translation remains background/non-blocking and never freezes the UI.

## User feedback: Add content and sender filter/block settings

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: Settings / filtering / feed hygiene

Users need a filter option in Settings to block or filter messages by content keyword or by sender/user.

Requested behavior:

- Add a dedicated Settings page/section for filters.
- Allow keyword/content filters.
- Allow sender/user filters.
- Support enable/disable per filter.
- Support case-insensitive matching by default.
- Optionally support exact, contains, and regex modes later.
- Filtered messages should not clutter the main feed.
- Diagnostics should show filtered-message counts.

Acceptance notes:

- User can add a keyword and matching messages are hidden or suppressed.
- User can add a sender name and messages from that sender are hidden or suppressed.
- Filter settings persist across restarts.
- There is a safe way to review/edit/delete filters.

## User feedback: Add local-channel spam and ASCII-art rate limiting

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: feed hygiene / Local channel / spam control

Local chat can be spammed heavily, including ASCII-art messages. The app needs rate limiting or suppression controls so spam does not overwhelm the feed or UI.

Requested behavior:

- Add per-channel rate limiting, especially for Local.
- Detect and suppress repeated messages from the same sender within a short window.
- Detect very long ASCII-art or symbol-heavy messages.
- Optionally collapse spam bursts into a single summary row.
- Keep important intel messages visible.
- Expose settings so users can tune or disable spam controls.

Acceptance notes:

- Repeated Local spam does not flood the feed.
- ASCII-art messages can be hidden/collapsed.
- Rate limiting does not block normal intel reports.
- Diagnostics include suppressed/rate-limited counts.

## User feedback: Translation Cache page layout hides important controls

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: Settings / Translation Cache UI / layout

The Translation Cache Manager is still not laid out well. If the user does not expand the page/window, they may not know that more options are hidden off the page.

Reported symptoms:

- Important buttons/options are hidden unless the page is expanded.
- The Original and English tables are too wide.
- The wide tables make the editor controls harder to see and use.
- Users may not realize there are more controls below or off-screen.

Requested behavior:

- Make the Translation Cache page usable at the normal Settings window size.
- Reduce the default width of the Original and English tables so both columns fit better.
- Keep the Original and English edit boxes visible without requiring window expansion.
- Keep action buttons visible or move them into a fixed action bar.
- Use clearer spacing, labels, and scroll behavior so hidden options are obvious.

Acceptance notes:

- At default Settings size, users can see the row lists, edit boxes, and main actions.
- The page should not feel like a raw debug table.
- No critical action should be hidden without a visible scroll cue or fixed action bar.

## User feedback: Translation Cache still contains English in Original and English fields

- Status: open
- Priority: high
- Reported: 2026-06-21
- Area: translation cache / segmentation / cache hygiene / design review

The Translation Cache still has bugs where English chat/content appears in both the Original and English sides. This needs an in-depth review and planning before another fix is attempted.

Reported symptoms:

- Some Original/source rows contain English instead of only the translatable source segment.
- Some rows may have English duplicated into both Original and English.
- This makes the cache editor confusing and suggests cache keys are still being polluted by already-English chat or mixed intel lines.

Review goals:

- Re-review the full translation-cache data model.
- Separate machine cache, manual overrides, source segments, rendered display text, and diagnostics clearly.
- Confirm when English-only messages should be ignored entirely.
- Confirm when mixed EVE intel lines should cache only the non-English segment.
- Confirm how protected EVE terms, aliases, systems, ships, pilots, URLs, and counts are removed/restored.
- Confirm how grouped rows should decide the displayed Original and English values.
- Design a cleanup/migration for existing polluted rows.

Acceptance notes:

- English-only chat should not create translation cache rows by default.
- Mixed intel should cache the translatable non-English segment, not the whole rendered line.
- Manual overrides must remain easy to inspect/edit.
- Cleanup should be safe and should preserve user-created manual corrections where possible.
- A design review should be documented before implementation.

## User feedback: Intel History should be enabled by default

- Status: open
- Priority: medium
- Reported: 2026-06-21
- Area: Intel History / Add-ons / default settings

Intel History is now bundled in the portable ZIP by default, but users also want it enabled by default.

Requested behavior:

- Fresh installs should have Intel History enabled by default.
- The bundled `modules/intel-history` add-on should load automatically if present.
- Users should still be able to disable Intel History in Settings > Add-ons.
- If Intel History fails to load, the app should keep the missing-module/failure guard and continue running.

Acceptance notes:

- Clean portable profile starts with Intel History installed and enabled.
- Settings > Add-ons shows Intel History as installed/enabled/healthy when the module loads.
- Existing users keep their explicit enable/disable preference where possible.
- Startup remains safe: no modal loop and no blocking if the module is unavailable.


## Open: Dedicated settings tab and sub-page design pass

- Status: open
- Priority: medium
- Area: Settings / UX design / dialogs
- Reported: user feedback

### Feedback

Settings has grown into many tabs and sub-pages, and each page needs a focused design pass instead of isolated control-by-control fixes.

### Requested outcome

- Review every Settings tab and sub-page individually.
- Keep important controls visible at normal Settings window size.
- Avoid hidden actions that require expanding the window to discover.
- Use consistent spacing, section titles, help text, and action placement.
- Make modal sub-dialogs open above Settings/main app reliably.
- Keep destructive actions visually separated and clearly confirmed.
- Prefer compact two-column or responsive layouts where tables/editors are currently too wide.

### Candidate pages

- General
- Channels
- Appearance
- Translation
- Translation Cache
- EVE Catalog
- Aliases
- ESI
- Exclusions
- Add-ons
- Cache & Data
- Diagnostics
- About / Support

### Acceptance criteria

- Each Settings page has a clear primary purpose.
- Important controls are visible without resizing on the default Settings size.
- Nested dialogs are parented/transient/modal correctly and do not open behind other windows.
- Tables and editors resize gracefully on narrow/mobile-style layouts.
- Help text explains impact without making pages feel like debug tools.


## Open: False system detection for decimal/security values such as 9.2

- Status: open
- Priority: medium
- Area: entity detection / system highlighting / aliases
- Reported: user feedback with screenshot

### Feedback

`9.2` is being detected/highlighted as a system even though it is not in the alias list and should not be treated as an EVE system name.

### Expected behavior

- Decimal values like `9.2`, `7.5`, `10.0`, and similar numeric values should not be detected as systems.
- Security/range/count-style numbers should remain plain text unless they are part of a valid, known entity.
- System detection should require a valid EVE system code/name from the catalog or an explicit user alias.

### Investigation notes

- Check whether this comes from a hardcoded system regex rather than aliases.
- Review `SYSTEM_RE`, catalog lookup fallback, alias replacement, and render-time highlight paths.
- Verify decimal tokens are excluded before system/entity classification.
- Confirm the fix does not break real nullsec-style systems such as `15W-GC`, `UH-9ZG`, `4-HWWF`, or `1DQ1-A`.

### Acceptance criteria

- `9.2` is not highlighted as a system.
- Similar decimal values are not highlighted as systems.
- Valid EVE system codes still highlight correctly.
- The exclusion is handled in detection logic, not by adding one-off aliases.

## Fixed: Hyperlink enable/disable setting

- Status: fixed in v0.4 source refresh\n- Priority: Medium\n- Area: Settings / feed rendering / safe URL handling\n- Type: user feedback / settings feature

### User feedback

Users should have a Settings option to enable or disable clickable hyperlinks in the chat feed.

### Expected behavior

- Hyperlinks should be enabled by default.
- Users should be able to disable clickable links from Settings.
- Disabled links should remain visible as plain text so copy/paste still works.
- The setting should persist across restarts.
- The setting should apply to URLs detected in live chat, translated text, copied visible text behavior where relevant, and any context-menu link actions.

### Investigation notes

- Check current URL/link detection and rendering paths.
- Ensure only safe URL schemes are clickable, for example `http` and `https`.
- Avoid auto-opening links; clicking should require explicit user action.
- Make sure disabling hyperlinks does not affect EVE entity highlighting, ship/system highlighting, Pilot Info, or zKill buttons.
- Add this to the dedicated Settings design pass so placement is consistent.

### Acceptance criteria

- Settings contains a clear `Enable clickable hyperlinks` option.
- Fresh installs default to enabled.
- Existing users get enabled unless they explicitly turn it off.
- When disabled, URLs render as plain text and are not clickable.
- When enabled, URLs are clickable using safe URL handling.
- The setting is documented in README/help/release notes when implemented.

