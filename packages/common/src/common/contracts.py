"""Payloads exchanged over the queues."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: AnyHttpUrl
    tags: list[str] = Field(default_factory=list)


class Extracted(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str | None = None
    text: str | None = None
    links: list[str] = Field(default_factory=list)
