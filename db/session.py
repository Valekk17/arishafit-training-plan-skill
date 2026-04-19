"""SQLAlchemy engine + session factory для ArishaFit."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_ENV = Path(__file__).resolve().parent.parent / ".env"
if _ENV.exists():
    load_dotenv(_ENV)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://arishafit:arishafit_dev@localhost:5432/arishafit",
)

engine = create_engine(DATABASE_URL, future=True, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Session:
    """Одноразовая сессия (используй в `with` блоке)."""
    return SessionLocal()
