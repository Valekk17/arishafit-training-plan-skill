"""
extract_hd_frame.py — извлекает замороженный кадр из HD WebP и кладёт его в assets/.

Назначение: некоторые «упражнения» не являются упражнениями — это статичные практики
(дыхание, медитация, изометрия). GIF-анимация для них вредна: показывает движение,
которого не должно быть. Нам нужен одиночный HD-кадр с правильной стартовой позицией.

Источник: exercisedb_data/gifs_hd/<exerciseId>.webp (720×720 HD WebP, 12 кадров)
Выход:    training-skill/assets/<asset_name>.png (720×720 HD PNG, один кадр)

Использование:
    python scripts/extract_hd_frame.py --exercise-id NKJ8o6x --asset-name breathing_lying --frame 0
    python scripts/extract_hd_frame.py --exercise-id iny3m5y --asset-name dead_bug_setup
"""

import argparse
import os
import sys

from PIL import Image


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GIFS_HD_DIR = os.path.join(SCRIPT_DIR, "..", "..", "exercisedb_data", "gifs_hd")
ASSETS_DIR = os.path.join(SCRIPT_DIR, "..", "assets")


def extract_frame(exercise_id: str, asset_name: str, frame_idx: int = 0) -> str:
    src_path = os.path.join(GIFS_HD_DIR, f"{exercise_id}.webp")
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"HD source not found: {src_path}")

    os.makedirs(ASSETS_DIR, exist_ok=True)
    out_path = os.path.join(ASSETS_DIR, f"{asset_name}.png")

    im = Image.open(src_path)
    n_frames = getattr(im, "n_frames", 1)
    if frame_idx >= n_frames:
        raise ValueError(f"{exercise_id} has {n_frames} frames, asked for {frame_idx}")
    im.seek(frame_idx)

    frame = im.convert("RGBA")
    frame.save(out_path, "PNG", optimize=True)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Extracted: {exercise_id} frame #{frame_idx} -> assets/{asset_name}.png")
    print(f"  Resolution: {frame.size}")
    print(f"  File size:  {size_kb:.1f} KB")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exercise-id", required=True, help="exerciseId из ExerciseDB (напр. NKJ8o6x)")
    ap.add_argument("--asset-name", required=True, help="имя файла в assets/ без расширения")
    ap.add_argument("--frame", type=int, default=0, help="индекс кадра (0 = стартовая поза, default)")
    args = ap.parse_args()
    try:
        extract_frame(args.exercise_id, args.asset_name, args.frame)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
