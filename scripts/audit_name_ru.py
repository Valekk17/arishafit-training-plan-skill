"""
Аудит качества nameRu в exercise_db_final.json.

Категории проблем:
  A. Пустое / None nameRu
  B. nameRu == nameEn (не переведено)
  C. nameRu короче 5 символов
  D. nameRu без кириллицы (латиница / транслитерация вместо перевода)
  E. nameRu содержит явные артефакты транслитерации (zh, ch, sh, kh в русском контексте)

Группирует находки по movementPatterns + targetMuscles → облегчает батч-перевод
(движения одной группы получают консистентную терминологию).

Output: stdout report + JSON dump в exercisedb_data/audit/name_ru_issues.json
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

CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
# Транслит-маркеры: z/sh/ch/kh/yo/tsy — почти всегда артефакт машинного перевода en→ru
TRANSLIT_MARKERS = re.compile(r"\b(?:zh|sh|ch|kh|yo|ya|yu|ts|ij)\w*\b", re.IGNORECASE)


def classify(ex: dict) -> list[str]:
    """Вернуть список кодов проблем (A..E) для данного упражнения."""
    issues: list[str] = []
    name_ru = ex.get("nameRu")
    name_en = ex.get("nameEn", "")

    if not name_ru:
        issues.append("A_empty")
        return issues

    name_ru = name_ru.strip()

    if name_ru == name_en.strip():
        issues.append("B_same_as_en")

    if len(name_ru) < 5:
        issues.append("C_too_short")

    if not CYRILLIC_RE.search(name_ru):
        issues.append("D_no_cyrillic")

    # E — кириллица есть, но и латинские транслит-маркеры тоже: редкий случай (смешанный)
    if CYRILLIC_RE.search(name_ru) and TRANSLIT_MARKERS.search(name_ru):
        issues.append("E_mixed_translit")

    return issues


def main() -> None:
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} exercises from {DB_PATH.name}")

    problems: list[dict] = []
    issue_counter: Counter[str] = Counter()
    by_pattern: dict[str, list[dict]] = defaultdict(list)

    for ex in data:
        codes = classify(ex)
        if not codes:
            continue

        for c in codes:
            issue_counter[c] += 1

        entry = {
            "exerciseId": ex["exerciseId"],
            "nameEn": ex.get("nameEn"),
            "nameRu": ex.get("nameRu"),
            "movementPatterns": ex.get("movementPatterns", []),
            "targetMuscles": ex.get("targetMuscles", []),
            "bodyParts": ex.get("bodyParts", []),
            "equipments": ex.get("equipments", []),
            "issues": codes,
        }
        problems.append(entry)

        # Группировка по первому movement pattern (или "unknown")
        patterns = ex.get("movementPatterns") or ["_unclassified"]
        by_pattern[patterns[0]].append(entry)

    total_problematic = len(problems)
    print(f"\n=== SUMMARY ===")
    print(f"Total problematic: {total_problematic} / {len(data)}  "
          f"({100 * total_problematic / len(data):.1f}%)")
    print(f"\nBy issue code:")
    for code, n in sorted(issue_counter.items()):
        print(f"  {code}: {n}")

    print(f"\nBy movement pattern (top 15):")
    pattern_sizes = sorted(by_pattern.items(), key=lambda kv: -len(kv[1]))
    for pat, items in pattern_sizes[:15]:
        print(f"  {pat:30s} {len(items):4d} problematic")

    # Sample по каждой категории (первые 5)
    print(f"\n=== SAMPLES per category ===")
    by_code: dict[str, list[dict]] = defaultdict(list)
    for p in problems:
        for c in p["issues"]:
            by_code[c].append(p)

    for code in sorted(by_code.keys()):
        print(f"\n[{code}] — {len(by_code[code])} total")
        for s in by_code[code][:5]:
            print(f"  {s['exerciseId']:10s} | EN: {s['nameEn'][:50]:50s} | RU: {s['nameRu']}")

    # Dump полный JSON для следующего шага (батч-перевод)
    out_file = OUT_DIR / "name_ru_issues.json"
    out_file.write_text(
        json.dumps({
            "summary": {
                "total_db": len(data),
                "total_problematic": total_problematic,
                "by_code": dict(issue_counter),
                "by_pattern": {k: len(v) for k, v in by_pattern.items()},
            },
            "problems": problems,
            "grouped_by_pattern": dict(by_pattern),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] Full report: {out_file}")


if __name__ == "__main__":
    main()
