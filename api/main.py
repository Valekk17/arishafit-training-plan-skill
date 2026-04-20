"""
ArishaFit API — FastAPI backend.

Что делает сейчас:
  GET /               → health check + версия
  GET /plans          → список всех планов (для админки)
  GET /plan/{slug}    → HTML-рендер плана клиента (для Safari/браузера)
  GET /plan/{slug}.json → JSON-версия плана (для мобильного app)
  GET /exercises      → каталог упражнений (с фильтрами)
  GET /mp4/{id}.mp4   → видео упражнения
  GET /assets/*       → статические ассеты

Локальный запуск:
  uvicorn api.main:app --reload --port 8000

Production (Railway / Fly.io):
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import sys
from pathlib import Path

# Путь к корню проекта — чтобы импорт db.* работал
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from db import SessionLocal, models as M
from db.queries import is_db_available
from scripts.export_plan_from_db import export_client_latest_plan

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "training-skill" / "templates" / "training_plan_v4.html"

app = FastAPI(
    title="ArishaFit API",
    version="0.1.0",
    description="Backend для тренировочных планов. PostgreSQL as source of truth.",
)

# Ассеты (картинки разминки, breathing.png и т.д.) раздаём из training-skill/assets
app.mount("/assets", StaticFiles(directory=str(ROOT / "training-skill" / "assets")), name="assets")


# ======================================================================
# HEALTH
# ======================================================================
@app.get("/")
def root():
    return {
        "app": "ArishaFit API",
        "version": "0.1.0",
        "db": "ok" if is_db_available() else "unavailable",
    }


# ======================================================================
# CLIENTS / PLANS
# ======================================================================
@app.get("/plans")
def list_plans():
    """Все планы со всех клиентов. Для админки тренера."""
    with SessionLocal() as s:
        rows = s.execute(
            select(M.Plan, M.Client).join(M.Client, M.Client.id == M.Plan.client_id)
        ).all()
        return [
            {
                "plan_id": p.id,
                "client_id": c.id,
                "client_name": c.name,
                "mesocycle_num": p.mesocycle_num,
                "status": p.status,
                "split_type": p.split_type,
                "weeks": p.total_weeks,
                "deload_week": p.deload_week,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p, c in rows
        ]


@app.get("/plan/{slug}.json")
def get_plan_json(slug: str):
    """JSON-версия плана — для мобильного клиента."""
    with SessionLocal() as s:
        try:
            return export_client_latest_plan(s, slug)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@app.get("/plan/{slug}", response_class=HTMLResponse)
def get_plan_html(slug: str):
    """HTML-рендер плана — открывается в Safari/Chrome напрямую."""
    # Импортируем рендерер лениво (медиа base64 тяжёлый)
    from training_skill_scripts.fill_template import fill_template  # type: ignore
    # fill_template.py лежит в training-skill/scripts/ — имя папки с дефисом,
    # импорт идёт через sys.path + alias. Делаем через runpy для надёжности.
    import importlib.util

    fill_template_path = ROOT / "training-skill" / "scripts" / "fill_template.py"
    spec = importlib.util.spec_from_file_location("fill_template", fill_template_path)
    ft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ft)

    with SessionLocal() as s:
        try:
            plan_data = export_client_latest_plan(s, slug)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    ft.USE_RELATIVE = False  # base64 embed для автономности HTML
    html = ft.fill_template(plan_data)
    return HTMLResponse(content=html)


# ======================================================================
# EXERCISES CATALOG
# ======================================================================
@app.get("/exercises")
def list_exercises(
    target_muscle: str | None = Query(None),
    body_part: str | None = Query(None),
    equipment: str | None = Query(None),
    movement_pattern: str | None = Query(None),
    has_animation: bool = True,
    limit: int = 50,
):
    """Каталог с фильтрами. Для UI выбора альтернатив."""
    stmt = select(M.Exercise)
    if has_animation:
        stmt = stmt.where(M.Exercise.has_animation == True)
    if target_muscle:
        stmt = stmt.where(M.Exercise.target_muscles.any(target_muscle))
    if body_part:
        stmt = stmt.where(M.Exercise.body_parts.any(body_part))
    if equipment:
        stmt = stmt.where(M.Exercise.equipments.any(equipment))
    if movement_pattern:
        stmt = stmt.where(M.Exercise.movement_patterns.any(movement_pattern))
    stmt = stmt.limit(limit)

    with SessionLocal() as s:
        rows = s.scalars(stmt).all()
        return [
            {
                "id": ex.exercise_id,
                "nameEn": ex.name_en,
                "nameRu": ex.name_ru,
                "targetMuscles": ex.target_muscles,
                "bodyParts": ex.body_parts,
                "equipments": ex.equipments,
                "movementPatterns": ex.movement_patterns,
            }
            for ex in rows
        ]


@app.get("/exercise/{exercise_id}")
def get_exercise(exercise_id: str):
    with SessionLocal() as s:
        ex = s.get(M.Exercise, exercise_id)
        if not ex:
            raise HTTPException(status_code=404, detail=f"exercise {exercise_id} not found")
        return {
            "id": ex.exercise_id,
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


# ======================================================================
# MEDIA (MP4)
# ======================================================================
MP4_PAUSED_DIR = ROOT / "exercisedb_data" / "mp4_paused"


@app.get("/mp4/{exercise_id}.mp4")
def get_mp4(exercise_id: str):
    path = MP4_PAUSED_DIR / f"{exercise_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="video/mp4")


# ======================================================================
# INFO BOXES (научные справки)
# ======================================================================
@app.get("/info-boxes")
def list_info_boxes():
    with SessionLocal() as s:
        rows = s.scalars(select(M.InfoBox)).all()
        return {
            ib.id: {"title": ib.title, "body": ib.body, "source": ib.source or ""}
            for ib in rows
        }
