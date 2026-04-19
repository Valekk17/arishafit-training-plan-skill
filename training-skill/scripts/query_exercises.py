"""
query_exercises.py — Поиск упражнений в PostgreSQL через SQLAlchemy.

Для ручного исследования БД и построения промптов для Opus.
Читает через db.queries (без docker exec / psql).

Примеры:
    # все упражнения на грудь
    python query_exercises.py --target-muscle pectorals

    # жимовые движения без свободного веса
    python query_exercises.py --movement-pattern push_horizontal --equipment "leverage machine"

    # все с тазобедренным паттерном и анимацией
    python query_exercises.py --body-part "upper legs" --has-animation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from db.queries import find_exercises, is_db_available


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-muscle", default=None)
    ap.add_argument("--body-part", default=None)
    ap.add_argument("--equipment", default=None)
    ap.add_argument("--movement-pattern", default=None)
    ap.add_argument("--has-animation", action="store_true")
    ap.add_argument("--output", default=None, help="Сохранить в JSON (иначе stdout таблицей)")
    ap.add_argument("--limit", type=int, default=0, help="Ограничить вывод")
    args = ap.parse_args()

    if not is_db_available():
        print("ERROR: PostgreSQL недоступен. Запусти: docker compose up -d", file=sys.stderr)
        sys.exit(1)

    results = find_exercises(
        target_muscle=args.target_muscle,
        body_part=args.body_part,
        equipment=args.equipment,
        movement_pattern=args.movement_pattern,
        has_animation=args.has_animation if args.has_animation else None,
    )

    if args.limit:
        results = results[: args.limit]

    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Сохранено: {args.output} ({len(results)} упр.)")
    else:
        print(f"Найдено: {len(results)}")
        for ex in results[:50]:
            pat = ",".join(ex.get("movementPatterns", []))
            print(f"  {ex['exerciseId']}: {ex['nameRu'][:50]:<50} [{pat}]")
        if len(results) > 50:
            print(f"  … и ещё {len(results) - 50}")


if __name__ == "__main__":
    main()
