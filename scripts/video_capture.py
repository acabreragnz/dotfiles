#!/usr/bin/env python3
"""
video_capture.py — Captura frames de un video con detección de cambios.

Modos:
  full   (default) — FPS real del video, guarda todo frame con cualquier diferencia
  medium           — 4 FPS, detecta movimiento significativo (umbral moderado)
  low              — 2 FPS, solo cambios grandes (menos capturas)
  smart            — dos pasos: (1) scan a scan_fps con MOG2 (ignora cambios de luz),
                     detecta rangos de movimiento real; (2) extrae todos los frames
                     dentro de esos rangos al FPS real del video.

Uso:
  python3 video_capture.py <video> [full|medium|low|smart] [opciones]

Ejemplos:
  python3 video_capture.py video.avi
  python3 video_capture.py video.avi medium --rotate 180
  python3 video_capture.py video.avi low --output /tmp/capturas
  python3 video_capture.py video.avi smart --min-blob-pct 0.5 --gap 5 --pad 1
  python3 video_capture.py video.avi smart --quality 75 --max-width 1280
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Cap threads ANTES de importar numpy/cv2 para evitar que BLAS/OpenMP saturen
# todos los cores. Este proceso + ffmpeg (decoder + encoder) + ffprobe
# fácilmente se suben a 10+ cores sin control.
_THREAD_CAP = os.environ.get("VIDEO_SCRIPTS_THREADS", "4")
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_THREAD_LIMIT"):
    os.environ.setdefault(_v, _THREAD_CAP)

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filename_date import effective_mtime

_DATE_FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
def _draw_date(img: Image.Image, date_str: str, position: str = "right") -> Image.Image:
    _, h = img.size
    font_size = max(16, int(h * 0.025))
    font = ImageFont.truetype(_DATE_FONT_PATH, font_size)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    bbox = draw.textbbox((0, 0), date_str, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    y = h - th - int(h * 0.02)
    stroke = max(2, font_size // 12)
    margin = int(w * 0.04)
    if position == "both":
        sides = ["right", "left"]
    else:
        sides = [s for s in position.replace("|", ",").split(",") if s]
    for side in sides:
        if side == "right":
            x = w - tw - margin
        elif side == "left":
            x = margin
        elif side == "center":
            x = (w - tw) // 2
        else:
            continue
        draw.text((x, y), date_str, font=font, fill="white", stroke_width=stroke, stroke_fill="black")
    return img

DEFACE_SITE = "/home/tcabrera/.local/share/pipx/venvs/deface/lib/python3.12/site-packages"


def _load_pixelizer():
    """Carga CenterFace y helpers de pixelize.py (lazy, solo si --pixelize)."""
    if DEFACE_SITE not in sys.path:
        sys.path.insert(0, DEFACE_SITE)
    import cv2
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


def get_video_info(video_path: str) -> tuple[float, int, float, int, int]:
    """Devuelve (duración_seg, rotación_grados, fps_real, width, height).

    Prefiere avg_frame_rate sobre r_frame_rate para manejar VFR correctamente.
    """
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")

    duration = float(stream.get("duration", 0))

    def _parse_rate(s: str) -> float:
        try:
            num, den = s.split("/")
            d = int(den)
            return round(int(num) / d, 3) if d else 0.0
        except (ValueError, AttributeError):
            return 0.0

    real_fps = _parse_rate(stream.get("avg_frame_rate", "0/0"))
    if real_fps <= 0:
        real_fps = _parse_rate(stream.get("r_frame_rate", "25/1"))

    rotation = 0
    tags = stream.get("tags", {})
    if "rotate" in tags:
        rotation = int(tags["rotate"])
    for sd in stream.get("side_data_list", []):
        if "rotation" in sd:
            rotation = -int(sd["rotation"])

    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))

    return duration, rotation, real_fps, width, height


def compute_output_dims(in_w: int, in_h: int, rotation: int, max_width: int) -> tuple[int, int]:
    """Computa (W, H) de salida después de rotación + downscale."""
    r = rotation % 360
    w, h = (in_h, in_w) if r in (90, 270) else (in_w, in_h)
    if max_width > 0 and w > max_width:
        scale = max_width / w
        w = max_width
        h = max(2, int(round(h * scale / 2)) * 2)
    return w, h


def _build_vf(fps: float | None, rotation: int, max_width: int = 1920) -> str:
    parts: list[str] = []
    if fps is not None:
        parts.append(f"fps={fps}")
    r = rotation % 360
    if r == 90:
        parts.append("transpose=1")
    elif r == 180:
        parts.append("hflip,vflip")
    elif r == 270:
        parts.append("transpose=2")
    if max_width > 0:
        parts.append(f"scale=w='min({max_width},iw)':h=-2")
    return ",".join(parts) if parts else "null"


def stream_frames(video_path: str, fps: float | None, rotation: int = 0, max_width: int = 1920,
                  start: float = 0, end: float = 0, pix_fmt: str = "rgb24"):
    """Generator que produce (timestamp, frame) en streaming desde ffmpeg rawvideo.

    pix_fmt: "rgb24" (default) o "bgr24" (para alimentar OpenCV sin cvtColor).
    Seek híbrido: -ss rápido (input-seek) a ~2s antes del start + -ss preciso (output-seek)
    para exactitud frame-por-frame sin re-decodificar el video desde 0.
    """
    _, _, _, in_w, in_h = get_video_info(video_path)
    out_w, out_h = compute_output_dims(in_w, in_h, rotation, max_width)

    cmd = ["ffmpeg", "-noautorotate", "-threads", _THREAD_CAP]
    if start > 2.0:
        # hybrid: fast input-seek cerca del start, luego output-seek los últimos 2s
        fast = start - 2.0
        cmd += ["-ss", f"{fast:.3f}", "-i", video_path, "-ss", "2.0"]
        if end > 0:
            cmd += ["-t", f"{end - start:.3f}"]
    else:
        cmd += ["-i", video_path]
        if start > 0:
            cmd += ["-ss", f"{start:.3f}"]
        if end > 0:
            cmd += ["-to", f"{end:.3f}"]

    cmd += [
        "-vf", _build_vf(fps, rotation, max_width),
        "-f", "rawvideo",
        "-pix_fmt", pix_fmt,
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_bytes = out_w * out_h * 3
    frame_idx = 0
    step = 1.0 / fps if fps else 0.0
    while True:
        # read(N) en pipes puede devolver menos que N; loop hasta completar un frame
        chunks: list[bytes] = []
        remaining = frame_bytes
        while remaining > 0:
            chunk = proc.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining > 0:
            break  # EOF
        data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
        frame = np.frombuffer(data, np.uint8).reshape(out_h, out_w, 3)
        yield start + frame_idx * step, frame
        frame_idx += 1

    proc.wait()


def pixel_change_ratio(a: np.ndarray, b: np.ndarray, noise_floor: int) -> float:
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return float(np.any(diff > noise_floor, axis=2).mean())


def _ensure_cv2():
    if DEFACE_SITE not in sys.path:
        sys.path.insert(0, DEFACE_SITE)
    import cv2
    try:
        cv2.setNumThreads(int(_THREAD_CAP))
    except Exception:
        pass
    return cv2


def motion_scan(
    video_path: str,
    scan_fps: float,
    rotation: int,
    scan_width: int,
    min_blob_pct: float,
    uniform_pct: float = 70.0,
    min_solidity: float = 0.3,
    max_fragments: int = 30,
    min_active_pct: float = 0.05,
    strong_blob_pct: float = 2.0,
    warmup_frames: int = 4,
    history: int = 500,
    var_threshold: float = 30.0,
    open_kernel: int = 3,
) -> list[float]:
    """Scan MOG2 con filtros anti-iluminación y anti-ruido de compresión.

    Decodifica el video a baja resolución (scan_width) y bgr24 directo para
    alimentar OpenCV sin conversiones. Deja pasar movimientos chicos (una mano,
    un pie entrando) pero descarta cambios de luz y artefactos de codec.

    Filtros:
      1. Opening morfológico 3×3 → elimina speckle de ruido
      2. Dilate 1× → reconecta blobs finos (brazos/piernas partidos por opening)
      3. fg% > uniform_pct → cambio global de luz, descartar
      4. fragments > max_fragments con blob chico → ruido de compresión, descartar
      5. blob mayor >= min_blob_pct → candidato
      6. Solidity del blob mayor >= min_solidity → rechaza streaks elongados
      7. Active-motion: frame-a-frame diff >= min_active_pct → descarta
         "MOG2 ve foreground pero nada se mueve" (ángulo de cámara cambió, o
         persona inmóvil en posición nueva). Sin esto, MOG2 tarda 125s en
         absorber el fondo nuevo.
    """
    cv2 = _ensure_cv2()
    mog = cv2.createBackgroundSubtractorMOG2(
        history=history, varThreshold=var_threshold, detectShadows=False
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel, open_kernel))

    duration, _, _, _, _ = get_video_info(video_path)
    total = int(duration * scan_fps)
    detected: list[float] = []
    frame_idx = 0
    prev_gray: np.ndarray | None = None

    with tqdm(total=total, desc="Pass 1 (scan MOG2)", unit="frame") as pbar:
        for ts, bgr in stream_frames(video_path, scan_fps, rotation, scan_width, pix_fmt="bgr24"):
            pbar.update(1)
            frame_idx += 1
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            # Pre-entrenar MOG2 con learningRate=1 durante los primeros frames
            # para converger el modelo de fondo sin evaluar todavía.
            if frame_idx <= warmup_frames:
                mog.apply(bgr, learningRate=1.0)
                prev_gray = gray
                continue
            fg = mog.apply(bgr)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
            fg = cv2.dilate(fg, kernel, iterations=1)

            total_pix = fg.shape[0] * fg.shape[1]
            fg_pix = cv2.countNonZero(fg)
            fg_pct = fg_pix / total_pix * 100

            if fg_pct >= uniform_pct:
                prev_gray = gray
                continue  # cambio global de luz

            contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                prev_gray = gray
                continue

            # Blob más grande
            big = max(contours, key=cv2.contourArea)
            max_area = cv2.contourArea(big)
            max_pct = max_area / total_pix * 100

            if max_pct < min_blob_pct:
                prev_gray = gray
                continue

            # Rechazar flicker: muchos fragmentos y blob mayor apenas pasa
            if len(contours) > max_fragments and max_pct < 2 * min_blob_pct:
                prev_gray = gray
                continue

            # Solidity: área / área del convex hull. Blobs reales (mano, pie,
            # perro) son compactos (solidity >= 0.5). Streaks de ruido o
            # artefactos de codec son elongados/dispersos (solidity < 0.3).
            hull_area = cv2.contourArea(cv2.convexHull(big))
            solidity = max_area / max(hull_area, 1.0)
            if solidity < min_solidity:
                prev_gray = gray
                continue

            # Strong-blob bypass: si el blob es grande (≥ strong_blob_pct),
            # es presencia clara de un objeto — keep aunque frame-a-frame no
            # haya cambio (persona quieta pero visible). Evita que una persona
            # agachándose lentamente se descarte por falta de active-motion.
            if max_pct >= strong_blob_pct:
                detected.append(ts)
                prev_gray = gray
                continue

            # Active-motion gate: el cambio frame-a-frame tiene que estar DENTRO
            # del blob de MOG2. Filtra:
            #   a) MOG2 ve "new content" (cámara movida, persona quieta en pose
            #      nueva) pero nada cambia entre frames → diff ≈ 0.
            #   b) Vibraciones del celular → edges del fondo cambian por todo
            #      el frame pero MOG2 solo tiene blob chico/concentrado → la
            #      intersección es pequeña.
            #   c) Movimiento real dentro del blob detectado → intersección
            #      grande → pasa.
            if prev_gray is not None:
                # Camera shake check (phaseCorrelate): mide el desplazamiento
                # global entre frames. Vibración → shift detectable y response
                # alto. Motion real → shift ≈ 0 porque el fondo no se mueve.
                shift, response = cv2.phaseCorrelate(
                    prev_gray.astype(np.float32), gray.astype(np.float32)
                )
                shake_mag = float(np.hypot(shift[0], shift[1]))
                if response > 0.3 and shake_mag > 0.5:
                    prev_gray = gray
                    continue  # camera shake, no motion real

                diff = cv2.absdiff(gray, prev_gray)
                _, motion_mask = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
                motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
                motion_in_fg = cv2.bitwise_and(motion_mask, fg)
                total_motion_pix = cv2.countNonZero(motion_in_fg)
                if total_motion_pix == 0:
                    prev_gray = gray
                    continue
                motion_contours, _ = cv2.findContours(
                    motion_in_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                max_motion_area = max(cv2.contourArea(c) for c in motion_contours)
                active_pct = max_motion_area / total_pix * 100
                if active_pct < min_active_pct:
                    prev_gray = gray
                    continue

            prev_gray = gray
            detected.append(ts)
    return detected


def cluster_ranges(
    timestamps: list[float], gap: float, pad: float, duration: float
) -> list[tuple[float, float]]:
    """Agrupa timestamps en rangos contiguos (gap máximo entre detecciones) y
    aplica padding a ambos lados, clampeando a [0, duration]."""
    if not timestamps:
        return []
    ranges: list[tuple[float, float]] = []
    start = prev = timestamps[0]
    for t in timestamps[1:]:
        if t - prev > gap:
            ranges.append((start, prev))
            start = t
        prev = t
    ranges.append((start, prev))
    return [(max(0.0, s - pad), min(duration, e + pad)) for s, e in ranges]


def process(
    video_path: str,
    output_dir: str,
    mode: str,
    by_minute: bool,
    force_rotate: int | None,
    max_width: int = 1920,
    start: float = 0,
    end: float = 0,
    pixelize: bool = False,
    date_overlay: bool = True,
    quality: int = 85,
) -> int:
    fps_cfg, threshold, cooldown, noise = MODES[mode]
    duration, rotation, real_fps, _, _ = get_video_info(video_path)

    if force_rotate is not None:
        rotation = force_rotate

    fps = fps_cfg or real_fps  # full usa FPS real
    total_frames = int(duration * fps)
    stem = Path(video_path).stem

    print(f"Video : {Path(video_path).name}")
    print(f"Mode  : {mode} | Analysis FPS: {fps} | Duration: {duration:.1f}s (~{total_frames} frames)")
    if rotation:
        print(f"Rot.  : {rotation}° auto-corrected")
    if max_width > 0:
        print(f"Scale : max {max_width}px width (no upscale)")
    if start or end:
        end_label = f"{end:.0f}s" if end else "end"
        print(f"Range : {start:.0f}s → {end_label}")
    if pixelize:
        print(f"Pixelize: enabled — loading face detection model...")
        cv2, detect_faces, apply_mosaic = _load_pixelizer()
        print(f"Pixelize: ready")
    print()

    src_mtime = effective_mtime(video_path)
    date_str = datetime.fromtimestamp(src_mtime).strftime("%d/%m/%Y") if date_overlay else None

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    prev_small = None
    last_ts    = -cooldown
    captured   = 0
    SCALE      = 0.25

    with tqdm(total=total_frames, desc="Procesando", unit="frame") as pbar:
        for ts, frame in stream_frames(video_path, fps, rotation, max_width, start, end):
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
                _save(frame, output_dir, stem, captured + 1, ts, by_minute, src_mtime, date_str, quality)
                captured += 1
                last_ts   = ts
            del frame  # libera el array grande antes del próximo frame

    os.utime(output_dir, (src_mtime, src_mtime))
    return captured


def _draw_label(img: Image.Image, label: str) -> Image.Image:
    _, h = img.size
    font_size = max(24, int(h * 0.035))
    font = ImageFont.truetype(_DATE_FONT_PATH, font_size)
    draw = ImageDraw.Draw(img, "RGBA")
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = int(h * 0.025)
    pad = int(font_size * 0.4)
    box = (margin - pad, margin - pad, margin + tw + pad, margin + th + pad)
    draw.rectangle(box, fill=(0, 0, 0, 160))
    draw.text((margin, margin), label, font=font, fill="white",
              stroke_width=max(2, font_size // 14), stroke_fill="black")
    return img


def save_range_previews(
    video_path: str,
    preview_dir: Path,
    ranges: list[tuple[float, float]],
    rotation: int,
    max_width: int,
    quality: int = 85,
) -> None:
    """Extrae 1 frame al inicio y 1 al final de cada rango, con label overlay.
    ffmpeg extrae el frame raw; PIL agrega el texto (ffmpeg acá no trae drawtext)."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    for i, (s, e) in enumerate(ranges, 1):
        mid = (s + e) / 2
        for kind, ts in (("in", s), ("mid", mid), ("out", e)):
            mm = int(ts // 60)
            ss = ts % 60
            stamp = f"{mm:02d}m{ss:05.2f}s"
            label = f"R{i:02d} {kind.upper()} {stamp}"
            dest = preview_dir / f"range_{i:02d}_{kind}_{stamp}.jpg"
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-noautorotate"]
            if ts > 2.0:
                cmd += ["-ss", f"{ts - 2.0:.3f}", "-i", video_path, "-ss", "2.0"]
            else:
                cmd += ["-i", video_path, "-ss", f"{ts:.3f}"]
            cmd += [
                "-frames:v", "1",
                "-vf", _build_vf(None, rotation, max_width),
                "-f", "image2pipe", "-vcodec", "png", "-",
            ]
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0 or not proc.stdout:
                continue
            img = Image.open(BytesIO(proc.stdout)).convert("RGB")
            img = _draw_label(img, label)
            img.save(dest, quality=quality, optimize=True)


def save_ranges_video(
    video_path: str,
    output_path: Path,
    ranges: list[tuple[float, float]],
    rotation: int,
    max_width: int,
    real_fps: float,
) -> None:
    """Concatena los rangos activos a un solo mp4 con label overlay por frame.

    Pipeline: ffmpeg decode+select → rawvideo stdin → Python PIL label → rawvideo
    stdout → ffmpeg encode. Sin audio (cada rango necesitaría re-timestampear).
    """
    _, _, _, in_w, in_h = get_video_info(video_path)
    out_w, out_h = compute_output_dims(in_w, in_h, rotation, max_width)

    select_expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in ranges)
    vf = (
        f"select='{select_expr}',setpts=N/({real_fps}*TB)," +
        _build_vf(None, rotation, max_width)
    ).rstrip(",")

    decoder_cmd = [
        "ffmpeg", "-noautorotate", "-hide_banner", "-loglevel", "error",
        "-threads", _THREAD_CAP,
        "-i", video_path,
        "-vf", vf,
        "-an",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    encoder_cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{out_w}x{out_h}", "-r", f"{real_fps}",
        "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "15",
        "-threads", _THREAD_CAP,
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    decoder = subprocess.Popen(decoder_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    encoder = subprocess.Popen(encoder_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_bytes = out_w * out_h * 3
    frame_idx = 0
    cum_durations = []
    cum = 0.0
    for s, e in ranges:
        cum += e - s
        cum_durations.append(cum)

    def range_and_original_ts(output_t: float) -> tuple[int, float]:
        for i, (s, e) in enumerate(ranges):
            prev_cum = cum_durations[i - 1] if i > 0 else 0.0
            if output_t < cum_durations[i]:
                return i + 1, s + (output_t - prev_cum)
        i = len(ranges)
        s, e = ranges[-1]
        return i, e

    try:
        with tqdm(desc="Encoding highlights", unit="frame") as pbar:
            while True:
                chunks: list[bytes] = []
                remaining = frame_bytes
                while remaining > 0:
                    chunk = decoder.stdout.read(remaining)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                if remaining > 0:
                    break
                data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
                frame = np.frombuffer(data, np.uint8).reshape(out_h, out_w, 3).copy()

                output_t = frame_idx / real_fps
                rng_idx, orig_t = range_and_original_ts(output_t)
                mm = int(orig_t // 60)
                ss = orig_t % 60
                label = f"R{rng_idx:02d}  orig {mm:02d}:{ss:05.2f}"
                img = _draw_label(Image.fromarray(frame), label)
                encoder.stdin.write(np.asarray(img).tobytes())
                frame_idx += 1
                pbar.update(1)
    finally:
        if encoder.stdin:
            encoder.stdin.close()
        decoder.wait()
        encoder.wait()

    # Merge audio de los mismos rangos (si el source tiene audio)
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "default=nw=1:nk=1", video_path],
        capture_output=True, text=True
    )
    if probe.stdout.strip() == "audio":
        print("Merging concatenated audio...")
        video_only = output_path.with_suffix(".video_only.mp4")
        output_path.rename(video_only)
        audio_expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in ranges)
        audio_tmp = output_path.with_suffix(".audio_only.m4a")
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-threads", _THREAD_CAP,
            "-i", video_path,
            "-af", f"aselect='{audio_expr}',asetpts=N/SR/TB",
            "-vn", "-c:a", "aac", "-b:a", "128k",
            str(audio_tmp),
        ], check=False)
        if audio_tmp.exists():
            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-threads", _THREAD_CAP,
                "-i", str(video_only), "-i", str(audio_tmp),
                "-c:v", "copy", "-c:a", "copy",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                str(output_path),
            ], check=False)
            video_only.unlink(missing_ok=True)
            audio_tmp.unlink(missing_ok=True)
        else:
            video_only.rename(output_path)  # fallback


def smart_process(
    video_path: str,
    output_dir: str,
    scan_fps: float,
    scan_width: int,
    min_blob_pct: float,
    uniform_pct: float,
    min_solidity: float,
    min_active_pct: float,
    strong_blob_pct: float,
    gap: float,
    pad: float,
    force_rotate: int | None,
    max_width: int = 1920,
    pixelize: bool = False,
    date_overlay: bool = True,
    by_minute: bool = True,
    history: int = 500,
    var_threshold: float = 30.0,
    video_only: bool = False,
    quality: int = 85,
) -> int:
    """Pass 1: scan MOG2 → rangos. Pass 2: full-fps extraction en cada rango."""
    duration, rotation, real_fps, _, _ = get_video_info(video_path)
    if force_rotate is not None:
        rotation = force_rotate

    print(f"Video : {Path(video_path).name}")
    print(f"Mode  : smart | Scan fps: {scan_fps} @ {scan_width}px | Real fps: {real_fps}")
    print(f"Filters: min-blob {min_blob_pct}% | uniform {uniform_pct}% | solidity {min_solidity}")
    print(f"Cluster: gap {gap}s | pad {pad}s")
    print(f"Duration: {duration:.1f}s")
    if rotation:
        print(f"Rot.  : {rotation}° auto-corrected")
    print()
    print("Pass 1: scanning for motion (MOG2)...")
    timestamps = motion_scan(
        video_path, scan_fps, rotation, scan_width,
        min_blob_pct=min_blob_pct,
        uniform_pct=uniform_pct,
        min_solidity=min_solidity,
        min_active_pct=min_active_pct,
        strong_blob_pct=strong_blob_pct,
        history=history,
        var_threshold=var_threshold,
    )

    ranges = cluster_ranges(timestamps, gap, pad, duration)
    total_range_dur = sum(e - s for s, e in ranges)

    print()
    print(f"Detected {len(ranges)} active ranges ({total_range_dur:.1f}s total):")
    for i, (s, e) in enumerate(ranges, 1):
        sm, ss = int(s // 60), s % 60
        em, es = int(e // 60), e % 60
        print(f"  {i:2d}. {sm:02d}:{ss:05.2f} → {em:02d}:{es:05.2f}  ({e - s:.1f}s)")
    print()

    if not ranges:
        print("No motion detected. Nothing to extract.")
        return 0

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print("Saving range boundaries preview...")
    save_range_previews(
        video_path, Path(output_dir) / "_ranges_preview", ranges, rotation, max_width, quality
    )

    if video_only:
        video_path_out = Path(output_dir) / f"{Path(video_path).stem}_highlights.mp4"
        print(f"Pass 2: concatenating ranges to single video with labels...")
        save_ranges_video(
            video_path, video_path_out, ranges, rotation, max_width, real_fps
        )
        print(f"\nSaved highlights video: {video_path_out}")
        return 0

    print("Pass 2: extracting full-fps frames within ranges...")

    src_mtime = effective_mtime(video_path)
    date_str = datetime.fromtimestamp(src_mtime).strftime("%d/%m/%Y") if date_overlay else None
    stem = Path(video_path).stem

    if pixelize:
        cv2, detect_faces, apply_mosaic = _load_pixelizer()

    total_frames = int(total_range_dur * real_fps)
    captured = 0

    with tqdm(total=total_frames, desc="Pass 2 (full)", unit="frame") as pbar:
        for s, e in ranges:
            for ts, frame in stream_frames(video_path, real_fps, rotation, max_width, start=s, end=e):
                pbar.update(1)
                if pixelize:
                    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    boxes = detect_faces(bgr)
                    if boxes:
                        bgr = apply_mosaic(bgr, boxes)
                    frame = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                _save(frame, output_dir, stem, captured + 1, ts, by_minute, src_mtime, date_str, quality)
                captured += 1
                del frame

    os.utime(output_dir, (src_mtime, src_mtime))
    return captured


def _save(frame: np.ndarray, output_dir: str, stem: str, idx: int, ts: float, by_minute: bool, src_mtime: float, date_str: str | None = None, quality: int = 85) -> None:
    minutes  = int(ts // 60)
    seconds  = ts % 60
    filename = f"{stem}_{idx:04d}_{minutes:02d}m{seconds:05.2f}s.jpg"
    dest     = Path(output_dir) / (f"{minutes:02d}m" if by_minute else "") / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if date_str:
        img = _draw_date(Image.fromarray(frame), date_str)
        img.save(dest, quality=quality, optimize=True)
    else:
        import cv2 as _cv2  # local: avoid hard dep si no está cargado
        opts = [_cv2.IMWRITE_JPEG_QUALITY, quality]
        if hasattr(_cv2, "IMWRITE_JPEG_OPTIMIZE"):
            opts += [_cv2.IMWRITE_JPEG_OPTIMIZE, 1]
        _cv2.imwrite(str(dest), frame[:, :, ::-1], opts)
    os.utime(dest, (src_mtime, src_mtime))


def main():
    parser = argparse.ArgumentParser(
        description="Captura frames de un video con detección de cambios"
    )
    parser.add_argument("video", help="Ruta al video")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["full", "medium", "low", "smart"],
        default="full",
        help="Modo de captura (default: full)"
    )
    parser.add_argument("--output", "-o", default=None, help="Directorio de salida")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None,
                        help="Forzar rotación en grados")
    parser.add_argument("--no-group", action="store_true",
                        help="No agrupar capturas por minuto")
    parser.add_argument("--max-width", type=int, default=1920, metavar="PX",
                        help="Downscale a este ancho máximo antes de procesar (default: 1920). 0 = sin límite")
    parser.add_argument("--start", default="0",
                        help="Comenzar desde este punto (segundos o MM:SS, default: 0)")
    parser.add_argument("--end", default="0",
                        help="Detener en este punto (segundos o MM:SS, default: fin del video)")
    parser.add_argument("--pixelize", "-p", action="store_true",
                        help="Aplicar mosaico fuerte sobre caras detectadas en cada captura")
    parser.add_argument("--no-date", action="store_true",
                        help="No agregar overlay de fecha en las capturas")
    parser.add_argument("--quality", "-q", type=int, default=85, metavar="N",
                        help="Calidad JPEG 1–95 (default: 85). "
                             "85 es visualmente equivalente a 95 pero ~40%% más liviano. "
                             "75 para archivado, 65 para tamaño mínimo")
    # smart-mode flags
    parser.add_argument("--scan-fps", type=float, default=4.0,
                        help="[smart] FPS del pass 1 (default: 4)")
    parser.add_argument("--scan-width", type=int, default=480,
                        help="[smart] Ancho en px al que se downsamplea el video para el scan (default: 480). Más chico = más rápido, menos recall en cosas muy chicas")
    parser.add_argument("--min-blob-pct", type=float, default=0.1,
                        help="[smart] Área mínima del blob como %% del frame (default: 0.1 = ~130px a 480×270). Más chico = detecta partes de cuerpo más pequeñas")
    parser.add_argument("--uniform-pct", type=float, default=70.0,
                        help="[smart] Si el cambio cubre más de este %% del frame, se considera cambio global de luz y se descarta (default: 70)")
    parser.add_argument("--min-solidity", type=float, default=0.3,
                        help="[smart] Solidez mínima del blob (área/hull_area). Descarta streaks elongados de ruido. 0.3 tolera bastante; subir a 0.5 para ser más estricto (default: 0.3)")
    parser.add_argument("--min-active-pct", type=float, default=0.05,
                        help="[smart] %% mínimo del blob CONTIGUO más grande de cambio frame-a-frame. Filtra vibraciones (muchos edges dispersos) y colas post-motion (MOG2 aún absorbiendo nuevo fondo). 0.05 ≈ 65px a 480×270. Subir a 0.2 para rechazar movimientos muy chicos (default: 0.05)")
    parser.add_argument("--strong-blob-pct", type=float, default=2.0,
                        help="[smart] Si el blob MOG2 es ≥ este %%, bypassea el filtro de active-motion (presencia clara aunque no se mueva). Evita cortar cuando una persona queda quieta en escena (default: 2.0)")
    parser.add_argument("--history", type=int, default=500,
                        help="[smart] Frames de historia del modelo de fondo MOG2. Más alto = los micro-movimientos se absorben antes (default: 500 ≈ 125s a 4fps)")
    parser.add_argument("--var-threshold", type=float, default=30.0,
                        help="[smart] Umbral de varianza MOG2 por pixel. Más alto = menos sensible a cambios chicos de intensidad (default: 30). OpenCV default es 16 pero es muy sensible para escenas con respiración/iluminación sutil")
    parser.add_argument("--video-only", action="store_true",
                        help="[smart] En lugar de extraer frames, produce un solo mp4 concatenando los rangos activos con label de tiempo original")
    parser.add_argument("--gap", type=float, default=5.0,
                        help="[smart] Máximo segundos entre detecciones para seguir en el mismo rango (default: 5)")
    parser.add_argument("--pad", type=float, default=3.0,
                        help="[smart] Segundos de padding a cada lado del rango (default: 3). Más alto captura mejor las continuaciones lentas (persona agachándose) a costa de algunos frames vacíos al borde")

    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: not found '{args.video}'", file=sys.stderr)
        sys.exit(1)

    def parse_time(s: str) -> float:
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) * 60 + float(parts[1])
        return float(s)

    video_path = Path(args.video).resolve()
    output_dir = args.output or str(video_path.parent / f"{video_path.stem}_capturas_{args.mode}")

    if args.mode == "smart":
        captured = smart_process(
            video_path=str(video_path),
            output_dir=output_dir,
            scan_fps=args.scan_fps,
            scan_width=args.scan_width,
            min_blob_pct=args.min_blob_pct,
            uniform_pct=args.uniform_pct,
            min_solidity=args.min_solidity,
            min_active_pct=args.min_active_pct,
            strong_blob_pct=args.strong_blob_pct,
            gap=args.gap,
            pad=args.pad,
            force_rotate=args.rotate,
            max_width=args.max_width,
            pixelize=args.pixelize,
            date_overlay=not args.no_date,
            by_minute=False,
            history=args.history,
            var_threshold=args.var_threshold,
            video_only=args.video_only,
            quality=args.quality,
        )
    else:
        captured = process(
            video_path=str(video_path),
            output_dir=output_dir,
            mode=args.mode,
            by_minute=not args.no_group and args.mode == "full",
            force_rotate=args.rotate,
            max_width=args.max_width,
            start=parse_time(args.start),
            end=parse_time(args.end),
            pixelize=args.pixelize,
            date_overlay=not args.no_date,
            quality=args.quality,
        )

    print(f"\nSaved {captured} frames in: {output_dir}/")


if __name__ == "__main__":
    main()
