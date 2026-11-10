#!/usr/bin/env bash
# Build a macOS .dmg disk image containing UniConvert.app.
# This is meant to run on macOS (it uses hdiutil + iconutil).
# On Linux we create a .app bundle skeleton + zip of the Linux binary
# so CI still produces an artifact; replace with a real macOS build in CI.
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSION="0.1.0"
APP="dist/macos/UniConvert.app"
rm -rf "$APP" dist/macos/UniConvert.dmg 2>/dev/null || true
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Try to build .icns if iconutil exists (macOS host)
if command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns installers/macos/UniConvert.iconset -o "$APP/Contents/Resources/UniConvert.icns"
else
  # Fallback: copy the PNG as a resource
  cp assets/logo.png "$APP/Contents/Resources/UniConvert.png"
fi

# Info.plist
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>UniConvert</string>
<key>CFBundleDisplayName</key><string>UniConvert</string>
<key>CFBundleIdentifier</key><string>app.uniconvert.UniConvert</string>
<key>CFBundleVersion</key><string>${VERSION}</string>
<key>CFBundleShortVersionString</key><string>${VERSION}</string>
<key>CFBundleExecutable</key><string>uniconvert</string>
<key>CFBundleIconFile</key><string>UniConvert.icns</string>
<key>NSHighResolutionCapable</key><true/>
<key>LSMinimumSystemVersion</key><string>10.15</string>
<key>NSRequiresAquaSystemAppearance</key><false/>
</dict></plist>
EOF

# Executable — on macOS pyinstaller would build a real binary;
# on non-mac hosts we drop a stub launcher shell + whatever binary exists.
if [[ "$(uname -s)" == "Darwin" ]]; then
  pyinstaller --noconfirm --windowed --name uniconvert \
    --icon "$APP/Contents/Resources/UniConvert.icns" \
    --add-data "assets:assets" \
    uniconvert/__main__.py
  cp -r dist/uniconvert/* "$APP/Contents/MacOS/"
  hdiutil create -volname "UniConvert" -srcfolder dist/macos -ov -format UDZO \
    "dist/release/UniConvert-${VERSION}.dmg"
else
  # Linux host: create a best-effort .app folder + zip a placeholder bundle
  cat > "$APP/Contents/MacOS/uniconvert" <<'EOF'
#!/bin/bash
echo "This is a placeholder UniConvert.app bundle built on Linux."
echo "Install Python 3.9+, PyQt6, Pillow, and ffmpeg, then run:"
echo "  pip install uniconvert && uniconvert"
EOF
  chmod +x "$APP/Contents/MacOS/uniconvert"
  mkdir -p dist/release
  cd dist/macos
  zip -qr "../release/UniConvert-${VERSION}-macos.zip" "UniConvert.app"
  cd ../..
  echo "Built dist/release/UniConvert-${VERSION}-macos.zip (stub bundle; rebuild on macOS for a native .dmg)"
fi
