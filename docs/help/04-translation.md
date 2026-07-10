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

Settings, page **Translation Cache** (Translation Corrections): one table of
cached phrases where you can edit the primary English text. Manual corrections
persist and win over engine output. Cleanup tools remove polluted machine-cache
rows without deleting manual overrides.
