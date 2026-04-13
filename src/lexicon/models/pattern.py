"""Query pattern primitive — cross-source recipes combining multiple tools."""

from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class QueryPattern(Base, TimestampMixin):
    __tablename__ = "query_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    involves_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    recipe: Mapped[str] = mapped_column(Text)
