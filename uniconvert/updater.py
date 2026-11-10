"""GitHub-Releases based auto-updater.

Compares the running version against the latest release on
https://github.com/Comet-Suite/UniConvert, and on Windows offers to download
and apply the new installer automatically. On Linux/macOS it shows a dialog
with a download link.
"""
from __future__ import annotations

import json
import platform
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import __version__

REPO = "Comet-Suite/UniConvert"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PAGE = f"https://github.com/{REPO}/releases/latest"


@dataclass
class Release:
    tag: str
    version: tuple  # (major, minor, patch)
    url: str
    notes: str
    assets: list  # list of (name, browser_download_url, size)


def _parse_version(tag: str) -> tuple:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", tag or "")
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def fetch_latest(timeout: float = 6.0) -> Optional[Release]:
    try:
        req = urllib.request.Request(API, headers={"User-Agent": "UniConvert"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    tag = data.get("tag_name", "")
    assets = [(a["name"], a["browser_download_url"], a["size"])
              for a in data.get("assets", [])]
    return Release(
        tag=tag,
        version=_parse_version(tag),
        url=data.get("html_url", DOWNLOAD_PAGE),
        notes=data.get("body", ""),
        assets=assets,
    )


def update_available(latest: Optional[Release] = None) -> Optional[Release]:
    latest = latest or fetch_latest()
    if not latest:
        return None
    current = _parse_version(__version__)
    if latest.version > current:
        return latest
    return None


def pick_asset(release: Release) -> Optional[tuple]:
    """Return the best asset URL for the current platform."""
    sysname = platform.system().lower()
    arch = platform.machine().lower()
    if sysname == "windows":
        for name, url, size in release.assets:
            if name.endswith("-Setup.exe"):
                return (name, url, size)
        for name, url, size in release.assets:
            if name.endswith("-portable-windows.zip"):
                return (name, url, size)
    elif sysname == "linux":
        for name, url, size in release.assets:
            if name.endswith(".deb"):
                return (name, url, size)
        for name, url, size in release.assets:
            if name.endswith("-linux-portable.tar.gz"):
                return (name, url, size)
    elif sysname == "darwin":
        for name, url, size in release.assets:
            if "macos" in name.lower() and name.endswith(".zip"):
                return (name, url, size)
    return release.assets[0] if release.assets else None


def check_and_prompt(parent=None, silent_if_current: bool = True) -> Optional[Release]:
    """Non-blocking check: if a new version exists, pop up a dialog.

    Returns the Release if an update is available and the user accepts,
    else None. On Windows the caller can then run `download_and_install`.
    """
    try:
        from PyQt6.QtWidgets import QMessageBox, QApplication
    except ImportError:
        return None
    latest = update_available()
    if not latest:
        if not silent_if_current:
            QMessageBox.information(parent, "UniConvert is up to date",
                                    f"You are running the latest version ({__version__}).")
        return None

    asset = pick_asset(latest)
    asset_text = f"\n\nRecommended download: {asset[0]} ({asset[2]/1024/1024:.1f} MB)" if asset else ""
    box = QMessageBox(parent)
    box.setWindowTitle("Update available")
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(f"<h3>A new version of UniConvert is available</h3>"
                f"<p>Installed: <b>v{__version__}</b><br>"
                f"Latest: <b>{latest.tag}</b></p>{asset_text}")
    box.setDetailedText(latest.notes[:4000] if latest.notes else "")
    install_btn = box.addButton("Download and install", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is install_btn:
        return latest
    return None


def download_and_install(release: Release, dest_dir: Optional[Path] = None) -> Optional[Path]:
    """Download the recommended asset for the current platform.

    On Windows, after download we shell-execute the installer (which will
    overwrite the existing install). On other platforms we just save to
    ~/Downloads and open the containing folder.
    """
    import os
    import tempfile
    import urllib.request
    from PyQt6.QtWidgets import QMessageBox, QProgressDialog
    from PyQt6.QtCore import Qt

    asset = pick_asset(release)
    if not asset:
        return None
    name, url, size = asset
    if dest_dir is None:
        dest_dir = Path.home() / "Downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name

    pd = QProgressDialog(f"Downloading {name}…", "Cancel", 0, 100)
    pd.setWindowTitle("UniConvert updater")
    pd.setWindowModality(Qt.WindowModality.WindowModal)
    pd.setMinimumDuration(200)

    def _report(block_count, block_size, total):
        if total <= 0:
            pd.setRange(0, 0)
            return
        pct = min(100, int((block_count * block_size * 100) / total))
        pd.setValue(pct)
        QApplication.processEvents()  # type: ignore
        if pd.wasCanceled():
            raise RuntimeError("cancelled")

    try:
        urllib.request.urlretrieve(url, dest, reporthook=_report)
    except Exception as e:
        pd.close()
        QMessageBox.warning(None, "Download failed", f"Could not download update:\n{e}")
        return None
    pd.close()

    # Launch the installer / open folder
    if platform.system() == "Windows" and dest.suffix.lower() == ".exe":
        try:
            import subprocess
            subprocess.Popen([str(dest)], cwd=str(dest.parent), shell=False)
            QMessageBox.information(None, "Update downloaded",
                                    "The installer will launch now. Save your work and click through. "
                                    "UniConvert will close.")
            sys.exit(0)
        except Exception as e:
            QMessageBox.warning(None, "Could not launch installer", str(e))
    else:
        try:
            import subprocess
            if platform.system() == "Darwin":
                subprocess.Popen(["open", str(dest.parent)])
            elif platform.system() == "Linux":
                subprocess.Popen(["xdg-open", str(dest.parent)])
        except Exception:
            pass
        QMessageBox.information(None, "Update downloaded",
                                f"Saved to:\n{dest}\n\nInstall it with your package manager, "
                                "then restart UniConvert.")
    return dest
