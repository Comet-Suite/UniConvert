# UniConvert <img src="assets/logo.png" width="48" align="right" alt="UniConvert logo">

**Universal multi-format file converter for Windows, Linux, and macOS.**

Drag files in, pick a target format, click *Convert*. UniConvert handles
hundreds of combinations across:

| Category     | Examples                                                                 |
|--------------|--------------------------------------------------------------------------|
| Audio        | MP3, WAV, FLAC, AAC, OGG, M4A, WMA, Opus, AIFF…                         |
| Video        | MP4, MKV, MOV, AVI, WMV, WebM, FLV, 3GP, GIF…                           |
| Images       | JPG, PNG, WebP, BMP, TIFF, GIF, HEIC, AVIF, SVG, PDF, PSD, AI, EPS…     |
| Documents    | PDF, DOCX, DOC, ODT, RTF, TXT, HTML, Markdown, XLSX, PPTX…             |
| E-books      | EPUB, MOBI, AZW3                                                         |
| Archives     | ZIP, RAR, 7z, TAR, GZ, BZ2, ISO                                          |
| Data         | CSV, JSON, YAML, XML, XLSX                                               |
| Code / text  | Python ↔ JS ↔ Java ↔ C++ ↔ Go ↔ Rust ↔ …, code → highlighted HTML        |

Built-in features:

* Drag-and-drop UI with batch conversion and live progress
* System tray integration with "minimize to tray"
* Right-click shell integration (Windows 11 via registry, GNOME/Nautilus via Python extension)
* Sensible default codecs chosen per output format
* Overwrite protection and cancel-in-progress
* Offline — no telemetry, no cloud calls

## Install

### Windows

Download `UniConvert-0.1.0-Setup.exe` from the [Releases](../../releases) page
and run it. The installer registers a **Convert with UniConvert…** right-click
menu entry in Explorer.

### Linux (Debian / Ubuntu / Pop!_OS / Mint etc.)

```bash
sudo apt install ffmpeg pandoc          # recommended runtime deps
sudo dpkg -i uniconvert_0.1.0_amd64.deb
```

Or run the AppImage / flatpak if you prefer; just make sure `ffmpeg` is on your PATH.

### macOS

Open `UniConvert-0.1.0.dmg`, drag **UniConvert.app** into `/Applications`, then
right-click and choose *Open* once to bypass Gatekeeper. Install `ffmpeg` via
Homebrew: `brew install ffmpeg pandoc`.

## From source

```bash
git clone https://github.com/Comet-Suite/UniConvert.git
cd UniConvert
python -m pip install -e .[full]
python -m uniconvert
```

Dependencies: Python ≥ 3.9, [PyQt6](https://pypi.org/project/PyQt6/),
[Pillow](https://pypi.org/project/Pillow/), plus [ffmpeg](https://ffmpeg.org/)
for audio/video and (optionally) [pandoc](https://pandoc.org/) for richer
document/e-book conversions.

## Building installers

Platform-specific build scripts live in `installers/`:

| Platform | Command                                          | Output                                        |
|----------|--------------------------------------------------|-----------------------------------------------|
| Windows  | `powershell installers\windows\build_exe.ps1`    | `dist/release/UniConvert-0.1.0-Setup.exe`     |
| Linux    | `bash installers/linux/build_deb.sh`             | `dist/release/uniconvert_0.1.0_amd64.deb`     |
| macOS    | `bash installers/macos/build_dmg.sh`             | `dist/release/UniConvert-0.1.0.dmg`           |

## Project layout

```
uniconvert/
├── __init__.py          version metadata
├── __main__.py          python -m uniconvert entry point
├── formats.py           CSV-backed format registry + categories
├── converter.py         dispatcher & backends (ffmpeg, PIL, archive, data…)
└── gui.py               PyQt6 main window, drag & drop, tray, progress
assets/
├── formats.csv          supported (From, To) conversion pairs
├── logo.png / logo.ico  branding
installers/
├── windows/             NSIS script + context-menu .reg files + PowerShell builder
├── linux/               .deb builder + .desktop + Nautilus extension
└── macos/               .dmg builder + .iconset
tests/                   pytest suite
```

## License

MIT. See `LICENSE`.
