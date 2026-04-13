"""Smoke tests for the v0 scaffold. Real behavior tests arrive in v0.1."""

from __future__ import annotations


def test_package_imports() -> None:
    import lexicon

    assert lexicon.__version__ == "0.0.1"


def test_models_importable() -> None:
    from lexicon.models import (
        Base,
        CanonicalQuery,
        Decision,
        GlossaryEntry,
        Guardrail,
        QueryPattern,
        Tool,
    )

    assert Base is not None
    for model in (Tool, GlossaryEntry, CanonicalQuery, QueryPattern, Guardrail, Decision):
        assert model.__tablename__


def test_mcp_server_lists_five_tools() -> None:
    import asyncio

    from lexicon.api.mcp_server import list_tools

    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert names == {
        "lexicon.search",
        "lexicon.get_tool",
        "lexicon.get_canonical_query",
        "lexicon.define",
        "lexicon.list_guardrails",
    }


def test_rest_root() -> None:
    from fastapi.testclient import TestClient

    from lexicon.api.rest import app

    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/").json()["name"] == "lexicon"
