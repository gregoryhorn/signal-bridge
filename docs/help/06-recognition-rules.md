# Recognition Rules

Use scoped recognition rules when Signal Bridge recognizes, highlights, or
checks the wrong text. Each scope changes a different part of the
parser/rendering pipeline.

## Scopes

- **Ignored pilots**: names never treated as pilots (no ESI checks, no Pilot Info).
- **Highlight exclusions**: text never highlighted as a system/ship/asset even if it matches the catalog.
- **Noise words**: chat noise stripped before parsing.

## Managing rules

- Open **Settings**, page **Recognition Rules**, then **Open Recognition Rules…** for the full editor.
- Rules can be added one at a time or imported as a pasted list, one term per line.
- Bundled starter rules cover common parser noise; your own rules are stored locally.

Prefer the narrowest scope that fixes the problem — a noise word is
invisible to the whole pipeline, while a highlight exclusion still lets
the text be read as chat.
