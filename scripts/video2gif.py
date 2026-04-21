#!/home/tcabrera/.local/share/pipx/venvs/deface/bin/python3
"""
video2gif.py — convierte un tramo de video a GIF con gifski.

Pipeline: ffmpeg extrae frames PNG a un tmpdir → [pixelate opcional] → gifski empaqueta.
Preserva el mtime del archivo original en el GIF resultante.

Uso:
    video2gif.py input.mp4
    video2gif.py input.mp4 --start 5 --duration 4 --fps 20 --width 600
    video2gif.py input.mp4 --start 00:01:30 --to 00:01:35 -o out.gif
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
    p.add_argument("--quality", type=int, default=90, help="Calidad gifski 1-100 (default: 90)")
    p.add_argument("--lossy", type=int, help="gifski --lossy (1-100, opcional)")
    p.add_argument("--pixelate-faces", action="store_true",
                   help="Aplicar mosaic sobre caras detectadas en cada frame")
    p.add_argument("--pixelate-block", type=float, default=30.0,
                   help="Tamaño del bloque como %% del ancho de cara (default: 30 — más alto = más pixelado)")
    args = p.parse_args()

    src = args.input.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: no existe {src}")

    for tool in ("ffmpeg", "gifski"):
        if not shutil.which(tool):
            sys.exit(f"Error: falta '{tool}' en PATH")

    out = args.output.expanduser().resolve() if args.output else src.with_suffix(".gif")
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
            print(f"[1.5/2] Pixelando caras en {len(frames)} frames...")
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import cv2  # noqa: E402
            import pixelize  # noqa: E402
            faces_frames = 0
            for i, f in enumerate(frames, 1):
                img = cv2.imread(str(f))
                boxes, _ = pixelize.detect_faces(img)
                if boxes:
                    faces_frames += 1
                    for box in boxes:
                        img = pixelize.apply_mosaic_median(img, box, args.pixelate_block)
                    cv2.imwrite(str(f), img)
                if i % 10 == 0 or i == len(frames):
                    print(f"      {i}/{len(frames)} frames ({faces_frames} con caras)")

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
