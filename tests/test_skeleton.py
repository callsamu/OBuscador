"""Smoke tests for the skeleton."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from common.celery_app import create_app
from common.queues import QUEUES, TaskNames


def test_queues_are_distinct() -> None:
    assert len(set(QUEUES.values())) == len(QUEUES)


def test_celery_app_uses_json_serialization() -> None:
    app = create_app("test", QUEUES["download"])
    assert app.conf.task_serializer == "json"
    assert app.conf.task_create_missing_queues is True


def test_task_names_are_namespaced() -> None:
    for name in (TaskNames.DOWNLOAD, TaskNames.EXTRACT, TaskNames.INDEX):
        assert "." in name


def test_api_healthz() -> None:
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
