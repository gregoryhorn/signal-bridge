## v0.4 publication note

Signal Bridge v0.4 published the current known issue list alongside the refreshed README, screenshot, packaged alias/exclusion data, and clean translation-cache release assets. Continue using this file for concise public issue tracking.

# Signal Bridge Public Issue List

This list tracks current known issues and follow-up work for the public GitHub repo. It is intentionally concise so users can see what is known without reading the full roadmap.

## Active issues

## Fixed: Feed briefly reverts to raw/old render state when new chat arrives

- Status: fixed in source / v0.4 refresh
- Priority: high
- Area: feed rendering / redraw stability / translation display / row model
- Type: bug / UX

A live-feed redraw could briefly show an older/raw-looking intermediate state when a new chat or translation update triggered a redraw. Normal-sized feed redraws now render atomically instead of exposing chunked half-redraw states, while very large redraws still use chunking for responsiveness.

### Fix summary

- Added an atomic redraw path for normal live-feed sizes.
- Kept chunked redraws for very large visible feeds.
- During chunked redraws, keep the bottom view pinned when the user was already at the bottom.
- Added `last_redraw_mode` diagnostics so redraw behavior can be inspected.
- Source GUI was restarted and visually inspected after the patch.


## Open: Translation Corrections layout gives too much width to Original and squeezes English

- Status: open
- Priority: high
- Area: Settings / Translation Cache / Translation Corrections / UI layout
- Type: bug / UX

The Translation Corrections page still lays out the Original and English lists unevenly. The Original list consumes almost all available horizontal width, while the English list is squeezed into a very narrow right-side column. This makes the English translation preview hard to read and makes the correction workflow feel like a cramped debug table instead of a user-friendly editor.

### Reported behavior

- The Original table/list is much wider than needed.
- The English table/list is too narrow and cuts off most translation text.
- The middle area appears wasted while the right-side English column is cramped.
- Users cannot easily compare original text with the English translation.
- The page still does not feel like a clear correction workflow.

### Desired behavior

- Original and English preview areas should be balanced and readable at the default Settings window size.
- The English side should have enough width to read normal translation text without severe truncation.
- The editable Original/source phrase box and English correction box should remain clearly visible.
- The page should behave like a Translation Corrections editor, not a raw cache/debug browser.
- Advanced cache internals should remain hidden unless explicitly enabled.

### Design direction

- Replace the current uneven split with a balanced layout, such as 50/50 Original and English columns, or a single table with Original and English preview columns plus a dedicated editor area below.
- Keep action buttons visible near the top or in a fixed action area.
- Ensure the English correction editor is visually primary and easy to use.
- Avoid horizontal scrolling for normal translation text where possible.
- Preserve the ability to show cache internals as an advanced option.

### Acceptance criteria

- Visual inspection before and after the fix.
- At default Settings size, the English list is readable and no longer squeezed into a tiny column.
- Original no longer consumes most horizontal width.
- Users can select a row and clearly see both Original/source and English/correction text.
- Save, delete, cleanup, and cache-status actions remain visible and usable.
- Resizing the Settings window improves available space instead of leaving the English side cramped.
- Manual overrides and existing cache/correction behavior continue to work.


### Recently fixed: Feed Translation Stability Pass

- Translated Only mode now uses a stable `Translating...` pending row for non-English text instead of flashing original text before English arrives.
- Translation-result redraws preserve the feed scroll position and only return to bottom when the user was already at the bottom.
- Non-translatable rows are skipped before queueing background translation work to reduce unnecessary redraw pressure.


### Recently fixed: ESI Name Recognition P1

- Multi-word ESI character names now prefer full resolved spans over partial word matches.
- Short suffix names such as `Picard X` are preserved and submitted before shorter overlapping candidates.
- Ordinary chat noise such as `channel changed`, `thanks fc`, and `where are they` is rejected earlier by candidate gating.
- Feed separators no longer split a full pilot name into partial terms such as `Matek · Bathana`.


## Fixed: ESI character detection drops short suffix tokens such as Picard X

- Status: fixed in source / v0.4 refresh
- Priority: high
- Area: ESI detection / pilot highlighting / name boundary handling / Pilot Info
- Type: bug

A character whose full name includes a short suffix token can be detected or displayed as the shorter partial name. The reported example is `Picard X`, where Signal Bridge appears to detect/display `Picard` without the `X`. The short suffix is part of the character name and must be preserved.

### Reported behavior

- `Picard X` is the actual character name.
- Signal Bridge is not getting/preserving the `X` suffix.
- Pilot-related actions may target `Picard` instead of `Picard X`.
- Screenshot provided for context.

### Root-cause areas to review

- Candidate trimming may remove one-letter trailing tokens as noise.
- Name-boundary regex may not treat single-letter suffixes as valid pilot-name parts.
- ESI cache hydration may prefer a shorter partial match over the full resolved name.
- Longest-match span selection may be missing or not applied before rendering/click targeting.
- Right-click Pilot Info may map to a partial token instead of the full ESI-confirmed pilot.

### Desired behavior

- `Picard X` should resolve/display as `Picard X`.
- The `X` suffix should not be dropped or treated as noise.
- If both `Picard` and `Picard X` are candidates, the full/longest ESI-confirmed name should win.
- Pilot Info, zKill, Intel History, flags, and right-click actions should use the correct character ID/name.
- The fix should not create broad false positives from random one-letter words.

### Acceptance criteria

- `Picard X` displays/highlights as one full pilot/entity.
- Pilot Info opens for `Picard X`, not `Picard`.
- The short suffix token remains part of the entity span.
- Existing multi-word pilot behavior such as `Matek Bathana` remains correct.
- Single-letter suffix support does not make common chat text overly broad.
- Add a targeted test/fixture for a single-letter pilot suffix.


## Fixed: ESI character names can be split into separate highlighted tokens

- Status: fixed in source / v0.4 refresh
- Priority: high
- Area: ESI detection / pilot highlighting / feed rendering / entity spans
- Type: bug

A single EVE character name can be rendered as separate highlighted pieces, for example `Matek · Bathana`, even though `Matek Bathana` is one character. Full resolved ESI character names should render as one entity span and should win over partial word-level matches.

### Reported behavior

- A full character name is visually split into separate highlighted tokens.
- A separator dot can appear between parts of the same pilot name.
- The example from the screenshot is `Matek · Bathana`.
- The expected display is `Matek Bathana` as one pilot/entity.

### Root-cause areas to review

- ESI candidate generation may split a multi-word character into separate one-word candidates.
- Cached/resolved ESI hydration may add both full-name and partial-name entities to the same row.
- Feed entity-span rendering may insert separators between adjacent spans without checking whether they belong to the same resolved character.
- Word-boundary/pilot-tag logic may tag each word separately instead of preferring the longest resolved ESI entity span.
- Right-click span targeting may point to a partial token instead of the full ESI-confirmed pilot.

### Desired behavior

- Full resolved ESI character names should be treated as one entity span.
- Multi-word pilot names should not be split with a separator dot.
- If both full and partial matches exist, the full/longest resolved ESI name should win.
- Pilot Info right-click should target the full character, not a partial word.
- Separators should only appear between different entities, not inside one character name.

### Acceptance criteria

- `Matek Bathana` displays/highlights as one pilot/entity.
- No separator dot appears between `Matek` and `Bathana`.
- Right-click Pilot Info opens for `Matek Bathana`, not `Matek` or `Bathana` separately.
- Full resolved ESI names override overlapping partial candidates.
- Existing adjacent separate-pilot detection still works.
- Add a regression fixture or targeted test for a two-word pilot name.


## Fixed: Feed text jumps when Chinese text switches to English translation

- Status: fixed in source / v0.4 refresh
- Priority: high
- Area: feed rendering / translation display / row layout stability
- Type: bug / UX

When Chinese chat text is translated into English, the visible feed row can change size or layout after the translation arrives, causing a distracting jumping effect in the feed. This is especially noticeable in Translated Only mode or during bursts of translation completions.

### Reported behavior

- Chinese text appears first, then switches to English.
- Rows shift up/down when the English translation arrives.
- The user loses visual position while scanning live intel.
- The effect is annoying during active chat monitoring.

### Root-cause areas to review

- Async translation updates changing row height after first render.
- Translated Only mode rendering original text before translated text is ready.
- Feed redraws not preserving scroll/anchor position during translation updates.
- Translation line visibility toggling after a row is already visible.
- Batch/chunked redraw behavior making translation updates more noticeable.

### Desired behavior

- Chinese rows should not visibly jump when English translation arrives.
- Translated Only mode should not flash original Chinese before English if translation is pending.
- Cached translations should render immediately with no layout shift.
- Pending translations should use a stable placeholder or reserved layout if needed.
- If the user has scrolled up, async translations should not yank the viewport.
- If the user is at the bottom, auto-scroll should remain smooth.

### Acceptance criteria

- Visual inspection before and after the fix.
- Reproduce the jumping behavior with live or fixture CJK rows before patching.
- Fix the rendering/layout root cause, not individual translation strings.
- Verify cached translations render without jumping.
- Verify pending translations do not cause repeated row-height changes.
- Verify translation failures fall back without repeated layout shifts.
- Verify feed performance remains non-blocking.


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

## P1 Bug: Translation Cache still contains English in Original and English fields

- Status: open / P1
- Priority: P1 / High - requires visual inspection before and after fix
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
### Visual inspection requirement for English-original cache bug

This is now a P1 bug. Any fix must include visual inspection before and after implementation.

Before fixing:

- Open Settings > Translation Cache at normal/default Settings size.
- Capture or visually inspect rows where the Original/source field contains English-only or mostly-English text.
- Record examples from the UI, including Original, English, target language, engine/source type, and duplicate count where visible.
- Confirm whether the problem appears in Auto -> EN rows, EN -> CN rows, or both.
- Save a before screenshot or record exact visual findings.

After fixing:

- Re-open Settings > Translation Cache at normal/default Settings size.
- Confirm English-only Original rows are gone from Auto -> EN cache results.
- Confirm valid EN -> CN rows, if any, are clearly separated or labeled by target/direction.
- Confirm newly generated cache rows do not reintroduce English-only Original entries during live monitoring.
- Confirm manual overrides still work and are not deleted by cleanup.
- Include before/after screenshots or a visual verification note in PR/release notes.

### Root-cause checks required

- Review segmentation before cache lookup/write.
- Add or verify a central `should_cache_translation_source(...)` gate.
- For Auto -> EN, reject English-only, URL-only, system-only, pilot-only, and protected-term-only source text.
- For EN -> CN, allow English source only when target language/direction is explicitly Chinese.
- Add a cleanup/dedupe path for existing polluted rows.

## Fixed: Intel History enabled by default

- Status: fixed in v0.4 source refresh
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


## Fixed: False system detection for decimal/security values such as 9.2

- Status: fixed in v0.4 source refresh
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


## P1 Bug: Translation Cache page layout hides controls and tables are too wide

- Status: open / P1
- Priority: P1 / High - requires visual inspection before and after fix
- Area: Settings / Translation Cache / UI layout

### Visual inspection requirement

This is now a P1 UI bug. Any fix must include visual inspection before and after implementation.

Before fixing:

- Capture or inspect the current Translation Cache page at the normal/default Settings window size.
- Confirm which controls are hidden below the fold or off-page.
- Confirm the Original and English tables/editors are too wide for normal use.
- Save the before screenshot or record the exact visual findings.

After fixing:

- Re-open Settings > Translation Cache at the normal/default Settings window size.
- Capture or inspect the corrected page.
- Verify important controls are visible without needing to expand the Settings window.
- Verify Original and English tables/editors fit better and remain usable.
- Verify action buttons such as Save, Delete Selected Entry, Delete All Entries, Clean Duplicates, and Cache Status are discoverable.
- Include before/after screenshots or a visual verification note in the PR/release notes.





### Decimal system false positive fix notes

- Added a shared numeric/decimal token guard so values like `9.2`, `7.5`, and `10.0` are never treated as systems by catalog or alias-based system matching.
- Valid EVE system codes such as `15W-GC`, `UH-9ZG`, `4-HWWF`, and `1DQ1-A` remain valid.

## Fixed: Channel add/open menu not showing channels correctly

- Status: fixed in v0.4 source refresh
- Priority: high
- Area: channel discovery / Add/Open Channels menu / tracking startup
- Fix summary: Add/Open Channels now merges recent chatlog discovery with persisted active, hidden, and saved tab state so previously tracked channels remain visible even when no current chatlog file exists. The chooser now shows tracking/discovered/hidden/waiting statuses, uses consistent modal stacking, and saved channels continue waiting for new log files after restart instead of requiring manual re-add.
- Validation: compile passed; helper validation confirmed discovered channels, persisted missing active channels, hidden channels, and discovered-only channels are categorized correctly.

## Recently resolved in v0.5

- Resolved Translation Corrections layout/design issue with aligned panes, clearer button hierarchy, and advanced controls hidden behind a toggle.
- Resolved broad legacy exclusion cleanup by replacing it with scoped Recognition Rules and bundled parser-noise defaults.
- Added inline Recognition Rules help as the first local help pattern; broader Help Center remains future work.

## P1 UX/Data Issue: Pilot Info card layout and zKill usefulness

- Status: open / needs design
- Priority: P1 / High
- Area: Pilot Info / zKill integration / UI layout
- Type: user feedback / UX and data-quality improvement

### User feedback

The Pilot Info card is badly laid out and wastes too much space. Some buttons are hidden at the bottom because the window is not auto-sized, forcing the user to resize the window every time it opens.

The zKill section also does not show the most useful information. It should show recent kills and recent losses in a way that helps quickly judge a pilot.

### Problems to solve

- Pilot Info window does not auto-size well for its content.
- Important buttons can be hidden below the fold at the default/opening size.
- Layout wastes space and does not prioritize the most useful pilot information.
- zKill data is not currently presented as a useful recent activity view.
- The card should not require manual resizing every time it opens.

### Desired behavior

- Pilot Info should open at a useful default size, or auto-size to its current content within sane screen bounds.
- Primary actions should always be visible without resizing.
- The layout should reduce wasted space and make high-value sections easier to scan.
- zKill should show separate recent activity lists:
  - recent kills
  - recent losses
- Each listed kill/loss should link to the relevant zKill page.
- The recent-kill list should prioritize more meaningful/smaller engagements over huge killmails.

### zKill prioritization notes

For recent kills, killmails with many participants are often lower-value for judging the pilot. If a killmail has many involved characters, for example more than 10, it should be lower priority than killmails with only a few participants.

The app cannot show every killmail, so the design needs a ranking/filtering strategy.

Potential strategy to evaluate:

- Always show recent losses separately because they are usually highly informative.
- For kills, prefer recent killmails with fewer involved parties.
- De-prioritize very large fleet killmails unless there are too few smaller engagements.
- Show a compact capped list, for example 5 recent kills and 5 recent losses.
- Include a link to open the full zKill profile for deeper review.
- Consider labels such as `solo/small gang`, `fleet`, or `large fleet` based on participant count.

### Acceptance criteria

- Pilot Info opens at a usable size with important buttons visible.
- User does not need to resize the Pilot Info window every time.
- Layout visibly wastes less space.
- Recent kills and recent losses are shown as separate sections.
- Each listed kill/loss has a clickable zKill link.
- Recent kills are ranked so smaller/more informative engagements are favored over very large killmails.
- If not enough small kills exist, the card can still show larger killmails as fallback.
- Visual review is performed before marking fixed.

