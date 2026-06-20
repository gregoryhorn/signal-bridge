# Contract: RenderRow

`RenderRow` is the future stable display contract consumed by the desktop feed and LAN viewer.

## Proposed fields

| Field | Type | Notes |
|---|---|---|
| `row_id` | string | Stable row identifier |
| `channel` | string | Chat channel |
| `timestamp` | string | Source timestamp |
| `sender` | string | Sender display name |
| `visible_lines` | string[] | Final lines to draw |
| `original_line` | string | Copy-original text |
| `translated_line` | string | Copy-translated text when available |
| `segments` | IntelSegment[] | Structured segments |
| `entities` | object[] | Systems, pilots, ships, links, etc. |
| `spans` | object[] | Future click/right-click spans |
| `diagnostics` | object | Compact decision summary |

## Invariants

- Building a RenderRow must not call network.
- Rendering a RenderRow must not translate, hydrate ESI, or scan large DB/cache state.
