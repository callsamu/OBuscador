"""Minimal Sonic Channel client (ingestion only).

Sonic speaks a line based TCP protocol. This covers the two commands the
pipeline needs, without pulling in an extra dependency. Add ``search``/
``control`` channels here when the API grows a query endpoint.
"""

from __future__ import annotations

import socket

#: Sonic's channel buffer is 20_000 bytes; keep commands comfortably below it.
MAX_TEXT_LENGTH = 10_000


class SonicError(RuntimeError):
    """Raised when Sonic answers with an ``ERR`` line."""


class SonicIngest:
    """Blocking client for the Sonic ``ingest`` channel."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1491,
        password: str = "",
        timeout: float = 10.0,
    ) -> None:
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._reader = self._sock.makefile("r", encoding="utf-8", newline="\n")
        self._writer = self._sock.makefile("w", encoding="utf-8", newline="\n")

        try:
            greeting = self._reader.readline()
            if not greeting.startswith("CONNECTED"):
                raise SonicError(f"unexpected greeting: {greeting.strip()!r}")
            response = self._command(f"START ingest {password}".rstrip())
            if not response.startswith("STARTED"):
                raise SonicError(f"could not open ingest channel: {response!r}")
        except Exception:
            self.close()
            raise

    def _command(self, line: str) -> str:
        self._writer.write(f"{line}\n")
        self._writer.flush()
        response = self._reader.readline().strip()
        if response.startswith("ERR"):
            raise SonicError(response)
        return response

    def push(self, collection: str, bucket: str, object_id: str, text: str) -> None:
        """Index ``text`` under ``object_id``; Sonic stores no documents itself."""
        escaped = (
            text[:MAX_TEXT_LENGTH]
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\r", " ")
            .replace("\n", " ")
        )
        self._command(f'PUSH {collection} {bucket} {object_id} "{escaped}"')

    def close(self) -> None:
        for stream in (self._reader, self._writer):
            stream.close()
        self._sock.close()

    def __enter__(self) -> SonicIngest:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
