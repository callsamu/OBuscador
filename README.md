# engsoftware

Microservices scaffold: an HTTP API orchestrates a Celery pipeline of
**downloader → extractor → indexer**, with Redis as broker and Sonic
as the search engine.

```
             POST /crawl
                 │
                 ▼
          ┌────────────┐  download  ┌────────────┐  extract   ┌────────────┐  index   ┌────────────┐
          │    api     │ ─────────▶ │ downloader │ ─────────▶ │ extractor  │ ───────▶ │  indexer   │ ──▶ Sonic
          │ (FastAPI)  │   queue    │  (Celery)  │   queue    │  (Celery)  │  queue   │  (Celery)  │
          └────────────┘            └────────────┘            └────────────┘          └────────────┘
```

Each service is an independent Celery worker bound to a single queue. They
never import one another: they publish well known task names
(`common.queues.TaskNames`) onto well known queues, so any stage can be
replaced or scaled on its own.

Sonic indexes the text and returns only object ids; the indexer derives that id
from the URL hash, so pair it with a document store when you need full payloads.

## Layout

```
pyproject.toml            uv workspace root (dev tooling, ruff/mypy/pytest)
packages/common/          shared settings, contracts, Celery factory
services/api/             FastAPI HTTP layer
services/downloader/      fetches URLs, stores raw HTML
services/extractor/       parses HTML into structured data
services/indexer/         pushes document text to Sonic
Dockerfile                one image, SERVICE build arg selects the member
docker-compose.yml        redis + sonic + the four services
```

## Getting started

```bash
cp .env.example .env
uv sync --all-packages        # install the workspace
make up                      # docker compose: redis, sonic, 4 services
```

Or run the pieces locally (needs Redis and Sonic reachable at the addresses in
`.env`):

```bash
make api        # uvicorn api.main:app --reload
make downloader # celery -A downloader.main:app worker -Q download
make extractor  # celery -A extractor.main:app worker -Q extract
make indexer    # celery -A indexer.main:app worker -Q index
```

## API

| Method | Path              | Description                                     |
| ------ | ----------------- | ----------------------------------------------- |
| POST   | `/crawl`          | Queue a URL: `{"url": "https://example.com"}`   |
| GET    | `/tasks/{id}`     | Celery task state and result                    |
| GET    | `/healthz`        | Liveness probe                                  |
| GET    | `/docs`           | OpenAPI UI                                      |

```bash
curl -X POST localhost:8000/crawl \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com"}'
```

## Configuration

All settings live in `packages/common/src/common/config.py` and are read from
the environment (see `.env.example`): `REDIS_URL`, `SONIC_HOST`, `SONIC_PORT`, `SONIC_PASSWORD`,
`RAW_STORAGE_DIR`, `DOWNLOAD_TIMEOUT`, …

## Quality gates

```bash
make lint   # ruff check + ruff format --check + mypy
make test   # pytest
```
