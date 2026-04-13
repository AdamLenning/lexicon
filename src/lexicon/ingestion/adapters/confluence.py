"""Confluence adapter — requires CONFLUENCE_TOKEN + space key. v0 scaffold (v0.3)."""

from __future__ import annotations


async def fetch(space_key: str, token: str) -> list[str]:
    raise NotImplementedError("v0.3")
