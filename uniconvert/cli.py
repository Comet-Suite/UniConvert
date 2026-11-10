"""Command-line interface for batch/headless conversions.

Usage:
    python -m uniconvert.cli file1.mp3 file2.wav --to flac --out ./out/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import ConversionJob, convert, ConversionError
from .formats import get_registry


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="uniconvert", description="Convert files between many formats."
    )
    p.add_argument("files", nargs="+", help="Input files")
    p.add_argument("--to", "-t", required=True, help="Target extension (e.g. mp3, png, pdf)")
    p.add_argument("--out", "-o", default=None, help="Output directory (default: same as source)")
    p.add_argument("--overwrite", "-f", action="store_true", help="Overwrite existing files")
    p.add_argument("--list-formats", action="store_true", help="List supported (From,To) pairs")
    p.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)

    reg = get_registry()

    if args.list_formats:
        for s, d in reg.pairs:
            print(f"{s}\t{d}")
        return 0

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    failed = 0
    total = len(args.files)
    fmt = args.to.lower().lstrip(".")
    for i, f in enumerate(args.files, 1):
        src = Path(f)
        if not src.is_file():
            print(f"[{i}/{total}] SKIP (not a file): {src}", file=sys.stderr)
            failed += 1
            continue
        job = ConversionJob(src=src, dst_format=fmt, dst_dir=out_dir, overwrite=args.overwrite)

        def p(pct: float, msg: str, _i=i, _t=total, _n=src.name):
            pct_overall = int(((_i - 1) / _t + pct / _t) * 100)
            print(f"\r[{pct_overall:3d}%] {_n}: {msg}", end="", flush=True)

        try:
            out = convert(job, progress=p)
            print(f"\r[{i}/{total}] OK  {src.name} -> {out.name}")
            ok += 1
        except ConversionError as e:
            print(f"\r[{i}/{total}] FAIL {src.name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone. {ok} succeeded, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
