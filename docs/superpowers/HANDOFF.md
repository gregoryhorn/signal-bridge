# Signal Bridge - Handoff

**Updated:** 2026-07-03  
**Repo:** `D:\AI\Rift\signal-bridge-live-gui`  
**Branch:** `main`  
**Latest pushed commit:** `7e47706a6dee9dc6338628841048336287a7c270` (`release: prepare Signal Bridge v0.6`)

## Current state

Signal Bridge is now prepared as **v0.6** and pushed to GitHub `origin/main`.

Completed release work:

- Bumped `APP_VERSION` in `signal_bridge_gui.py` from `0.5` to `0.6`.
- Updated `build_portable.ps1` to build `SignalBridge-v0.6-win64-portable.zip`.
- Updated `README.md`, `GITHUB_RELEASE.md`, `CHANGELOG.md`, `PACKAGING.md`, `README_DISTRIBUTION.md`, and `ROADMAP.md` for v0.6.
- Added a narrow retry around `Compress-Archive` in `build_portable.ps1` because PyInstaller's generated `_internal\base_library.zip` can remain transiently locked for a moment after build completion.
- Rebuilt the portable package locally.
- Pushed commit `7e47706a6dee9dc6338628841048336287a7c270` to `origin/main`.

## Local release artifacts

These files exist locally and are intentionally ignored release artifacts, except `SignalBridge.exe.sha256`, which is tracked and was updated by the release commit:

- `SignalBridge-v0.6-win64-portable.zip`
- `SignalBridge-v0.6-win64-portable.zip.sha256`
- `SignalBridge.exe.sha256`

Artifact details from the verified build:

- ZIP size: `19031027` bytes
- ZIP SHA256: `0362CCC03EE56FA659FD321E84775641640FE972E60F3AF4964F2559137C4A86`
- EXE SHA256: `D636D0733AF5C1633C8A3C56621E1C5EA86E58A78586EEC6A5B388A59FC5709D`

The ZIP inspection confirmed:

- `docs/help/` contains 9 packaged offline help topics.
- Packaged `cache/`, `logs/`, `config/`, and `runtime/` folders contain no files.
- `SignalBridge.exe` is present.

The packaged EXE launch smoke was run from `dist\SignalBridge\SignalBridge.exe`; the process started successfully and was then stopped.

## Verification already run

Fresh gates after the release commit:

```powershell
python -m py_compile signal_bridge_gui.py
python scripts/check-fixtures.py
python -m pytest tests/ -q
```

Observed results:

- `py_compile`: exit 0
- fixture check: `Fixture check OK: 6 case(s)`
- pytest: `67 passed`

Build command:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

Observed result: exit 0, package and checksum files produced.

## Git state to expect

Expected status immediately after this handoff update, before committing this file:

- Modified: `docs/superpowers/HANDOFF.md`
- Untracked: `assets/signal_bridge_icon_true_transparent_1024.png`

The untracked icon asset pre-existed this release work and was intentionally not committed.

Generated build outputs remain ignored by `.gitignore`:

- `build/`
- `dist/`
- `*.zip`
- `*.zip.sha256`
- `*.spec`

## Recommended next actions

1. Commit this handoff file if desired:

   ```powershell
   git add docs/superpowers/HANDOFF.md
   git commit -m "docs: update v0.6 handoff"
   git push origin main
   ```

2. Publish GitHub Release `v0.6` manually or with GitHub CLI, using `GITHUB_RELEASE.md` as the release notes source.

3. Upload these release assets:

   ```text
   SignalBridge-v0.6-win64-portable.zip
   SignalBridge-v0.6-win64-portable.zip.sha256
   SignalBridge.exe.sha256
   ```

4. Optional before publishing: download/extract the ZIP into a fresh folder and open `SignalBridge.exe` once from the extracted copy.

## Architecture and workflow constraints

- Keep `signal_bridge_gui.py` surgical. Do not refactor the monolith unless a plan specifically calls for it.
- Preserve `docs/INVARIANTS.md`: no network, machine translation, ESI, or cache-heavy work in Tk render paths; do not block the UI thread.
- Keep portable builds clean. Do not bundle local `cache/`, `runtime/`, `logs/`, ESI tokens, zKill cache, local settings, or local test state.
- Use `pytest tests/ -q`, `python -m py_compile signal_bridge_gui.py`, and `python scripts/check-fixtures.py` before claiming a change is complete.
- Prefer one commit per planned deliverable.

## Notes for the next agent

- The v0.6 release commit is already on GitHub. Do not recreate it.
- The local package has been built but not uploaded to a GitHub Release in this session.
- `GITHUB_RELEASE.md` references the v0.6 assets and can be used directly as release-note draft material.
- The README now links to the future `v0.6` GitHub Release tag and direct ZIP URL. Those links will work after the release is published.
