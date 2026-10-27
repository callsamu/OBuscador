"""Tests for :mod:`downloader.downloader`."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine, select

from common.db import Document, DocumentState, create_db, hash_url
from downloader.downloader import Downloader, FetchResult

URL = "https://example.com/article"
BODY = b"<html>hi</html>"


def _engine(path: Path) -> Engine:
    engine = create_engine(f"sqlite:///{path}")
    create_db(engine)
    return engine


def _client(body: bytes = BODY, content_type: str = "text/html") -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": content_type})

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_fetch_returns_body_and_content_type(tmp_path: Path) -> None:
    result = Downloader(raw_dir=tmp_path, client=_client()).fetch(URL)

    assert result.body == b"<html>hi</html>"
    assert result.content_type == "text/html"
    assert result.size_bytes == len(result.body)


def test_fetch_truncates_the_body_to_max_bytes(tmp_path: Path) -> None:
    downloader = Downloader(tmp_path, max_bytes=4, client=_client(b"0123456789"))

    assert downloader.fetch(URL).body == b"0123"


def test_fetch_raises_on_error_status(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        Downloader(tmp_path, client=client).fetch(URL)


def test_store_writes_a_hashed_file_and_records_metadata(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "metadata.db")
    downloader = Downloader(tmp_path / "raw", engine=engine, client=_client())

    path = downloader.store(downloader.fetch(URL))

    expected = tmp_path / "raw" / f"{hash_url(URL)[:16]}.html"
    assert path == expected
    assert path.read_bytes() == BODY

    with Session(engine) as session:
        [document] = session.exec(select(Document)).all()

    assert document.url_hash == hash_url(URL)
    assert document.url == URL
    assert document.host == "example.com"
    assert document.content_path == str(expected)
    assert document.content_hash == hashlib.sha256(BODY).hexdigest()
    assert document.state is DocumentState.DOWNLOADED


def test_store_updates_the_existing_row_for_the_same_url(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "metadata.db")
    downloader = Downloader(tmp_path / "raw", engine=engine, client=_client())

    downloader.store(downloader.fetch(URL))
    downloader.store(downloader.fetch(URL))

    with Session(engine) as session:
        documents = session.exec(select(Document)).all()

    assert len(documents) == 1


@pytest.mark.parametrize(
    "content_type",
    ["text/html", "text/html; charset=utf-8", "application/xhtml+xml", "TEXT/HTML"],
)
def test_is_html_accepts_html_documents(content_type: str) -> None:
    result = FetchResult(url=URL, body=b"", content_type=content_type)

    assert Downloader.is_html(result)


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "text/plain", "", None])
def test_is_html_rejects_other_content_types(content_type: str | None) -> None:
    result = FetchResult(url=URL, body=b"", content_type=content_type)

    assert not Downloader.is_html(result)
