# lexicon

> **A Context Store for AI agents.** Dynamically retrieves the information your agent needs to construct its context — *before* it queries your data tools.

Feature store is to ML what context store is to agents. `lexicon` stores your team's canonical queries, tool registry, terminology, guardrails, and decision log, and serves them to any MCP-compatible agent so the agent can ground itself in *your* organization before it acts.

---

## The easiest install: let your agent do it

Clone this repo, open Claude Code (or Cursor, Windsurf, any MCP-capable coding agent) in it, and say:

> *"Implement the context store from this repo."*

The agent reads `.claude/skills/install-lexicon.md`, spins up a dedicated Postgres via `docker compose`, runs the migrations, wires the MCP client config, and hands you a working agent query. Empty DB, ready to curate.

No clone required either — if your agent can read URLs, tell it:

> *"Implement the context store from https://github.com/AdamLenning/lexicon"*

---

## Or install it yourself

```bash
git clone https://github.com/AdamLenning/lexicon && cd lexicon
docker compose up -d
uvx lexicon-ai bootstrap --agent
```

`bootstrap --agent` detects your MCP client, writes the config, applies migrations, and prints your first query to try.

---

## Bring your own Postgres

Most users should skip this — the built-in docker-compose stack is small (~50 MB idle) and avoids schema/permission tangles.

If you want consolidation with existing infra:

```bash
pip install lexicon-ai
export LEXICON_DATABASE_URL=postgres://user:pass@host:5432/lexicon  # requires pgvector
lexicon init
lexicon serve
```

---

## What's stored

| Primitive | What it is | Example |
|---|---|---|
| Tool registry | Known data sources and what they contain | `salesforce`, `snowflake.analytics`, `stripe-api` |
| Glossary | Your team's terminology | "active customer" = logged in within 30 days AND paying |
| Canonical queries | Vetted SQL/API templates with parameters | `mrr_by_month(start, end)` |
| Query patterns | Cross-source recipes | "pipeline-to-revenue joins SFDC opportunities to Stripe charges via …" |
| Guardrails | Rules the agent must respect | "never query prod replica between 9–11 AM PT" |
| Decision log | Why past analytical calls were made | "We count trials in MRR starting 2025-Q2 because …" |

---

## MCP tools exposed

| Tool | Purpose |
|---|---|
| `lexicon.search(query, types=[...])` | Hybrid semantic + lexical search across all primitives |
| `lexicon.get_tool(name)` | Full tool registry entry |
| `lexicon.get_canonical_query(name, params)` | Query template + execution hints |
| `lexicon.define(term)` | Glossary lookup |
| `lexicon.list_guardrails(scope)` | Guardrails matching a scope (tool, dataset, time) |

---

## Architecture

```
 ┌──────────────────┐   MCP (stdio/SSE)   ┌─────────────────────────┐
 │  Claude / Cursor │ ──────────────────► │  lexicon MCP server     │
 │  Windsurf / …    │                     │  (src/lexicon/api)      │
 └──────────────────┘                     └────────────┬────────────┘
                                                       │
                                          hybrid search │ FastAPI REST
                                          (pgvector +   │ (admin curation)
                                           Postgres FTS)│
                                                       ▼
                                        ┌──────────────────────────┐
                                        │  Postgres + pgvector     │
                                        │  (dedicated, port 5433)  │
                                        └──────────────────────────┘
                                                       ▲
                                          ingestion    │
                                          ┌────────────┴────────────┐
                                          │  Bootstrap skill (LLM)  │
                                          │  file-glob, dbt,        │
                                          │  Notion, Confluence     │
                                          └─────────────────────────┘
```

---

## Why this exists

Every major data platform shipped an MCP server in 2025–2026 — dbt, Omni, Looker, BigQuery, Snowflake Cortex. They are all **single-source semantic layers**. None of them answer the questions an agent actually has when it wakes up:

- Which tool has this data?
- What does "active customer" mean at *this* company?
- Is there a canonical query for this?
- Am I allowed to run this right now?

`lexicon` is the layer that answers those questions. Read [`DESIGN.md`](./DESIGN.md) for the full rationale, competitive landscape, and roadmap.

---

## Status

v0 — scaffolded, stubs only. Not yet functional. See [`DESIGN.md`](./DESIGN.md) for the roadmap.

## License

Apache 2.0
