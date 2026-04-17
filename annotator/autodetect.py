"""
autodetect.py v4 — старт всегда frame 0, пик = самый «чёрный» кадр.

Наблюдение пользователя:
  - переходные кадры имеют motion blur → чёрные элементы размываются
    и становятся серыми (в среднем светлее)
  - кадр-поза сохраняет чёрные элементы максимально насыщенными
  - поэтому самый «чёрный» кадр = пиковая поза

Метрика: blackness = 255 − percentile(gray, 5)
  percentile(gray, 5) — 5-й перцентиль яркости; это «самые тёмные» пиксели кадра.
  чем они темнее → тем больше blackness → тем чётче видна поза.

Алгоритм:
  1. start_frame = 0 (всегда).
  2. Считаем blackness для каждого кадра в пределах первого цикла.
  3. peak_frame = argmax(blackness) среди кадров 2..N-2 (исключая соседей старта).

Результат: annotator/annotations_auto.json
"""

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MP4_DIR = ROOT / "exercisedb_data" / "mp4"
OUT = Path(__file__).resolve().parent / "annotations_auto.json"


BLACK_THRESHOLD = 30         # пиксели яркости ниже 30 = «чёрные»
PEAK_THRESHOLD_RATIO = 1.5    # ключевой кадр = blackness ≥ median × 1.5
MIN_PEAK_SPACING = 3          # между ключевыми кадрами минимум 3 кадра


def find_key_frames(black_counts, min_spacing=MIN_PEAK_SPACING, threshold_ratio=PEAK_THRESHOLD_RATIO):
    """Находит все кадры с высокой чернотой (локальные максимумы циклические)."""
    n = len(black_counts)
    median = float(np.median(black_counts))
    threshold = median * threshold_ratio

    candidates = []
    for i in range(n):
        if black_counts[i] < threshold:
            continue
        # Локальный максимум — сравниваем с соседями циклически
        neighbors = [black_counts[(i + d) % n] for d in (-2, -1, 1, 2)]
        if all(black_counts[i] >= nb for nb in neighbors):
            candidates.append(i)

    # Убираем соседей ближе min_spacing (оставляем самый сильный из группы)
    candidates.sort()
    filtered = []
    for c in candidates:
        if filtered and c - filtered[-1] < min_spacing:
            if black_counts[c] > black_counts[filtered[-1]]:
                filtered[-1] = c
        else:
            filtered.append(c)
    return filtered


def analyze(path: Path):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        frames.append(gray)
    cap.release()

    n = len(frames)
    if n < 4:
        return None

    black_counts = np.array(
        [int(np.sum(f < BLACK_THRESHOLD)) for f in frames],
        dtype=np.int64,
    )

    # Находим все ключевые кадры (позы) в видео — НЕ пытаемся дедупить.
    # Пользователь в UI удалит лишние если они есть (например, 4 пика в 24-кадровом
    # жиме = 2 реальных позы × 2 цикла). Для Bradford (3 позы) и burpee (5 поз)
    # все пики реальные.
    key_frames = find_key_frames(black_counts)

    if not key_frames:
        key_frames = [0, min(6, n - 1)]
    elif 0 not in key_frames:
        key_frames = [0] + key_frames

    # Надёжность: все ли ключевые кадры имеют чистый сигнал
    median_non_key = float(np.median([
        black_counts[i] for i in range(n) if i not in key_frames
    ])) if len(key_frames) < n else 0.0
    min_key_count = int(min(black_counts[k] for k in key_frames))
    ratio = min_key_count / max(median_non_key, 1.0)
    reliable = ratio >= 2.0

    return {
        "total_frames": n,
        "fps": round(fps, 3),
        "key_frames": [int(k) for k in key_frames],
        # Обратная совместимость — старый формат с 2 точками
        "start_frame": int(key_frames[0]),
        "peak_frame": int(key_frames[1]) if len(key_frames) > 1 else int(key_frames[0]),
        "min_key_black_count": min_key_count,
        "median_others": round(median_non_key, 1),
        "ratio": round(ratio, 2),
        "reliable": bool(reliable),
        "auto": True,
    }


def process(path_str):
    p = Path(path_str)
    try:
        result = analyze(p)
        return (p.stem, result)
    except Exception as e:
        return (p.stem, {"error": str(e)})


def main():
    mp4s = sorted(MP4_DIR.glob("*.mp4"))
    print(f"Анализирую {len(mp4s)} MP4 через variance(Laplacian)...")

    results = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        futures = {ex.submit(process, str(p)): p.stem for p in mp4s}
        done = 0
        for fut in as_completed(futures):
            eid, data = fut.result()
            if data:
                results[eid] = data
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(mp4s)}...")

    # Статистика: сколько ключевых кадров и как распределены
    from collections import Counter
    key_counts = Counter()
    frame_counts = Counter()
    for d in results.values():
        key_counts[len(d.get("key_frames", []))] += 1
        frame_counts[d.get("total_frames")] += 1

    print()
    print(f"Готово: {len(results)} упражнений")
    print(f"\nКол-во ключевых кадров на упражнение:")
    for k in sorted(key_counts):
        bar = "█" * (key_counts[k] // 20)
        print(f"  {k} поз: {key_counts[k]:>4d} {bar}")

    print(f"\nРаспределение длины видео:")
    for fc in sorted(frame_counts):
        bar = "█" * (frame_counts[fc] // 20)
        print(f"  {fc} кадров: {frame_counts[fc]:>4d} {bar}")

    reliable = sum(1 for d in results.values() if d.get("reliable"))
    unreliable_ids = sorted(eid for eid, d in results.items() if not d.get("reliable"))
    print(f"\nНадёжность (min blackness ключевого кадра / median остальных ≥ 2):")
    print(f"  Надёжно:     {reliable}/{len(results)} ({reliable/len(results)*100:.1f}%)")
    print(f"  Сомнительно: {len(unreliable_ids)}")
    if unreliable_ids[:10]:
        print(f"  Примеры сомнительных: {unreliable_ids[:10]}")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {OUT}")


if __name__ == "__main__":
    main()
