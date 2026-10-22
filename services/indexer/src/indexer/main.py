"""Search indexer worker (Elasticsearch)."""

from __future__ import annotations

import hashlib

from elasticsearch import Elasticsearch

from common.celery_app import create_app
from common.config import settings
from common.contracts import Extracted
from common.queues import QUEUES, TaskNames

app = create_app("indexer", QUEUES["index"])
client = Elasticsearch(settings.elasticsearch_url)


@app.task(name=TaskNames.INDEX)
def index(payload: dict) -> dict:
    """Store the extracted document in the search index."""
    document = Extracted.model_validate(payload)
    doc_id = hashlib.sha256(document.url.encode()).hexdigest()[:16]
    client.index(index=settings.elasticsearch_index, id=doc_id, document=document.model_dump())
    return {"id": doc_id, "index": settings.elasticsearch_index, "url": document.url}
