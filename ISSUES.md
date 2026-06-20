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
- Curated shorthand aliases are still needed for player slang such as `海鱼`.
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
