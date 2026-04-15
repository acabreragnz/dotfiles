#!/usr/bin/env python3
"""
video_capture.py — Captura frames de un video basado en detección de cambios.

Estrategia para video con movimiento continuo (persona en movimiento):
  - Pixel diff: compara % de píxeles que cambiaron entre frames
    → detecta movimiento local aunque el fondo sea estático
  - Análisis en resolución reducida (--scale) para mayor velocidad
  - Guardado en resolución original sin pérdida de calidad
  - Cooldown configurable para evitar ráfagas de frames similares
  - Procesamiento en streaming: bajo consumo de memoria

Uso:
  python3 video_capture.py <video> [opciones]

Ejemplos:
  python3 video_capture.py video.mp4
  python3 video_capture.py video.mp4 --threshold 0.02 --cooldown 0.5
  python3 video_capture.py video.mp4 --fps 4 --scale 0.3
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image
from tqdm import tqdm


def get_video_info(video_path: str) -> tuple[float, int, float]:
    """Devuelve (duración_seg, rotación_grados, fps_real) del video."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    duration = float(stream.get("duration", 0))

    # FPS real (r_frame_rate es "num/den", e.g. "30000/1001")
    num, den = stream.get("r_frame_rate", "25/1").split("/")
    real_fps = round(int(num) / int(den), 3)

    # Rotation en tags (formato viejo) o side_data_list (formato nuevo)
    rotation = 0
    tags = stream.get("tags", {})
    if "rotate" in tags:
        rotation = int(tags["rotate"])
    for sd in stream.get("side_data_list", []):
        if "rotation" in sd:
            rotation = -int(sd["rotation"])  # side_data usa signo opuesto

    return duration, rotation, real_fps


def _build_vf(fps: float, rotation: int) -> str:
    """Construye el filtro -vf con fps + corrección de rotación si es necesario."""
    parts = [f"fps={fps}"]
    r = rotation % 360
    if r == 90:
        parts.append("transpose=1")
    elif r == 180:
        parts.append("hflip,vflip")
    elif r == 270:
        parts.append("transpose=2")
    return ",".join(parts)


def stream_frames(video_path: str, fps: float, rotation: int = 0):
    """Generator que produce (timestamp, frame_rgb) en streaming desde FFmpeg."""
    cmd = [
        "ffmpeg", "-noautorotate", "-i", video_path,
        "-vf", _build_vf(fps, rotation),
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    PNG_HEADER = b"\x89PNG\r\n\x1a\n"
    PNG_END    = b"IEND\xaeB`\x82"
    CHUNK      = 65536
    buf        = b""
    frame_idx  = 0

    while True:
        chunk = proc.stdout.read(CHUNK)
        if not chunk:
            break
        buf += chunk

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
            yield frame_idx / fps, np.array(img)
            frame_idx += 1

    proc.wait()


def pixel_change_ratio(a: np.ndarray, b: np.ndarray, noise_floor: int = 15) -> float:
    """
    % de píxeles (0–1) que cambiaron más que el ruido de cámara.
    Detecta movimiento local aunque el fondo sea estático.
    noise_floor: diferencia mínima por canal para no contar como ruido.
    """
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    changed = np.any(diff > noise_floor, axis=2)
    return float(changed.mean())


def detect_and_save(
    video_path: str,
    output_dir: str,
    fps: float,
    threshold: float,
    cooldown: float,
    scale: float,
    noise_floor: int,
    capture_all: bool = False,
    dedupe: bool = False,
    by_minute: bool = True,
    force_rotate: int | None = None,
) -> int:
    duration, rotation, real_fps = get_video_info(video_path)
    if force_rotate is not None:
        rotation = force_rotate
    if (capture_all or dedupe) and fps == 4.0:
        fps = real_fps  # usar FPS real del video en modos agresivos
    total_frames = int(duration * fps)
    stem = Path(video_path).stem

    print(f"Video: {Path(video_path).name} | Duración: {duration:.1f}s | FPS real: {real_fps} | FPS análisis: {fps}")
    if capture_all:
        print(f"Modo: todas las capturas ({total_frames} frames esperados)")
    elif dedupe:
        print(f"Modo: todos los frames con cambio (sin cooldown, solo filtra estáticos)")
    else:
        print(f"Threshold: {threshold:.0%} píxeles | Cooldown: {cooldown}s | Escala análisis: {scale:.0%}")
    if rotation:
        print(f"Rotación detectada: {rotation}° → corrigiendo automáticamente")
    print()

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    prev_small = None   # frame anterior (para detectar movimiento)
    last_ts    = -cooldown
    captured   = 0

    with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
        for ts, frame in stream_frames(video_path, fps, rotation):
            pbar.update(1)

            if capture_all:
                _save_frame(frame, output_dir, stem, captured + 1, ts, by_minute)
                captured += 1
                continue

            if dedupe:
                # Guardar todo excepto frames idénticos al anterior (solo ruido)
                h, w = frame.shape[:2]
                small_w, small_h = max(1, int(w * scale)), max(1, int(h * scale))
                small = np.array(Image.fromarray(frame).resize((small_w, small_h), Image.BILINEAR))
                if prev_small is None or pixel_change_ratio(small, prev_small, noise_floor) > 0:
                    _save_frame(frame, output_dir, stem, captured + 1, ts, by_minute)
                    captured += 1
                prev_small = small
                continue

            # Downscale solo para análisis (más rápido)
            h, w = frame.shape[:2]
            small_w, small_h = max(1, int(w * scale)), max(1, int(h * scale))
            small = np.array(Image.fromarray(frame).resize((small_w, small_h), Image.BILINEAR))

            if prev_small is None:
                # Primer frame: siempre capturar
                _save_frame(frame, output_dir, stem, captured + 1, ts, by_minute)
                captured += 1
                prev_small = small
                last_ts = ts
                continue

            # Comparar contra el frame ANTERIOR (no el último guardado)
            # → detecta cada instante de movimiento, no solo cambios acumulados
            ratio = pixel_change_ratio(small, prev_small, noise_floor)
            prev_small = small  # siempre avanzar la ventana

            if ratio >= threshold and (ts - last_ts) >= cooldown:
                _save_frame(frame, output_dir, stem, captured + 1, ts, by_minute)
                captured += 1
                last_ts = ts

    return captured


def _save_frame(frame: np.ndarray, output_dir: str, stem: str, idx: int, ts: float, by_minute: bool = False) -> None:
    minutes = int(ts // 60)
    seconds = ts % 60
    filename = f"{stem}_{idx:04d}_{minutes:02d}m{seconds:05.2f}s.jpg"
    dest = Path(output_dir) / f"{minutes:02d}m" / filename if by_minute else Path(output_dir) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(dest, quality=92)


def main():
    parser = argparse.ArgumentParser(
        description="Captura frames con detección de movimiento para video continuo"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Directorio de salida (default: <video>_capturas/ junto al video)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.03,
        help="porcentaje de píxeles que deben cambiar para capturar, 0–1 (default: 0.03 = 3 pct)"
    )
    parser.add_argument(
        "--cooldown", "-c",
        type=float,
        default=0.5,
        help="Segundos mínimos entre capturas (default: 0.5)"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=4.0,
        help="FPS de análisis (default: 4). Más alto = más detalle temporal, más lento."
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.25,
        help="Escala para análisis, 0–1 (default: 0.25). No afecta calidad del output."
    )
    parser.add_argument(
        "--noise",
        type=int,
        default=15,
        help="Diferencia mínima por canal para no contar como ruido (default: 15)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Capturar todos los frames sin detección de cambios"
    )
    parser.add_argument(
        "--no-group",
        action="store_true",
        help="No agrupar por minuto, guardar todo en un directorio plano"
    )
    parser.add_argument(
        "--dedupe", "-d",
        action="store_true",
        help="Guardar todos los frames excepto los idénticos al anterior (sin cooldown)"
    )
    parser.add_argument(
        "--rotate",
        type=int,
        choices=[0, 90, 180, 270],
        default=None,
        help="Forzar rotación en grados (sobreescribe la metadata del video)"
    )

    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: no se encontró '{args.video}'", file=sys.stderr)
        sys.exit(1)

    video_path = Path(args.video).resolve()
    output_dir = args.output or str(video_path.parent / f"{video_path.stem}_capturas")

    captured = detect_and_save(
        video_path=str(video_path),
        output_dir=output_dir,
        fps=args.fps,
        threshold=args.threshold,
        cooldown=args.cooldown,
        scale=args.scale,
        noise_floor=args.noise,
        capture_all=args.all,
        dedupe=args.dedupe,
        by_minute=not args.no_group,
        force_rotate=args.rotate,
    )

    if captured:
        print(f"\nGuardados {captured} frames en: {output_dir}/")
    else:
        print("\nNo se detectaron cambios. Probá reduciendo --threshold.")


if __name__ == "__main__":
    main()
