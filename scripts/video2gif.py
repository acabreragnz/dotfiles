#!/home/tcabrera/.local/share/pipx/venvs/deface/bin/python3
"""
video2gif.py — convierte un tramo de video a GIF con gifski.

Pipeline: ffmpeg extrae frames PNG a un tmpdir → [pixelate opcional] → gifski empaqueta.
Preserva el mtime del archivo original en el GIF resultante.

Uso:
    video2gif.py input.mp4
    video2gif.py input.mp4 --start 5 --duration 4 --fps 20 --width 600
    video2gif.py input.mp4 --start 00:01:30 --to 00:01:35 -o out.gif
    video2gif.py input.mp4 --crop-height 400                 # recorta altura centrada
    video2gif.py input.mp4 --crop-height 400 --crop-y top    # recorta desde arriba
    video2gif.py input.mp4 --pixelate-faces       # mosaic sobre caras en cada frame
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"FAILED: {' '.join(cmd)}\n{result.stderr}\n")
        sys.exit(result.returncode)


def _parse_time(s: str) -> float:
    s = str(s).strip()
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        raise ValueError(f"formato inválido: {s}")
    return float(s)


def _format_time_compact(seconds: float) -> str:
    t = int(round(seconds))
    h, rem = divmod(t, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}h{m:02d}m{sec:02d}"
    if m > 0:
        return f"{m}m{sec:02d}"
    return f"{sec}s"


def _unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem}_{n}{p.suffix}")
        if not cand.exists():
            return cand
        n += 1


def _default_gif_path(src: Path, start: str, to: str | None, duration: str | None) -> Path:
    """<stem>.gif si no hay rango; <stem>_<start>-<end>.gif si hay."""
    try:
        start_s = _parse_time(start)
    except ValueError:
        start_s = 0.0
    has_start = start_s > 0
    end_s: float | None = None
    if to:
        try:
            end_s = _parse_time(to)
        except ValueError:
            end_s = None
    elif duration:
        try:
            end_s = start_s + _parse_time(duration)
        except ValueError:
            end_s = None

    if not has_start and end_s is None:
        return src.with_suffix(".gif")
    start_lbl = _format_time_compact(start_s)
    if end_s is not None:
        return src.with_name(f"{src.stem}_{start_lbl}-{_format_time_compact(end_s)}.gif")
    return src.with_name(f"{src.stem}_from_{start_lbl}.gif")


def main() -> None:
    p = argparse.ArgumentParser(description="Video → GIF con gifski.")
    p.add_argument("input", type=Path, help="Video de entrada")
    p.add_argument("-o", "--output", type=Path, help="GIF de salida (default: <stem>.gif al lado)")
    p.add_argument("--start", default="0", help="Tiempo de inicio (seg o HH:MM:SS). Default: 0")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--duration", help="Duración del tramo (seg o HH:MM:SS)")
    g.add_argument("--to", help="Tiempo final (seg o HH:MM:SS)")
    p.add_argument("--fps", type=int, default=15, help="FPS del GIF (default: 15)")
    p.add_argument("--width", type=int, default=480, help="Ancho en px (default: 480, -1 = original)")
    p.add_argument("--crop-height", type=int,
                   help="Recorta la altura a N px manteniendo el ancho completo (se aplica antes del scale)")
    p.add_argument("--crop-y", default="center",
                   help="Offset Y del crop en px, o 'top'/'center'/'bottom' (default: center)")
    p.add_argument("--quality", type=int, default=90, help="Calidad gifski 1-100 (default: 90)")
    p.add_argument("--lossy", type=int, help="gifski --lossy (1-100, opcional)")
    p.add_argument("--pixelate-faces", action="store_true",
                   help="Aplicar mosaic sobre caras detectadas en cada frame")
    p.add_argument("--pixelate-block", type=float, default=30.0,
                   help="Tamaño del bloque como %% del ancho de cara (default: 30 — más alto = más pixelado)")
    p.add_argument("--pixelate-threshold", type=float, default=0.2,
                   help="Umbral de detección (default: 0.2)")
    p.add_argument("--pixelate-model", default="scrfd", choices=["scrfd", "retinaface", "centerface"],
                   help="Detector: scrfd (default), retinaface (máx. precisión), centerface (rápido)")
    p.add_argument("--pixelate-fill-gaps", action=argparse.BooleanOptionalAction, default=True,
                   help="Rellenar gaps con bbox dilatada del frame detectado más cercano (default: on)")
    args = p.parse_args()

    src = args.input.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: no existe {src}")

    for tool in ("ffmpeg", "gifski"):
        if not shutil.which(tool):
            sys.exit(f"Error: falta '{tool}' en PATH")

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        out = _unique_path(_default_gif_path(src, args.start, args.to, args.duration))
    out.parent.mkdir(parents=True, exist_ok=True)

    src_mtime = os.stat(src).st_mtime

    with tempfile.TemporaryDirectory(prefix="video2gif_") as tmp:
        tmp_path = Path(tmp)
        frames_glob = tmp_path / "frame_%05d.png"

        ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
              "-ss", str(args.start), "-i", str(src)]
        if args.duration:
            ff += ["-t", str(args.duration)]
        elif args.to:
            ff += ["-to", str(args.to)]

        vf = [f"fps={args.fps}"]
        if args.crop_height:
            y_map = {"top": "0", "center": "(ih-oh)/2", "bottom": "ih-oh"}
            y_expr = y_map.get(args.crop_y, args.crop_y)
            vf.append(f"crop=iw:{args.crop_height}:0:{y_expr}")
        if args.width and args.width != -1:
            vf.append(f"scale={args.width}:-2:flags=lanczos")
        ff += ["-vf", ",".join(vf), str(frames_glob)]

        print(f"[1/2] Extrayendo frames → {tmp_path}")
        run(ff)

        frames = sorted(tmp_path.glob("frame_*.png"))
        if not frames:
            sys.exit("Error: ffmpeg no produjo frames (¿rango inválido?)")
        print(f"      {len(frames)} frame(s)")

        if args.pixelate_faces:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import cv2  # noqa: E402
            import pixelize  # noqa: E402

            # Paso 1: detectar en todos los frames (threshold bajo para más sensibilidad)
            print(f"[1.5/2] Detectando caras con {args.pixelate_model} en {len(frames)} frames (threshold={args.pixelate_threshold})...")
            imgs = [cv2.imread(str(f)) for f in frames]
            per_frame: list[list[tuple]] = []
            detected_count = 0
            for i, img in enumerate(imgs, 1):
                boxes, _ = pixelize.detect_faces(img, threshold=args.pixelate_threshold, model=args.pixelate_model)
                per_frame.append(boxes)
                if boxes:
                    detected_count += 1
                if i % 10 == 0 or i == len(imgs):
                    print(f"      {i}/{len(imgs)} analizados ({detected_count} con caras)")

            # Paso 2: rellenar gaps con la bbox del frame detectado más cercano
            if args.pixelate_fill_gaps:
                n = len(per_frame)
                prev_i = [-1] * n
                last = -1
                for i in range(n):
                    if per_frame[i]:
                        last = i
                    prev_i[i] = last
                next_i = [-1] * n
                nxt = -1
                for i in range(n - 1, -1, -1):
                    if per_frame[i]:
                        nxt = i
                    next_i[i] = nxt

                # Dilatación proporcional al gap, con máximo y límite de gap
                DILATE_PER_FRAME = 3   # % por frame de distancia
                MAX_DILATE = 25        # % máximo de dilatación
                MAX_GAP = 5            # si el gap a un lado supera esto, ignorar ese lado

                def dilate_box(box, pct, shape):
                    pct = min(pct, MAX_DILATE)
                    x1, y1, x2, y2 = box
                    dx, dy = int((x2 - x1) * pct / 100), int((y2 - y1) * pct / 100)
                    H, W = shape[:2]
                    return (max(0, x1 - dx), max(0, y1 - dy), min(W, x2 + dx), min(H, y2 + dy))

                filled = list(per_frame)
                gaps_filled = 0
                gaps_skipped = 0
                for i in range(n):
                    if filled[i]:
                        continue
                    p, nx = prev_i[i], next_i[i]
                    shape = imgs[i].shape
                    boxes = []
                    if p != -1 and (i - p) <= MAX_GAP:
                        boxes += [dilate_box(b, (i - p) * DILATE_PER_FRAME, shape) for b in per_frame[p]]
                    if nx != -1 and (nx - i) <= MAX_GAP:
                        boxes += [dilate_box(b, (nx - i) * DILATE_PER_FRAME, shape) for b in per_frame[nx]]
                    if boxes:
                        filled[i] = boxes
                        gaps_filled += 1
                    else:
                        gaps_skipped += 1
                print(f"      Gaps rellenados: {gaps_filled}  ·  skipeados (>{MAX_GAP} frames): {gaps_skipped}")
            else:
                filled = per_frame
                print(f"      Gap-fill desactivado (--no-pixelate-fill-gaps)")

            # Paso 3: aplicar mosaic sobre los frames
            print(f"      Aplicando mosaic (block={args.pixelate_block}%)...")
            for i, (img, boxes) in enumerate(zip(imgs, filled)):
                if not boxes:
                    continue
                for box in boxes:
                    img = pixelize.apply_mosaic_median(img, box, args.pixelate_block)
                cv2.imwrite(str(frames[i]), img)

        gs = ["gifski", "-o", str(out), "--fps", str(args.fps),
              "--quality", str(args.quality)]
        if args.lossy is not None:
            gs += ["--lossy-quality", str(args.lossy)]
        gs += [str(f) for f in frames]

        print(f"[2/2] Empaquetando GIF → {out.name}")
        run(gs)

    os.utime(out, (src_mtime, src_mtime))
    size_kb = out.stat().st_size / 1024
    print(f"\n✓ {out}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
