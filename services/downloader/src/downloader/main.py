"""URL downloader worker."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from common.celery_app import create_app
from common.config import settings
from common.contracts import Downloaded
from common.queues import QUEUES, TaskNames

app = create_app("downloader", QUEUES["download"])


@app.task(name=TaskNames.DOWNLOAD)
def download(url: str) -> dict:
    """Fetch the URL, store the raw body and forward it to the extractor."""
    raw_dir = Path(settings.raw_storage_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True, timeout=settings.download_timeout) as client:
        response = client.get(url, headers={"User-Agent": settings.user_agent})
        response.raise_for_status()
        body = response.content[: settings.download_max_bytes]

    raw_path = raw_dir / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.html"
    raw_path.write_bytes(body)

    payload = Downloaded(
        url=url,
        raw_path=str(raw_path),
        content_type=response.headers.get("content-type"),
        size_bytes=len(body),
    )
    app.send_task(
        TaskNames.EXTRACT,
        kwargs={"payload": payload.model_dump()},
        queue=QUEUES["extract"],
    )
    return payload.model_dump()
