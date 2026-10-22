ARG PYTHON_VERSION=3.12
FROM ghcr.io/astral-sh/uv:${PYTHON_VERSION}-bookworm-slim

ARG SERVICE
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

# Workspace manifests first so dependency layers stay cached.
COPY pyproject.toml uv.lock ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/downloader/pyproject.toml services/downloader/pyproject.toml
COPY services/extractor/pyproject.toml services/extractor/pyproject.toml
COPY services/indexer/pyproject.toml services/indexer/pyproject.toml

RUN uv sync --frozen --no-dev --package "${SERVICE}"

COPY packages/common packages/common
COPY services services

ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", "echo 'override with a service command'"]
