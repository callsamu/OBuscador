"""Tests for :mod:`downloader.main`."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from sqlmodel import create_engine

from common.contracts import Downloaded
from common.db import create_db
from common.queues import QUEUES, TaskNames
from downloader import main
from downloader.downloader import Downloader

URL = "https://example.com/article"


def _downloader(raw_dir: Path, body: bytes, content_type: str | None) -> Downloader:
    headers = {} if content_type is None else {"content-type": content_type}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers=headers)

    engine = create_engine(f"sqlite:///{raw_dir.parent / 'metadata.db'}")
    create_db(engine)
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    return Downloader(raw_dir, client=client, engine=engine)


def test_non_html_is_stored_nowhere(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    payload = main.process(URL, _downloader(raw_dir, b"%PDF-1.7", "application/pdf"))

    assert payload.raw_path is None
    assert not raw_dir.exists()


def test_html_is_stored(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    payload = main.process(URL, _downloader(raw_dir, b"<html></html>", "text/html; charset=utf-8"))

    expected = raw_dir / f"{hashlib.sha256(URL.encode()).hexdigest()[:16]}.html"
    assert payload.raw_path == str(expected)
    assert expected.read_bytes() == b"<html></html>"


def _capture_sent_tasks() -> tuple[list[dict[str, Any]], Callable[..., None]]:
    sent: list[dict[str, Any]] = []

    def fake_send(*args: object, **kwargs: object) -> None:
        sent.append({"args": args, **kwargs})

    return sent, fake_send


def test_forward_skips_payloads_without_a_raw_file() -> None:
    sent, fake_send = _capture_sent_tasks()

    main.forward(Downloaded(url=URL), send=fake_send)

    assert sent == []


def test_forward_queues_stored_documents() -> None:
    sent, fake_send = _capture_sent_tasks()
    payload = Downloaded(url=URL, raw_path="data/raw/abc.html")

    main.forward(payload, send=fake_send)

    assert sent[0]["args"] == (TaskNames.EXTRACT,)
    assert sent[0]["queue"] == QUEUES["extract"]
    assert sent[0]["kwargs"]["payload"]["raw_path"] == payload.raw_path
