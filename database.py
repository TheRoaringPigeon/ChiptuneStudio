from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = create_engine(
    "sqlite:///./chiptune_studio.db",
    connect_args={"check_same_thread": False},
)

Session = sessionmaker(engine, autoflush=False)


def init_db() -> None:
    """Create all tables if they don't exist."""
    from models import db as _  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(engine)
    # Safe migration: add plugin_id to channels if it doesn't exist yet
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE channels ADD COLUMN plugin_id VARCHAR(64) DEFAULT 'chiptune'"
            ))
            conn.commit()
    except Exception:
        pass  # column already exists
