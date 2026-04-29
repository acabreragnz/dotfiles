#!/usr/bin/env python3
"""Trim dead time from a Chrome DevTools MCP screencast.

Detects idle runs (consecutive frames with low pixel diff) and drops them,
preserving an "assimilation gap" of N frames after each motion-to-idle
transition so the viewer can register what happened.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def trim(src: Path, dst: Path, threshold: float, gap_frames: int, fps: int,
         keep_frames: bool) -> None:
    if not src.exists():
        sys.exit(f"input not found: {src}")

    with tempfile.TemporaryDirectory(prefix="trim-screencast-") as tmp:
        frames_dir = Path(tmp) / "frames"
        keep_dir = Path(tmp) / "kept"
        frames_dir.mkdir()
        keep_dir.mkdir()

        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-vf", f"fps={fps}", str(frames_dir / "f%05d.png")],
            check=True,
        )

        frames = sorted(frames_dir.glob("f*.png"))
        if not frames:
            sys.exit("no frames extracted")

        prev = None
        keep_idx: list[int] = []
        idle_run = 0
        for i, p in enumerate(frames):
            arr = np.array(
                Image.open(p).convert("L").resize((160, 90)), dtype=np.int16
            )
            if prev is None:
                keep_idx.append(i)
                prev = arr
                continue
            diff = float(np.mean(np.abs(arr - prev)))
            if diff > threshold:
                keep_idx.append(i)
                idle_run = 0
            else:
                idle_run += 1
                if idle_run <= gap_frames:
                    keep_idx.append(i)
            prev = arr

        for j, idx in enumerate(keep_idx, 1):
            os.symlink(frames[idx], keep_dir / f"g{j:05d}.png")

        if dst.suffix == ".webm":
            codec = ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0"]
        else:
            codec = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23"]

        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-framerate", str(fps),
             "-i", str(keep_dir / "g%05d.png"),
             *codec, str(dst)],
            check=True,
        )

        if keep_frames:
            target = Path("/tmp/trim-screencast-frames")
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(frames_dir, target)
            print(f"kept frames: {target}")

    total_s = len(frames) / fps
    kept_s = len(keep_idx) / fps
    print(
        f"frames: {len(keep_idx)}/{len(frames)} kept "
        f"({kept_s:.2f}s of {total_s:.2f}s, "
        f"{100 * (1 - len(keep_idx) / len(frames)):.1f}% trimmed)"
    )
    print(f"output: {dst}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input", help="input .webm/.mp4")
    ap.add_argument("output", help="output .webm/.mp4")
    ap.add_argument(
        "--threshold", type=float, default=0.05,
        help="motion threshold (mean abs diff on 160x90 grayscale, 0-255). "
             "Higher trims more aggressively. Default 0.05.",
    )
    ap.add_argument(
        "--gap-frames", type=int, default=30,
        help="frames kept after motion stops (assimilation gap). "
             "Default 30 (~1.2s at 25fps).",
    )
    ap.add_argument("--fps", type=int, default=25, help="frame rate. Default 25.")
    ap.add_argument(
        "--keep-frames", action="store_true",
        help="copy extracted frames to /tmp/trim-screencast-frames for inspection.",
    )
    args = ap.parse_args()
    trim(Path(args.input).resolve(), Path(args.output).resolve(),
         args.threshold, args.gap_frames, args.fps, args.keep_frames)


if __name__ == "__main__":
    main()
