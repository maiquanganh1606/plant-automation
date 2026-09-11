# Build a Windows customer release. Run in PowerShell on Windows, with Python 3.10+.
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

try { py -m PyInstaller --version | Out-Null } catch { py -m pip install --upgrade pyinstaller }
$env:PYINSTALLER_CONFIG_DIR = Join-Path $Project ".pyinstaller"
Remove-Item -Recurse -Force build, dist, release -ErrorAction SilentlyContinue
py -m PyInstaller --noconfirm --clean --windowed `
  --name "Plant Automation" `
  --add-data "$Project\config;config" `
  --add-data "$Project\captures;captures" `
  desktop_launcher.py

$Release = Join-Path $Project "release\Plant-Automation-Windows"
New-Item -ItemType Directory -Force -Path $Release | Out-Null
Copy-Item -Recurse "dist\Plant Automation\*" $Release
Copy-Item "docs\HUONG_DAN_SU_DUNG.md", "docs\GHI_CHU_PHAT_HANH.md" $Release
Compress-Archive -Path $Release -DestinationPath "$Project\release\Plant-Automation-Windows.zip" -Force
Write-Host "Đã tạo: $Project\release\Plant-Automation-Windows.zip"
