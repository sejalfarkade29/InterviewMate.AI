import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

log = logging.getLogger("interviewmate.db")


def _sqlite_engine(url: str):
    return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)


def _build_engine():
    url = settings.sqlalchemy_database_url
    if url.startswith("sqlite"):
        return _sqlite_engine(url)
    engine = create_engine(url, connect_args=settings.database_connect_args, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:  # noqa: BLE001
        if not settings.SQLITE_FALLBACK:
            raise
        log.warning("Could not connect to the configured database (%s). Using local SQLite file instead: %s",
                    exc.__class__.__name__, settings.SQLITE_FALLBACK_URL)
        print(f"\n[InterviewMate] WARNING: cannot reach your database ({exc.__class__.__name__}). "
              f"Falling back to {settings.SQLITE_FALLBACK_URL}. Start PostgreSQL to use it instead.\n")
        engine.dispose()
        return _sqlite_engine(settings.SQLITE_FALLBACK_URL)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
