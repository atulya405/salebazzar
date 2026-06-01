from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import PROJECT_DIR, get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def _database_url() -> str:
    if settings.database_url == "sqlite:///./80off.db":
        return f"sqlite:///{(PROJECT_DIR / '80off.db').as_posix()}"
    return settings.database_url


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(_database_url(), connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
