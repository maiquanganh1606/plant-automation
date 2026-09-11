# Build a Windows customer release. Run in PowerShell on Windows, with Python 3.10+.
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  python -m pip install --upgrade pyinstaller
  if ($LASTEXITCODE -ne 0) { throw "Không cài được PyInstaller bằng Python đang dùng." }
}
$env:PYINSTALLER_CONFIG_DIR = Join-Path $Project ".pyinstaller"
Remove-Item -Recurse -Force build, dist, release -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm --clean --windowed `
  --name "Plant Automation" `
  --add-data "$Project\config;config" `
  --add-data "$Project\captures;captures" `
  desktop_launcher.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller không thể tạo bản phát hành Windows." }

$Release = Join-Path $Project "release\Plant-Automation-Windows"
New-Item -ItemType Directory -Force -Path $Release | Out-Null
$BuildOutput = Join-Path $Project "dist\Plant Automation"
if (!(Test-Path $BuildOutput)) { throw "Không tìm thấy thư mục đầu ra PyInstaller: $BuildOutput" }
Copy-Item -Recurse "$BuildOutput\*" $Release
Copy-Item "docs\HUONG_DAN_SU_DUNG.md", "docs\GHI_CHU_PHAT_HANH.md" $Release
Compress-Archive -Path $Release -DestinationPath "$Project\release\Plant-Automation-Windows.zip" -Force
Write-Host "Đã tạo: $Project\release\Plant-Automation-Windows.zip"
