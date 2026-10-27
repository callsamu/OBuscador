"""Tests for :mod:`extractor.main`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.contracts import Downloaded, Extracted
from common.queues import QUEUES, TaskNames
from extractor import main
from extractor.extractor import Extractor

URL = "https://example.com/article"


def test_process_parses_the_stored_file(tmp_path: Path) -> None:
    path = tmp_path / "page.html"
    path.write_text("<title>Stored</title><a href='/one'>one</a>", encoding="utf-8")
    payload = Downloaded(url=URL, raw_path=str(path)).model_dump()

    extracted = main.process(payload, Extractor())

    assert extracted.url == URL
    assert extracted.title == "Stored"
    assert extracted.links == ["/one"]


def test_process_tolerates_a_missing_file(tmp_path: Path) -> None:
    payload = Downloaded(url=URL, raw_path=str(tmp_path / "missing.html")).model_dump()

    extracted = main.process(payload, Extractor())

    assert extracted.url == URL
    assert extracted.title is None
    assert extracted.text == ""
    assert extracted.links == []


def test_forward_queues_the_extracted_document() -> None:
    sent: list[dict[str, Any]] = []

    def fake_send(*args: object, **kwargs: object) -> None:
        sent.append({"args": args, **kwargs})

    extracted = Extracted(url=URL, title="Stored", text="body", links=["/one"])
    main.forward(extracted, send=fake_send)

    assert sent[0]["args"] == (TaskNames.INDEX,)
    assert sent[0]["queue"] == QUEUES["index"]
    assert sent[0]["kwargs"]["payload"]["title"] == "Stored"
