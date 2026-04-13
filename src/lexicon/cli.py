"""CLI entry point for `lexicon`.

Commands:
    lexicon init                  Apply migrations against the configured Postgres.
    lexicon serve                 Run the REST API + MCP server.
    lexicon ingest <adapter>      Run an ingestion adapter and stage proposals.
    lexicon review                Interactive approval queue for ingested proposals.
    lexicon bootstrap --agent     One-shot agent-driven install (detect client, wire MCP).

All commands are stubs at v0. See DESIGN.md §9 for implementation milestones.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="lexicon",
    help="Context Store for AI agents. See https://github.com/AdamLenning/lexicon",
    no_args_is_help=True,
)


@app.command()
def init() -> None:
    """Apply Alembic migrations against the configured Postgres."""
    typer.echo("stub — not yet implemented (v0.1)")


@app.command()
def serve(host: str | None = None, port: int | None = None) -> None:
    """Run the REST API and the MCP server (stdio transport)."""
    typer.echo("stub — not yet implemented (v0.1)")


@app.command()
def ingest(adapter: str, source: str | None = None, preview: bool = False) -> None:
    """Run an ingestion adapter (file-glob | dbt | notion | confluence) and stage proposals."""
    typer.echo(f"stub — ingest {adapter} not yet implemented (v0.2)")


@app.command()
def review() -> None:
    """Interactive approval queue for ingested proposals."""
    typer.echo("stub — not yet implemented (v0.2)")


@app.command()
def bootstrap(agent: bool = False) -> None:
    """One-shot install helper. With --agent, auto-detects and configures MCP clients."""
    typer.echo("stub — not yet implemented (v0.1)")


if __name__ == "__main__":
    app()
