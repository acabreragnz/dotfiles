#!/usr/bin/env python3
"""
rotate.py — rotate one image or all images in a directory.

Usage:
    rotate.py <image_or_dir> --angle 180
    rotate.py <image_or_dir> --angle 90 --output-dir /path/to/output
    rotate.py <image_or_dir> --angle 270 --in-place

Options:
    --angle       Degrees to rotate counter-clockwise (default: 180)
    --in-place    Overwrite originals (default when input is a directory)
    --output-dir  Save results here instead of overwriting
    --quality     JPEG quality for output (default: 95)
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def rotate_image(src: Path, dst: Path, angle: int, quality: int):
    img = Image.open(src)
    rotated = img.rotate(angle, expand=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    rotated.save(dst, quality=quality)


def collect_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in IMAGE_EXTS else []
    return sorted(f for f in path.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS)


def main():
    parser = argparse.ArgumentParser(
        description="Rotate one image or all images in a directory."
    )
    parser.add_argument("input", help="Image file or directory")
    parser.add_argument("--angle", type=int, default=180,
                        help="Degrees to rotate counter-clockwise (default: 180)")
    parser.add_argument("--in-place", action="store_true",
                        help="Overwrite originals (default for directories)")
    parser.add_argument("--output-dir", help="Output directory (single file: defaults to same dir with suffix)")
    parser.add_argument("--quality", type=int, default=95,
                        help="JPEG quality (default: 95)")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    images = collect_images(input_path)
    if not images:
        print(f"Error: no images found in {input_path}", file=sys.stderr)
        sys.exit(1)

    is_dir = input_path.is_dir()
    in_place = args.in_place or (is_dir and not args.output_dir)

    if in_place:
        pairs = [(img, img) for img in images]
    elif args.output_dir:
        out_dir = Path(args.output_dir).expanduser().resolve()
        if is_dir:
            pairs = [(img, out_dir / img.name) for img in images]
        else:
            pairs = [(images[0], out_dir / images[0].name)]
    else:
        # single file, no output_dir → save next to original with suffix
        src = images[0]
        dst = src.parent / f"{src.stem}_rot{args.angle}{src.suffix}"
        pairs = [(src, dst)]

    total = len(pairs)
    for i, (src, dst) in enumerate(pairs, 1):
        rotate_image(src, dst, args.angle, args.quality)
        if total > 1 and (i % 50 == 0 or i == total):
            print(f"{i}/{total} done")

    if total == 1:
        print(f"→ {pairs[0][1]}")
    else:
        print(f"Completado! {total} imágenes rotadas {args.angle}°")


if __name__ == "__main__":
    main()
