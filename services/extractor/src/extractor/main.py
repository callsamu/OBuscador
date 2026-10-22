"""HTML extraction worker."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from common.celery_app import create_app
from common.contracts import Downloaded, Extracted
from common.queues import QUEUES, TaskNames

app = create_app("extractor", QUEUES["extract"])


@app.task(name=TaskNames.EXTRACT)
def extract(payload: dict) -> dict:
    """Parse the stored HTML and forward the structured result to the indexer."""
    downloaded = Downloaded.model_validate(payload)

    html = ""
    if downloaded.raw_path and Path(downloaded.raw_path).exists():
        html = Path(downloaded.raw_path).read_text(encoding="utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    extracted = Extracted(
        url=downloaded.url,
        title=soup.title.get_text(strip=True) if soup.title else None,
        text=soup.get_text(" ", strip=True),
        links=[str(a["href"]) for a in soup.find_all("a", href=True)],
    )
    app.send_task(
        TaskNames.INDEX,
        kwargs={"payload": extracted.model_dump()},
        queue=QUEUES["index"],
    )
    return extracted.model_dump()
