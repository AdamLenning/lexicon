---
name: install-lexicon
description: Install, configure, and bootstrap `lexicon` (a Context Store for AI agents) in the user's environment. Use when the user says "implement the context store from this repo", "install lexicon", "set up the context store", or otherwise asks to get lexicon running. Handles docker-compose setup, migrations, MCP client wiring (Claude Desktop, Claude Code, Cursor, Windsurf), and first-entry guidance.
---

# Install `lexicon` — Context Store

Your job: take the user from "I just cloned (or discovered) this repo" to "my agent can query the context store" in under 2 minutes, with zero manual config file editing.

## Phase 0 — Preflight (do this first, report findings before acting)

Check all of these in parallel:

1. **Working directory:** are we inside the `lexicon` repo? Look for `pyproject.toml` with `name = "lexicon-ai"`. If not, ask the user if they want to `git clone https://github.com/AdamLenning/lexicon` first.
2. **Docker:** `docker version` — daemon running? If not, tell the user to start Docker Desktop and wait for them to confirm before proceeding.
3. **Port 5433:** `lsof -i :5433` — anything listening? If yes, note the conflict and offer to either stop the conflicting process or set `LEXICON_POSTGRES_PORT=<free-port>` in a `.env` file.
4. **uv available:** `which uv` — if missing, `curl -LsSf https://astral.sh/uv/install.sh | sh` (confirm with user first).
5. **MCP client detection:** check these paths in parallel and report which exist:
   - Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows) / `~/.config/Claude/claude_desktop_config.json` (Linux)
   - Claude Code: `~/.claude.json` or `~/.claude/settings.json`
   - Cursor: `~/.cursor/mcp.json`
   - Windsurf: `~/.codeium/windsurf/mcp_config.json`

Summarize findings in 3-5 bullet points before moving on. Example:
> Found: Docker running, port 5433 free, uv installed, Claude Desktop + Cursor configs detected.
> Plan: bring up Postgres, run migrations, add lexicon MCP server to both Claude Desktop and Cursor.
> Proceeding.

## Phase 1 — Bring up the dedicated Postgres

```bash
docker compose up -d
```

Wait for the healthcheck:
```bash
docker compose ps
```
Look for `lexicon-postgres` in `healthy` state. If it fails to start within 30 seconds, `docker compose logs lexicon-postgres` and help the user diagnose (most common: port conflict or pgvector image pull failure on slow connection).

## Phase 2 — Bootstrap

```bash
uvx --from . lexicon-ai bootstrap --agent
```

This command (when fully implemented) will:
- Apply Alembic migrations against the docker-compose Postgres
- Detect MCP clients from Phase 0
- Write the lexicon server stanza into each detected client's config (idempotent — safe to re-run)
- Emit machine-readable JSON on stdout describing what changed

Parse the JSON output and narrate the changes back to the user in plain English.

**Note:** at v0 (current scaffold state), the CLI is stubbed and the bootstrap command will print "stub — not yet implemented" and exit. That's expected. Tell the user: "The scaffold is in place but the bootstrap logic isn't implemented yet — this is v0. Once v0.1 ships, this skill will take you end-to-end."

## Phase 3 — Verify MCP wiring

Ask the user to restart their MCP client (Claude Desktop needs a full quit/relaunch; Cursor/Windsurf need a reload window). After restart, they should see `lexicon` tools available — try:

```
lexicon.search("test")
```

Expected: empty results (DB is empty) but no errors.

## Phase 4 — First-entry guidance

The DB is empty by design. Offer the user two paths:

### Path A — Auto-ingest what's in this repo
Scan the cwd for things the bootstrap skill can learn from:
- `dbt_project.yml` + `target/manifest.json` → propose tool + glossary entries
- `*.md` wikis → propose glossary + decision-log entries
- `*.sql` schema dumps → propose canonical queries

If any of these exist, run:
```bash
lexicon ingest file-glob "**/*.md" --preview
lexicon ingest dbt ./target --preview  # if dbt detected
```
`--preview` shows what would be proposed without writing. Walk the user through reviewing a few.

### Path B — Manually add a first glossary entry
Ask the user: *"What's one term in your company that people use loosely and an agent would probably get wrong? Give me the term and the precise definition."*

Then POST it via REST:
```bash
curl -X POST http://localhost:8000/glossary \
  -H "Content-Type: application/json" \
  -d '{"term": "<term>", "definition": "<definition>", "owner": "<user>"}'
```

Then demo: tell Claude "what do we mean by <term>?" — it should use `lexicon.define` to answer from the freshly-added entry.

## Recovery paths

| Symptom | Fix |
|---|---|
| `docker compose up` fails with "port already in use" | `echo "LEXICON_POSTGRES_PORT=5434" >> .env && docker compose up -d` — then update `DATABASE_URL` in the MCP config accordingly |
| `docker compose ps` shows container unhealthy | `docker compose logs lexicon-postgres` — most commonly: pgvector extension failed, needs image re-pull |
| No MCP client detected | Ask the user which agent they use. If it's not in the supported list, manually show them the MCP config JSON block to paste into their client's config |
| `uvx` fails with a package resolution error | Fall back to `pip install -e .` inside a fresh venv and invoke `lexicon-ai bootstrap --agent` directly |
| MCP client doesn't show `lexicon` tools after restart | Check the config file — the lexicon entry should be under `mcpServers` with a `command` that points to the installed `lexicon-mcp` binary. If missing, re-run bootstrap |

## What you're NOT allowed to do

- Don't modify the user's MCP config without showing them the diff first.
- Don't seed sample data. The v0 design is intentionally empty-on-install.
- Don't run `docker compose down -v` (destroys data) without explicit user confirmation.
- Don't expose the MCP server on a non-loopback interface unless the user explicitly asks for it — v0 has no auth.

## When in doubt

Ask the user. This skill optimizes for *zero-surprise* installs. A 30-second pause to confirm is always better than a mess.
