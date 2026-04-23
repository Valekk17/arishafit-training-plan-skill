"""
Точечные правки nameRu для 3 упражнений с литеральным переводом
(категория Q3_literal_pattern из audit_name_ru_quality.py).

Правки обоснованы:
  - '8ARQ9Hw': убрать кальку 'в стиле сумо' → 'сумо' (устойчивый термин)
  - '0CXGHya': заменить 'вариация' → '(вариант)' — конвенция базы
  - 'ZgwWBoC': убрать 'в стиле байдарки' → 'тяга-гребля'
    (у kayak row важна суть движения = альтернативная гребля)
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "exercisedb_data" / "exercise_db_final.json"

FIXES: dict[str, tuple[str, str]] = {
    "8ARQ9Hw": (
        "Высокая тяга гири в стиле сумо",
        "Высокая тяга гири сумо",
    ),
    "0CXGHya": (
        "Кроссовер - вариация",
        "Кроссовер (вариант)",
    ),
    "ZgwWBoC": (
        "Тяга на блоке в стиле байдарки (Тибодо)",
        "Тяга-гребля в блоке (по Тибодо)",
    ),
}


def main() -> None:
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    applied = []
    skipped = []

    for ex in data:
        eid = ex["exerciseId"]
        if eid not in FIXES:
            continue
        old, new = FIXES[eid]
        current = ex.get("nameRu")
        if current == old:
            ex["nameRu"] = new
            applied.append((eid, old, new))
        else:
            skipped.append((eid, current, old, new))

    if skipped:
        print("[WARN] Skipped (unexpected current nameRu):")
        for eid, cur, old, new in skipped:
            print(f"  {eid}: current={cur!r}  expected={old!r}")

    if applied:
        print(f"[OK] Applying {len(applied)} fixes:")
        for eid, old, new in applied:
            # Избегаем unicode-символов в print для Windows cp1251 консоли;
            # сами строки old/new будут печататься через repr() → \uXXXX escapes
            print(f"  {eid}:")
            print(f"    old: {old!r}")
            print(f"    new: {new!r}")
        # Сохраняем с тем же форматированием что у исходника (indent=2, ensure_ascii=False)
        DB_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[OK] Saved: {DB_PATH}")
    else:
        print("[NOP] Nothing to change")


if __name__ == "__main__":
    main()
