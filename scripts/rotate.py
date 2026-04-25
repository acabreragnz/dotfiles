#!/usr/bin/env python3
"""
rotate.py — rotate all images in a directory.

Usage:
    rotate.py <dir>                       # 180°, output a <dir>_rotated_180/
    rotate.py <dir> --angle 90
    rotate.py <dir> --output-dir /otro/dir/
    rotate.py <dir> --in-place            # sobreescribe (sólo si lo pedís explícito)

Comportamiento:
    - JPEG + ángulo múltiplo de 90: jpegtran -rotate (LOSSLESS, preserva EXIF).
    - JPEG + ángulo arbitrario: PIL re-encode preservando EXIF.
    - PNG/WebP/etc: PIL, optimize=True para PNG.

Options:
    --angle       Degrees to rotate counter-clockwise (default: 180)
    --output-dir  Output directory
    --in-place    Sobreescribe los originales (no recomendado)
    --quality     JPEG quality si se cae a re-encode (default: 95)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filename_date import effective_mtime

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
JPEG_EXTS = {".jpg", ".jpeg"}

# jpegtran toma rotación clockwise; PIL .rotate() es counter-clockwise.
# Mapeo CCW → CW para mantener semántica del script anterior.
JPEGTRAN_CW = {90: 270, 180: 180, 270: 90}


def rotate_jpeg_lossless(src: Path, dst: Path, angle: int) -> bool:
    """Rota JPEG con jpegtran (lossless, preserva EXIF). Devuelve True si tuvo éxito."""
    cw = JPEGTRAN_CW.get(angle % 360)
    if cw is None:
        return False
    if not shutil.which("jpegtran"):
        return False
    # -trim porque jpegtran requiere dimensiones múltiplos de MCU para rotación perfecta;
    # -copy all preserva EXIF/ICC/comments.
    try:
        subprocess.run(
            ["jpegtran", "-rotate", str(cw), "-trim", "-copy", "all",
             "-outfile", str(dst), str(src)],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def rotate_pil(src: Path, dst: Path, angle: int, quality: int) -> None:
    img = Image.open(src)
    exif = img.info.get("exif", b"")
    rotated = img.rotate(angle, expand=True)
    save_kwargs: dict = {}
    ext = dst.suffix.lower()
    if ext in JPEG_EXTS:
        save_kwargs["quality"] = quality
        save_kwargs["subsampling"] = "keep" if src.suffix.lower() in JPEG_EXTS else 0
        if exif:
            save_kwargs["exif"] = exif
    elif ext == ".png":
        save_kwargs["optimize"] = True
    elif ext == ".webp":
        save_kwargs["quality"] = quality
        save_kwargs["method"] = 6
        if exif:
            save_kwargs["exif"] = exif
    rotated.save(dst, **save_kwargs)


def main():
    parser = argparse.ArgumentParser(description="Rotate all images in a directory.")
    parser.add_argument("dir", help="Directory with images")
    parser.add_argument("--angle", type=int, default=180,
                        help="Degrees CCW (default: 180)")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--in-place", action="store_true",
                        help="Sobreescribe los originales")
    parser.add_argument("--quality", type=int, default=95,
                        help="JPEG quality si se cae a re-encode (default: 95)")
    args = parser.parse_args()

    src_dir = Path(args.dir).expanduser().resolve()
    if not src_dir.is_dir():
        print(f"Error: not a directory: {src_dir}", file=sys.stderr)
        sys.exit(1)

    images = sorted(f for f in src_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
    if not images:
        print(f"Error: no images found in {src_dir}", file=sys.stderr)
        sys.exit(1)

    if args.in_place:
        out_dir = src_dir
    elif args.output_dir:
        out_dir = Path(args.output_dir).expanduser().resolve()
    else:
        out_dir = src_dir.parent / f"{src_dir.name}_rotated_{args.angle}"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(images)
    lossless_count = 0
    for i, src in enumerate(images, 1):
        dst = out_dir / src.name
        mtime = effective_mtime(src)

        used_lossless = False
        if src.suffix.lower() in JPEG_EXTS:
            used_lossless = rotate_jpeg_lossless(src, dst, args.angle)
        if not used_lossless:
            rotate_pil(src, dst, args.angle, args.quality)
        else:
            lossless_count += 1

        os.utime(dst, (mtime, mtime))
        if i % 50 == 0 or i == total:
            print(f"{i}/{total} done")

    print(f"Done! {total} images rotated {args.angle}° "
          f"({lossless_count} lossless via jpegtran) → {out_dir}")


if __name__ == "__main__":
    main()
