#!/usr/bin/env python3
"""
rotate.py — rotate all images in a directory (in-place).

Usage:
    rotate.py <dir>               # 180° (default)
    rotate.py <dir> --angle 90
    rotate.py <dir> --output-dir /otro/dir/

Options:
    --angle       Degrees to rotate counter-clockwise (default: 180)
    --output-dir  Save to a different directory instead of overwriting
    --quality     JPEG quality (default: 95)
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filename_date import effective_mtime

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def main():
    parser = argparse.ArgumentParser(
        description="Rotate all images in a directory."
    )
    parser.add_argument("dir", help="Directory with images")
    parser.add_argument("--angle", type=int, default=180,
                        help="Degrees to rotate counter-clockwise (default: 180)")
    parser.add_argument("--output-dir", help="Output directory (default: overwrite originals)")
    parser.add_argument("--quality", type=int, default=95,
                        help="JPEG quality (default: 95)")
    args = parser.parse_args()

    src_dir = Path(args.dir).expanduser().resolve()
    if not src_dir.is_dir():
        print(f"Error: not a directory: {src_dir}", file=sys.stderr)
        sys.exit(1)

    images = sorted(f for f in src_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
    if not images:
        print(f"Error: no images found in {src_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else src_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(images)
    for i, src in enumerate(images, 1):
        dst = out_dir / src.name
        mtime = effective_mtime(src)
        img = Image.open(src)
        img.rotate(args.angle, expand=True).save(dst, quality=args.quality)
        os.utime(dst, (mtime, mtime))
        if i % 50 == 0 or i == total:
            print(f"{i}/{total} done")

    print(f"Completado! {total} imágenes rotadas {args.angle}°")


if __name__ == "__main__":
    main()
