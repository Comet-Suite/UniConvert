"""Format registry: loads supported conversions from the bundled CSV and groups
them into categories (audio, video, image, document, archive, data, ebook, code).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

FORMATS_CSV = Path(__file__).resolve().parent.parent / "assets" / "formats.csv"


AUDIO_EXTS = {"mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "aiff", "opus",
              "ape", "ac3", "dts", "midi", "amr", "au", "ra", "voc", "w64"}
VIDEO_EXTS = {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "mpeg", "mpg",
              "m4v", "3gp", "3g2", "vob", "ogv", "asf", "rmvb", "divx", "xvid",
              "ts", "mts", "gif"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "bmp", "tiff", "webp", "heic", "avif", "svg",
              "raw", "cr2", "nef", "arw", "dng", "orf", "rw2", "psd", "ai", "eps"}
DOC_EXTS = {"pdf", "docx", "doc", "odt", "rtf", "txt", "html", "md", "xlsx", "xls",
            "ods", "csv", "pptx", "ppt", "odp", "key", "xml", "json", "yaml", "yml"}
EBOOK_EXTS = {"epub", "mobi", "azw3"}
ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "bz2", "iso"}
CODE_EXTS = {"py", "js", "java", "cpp", "cc", "cxx", "c", "h", "hpp", "go", "rs", "rb",
             "php", "ts", "swift", "kt", "scala", "pl", "lua", "r", "m", "sql", "sh",
             "ps1", "html", "css", "json", "xml", "yaml", "yml", "md", "toml", "ini",
             "cfg", "bat", "cmd"}


def categorise(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in EBOOK_EXTS:
        return "ebook"
    if ext in ARCHIVE_EXTS:
        return "archive"
    if ext in DOC_EXTS:
        if ext in {"csv", "json", "xml", "yaml", "yml", "xlsx", "xls", "ods"}:
            return "data"
        return "document"
    if ext in CODE_EXTS:
        return "code"
    return "other"


@dataclass
class FormatRegistry:
    """Holds every supported (source, target) conversion pair."""
    pairs: List[Tuple[str, str]] = field(default_factory=list)
    sources_by_category: Dict[str, Set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.pairs = []
        self.sources_by_category = {
            "audio": set(), "video": set(), "image": set(), "document": set(),
            "data": set(), "archive": set(), "ebook": set(), "code": set(),
        }
        self._load()

    # Extensions in the CSV that are labels (not real file extensions) — skip them
    _SKIP = {"c++", "c#"}

    def _load(self) -> None:
        with FORMATS_CSV.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                src = row["From"].strip().lower()
                dst = row["To"].strip().lower()
                if not src or not dst:
                    continue
                if src in self._SKIP or dst in self._SKIP:
                    continue
                self.pairs.append((src, dst))
                cat = categorise(src)
                self.sources_by_category.setdefault(cat, set()).add(src)
                dcat = categorise(dst)
                self.sources_by_category.setdefault(dcat, set()).add(dst)

    def targets_for(self, src_ext: str) -> List[str]:
        src_ext = src_ext.lower().lstrip(".")
        return sorted({dst for s, dst in self.pairs if s == src_ext})

    def is_supported(self, src_ext: str, dst_ext: str) -> bool:
        s = src_ext.lower().lstrip(".")
        d = dst_ext.lower().lstrip(".")
        return (s, d) in self.pairs

    def all_categories(self) -> Iterable[str]:
        return (c for c in self.sources_by_category if self.sources_by_category[c])


_registry: FormatRegistry | None = None


def get_registry() -> FormatRegistry:
    global _registry
    if _registry is None:
        _registry = FormatRegistry()
    return _registry
