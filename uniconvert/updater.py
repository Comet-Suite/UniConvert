"""GitHub-Releases based auto-updater.

Compares the running version against the latest release on
https://github.com/Comet-Suite/UniConvert, and on Windows offers to download
and apply the new installer automatically. On Linux/macOS it shows a dialog
with a download link.

The network check runs on a background thread so the GUI never blocks.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import __version__

REPO = "Comet-Suite/UniConvert"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PAGE = f"https://github.com/{REPO}/releases/latest"


@dataclass
class Release:
    tag: str
    version: tuple
    url: str
    notes: str
    assets: list  # list of (name, browser_download_url, size)


def _parse_version(tag: str) -> tuple:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", tag or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def fetch_latest(timeout: float = 8.0) -> Optional[Release]:
    """Synchronous fetch. Returns None on any network error (offline, etc.)."""
    try:
        req = urllib.request.Request(API, headers={"User-Agent": "UniConvert"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    tag = data.get("tag_name", "")
    assets = [(a["name"], a["browser_download_url"], a["size"])
              for a in data.get("assets", [])]
    return Release(tag=tag, version=_parse_version(tag),
                  url=data.get("html_url", DOWNLOAD_PAGE),
                  notes=data.get("body", ""), assets=assets)


def update_available(latest: Optional[Release] = None) -> Optional[Release]:
    latest = latest or fetch_latest()
    if not latest:
        return None
    return latest if latest.version > _parse_version(__version__) else None


def pick_asset(release: Release) -> Optional[tuple]:
    """Return the best asset (name, url, size) for the current platform."""
    sysname = platform.system().lower()
    order = []
    if sysname == "windows":
        order = ("-Setup.exe", "-portable-windows.zip")
    elif sysname == "linux":
        order = ("_amd64.deb", "-linux-portable.tar.gz")
    elif sysname == "darwin":
        order = ("-macOS.zip",)
    for suffix in order:
        for a in release.assets:
            if a[0].endswith(suffix):
                return a
    return release.assets[0] if release.assets else None


def check_and_prompt(parent=None, silent_if_current: bool = True) -> Optional[Release]:
    """Modal check. Must be called from the GUI thread.

    Returns the Release if the user accepts an update; None otherwise.
    """
    try:
        from PyQt6.QtWidgets import QMessageBox, QApplication
        from PyQt6.QtCore import Qt
    except ImportError:
        return None

    latest = update_available()
    if not latest:
        if not silent_if_current:
            QMessageBox.information(
                parent, "UniConvert is up to date",
                f"You are running the latest version (v{__version__}).")
        return None

    asset = pick_asset(latest)
    size_mb = f" ({asset[2]/1024/1024:.1f} MB)" if asset else ""
    fname = asset[0] if asset else "the update"

    box = QMessageBox(parent)
    box.setWindowTitle("Update available")
    box.setIcon(QMessageBox.Icon.Information)
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(
        f"<h3>A new version of UniConvert is available</h3>"
        f"<p>Installed: <b>v{__version__}</b><br/>"
        f"Latest: <b>{latest.tag}</b></p>"
        f"<p>Recommended: <b>{fname}</b>{size_mb}</p>")
    if latest.notes:
        box.setDetailedText(latest.notes[:4000])
    install_btn = box.addButton("Download and install", QMessageBox.ButtonRole.AcceptRole)
    later_btn = box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(install_btn)
    box.exec()
    return latest if box.clickedButton() is install_btn else None


def check_in_background(parent, on_result: Callable[[Optional[Release]], None]) -> None:
    """Run the update check on a background thread, then call on_result(latest_or_None)
    on the GUI thread. Never blocks the UI."""
    def worker():
        latest = update_available()
        try:
            from PyQt6.QtCore import QMetaObject, Qt
            from PyQt6.QtWidgets import QApplication
            # Schedule the callback on the main thread
            QMetaObject.invokeMethod(parent, "_on_update_checked",
                                     Qt.ConnectionType.QueuedConnection,
                                     GenericArgument=latest)
        except Exception:
            pass
    threading.Thread(target=worker, daemon=True).start()


def download_and_install(release: Release, parent=None, dest_dir: Optional[Path] = None) -> Optional[Path]:
    """Download the recommended asset, then launch it (Windows installer) or
    open the containing folder (Linux/macOS)."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog

    asset = pick_asset(release)
    if not asset:
        QMessageBox.warning(parent, "Update", "No download is available for your platform yet.")
        return None
    name, url, size = asset
    if dest_dir is None:
        dest_dir = Path.home() / "Downloads"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    dest = dest_dir / name

    pd = QProgressDialog(parent)
    pd.setWindowTitle("UniConvert updater")
    pd.setLabelText(f"Downloading {name}…")
    pd.setCancelButtonText("Cancel")
    pd.setRange(0, 100)
    pd.setWindowModality(Qt.WindowModality.WindowModal)
    pd.setMinimumDuration(200)
    pd.show()
    QApplication.processEvents()

    cancelled = {"flag": False}

    def _report(block_count, block_size, total):
        if cancelled["flag"]:
            raise RuntimeError("cancelled")
        if total > 0:
            pct = min(100, int((block_count * block_size * 100) / total))
            pd.setValue(pct)
        else:
            pd.setRange(0, 0)
        QApplication.processEvents()

    def _on_cancel():
        cancelled["flag"] = True
    pd.canceled.connect(_on_cancel)

    try:
        urllib.request.urlretrieve(url, dest, reporthook=_report)
    except Exception as e:
        pd.close()
        if "cancelled" not in str(e).lower():
            QMessageBox.warning(parent, "Download failed", f"Could not download the update:\n{e}")
        return None
    pd.setValue(100)
    pd.close()

    sysname = platform.system()
    try:
        if sysname == "Windows" and dest.suffix.lower() == ".exe":
            # Detach installer and exit. Use cmd /c start so UAC/launcher works even
            # when we exit immediately.
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", str(dest)],
                cwd=str(dest.parent), shell=False, close_fds=True)
            QMessageBox.information(
                parent, "Update ready",
                "The installer will launch now. Save your work and click through.\n"
                "UniConvert will close.")
            QApplication.quit()
            import time; time.sleep(0.3)
            sys.exit(0)
        else:
            # Linux / macOS — open the folder containing the download
            try:
                if sysname == "Darwin":
                    subprocess.Popen(["open", str(dest.parent)], close_fds=True)
                elif sysname == "Linux":
                    subprocess.Popen(["xdg-open", str(dest.parent)], close_fds=True)
            except Exception:
                pass
            QMessageBox.information(
                parent, "Update downloaded",
                f"Saved to:\n{dest}\n\nInstall it, then restart UniConvert.")
    except Exception as e:
        QMessageBox.warning(parent, "Could not launch", str(e))
    return dest
