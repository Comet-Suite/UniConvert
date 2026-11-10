"""PyQt6 GUI for UniConvert."""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QSettings, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QComboBox, QFileDialog, QProgressBar,
    QMessageBox, QSystemTrayIcon, QMenu, QStatusBar, QCheckBox, QGroupBox, QStyle,
)

from . import __app_name__, __version__
from .converter import ConversionJob, convert, ConversionError
from .formats import get_registry, categorise
from . import updater


def _assets_dir() -> Path:
    """Return the assets/ directory whether running from source, from a PyInstaller
    bundle (sys._MEIPASS), or from the Windows embedded-Python layout."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "assets"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "assets"
    # Source tree: uniconvert/gui.py -> ../assets
    return Path(__file__).resolve().parent.parent / "assets"


ASSETS_DIR = _assets_dir()


def load_icon() -> QIcon:
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            return QIcon(pix)
    return QIcon()


class ConvertWorker(QThread):
    progress = pyqtSignal(int, str)
    file_done = pyqtSignal(str, str)
    finished_all = pyqtSignal(int, int)
    log = pyqtSignal(str)

    def __init__(self, jobs: List[ConversionJob], overwrite: bool = False):
        super().__init__()
        self.jobs = jobs
        self.overwrite = overwrite
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        ok = 0
        failed = 0
        total = len(self.jobs)
        for i, job in enumerate(self.jobs, 1):
            if self._cancel:
                self.log.emit("Cancelled by user.")
                break
            overall = int(((i - 1) / max(1, total)) * 100)
            self.progress.emit(overall, f"[{i}/{total}] {job.src.name} -> .{job.dst_format}")

            def p(pct: float, msg: str, _i=i, _total=total):
                base = ((_i - 1) / _total) * 100
                self.progress.emit(int(base + pct * (100 / _total)), msg)

            try:
                out = convert(job, progress=p, cancel_check=lambda: self._cancel)
                self.file_done.emit(str(job.src), f"OK -> {out.name}")
                ok += 1
            except ConversionError as e:
                self.file_done.emit(str(job.src), f"FAILED: {e}")
                failed += 1
            except Exception as e:  # pragma: no cover
                self.file_done.emit(str(job.src), f"ERROR: {e}")
                failed += 1
        self.progress.emit(100, "Done")
        self.finished_all.emit(ok, failed)


class DropList(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        paths = []
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p:
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
        e.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, initial_files: Optional[List[str]] = None):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(820, 600)
        icon = load_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.registry = get_registry()
        self.files: List[Path] = []
        self.worker: Optional[ConvertWorker] = None
        self._build_menu()
        self._build_ui()
        self._build_tray(icon)
        self._apply_startup_setting()
        # Queue initial files (e.g. from right-click "Convert with UniConvert...")
        if initial_files:
            QTimer.singleShot(100, lambda: self.add_files(initial_files))
        # Background update check — runs on a worker thread after 4 seconds
        QTimer.singleShot(4000, self._background_update_check)

    # ---------- Menu ----------
    def _build_menu(self) -> None:
        mb = self.menuBar()
        file_menu = mb.addMenu("&File")
        add_act = QAction("Add &files...", self, shortcut="Ctrl+O", triggered=self._browse_files)
        clear_act = QAction("&Clear list", self, shortcut="Ctrl+L", triggered=self._clear_files)
        quit_act = QAction("&Quit", self, shortcut="Ctrl+Q", triggered=self._quit_app)
        file_menu.addAction(add_act)
        file_menu.addAction(clear_act)
        file_menu.addSeparator()
        file_menu.addAction(quit_act)

        opts_menu = mb.addMenu("&Options")
        self.startup_act = QAction("Start at &login", self, checkable=True)
        self.startup_act.setChecked(self._is_autostart_enabled())
        self.startup_act.toggled.connect(self._set_autostart)
        opts_menu.addAction(self.startup_act)

        help_menu = mb.addMenu("&Help")
        update_act = QAction("&Check for updates...", self, triggered=lambda: self._check_updates(False))
        about_act = QAction(f"&About {__app_name__}", self, triggered=self._show_about)
        help_menu.addAction(update_act)
        help_menu.addSeparator()
        help_menu.addAction(about_act)

    def _quit_app(self) -> None:
        # Properly quit even when minimized to tray
        if getattr(self, "tray", None):
            self.tray.hide()
        QApplication.instance().quit()

    def _show_about(self) -> None:
        icon = load_icon()
        text = (
            f"<h2>{__app_name__} v{__version__}</h2>"
            "<p>Universal multi-format file converter.</p>"
            "<p>Convert between hundreds of audio, video, image, document, "
            "archive, e-book, and data formats.</p>"
            f"<p style='color:#666'>Running on Python {platform.python_version()} / "
            f"{platform.system()} {platform.release()}</p>"
            "<p><a href='https://github.com/Comet-Suite/UniConvert'>github.com/Comet-Suite/UniConvert</a></p>"
        )
        box = QMessageBox(self)
        box.setWindowTitle(f"About {__app_name__}")
        box.setText(text)
        if not icon.isNull():
            box.setIconPixmap(icon.pixmap(64, 64))
        box.exec()

    # ---------- Updater ----------
    def _background_update_check(self) -> None:
        """Fire the update check on a worker thread; if there's an update,
        show the prompt from the main thread."""
        import threading
        def worker():
            latest = updater.update_available()
            if latest is not None:
                QMetaObject_method = None  # just invoke via singleShot
                QTimer.singleShot(0, lambda: self._prompt_update(latest))
        threading.Thread(target=worker, daemon=True).start()

    def _prompt_update(self, latest) -> None:
        # Don't interrupt if a conversion is running
        if self.worker and self.worker.isRunning():
            return
        chosen = updater.check_and_prompt(parent=self, silent_if_current=True)
        if chosen is not None:
            updater.download_and_install(latest, parent=self)

    def _check_updates(self, silent_if_current: bool = False) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            latest = updater.update_available()
        finally:
            QApplication.restoreOverrideCursor()
        if latest is None:
            if not silent_if_current:
                QMessageBox.information(self, "Up to date",
                                        f"You are running the latest version (v{__version__}).")
            return
        if updater.check_and_prompt(parent=self, silent_if_current=silent_if_current) is not None:
            updater.download_and_install(latest, parent=self)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        header = QLabel(
            f"<h2 style='margin:0'>{__app_name__}</h2>"
            f"<div style='color:#666'>Universal multi-format file converter — "
            f"audio, video, images, documents, archives, data, e-books &amp; code</div>")
        root.addWidget(header)

        self.list = DropList()
        self.list.files_dropped.connect(self.add_files)
        self.list.setToolTip("Drag & drop files here, or click 'Add files...'")
        root.addWidget(self.list, 1)

        fmt_box = QGroupBox("Output format")
        fmt_layout = QHBoxLayout(fmt_box)
        fmt_layout.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        for cat in ["auto"] + sorted(self.registry.all_categories()):
            self.cat_combo.addItem(cat.capitalize(), cat)
        self.cat_combo.currentIndexChanged.connect(self._on_category_changed)
        fmt_layout.addWidget(self.cat_combo)

        fmt_layout.addWidget(QLabel("Convert to:"))
        self.fmt_combo = QComboBox()
        fmt_layout.addWidget(self.fmt_combo, 1)

        self.overwrite_chk = QCheckBox("Overwrite existing files")
        fmt_layout.addWidget(self.overwrite_chk)
        root.addWidget(fmt_box)

        out_box = QHBoxLayout()
        self.out_label = QLabel("Output folder: (same as source)")
        self.out_label.setStyleSheet("color:#555")
        out_box.addWidget(self.out_label, 1)
        self.out_btn = QPushButton("Choose folder...")
        self.out_btn.clicked.connect(self._choose_out_dir)
        out_box.addWidget(self.out_btn)
        self.out_dir: Optional[Path] = None
        root.addLayout(out_box)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add files...")
        self.add_btn.clicked.connect(self._browse_files)
        btns.addWidget(self.add_btn)
        self.clear_btn = QPushButton("Clear list")
        self.clear_btn.clicked.connect(self._clear_files)
        btns.addWidget(self.clear_btn)
        btns.addStretch(1)
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;padding:8px 22px;border-radius:6px;font-weight:bold;}"
            "QPushButton:hover{background:#1d4ed8;}"
            "QPushButton:disabled{background:#9ca3af;}")
        self.convert_btn.clicked.connect(self._start_conversion)
        btns.addWidget(self.convert_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_conversion)
        btns.addWidget(self.cancel_btn)
        root.addLayout(btns)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready. Drag files to begin.")

        # Populate the format dropdown for the initial category
        self._on_category_changed(0)

    @property
    def status(self):
        return self._status_bar

    # ---------- Tray ----------
    def _build_tray(self, icon: QIcon) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(
            icon or self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        self.tray.setToolTip(f"{__app_name__} v{__version__}")
        menu = QMenu()
        show_act = QAction("Show UniConvert", self)
        show_act.triggered.connect(self._show_from_tray)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self._quit_app)
        menu.addAction(show_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, e) -> None:
        if self.tray is not None and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                __app_name__,
                "UniConvert is still running in the tray. Right-click the tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information, 3000)
            e.ignore()
        else:
            super().closeEvent(e)

    # ---------- Files ----------
    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Choose files to convert")
        if files:
            self.add_files(files)

    def _choose_out_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if d:
            self.out_dir = Path(d)
            self.out_label.setText(f"Output folder: {d}")
        else:
            self.out_dir = None
            self.out_label.setText("Output folder: (same as source)")

    def add_files(self, paths: List[str]) -> None:
        added = 0
        for p in paths:
            path = Path(p)
            if path.is_file() and path not in self.files:
                self.files.append(path)
                item = QListWidgetItem(f"  {path.name}     -     {path.suffix.upper() or '?'}     ({path.parent})")
                item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                self.list.addItem(item)
                added += 1
        if added:
            self.status.showMessage(f"Added {added} file(s). {len(self.files)} total.")
            self._auto_pick_format()

    def _clear_files(self) -> None:
        self.files.clear()
        self.list.clear()
        self.progress.setValue(0)
        self.status.showMessage("List cleared.")

    def _on_category_changed(self, idx: int) -> None:
        cat = self.cat_combo.currentData()
        self.fmt_combo.clear()
        if cat == "auto":
            seen = set()
            for c in sorted(self.registry.all_categories()):
                for s, dst in self.registry.pairs:
                    if categorise(s) == c and dst not in seen:
                        seen.add(dst)
                        self.fmt_combo.addItem(f"{c.capitalize()} -> {dst.upper()}", dst)
        else:
            exts = sorted({dst for s, dst in self.registry.pairs
                          if categorise(s) == cat or categorise(dst) == cat})
            for e in exts:
                self.fmt_combo.addItem(e.upper(), e)
        if self.fmt_combo.count() == 0:
            self.fmt_combo.addItem("(no formats)", "")

    def _auto_pick_format(self) -> None:
        if not self.files:
            return
        src_ext = self.files[0].suffix.lower().lstrip(".")
        targets = self.registry.targets_for(src_ext)
        if not targets:
            return
        for pref in ("mp3", "png", "pdf", "mp4", "txt", "zip", "json"):
            if pref in targets:
                for i in range(self.fmt_combo.count()):
                    if self.fmt_combo.itemData(i) == pref:
                        self.fmt_combo.setCurrentIndex(i)
                        return
        self.fmt_combo.setCurrentIndex(0)

    # ---------- Conversion ----------
    def _start_conversion(self) -> None:
        if not self.files:
            QMessageBox.information(self, "No files", "Add some files first (drag & drop or Add files...).")
            return
        fmt = self.fmt_combo.currentData()
        if not fmt:
            QMessageBox.warning(self, "No format", "Choose an output format.")
            return
        jobs = []
        skipped = 0
        for f in self.files:
            src_ext = f.suffix.lower().lstrip(".")
            cross = (categorise(src_ext) in {"image", "document", "audio", "video"}
                     and categorise(fmt) in {"image", "document", "audio", "video"})
            if not self.registry.is_supported(src_ext, fmt) and not cross:
                skipped += 1
                continue
            jobs.append(ConversionJob(src=f, dst_format=fmt, dst_dir=self.out_dir,
                                      overwrite=self.overwrite_chk.isChecked()))
        if not jobs:
            QMessageBox.warning(self, "No convertible files",
                                f"None of the selected files can be converted to {fmt.upper()}.")
            return
        if skipped:
            self.status.showMessage(f"Skipping {skipped} file(s) that don't support {fmt.upper()}.")
        self.progress.setValue(0)
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.add_btn.setEnabled(False)
        self.worker = ConvertWorker(jobs, overwrite=self.overwrite_chk.isChecked())
        self.worker.progress.connect(self._on_progress)
        self.worker.file_done.connect(self._on_file_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _cancel_conversion(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.status.showMessage("Cancelling...")

    def _on_progress(self, pct: int, msg: str) -> None:
        self.progress.setValue(pct)
        self.status.showMessage(msg)

    def _on_file_done(self, src: str, msg: str) -> None:
        name = Path(src).name
        for i in range(self.list.count()):
            it = self.list.item(i)
            txt = it.text().strip()
            if txt.startswith(name):
                if msg.startswith("OK"):
                    it.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
                else:
                    it.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
                it.setText(f"  {name}     -     {msg}")
                break

    def _on_finished(self, ok: int, failed: int) -> None:
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_btn.setEnabled(True)
        msg = f"Finished: {ok} succeeded, {failed} failed."
        self.status.showMessage(msg)
        if self.tray:
            self.tray.showMessage(__app_name__, msg,
                                  QSystemTrayIcon.MessageIcon.Information, 4000)
        if failed:
            QMessageBox.warning(self, "Completed with errors", msg)
        else:
            QMessageBox.information(self, "Done", msg)

    # ---------- Autostart ----------
    def _autostart_path(self) -> Optional[Path]:
        sysname = platform.system()
        if sysname == "Windows":
            return Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/UniConvert.bat"
        if sysname == "Linux":
            return Path.home() / ".config/autostart/uniconvert.desktop"
        if sysname == "Darwin":
            return Path.home() / "Library/LaunchAgents/app.uniconvert.UniConvert.plist"
        return None

    def _is_autostart_enabled(self) -> bool:
        p = self._autostart_path()
        return bool(p and p.exists())

    def _apply_startup_setting(self) -> None:
        self.startup_act.blockSignals(True)
        self.startup_act.setChecked(self._is_autostart_enabled())
        self.startup_act.blockSignals(False)

    def _set_autostart(self, enabled: bool) -> None:
        p = self._autostart_path()
        if p is None:
            return
        if enabled:
            p.parent.mkdir(parents=True, exist_ok=True)
            sysname = platform.system()
            if sysname == "Linux":
                p.write_text(
                    "[Desktop Entry]\n"
                    "Type=Application\nName=UniConvert\nExec=uniconvert\n"
                    "Terminal=false\nX-GNOME-Autostart-enabled=true\n",
                    encoding="utf-8")
            elif sysname == "Darwin":
                p.write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"\n'
                    ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>'
                    '<key>Label</key><string>app.uniconvert.UniConvert</string>'
                    '<key>ProgramArguments</key><array><string>uniconvert</string></array>'
                    '<key>RunAtLoad</key><true/></dict></plist>\n', encoding="utf-8")
            else:
                # Windows: batch file in Startup folder (launches UniConvert.exe)
                install_dir = os.environ.get("UNICONVERT_DIR",
                                             str(Path(__file__).resolve().parent.parent))
                exe = Path(install_dir) / "UniConvert.exe"
                p.write_text(f'@echo off\r\nstart "" "{exe}"\r\n', encoding="utf-8")
        else:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("UniConvert")
    app.setQuitOnLastWindowClosed(False)
    # Any files passed on the command line (from right-click "Convert with UniConvert...")
    initial = [a for a in sys.argv[1:] if not a.startswith("-") and Path(a).is_file()]
    w = MainWindow(initial_files=initial if initial else None)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
