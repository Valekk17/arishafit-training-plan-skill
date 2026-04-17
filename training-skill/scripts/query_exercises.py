"""
query_exercises.py — Запрос упражнений из PostgreSQL для генерации тренировочного плана.

Вход: JSON с параметрами клиента (травмы, оборудование, уровень, цель)
Выход: JSON с отфильтрованными упражнениями, сгруппированными по мышечным группам

Использование:
    python query_exercises.py --input client_params.json --output exercises.json
    python query_exercises.py --injuries hernia_lumbar --equipment barbell,dumbbell,cable,machine --level intermediate
"""

import json
import subprocess
import sys
import argparse
import os

# =====================================================
# КОНФИГУРАЦИЯ PostgreSQL (Docker)
# =====================================================
DB_CONTAINER = "arishafit-postgres"
DB_USER = "arishafit"
DB_NAME = "exercise_db"


def psql_query(sql):
    """Выполнить SQL запрос и вернуть результат как список словарей."""
    # Используем формат CSV для парсинга
    full_sql = f"COPY ({sql}) TO STDOUT WITH CSV HEADER;"
    result = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-c", full_sql],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        # Fallback: обычный запрос
        result = subprocess.run(
            ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
             "-t", "-A", "-F", "|", "-c", sql],
            capture_output=True, text=True, encoding="utf-8"
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        return lines

    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        return []

    import csv
    from io import StringIO
    reader = csv.DictReader(StringIO(result.stdout))
    return list(reader)


def psql_simple(sql):
    """Выполнить SQL и вернуть сырой вывод."""
    result = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def get_forbidden_exercise_ids(injury_slugs):
    """Получить ID упражнений, запрещённых для данных травм (severity = 'forbidden')."""
    if not injury_slugs:
        return set()

    slugs_sql = ",".join(f"'{s}'" for s in injury_slugs)
    sql = f"""
    SELECT DISTINCT e.exercise_id
    FROM exercise_contraindications ec
    JOIN injury_types it ON ec.injury_id = it.id
    JOIN exercises e ON ec.exercise_id = e.id
    WHERE it.slug IN ({slugs_sql})
    AND ec.severity = 'forbidden'
    """
    result = psql_simple(sql)
    return set(result.split("\n")) if result else set()


def get_caution_exercises(injury_slugs):
    """Получить упражнения с предупреждениями (caution/modification_needed)."""
    if not injury_slugs:
        return {}

    slugs_sql = ",".join(f"'{s}'" for s in injury_slugs)
    sql = f"""
    SELECT e.exercise_id, it.slug as injury, ec.severity, ec.note
    FROM exercise_contraindications ec
    JOIN injury_types it ON ec.injury_id = it.id
    JOIN exercises e ON ec.exercise_id = e.id
    WHERE it.slug IN ({slugs_sql})
    AND ec.severity IN ('caution', 'modification_needed')
    """
    result = psql_simple(sql)
    cautions = {}
    for line in result.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                eid = parts[0]
                if eid not in cautions:
                    cautions[eid] = []
                cautions[eid].append({
                    "injury": parts[1],
                    "severity": parts[2],
                    "note": parts[3]
                })
    return cautions


def get_available_equipment_ids(equipment_slugs):
    """Получить ID оборудования по slug'ам."""
    if not equipment_slugs:
        return None  # None = все оборудование доступно

    slugs_sql = ",".join(f"'{s}'" for s in equipment_slugs)
    sql = f"SELECT id FROM equipment WHERE slug IN ({slugs_sql})"
    result = psql_simple(sql)
    return set(result.split("\n")) if result else set()


def query_exercises(injuries=None, equipment_slugs=None, level=None, goal=None):
    """
    Основной запрос: получить подходящие упражнения.

    Args:
        injuries: список slug'ов травм клиента (hernia_lumbar, shoulder_impingement, etc.)
        equipment_slugs: список slug'ов оборудования (barbell, dumbbell, cable, machine, body_weight, etc.)
                         None = всё оборудование доступно (зал)
        level: beginner / intermediate / advanced
        goal: hypertrophy / strength / endurance / weight_loss / maintenance

    Returns:
        dict с упражнениями, сгруппированными по bodyPart → targetMuscle
    """

    # 1. Получить запрещённые упражнения
    forbidden_ids = get_forbidden_exercise_ids(injuries or [])

    # 2. Получить предупреждения
    cautions = get_caution_exercises(injuries or [])

    # 3. Основной запрос — все упражнения с данными
    sql = """
    SELECT
        e.id,
        e.exercise_id,
        e.name_en,
        e.name_ru,
        e.description_ru,
        e.technique_tips,
        e.common_mistakes,
        e.breathing,
        e.difficulty,
        e.exercise_type,
        e.force_type,
        e.gif_url,
        e.gif_local_path
    FROM exercises e
    WHERE e.exercise_type IS NOT NULL
    """

    # Фильтр по уровню: beginner видит beginner, intermediate видит beginner+intermediate, etc.
    if level == "beginner":
        sql += " AND e.difficulty IN ('beginner')"
    elif level == "intermediate":
        sql += " AND e.difficulty IN ('beginner', 'intermediate')"
    # advanced видит всё

    sql += " ORDER BY e.name_ru"

    raw_exercises = psql_simple(sql)

    # 4. Получить связи: мышцы, оборудование, паттерны
    muscles_sql = """
    SELECT em.exercise_id, m.name_en, m.body_part, em.role
    FROM exercise_muscles em
    JOIN muscles m ON em.muscle_id = m.id
    """
    muscles_raw = psql_simple(muscles_sql)
    muscle_map = {}  # exercise_db_id → [{"muscle": ..., "body_part": ..., "role": ...}]
    for line in muscles_raw.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                eid = parts[0]
                if eid not in muscle_map:
                    muscle_map[eid] = []
                muscle_map[eid].append({
                    "muscle": parts[1],
                    "bodyPart": parts[2],
                    "role": parts[3]
                })

    equipment_sql = """
    SELECT ee.exercise_id, eq.slug, eq.name_ru
    FROM exercise_equipment ee
    JOIN equipment eq ON ee.equipment_id = eq.id
    """
    equip_raw = psql_simple(equipment_sql)
    equip_map = {}
    for line in equip_raw.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                eid = parts[0]
                if eid not in equip_map:
                    equip_map[eid] = []
                equip_map[eid].append({"slug": parts[1], "nameRu": parts[2]})

    patterns_sql = """
    SELECT ep.exercise_id, mp.slug
    FROM exercise_patterns ep
    JOIN movement_patterns mp ON ep.pattern_id = mp.id
    """
    patterns_raw = psql_simple(patterns_sql)
    pattern_map = {}
    for line in patterns_raw.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 2:
                eid = parts[0]
                if eid not in pattern_map:
                    pattern_map[eid] = []
                pattern_map[eid].append(parts[1])

    # 5. Собрать финальный список
    exercises = []
    available_equip = set(equipment_slugs) if equipment_slugs else None

    for line in raw_exercises.split("\n"):
        if "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 13:
            continue

        db_id = parts[0]
        exercise_id = parts[1]

        # Пропустить forbidden
        if db_id in forbidden_ids or exercise_id in forbidden_ids:
            continue

        # ЖЁСТКИЙ ФИЛЬТР по movement patterns + травмы
        patterns = pattern_map.get(db_id, [])
        injury_set = set(injuries or [])
        pattern_blocked = False

        if injury_set & {"hernia_lumbar", "protrusion_lumbar"}:
            # При грыже поясницы — запретить опасные паттерны
            if "axial_load" in patterns:
                pattern_blocked = True  # штанга на спине/плечах
            if "back_flexion" in patterns:
                pattern_blocked = True  # сгибание поясницы под весом
            if "rotation_under_load" in patterns:
                pattern_blocked = True  # ротация корпуса с весом
            if "impact" in patterns:
                pattern_blocked = True  # прыжки, плиометрика
            # hip_hinge допустим ТОЛЬКО если есть supported_back (мост, тренажёр)
            if "hip_hinge" in patterns and "supported_back" not in patterns:
                pattern_blocked = True

        if "shoulder_impingement" in injury_set or "rotator_cuff_tear" in injury_set:
            # При проблемах с плечом — запретить overhead без опоры
            if "overhead" in patterns and "supported_back" not in patterns:
                pattern_blocked = True

        if injury_set & {"knee_meniscus", "knee_acl"}:
            if "impact" in patterns:
                pattern_blocked = True  # прыжки запрещены

        if "hypertension" in injury_set:
            # Нет упражнений вниз головой — проверяем через название
            name_lower = parts[2].lower() if len(parts) > 2 else ""
            if "decline" in name_lower or "headstand" in name_lower or "handstand" in name_lower:
                pattern_blocked = True

        if "obesity_severe" in injury_set:
            if "impact" in patterns:
                pattern_blocked = True

        if "diastasis_recti" in injury_set:
            if "back_flexion" in patterns:
                pattern_blocked = True

        if pattern_blocked:
            continue

        # Проверить оборудование
        ex_equips = equip_map.get(db_id, [])
        if available_equip:
            equip_slugs_ex = [e["slug"] for e in ex_equips]
            # Упражнение подходит если хотя бы одно его оборудование доступно
            # Или если это body_weight (всегда доступно)
            if not any(es in available_equip or es == "body_weight" for es in equip_slugs_ex):
                continue

        # Получить мышцы
        muscles = muscle_map.get(db_id, [])
        primary_muscles = [m for m in muscles if m["role"] == "primary"]
        secondary_muscles = [m for m in muscles if m["role"] == "secondary"]

        # Получить паттерны
        patterns = pattern_map.get(db_id, [])

        # Предупреждения
        warnings = cautions.get(db_id, []) + cautions.get(exercise_id, [])

        ex = {
            "id": exercise_id,
            "nameEn": parts[2],
            "nameRu": parts[3] if parts[3] else parts[2],
            "descriptionRu": parts[4] if parts[4] else None,
            "techniqueTips": parts[5] if parts[5] else None,
            "commonMistakes": parts[6] if parts[6] else None,
            "breathing": parts[7] if parts[7] else None,
            "difficulty": parts[8],
            "exerciseType": parts[9],
            "forceType": parts[10],
            "gifUrl": parts[11] if parts[11] else None,
            "gifLocalPath": parts[12] if parts[12] else None,
            "primaryMuscles": [m["muscle"] for m in primary_muscles],
            "secondaryMuscles": [m["muscle"] for m in secondary_muscles],
            "bodyParts": list(set(m["bodyPart"] for m in primary_muscles)),
            "equipment": ex_equips,
            "movementPatterns": patterns,
            "warnings": warnings if warnings else None,
        }

        exercises.append(ex)

    # 6. Группировка по bodyPart → targetMuscle
    grouped = {}
    for ex in exercises:
        for bp in ex.get("bodyParts", ["other"]):
            if bp not in grouped:
                grouped[bp] = {}
            for pm in ex.get("primaryMuscles", ["other"]):
                if pm not in grouped[bp]:
                    grouped[bp][pm] = []
                grouped[bp][pm].append(ex)

    # 7. Статистика
    stats = {
        "total_available": len(exercises),
        "forbidden_count": len(forbidden_ids),
        "by_body_part": {bp: sum(len(exs) for exs in muscles.values()) for bp, muscles in grouped.items()},
        "by_difficulty": {},
        "by_type": {},
    }
    for ex in exercises:
        d = ex.get("difficulty", "unknown")
        stats["by_difficulty"][d] = stats["by_difficulty"].get(d, 0) + 1
        t = ex.get("exerciseType", "unknown")
        stats["by_type"][t] = stats["by_type"].get(t, 0) + 1

    return {
        "stats": stats,
        "exercises": grouped,
        "flat": exercises,  # плоский список для удобства
    }


def main():
    parser = argparse.ArgumentParser(description="Query exercises from PostgreSQL")
    parser.add_argument("--injuries", type=str, help="Comma-separated injury slugs")
    parser.add_argument("--equipment", type=str, help="Comma-separated equipment slugs")
    parser.add_argument("--level", type=str, choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--goal", type=str, choices=["hypertrophy", "strength", "endurance", "weight_loss", "maintenance"])
    parser.add_argument("--input", type=str, help="JSON file with client params")
    parser.add_argument("--output", type=str, default="exercises_filtered.json", help="Output JSON file")

    args = parser.parse_args()

    # Если есть входной JSON
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            params = json.load(f)
        injuries = params.get("injuries", [])
        equipment = params.get("equipment", None)
        level = params.get("level", None)
        goal = params.get("goal", None)
    else:
        injuries = args.injuries.split(",") if args.injuries else []
        equipment = args.equipment.split(",") if args.equipment else None
        level = args.level
        goal = args.goal

    print(f"Querying exercises...")
    print(f"  Injuries: {injuries}")
    print(f"  Equipment: {equipment or 'ALL (gym)'}")
    print(f"  Level: {level or 'all'}")
    print(f"  Goal: {goal or 'general'}")

    result = query_exercises(
        injuries=injuries,
        equipment_slugs=equipment,
        level=level,
        goal=goal,
    )

    print(f"\n=== RESULTS ===")
    print(f"  Available exercises: {result['stats']['total_available']}")
    print(f"  Forbidden (excluded): {result['stats']['forbidden_count']}")
    print(f"  By body part:")
    for bp, count in sorted(result["stats"]["by_body_part"].items()):
        print(f"    {bp}: {count}")
    print(f"  By difficulty:")
    for d, count in sorted(result["stats"]["by_difficulty"].items()):
        print(f"    {d}: {count}")

    # Сохранить
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
