# Pilot Info Snapshot Contract

Purpose: compact local/cache-first data used by the Pilot Info card. Opening the card must not call zKill, ESI, Google, Argos, or perform unbounded scans.

Required shape:

```json
{
  "schema_version": 1,
  "pilot": {"pilot_id": 0, "name": "", "corp_name": "", "alliance_name": ""},
  "report_count": 0,
  "recent_sightings": [],
  "top_ships": [],
  "top_systems": [],
  "flags": [],
  "zkill": {"status": "not_synced|syncing|synced|failed", "synced_at": null}
}
```

Display rules:
- Empty values render as muted `—` or `Unknown`, not repeated dashes.
- Counts of 1 are hidden in compact activity rows.
- zKill is manual, cache-first, background-only, timeout-protected, and diagnostic-logged.
## Tactical normalization

- `No visual` / `nv` are statuses, not ship names. Display ship as `Unknown` and status as `No visual`.
- zKill summaries may include `recent_events[]` with type, time, ship, value, and ids.
- Priority rules: same-day zKill event = HIGH, same-week event = MED, same confirmed ship = HIGH.
- The Pilot Info body may scroll, but footer action buttons must remain visible.
