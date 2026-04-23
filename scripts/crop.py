#!/usr/bin/env python3
"""
crop.py — motor de crop para videos y GIFs.

Recorta desde los 4 bordes en px o %. Preserva mtime. Nunca sobreescribe el original.

Uso:
    crop.py input.mp4 --left 10%
    crop.py input.gif --left 40 --right 40 --top 20 --bottom 20
    crop.py input.mov --left 10% --right 10% -o out.mp4
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
GIF_EXTS = {".gif"}


def _side_expr(val: str, dim: str) -> str:
    """Convierte '10', '10%', '0', '' a expresión ffmpeg usando dim ('iw' o 'ih')."""
    val = (val or "").strip()
    if not val or val == "0":
        return "0"
    if val.endswith("%"):
        pct = float(val[:-1]) / 100
        if pct < 0 or pct >= 1:
            raise ValueError(f"Porcentaje fuera de rango: {val}")
        return f"{dim}*{pct}"
    int(val)  # valida que sea entero
    return val


def build_crop_filter(left: str = "0", right: str = "0",
                      top: str = "0", bottom: str = "0") -> str:
    """Devuelve el filtro ffmpeg `crop=W:H:X:Y` para recortar desde los 4 bordes."""
    l = _side_expr(left, "iw")
    r = _side_expr(right, "iw")
    t = _side_expr(top, "ih")
    b = _side_expr(bottom, "ih")
    w = "iw" if l == "0" and r == "0" else f"iw-({l})-({r})"
    h = "ih" if t == "0" and b == "0" else f"ih-({t})-({b})"
    return f"crop={w}:{h}:{l}:{t}"


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"FAILED: {' '.join(cmd)}\n{r.stderr}\n")
        sys.exit(r.returncode)


def probe_dims(path: Path) -> tuple[int, int] | None:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True,
    )
    try:
        w, h = (r.stdout or "").strip().split("x")
        return int(w), int(h)
    except ValueError:
        return None


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem}_{n}{p.suffix}")
        if not cand.exists():
            return cand
        n += 1


def main() -> None:
    p = argparse.ArgumentParser(description="Crop for videos and GIFs (reusable motor).")
    p.add_argument("input", type=Path, help="Input video or GIF")
    p.add_argument("-o", "--output", type=Path, help="Output file (default: <stem>_cropped.<ext>)")
    p.add_argument("--left", default="0", help="Left crop in px or %% (default: 0)")
    p.add_argument("--right", default="0", help="Right crop in px or %% (default: 0)")
    p.add_argument("--top", default="0", help="Top crop in px or %% (default: 0)")
    p.add_argument("--bottom", default="0", help="Bottom crop in px or %% (default: 0)")
    p.add_argument("--crf", type=int, default=18, help="CRF for x264 (default: 18, lower = better)")
    args = p.parse_args()

    src = args.input.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: file does not exist: {src}")

    if not shutil.which("ffmpeg"):
        sys.exit("Error: 'ffmpeg' not found in PATH")

    ext = src.suffix.lower()
    if ext in VIDEO_EXTS:
        kind = "video"
    elif ext in GIF_EXTS:
        kind = "gif"
    else:
        sys.exit(f"Error: unsupported extension ({ext}). Video: {sorted(VIDEO_EXTS)}  ·  GIF: {sorted(GIF_EXTS)}")

    if all(v in ("", "0") for v in (args.left, args.right, args.top, args.bottom)):
        sys.exit("Error: specify at least one of --left/--right/--top/--bottom")

    try:
        vf = build_crop_filter(args.left, args.right, args.top, args.bottom)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    user_output = args.output is not None
    if user_output:
        out = args.output.expanduser().resolve()
    else:
        # Path tentativo — se renombra al final con las dims reales
        out = src.with_name(f"{src.stem}_cropped{src.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out == src:
        sys.exit("Error: output cannot overwrite the input")

    src_mtime = os.stat(src).st_mtime

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf]
    if kind == "video":
        cmd += ["-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium",
                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart"]
    else:  # gif
        cmd += ["-gifflags", "+transdiff"]
    cmd += [str(out)]

    print(f"[crop] {src.name}  ·  filter: {vf}")
    run(cmd)

    # Renombrar con dims finales (solo si el user no pasó -o)
    if not user_output:
        dims = probe_dims(out)
        if dims:
            w, h = dims
            final = unique_path(src.with_name(f"{src.stem}_cropped_{w}x{h}{src.suffix}"))
            out.rename(final)
            out = final

    os.utime(out, (src_mtime, src_mtime))
    size_kb = out.stat().st_size / 1024
    print(f"\n✓ {out}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
