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
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image
from tqdm import tqdm

import json

sys.path.insert(0, str(Path(__file__).parent))
from video_capture import _draw_date, get_video_info, stream_frames


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


def main():
    parser = argparse.ArgumentParser(description="Quema la fecha del mtime en un video")
    parser.add_argument("video", help="Ruta al video")
    parser.add_argument("--output", "-o", default=None, help="Archivo de salida (default: <nombre>_labeled.mp4)")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None,
                        help="Forzar rotación en grados (útil para videos grabados al revés sin metadata)")
    args = parser.parse_args()

    src = Path(args.video).resolve()
    if not src.exists():
        print(f"Error: no se encontró '{src}'", file=sys.stderr)
        sys.exit(1)

    dst = Path(args.output).resolve() if args.output else src.parent / f"{src.stem}_labeled.mp4"

    src_mtime = src.stat().st_mtime
    date_str = datetime.fromtimestamp(src_mtime).strftime("%d/%m/%Y")
    duration, rotation, real_fps = get_video_info(str(src))
    codec, bit_rate = get_video_codec_info(str(src))
    fps = real_fps
    total_frames = int(duration * fps)

    if args.rotate is not None:
        rotation = args.rotate

    # Mapear codec a encoder libav
    encoder_map = {"h264": "libx264", "hevc": "libx265", "vp9": "libvpx-vp9"}
    encoder = encoder_map.get(codec, "libx264")

    print(f"Video : {src.name}")
    print(f"Fecha : {date_str} | FPS: {fps} | Duración: {duration:.1f}s (~{total_frames} frames)")
    print(f"Codec : {codec} → {encoder} @ {bit_rate // 1000}kbps")
    if rotation:
        print(f"Rot.  : {rotation}° corregida")
    print(f"Salida: {dst.name}")
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
        "-c:v", encoder, "-b:v", str(bit_rate), "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        # Los frames ya salen corregidos por stream_frames; limpiar metadata de
        # rotación para que el player no vuelva a rotar el output.
        "-metadata:s:v:0", "rotate=0",
        str(dst)
    ]
    encoder = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def write_frame(frame):
        img = _draw_date(Image.fromarray(frame), date_str)
        encoder.stdin.write(np.array(img).tobytes())

    with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
        write_frame(first)
        pbar.update(1)
        for _, frame in gen:
            write_frame(frame)
            pbar.update(1)

    encoder.stdin.close()
    encoder.wait()

    os.utime(dst, (src_mtime, src_mtime))
    print(f"\nGuardado: {dst}")


if __name__ == "__main__":
    main()
