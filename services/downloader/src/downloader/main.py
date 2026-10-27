"""URL downloader worker."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from common.celery_app import create_app
from common.contracts import Downloaded
from common.queues import QUEUES, TaskNames
from downloader.downloader import Downloader

logger = logging.getLogger(__name__)

app = create_app("downloader", QUEUES["download"])


def process(url: str, downloader: Downloader) -> Downloaded:
    """Fetch ``url`` and store its body when the response is HTML."""
    fetched = downloader.fetch(url)
    payload = Downloaded(
        url=url,
        content_type=fetched.content_type,
        size_bytes=fetched.size_bytes,
    )

    if not downloader.is_html(fetched):
        logger.info("not forwarding %s: content type %r is not HTML", url, fetched.content_type)
        return payload

    payload.raw_path = str(downloader.store(fetched))
    return payload


def forward(payload: Downloaded, send: Callable[..., Any] | None = None) -> None:
    """Queue a stored document for extraction, skipping ones with no raw file."""
    if payload.raw_path is None:
        return
    (send or app.send_task)(
        TaskNames.EXTRACT,
        kwargs={"payload": payload.model_dump()},
        queue=QUEUES["extract"],
    )


@app.task(name=TaskNames.DOWNLOAD)
def download(url: str) -> dict:
    """Fetch the URL, store HTML bodies and forward them to the extractor."""
    payload = process(url, Downloader())
    forward(payload)
    return payload.model_dump()
