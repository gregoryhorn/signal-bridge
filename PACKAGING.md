# Build and Packaging Notes

Signal Bridge is currently packaged with PyInstaller.

Recommended command:

```powershell
pyinstaller --noconfirm --clean --noupx --windowed --icon .\assets\signal_bridge_icon.ico --name SignalBridge signal_bridge_gui.py
```

Important:

- Use `--noupx` to avoid packed executable heuristics.
- Use `--windowed` for native GUI behavior.
- Do not require administrator rights.
- Do not silently download translation models.
- Publish SHA256 checksums.
- Prefer code signing before broad public distribution.

If PyInstaller hangs or produces a huge build because of Argos/Torch dependencies, build a first release without bundling Argos and keep Argos as an optional source/dev feature or separate advanced package.



