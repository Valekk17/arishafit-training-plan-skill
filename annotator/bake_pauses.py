"""
bake_pauses.py — пересобирает MP4 с запечёнными паузами на ключевых кадрах.

Вход:
  exercisedb_data/mp4/<id>.mp4
  annotator/annotations_auto.json         — автодетект key_frames
  annotator/annotations_manual.json       — ручные правки (перекрывают авто)

Выход:
  exercisedb_data/mp4_paused/<id>.mp4     — то же видео, но на каждом ключевом
                                             кадре длительность ×HOLD_FRAMES

Алгоритм:
  1. Читаем все кадры MP4 через OpenCV.
  2. Строим новую последовательность: на ключевых кадрах вставляем HOLD_FRAMES-1
     дубликатов (всего HOLD_FRAMES кадров в этой позе).
  3. Пишем через ffmpeg raw pipe (bgr24) с тем же fps → libx264.

Параметры:
  HOLD_SECONDS = 0.5 — длительность паузы на ключевой позе
  На 10 fps это = 5 кадров одной позы подряд.
  Меньшая пауза = ритмичный «поза—движение—поза» без мёртвого воздуха.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MP4_DIR = ROOT / "exercisedb_data" / "mp4"
OUT_DIR = ROOT / "exercisedb_data" / "mp4_paused"
AUTO_F = Path(__file__).resolve().parent / "annotations_auto.json"
MANUAL_F = Path(__file__).resolve().parent / "annotations_manual.json"

HOLD_SECONDS = 0.5


def load_json(p):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def bake(eid: str, key_frames: list[int], verbose: bool = False):
    src = MP4_DIR / f"{eid}.mp4"
    dst = OUT_DIR / f"{eid}.mp4"
    if not src.exists():
        return (eid, "no_source")

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()

    if not frames:
        return (eid, "no_frames")

    hold_count = max(1, int(round(fps * HOLD_SECONDS)))
    key_set = set(key_frames)

    # Строим расширенную последовательность
    sequence = []
    for i, frame in enumerate(frames):
        sequence.append(frame)
        if i in key_set:
            # добавляем (hold_count - 1) дубликатов
            for _ in range(hold_count - 1):
                sequence.append(frame)

    h, w = frames[0].shape[:2]

    # Пишем через ffmpeg raw pipe
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "30",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(dst),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in sequence:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        err = proc.stderr.read()
        rc = proc.wait(timeout=60)
        if rc != 0:
            return (eid, f"ffmpeg_rc={rc}: {err.decode('utf-8', errors='ignore')[:200]}")
    except Exception as e:
        proc.kill()
        return (eid, f"exception: {e}")

    return (eid, "ok")


def resolve_key_frames(eid, auto, manual):
    m = manual.get(eid) or {}
    a = auto.get(eid) or {}
    if m.get("key_frames"):
        return list(m["key_frames"])
    if a.get("key_frames"):
        return list(a["key_frames"])
    # Обратная совместимость: start_frame + peak_frame
    sf = m.get("start_frame", a.get("start_frame", 0))
    pf = m.get("peak_frame", a.get("peak_frame", 6))
    return sorted({sf, pf})


def process_one(args):
    eid, key_frames = args
    return bake(eid, key_frames)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    auto = load_json(AUTO_F)
    manual = load_json(MANUAL_F)

    mp4s = sorted(MP4_DIR.glob("*.mp4"))
    tasks = []
    for mp4 in mp4s:
        eid = mp4.stem
        kf = resolve_key_frames(eid, auto, manual)
        if not kf:
            kf = [0, 6]
        tasks.append((eid, kf))

    print(f"Запекаю паузы в {len(tasks)} MP4 ({HOLD_SECONDS}с на ключевой кадр)...")
    print(f"  Источник: {MP4_DIR}")
    print(f"  Назначение: {OUT_DIR}")
    print()

    ok = 0
    fail = 0
    errors = []
    with ProcessPoolExecutor(max_workers=max(1, os.cpu_count() - 1)) as ex:
        futures = {ex.submit(process_one, t): t[0] for t in tasks}
        done = 0
        for fut in as_completed(futures):
            eid, status = fut.result()
            if status == "ok":
                ok += 1
            else:
                fail += 1
                errors.append((eid, status))
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(tasks)}  (ok={ok}, fail={fail})")

    print()
    print(f"Готово: {ok}/{len(tasks)} успешно, {fail} сбой")
    if errors:
        print("\nОшибки (первые 10):")
        for eid, st in errors[:10]:
            print(f"  {eid}: {st}")

    # Размер итога
    total_size = sum(p.stat().st_size for p in OUT_DIR.glob("*.mp4"))
    print(f"\nРазмер папки mp4_paused: {total_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
