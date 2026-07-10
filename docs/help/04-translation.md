# Translation

Signal Bridge translates non-English chat to English (or English to Chinese)
inline in the feed.

## Modes

- **Auto -> EN**: translate non-English free text to English. Chinese (CJK) uses a Chinese source hint; other languages (for example Russian) use Google **auto** detect.
- **EN -> CN**: translate English lines to Chinese.
- **Translated only**: show only the translation (or a stable pending placeholder) instead of flashing original text.
- **Translate free text**: also translate free-form chat, not just recognized intel terms.

## Engines and fallback

Settings, page **Translation**:

- Preferred engine: `auto`, `argos` (offline, safety-gated), or `google` (online).
- Cache mode: `cache-first-auto` or `cache-only`.
- Fallback mode controls what happens when the preferred engine fails, including `offline-only` and `online-only`.

Translation display never blocks the feed: redraws use cached or precomputed
results and new translations arrive in the background.

## Fixing bad translations

Translation layers (highest trust first):

1. **Phrase overrides** (`data/phrase_overrides.json`) — curated EVE Chinese/English
   fixes shipped with the app. Not wiped by cache cleanup.
2. **Manual corrections** (Settings → Translation Cache) — your saved overrides in
   the local DB. Survive “clean machine cache”; deleted only if you delete that entry.
3. **Machine cache** — Google/Argos results. Ephemeral; safe to clean; can be wrong
   for EVE slang (ships, attributes, market talk).

When a machine translation is wrong for EVE, prefer promoting a fix into
**phrase overrides** or a **manual correction**, then delete the bad machine-cache
row so it cannot reappear until re-fetched.

Settings, page **Translation Cache** (Translation Corrections): edit English text
for a phrase. Manual corrections win over engine output. Cleanup removes polluted
machine rows without deleting manual overrides.
