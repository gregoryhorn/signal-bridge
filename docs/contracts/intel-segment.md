# Contract: IntelSegment

`IntelSegment` is a structured piece of intel extracted from one chat row. One raw row may contain one or more segments.

## Fields

| Field | Type | Notes |
|---|---|---|
| `kind` | string | `message`, `sighting`, `kill`, `clear`, or future value |
| `text` | string | Display-safe segment text, raw row remains preserved elsewhere |
| `systems` | string[] | Matched solar systems in this segment |
| `assets` | string[] | Matched ships/modules/items/status assets |
| `pilots` | string[] | Best-effort pilot display names; ESI entity is authoritative elsewhere |
| `notes` | string[] | Short tags like `VOICE` |
| `status` | string[] | Short tags like `NV` |
| `confidence` | string | `low`, `medium`, `high` |

## Display invariant

Segmentation is internal-first. Single-segment rows render as normal chat. Multi-segment rows may split compactly for readability.
