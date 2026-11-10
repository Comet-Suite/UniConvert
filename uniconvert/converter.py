"""Core conversion dispatcher.

Selects the correct backend (ffmpeg for audio/video/images, Pillow for images,
pandoc for documents, pure-python for archives/data/code) and runs the conversion
in a worker thread, reporting progress and cancellation.
"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore


ProgressCb = Callable[[float, str], None]


class ConversionError(Exception):
    pass


@dataclass
class ConversionJob:
    src: Path
    dst_format: str  # extension without dot, e.g. "mp3"
    dst_dir: Optional[Path] = None
    overwrite: bool = False

    @property
    def dst(self) -> Path:
        target_dir = self.dst_dir or self.src.parent
        stem = self.src.stem
        return target_dir / f"{stem}.{self.dst_format.lower()}"


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _run(cmd: list[str], progress: Optional[ProgressCb] = None) -> None:
    """Run an external command, streaming progress via stderr parsing."""
    if progress:
        progress(0.05, "Starting…")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, bufsize=1, errors="replace")
    assert proc.stderr is not None
    last_pct = 0.0
    for line in proc.stderr:
        # ffmpeg-style "time=00:00:05.00" — estimate from duration
        if "time=" in line and progress:
            try:
                tok = [t for t in line.split() if t.startswith("time=")][0]
                t_str = tok.split("=", 1)[1]
                h, m, s = t_str.split(":")
                seconds = int(h) * 3600 + int(m) * 60 + float(s)
                pct = min(0.95, seconds / max(1.0, seconds + 1.0))
                if pct - last_pct > 0.02:
                    progress(pct, "Converting…")
                    last_pct = pct
            except Exception:
                pass
    proc.wait()
    if proc.returncode != 0:
        err = (proc.stderr.read() if proc.stderr else "") or ""
        raise ConversionError(f"Command failed (exit {proc.returncode}): {' '.join(cmd[:2])}\n{err[:500]}")
    if progress:
        progress(1.0, "Done")


def _convert_audio_video(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    ffmpeg = _which("ffmpeg")
    if not ffmpeg:
        raise ConversionError("ffmpeg is not installed. Please install ffmpeg to convert audio/video files.")
    dst = job.dst
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    cmd = [ffmpeg, "-y", "-i", str(job.src), "-progress", "pipe:2", "-nostats"]
    fmt = job.dst_format.lower()
    # Pick sensible codecs per container
    if fmt in {"mp3"}:
        cmd += ["-c:a", "libmp3lame", "-q:a", "2"]
    elif fmt in {"wav"}:
        cmd += ["-c:a", "pcm_s16le"]
    elif fmt in {"flac"}:
        cmd += ["-c:a", "flac"]
    elif fmt in {"aac", "m4a"}:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    elif fmt in {"ogg", "opus"}:
        cmd += ["-c:a", "libopus" if fmt == "opus" else "libvorbis", "-b:a", "160k"]
    elif fmt in {"mp4", "m4v"}:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "160k"]
    elif fmt in {"mkv", "webm"}:
        cmd += ["-c:v", "libvp9" if fmt == "webm" else "libx264", "-b:v", "0",
                "-crf", "28" if fmt == "webm" else "23",
                "-c:a", "libopus" if fmt == "webm" else "libvorbis", "-b:a", "160k"]
    elif fmt in {"mov", "avi"}:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"]
    elif fmt in {"gif"}:
        cmd += ["-vf", "split[v0][v1];[v0]palettegen[p];[v1][p]paletteuse", "-loop", "0"]
    else:
        # Generic: let ffmpeg pick
        pass
    cmd += [str(dst)]
    _run(cmd, progress)


def _convert_image(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    dst = job.dst
    fmt = job.dst_format.lower()
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    # PIL can handle most image formats
    if Image is None:
        raise ConversionError("Pillow is not installed.")
    if progress:
        progress(0.1, "Loading image…")
    with Image.open(job.src) as im:
        if fmt in {"jpg", "jpeg"}:
            im = im.convert("RGB")
            im.save(dst, "JPEG", quality=92)
        elif fmt == "png":
            im.save(dst, "PNG")
        elif fmt == "bmp":
            im.save(dst, "BMP")
        elif fmt == "webp":
            im.save(dst, "WEBP", quality=90)
        elif fmt == "tiff":
            im.save(dst, "TIFF")
        elif fmt == "gif":
            im.save(dst, "GIF")
        elif fmt == "pdf":
            im.convert("RGB").save(dst, "PDF", resolution=200.0)
        else:
            # Fall back to ffmpeg for heic/avif/raw etc.
            ffmpeg = _which("ffmpeg")
            if ffmpeg:
                _run([ffmpeg, "-y", "-i", str(job.src), str(dst)], progress)
                return
            im.save(dst)
    if progress:
        progress(1.0, "Done")


def _convert_document(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    dst = job.dst
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    fmt = job.dst_format.lower()
    src_ext = job.src.suffix.lower().lstrip(".")
    pandoc = _which("pandoc")
    # Plain-text conversions can be done without pandoc
    if fmt == "txt":
        text = _extract_text(job.src, src_ext)
        dst.write_text(text, encoding="utf-8")
        if progress:
            progress(1.0, "Done")
        return
    if fmt == "html" and src_ext in {"md", "markdown", "txt"}:
        if pandoc:
            _run([pandoc, str(job.src), "-o", str(dst)], progress)
            return
        # Naive fallback: wrap
        text = job.src.read_text(encoding="utf-8", errors="replace")
        import html as htmlmod
        body = htmlmod.escape(text).replace("\n", "<br/>\n")
        dst.write_text(f"<!doctype html><html><body>{body}</body></html>", encoding="utf-8")
        if progress:
            progress(1.0, "Done")
        return
    if pandoc:
        cmd = [pandoc, str(job.src), "-o", str(dst)]
        _run(cmd, progress)
        return
    raise ConversionError(
        f"Pandoc is required to convert {src_ext.upper()} → {fmt.upper()} but is not installed. "
        "Install pandoc (https://pandoc.org) for full document support."
    )


def _extract_text(path: Path, ext: str) -> str:
    ext = ext.lower()
    if ext in {"txt", "md", "html", "rtf", "json", "xml", "yaml", "yml", "csv",
               "py", "js", "java", "cpp", "c", "h", "cs", "go", "rs", "rb", "php",
               "ts", "swift", "kt", "scala", "pl", "lua", "r", "sh", "ps1", "sql", "m"}:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return path.read_bytes().decode("latin-1", errors="replace")
    if ext == "pdf":
        try:
            from pypdf import PdfReader  # type: ignore
            return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
        except Exception:
            return f"[Could not extract text from {path.name}; install pypdf for PDF text extraction]"
    # DOCX etc. best-effort
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return f"[Binary file: {path.name}]"


def _convert_archive(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    src = job.src
    dst = job.dst
    fmt = job.dst_format.lower()
    src_ext = src.suffix.lower().lstrip(".")
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "extracted"
        tmp.mkdir()
        if progress:
            progress(0.1, "Extracting…")
        _extract_archive(src, tmp)
        if progress:
            progress(0.6, "Re-packaging…")
        _create_archive(dst, tmp, fmt)
    if progress:
        progress(1.0, "Done")


def _extract_archive(src: Path, dest: Path) -> None:
    ext = src.suffix.lower().lstrip(".")
    if ext == "zip":
        with zipfile.ZipFile(src) as z:
            z.extractall(dest)
    elif ext in {"tar", "tar.gz", "tgz", "gz", "tar.bz2", "bz2"}:
        if ext == "gz" and src.suffixes[-2:] != [".tar", ".gz"]:
            with gzip.open(src, "rb") as gz, open(dest / src.stem, "wb") as out:
                shutil.copyfileobj(gz, out)
            return
        with tarfile.open(src, "r:*") as t:
            t.extractall(dest)
    elif ext == "7z":
        seven = _which("7z") or _which("7za")
        if not seven:
            raise ConversionError("7-Zip (7z) is required to extract .7z archives.")
        subprocess.run([seven, "x", f"-o{dest}", str(src), "-y"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif ext == "rar":
        unrar = _which("unrar") or _which("rar")
        if not unrar:
            raise ConversionError("unrar is required to extract .rar archives.")
        subprocess.run([unrar, "x", str(src), str(dest) + "/"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        raise ConversionError(f"Cannot extract archive of type: {ext}")


def _create_archive(dst: Path, src_dir: Path, fmt: str) -> None:
    if fmt == "zip":
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(src_dir):
                for f in files:
                    p = Path(root) / f
                    z.write(p, p.relative_to(src_dir))
    elif fmt == "tar":
        with tarfile.open(dst, "w") as t:
            t.add(src_dir, arcname=".")
    elif fmt == "gz":
        # tar.gz
        with tarfile.open(dst, "w:gz") as t:
            t.add(src_dir, arcname=".")
    elif fmt == "7z":
        seven = _which("7z") or _which("7za")
        if not seven:
            raise ConversionError("7-Zip (7z) is required to create .7z archives.")
        subprocess.run([seven, "a", str(dst), str(src_dir) + "/*"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        raise ConversionError(f"Cannot create archive of type: {fmt}")


def _convert_data(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    src = job.src
    dst = job.dst
    src_ext = src.suffix.lower().lstrip(".")
    fmt = job.dst_format.lower()
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    # csv <-> json, json <-> yaml, xml <-> json, xlsx via pandas
    import csv as csvmod
    if src_ext in {"csv", "json", "yaml", "yml"} and fmt in {"csv", "json", "yaml", "yml"}:
        data = _load_structured(src, src_ext)
        _save_structured(data, dst, fmt)
        if progress:
            progress(1.0, "Done")
        return
    if fmt in {"xlsx", "xls"} or src_ext in {"xlsx", "xls"}:
        try:
            import pandas as pd
        except ImportError as e:
            raise ConversionError("pandas + openpyxl are required for Excel conversions.") from e
        if src_ext == "csv":
            df = pd.read_csv(src)
        elif src_ext == "json":
            df = pd.read_json(src)
        elif src_ext in {"xlsx", "xls"}:
            df = pd.read_excel(src)
        else:
            raise ConversionError(f"Cannot read {src_ext} for Excel conversion.")
        if fmt == "csv":
            df.to_csv(dst, index=False)
        elif fmt == "json":
            df.to_json(dst, orient="records", indent=2)
        elif fmt == "xlsx":
            df.to_excel(dst, index=False)
        else:
            raise ConversionError(f"Unsupported data target: {fmt}")
        if progress:
            progress(1.0, "Done")
        return
    # HTML conversions for data
    pandoc = _which("pandoc")
    if pandoc and fmt in {"html", "pdf", "docx"}:
        _run([pandoc, str(src), "-o", str(dst)], progress)
        return
    raise ConversionError(f"Data conversion {src_ext} → {fmt} not supported.")


def _load_structured(path: Path, ext: str):
    text = path.read_text(encoding="utf-8")
    if ext == "json":
        return json.loads(text)
    if ext in {"yaml", "yml"}:
        try:
            import yaml
        except ImportError as e:
            raise ConversionError("PyYAML is required for YAML conversions.") from e
        return yaml.safe_load(text)
    if ext == "csv":
        import csv as csvmod
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csvmod.DictReader(fh))
    raise ConversionError(f"Unsupported structured source: {ext}")


def _save_structured(data, path: Path, fmt: str) -> None:
    if fmt == "json":
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return
    if fmt in {"yaml", "yml"}:
        try:
            import yaml
        except ImportError as e:
            raise ConversionError("PyYAML is required for YAML conversions.") from e
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return
    if fmt == "csv":
        import csv as csvmod
        if isinstance(data, list) and data and isinstance(data[0], dict):
            with path.open("w", newline="", encoding="utf-8") as fh:
                w = csvmod.DictWriter(fh, fieldnames=list(data[0].keys()))
                w.writeheader()
                w.writerows(data)
            return
        # Fallback: list-of-lists
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csvmod.writer(fh)
            for row in data:
                w.writerow(row if isinstance(row, (list, tuple)) else [row])
        return
    raise ConversionError(f"Unsupported structured target: {fmt}")


def _convert_code(job: ConversionJob, progress: Optional[ProgressCb]) -> None:
    """Code 'transpilation' is lossy/pretty-print only. We support data-style
    conversions (JSON/YAML/XML) and syntax-highlighted HTML, plus naive
    conversions for text-style pairs. Real language translation would require
    an LLM; here we copy source with a header indicating the target language
    and preserve content for text-based pairs (py<->html, etc.)."""
    src = job.src
    dst = job.dst
    fmt = job.dst_format.lower()
    src_ext = src.suffix.lower().lstrip(".")
    if dst.exists() and not job.overwrite:
        raise ConversionError(f"Output already exists: {dst}")
    text = src.read_text(encoding="utf-8", errors="replace")
    if fmt == "html":
        import html as htmlmod
        body = htmlmod.escape(text).replace("\n", "<br/>\n")
        dst.write_text(
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{src.name}</title></head><body><pre><code>{body}</code></pre></body></html>",
            encoding="utf-8")
    elif fmt in {"json", "yaml", "yml", "xml", "csv"}:
        _convert_data(job, progress)
        return
    else:
        # Lossy "translation": leave a comment header + original code.
        header = (
            f"// Converted from {src_ext} to {fmt} by UniConvert v0.1.0\n"
            f"// Note: semantic translation between programming languages requires an AI backend.\n"
            f"// The original source is preserved below; adjust by hand as needed.\n\n"
        )
        dst.write_text(header + text, encoding="utf-8")
    if progress:
        progress(1.0, "Done")


def convert(job: ConversionJob, progress: Optional[ProgressCb] = None,
            cancel_check: Optional[Callable[[], bool]] = None) -> Path:
    """Run a conversion job and return the output path."""
    from .formats import categorise
    src_ext = job.src.suffix.lower().lstrip(".")
    cat = categorise(src_ext)
    target_cat = categorise(job.dst_format)
    # Some cross-category conversions (e.g. mp4->mp3, pdf->jpg, svg->pdf) use ffmpeg/PIL
    if cat in {"audio", "video"} or target_cat in {"audio", "video"}:
        _convert_audio_video(job, progress)
    elif cat == "image" or (cat != "image" and job.dst_format.lower() in {"jpg", "jpeg", "png", "bmp", "webp", "tiff", "gif", "pdf"}):
        if cat == "document" and job.dst_format.lower() == "pdf":
            _convert_document(job, progress)
        else:
            _convert_image(job, progress)
    elif cat == "archive":
        _convert_archive(job, progress)
    elif cat == "data":
        _convert_data(job, progress)
    elif cat == "ebook" or target_cat == "ebook":
        pandoc = _which("pandoc")
        if pandoc:
            _run([pandoc, str(job.src), "-o", str(job.dst)], progress)
        else:
            raise ConversionError("Pandoc is required for e-book conversions.")
    elif cat == "document":
        _convert_document(job, progress)
    elif cat == "code":
        _convert_code(job, progress)
    else:
        raise ConversionError(f"No converter registered for {src_ext} → {job.dst_format}")
    return job.dst
