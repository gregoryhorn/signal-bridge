$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Version = '0.1'
Set-Location $Root

# Lean portable build:
# - Do not bundle Argos/Torch/spaCy ML stacks into the default EXE.
# - Google free translation remains available.
# - Argos remains an optional runtime/install feature for advanced/source users.
python -m pip install --upgrade pyinstaller
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force }
if (Test-Path .\dist) { Remove-Item .\dist -Recurse -Force }
if (Test-Path .\SignalBridge-v$Version-win64-portable.zip) { Remove-Item .\SignalBridge-v$Version-win64-portable.zip -Force }

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

New-Item -ItemType Directory -Force -Path .\dist\SignalBridge\config, .\dist\SignalBridge\cache, .\dist\SignalBridge\models\argos, .\dist\SignalBridge\logs, .\dist\SignalBridge\data | Out-Null
Copy-Item .\README.md .\dist\SignalBridge\README.md -Force
Copy-Item .\README_DISTRIBUTION.md .\dist\SignalBridge\README_DISTRIBUTION.md -Force
Copy-Item .\GITHUB_RELEASE.md .\dist\SignalBridge\GITHUB_RELEASE.md -Force
Copy-Item .\\PACKAGING.md .\\dist\\SignalBridge\\PACKAGING.md -Force
Copy-Item .\\CHANGELOG.md .\\dist\\SignalBridge\\CHANGELOG.md -Force

$Zip = Join-Path $Root 'SignalBridge-v$Version-win64-portable.zip'
Compress-Archive -Path .\dist\SignalBridge\* -DestinationPath $Zip
Get-FileHash $Zip -Algorithm SHA256 | Tee-Object -FilePath .\SignalBridge-v$Version-win64-portable.zip.sha256
Get-FileHash .\dist\SignalBridge\SignalBridge.exe -Algorithm SHA256 | Tee-Object -FilePath .\SignalBridge.exe.sha256
Write-Host "Portable ZIP created: $Zip"



