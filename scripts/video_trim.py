#!/usr/bin/env python3
"""
video_trim.py — corta un tramo de video sin pérdida (stream copy) o con re-encode preciso.

Por defecto usa `-c copy` (lossless, pero para H.264/HEVC/VP9 el inicio se ajusta
al keyframe más cercano antes del --start). Con --precise re-encodea para corte
exacto al frame, eligiendo códec y calidad según el original (similar a rotate-video).

Preserva el mtime del archivo original en el archivo resultante.

Uso:
    video_trim.py input.mp4 --start 1:39 --to 6:30
    video_trim.py input.avi --start 5 --duration 30 -o output.avi
    video_trim.py input.mp4 --start 00:00:10 --to 00:00:45 --precise
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filename_date import effective_mtime


def parse_time(s: str) -> float:
    """HH:MM:SS, MM:SS, SS (con decimales opcionales) → segundos."""
    s = s.strip()
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        raise ValueError(f"invalid format: {s}")
    return float(s)


def format_time_compact(seconds: float) -> str:
    """Segundos → `10s`, `1m39`, `1h02m03` (compacto, apto para filename)."""
    t = int(round(seconds))
    h, rem = divmod(t, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}h{m:02d}m{sec:02d}"
    if m > 0:
        return f"{m}m{sec:02d}"
    return f"{sec}s"


def probe_codec(src: Path) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=nw=1:nk=1", str(src)],
        capture_output=True, text=True,
    )
    return (r.stdout or "").strip().lower()


def probe_duration(src: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(src)],
        capture_output=True, text=True,
    )
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def encode_flags(codec: str) -> tuple[list[str], list[str]]:
    """Devuelve (vcodec_args, pix_fmt_args) para un codec de video dado."""
    match codec:
        case "mjpeg":
            return (["-c:v", "mjpeg", "-q:v", "2"], [])
        case "hevc" | "h265":
            return (["-c:v", "libx265", "-crf", "15"], ["-pix_fmt", "yuv420p"])
        case "vp9":
            return (["-c:v", "libvpx-vp9", "-crf", "18", "-b:v", "0"], ["-pix_fmt", "yuv420p"])
        case _:
            return (["-c:v", "libx264", "-crf", "15", "-preset", "slow"], ["-pix_fmt", "yuv420p"])


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"FAILED: {' '.join(cmd)}\n{r.stderr}\n")
        sys.exit(r.returncode)


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem}_{n}{p.suffix}")
        if not cand.exists():
            return cand
        n += 1


def default_output_name(src: Path, start_s: float, end_s: float | None) -> Path:
    """Nombre de salida `<stem>_cut_<start>-<end><ext>` (o `_cut_<start>` si no hay fin)."""
    start_lbl = format_time_compact(start_s)
    if end_s is not None:
        range_lbl = f"{start_lbl}-{format_time_compact(end_s)}"
    else:
        range_lbl = start_lbl
    return src.with_name(f"{src.stem}_cut_{range_lbl}{src.suffix}")


def main() -> None:
    p = argparse.ArgumentParser(description="Trim a video range (stream copy by default).")
    p.add_argument("input", type=Path, help="Input video")
    p.add_argument("-o", "--output", type=Path,
                   help="Output video (default: <stem>_cut_<start>-<end>.<ext> next to source)")
    p.add_argument("--start", default="0",
                   help="Start time (seconds or HH:MM:SS). Default: 0")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--to", help="End time (seconds or HH:MM:SS)")
    g.add_argument("--duration", help="Range duration (seconds or HH:MM:SS)")
    p.add_argument("--precise", action="store_true",
                   help="Re-encode for frame-accurate cut (not lossless)")
    args = p.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("Error: 'ffmpeg' not found in PATH")

    src = args.input.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: file does not exist: {src}")

    try:
        start_s = parse_time(args.start)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    end_s: float | None = None
    if args.to:
        try:
            end_s = parse_time(args.to)
        except ValueError as e:
            sys.exit(f"Error: {e}")
    elif args.duration:
        try:
            end_s = start_s + parse_time(args.duration)
        except ValueError as e:
            sys.exit(f"Error: {e}")

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        out = unique_path(default_output_name(src, start_s, end_s))
    out.parent.mkdir(parents=True, exist_ok=True)

    mtime = effective_mtime(src)

    ff = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-y"]

    if args.precise:
        ff += ["-i", str(src), "-ss", str(args.start)]
        if args.to:
            ff += ["-to", str(args.to)]
        elif args.duration:
            ff += ["-t", str(args.duration)]
        vcodec, pix_fmt = encode_flags(probe_codec(src))
        ff += vcodec + pix_fmt + ["-c:a", "copy", "-map_metadata", "0"]
    else:
        ff += ["-ss", str(args.start)]
        if args.to:
            ff += ["-to", str(args.to)]
        ff += ["-i", str(src)]
        if args.duration:
            ff += ["-t", str(args.duration)]
        ff += ["-c", "copy", "-avoid_negative_ts", "make_zero", "-map_metadata", "0"]

    ff += [str(out)]

    print(f"[1/1] Trimming → {out.name}  ({'precise' if args.precise else 'lossless'})")
    run(ff)

    os.utime(out, (mtime, mtime))
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"\n✓ {out}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
