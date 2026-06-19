# Signal Bridge Portable Build Notes

Goal: no-install Windows 10/11 x64 portable ZIP.

AV-conscious guidelines:
- Build on a clean Windows VM with a stable Python release.
- Avoid UPX compression; packed executables are more likely to trigger AV heuristics.
- Use PyInstaller --clean --noupx --windowed.
- Keep network access transparent: Google Translate only when user enables Translate Free Text; Argos model download only after prompt.
- Sign the EXE later if distributing broadly.
- Publish checksums for ZIP releases.
- Do not bundle the 507 MB full translations.db by default; use compact catalog later.

Build:
```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```


