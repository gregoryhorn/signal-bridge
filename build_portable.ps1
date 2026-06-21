$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Version = '0.4'
Set-Location $Root

# Lean portable build:
# - Do not bundle Argos/Torch/spaCy ML stacks into the default EXE.
# - Google free translation remains available.
# - Argos remains an optional runtime/install feature for advanced/source users.
python -m pip install --upgrade pyinstaller
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force }
if (Test-Path .\dist) { Remove-Item .\dist -Recurse -Force }

$Zip = Join-Path $Root "SignalBridge-v$Version-win64-portable.zip"
Remove-Item $Zip,"$Zip.sha256",.\SignalBridge.exe.sha256 -Force -ErrorAction SilentlyContinue

$excludes = @(
  '--exclude-module', 'argostranslate',
  '--exclude-module', 'torch',
  '--exclude-module', 'torchvision',
  '--exclude-module', 'torchaudio',
  '--exclude-module', 'spacy',
  '--exclude-module', 'stanza',
  '--exclude-module', 'ctranslate2',
  '--exclude-module', 'onnxruntime',
  '--exclude-module', 'numpy',
  '--exclude-module', 'pandas',
  '--exclude-module', 'scipy',
  '--exclude-module', 'sklearn',
  '--exclude-module', 'matplotlib'
)

pyinstaller --noconfirm --clean --noupx --windowed --icon .\assets\signal_bridge_icon.ico --name SignalBridge @excludes signal_bridge_gui.py

New-Item -ItemType Directory -Force -Path .\dist\SignalBridge\config, .\dist\SignalBridge\cache, .\dist\SignalBridge\models\argos, .\dist\SignalBridge\logs, .\dist\SignalBridge\data, .\dist\SignalBridge\modules | Out-Null
# Bundle the official Intel History add-on as installed-by-default module code.
# It is copied to both the portable root and _internal so the app can find it
# regardless of PyInstaller onedir _MEIPASS behavior.
if (Test-Path .\addons\intel-history) {
  Copy-Item .\addons\intel-history .\dist\SignalBridge\modules\intel-history -Recurse -Force
  if (Test-Path .\dist\SignalBridge\_internal) {
    New-Item -ItemType Directory -Force -Path .\dist\SignalBridge\_internal\modules | Out-Null
    Copy-Item .\addons\intel-history .\dist\SignalBridge\_internal\modules\intel-history -Recurse -Force
  }
}
Copy-Item .\README.md .\dist\SignalBridge\README.md -Force
Copy-Item .\README_DISTRIBUTION.md .\dist\SignalBridge\README_DISTRIBUTION.md -Force
Copy-Item .\GITHUB_RELEASE.md .\dist\SignalBridge\GITHUB_RELEASE.md -Force
Copy-Item .\PACKAGING.md .\dist\SignalBridge\PACKAGING.md -Force
Copy-Item .\CHANGELOG.md .\dist\SignalBridge\CHANGELOG.md -Force
Copy-Item .\ROADMAP.md .\dist\SignalBridge\ROADMAP.md -Force
Copy-Item .\ISSUES.md .\dist\SignalBridge\ISSUES.md -Force
Copy-Item .\docs .\dist\SignalBridge\docs -Recurse -Force
Copy-Item .\data\eve_catalog.json,.\data\catalog_manifest.json,.\data\phrase_overrides.json,.\data\user_aliases.json,.\data\default_exclusions.json,.\data\default_exclusions.json.sha256,.\data\default_esi_entities.json,.\data\default_esi_entities.json.sha256,.\data\default_translation_cache.json,.\data\default_translation_cache.json.sha256 -Destination .\dist\SignalBridge\data -Force

Compress-Archive -Path .\dist\SignalBridge\* -DestinationPath $Zip -Force
Get-FileHash $Zip -Algorithm SHA256 | Tee-Object -FilePath "$Zip.sha256"
Get-FileHash .\dist\SignalBridge\SignalBridge.exe -Algorithm SHA256 | Tee-Object -FilePath .\SignalBridge.exe.sha256
Write-Host "Portable ZIP created: $Zip"
