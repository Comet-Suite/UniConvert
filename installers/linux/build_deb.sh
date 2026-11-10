#!/usr/bin/env bash
# Build a Debian/Ubuntu .deb package for UniConvert.
# Usage: bash installers/linux/build_deb.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSION="0.1.0"
ARCH="amd64"
PKG="uniconvert"
ROOT="$(pwd)/dist/deb/${PKG}_${VERSION}_${ARCH}"
rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" "$ROOT/usr/bin" "$ROOT/opt/uniconvert" \
         "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/256x256/apps" \
         "$ROOT/usr/share/nautilus-python/extensions"

# Bundle the PyInstaller-built executable + assets
if [[ ! -x dist/uniconvert_linux/uniconvert_linux ]]; then
  echo "Building Linux one-folder bundle with PyInstaller first..."
  pyinstaller --noconfirm --name uniconvert_linux \
    --add-data "assets:assets" \
    main.py
fi
cp -r dist/uniconvert_linux/. "$ROOT/opt/uniconvert/"

# Wrapper script
cat > "$ROOT/usr/bin/uniconvert" <<'EOF'
#!/usr/bin/env bash
exec /opt/uniconvert/uniconvert_linux "$@"
EOF
chmod 755 "$ROOT/usr/bin/uniconvert"

# Desktop entry and icon
cp installers/linux/uniconvert.desktop "$ROOT/usr/share/applications/"
cp installers/linux/uniconvert.png "$ROOT/usr/share/icons/hicolor/256x256/apps/uniconvert.png"

# Nautilus extension (optional; works if nautilus-python is installed)
cp installers/linux/nautilus_uniconvert.py "$ROOT/usr/share/nautilus-python/extensions/"

# Debian control file
INSTALLED_SIZE=$(du -sk "$ROOT" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<EOF
Package: uniconvert
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: UniConvert <hello@uniconvert.app>
Homepage: https://github.com/Comet-Suite/UniConvert
Description: Universal multi-format file converter
 Converts between hundreds of audio, video, image, document, archive,
 e-book, and data formats with a drag-and-drop GUI and system tray.
Depends: ffmpeg, libxcb-cursor0
Recommends: pandoc, nautilus-python
Installed-Size: ${INSTALLED_SIZE}
EOF

# Postinst / prerm to update icon cache
cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database -q 2>/dev/null || true
EOF
chmod 755 "$ROOT/DEBIAN/postinst"
cat > "$ROOT/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
EOF
chmod 755 "$ROOT/DEBIAN/prerm"

mkdir -p dist/release
dpkg-deb --build --root-owner-group "$ROOT" "dist/release/uniconvert_${VERSION}_${ARCH}.deb"
echo "Built dist/release/uniconvert_${VERSION}_${ARCH}.deb"
