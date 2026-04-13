"""dbt adapter — parse manifest.json to seed tools + glossary. v0 scaffold (v0.2)."""

from __future__ import annotations


async def fetch(target_dir: str) -> list[str]:
    raise NotImplementedError("v0.2")
