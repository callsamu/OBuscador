"""HTML extraction worker."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from common.celery_app import create_app
from common.contracts import Downloaded, Extracted
from common.queues import QUEUES, TaskNames
from extractor.extractor import Extractor

app = create_app("extractor", QUEUES["extract"])


def process(payload: dict, extractor: Extractor) -> Extracted:
    """Parse the stored HTML and build the indexer payload."""
    downloaded = Downloaded.model_validate(payload)
    return extractor.from_file(downloaded.url, downloaded.raw_path)


def forward(extracted: Extracted, send: Callable[..., Any] | None = None) -> None:
    """Queue an extracted document for indexing."""
    (send or app.send_task)(
        TaskNames.INDEX,
        kwargs={"payload": extracted.model_dump()},
        queue=QUEUES["index"],
    )


@app.task(name=TaskNames.EXTRACT)
def extract(payload: dict) -> dict:
    """Parse the stored HTML and forward the structured result to the indexer."""
    extracted = process(payload, Extractor())
    forward(extracted)
    return extracted.model_dump()
