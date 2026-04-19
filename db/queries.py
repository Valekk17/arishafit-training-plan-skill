"""
Helper-функции для чтения каталога упражнений и справок из Postgres.

Архитектура: БД — источник правды. Эти функции дают удобный доступ
к каталогу без прямого SQLAlchemy в каждом скрипте скилла.

Скрипты (fill_template.py, build_safe_pool.py, query_exercises.py)
не читают JSON напрямую. Только через функции отсюда.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from .session import SessionLocal
from . import models as M


# ======================================================================
# EXERCISES
# ======================================================================

@lru_cache(maxsize=1)
def load_all_exercises() -> dict:
    """Загрузить весь каталог упражнений в dict {id: data}.

    Кэшируется на время жизни процесса. Для rerun нужно вызвать
    load_all_exercises.cache_clear().

    Возвращает None если БД недоступна — вызывающая сторона может
    сделать fallback на JSON.
    """
    try:
        with SessionLocal() as s:
            rows = s.scalars(select(M.Exercise)).all()
    except OperationalError:
        return {}

    return {
        ex.exercise_id: {
            "exerciseId": ex.exercise_id,
            "nameEn": ex.name_en,
            "nameRu": ex.name_ru,
            "instructions": ex.instructions,
            "targetMuscles": ex.target_muscles,
            "bodyParts": ex.body_parts,
            "equipments": ex.equipments,
            "secondaryMuscles": ex.secondary_muscles,
            "movementPatterns": ex.movement_patterns,
            "hasAnimation": ex.has_animation,
        }
        for ex in rows
    }


def get_exercise(exercise_id: str) -> Optional[dict]:
    """Одно упражнение по id."""
    return load_all_exercises().get(exercise_id)


def find_exercises(
    *,
    target_muscle: Optional[str] = None,
    body_part: Optional[str] = None,
    equipment: Optional[str] = None,
    movement_pattern: Optional[str] = None,
    has_animation: bool = True,
) -> list[dict]:
    """Поиск упражнений по фильтрам. EN-поля в БД, input тоже EN."""
    stmt = select(M.Exercise)
    if has_animation is not None:
        stmt = stmt.where(M.Exercise.has_animation == has_animation)
    if target_muscle:
        stmt = stmt.where(M.Exercise.target_muscles.any(target_muscle))
    if body_part:
        stmt = stmt.where(M.Exercise.body_parts.any(body_part))
    if equipment:
        stmt = stmt.where(M.Exercise.equipments.any(equipment))
    if movement_pattern:
        stmt = stmt.where(M.Exercise.movement_patterns.any(movement_pattern))

    with SessionLocal() as s:
        rows = s.scalars(stmt).all()

    return [
        {
            "exerciseId": ex.exercise_id,
            "nameEn": ex.name_en,
            "nameRu": ex.name_ru,
            "targetMuscles": ex.target_muscles,
            "bodyParts": ex.body_parts,
            "equipments": ex.equipments,
            "movementPatterns": ex.movement_patterns,
            "hasAnimation": ex.has_animation,
        }
        for ex in rows
    ]


# ======================================================================
# INFO BOXES
# ======================================================================

@lru_cache(maxsize=1)
def load_all_info_boxes() -> dict:
    """Загрузить все справки в dict {id: {title, body, source}}."""
    try:
        with SessionLocal() as s:
            rows = s.scalars(select(M.InfoBox)).all()
    except OperationalError:
        return {}

    return {
        ib.id: {"title": ib.title, "body": ib.body, "source": ib.source or ""}
        for ib in rows
    }


def get_info_box(info_id: str) -> Optional[dict]:
    """Одна справка по id."""
    return load_all_info_boxes().get(info_id)


# ======================================================================
# DB AVAILABILITY
# ======================================================================

def is_db_available() -> bool:
    """Проверка что БД поднята и отвечает."""
    try:
        with SessionLocal() as s:
            s.execute(select(1))
        return True
    except OperationalError:
        return False
