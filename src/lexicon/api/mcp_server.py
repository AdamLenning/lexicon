"""MCP server for `lexicon`.

Exposes five tools that an agent calls to ground itself before querying data tools:
    lexicon.search(query, types=[...])
    lexicon.get_tool(name)
    lexicon.get_canonical_query(name, params)
    lexicon.define(term)
    lexicon.list_guardrails(scope)

v0 scaffold — tool handlers return placeholder payloads. Real implementations ship in v0.1.
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server: Server = Server("lexicon")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="lexicon.search",
            description=(
                "Hybrid semantic + lexical search across all lexicon primitives "
                "(tools, glossary, canonical queries, query patterns, guardrails, decisions)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "tool",
                                "glossary",
                                "canonical_query",
                                "pattern",
                                "guardrail",
                                "decision",
                            ],
                        },
                    },
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="lexicon.get_tool",
            description="Return the full tool registry entry for a given tool name.",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        ),
        Tool(
            name="lexicon.get_canonical_query",
            description="Return a canonical query template with execution hints.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="lexicon.define",
            description=(
                "Look up a glossary term and return the organization's canonical definition."
            ),
            inputSchema={
                "type": "object",
                "properties": {"term": {"type": "string"}},
                "required": ["term"],
            },
        ),
        Tool(
            name="lexicon.list_guardrails",
            description="List guardrails that apply to a given scope (tool, dataset, time).",
            inputSchema={
                "type": "object",
                "properties": {"scope": {"type": "string"}},
                "required": ["scope"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # v0 stub — return a placeholder that agents can parse without erroring.
    return [
        TextContent(
            type="text",
            text=(
                f"[lexicon v0 stub] tool={name} args={arguments} — "
                "handlers not yet implemented. See DESIGN.md §9 roadmap."
            ),
        )
    ]


def main() -> None:
    """Entry point for the `lexicon-mcp` stdio server."""
    import asyncio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
