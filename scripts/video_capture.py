#!/usr/bin/env python3
"""
video_capture.py — Captura frames de un video basado en detección de cambios.

Estrategia para video con movimiento continuo:
  - Compara histogramas de frames consecutivos (robusto al ruido y movimiento menor)
  - Cooldown configurable para evitar ráfagas de frames similares
  - Guarda el frame más representativo de cada "escena"

Uso:
  python3 video_capture.py <video> [opciones]

Ejemplos:
  python3 video_capture.py video.mp4
  python3 video_capture.py video.mp4 --output capturas/ --threshold 0.4 --cooldown 2.0
  python3 video_capture.py video.mp4 --fps 5 --threshold 0.3
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image
from tqdm import tqdm


def extract_frames_ffmpeg(video_path: str, fps: float) -> list[tuple[float, np.ndarray]]:
    """Extrae frames del video usando FFmpeg, devuelve lista de (timestamp_seg, array_rgb)."""
    # Obtener duración del video
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True
    )
    import json
    info = json.loads(probe.stdout)
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    duration = float(video_stream.get("duration", 0))

    total_frames = int(duration * fps)
    print(f"Video: {Path(video_path).name} | Duración: {duration:.1f}s | FPS de análisis: {fps}")

    # Extraer frames via pipe (más eficiente que escribir archivos temporales)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps}",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frames = []
    frame_idx = 0
    buf = b""

    PNG_HEADER = b"\x89PNG\r\n\x1a\n"
    PNG_END = b"IEND\xaeB`\x82"
    CHUNK = 65536  # 64 KB

    # Parsear PNGs en streaming — la barra avanza a medida que FFmpeg produce frames
    with tqdm(total=total_frames, desc="Extrayendo", unit="frame") as pbar:
        while True:
            chunk = proc.stdout.read(CHUNK)
            if not chunk:
                break
            buf += chunk

            # Extraer todos los PNGs completos que haya en el buffer
            while True:
                start = buf.find(PNG_HEADER)
                if start == -1:
                    break
                end = buf.find(PNG_END, start)
                if end == -1:
                    break
                end += len(PNG_END)
                png_data = buf[start:end]
                buf = buf[end:]
                img = Image.open(BytesIO(png_data)).convert("RGB")
                timestamp = frame_idx / fps
                frames.append((timestamp, np.array(img)))
                frame_idx += 1
                pbar.update(1)

    proc.wait()
    return frames


def compute_histogram(frame: np.ndarray, bins: int = 64) -> np.ndarray:
    """Histograma normalizado HSV — robusto a cambios de iluminación."""
    img = Image.fromarray(frame).convert("HSV")
    hsv = np.array(img)
    hist = np.concatenate([
        np.histogram(hsv[:, :, c], bins=bins, range=(0, 255))[0]
        for c in range(3)
    ])
    return hist.astype(float) / hist.sum()


def histogram_distance(h1: np.ndarray, h2: np.ndarray) -> float:
    """Distancia chi-cuadrado entre histogramas (0 = idénticos, mayor = más diferentes)."""
    denom = h1 + h2
    mask = denom > 0
    return float(np.sum(((h1[mask] - h2[mask]) ** 2) / denom[mask]))


def detect_changes(
    frames: list[tuple[float, np.ndarray]],
    threshold: float,
    cooldown: float,
) -> list[tuple[float, np.ndarray]]:
    """
    Detecta frames con cambio significativo respecto al último capturado.

    threshold: distancia mínima chi-cuadrado para considerar cambio (0.1–1.0)
    cooldown: segundos mínimos entre capturas
    """
    if not frames:
        return []

    captured = []
    last_hist = compute_histogram(frames[0][1])
    last_ts = -cooldown  # permite capturar el primer frame

    for ts, frame in tqdm(frames, desc="Analizando", unit="frame"):
        hist = compute_histogram(frame)
        dist = histogram_distance(hist, last_hist)

        if dist >= threshold and (ts - last_ts) >= cooldown:
            captured.append((ts, frame))
            last_hist = hist
            last_ts = ts

    return captured


def save_frames(
    captures: list[tuple[float, np.ndarray]],
    output_dir: str,
    video_name: str,
) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stem = Path(video_name).stem

    for i, (ts, frame) in enumerate(tqdm(captures, desc="Guardando", unit="frame"), 1):
        minutes = int(ts // 60)
        seconds = ts % 60
        filename = f"{stem}_{i:04d}_{minutes:02d}m{seconds:05.2f}s.jpg"
        path = Path(output_dir) / filename
        Image.fromarray(frame).save(path, quality=92)

    print(f"Guardados {len(captures)} frames en: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Captura frames con detección de cambios para video con movimiento continuo"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Directorio de salida (default: <video>_capturas/)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.35,
        help="Sensibilidad de detección 0.1–1.0 (default: 0.35). Menor = más capturas."
    )
    parser.add_argument(
        "--cooldown", "-c",
        type=float,
        default=1.5,
        help="Segundos mínimos entre capturas (default: 1.5)"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="FPS de análisis — cuántos frames/seg evaluar (default: 2). Más alto = más precisión, más lento."
    )

    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: no se encontró el archivo '{args.video}'", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output or f"{Path(args.video).stem}_capturas"

    print(f"Threshold: {args.threshold} | Cooldown: {args.cooldown}s | FPS análisis: {args.fps}")
    print()

    frames = extract_frames_ffmpeg(args.video, args.fps)
    captures = detect_changes(frames, args.threshold, args.cooldown)

    print(f"Cambios detectados: {len(captures)}")

    if captures:
        save_frames(captures, output_dir, args.video)
    else:
        print("No se detectaron cambios. Probá reduciendo --threshold.")


if __name__ == "__main__":
    main()
