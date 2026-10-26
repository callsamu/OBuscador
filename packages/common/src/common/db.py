"""Database models and engine setup shared by all services."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine

from common.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


@lru_cache
def get_engine() -> Engine:
    """Build the SQLAlchemy engine described by the shared settings."""
    connect_args: dict[str, object] = {}
    if settings.db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        settings.db_url,
        echo=settings.log_level.upper() == "DEBUG",
        connect_args=connect_args,
    )


def create_db(eng: Engine):
    SQLModel.metadata.create_all(eng)


class Document(SQLModel, table=True):
    """A crawled document stored on disk and indexed for search."""

    id: int | None = Field(default=None, primary_key=True)
    domain: str = Field(index=True)
    path: str
    filepath: str = Field(index=True)
    updatedAt: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"onupdate": _utcnow})
    createdAt: datetime = Field(default_factory=_utcnow)
