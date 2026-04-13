"""Glossary primitive — terminology with the exact definition this org uses."""

from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class GlossaryEntry(Base, TimestampMixin):
    __tablename__ = "glossary"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    definition: Mapped[str] = mapped_column(Text)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
