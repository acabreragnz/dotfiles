#!/usr/bin/env python3
"""
video_capture.py — Captura frames de un video con detección de cambios.

Modos:
  full   (default) — FPS real del video, guarda todo frame con cualquier diferencia
  medium           — 4 FPS, detecta movimiento significativo (umbral moderado)
  low              — 2 FPS, solo cambios grandes (menos capturas)

Uso:
  python3 video_capture.py <video> [full|medium|low] [opciones]

Ejemplos:
  python3 video_capture.py video.avi
  python3 video_capture.py video.avi medium --rotate 180
  python3 video_capture.py video.avi low --output /tmp/capturas
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

DEFACE_SITE = "/home/tcabrera/.local/share/pipx/venvs/deface/lib/python3.12/site-packages"


def _load_pixelizer():
    """Carga CenterFace y helpers de pixelize.py (lazy, solo si --pixelize)."""
    import cv2
    if DEFACE_SITE not in sys.path:
        sys.path.insert(0, DEFACE_SITE)
    from deface.centerface import CenterFace

    model = CenterFace()

    def detect(img_bgr):
        dets, _ = model(img_bgr, threshold=0.2)
        boxes = []
        for det in dets:
            rx1, ry1, rx2, ry2 = det[:4]
            cx, cy = (rx1 + rx2) / 2, (ry1 + ry2) / 2
            fw = (rx2 - rx1) * 1.3
            fh = (ry2 - ry1) * 1.3
            H, W = img_bgr.shape[:2]
            boxes.append((
                max(0, int(cx - fw / 2)), max(0, int(cy - fh / 2)),
                min(W, int(cx + fw / 2)), min(H, int(cy + fh / 2)),
            ))
        return boxes

    def mosaic(img_bgr, boxes, block_pct=20):
        out = img_bgr.copy()
        for x1, y1, x2, y2 in boxes:
            block = max(2, int((x2 - x1) * block_pct / 100))
            for y in range(y1, y2, block):
                for x in range(x1, x2, block):
                    bx2, by2 = min(x2, x + block), min(y2, y + block)
                    color = np.median(
                        img_bgr[y:by2, x:bx2].reshape(-1, 3), axis=0
                    ).astype(np.uint8)
                    out[y:by2, x:bx2] = color
        return out

    return cv2, detect, mosaic


MODES = {
    #          fps    threshold  cooldown  noise
    "full":   (None,  0.0,       0.0,      5),   # fps=None → usa FPS real del video
    "medium": (4.0,   0.03,      0.5,      15),
    "low":    (2.0,   0.08,      2.0,      20),
}


def get_video_info(video_path: str) -> tuple[float, int, float]:
    """Devuelve (duración_seg, rotación_grados, fps_real)."""
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")

    duration = float(stream.get("duration", 0))

    num, den = stream.get("r_frame_rate", "25/1").split("/")
    real_fps = round(int(num) / int(den), 3)

    rotation = 0
    tags = stream.get("tags", {})
    if "rotate" in tags:
        rotation = int(tags["rotate"])
    for sd in stream.get("side_data_list", []):
        if "rotation" in sd:
            rotation = -int(sd["rotation"])

    return duration, rotation, real_fps


def _build_vf(fps: float, rotation: int) -> str:
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
            img = Image.open(BytesIO(buf[start:end])).convert("RGB")
            buf = buf[end:]
            yield frame_idx / fps, np.array(img)
            frame_idx += 1

    proc.wait()


def pixel_change_ratio(a: np.ndarray, b: np.ndarray, noise_floor: int) -> float:
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return float(np.any(diff > noise_floor, axis=2).mean())


def process(
    video_path: str,
    output_dir: str,
    mode: str,
    by_minute: bool,
    force_rotate: int | None,
    pixelize: bool = False,
) -> int:
    fps_cfg, threshold, cooldown, noise = MODES[mode]
    duration, rotation, real_fps = get_video_info(video_path)

    if force_rotate is not None:
        rotation = force_rotate

    fps = fps_cfg or real_fps  # full usa FPS real
    total_frames = int(duration * fps)
    stem = Path(video_path).stem

    print(f"Video : {Path(video_path).name}")
    print(f"Modo  : {mode} | FPS análisis: {fps} | Duración: {duration:.1f}s (~{total_frames} frames)")
    if rotation:
        print(f"Rot.  : {rotation}° corregida automáticamente")
    if pixelize:
        print(f"Pixelize: activado — cargando modelo de detección de caras...")
        cv2, detect_faces, apply_mosaic = _load_pixelizer()
        print(f"Pixelize: listo")
    print()

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    prev_small = None
    last_ts    = -cooldown
    captured   = 0
    SCALE      = 0.25

    with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
        for ts, frame in stream_frames(video_path, fps, rotation):
            pbar.update(1)

            h, w   = frame.shape[:2]
            small  = np.array(Image.fromarray(frame).resize(
                (max(1, int(w * SCALE)), max(1, int(h * SCALE))), Image.BILINEAR
            ))

            if prev_small is None:
                should_save = True
            else:
                ratio      = pixel_change_ratio(small, prev_small, noise)
                prev_small = small
                should_save = ratio > threshold and (ts - last_ts) >= cooldown

            if prev_small is None:
                prev_small = small

            if should_save:
                if pixelize:
                    bgr   = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    boxes = detect_faces(bgr)
                    if boxes:
                        bgr   = apply_mosaic(bgr, boxes)
                    frame = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                _save(frame, output_dir, stem, captured + 1, ts, by_minute)
                captured += 1
                last_ts   = ts

    return captured


def _save(frame: np.ndarray, output_dir: str, stem: str, idx: int, ts: float, by_minute: bool) -> None:
    minutes  = int(ts // 60)
    seconds  = ts % 60
    filename = f"{stem}_{idx:04d}_{minutes:02d}m{seconds:05.2f}s.jpg"
    dest     = Path(output_dir) / (f"{minutes:02d}m" if by_minute else "") / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(dest, quality=92)


def main():
    parser = argparse.ArgumentParser(
        description="Captura frames de un video con detección de cambios"
    )
    parser.add_argument("video", help="Ruta al video")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["full", "medium", "low"],
        default="full",
        help="Modo de captura (default: full)"
    )
    parser.add_argument("--output", "-o", default=None, help="Directorio de salida")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None,
                        help="Forzar rotación en grados")
    parser.add_argument("--no-group", action="store_true",
                        help="No agrupar capturas por minuto")
    parser.add_argument("--pixelize", "-p", action="store_true",
                        help="Aplicar mosaico fuerte sobre caras detectadas en cada captura")

    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: no se encontró '{args.video}'", file=sys.stderr)
        sys.exit(1)

    video_path = Path(args.video).resolve()
    output_dir = args.output or str(video_path.parent / f"{video_path.stem}_capturas_{args.mode}")

    captured = process(
        video_path=str(video_path),
        output_dir=output_dir,
        mode=args.mode,
        by_minute=not args.no_group and args.mode == "full",
        force_rotate=args.rotate,
        pixelize=args.pixelize,
    )

    print(f"\nGuardados {captured} frames en: {output_dir}/")


if __name__ == "__main__":
    main()
