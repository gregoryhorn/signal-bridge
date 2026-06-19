# Signal Bridge v0.3 Alpha version. I will make it better :) If you find bugs or want features log an issue here in githb.

Signal Bridge is a lightweight Windows app for translating chat logs CN -> EN and EN -> CN

## Version

Current version: 0.1


## v0.3 Optional ESI

Public ESI entity recognition is enabled by default in v0.3. OAuth remains disabled unless the user opts in for future character-aware features.

Signal Bridge includes optional ESI/OAuth foundation for future EVE entity recognition and character-aware features. ESI is **disabled by default** and is never required for normal live chat monitoring or translation.

ESI features:

- cache-first SQLite entity cache at `cache/esi_cache.sqlite`,
- 30-day positive cache for resolved players/entities,
- negative cache to avoid repeated bad lookups,
- background resolver queue only,
- right-click sender resolve/refresh/ignore actions,
- optional OAuth using `http://localhost:8080/callback`,
- temporary listener bound to `127.0.0.1:8080` only during authorization,
- local-only client secret/token storage in ignored `config/` files.

## Current Interaction Behavior

- Right-click a feed row for copy actions.
- HTTP/HTTPS URLs can be clicked or copied from the context menu.
- Use `Settings > Open Logs Folder` to inspect startup/error logs.
- Use `Help > Check for Updates` to manually check the latest GitHub release.
- Monitoring remains live-only by default; old chat history is not backfilled.

## Current Tab Behavior

- `All` is the default combined chat tab.
- New chat tabs appear automatically unless manually hidden.
- New tabs never steal focus.
- Unread indicators clear when the tab is focused.
- Hidden tabs can be restored from the Channels menu or the `+ Hidden (N)` tab-bar button.
- Tabs wrap/stack when the window is narrowed and can be drag-reordered with hover/drag visual polish.
- All tab shows combined chat while channel tabs stay focused.

## Planned Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features, including tab polish, right-click/copy support, automatic translation catalog updates from GitHub, ESI character detection, URL auto-linking, and release/signing improvements.



## Display, Layout, and Appearance

Signal Bridge opens by default in a narrow mobile-style side-panel layout (`430x720`) so it can sit beside EVE without consuming a wide monitor area. You can still resize the window normally.

Use `View > Appearance / Display Options...` to tune the feed for your eyes and monitor:

- choose a preset: Default Dark, Soft Dark, Low Color / Minimal, High Contrast, or Overlay Transparent;
- change font family and font size;
- adjust whole-window opacity for overlay-style use;
- enable/disable background highlight rectangles;
- edit each highlight category with both a visible swatch and editable hex color code;
- toggle bold per category;
- preview changes live before applying.

Highlight categories include Timestamp, Sender, Systems, Characters / ESI, Ships, Modules / Assets, ESS, Translation, and Links. Sender names are neutral by default to reduce distraction.

Use `Tools > General Exclusion List...` for words or names that should stay visually neutral. Excluded terms suppress recognition/highlighting globally, including ESI red, ship orange, asset/module purple, system yellow, and ESS blue rules.

## Download

Get the Windows portable app from the GitHub release:

- **Release page:** [https://github.com/gregoryhorn/signal-bridge/releases/tag/v0.2](https://github.com/gregoryhorn/signal-bridge/releases/tag/v0.2)
- **Direct download:** [SignalBridge-v0.3-win64-portable.zip](https://github.com/gregoryhorn/signal-bridge/releases/download/v0.2/SignalBridge-v0.3-win64-portable.zip)

Extract the ZIP, then run:

```text
SignalBridge.exe
```

No installer is required. The ZIP is the standalone portable package; keep the extracted folder together because `SignalBridge.exe` uses the bundled `_internal` runtime folder.

SHA256:

```text
A7AFFFDE24F94659D9ED196827544153350E05334A19C730EA01031FEC9889EE
```

## Screenshot

![Signal Bridge screenshot](docs/images/signal-bridge-screenshot.png)

Signal Bridge is a lightweight Windows desktop tool for monitoring EVE Online chat logs and making intel easier to read.

It watches selected EVE chat channels, highlights important entities, and can translate localized/non-English text while preserving EVE-specific terms.

## Features

- Portable Windows app: no installer required.
- Dynamic EVE chat channel discovery; no channel is hard-coded.
- Active channels appear as tabs; each tab has an `x` button to close/hide it.
- Solar systems highlighted in yellow.
- Ships/assets highlighted in red.
- `ESS` highlighted in light blue.
- EVE localization DB support for Chinese/localized ship names to English canonical names.
- Free Google auto-detect translation to English.
- Optional Argos Translate offline fallback.
- Optional EN -> CN mode.
- Always-on-top mode.
- Configurable font family, font size, and timestamp visibility.
- Saves settings locally in the portable app folder.

## Quick Start

1. Download `SignalBridge-win64-portable.zip` from GitHub Releases.
2. Extract the ZIP anywhere, for example:

   ```text
   C:\Tools\SignalBridge
   ```

3. Run:

   ```text
   SignalBridge.exe
   ```

4. If your EVE chatlog folder is not detected automatically, choose it from:

   ```text
   Settings > Choose Chatlog Folder...
   ```

5. Open channels from:

   ```text
   Channels > Choose / Open Channels...
   ```

## EVE Chatlog Folder

Signal Bridge tries to auto-detect:

```text
%USERPROFILE%\Documents\EVE\logs\Chatlogs
%USERPROFILE%\OneDrive\Documents\EVE\logs\Chatlogs
```

If your logs are somewhere else, select the folder manually in Settings.

## Translation

Signal Bridge uses a layered approach:

1. EVE DB/catalog localization for ships/items/systems.
2. Google free auto-detect translation for normal non-English text.
3. Optional Argos Translate offline fallback if installed.

Default recommended mode:

```text
View > Translate Free Text: ON
View > Auto -> EN: selected
View > Translated Only: ON
```

Argos fallback can be installed from:

```text
Settings > Install Argos Offline Fallback
```

The app asks before downloading anything.

## Menus

### File

- Start Monitoring
- Stop Monitoring
- Clear Feed
- Exit

### Channels

- Choose / Open Channels...
- Close All Active Channels
- Refresh Channel List

### Settings

- Choose Chatlog Folder...
- Choose Translation DB...
- Install Argos Offline Fallback
- Open App Folder

### View

- Always on Top
- Translated Only
- Translate Free Text
- Auto -> EN
- EN -> CN
- Compact Mode
- Show Timestamps
- Choose Font...
- Increase Font Size
- Decrease Font Size

### Tools

- Backend / DB Health
- Open Chatlog Folder

### Help

- About Signal Bridge
- Support / Donate ISK

## Support

If you like this app and want further development, donate me some ISK in game | Mizz Betty

## Privacy / Network Use

Signal Bridge reads local EVE chatlog files.

Network access is only used when:

- Google free translation is enabled and non-English free text is detected.
- You explicitly install Argos offline fallback models.

No EVE account credentials are used or requested.

## Antivirus Notes

Some antivirus products may flag unsigned PyInstaller apps because they bundle a Python runtime.

To reduce false positives, releases should be built with:

- no UPX packing,
- no installer requiring admin rights,
- transparent network behavior,
- published SHA256 checksums,
- code signing when possible.

## Development

Run from source:

```powershell
python -X utf8 signal_bridge_gui.py
```

Self-test:

```powershell
python -X utf8 signal_bridge_gui.py --self-test --limit 5
```

Build portable package:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```




## Live-only monitoring / backfill

Backfill is disabled by default. When a channel tab is opened, Signal Bridge snapshots existing chatlog files at their current end position and only displays new messages appended after monitoring starts. This avoids old private chats or stale channel history appearing unexpectedly.


## Channel tabs and channel names

Active channels appear as tabs. When more than one channel is open, an **All Channels** tab is available. Normal per-channel tabs hide channel-name prefixes by default because the tab already identifies the channel. Use **View > Show Channel Names in Feed** to show/hide channel prefixes globally.




- Ships render red; non-ship catalog assets/modules are purple.


ESI refinement: when enabled, Signal Bridge can conservatively resolve likely character names inside chat messages while excluding EVE systems, ships, modules, links, and counts first. Confirmed character names are protected from machine translation.

The chat feed now defaults to a clear sans-serif typeface (`Segoe UI`) while still allowing font changes from the View menu.

ESI cache policy: successful entity lookups cache for 30 days; negative ESI answers cache for 90 days to avoid unnecessary ESI rechecks.

ESI usability: right-click menu includes selected-text resolve/ignore, last-check diagnostics, and an exclusion list for badly named characters.
Built-in ESI exclusions include common individual words such as `Link`, `Jump`, `Fleet`, `and`, `the`, `Gate`, `Star`, `ISK`, and `Ship`; these can also be stored in the local ESI exclusion DB.
ESI rendering note: resolved/cached character names are hydrated onto visible rows so the feed highlights detected characters in red.
ESI diagnostics: use Tools > Manual ESI Character Check... or right-click selected text to run a visible ESI check with a result dialog and log entry.

Live monitoring emits new chat rows before any optional online/free-text translation so chat reception is not blocked by translation services.

Live monitoring uses compact catalog-only enrichment and avoids the optional large `translations.db` path so new chat rows are not delayed by DB lookups.

Feed rendering now guards highlight errors so one malformed/highlighted row cannot stop later live chat rows from appearing.

Sender names render neutrally, and common words such as `Red` and `enemy` are excluded from distracting highlight/ESI tagging.

Right-click selected text now includes `Add Selected Text as ESI Character`; resolving or adding a character caches it and redraws matching rows immediately.

Appearance options include configurable font, colors, bold highlights, optional background rectangles, presets, preview, reset defaults, and window opacity.

Signal Bridge includes curated shorthand ship aliases such as `短剑` -> `Stabber` and `海狞獾` -> `Caracal Navy Issue`.
The portable build includes `data/default_exclusions.json`, which seeds the General Exclusion List on first run without overwriting user changes.

The portable build also includes `data/default_esi_entities.json`, a starter cache of verified ESI characters seeded on first run without overwriting local cache entries.

- Bundled starter translation cache seeds known free-text translations into new installs without overwriting local cache rows.
- Starter translation-cache entries include curated EVE terminology fixes for common ship/item/intel phrases.
- Appearance / Display Options keeps Apply/OK/Cancel in a fixed footer with a scrollable settings body for small windows.
- Channels can be added non-destructively with Add Selected; Replace All is explicit, and newly active EVE chat channels auto-open as tabs while keeping focus where it is.
- The channel area uses a compact mobile-style bar: All button, current-channel dropdown, close-current button, and hidden restore count.
