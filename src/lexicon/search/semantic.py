"""Semantic search via pgvector. v0 scaffold — implementation ships in v0.1."""

from __future__ import annotations


async def embed(text: str) -> list[float]:
    """Return the embedding vector for a piece of text."""
    raise NotImplementedError("v0.1")


async def semantic_search(query: str, types: list[str], limit: int = 10) -> list[dict]:
    """Run pgvector cosine-similarity search over requested primitive types."""
    raise NotImplementedError("v0.1")
