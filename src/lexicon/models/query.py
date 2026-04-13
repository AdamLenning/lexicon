"""Canonical query primitive — vetted SQL/API call templates with parameters."""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class CanonicalQuery(Base, TimestampMixin):
    __tablename__ = "canonical_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    tool_id: Mapped[int | None] = mapped_column(ForeignKey("tools.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    template: Mapped[str] = mapped_column(Text)  # SQL or API call template
    parameters: Mapped[list[dict]] = mapped_column(JSON, default=list)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    gotchas: Mapped[str | None] = mapped_column(Text, nullable=True)
