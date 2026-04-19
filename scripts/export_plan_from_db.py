"""
export_plan_from_db.py — выгружает план клиента из Postgres в JSON того же
формата что training-skill/output/plan_andrey_v5.json.

БД — источник правды. JSON — промежуточный формат для рендера через
fill_template.py (чтобы не менять существующий рендерер).

Использование:
  python scripts/export_plan_from_db.py --client "Андрей" --output training-skill/output/plan_andrey_v5.json
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy.orm import joinedload

from db import SessionLocal, models as M

sys.stdout.reconfigure(encoding="utf-8")


def _dec(v):
    """Сериализуем Decimal → float (JSON не умеет Decimal из коробки)."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def export_client_latest_plan(session, client_name: str) -> dict:
    client = session.query(M.Client).filter_by(name=client_name).first()
    if not client:
        raise ValueError(f"Клиент '{client_name}' не найден")

    plan = (
        session.query(M.Plan)
        .filter_by(client_id=client.id)
        .order_by(M.Plan.mesocycle_num.desc(), M.Plan.id.desc())
        .first()
    )
    if not plan:
        raise ValueError(f"У клиента '{client_name}' нет планов")

    # Экспортируем в формате plan_andrey_v5.json
    out: dict = {}

    out["client"] = {
        "name": client.name,
        "age": client.age,
        "height_cm": client.height_cm,
        "weight_kg": _dec(client.weight_kg),
        "gender": client.gender,
        "experience": client.experience,
        "goal": client.goal,
        "training_days": client.training_days,
        "location": client.location,
        "injuries": list(client.injuries or []),
        "injury_details": client.injury_details or "",
    }

    program: dict = {
        "split_type": plan.split_type,
        "weeks": plan.total_weeks,
        "deload_week": plan.deload_week,
        "goal": plan.goal,
        "scientific_basis": plan.scientific_basis,
        "progression": plan.progression_note,
    }
    if plan.program_meta:
        program.update(plan.program_meta)
    if plan.training_history:
        program["training_history"] = plan.training_history
    out["program"] = program

    # Разминки / заминки
    wu = {}
    for v in plan.warmup_variants:
        wu[v.variant] = {"total_min": v.total_min, "blocks": v.blocks or []}
    if wu:
        out["warmups"] = wu
    cd = {}
    for v in plan.cooldown_variants:
        cd[v.variant] = {"total_min": v.total_min, "blocks": v.blocks or []}
    if cd:
        out["cooldowns"] = cd

    if plan.warmups_info_box:
        out["warmups_info_box"] = plan.warmups_info_box
    if plan.cooldowns_info_box:
        out["cooldowns_info_box"] = plan.cooldowns_info_box

    # Недели → дни → упражнения
    weeks_out = []
    weeks = (
        session.query(M.Week)
        .filter_by(plan_id=plan.id)
        .order_by(M.Week.week_num)
        .all()
    )
    for week in weeks:
        week_dict = {"week_number": week.week_num, "focus": week.focus or ""}
        if week.info_box_id:
            week_dict["info_box"] = week.info_box_id
        days_out = []
        days = (
            session.query(M.Day)
            .filter_by(week_id=week.id)
            .order_by(M.Day.day_num)
            .all()
        )
        for day in days:
            day_dict = {
                "day_number": day.day_num,
                "name": day.name,
                "nameRu": day.name_ru,
                "focus": day.focus,
                "warmup_type": day.warmup_type,
                "cooldown_type": day.cooldown_type,
            }
            if day.info_box_id:
                day_dict["info_box"] = day.info_box_id
            exs_out = []
            exs = (
                session.query(M.PlanExercise)
                .filter_by(day_id=day.id)
                .order_by(M.PlanExercise.order)
                .all()
            )
            for ex in exs:
                # Имя: из каталога exercises + квалификатор если есть
                ex_cat = session.get(M.Exercise, ex.exercise_ref)
                name = ex_cat.name_ru if ex_cat else ex.exercise_ref
                if ex.display_qualifier:
                    name = f"{name} ({ex.display_qualifier})"
                ex_dict = {
                    "exerciseId": ex.exercise_ref,
                    "nameRu": name,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "rest_sec": ex.rest_sec,
                    "rpe": ex.rpe,
                    "tips": ex.tips or "",
                    "warning": ex.warning or "",
                    "gifUrl": f"https://static.exercisedb.dev/media/{ex.exercise_ref}.gif",
                }
                if ex.tempo:
                    ex_dict["tempo"] = ex.tempo
                if ex.hr_target:
                    ex_dict["hr_target"] = ex.hr_target
                if ex.info_box_id:
                    ex_dict["info_box"] = ex.info_box_id
                if ex.extra:
                    ex_dict.update(ex.extra)

                # Альтернативы
                alts = (
                    session.query(M.PlanAlternative)
                    .filter_by(plan_exercise_id=ex.id)
                    .order_by(M.PlanAlternative.order)
                    .all()
                )
                alts_out = []
                for alt in alts:
                    alt_cat = session.get(M.Exercise, alt.exercise_ref)
                    alt_name = alt_cat.name_ru if alt_cat else alt.exercise_ref
                    alts_out.append({
                        "exerciseId": alt.exercise_ref,
                        "nameRu": alt_name,
                        "tips": alt.tips or "",
                        "warning": alt.warning or "",
                        "gifUrl": f"https://static.exercisedb.dev/media/{alt.exercise_ref}.gif",
                    })
                ex_dict["alternatives"] = alts_out
                exs_out.append(ex_dict)
            day_dict["exercises"] = exs_out
            days_out.append(day_dict)
        week_dict["days"] = days_out
        weeks_out.append(week_dict)
    out["weeks"] = weeks_out

    # legal — сохраняем если был в program_meta, иначе пропускаем (не критично)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True, help="Имя клиента")
    ap.add_argument("--output", required=True, help="Путь куда сохранить JSON")
    args = ap.parse_args()

    session = SessionLocal()
    try:
        data = export_client_latest_plan(session, args.client)
    finally:
        session.close()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Экспортировано: {out_path}")
    print(f"  weeks: {len(data['weeks'])}")
    print(f"  warmups: {list((data.get('warmups') or {}).keys())}")
    print(f"  cooldowns: {list((data.get('cooldowns') or {}).keys())}")


if __name__ == "__main__":
    main()
