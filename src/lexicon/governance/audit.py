"""Audit log — every MCP read and REST write is logged. v0 scaffold (v0.3)."""

from __future__ import annotations


def log_read(tool: str, arguments: dict, agent_id: str | None = None) -> None:
    raise NotImplementedError("v0.3")


def log_write(primitive: str, action: str, actor: str, before: dict | None, after: dict) -> None:
    raise NotImplementedError("v0.3")
