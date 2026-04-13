"""Hybrid search = semantic + lexical, reciprocal-rank-fusion. v0 scaffold."""

from __future__ import annotations


async def hybrid_search(query: str, types: list[str], limit: int = 10) -> list[dict]:
    """RRF-merge semantic and lexical results with type-aware reranking."""
    raise NotImplementedError("v0.1")
