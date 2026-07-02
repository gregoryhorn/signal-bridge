# Phase 2.4 Design: Help Center + About/Support

**Date:** 2026-07-03
**Status:** approved by owner (brainstorming session)
**Closes:** ISSUES.md "Help menu needs a proper help system" (medium), "About and Support need a dedicated menu" (medium)
**Roadmap:** `docs/superpowers/plans/2026-07-02-ui-overhaul-roadmap.md` Phase 2.4

## Decisions (owner-approved)

1. **Help content = Markdown files + in-app viewer.** Topics are `.md` files in `docs/help/`, shipped inside the portable ZIP, rendered in a themed Tk window. Offline by design; readable on GitHub too.
2. **English only.** Bilingual EN/CN deferred; may become a Phase 3+ follow-up if requested.
3. **About/Support = dedicated window, settings page kept.** New themed About window; the existing `_render_settings_about` page stays as a thin pointer whose buttons open the new window. The old `show_about`/`show_support` messageboxes are replaced (methods re-pointed, not removed).
4. **Help viewer = left topic nav + content pane**, the proven SettingsShell pattern (`sb_ui/settings_center.py`), with deep-linking.

## Components

### 1. Help content: `docs/help/*.md`

Nine English topic files (roadmap list):

| Order | Title | File |
|---|---|---|
| 1 | Getting Started | `01-getting-started.md` |
| 2 | Chatlog Folder | `02-chatlog-folder.md` |
| 3 | Channels | `03-channels.md` |
| 4 | Translation | `04-translation.md` |
| 5 | Aliases | `05-aliases.md` |
| 6 | Recognition Rules | `06-recognition-rules.md` |
| 7 | Pilot Info | `07-pilot-info.md` |
| 8 | Intel History | `08-intel-history.md` |
| 9 | Diagnostics | `09-diagnostics.md` |

- A fixed manifest in code — ordered `(title, filename)` pairs — drives the nav. No directory scanning: ordering and titles stay stable, and a stray file can't appear in the UI.
- Files resolve via `APP_DIR / "docs" / "help"` (`APP_DIR` already handles PyInstaller `_MEIPASS` and source layouts, `signal_bridge_gui.py:43`).
- Missing file → the content pane renders a friendly "This topic is unavailable in this build — see the docs on GitHub" note with the repo URL. No crash, no empty pane.
- Content is user-task oriented (how to set the chatlog folder, what translation modes mean, how Pilot Info/zKill works, what to send when reporting issues). Topics end with relevant links (README, ISSUES.md, releases page) where natural.

### 2. `sb_ui/markdown_view.py` (new module)

Minimal markdown → Tk Text rendering, split for testability:

- `parse_markdown(text: str) -> list[tuple[str, str]]` — pure function returning `(text, tag)` segments. Supported subset: `#`/`##`/`###` headings, `**bold**`, `- ` bullets, `` `inline code` ``, bare `https://` URLs (tag `link`), plain paragraphs. Unknown markdown passes through as plain text. No Tk import needed to test.
- `render_into(text_widget, segments)` — configures themed tags (fonts/colors from `sb_theme`), inserts segments, binds `link`-tagged ranges to `webbrowser.open` with a hand cursor, then sets the widget read-only.
- Deliberately NOT a full markdown engine. If a help doc uses syntax outside the subset, it renders as plain text — acceptable.

### 3. Help window: `show_help_center(topic: str | None = None)`

- Method on `SignalBridgeGui`, following `show_settings_center`'s use of the shell pattern: left nav listing the nine titles, right scrolled content pane rendering the selected topic via `markdown_view`, footer with Close.
- Reuse `SettingsShell` directly if its API fits (nav + per-page renderers is exactly this shape); otherwise a small `HelpShell` in `sb_ui` modeled on it. Decision made at planning time by reading `SettingsShell`'s constructor — prefer reuse.
- `topic` argument deep-links to a topic by title; default opens the first topic.
- Sized with `fit_to_content`; minsize keeps nav + content readable.
- Inline-help hook: the Recognition Rules dialog gets a small "?" button opening `show_help_center("Recognition Rules")`. Only that one hook in this phase (extends the pattern the roadmap names; more hooks can follow opportunistically).

### 4. About window + menu restructure

New `show_about_window()` (themed Toplevel, `sb_ui` components):

- App name, `APP_VERSION`, one-line description.
- Links (clickable, `webbrowser`): GitHub repo, latest release (`UPDATE_RELEASE_URL`), report an issue (`https://github.com/gregoryhorn/signal-bridge/issues`).
- Actions: Copy Diagnostics (existing `copy_diagnostics`), Check for Updates (existing `check_for_updates(manual=True)`).
- Support/donation card: "Donate ISK to: Mizz Betty", `DONATION_TEXT`, Copy Character Name / Copy Donation Message buttons (content moves from the settings page implementation; settings page keeps a short version).
- `show_about` and `show_support` become thin wrappers opening this window (callers unchanged).

Help menubar becomes:

```
Help
├ Help Topics...            → show_help_center()
├ ──────────────
├ Check for Updates         → check_for_updates(manual=True)
├ Report an Issue...        → webbrowser.open(issues URL)
├ ──────────────
└ About Signal Bridge...    → show_about_window()
```

Settings About/Support page: keeps version line + short support blurb; its buttons become "About & Support..." (opens the About window) and "Help Topics..." (opens the Help window).

## Error handling

- Help file read errors (missing, unreadable, bad encoding) → per-topic fallback note; never an exception dialog.
- All URL opens go through `webbrowser.open` (non-blocking, no network in render paths — consistent with `docs/INVARIANTS.md`).

## Testing

- Unit tests (pytest, no Tk): `parse_markdown` cases — headings, bold, bullets, code, links, mixed document, pass-through of unsupported syntax.
- Unit test: every manifest entry's file exists in `docs/help/` (guards packaging drift).
- Screenshot verification (proven `SignalBridgeGui()`-without-`.run()` harness): Help window with a topic selected showing rendered markdown + nav; About window showing links/actions/donation card.
- Existing gates: `py_compile`, `pytest tests/ -q`, `scripts/check-fixtures.py`.

## Packaging

No build script exists in-repo; portable ZIP contents are curated per `GITHUB_RELEASE.md`. This phase updates that document's package-contents section to include `docs/help/`. The frozen build must add `docs/help` as bundled data when the v0.6 package is assembled (release checkpoint note, not code in this phase).

## Out of scope

- Bilingual help content.
- Full markdown support (tables, images, nested lists).
- Additional "?" inline-help hooks beyond Recognition Rules.
- Rewriting README or other repo docs.

## Tracker closure

Both ISSUES.md entries move to `## Fixed: ...` with fix summaries; CHANGELOG.md Unreleased gains a Help/About entry.
