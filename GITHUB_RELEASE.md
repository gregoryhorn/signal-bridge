# GitHub Release Checklist

## Before Release

1. Verify app runs from source:

   ```powershell
   python -X utf8 -m py_compile .\signal_bridge_gui.py
   python -X utf8 .\signal_bridge_gui.py --self-test --limit 5
   ```

2. Build portable package:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
   ```

3. Verify package exists:

   ```powershell
   Get-Item .\SignalBridge-v0.3-win64-portable.zip
   Get-FileHash .\SignalBridge-v0.3-win64-portable.zip -Algorithm SHA256
   ```

4. Extract ZIP to a clean folder and run:

   ```text
   SignalBridge.exe
   ```

5. Test on a non-dev Windows 10/11 machine if possible.

## Release Assets

Upload:

- `SignalBridge-v0.3-win64-portable.zip`
- SHA256 checksum in release notes

## Suggested Release Notes

```markdown
# Signal Bridge v0.3

- ESI public entity recognition is now enabled by default for new installs; OAuth remains disabled and optional.

- Fixed ESI public lookup to use cache-friendly `universe/ids` exact-name resolution and reduced automatic lookup noise to protect ESI rates.

- Optional ESI/OAuth foundation, disabled by default.
- Cache-first ESI resolver with 30-day positive cache, negative cache, and right-click refresh/ignore sender actions.
- Temporary localhost OAuth callback listener on `127.0.0.1:8080` only during authorization.
- Client secret and tokens are local-only and not committed/bundled.

- Header color legend removed for a cleaner live UI.
Backfill is disabled by default, so opened channel tabs start live-only and do not display old chat history.

Portable Windows release for EVE Online chat intel monitoring and translation.

## Highlights

- No installer required.
- Dynamic channel selection, no hard-coded channel.
- Channel tabs with close buttons.
- Systems highlighted yellow, ships/assets red, ESS light blue.
- EVE localization DB support.
- Google free auto-detect translation to English.
- Optional Argos offline fallback.
- Configurable font and timestamp display.

## Install

Download and extract `SignalBridge-v0.3-win64-portable.zip`, then run `SignalBridge.exe`.

## SHA256

`PASTE_HASH_HERE`
```

## AV / SmartScreen Note

Unsigned portable EXEs can trigger Windows SmartScreen or antivirus warnings. This does not necessarily mean malware; it is common for new unsigned PyInstaller apps. Long-term mitigation is code signing and reputation building.

### v0.3 message character detection update
- ESI now detects likely character names inside message bodies using a cache-first, conservative candidate extractor.
- System names and EVE catalog entities are excluded before ESI checks to protect API rate limits.
- Detected character names are preserved during translation and are not translated into Chinese.
- Ship highlights are orange; message/sender ESI characters are red; non-ship modules/assets remain purple.
- Fixed ESS highlighting so it no longer tags `ess` inside normal words.
- Updated the chat feed to use a clearer sans-serif default font and fixed ESI message-name detection for lowercase pilot handles while excluding plural ship names.
- Negative ESI answers now stay in the negative cache for 90 days to prevent repeat lookups from burning ESI rates.
- Added ESI diagnostics, selected-text ESI resolve/ignore, always-visible ESI context actions, and a character exclusion list for badly named characters.
- Added built-in and local-DB ESI individual-word exclusions: `Link`, `Jump`, `Fleet`, `and`, `the`, `Gate`, `Star`, `ISK`, and `Ship`.
- Fixed ESI screen rendering: resolved/cached characters now hydrate onto visible rows and highlight red reliably.
- ESI menu actions now show visible result dialogs and logs for manual, selected-text, sender, and status checks.
- Fixed live monitoring stalls by preventing online/free-text translation from blocking chat-log parsing; new rows now emit immediately with monitor diagnostics.
- Fixed live monitor stalls from large optional `translations.db` lookups; live monitoring now uses the compact catalog path so new chat rows are not delayed by DB scans.
- Fixed a GUI render crash in ESS highlighting that could make live chat appear stuck after the first row while the monitor kept reading logs.
- Sender names are now neutral/uncolored; common words like `Red` and `enemy` are excluded from distracting highlights.
- Added explicit right-click `Add Selected Text as ESI Character`; selected/manual ESI checks now cache the character and redraw matching rows immediately.
- Improved ESI detection for manually resolved names by splitting adjacent candidate chunks and allowing valid uppercase single-token pilots.
