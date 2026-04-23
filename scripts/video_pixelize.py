#!/home/tcabrera/.local/share/pipx/venvs/deface/bin/python3
"""
video_pixelize.py — pixela caras en un video (mosaic), preservando el mismo codec y audio.

Pipeline:
    ffmpeg extrae frames PNG → CenterFace detecta caras por frame →
    gap-fill con dilatación proporcional → mosaic median por frame →
    ffmpeg re-encodea con el codec del original (copia audio) →
    mtime original restaurado.

Uso:
    video_pixelize.py input.mp4
    video_pixelize.py input.mp4 --start 5 --to 15
    video_pixelize.py input.mp4 --block-pct 25 --threshold 0.15
    video_pixelize.py input.mp4 -o salida.mp4
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filename_date import effective_mtime  # noqa: E402


def run(cmd: list[str], *, stderr_to_stdout: bool = False) -> None:
    r = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if stderr_to_stdout else subprocess.PIPE,
        text=True,
    )
    if r.returncode != 0:
        err = r.stdout if stderr_to_stdout else r.stderr
        sys.stderr.write(f"FAILED: {' '.join(cmd)}\n{err}\n")
        sys.exit(r.returncode)


def probe_codec(src: Path) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=nw=1:nk=1", str(src)],
        capture_output=True, text=True,
    )
    return (r.stdout or "").strip().lower()


def probe_dims(src: Path) -> tuple[int, int] | None:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(src)],
        capture_output=True, text=True,
    )
    try:
        w, h = (r.stdout or "").strip().split("x")
        return int(w), int(h)
    except ValueError:
        return None


def encode_flags(codec: str) -> tuple[list[str], list[str], str]:
    """Devuelve (vcodec_args, pix_fmt_args, ext_sugerida)."""
    match codec:
        case "mjpeg":
            return (["-c:v", "mjpeg", "-q:v", "2"], [], ".avi")
        case "hevc" | "h265":
            return (["-c:v", "libx265", "-crf", "18"], ["-pix_fmt", "yuv420p"], ".mp4")
        case "vp9":
            return (["-c:v", "libvpx-vp9", "-crf", "20", "-b:v", "0"],
                    ["-pix_fmt", "yuv420p"], ".webm")
        case _:
            return (["-c:v", "libx264", "-crf", "18", "-preset", "slow"],
                    ["-pix_fmt", "yuv420p"], ".mp4")


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    n = 2
    while True:
        cand = p.with_name(f"{p.stem}_{n}{p.suffix}")
        if not cand.exists():
            return cand
        n += 1


# Gap-fill: si un frame no detectó caras, usar las del frame detectado más cercano
# dentro de MAX_GAP, con dilatación proporcional al gap (hasta MAX_DILATE).
DILATE_PER_FRAME = 3   # % por frame de distancia
MAX_DILATE = 25        # % máximo de dilatación
MAX_GAP = 5            # gaps > MAX_GAP se dejan sin mosaic


def _dilate_box(box, pct: float, shape: tuple[int, int]) -> tuple[int, int, int, int]:
    pct = min(pct, MAX_DILATE)
    x1, y1, x2, y2 = box
    dx = int((x2 - x1) * pct / 100)
    dy = int((y2 - y1) * pct / 100)
    H, W = shape
    return (max(0, x1 - dx), max(0, y1 - dy), min(W, x2 + dx), min(H, y2 + dy))


def _fill_gaps(per_frame: list[list[tuple]], shape: tuple[int, int]) -> tuple[list[list[tuple]], int, int]:
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

    filled = list(per_frame)
    gaps_filled = 0
    gaps_skipped = 0
    for i in range(n):
        if filled[i]:
            continue
        p, nx = prev_i[i], next_i[i]
        boxes: list[tuple] = []
        if p != -1 and (i - p) <= MAX_GAP:
            boxes += [_dilate_box(b, (i - p) * DILATE_PER_FRAME, shape) for b in per_frame[p]]
        if nx != -1 and (nx - i) <= MAX_GAP:
            boxes += [_dilate_box(b, (nx - i) * DILATE_PER_FRAME, shape) for b in per_frame[nx]]
        if boxes:
            filled[i] = boxes
            gaps_filled += 1
        else:
            gaps_skipped += 1
    return filled, gaps_filled, gaps_skipped


def main() -> None:
    p = argparse.ArgumentParser(description="Pixela caras en un video (mosaic sobre frames).")
    p.add_argument("input", type=Path, help="Video de entrada")
    p.add_argument("-o", "--output", type=Path,
                   help="Output video (default: <stem>_pixelated.<ext>)")
    p.add_argument("--start", help="Inicio (seg o HH:MM:SS)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--to", help="Fin (seg o HH:MM:SS)")
    g.add_argument("--duration", help="Duración (seg o HH:MM:SS)")
    p.add_argument("--block-pct", type=float, default=30.0,
                   dest="block_pct",
                   help="Tamaño del bloque como %% del ancho de cara (default: 30)")
    p.add_argument("--threshold", type=float, default=0.2,
                   help="Umbral de detección (default: 0.2)")
    p.add_argument("--model", default="scrfd", choices=["scrfd", "retinaface", "centerface"],
                   help="Detector: scrfd (balance, default), retinaface (R34, máx. precisión, ~3× más lento), centerface (2020, rápido)")
    p.add_argument("--fill-gaps", action=argparse.BooleanOptionalAction, default=True,
                   help="Rellenar gaps con bbox dilatada del frame detectado más cercano (default: on)")
    args = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"Error: '{tool}' not found in PATH")

    src = args.input.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: file does not exist: {src}")

    codec = probe_codec(src)
    vcodec_args, pix_fmt_args, default_ext = encode_flags(codec)

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        # Conservar la extensión original si es compatible; si no, usar la sugerida
        out = unique_path(src.with_name(f"{src.stem}_pixelated{src.suffix}"))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out == src:
        sys.exit("Error: output cannot overwrite the input")

    src_mtime = effective_mtime(src)

    # Importar deps pesadas después de validar inputs
    import cv2  # noqa: E402
    import pixelize as pix  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="video_pixelize_") as tmp:
        tmp_path = Path(tmp)
        frames_glob = tmp_path / "frame_%06d.png"

        # [1/3] Extraer frames (ffmpeg ya corrige rotación por defecto)
        ff_extract = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        if args.start:
            ff_extract += ["-ss", str(args.start)]
        if args.to:
            ff_extract += ["-to", str(args.to)]
        ff_extract += ["-i", str(src)]
        if args.duration:
            ff_extract += ["-t", str(args.duration)]
        ff_extract += [str(frames_glob)]

        print(f"[1/3] Extracting frames → {tmp_path}")
        run(ff_extract)

        frames = sorted(tmp_path.glob("frame_*.png"))
        if not frames:
            sys.exit("Error: ffmpeg produced no frames (invalid range?)")
        print(f"      {len(frames)} frame(s)")

        # Dims del primer frame
        first_img = cv2.imread(str(frames[0]))
        H, W = first_img.shape[:2]

        # [2/3] Detectar caras en todos los frames (sin cargarlos todos en RAM)
        print(f"[2/3] Detecting faces with {args.model} (threshold={args.threshold})...")
        per_frame: list[list[tuple]] = []
        detected = 0
        for i, f in enumerate(frames, 1):
            img = cv2.imread(str(f))
            boxes, _ = pix.detect_faces(img, threshold=args.threshold, model=args.model)
            per_frame.append(boxes)
            if boxes:
                detected += 1
            if i % 25 == 0 or i == len(frames):
                print(f"      {i}/{len(frames)} analyzed ({detected} with faces)")

        if args.fill_gaps:
            filled, gaps_ok, gaps_skip = _fill_gaps(per_frame, (H, W))
            print(f"      Gaps filled: {gaps_ok}  ·  skipped (>{MAX_GAP} frames): {gaps_skip}")
        else:
            filled = per_frame
            print(f"      Gap-fill disabled (--no-fill-gaps)")

        # [3/3] Aplicar mosaic sobre los frames y re-encodear
        print(f"      Applying mosaic (block={args.block_pct}%)...")
        for i, (f, boxes) in enumerate(zip(frames, filled), 1):
            if not boxes:
                continue
            img = cv2.imread(str(f))
            for box in boxes:
                img = pix.apply_mosaic_median(img, box, args.block_pct)
            cv2.imwrite(str(f), img)

        # FPS real del source (o entero aproximado). Usamos el del source para
        # mantener timing natural.
        fps_r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=nw=1:nk=1", str(src)],
            capture_output=True, text=True,
        ).stdout.strip()
        # r_frame_rate viene como "30000/1001" o "25/1"
        try:
            num, den = fps_r.split("/")
            fps = float(num) / float(den) if float(den) else 25.0
        except ValueError:
            fps = 25.0

        print(f"[3/3] Re-encoding → {out.name} ({codec} → {vcodec_args[1]})")
        ff_enc = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                  "-framerate", f"{fps:.6f}", "-i", str(frames_glob)]
        # Segundo input: el source (para copiar el audio del rango correspondiente)
        audio_args: list[str] = []
        if args.start or args.to or args.duration:
            audio_in = ["-i", str(src)]
            if args.start:
                audio_in = ["-ss", str(args.start)] + audio_in
            if args.to:
                audio_in = audio_in + ["-to", str(args.to)]
            if args.duration:
                audio_in = audio_in + ["-t", str(args.duration)]
            ff_enc += audio_in
            audio_args = ["-map", "0:v", "-map", "1:a?", "-c:a", "copy"]
        else:
            ff_enc += ["-i", str(src)]
            audio_args = ["-map", "0:v", "-map", "1:a?", "-c:a", "copy"]

        ff_enc += audio_args + vcodec_args + pix_fmt_args
        ff_enc += ["-metadata:s:v:0", "rotate=0", str(out)]

        run(ff_enc)

    os.utime(out, (src_mtime, src_mtime))
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"\n✓ {out}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
