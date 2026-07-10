# Contract: DiagnosticEvent

Diagnostic events are structured JSONL records written under `logs/`.

**Implemented in:** `sb_diagnostics.py` + `sb_contracts/diagnostic_event.py` (`redact_context`, `make_diagnostic_event`).

## Common fields

| Field | Type | Notes |
|---|---|---|
| `ts` | string | Local timestamp with timezone |
| `type` | string | Event type |
| `duration_ms` | number | Optional duration |
| `action` | string | Optional user/app action |
| `context` | object | Optional redacted detail |

## Privacy rules

Diagnostic events must not include OAuth tokens, client secrets, API keys, or auth headers. Raw chat in exported bundles should be opt-in.
