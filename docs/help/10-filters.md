# Filters and spam controls

Settings page **Filters** controls what reaches the live feed.

## Keyword and sender filters

- **Add keyword…** hides messages whose text contains (or exactly matches) the pattern.
- **Add sender…** hides messages from that character name.
- Matching is case-insensitive by default.
- Filters persist across restarts.
- Use **Remove selected** to delete a filter.

Keyword/sender changes save immediately when you add or remove them.

## Local spam controls

Spam controls are aimed at noisy **Local**-style channels. Intel lines that include a recognized **system** are not treated as ASCII-art spam.

Options:

- Enable spam controls
- Apply only to Local-like channels (default on)
- Filter ASCII-art / symbol spam
- Max messages per channel per minute
- Repeat-sender window (seconds) and max messages in that window

Click **Apply** in the Settings footer after changing spam options.

## Related pages

- **Recognition Rules**: ignored pilots, highlight exclusions, parser noise (not feed block lists).
- **Channels**: which chat channels are tracked.
