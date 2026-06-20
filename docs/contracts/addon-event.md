# Contract: AddonEvent

Add-ons should receive narrow, versioned events instead of arbitrary GUI internals.

## Proposed fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | number | Contract version |
| `type` | string | Event type, e.g. `row`, `entity_resolved`, `settings_changed` |
| `timestamp` | string | Event timestamp |
| `data` | object | Contract-specific payload |

## Add-on invariants

- Add-ons must fail isolated.
- Add-ons should not block the live feed.
- Add-ons should not mutate raw row data directly.
