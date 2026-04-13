"""Lexical search via Postgres FTS. v0 scaffold — implementation ships in v0.1."""

from __future__ import annotations


async def lexical_search(query: str, types: list[str], limit: int = 10) -> list[dict]:
    """Run Postgres `tsvector`/`tsquery` search over requested primitive types."""
    raise NotImplementedError("v0.1")
