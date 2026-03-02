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
