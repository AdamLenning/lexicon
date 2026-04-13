"""LLM-driven ingestion skill.

Given raw content from an adapter, call Anthropic's API (with prompt caching) to
propose primitive entries (tool / glossary / canonical_query / pattern / guardrail /
decision) with confidence scores. Proposals land in the review queue for human approval.

v0 scaffold — ships in v0.2. See DESIGN.md §5 for the eval methodology.
"""

from __future__ import annotations

from collections.abc import Iterable


async def propose_entries(content: Iterable[str], source_kind: str) -> list[dict]:
    """Given raw content, propose lexicon entries. Returns a list of proposal dicts."""
    raise NotImplementedError("v0.2")
