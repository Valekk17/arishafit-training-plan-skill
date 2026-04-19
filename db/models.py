"""
SQLAlchemy модели ArishaFit — каноническая схема PostgreSQL 16.

Архитектура:
  - exercises              каталог 1500 упражнений (read-only reference)
  - clients                клиенты с анкетой и травмами
  - plans                  мезоциклы (4 недели обычно) — attached к клиенту
  - weeks                  недели плана с focus/info_box
  - days                   дни недели (силовая / кардио / ...) с warmup_type/cooldown_type
  - plan_exercises         упражнения в дне (основные)
  - plan_alternatives      альтернативы к основному упражнению
  - plan_warmup_variants   варианты разминок плана (strength/cardio) как JSONB blocks
  - plan_cooldown_variants то же для заминок
  - info_boxes             библиотека научных справок (key=string id)
  - session_logs           фактические тренировки клиента (клиент отметил «сделано»)
  - exercise_logs          фактические веса/повторения в подходах
  - 1rm_estimates          вычисленные или записанные 1RM по упражнениям

JSONB используется для:
  - client.injuries, client.injury_details (оставляем гибкость)
  - warmup/cooldown blocks (they have nested phase+items structure)
  - plan_exercise tips (rich text)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ======================================================================
# КАТАЛОГ УПРАЖНЕНИЙ (из ExerciseDB, обогащённый Opus-именами)
# ======================================================================

class Exercise(Base):
    __tablename__ = "exercises"

    exercise_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    target_muscles: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    body_parts: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    equipments: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    secondary_muscles: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    movement_patterns: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    has_animation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ======================================================================
# БИБЛИОТЕКА СПРАВОК
# ======================================================================

class InfoBox(Base):
    __tablename__ = "info_boxes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # ключ типа "zone2_continuous"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # HTML-контент
    source: Mapped[Optional[str]] = mapped_column(Text)


# ======================================================================
# КЛИЕНТЫ
# ======================================================================

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer)
    weight_kg: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2))
    gender: Mapped[Optional[str]] = mapped_column(String(16))
    experience: Mapped[Optional[str]] = mapped_column(String(32))  # beginner/intermediate/advanced
    goal: Mapped[Optional[str]] = mapped_column(String(64))
    training_days: Mapped[Optional[int]] = mapped_column(Integer)
    location: Mapped[Optional[str]] = mapped_column(String(64))
    injuries: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    injury_details: Mapped[Optional[str]] = mapped_column(Text)
    profile_extra: Mapped[dict] = mapped_column(JSONB, default=dict)  # произвольные поля
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plans: Mapped[list["Plan"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    one_rms: Mapped[list["OneRM"]] = relationship(back_populates="client", cascade="all, delete-orphan")


# ======================================================================
# ПЛАН = МЕЗОЦИКЛ
# ======================================================================

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    mesocycle_num: Mapped[int] = mapped_column(Integer, default=1)  # номер мезоцикла в рамках клиента
    split_type: Mapped[Optional[str]] = mapped_column(String(128))
    total_weeks: Mapped[int] = mapped_column(Integer, default=4)
    deload_week: Mapped[Optional[int]] = mapped_column(Integer)
    goal: Mapped[Optional[str]] = mapped_column(String(64))
    scientific_basis: Mapped[Optional[str]] = mapped_column(Text)
    progression_note: Mapped[Optional[str]] = mapped_column(Text)
    program_meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # max_hr, zone2_target, fat_loss_features и т.п.
    training_history: Mapped[dict] = mapped_column(JSONB, default=dict)  # последние рабочие веса

    # Ссылки на справки для секций
    warmups_info_box: Mapped[Optional[str]] = mapped_column(ForeignKey("info_boxes.id", ondelete="SET NULL"))
    cooldowns_info_box: Mapped[Optional[str]] = mapped_column(ForeignKey("info_boxes.id", ondelete="SET NULL"))

    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="active")  # active / completed / abandoned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="plans")
    weeks: Mapped[list["Week"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="Week.week_num")
    warmup_variants: Mapped[list["WarmupVariant"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    cooldown_variants: Mapped[list["CooldownVariant"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    week_num: Mapped[int] = mapped_column(Integer, nullable=False)
    focus: Mapped[Optional[str]] = mapped_column(Text)
    is_deload: Mapped[bool] = mapped_column(Boolean, default=False)
    info_box_id: Mapped[Optional[str]] = mapped_column(ForeignKey("info_boxes.id", ondelete="SET NULL"))

    plan: Mapped["Plan"] = relationship(back_populates="weeks")
    days: Mapped[list["Day"]] = relationship(back_populates="week", cascade="all, delete-orphan", order_by="Day.day_num")


class Day(Base):
    __tablename__ = "days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False)
    day_num: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(128))
    name_ru: Mapped[Optional[str]] = mapped_column(String(255))
    focus: Mapped[Optional[str]] = mapped_column(Text)
    warmup_type: Mapped[Optional[str]] = mapped_column(String(32))  # "strength" | "cardio"
    cooldown_type: Mapped[Optional[str]] = mapped_column(String(32))
    info_box_id: Mapped[Optional[str]] = mapped_column(ForeignKey("info_boxes.id", ondelete="SET NULL"))

    week: Mapped["Week"] = relationship(back_populates="days")
    exercises: Mapped[list["PlanExercise"]] = relationship(back_populates="day", cascade="all, delete-orphan", order_by="PlanExercise.order")


class PlanExercise(Base):
    __tablename__ = "plan_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)  # позиция в дне (1, 2, 3…)
    exercise_ref: Mapped[str] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False)
    # Отображаемое имя с квалификатором, напр. "(A1 суперсета)". Базовое имя — из exercises.name_ru.
    display_qualifier: Mapped[Optional[str]] = mapped_column(String(64))
    sets: Mapped[Optional[int]] = mapped_column(Integer)
    reps: Mapped[Optional[str]] = mapped_column(String(64))  # "12-15" или "30 сек"
    rest_sec: Mapped[Optional[int]] = mapped_column(Integer)
    rpe: Mapped[Optional[str]] = mapped_column(String(16))  # "7", "7.5", "7-8"
    tempo: Mapped[Optional[str]] = mapped_column(String(16))
    tips: Mapped[Optional[str]] = mapped_column(Text)
    warning: Mapped[Optional[str]] = mapped_column(Text)
    hr_target: Mapped[Optional[str]] = mapped_column(String(32))  # для кардио
    info_box_id: Mapped[Optional[str]] = mapped_column(ForeignKey("info_boxes.id", ondelete="SET NULL"))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)  # notes_progression и прочее

    day: Mapped["Day"] = relationship(back_populates="exercises")
    alternatives: Mapped[list["PlanAlternative"]] = relationship(back_populates="plan_exercise", cascade="all, delete-orphan", order_by="PlanAlternative.order")


class PlanAlternative(Base):
    __tablename__ = "plan_alternatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_exercise_id: Mapped[int] = mapped_column(ForeignKey("plan_exercises.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_ref: Mapped[str] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False)
    tips: Mapped[Optional[str]] = mapped_column(Text)
    warning: Mapped[Optional[str]] = mapped_column(Text)

    plan_exercise: Mapped["PlanExercise"] = relationship(back_populates="alternatives")


# Разминка и заминка хранятся как структурированный JSONB — blocks имеют phase+items
class WarmupVariant(Base):
    __tablename__ = "plan_warmup_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    variant: Mapped[str] = mapped_column(String(32), nullable=False)  # strength | cardio
    total_min: Mapped[Optional[int]] = mapped_column(Integer)
    blocks: Mapped[dict] = mapped_column(JSONB, default=list)  # [{phase, label, duration_min, items: [...]}]

    plan: Mapped["Plan"] = relationship(back_populates="warmup_variants")


class CooldownVariant(Base):
    __tablename__ = "plan_cooldown_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    variant: Mapped[str] = mapped_column(String(32), nullable=False)
    total_min: Mapped[Optional[int]] = mapped_column(Integer)
    blocks: Mapped[dict] = mapped_column(JSONB, default=list)

    plan: Mapped["Plan"] = relationship(back_populates="cooldown_variants")


# ======================================================================
# ФАКТ-ТРЕНИРОВОК (для будущей автопрогрессии)
# ======================================================================

class SessionLog(Base):
    """Факт выполнения тренировочного дня клиентом."""
    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    week_num: Mapped[int] = mapped_column(Integer, nullable=False)
    day_num: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_min: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ExerciseLog(Base):
    """Факт подхода/веса/повторений в одном упражнении сессии."""
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_log_id: Mapped[int] = mapped_column(ForeignKey("session_logs.id", ondelete="CASCADE"), nullable=False)
    exercise_ref: Mapped[str] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False)
    # actual_sets = список подходов вида [{"weight": 40, "reps": 12, "rpe": 7}, ...]
    actual_sets: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class OneRM(Base):
    """Вычисленный или записанный 1RM по упражнению (для прогрессии)."""
    __tablename__ = "one_rm_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    exercise_ref: Mapped[str] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False)
    one_rm_kg: Mapped[Numeric] = mapped_column(Numeric(6, 2), nullable=False)
    estimated_from: Mapped[Optional[str]] = mapped_column(String(64))  # "epley" / "manual" / "tested"
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="one_rms")
