"""Guardrail primitive — hard rules the agent must respect."""

from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Guardrail(Base, TimestampMixin):
    __tablename__ = "guardrails"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    scope: Mapped[list[str]] = mapped_column(JSON, default=list)  # tool/dataset/time patterns
    severity: Mapped[str] = mapped_column(String(20), default="warn")  # warn | block
    rule: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
