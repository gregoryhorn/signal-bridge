# Intel History / Pilot Intelligence Add-On Spec

Status: planned optional add-on
Target: future Signal Bridge release after v0.3
Last updated: 2026-06-19

## 1. Summary

Intel History is the first planned optional Signal Bridge add-on. It adds local pilot memory and intelligence without bloating the core app.

Signal Bridge core remains focused on live monitoring, translation, ESI resolution, appearance/settings, LAN viewer, and Argos offline translation support. Intel History is optional because it stores long-term local data and performs deeper analysis.

The add-on should be stable, lightweight, easy to update, easy to modify, and explainable. It must never block live chat rendering.

## 2. Product Boundary

### Native/core Signal Bridge features

- Live EVE chat monitoring.
- CN <-> EN translation.
- Google translation.
- Argos offline translation support and model management.
- LAN Viewer / Phone View with URL and QR code.
- Settings Center.
- Appearance controls.
- Compact EVE catalog updates.
- ESI public character detection.
- General Exclusion List.

### Optional add-on feature

- Intel History / Pilot Intelligence.

The add-on owns historical pilot sightings, pilot cards, flags, zKill enrichment, import/export, movement summaries, and the read-only Intel Query Service for UI/LLM use.

## 3. Design Goals

- Keep the base app lightweight.
- Use the same SignalBridge.exe for the first version; no separate helper app by default.
- Store data locally in SQLite.
- Track ESI-confirmed pilots by default.
- Store normalized sightings by default, not raw chat dumps.
- Use conservative dedupe, retention, and confidence scoring.
- Run enrichment and maintenance in bounded background queues.
- Never wait on network or scan full history in the live feed path.
- Make all scores/flags explainable with visible reasons and sources.
- Make rules and settings easy to tune with readable JSON files.

## 4. Non-Goals For MVP

- Third-party plugin marketplace.
- Cloud sync or shared central database.
- Automatic public upload of user intel.
- Full raw chat archival by default.
- Full killmail ingestion.
- Vector database, embeddings, or arbitrary AI/RAG stack.
- LLM arbitrary SQL access.
- Complex separate worker processes unless later proven necessary.

## 5. Execution Model

The first add-on implementation should run inside the same SignalBridge.exe process.

The user launches only:

```text
SignalBridge.exe
```

The core app loads the optional add-on from the modules folder if installed and enabled.

Recommended folders:

```text
modules/intel-history/
  module.json
  intel_history.py
  schema.sql
  rules/
    flag_rules.json
    threat_rules.json

user_data/modules/intel-history/
  intel_history.sqlite
  settings.json
  logs/
```

The module must be logically isolated. If it crashes or misbehaves, Signal Bridge should disable it for the session and continue live monitoring.

## 6. Add-On Install / Update Model

Use official GitHub release assets for add-on packages.

Example package:

```text
signalbridge-addon-intel-history-v0.1.0.zip
```

Example remote manifest:

```json
{
  "schema": 1,
  "app": "SignalBridge",
  "addons": [
    {
      "id": "intel-history",
      "name": "Intel History / Pilot Intelligence",
      "version": "0.1.0",
      "url": "https://github.com/gregoryhorn/signal-bridge/releases/download/v0.4/signalbridge-addon-intel-history-v0.1.0.zip",
      "sha256": "...",
      "size_bytes": 1234567,
      "compatible_app": ">=0.4,<0.5",
      "summary": "Pilot profiles, sightings history, flags, and optional zKill enrichment."
    }
  ]
}
```

Install rules:

- Official add-ons only at first.
- User must explicitly install.
- SHA256 verification required.
- App compatibility check required.
- Install from local ZIP should be supported for offline/GitHub-blocked users.
- Add-on code updates must not delete user data.
- Uninstall defaults to removing code only and keeping data.

Settings location:

```text
Settings > Add-ons
```

Actions:

- Install.
- Enable.
- Disable.
- Update.
- Uninstall.
- Install from file.
- Open data folder.
- Copy diagnostics.

## 7. Core Add-On API

The core app emits normalized events; the add-on consumes them asynchronously.

Initial hooks:

```text
on_intel_row(row)
on_character_resolved(character)
on_settings_changed(settings)
on_shutdown()
```

Add-on outputs/hooks:

```text
get_pilot_badges(pilot_id)
open_pilot_profile(pilot_id)
get_context_menu_items(row)
get_settings_page()
get_health_status()
```

The core app should wrap all module calls with error handling and disable the module after repeated failures.

## 8. Ingestion Event Shape

Example normalized row event:

```json
{
  "type": "intel_row",
  "timestamp": "2026-06-19T14:05:00Z",
  "channel": "wc.Vale+Tr+Ge",
  "sender": "Scout",
  "characters": [
    {
      "name": "MisterDanger",
      "character_id": 123456789,
      "confidence": "high"
    }
  ],
  "systems": ["T5ZI-S"],
  "ships": ["Sabre"],
  "assets": [],
  "links": [],
  "raw_text_available": false
}
```

Default ingestion policy:

- Track ESI-confirmed pilots only.
- Honor General Exclusion List.
- Store normalized sightings only.
- Do not store raw chat lines by default.
- Keep low-confidence candidates out of long-term stats unless user enables broader tracking.

## 9. SQLite Schema MVP

Keep the schema small and understandable.

Core tables:

```text
pilots
sightings
pilot_stats
pilot_flags
external_facts
imported_packs
```

### pilots

```text
pilot_id INTEGER PRIMARY KEY
name TEXT NOT NULL
corp_id INTEGER
corp_name TEXT
alliance_id INTEGER
alliance_name TEXT
first_seen TEXT
last_seen TEXT
created_at TEXT
updated_at TEXT
```

### sightings

```text
id INTEGER PRIMARY KEY
pilot_id INTEGER
pilot_name TEXT
timestamp TEXT
system_name TEXT
ship_name TEXT
channel TEXT
confidence TEXT
source TEXT
dedupe_key TEXT UNIQUE
duplicate_count INTEGER DEFAULT 1
created_at TEXT
```

### pilot_stats

```text
pilot_id INTEGER PRIMARY KEY
report_count INTEGER
first_seen TEXT
last_seen TEXT
top_ships_json TEXT
top_systems_json TEXT
threat_level TEXT
threat_reasons_json TEXT
updated_at TEXT
```

### pilot_flags

```text
id INTEGER PRIMARY KEY
pilot_id INTEGER
flag TEXT
label TEXT
icon TEXT
source TEXT
confidence TEXT
reason TEXT
created_at TEXT
expires_at TEXT
active INTEGER
```

### external_facts

```text
pilot_id INTEGER
source TEXT
facts_json TEXT
last_checked TEXT
expires_at TEXT
error_state TEXT
PRIMARY KEY (pilot_id, source)
```

### imported_packs

```text
pack_id TEXT PRIMARY KEY
name TEXT
created_at TEXT
imported_at TEXT
trust_level TEXT
counts_json TEXT
active INTEGER
```

## 10. Indexing

Required indexes:

```text
sightings(pilot_id, timestamp DESC)
sightings(system_name, timestamp DESC)
sightings(ship_name, timestamp DESC)
sightings(channel, timestamp DESC)
sightings(timestamp DESC)
pilot_flags(pilot_id, active)
external_facts(pilot_id, source)
```

Profile views should read summary tables first, not scan the full sightings table.

## 11. Dedupe Rules

Dedupe repeated sightings using a stable key:

```text
pilot_id + system + ship + channel + 3-minute time bucket
```

If a duplicate is seen:

- Increment duplicate_count.
- Update pilot last_seen.
- Do not insert a new sighting row.

Default dedupe window:

```text
3 minutes
```

## 12. Pilot Intelligence Card

Implementation status: first v0.1 source slice completed. Manual Flags v0.1 feed integration is also implemented: compact feed badges, quick right-click flag actions, and Do Not Track future-record suppression. The current source supports right-click `Open Pilot Info`, compact summary view, same-window drill-downs for recent sightings/top ships/top systems, manual flag editing, and copyable summaries. zKill, richer threat scoring, auto flags, imports, and the LLM query entry remain planned.

Right-click an ESI-resolved pilot:

```text
Open Pilot Profile
```

Profile MVP shows:

- Pilot name.
- Corp/alliance if known.
- Reports.
- First seen.
- Last seen.
- Threat level.
- Threat reasons.
- Manual and auto flags.
- Top ships.
- Top systems/regions if known.
- Last 10 sightings.
- zKill summary if enabled.
- Notes.

Suggested tabs:

```text
Summary
Sightings
Flags
zKill
Notes
```

Later tabs:

```text
Movement
Associates
Import Sources
```

## 13. Manual Flags

Manual flags are persistent until user removes them.

Initial flag set:

```text
Hot Dropper
FC
Scout
Watchlist
High Threat
Extreme Threat
Friendly
Do Not Track
Custom
```

Default inline feed flags should remain restrained:

```text
🔥 Hot Drop Risk / Hot Dropper
👑 FC
👁 Scout
⭐ Watchlist
⚠️ High Threat
☠️ Extreme Threat
```

Do not add default inline icons for Dictor, Capital, or Blops. Those can appear as profile facts or inferred roles, not as feed badges.

Inline display settings:

- Icons.
- Text badges.
- Both.
- Hidden.
- Max inline flags: 1, 2, or 3.

## 14. Auto Flags

Auto flags must be temporary, explainable, and reversible.

### MVP auto rule: Hot Drop Risk

If an ESI-confirmed pilot is reported with a cyno/drop-capable ship, add a temporary/session flag:

```text
Hot Drop Risk
```

Reason example:

```text
Reported in Redeemer at 18:42 in T5ZI-S.
```

Default expiry:

```text
current session or 120 minutes
```

User actions:

- Dismiss.
- Convert to manual flag.
- Disable this rule.

## 15. zKill Enrichment

zKillboard integration is an optional enrichment inside the Intel History add-on.

Rules:

- Cache first.
- Background only.
- Rate limited.
- Manual refresh allowed.
- Never block live feed rendering.
- Use ESI character IDs as keys.

Cached facts:

- Recent kills.
- Recent losses.
- ISK destroyed/lost if available.
- Last kill/loss time.
- Top ships.
- Top systems/regions.
- zKill profile URL.

Suggested TTLs:

```text
pilot summary: 12-24 hours
ship pattern facts: 1-7 days
negative/no-data result: 7-30 days
```

Right-click actions:

- Open zKillboard page.
- Refresh zKill Intel.
- Copy pilot intel summary.

## 16. Threat Scoring

Threat score should be simple and explainable.

Labels:

```text
Low
Medium
High
Extreme
```

Every score must show reasons.

Example:

```text
Threat: High
Reasons:
- 127 local reports
- active Hot Drop Risk flag
- 61% sightings in Sabre/Flycatcher
- recent zKill activity
```

No opaque AI-only threat score in MVP.

## 17. Movement History

MVP can show recent movement paths only:

```text
T5ZI-S -> 1DQ1-A -> F7C-H0
```

Later features:

- Common routes.
- Route frequency.
- Ship swap detection.
- Fleet/gang association detection.
- Predictive route hints.

## 18. Import / Export Intel Packs

Intel sharing should use local ZIP/JSONL packs.

Example:

```text
signalbridge-intel-pack-2026-06-19.zip
```

Contents:

```text
manifest.json
pilots.jsonl
sightings.jsonl
flags.jsonl
zkill_facts.jsonl
notes.jsonl
README.txt
```

Default export excludes:

- Raw chat lines.
- Private notes.
- Private channels.
- Account/client names.

Import rules:

- Preview before import.
- Validate manifest.
- Dedupe records.
- Track source pack.
- Assign trust level.
- Local manual flags win by default.
- Imported packs can be removed later.

## 19. Intel Query Service / LLM Entry Point

Create a small read-only service used by UI and future LLM integrations.

Name:

```text
IntelQueryService
```

Initial functions:

```text
get_pilot_profile(name)
search_pilots(text)
get_recent_sightings(pilot, limit)
get_top_ships(pilot)
get_movement_path(pilot, hours)
get_flags(pilot)
get_zkill_summary(pilot)
get_recent_threats(hours)
get_watchlist_hits(hours)
```

Forbidden:

- Arbitrary SQL.
- Full database dumps.
- Raw chat sharing by default.

The LLM should query structured summaries, not raw tables. Answers must cite sources/reasons.

Example compact payload:

```json
{
  "pilot": "MisterDanger",
  "reports": 127,
  "first_seen": "2026-04-14",
  "last_seen": "2m ago",
  "flags": ["Hot Drop Risk", "High Threat"],
  "top_ships": [
    {"ship": "Sabre", "percent": 61},
    {"ship": "Flycatcher", "percent": 25}
  ],
  "sources": ["local_intel", "esi", "zkill", "manual_flags"]
}
```

## 20. Settings

Intel History settings should include:

- Enable Intel History.
- Track ESI-confirmed pilots only.
- Tracked channels.
- Retention period.
- Store raw chat lines, off by default.
- Enable manual flags.
- Enable auto flags.
- Enable zKill enrichment.
- zKill cache duration.
- Inline flag display.
- Max inline flags.
- Import/export controls.
- Database maintenance.
- Copy diagnostics.

Recommended defaults:

```text
Track ESI-confirmed pilots only: on
Store raw chat lines: off
Retention: 90 days
Dedupe window: 3 minutes
Inline max flags: 2
Auto flags: on
zKill enrichment: off until user enables
```

## 21. Maintenance / Health

Maintenance actions:

- Optimize database.
- Rebuild summaries.
- Clear expired data.
- Clear zKill cache.
- Export backup.
- Import backup.
- Open data folder.
- Copy diagnostics.

Diagnostics:

- Add-on installed/enabled status.
- DB size.
- Pilots tracked.
- Sightings stored.
- Oldest retained sighting.
- Pending history jobs.
- Pending zKill jobs.
- Last zKill check.
- Last cleanup.
- Last error.

## 22. Performance Rules

Hard rules:

- Never block live chat.
- Never wait on network in the live feed path.
- Never scan full history for each row.
- Never render giant lists inline.
- Use paged/capped profile views.
- Use bounded queues for history, profile refresh, and zKill work.
- Merge/drop low-priority background work if queues are full.

## 23. Privacy Rules

- Local-first storage.
- No automatic upload.
- No cloud sync in MVP.
- Raw chat off by default.
- Export warns users before sharing sensitive data.
- External LLM integrations, if ever added, require explicit opt-in and clear disclosure of what data is sent.

## 24. Rollout Plan

### Phase 0: Spec and boundaries

- Lock native vs optional boundary.
- Write this spec.
- Define add-on manifest and install flow.

### Phase 1: Add-on manager foundation

- Settings > Add-ons page.
- Official package install/update/disable/uninstall.
- SHA256 verification.
- Safe failure handling.

### Phase 2: Intel History MVP

- SQLite DB.
- ESI-confirmed pilot sightings.
- Dedupe and retention.
- Pilot Intelligence Card.
- Manual flags.
- Hot Drop Risk auto flag.
- Summary tables.

### Phase 3: zKill and import/export

- zKill summary cache.
- Open/refresh zKill actions.
- Intel Pack export/import.
- Trust and source tracking.

### Phase 4: Intel Query Service

- Read-only query API.
- Copyable summaries.
- Basic Intel Query panel.
- Future LLM entry point uses the same service.

### Phase 5: Advanced analysis

- Movement paths.
- Ship swap detection.
- Association detection.
- Route patterns.
- Improved threat explanations.

## 25. Open Decisions

| Topic | Recommendation |
|---|---|
| Install source | GitHub release manifest plus local ZIP install |
| Execution | Same SignalBridge.exe for MVP |
| Retention default | 90 days |
| Raw chat storage | Off by default |
| zKill default | Off until user enables inside add-on |
| Export/import | Include after MVP storage/profile basics |
| LLM entry | Start with read-only query service and copyable summaries |
| Threat labels | Low / Medium / High / Extreme |
| Inline flags | Max 2 by default |

## 26. Acceptance Criteria

The add-on should be considered ready only when:

- Installing/enabling/disabling does not affect live monitoring.
- Live feed continues if the module throws an error.
- ESI-confirmed sightings are recorded and deduped.
- Pilot Profile opens quickly for active pilots.
- Manual flags persist and render inline.
- Hot Drop Risk auto flag is explainable and temporary.
- zKill lookups are cached and background-only.
- Export/import can round-trip a small test pack.
- IntelQueryService returns structured summaries without arbitrary SQL.
- Diagnostics show DB size, counts, queues, and last errors.

## Implementation Status

Current MVP foundation implemented:

- installable source package under `addons/intel-history`,
- guarded same-EXE add-on runtime loader,
- normalized live-row event bridge,
- local SQLite database creation,
- ESI-confirmed pilot sighting capture,
- 3-minute dedupe buckets,
- basic Settings > Add-ons health/status counters.

Not yet implemented:

- Pilot Intelligence Cards,
- manual flags,
- auto Hot Drop Risk flags,
- zKill enrichment,
- import/export packs,
- Intel Query Service / LLM entry point.

## Implemented: Auto Hot Drop Risk v0.1

The first auto-flag rule is intentionally conservative. It creates a temporary `Hot Drop Risk` flag only for ESI-confirmed pilots reported in high-confidence likely-cyno ship classes:

- Force Recon Cruiser
- Expedition Frigate

Black Ops battleships such as Redeemer, Widow, Sin, and Panther are not default inline hot-drop caller triggers. They are drop-fleet/profile context and can later inform zKill/profile analytics without making every Black Ops sighting an immediate caller flag.

The flag reason stores the ship, ship class, system, timestamp, and likely-cyno explanation. The default expiry is 120 minutes.
