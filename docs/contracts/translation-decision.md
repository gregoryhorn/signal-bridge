# Contract: TranslationDecision

A `TranslationDecision` explains whether a row/segment was translated, skipped, or handled by local catalog/cache.

## Proposed fields

| Field | Type | Notes |
|---|---|---|
| `decision` | string | `used`, `skipped`, `queued`, `error` |
| `reason` | string | Human-readable reason |
| `engine` | string | `catalog`, `cache`, `google`, `argos`, `none` |
| `source_lang` | string | Optional source language |
| `target_lang` | string | Optional target language |
| `cache_hit` | bool | Whether cache was used |
| `duration_ms` | number | Optional timing |
| `error` | string | Redacted error message |

## Invariants

- Translation decisions are safe to show in diagnostics.
- Render path may display an existing decision but must not create one by doing MT work.
