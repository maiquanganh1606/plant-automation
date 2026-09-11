#!/usr/bin/env bash
# Build a macOS customer release.  Run this on a Mac with Python 3.10+.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

if ! python3 -m PyInstaller --version >/dev/null 2>&1; then
  python3 -m pip install --upgrade pyinstaller
fi
export PYINSTALLER_CONFIG_DIR="$project_dir/.pyinstaller"
rm -rf build dist release
python3 -m PyInstaller --noconfirm --clean --windowed \
  --name "Plant Automation" \
  --osx-bundle-identifier "com.plantautomation.desktop" \
  --add-data "$project_dir/config:config" \
  --add-data "$project_dir/captures:captures" \
  desktop_launcher.py

mkdir -p "release/Plant-Automation-macOS"
cp -R "dist/Plant Automation.app" "release/Plant-Automation-macOS/"
cp "docs/HUONG_DAN_SU_DUNG.md" "release/Plant-Automation-macOS/HUONG_DAN_SU_DUNG.md"
cp "docs/GHI_CHU_PHAT_HANH.md" "release/Plant-Automation-macOS/GHI_CHU_PHAT_HANH.md"
ditto -c -k --sequesterRsrc --keepParent "release/Plant-Automation-macOS" "release/Plant-Automation-macOS.zip"
echo "Đã tạo: $project_dir/release/Plant-Automation-macOS.zip"
