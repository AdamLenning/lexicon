"""File-glob adapter — ingest from markdown, SQL, schema dumps. v0 scaffold (v0.2)."""

from __future__ import annotations


async def fetch(pattern: str) -> list[str]:
    raise NotImplementedError("v0.2")
