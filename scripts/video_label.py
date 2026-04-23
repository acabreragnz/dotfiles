#!/usr/bin/env python3
"""
video_label.py — Quema la fecha (del mtime) en un video.

Uso:
  python3 video_label.py <video> [--output <salida>]

El archivo de salida es <nombre>_labeled.mp4 por defecto.
El audio original se preserva y el mtime se restaura.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image
from tqdm import tqdm

import json

sys.path.insert(0, str(Path(__file__).parent))
from video_capture import _draw_date, get_video_info, stream_frames
from filename_date import effective_mtime


def get_video_codec_info(video_path: str) -> tuple[str, int]:
    """Devuelve (codec_name, bit_rate) del stream de video."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    codec = stream.get("codec_name", "h264")
    # bit_rate puede estar en el stream o en format
    bit_rate = int(stream.get("bit_rate", 0))
    if not bit_rate:
        probe2 = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True
        )
        fmt = json.loads(probe2.stdout).get("format", {})
        bit_rate = int(fmt.get("bit_rate", 8_000_000))
    return codec, bit_rate


def _run_gif_pipeline(src: Path, dst: Path, fps: float, rotation: int,
                      date_str: str, total_frames: int, position: str,
                      src_mtime: float) -> None:
    """Pipeline para GIF: frames → PNG con timestamp → gifski."""
    print(f"GIF   : {src.name}")
    print(f"Date  : {date_str} | FPS: {fps} | Duration ~ {total_frames} frame(s)")
    print(f"Output: {dst.name}")
    print()

    with tempfile.TemporaryDirectory(prefix="video_label_gif_") as tmp:
        tmp_path = Path(tmp)
        gen = stream_frames(str(src), fps, rotation, max_width=0)
        count = 0
        with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
            for _, frame in gen:
                img = _draw_date(Image.fromarray(frame), date_str, position)
                count += 1
                img.save(tmp_path / f"frame_{count:05d}.png")
                pbar.update(1)

        frames = sorted(tmp_path.glob("frame_*.png"))
        if not frames:
            print("Error: no frames generated", file=sys.stderr)
            sys.exit(1)

        gs = ["gifski", "-o", str(dst), "--fps", str(int(round(fps))),
              "--quality", "90", *[str(f) for f in frames]]
        r = subprocess.run(gs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            print(f"gifski error:\n{r.stderr}", file=sys.stderr)
            sys.exit(r.returncode)

    os.utime(dst, (src_mtime, src_mtime))
    print(f"\nSaved: {dst}")


def main():
    parser = argparse.ArgumentParser(description="Burn the mtime date into a video")
    parser.add_argument("video", help="Path to the video")
    parser.add_argument("--output", "-o", default=None, help="Output file (default: <name>_labeled.mp4)")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None,
                        help="Force rotation in degrees (useful for videos recorded upside down without metadata)")
    parser.add_argument("--position", default="right",
                        help="Position(s) of the timestamp: right, left, center, both, or a comma-separated combination (e.g. left,center,right). Default: right")
    args = parser.parse_args()

    src = Path(args.video).resolve()
    if not src.exists():
        print(f"Error: not found '{src}'", file=sys.stderr)
        sys.exit(1)

    is_gif = src.suffix.lower() == ".gif"
    default_ext = ".gif" if is_gif else ".mp4"
    dst = Path(args.output).resolve() if args.output else src.parent / f"{src.stem}_labeled{default_ext}"

    if is_gif and not shutil.which("gifski"):
        print("Error: 'gifski' not found in PATH (required for GIF)", file=sys.stderr)
        sys.exit(1)

    src_mtime = effective_mtime(src)
    date_str = datetime.fromtimestamp(src_mtime).strftime("%d/%m/%Y")
    duration, rotation, real_fps = get_video_info(str(src))
    codec, bit_rate = get_video_codec_info(str(src))
    fps = real_fps
    total_frames = int(duration * fps)

    if args.rotate is not None:
        rotation = args.rotate

    if is_gif:
        _run_gif_pipeline(src, dst, fps, rotation, date_str, total_frames, args.position, src_mtime)
        return

    encoder_map = {"h264": "libx264", "hevc": "libx265", "vp9": "libvpx-vp9", "mjpeg": "mjpeg"}
    encoder = encoder_map.get(codec, "libx264")

    print(f"Video : {src.name}")
    print(f"Date  : {date_str} | FPS: {fps} | Duration: {duration:.1f}s (~{total_frames} frames)")
    print(f"Codec : {codec} → {encoder} @ {bit_rate // 1000}kbps")
    if rotation:
        print(f"Rot.  : {rotation}° corrected")
    print(f"Output: {dst.name}")
    print()

    # Primer frame para obtener dimensiones reales post-rotación
    gen = stream_frames(str(src), fps, rotation, max_width=0)
    ts0, first = next(gen)
    h, w = first.shape[:2]

    encode_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-",
        "-i", str(src),
        "-map", "0:v",
        "-map", "1:a?",
        "-c:v", encoder,
        *(["-crf", "18", "-b:v", "0"] if encoder == "libvpx-vp9"
          else ["-q:v", "2"] if encoder == "mjpeg"
          else ["-crf", "15", "-preset", "slow"]),
        *([] if encoder == "mjpeg" else ["-pix_fmt", "yuv420p"]),
        "-c:a", "copy",
        # Los frames ya salen corregidos por stream_frames; limpiar metadata de
        # rotación para que el player no vuelva a rotar el output.
        "-metadata:s:v:0", "rotate=0",
        str(dst)
    ]
    ffmpeg_log = open("/tmp/video_label_ffmpeg.log", "w")
    enc_proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)

    def write_frame(frame):
        img = _draw_date(Image.fromarray(frame), date_str, args.position)
        enc_proc.stdin.write(np.array(img).tobytes())

    try:
        with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
            write_frame(first)
            pbar.update(1)
            for _, frame in gen:
                write_frame(frame)
                pbar.update(1)
        enc_proc.stdin.close()
    except BrokenPipeError:
        ffmpeg_log.flush()
        print(f"\nError: ffmpeg exited unexpectedly. See /tmp/video_label_ffmpeg.log", file=sys.stderr)
        sys.exit(1)
    finally:
        ffmpeg_log.close()

    ret = enc_proc.wait()
    if ret != 0:
        print(f"\nError: ffmpeg exited with code {ret}. See /tmp/video_label_ffmpeg.log", file=sys.stderr)
        sys.exit(1)

    os.utime(dst, (src_mtime, src_mtime))
    print(f"\nSaved: {dst}")


if __name__ == "__main__":
    main()
