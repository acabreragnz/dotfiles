#!/home/tcabrera/.local/share/pipx/venvs/deface/bin/python3
"""
anonymize_faces.py — generate a full sample tree of face anonymization variants.

Usage:
    anonymize_faces.py <image>
    anonymize_faces.py <image> --output-dir /path/to/output

Output structure:
    {stem}_anonymized/
    ├── original.jpg
    ├── blur/
    │   ├── box/          (01_apenas.jpg … 04_sutil.jpg)
    │   ├── gaussian/     (02_muy_leve.jpg … 07_suave.jpg)
    │   └── median/       (01_apenas.jpg … 04_sutil.jpg)
    ├── mosaic/
    │   └── median/       (05pct.jpg … 40pct.jpg)
    └── face/             ← partial-region variants
        ├── eyes_band/blur/gaussian/*, eyes_band/mosaic/median/*
        └── eyes_nose/blur/gaussian/*, eyes_nose/mosaic/median/*

Files that already exist are skipped (preserves manual deletions).
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DEFACE_SITE = "/home/tcabrera/.local/share/pipx/venvs/deface/lib/python3.12/site-packages"
if DEFACE_SITE not in sys.path:
    sys.path.insert(0, DEFACE_SITE)

from deface.centerface import CenterFace  # noqa: E402


# ---------------------------------------------------------------------------
# Blur helpers
# ---------------------------------------------------------------------------

def _odd(n: int) -> int:
    n = max(1, n)
    return n if n % 2 == 1 else n + 1


def apply_box_blur(img: np.ndarray, box, bf: int) -> np.ndarray:
    x1, y1, x2, y2 = box
    kw = max(1, abs(x2 - x1) // bf)
    kh = max(1, abs(y2 - y1) // bf)
    out = img.copy()
    out[y1:y2, x1:x2] = cv2.blur(img[y1:y2, x1:x2], (kw, kh))
    return out


def apply_gaussian_blur(img: np.ndarray, box, bf: int) -> np.ndarray:
    x1, y1, x2, y2 = box
    kw = _odd(max(1, abs(x2 - x1) // bf))
    kh = _odd(max(1, abs(y2 - y1) // bf))
    out = img.copy()
    out[y1:y2, x1:x2] = cv2.GaussianBlur(img[y1:y2, x1:x2], (kw, kh), 0)
    return out


def apply_median_blur(img: np.ndarray, box, bf: int) -> np.ndarray:
    x1, y1, x2, y2 = box
    k = _odd(max(1, abs(x2 - x1) // bf))
    out = img.copy()
    out[y1:y2, x1:x2] = cv2.medianBlur(img[y1:y2, x1:x2], k)
    return out


# ---------------------------------------------------------------------------
# Mosaic helper (median-color per block, size as % of face width)
# ---------------------------------------------------------------------------

def apply_mosaic_median(img: np.ndarray, box, block_pct: float) -> np.ndarray:
    x1, y1, x2, y2 = box
    block_size = max(2, int((x2 - x1) * block_pct / 100))
    out = img.copy()
    for y in range(y1, y2, block_size):
        for x in range(x1, x2, block_size):
            bx2 = min(x2, x + block_size)
            by2 = min(y2, y + block_size)
            block = img[y:by2, x:bx2]
            median_color = np.median(block.reshape(-1, block.shape[2]), axis=0).astype(np.uint8)
            out[y:by2, x:bx2] = median_color
    return out


# ---------------------------------------------------------------------------
# Face detection with mask_scale
# ---------------------------------------------------------------------------

def detect_faces(img_bgr: np.ndarray, threshold: float = 0.2, mask_scale: float = 1.3):
    H, W = img_bgr.shape[:2]
    centerface = CenterFace()
    dets, lms = centerface(img_bgr, threshold=threshold)
    boxes, landmarks = [], []
    for det, lm in zip(dets, lms):
        rx1, ry1, rx2, ry2 = det[:4]
        cx, cy = (rx1 + rx2) / 2, (ry1 + ry2) / 2
        fw = (rx2 - rx1) * mask_scale
        fh = (ry2 - ry1) * mask_scale
        x1 = max(0, int(cx - fw / 2))
        y1 = max(0, int(cy - fh / 2))
        x2 = min(W, int(cx + fw / 2))
        y2 = min(H, int(cy + fh / 2))
        boxes.append((x1, y1, x2, y2))
        landmarks.append({
            "eye_l":   (int(lm[0]), int(lm[1])),
            "eye_r":   (int(lm[2]), int(lm[3])),
            "nose":    (int(lm[4]), int(lm[5])),
            "mouth_l": (int(lm[6]), int(lm[7])),
            "mouth_r": (int(lm[8]), int(lm[9])),
        })
    return boxes, landmarks


# ---------------------------------------------------------------------------
# Partial region helpers
# ---------------------------------------------------------------------------

def region_eyes_band(box, lm, img_shape):
    H, _ = img_shape[:2]
    x1, y1, x2, y2 = box
    face_h = y2 - y1
    eye_cy = (lm["eye_l"][1] + lm["eye_r"][1]) // 2
    return (x1, max(0, eye_cy - int(face_h * 0.18)), x2, min(H, eye_cy + int(face_h * 0.18)))


def region_eyes_nose(box, lm, img_shape):
    H, _ = img_shape[:2]
    x1, y1, x2, _ = box
    face_h = box[3] - y1
    return (x1, y1, x2, min(H, lm["nose"][1] + int(face_h * 0.10)))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_as_bgr(path: Path) -> np.ndarray:
    pil = Image.open(path).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BLUR_BOX_LEVELS = [
    ("01_apenas",   30),
    ("02_muy_leve", 20),
    ("03_leve",     15),
    ("04_sutil",    12),
]

BLUR_GAUSSIAN_LEVELS = [
    ("02_muy_leve", 20),
    ("03_leve",     15),
    ("04_sutil",    12),
    ("05_notorio",  10),
    ("06_medio",     8),
    ("07_suave",     4),
]

BLUR_MEDIAN_LEVELS = [
    ("01_apenas",   30),
    ("02_muy_leve", 20),
    ("03_leve",     15),
    ("04_sutil",    12),
]

MOSAIC_PCTS = [5, 10, 15, 20, 30, 40]


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def apply_to_all(img, boxes, fn):
    result = img.copy()
    for box in boxes:
        result = fn(result, box)
    return result


def save(path: Path, img: np.ndarray, output_dir: Path):
    if path.exists():
        print(f"  skip (exists) → {path.relative_to(output_dir)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)
    print(f"  → {path.relative_to(output_dir)}")


def generate(input_path: Path, output_dir: Path):
    print(f"Loading: {input_path}")
    img = load_as_bgr(input_path)

    print("Detecting faces...")
    boxes, landmarks = detect_faces(img)
    if not boxes:
        print("No faces detected. Exiting.")
        sys.exit(1)
    print(f"  Found {len(boxes)} face(s)")

    output_dir.mkdir(parents=True, exist_ok=True)

    # original
    orig = output_dir / "original.jpg"
    if not orig.exists():
        cv2.imwrite(str(orig), img)
        print(f"  → original.jpg")

    # --- full-face (flat) ---
    print("\n[full face — blur_box]")
    for label, bf in BLUR_BOX_LEVELS:
        save(output_dir / f"blur_box_{label}.jpg",
             apply_to_all(img, boxes, lambda im, b, _bf=bf: apply_box_blur(im, b, _bf)),
             output_dir)

    print("\n[full face — blur_gaussian]")
    for label, bf in BLUR_GAUSSIAN_LEVELS:
        save(output_dir / f"blur_gaussian_{label}.jpg",
             apply_to_all(img, boxes, lambda im, b, _bf=bf: apply_gaussian_blur(im, b, _bf)),
             output_dir)

    print("\n[full face — blur_median]")
    for label, bf in BLUR_MEDIAN_LEVELS:
        save(output_dir / f"blur_median_{label}.jpg",
             apply_to_all(img, boxes, lambda im, b, _bf=bf: apply_median_blur(im, b, _bf)),
             output_dir)

    print("\n[full face — mosaic_median]")
    for pct in MOSAIC_PCTS:
        save(output_dir / f"mosaic_median_{pct:02d}pct.jpg",
             apply_to_all(img, boxes, lambda im, b, _p=pct: apply_mosaic_median(im, b, _p)),
             output_dir)

    # --- partial regions (flat inside face/) ---
    face_dir = output_dir / "face"
    print("\n[face/ — partial regions]")
    for box, lm in zip(boxes, landmarks):
        band = region_eyes_band(box, lm, img.shape)
        eyes_nose = region_eyes_nose(box, lm, img.shape)

        for label, bf in BLUR_GAUSSIAN_LEVELS:
            save(face_dir / f"eyes_band_blur_gaussian_{label}.jpg",
                 apply_gaussian_blur(img, band, bf), output_dir)

        for pct in MOSAIC_PCTS:
            save(face_dir / f"eyes_band_mosaic_median_{pct:02d}pct.jpg",
                 apply_mosaic_median(img, band, pct), output_dir)

        for label, bf in BLUR_GAUSSIAN_LEVELS:
            save(face_dir / f"eyes_nose_blur_gaussian_{label}.jpg",
                 apply_gaussian_blur(img, eyes_nose, bf), output_dir)

        for pct in MOSAIC_PCTS:
            save(face_dir / f"eyes_nose_mosaic_median_{pct:02d}pct.jpg",
                 apply_mosaic_median(img, eyes_nose, pct), output_dir)

    print(f"\nDone. Output: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate face anonymization sample tree for a photo."
    )
    parser.add_argument("image", help="Path to input image (JPG, PNG, …)")
    parser.add_argument("--output-dir", help="Output directory (default: <stem>_anonymized next to input)")
    args = parser.parse_args()

    input_path = Path(args.image).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_path.parent / f"{input_path.stem}_anonymized"
    )

    generate(input_path, output_dir)


if __name__ == "__main__":
    main()
