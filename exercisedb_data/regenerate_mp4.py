"""
regenerate_mp4.py — конвертирует HD WebP-анимации в h264 MP4.

Зачем: MP4 в ~7 раз компактнее, чем WebP при том же визуальном качестве
(gifs_hd/ = 507 MB, mp4/ = ~70 MB для 1323 упражнений).

Pipeline:
  gifs_hd/<id>.webp  →  PIL extract frames → PNG pipe → ffmpeg libx264 → mp4/<id>.mp4

Resumable: пропускает уже сконвертированные.
"""

import concurrent.futures as cf
import io
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).parent
HD_DIR = SCRIPT_DIR / "gifs_hd"
MP4_DIR = SCRIPT_DIR / "mp4"

MP4_DIR.mkdir(exist_ok=True)


def webp_to_mp4(webp_path: Path, mp4_path: Path) -> tuple[bool, str]:
    """Один файл: WebP → PNG-поток → ffmpeg → MP4."""
    try:
        im = Image.open(webp_path)
        n_frames = im.n_frames
        # Длительность кадра из WebP (мс) — дефолт 100 мс если нет
        durations = []
        for i in range(n_frames):
            im.seek(i)
            durations.append(im.info.get("duration", 100))

        # Средний FPS: берём среднюю длительность кадра
        avg_dur = sum(durations) / len(durations) if durations else 100
        fps = round(1000 / avg_dur) if avg_dur > 0 else 10
        fps = max(5, min(fps, 30))  # clamp 5-30

        # Подготовим PNG-поток в памяти
        # Проще всего: сохраним временный GIF и его скармливаем ffmpeg
        tmp_gif = mp4_path.with_suffix(".tmp.gif")
        frames = []
        for i in range(n_frames):
            im.seek(i)
            frames.append(im.copy().convert("RGB"))

        if len(frames) == 1:
            frames[0].save(tmp_gif, "GIF")
        else:
            frames[0].save(
                tmp_gif, "GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2,
            )

        # GIF → MP4 (h264, baseline, faststart для web)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(tmp_gif),
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "30",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-vf", "scale=720:720",
            "-an",
            str(mp4_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        tmp_gif.unlink(missing_ok=True)

        if result.returncode != 0:
            return False, f"ffmpeg: {result.stderr[:120]}"
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    all_webps = sorted(HD_DIR.glob("*.webp"))
    done = {p.stem for p in MP4_DIR.glob("*.mp4")}
    todo = [p for p in all_webps if p.stem not in done]
    print(f"HD WebP: {len(all_webps)} | Already MP4: {len(done)} | To convert: {len(todo)}")

    if not todo:
        total = sum(p.stat().st_size for p in MP4_DIR.glob("*.mp4"))
        print(f"mp4/ total: {total/1024/1024:.1f} MB, {len(list(MP4_DIR.glob('*.mp4')))} files")
        return

    ok = fail = 0
    t0 = time.time()

    # Параллелим по ядрам (ffmpeg сам многопоточный, так что 4 воркера достаточно)
    def task(webp_path):
        mp4_path = MP4_DIR / f"{webp_path.stem}.mp4"
        return webp_path.stem, *webp_to_mp4(webp_path, mp4_path)

    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for i, (eid, success, err) in enumerate(ex.map(task, todo), 1):
            if success:
                ok += 1
            else:
                fail += 1
                print(f"  FAIL {eid}: {err}")
            if i % 50 == 0:
                dt = time.time() - t0
                rate = i / dt * 60
                eta = (len(todo) - i) / (rate / 60)
                print(f"  [{i}/{len(todo)}] ok={ok} fail={fail} | {rate:.0f}/min | ETA {eta:.0f}s")

    dt = time.time() - t0
    total = sum(p.stat().st_size for p in MP4_DIR.glob("*.mp4"))
    print(f"\nDone: {ok} ok, {fail} fail in {dt:.0f}s")
    print(f"mp4/ total: {total/1024/1024:.1f} MB across {len(list(MP4_DIR.glob('*.mp4')))} files")


if __name__ == "__main__":
    sys.exit(main())
