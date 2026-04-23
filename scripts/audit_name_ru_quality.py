"""
Глубокий аудит качества nameRu: ищем не формальные нули, а признаки
непрофессионального / машинно-буквального перевода.

Категории:
  Q1. Слишком длинное имя (>60 chars) — буквальный перевод
  Q2. Дублирующиеся nameRu (разные exerciseId → одно nameRu)
  Q3. Подозрительные паттерны в начале/конце:
      "Упражнение ", "... упражнение", "... техника", "... вариация"
  Q4. Использование "и", "с помощью", "по направлению" (калька с английского)
  Q5. Неидиоматичные конструкции: "в стиле ...", "с использованием ..."
  Q6. Отсутствие устоявшихся терминов там где они должны быть
       (например "жим" вместо "нажим", "тяга" вместо "тянуть")
  Q7. Hasanimation:false проверка — static references должны быть очевидны
  Q8. Content-length ratio: len(nameRu) / len(nameEn) > 2.0 — раздутый перевод

Также: дистрибуция длины + список самых длинных имен (визуальный review).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "exercisedb_data" / "exercise_db_final.json"
OUT_DIR = REPO / "exercisedb_data" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Паттерны буквального / слабого перевода
LITERAL_PATTERNS = [
    (r"\s+с\s+помощью\s+", "калька 'with the help of'"),
    (r"\s+по\s+направлению\s+", "калька 'in direction of'"),
    (r"\s+с\s+использованием\s+", "бюрократ. 'using'"),
    (r"\s+в\s+стиле\s+", "калька 'in the style of'"),
    (r"^Упражнение\s+", "начинается с 'Упражнение...'"),
    (r"\s+упражнение$", "заканчивается на '...упражнение'"),
    (r"\s+вариация$", "заканчивается на '...вариация' (должно: вариант)"),
    (r"\s+техника$", "заканчивается на '...техника'"),
    (r"^Как\s+", "начинается с 'Как' (инструкция, не имя)"),
]


def audit_exercise(ex: dict) -> list[tuple[str, str]]:
    """Вернуть (code, detail) issues для одного упражнения."""
    issues: list[tuple[str, str]] = []
    name_ru = (ex.get("nameRu") or "").strip()
    name_en = (ex.get("nameEn") or "").strip()

    if not name_ru or not name_en:
        return issues

    # Q1 — слишком длинное
    if len(name_ru) > 60:
        issues.append(("Q1_too_long", f"{len(name_ru)} chars"))

    # Q3, Q4, Q5 — паттерны буквального перевода
    for pat, desc in LITERAL_PATTERNS:
        if re.search(pat, name_ru, re.IGNORECASE):
            issues.append(("Q3_literal_pattern", desc))

    # Q8 — раздутый перевод относительно оригинала
    if len(name_en) >= 10 and len(name_ru) / len(name_en) > 2.0:
        issues.append(("Q8_bloated", f"ru/en ratio = {len(name_ru)/len(name_en):.2f}"))

    return issues


def main() -> None:
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} exercises")

    issue_counter: Counter[str] = Counter()
    per_ex_issues: dict[str, list[tuple[str, str]]] = {}
    lengths: list[tuple[str, int, int]] = []  # (id, len_ru, len_en)

    for ex in data:
        codes = audit_exercise(ex)
        name_ru = (ex.get("nameRu") or "").strip()
        name_en = (ex.get("nameEn") or "").strip()
        lengths.append((ex["exerciseId"], len(name_ru), len(name_en)))

        if codes:
            per_ex_issues[ex["exerciseId"]] = codes
            for c, _ in codes:
                issue_counter[c] += 1

    # Q2 — дубликаты nameRu
    name_ru_to_ids: dict[str, list[str]] = defaultdict(list)
    for ex in data:
        nr = (ex.get("nameRu") or "").strip()
        if nr:
            name_ru_to_ids[nr].append(ex["exerciseId"])
    duplicates = {nr: ids for nr, ids in name_ru_to_ids.items() if len(ids) > 1}

    print(f"\n=== ISSUE COUNTS ===")
    for code, n in sorted(issue_counter.items()):
        print(f"  {code}: {n}")

    print(f"\nТотал упражнений с минимум 1 issue: {len(per_ex_issues)} / {len(data)}"
          f"  ({100*len(per_ex_issues)/len(data):.1f}%)")

    print(f"\n=== DUPLICATE nameRu (Q2) ===")
    print(f"Unique дубль-групп: {len(duplicates)}")
    for nr, ids in sorted(duplicates.items(), key=lambda kv: -len(kv[1]))[:10]:
        print(f"  {len(ids)}× '{nr}': {', '.join(ids[:5])}{'...' if len(ids) > 5 else ''}")

    print(f"\n=== TOP 15 LONGEST nameRu ===")
    lengths.sort(key=lambda t: -t[1])
    # Нужен доступ к самим именам
    by_id = {ex["exerciseId"]: ex for ex in data}
    for eid, lr, le in lengths[:15]:
        ex = by_id[eid]
        print(f"  [{lr:3d} ch] {eid} | {ex.get('nameRu')}")
        print(f"            EN: {ex.get('nameEn')}")

    print(f"\n=== SAMPLES per Q-code ===")
    by_code: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for eid, codes in per_ex_issues.items():
        for c, detail in codes:
            by_code[c].append((eid, detail, by_id[eid]))

    for code in sorted(by_code.keys()):
        print(f"\n[{code}] — {len(by_code[code])} total")
        for eid, detail, ex in by_code[code][:8]:
            print(f"  {eid} ({detail}) | {ex.get('nameRu')[:80]}")
            print(f"                              EN: {ex.get('nameEn')[:80]}")

    # Dump for batch processing
    out_file = OUT_DIR / "name_ru_quality_issues.json"
    out_file.write_text(
        json.dumps({
            "summary": {
                "total_db": len(data),
                "total_with_issues": len(per_ex_issues),
                "by_code": dict(issue_counter),
                "duplicate_groups": len(duplicates),
            },
            "duplicates": duplicates,
            "per_ex_issues": {
                eid: {
                    "issues": codes,
                    "nameEn": by_id[eid].get("nameEn"),
                    "nameRu": by_id[eid].get("nameRu"),
                    "movementPatterns": by_id[eid].get("movementPatterns", []),
                    "targetMuscles": by_id[eid].get("targetMuscles", []),
                    "equipments": by_id[eid].get("equipments", []),
                } for eid, codes in per_ex_issues.items()
            },
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] Report: {out_file}")


if __name__ == "__main__":
    main()
