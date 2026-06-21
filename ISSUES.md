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

