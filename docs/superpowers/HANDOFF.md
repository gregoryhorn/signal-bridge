# Signal Bridge - Handoff

**Updated:** 2026-07-10  
**Repo:** `D:\AI\Rift\signal-bridge-live-gui`  
**Branch:** `main`  
**Public release:** **v0.7** on GitHub Releases

## Current state

The v0.7 portable package is the public download. Source, README download links, `CHANGELOG.md`, `GITHUB_RELEASE.md`, and release assets must stay aligned for every public cut.

## Release checklist (use every time)

1. `APP_VERSION` in `signal_bridge_gui.py` matches tag and ZIP name  
2. `build_portable.ps1` `$Version` matches  
3. README Download section points at the live release tag  
4. `CHANGELOG.md` has a dated section for that version (not only Unreleased)  
5. `GITHUB_RELEASE.md` describes that version  
6. `powershell -File .\build_portable.ps1`  
7. Verify package: `docs/help/`, `data/phrase_overrides.json`, `data/eve_phrase_promotions.json`, empty cache/logs  
8. `gh release create` (or `upload`) with ZIP + both `.sha256` files  
9. Confirm release is Latest and download URL returns 200  

## Do not

- Push “merge prep” language to default README without shipping assets  
- Leave README pointing at a release tag that does not exist  
- Ship a local EXE only without publishing ZIP + checksums on the same cut  
