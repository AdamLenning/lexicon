"""Human-in-the-loop review queue for ingestion proposals. v0 scaffold."""

from __future__ import annotations


def enqueue(proposal: dict) -> None:
    raise NotImplementedError("v0.2")


def approve(proposal_id: int, reviewer: str) -> None:
    raise NotImplementedError("v0.2")


def reject(proposal_id: int, reviewer: str, reason: str | None = None) -> None:
    raise NotImplementedError("v0.2")
