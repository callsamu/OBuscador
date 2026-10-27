"""Database models and engine setup shared by all services."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from functools import lru_cache

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine

from common.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


def hash_url(url: str) -> str:
    """Return the primary key used for a document URL."""
    return hashlib.sha256(url.encode()).hexdigest()


@lru_cache
def get_engine() -> Engine:
    """Build the SQLAlchemy engine described by the shared settings."""
    connect_args: dict[str, object] = {}
    if settings.db_url.startswith("sqlite"):
        # The API serves requests from a thread pool, so connections may move between threads.
        connect_args["check_same_thread"] = False
    return create_engine(
        settings.db_url,
        echo=settings.log_level.upper() == "DEBUG",
        connect_args=connect_args,
    )


def create_db(eng: Engine) -> None:
    SQLModel.metadata.create_all(eng)


class DocumentState(StrEnum):
    """Lifecycle of a document as it moves through the services."""

    PENDING = "pending"
    DOWNLOADED = "downloaded"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(SQLModel, table=True):
    """A crawled document, keyed by the hash of its URL."""

    url_hash: str = Field(primary_key=True)
    url: str = Field(unique=True)
    host: str = Field(index=True)
    content_path: str | None = None
    content_hash: str | None = None
    state: DocumentState = Field(
        default=DocumentState.PENDING,
        sa_column=Column(
            SAEnum(
                DocumentState,
                values_callable=lambda enum_cls: [member.value for member in enum_cls],
                name="documentstate",
            ),
            nullable=False,
            index=True,
        ),
    )
    updatedAt: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"onupdate": _utcnow})
    createdAt: datetime = Field(default_factory=_utcnow)
