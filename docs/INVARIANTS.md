# Signal Bridge Invariants

These are hard rules for future maintenance. Do not break them without an explicit architecture decision.

## UI/threading

- The Tkinter UI thread must not block.
- The render path must not perform network calls.
- The render path must not run machine translation.
- The render path must not import/probe Argos.
- The render path must not hydrate ESI or scan large caches.
- Settings pages must display cached status first and refresh slow state in the background.

## Translation

- Raw chat text must be preserved.
- Display normalization is display-only.
- Curated/cache/catalog replacement is preferred for EVE entities.
- Free machine translation must run only as a background job or precomputed row value.
- Direct in-process Argos is disabled until a helper-process design exists.

## ESI / network

- ESI is optional and cache-first.
- Positive/negative/manual ignore cache checks happen before network requests.
- Duplicate/pending ESI names must not cause repeated network queries.
- Network work must be queued, bounded, rate-limited, and never block feed rendering.

## Diagnostics / privacy

- Diagnostics must never include OAuth tokens, client secrets, API keys, or auth headers.
- Raw chat/pilot data in exported bundles should be opt-in.
- JSONL logs should be structured and append-only.
- Every skipped translation/entity decision should have an explainable reason when practical.

## Add-ons

- Add-ons must fail isolated.
- Add-ons should receive narrow events/contracts, not arbitrary GUI internals.
- Disabling an add-on should stop future processing without deleting user data by default.

## Packaging

- The normal portable ZIP must remain lightweight.
- No Python/dev tools/admin rights should be required by end users.
- Heavy optional runtime/model packages should be optional add-ons, not default bundle dependencies.
