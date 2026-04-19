"""
migrate_json_to_db.py — заливка JSON-артефактов в Postgres.

Источники:
  exercisedb_data/exercise_db_final.json  → exercises
  training-skill/assets/info_boxes.json   → info_boxes
  training-skill/output/plan_andrey_v5.json → clients + plans + weeks + days + ...

Использование:
  # первый раз — создаём таблицы:
  python scripts/migrate_json_to_db.py --create-tables

  # миграция с очисткой существующих данных:
  python scripts/migrate_json_to_db.py --wipe

  # миграция без очистки (idempotent где возможно):
  python scripts/migrate_json_to_db.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path чтобы импорт db.* работал
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete

from db import engine, SessionLocal, models as M
from db.models import Base

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
EX_DB_F = ROOT / "exercisedb_data" / "exercise_db_final.json"
INFO_F = ROOT / "training-skill" / "assets" / "info_boxes.json"
PLAN_F = ROOT / "training-skill" / "output" / "plan_andrey_v5.json"


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
_SUFFIX_RE = re.compile(r"^(.+?)\s*\(([^)]+)\)\s*$")


def extract_qualifier(name: str) -> str | None:
    """Извлечь квалификатор в скобках (A1 суперсета, ротация, дилоуд...)."""
    if not name:
        return None
    m = _SUFFIX_RE.match(name.strip())
    if not m:
        return None
    inner = m.group(2).strip()
    if any(k in inner.lower() for k in ["a1", "a2", "b1", "b2", "c1", "c2", "суперсет", "ротация", "дилоуд", "альтернатив"]):
        return inner
    return None


# ----------------------------------------------------------------------
# migrate
# ----------------------------------------------------------------------
def migrate_exercises(session, data):
    session.execute(delete(M.Exercise))
    for ex in data:
        session.add(M.Exercise(
            exercise_id=ex["exerciseId"],
            name_en=ex.get("nameEn", ""),
            name_ru=ex.get("nameRu", ""),
            instructions=ex.get("instructions", []),
            target_muscles=ex.get("targetMuscles", []),
            body_parts=ex.get("bodyParts", []),
            equipments=ex.get("equipments", []),
            secondary_muscles=ex.get("secondaryMuscles", []),
            movement_patterns=ex.get("movementPatterns", []),
            has_animation=ex.get("hasAnimation", True),
        ))
    session.flush()
    print(f"  exercises: {len(data)}")


def migrate_info_boxes(session, data):
    session.execute(delete(M.InfoBox))
    for iid, d in data.items():
        session.add(M.InfoBox(
            id=iid,
            title=d.get("title", ""),
            body=d.get("body", ""),
            source=d.get("source"),
        ))
    session.flush()
    print(f"  info_boxes: {len(data)}")


def migrate_plan(session, plan_data):
    client_data = plan_data.get("client", {})
    program = plan_data.get("program", {})

    # Клиент — ищем по имени, если нет — создаём
    client = session.query(M.Client).filter_by(name=client_data.get("name", "")).first()
    if not client:
        client = M.Client(
            name=client_data.get("name", "Unknown"),
            age=client_data.get("age"),
            height_cm=client_data.get("height_cm"),
            weight_kg=client_data.get("weight_kg"),
            gender=client_data.get("gender"),
            experience=client_data.get("experience"),
            goal=client_data.get("goal"),
            training_days=client_data.get("training_days"),
            location=client_data.get("location"),
            injuries=client_data.get("injuries", []),
            injury_details=client_data.get("injury_details"),
        )
        session.add(client)
        session.flush()

    # Удаляем старые планы этого клиента (перезаливка)
    session.execute(delete(M.Plan).where(M.Plan.client_id == client.id))
    session.flush()

    # Plan
    plan = M.Plan(
        client_id=client.id,
        mesocycle_num=1,
        split_type=program.get("split_type"),
        total_weeks=program.get("weeks", 4),
        deload_week=program.get("deload_week"),
        goal=program.get("goal"),
        scientific_basis=program.get("scientific_basis"),
        progression_note=program.get("progression"),
        program_meta={k: v for k, v in program.items()
                      if k not in ("split_type", "weeks", "deload_week", "goal",
                                   "scientific_basis", "progression", "training_history")},
        training_history=program.get("training_history", {}),
        warmups_info_box=plan_data.get("warmups_info_box"),
        cooldowns_info_box=plan_data.get("cooldowns_info_box"),
    )
    session.add(plan)
    session.flush()

    # Warmup / Cooldown варианты
    for variant, obj in (plan_data.get("warmups") or {}).items():
        session.add(M.WarmupVariant(
            plan_id=plan.id,
            variant=variant,
            total_min=obj.get("total_min"),
            blocks=obj.get("blocks", []),
        ))
    for variant, obj in (plan_data.get("cooldowns") or {}).items():
        session.add(M.CooldownVariant(
            plan_id=plan.id,
            variant=variant,
            total_min=obj.get("total_min"),
            blocks=obj.get("blocks", []),
        ))
    session.flush()

    # Weeks → Days → PlanExercises → Alternatives
    for week_data in plan_data.get("weeks", []):
        week = M.Week(
            plan_id=plan.id,
            week_num=week_data["week_number"],
            focus=week_data.get("focus"),
            is_deload=(week_data["week_number"] == program.get("deload_week")),
            info_box_id=week_data.get("info_box"),
        )
        session.add(week)
        session.flush()

        for day_data in week_data.get("days", []):
            day = M.Day(
                week_id=week.id,
                day_num=day_data["day_number"],
                name=day_data.get("name"),
                name_ru=day_data.get("nameRu"),
                focus=day_data.get("focus"),
                warmup_type=day_data.get("warmup_type"),
                cooldown_type=day_data.get("cooldown_type"),
                info_box_id=day_data.get("info_box"),
            )
            session.add(day)
            session.flush()

            for order, ex_data in enumerate(day_data.get("exercises", []), 1):
                plan_ex = M.PlanExercise(
                    day_id=day.id,
                    order=order,
                    exercise_ref=ex_data["exerciseId"],
                    display_qualifier=extract_qualifier(ex_data.get("nameRu", "")),
                    sets=ex_data.get("sets"),
                    reps=str(ex_data["reps"]) if ex_data.get("reps") is not None else None,
                    rest_sec=ex_data.get("rest_sec"),
                    rpe=str(ex_data["rpe"]) if ex_data.get("rpe") else None,
                    tempo=ex_data.get("tempo"),
                    tips=ex_data.get("tips"),
                    warning=ex_data.get("warning"),
                    hr_target=ex_data.get("hr_target"),
                    info_box_id=ex_data.get("info_box"),
                    extra={k: v for k, v in ex_data.items()
                           if k not in ("exerciseId", "nameRu", "sets", "reps", "rest_sec", "rpe",
                                        "tempo", "tips", "warning", "hr_target", "info_box",
                                        "alternatives", "gifUrl", "gifLocalPath")},
                )
                session.add(plan_ex)
                session.flush()

                for a_order, alt_data in enumerate(ex_data.get("alternatives", []) or [], 1):
                    if not alt_data.get("exerciseId"):
                        continue
                    session.add(M.PlanAlternative(
                        plan_exercise_id=plan_ex.id,
                        order=a_order,
                        exercise_ref=alt_data["exerciseId"],
                        tips=alt_data.get("tips"),
                        warning=alt_data.get("warning"),
                    ))
                session.flush()

    # Training history — уже в plan.training_history (сохранено выше)
    print(f"  plan: {plan.id} (client: {client.name})")


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--create-tables", action="store_true", help="CREATE TABLE IF NOT EXISTS для всех моделей")
    ap.add_argument("--wipe", action="store_true", help="Очистить существующие данные перед миграцией")
    args = ap.parse_args()

    if args.create_tables:
        print("Создаю таблицы…")
        Base.metadata.create_all(engine)
        print("Таблицы готовы.")

    session = SessionLocal()
    try:
        print("Заливаю данные…")

        print("→ exercises")
        migrate_exercises(session, json.loads(EX_DB_F.read_text(encoding="utf-8")))

        print("→ info_boxes")
        migrate_info_boxes(session, json.loads(INFO_F.read_text(encoding="utf-8")))

        print("→ plan_andrey_v5")
        migrate_plan(session, json.loads(PLAN_F.read_text(encoding="utf-8")))

        session.commit()
        print("Готово.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
