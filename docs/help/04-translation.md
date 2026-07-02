# Translation

Signal Bridge translates Chinese chat to English (or English to Chinese)
inline in the feed.

## Modes

- **Auto -> EN**: detect Chinese lines and translate them to English.
- **EN -> CN**: translate English lines to Chinese.
- **Translated only**: show only the translation instead of original plus translation.
- **Translate free text**: also translate free-form chat, not just recognized intel terms.

## Engines and fallback

Settings, page **Translation**:

- Preferred engine: `auto`, `argos` (offline), or `google` (online).
- Cache mode: `cache-first-auto` (use cached translations, fetch new ones as needed) or `cache-only` (never go online).
- Fallback mode controls what happens when the preferred engine fails, including `offline-only`.

Translation display never blocks the feed: redraws use cached results and
new translations arrive in the background.

## Fixing bad translations

Settings, page **Translation Cache**, opens the Translation Corrections
browser: one table of cached phrases where you can edit the primary
English text directly. Corrections persist and win over engine output.
