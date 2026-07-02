# Translation Cache Data Model Design Review

Date: 2026-07-03
Status: implementation-ready

## Problem

The Translation Corrections page groups machine-cache rows and manual overrides by source text. If the machine cache stores English-only chat, URL-only text, placeholder-only text, or protected EVE terms as Auto to EN source rows, the UI shows confusing Original and English pairs that users cannot trust.

## Data Boundaries

- Raw chat text stays on the row and is never rewritten by cache cleanup.
- `translation_source_for_cache(text, direction)` derives the smallest source segment used for lookup and optional persistence.
- `TranslationCache.put_machine(...)` is the storage boundary for machine-cache writes.
- `should_cache_translation_source(...)` is the central predicate used by `put_machine(...)` and cleanup.
- `translation_overrides` stores user corrections and is not cleaned by automatic machine-cache cleanup.
- `translation_cache` stores machine outputs only when the source text is useful as a future correction key.
- `translation_failures` tracks cooldowns and follows the same source-key boundary as machine-cache rows.

## Auto to EN Rules

Auto to EN may persist only source text with genuine non-English language content.

It must reject:

- empty text
- English-only text
- URL-only text
- count-only text
- `SBX` placeholder-only text
- protected EVE term-only text such as a system, ship, linked URL, count, or pilot placeholder
- mixed text that becomes protected-only after removing protected terms

It may persist:

- CJK phrase segments such as the escaped string `\u5929\u9e64\u7ea7\u6765\u4e86` when the remaining source still contains meaningful non-English language content
- Cyrillic or other non-English natural-language text
- mixed intel lines only after source extraction reduces them to the translatable non-English segment

## EN to CN Rules

English source text may persist only when the direction is explicitly EN to CN or the target language starts with `zh`. That keeps valid EN to CN correction rows separate from Auto to EN pollution.

## Cleanup Rules

Cleanup removes only invalid machine-cache rows. It preserves:

- every manual override
- every EN to CN machine-cache row
- every valid non-English Auto to EN machine-cache row

The Settings cleanup action runs duplicate cleanup, invalid Auto to EN cleanup, and polluted mixed-source cleanup. Failure cooldown rows may be left intact because they do not appear in the Translation Corrections table.

## UI Rules

The Settings Translation Cache page remains a correction editor, not a raw SQLite browser. The existing "Clean cache issues" action should report how many duplicate, invalid Auto to EN, and mixed-source machine rows were removed. Manual overrides must remain visible and editable after cleanup.

## Verification

- Unit tests cover the gate, storage-boundary writes, worker persistence, grouped rows, and cleanup.
- Visual before inspection records examples of polluted rows if present in the local cache; if no polluted rows exist, record that the UI was inspected and the cleanup test database reproduces the issue.
- Visual after inspection confirms invalid Auto to EN rows are gone, valid EN to CN rows remain, and manual overrides remain editable.
