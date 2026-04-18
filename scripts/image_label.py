#!/usr/bin/env python3
"""
image_label.py — Quema la fecha (del mtime) en imágenes.

Uso:
  python3 image_label.py <imagen> [<imagen2> ...]  [--output-dir <dir>]

Genera <nombre>_labeled.jpg junto al original (o en --output-dir).
El mtime original se restaura en el archivo de salida.
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from video_capture import _draw_date

from datetime import datetime

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def main():
    parser = argparse.ArgumentParser(description="Quema la fecha del mtime en imágenes")
    parser.add_argument("images", nargs="+", help="Imágenes a procesar")
    parser.add_argument("--output-dir", "-o", default=None, help="Directorio de salida (default: junto al original)")
    parser.add_argument("--quality", type=int, default=92, help="Calidad JPEG (default: 92)")
    parser.add_argument("--position", choices=["right", "left", "both"], default="right",
                        help="Posición del timestamp (default: right)")
    args = parser.parse_args()

    for path_str in args.images:
        src = Path(path_str).resolve()
        if not src.exists():
            print(f"SKIP: no existe '{src}'", file=sys.stderr)
            continue
        if src.suffix.lower() not in IMAGE_EXTS:
            print(f"SKIP: no es imagen '{src.name}'", file=sys.stderr)
            continue

        mtime = src.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")

        out_dir = Path(args.output_dir).resolve() if args.output_dir else src.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f"{src.stem}_labeled.jpg"

        img = _draw_date(Image.open(src).convert("RGB"), date_str, args.position)
        img.save(dst, quality=args.quality)
        os.utime(dst, (mtime, mtime))
        print(f"  → {dst.name}")

    print("Listo.")


if __name__ == "__main__":
    main()
