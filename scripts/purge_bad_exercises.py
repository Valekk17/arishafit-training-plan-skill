#!/usr/bin/env python3
"""
Удалить из БД упражнения с ошибочным mapping'ом, чтобы случайно
не использовать их снова.

Сейчас: cuKYxhu — nameRu «Наклон таза стоя», но анимация в БД показывает
подъём на носки (calf raise). Ошибка источника (ExerciseDB). Удаляю
полностью — и из JSON, и медиа-файлы.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'exercisedb_data' / 'exercise_db_final.json'
GIFS_HD = ROOT / 'exercisedb_data' / 'gifs_hd'
MP4_DIR = ROOT / 'exercisedb_data' / 'mp4'
MP4_PAUSED = ROOT / 'exercisedb_data' / 'mp4_paused'
GIFS_DIR = ROOT / 'exercisedb_data' / 'gifs'

# Список плохих exerciseId для полного удаления из БД
BAD_IDS = [
    'cuKYxhu',   # "Наклон таза стоя" — анимация calf raise, не pelvic tilt
]


def main():
    # 1. JSON
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    before = len(db)
    db = [e for e in db if e.get('exerciseId') not in BAD_IDS]
    removed = before - len(db)
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[JSON] removed {removed} entries (was {before}, now {len(db)})")

    # 2. Media files
    media_dirs = [GIFS_HD, MP4_DIR, MP4_PAUSED, GIFS_DIR]
    extensions = ['.webp', '.mp4', '.gif']

    for eid in BAD_IDS:
        for d in media_dirs:
            for ext in extensions:
                p = d / f'{eid}{ext}'
                if p.exists():
                    p.unlink()
                    print(f"[DEL] {p.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
