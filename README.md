# lexicon — Context Store spec

> A specification for a company-wide **Context Store** — the layer every AI agent in your organization queries before it queries anything else.

Feature store is to ML what context store is to agents. `lexicon` stores the terminology, tool registry, canonical queries, guardrails, and decision log your team already uses informally, and serves them to every MCP-capable AI client in the company so that agents ground themselves in *your* organization before they act.

## What is a Context Store?

A **Context Store** is a governed, queryable store of *organizational knowledge* designed to be consumed by AI agents at runtime. It holds the kind of context your senior employees carry in their heads — the terminology they use, the systems they know are authoritative for which data, the canonical queries they reach for, the operational rules they never write down, the reasoning behind past analytical decisions — and serves it to every AI agent in the company through the Model Context Protocol (MCP).

When an agent is asked a question, it queries the Context Store *before* it queries any data tool. Instead of guessing what "active customer" means, it looks it up. Instead of writing SQL from scratch, it pulls the team's canonical query. Instead of hitting the prod replica during ETL hours, it reads the guardrail and waits.

Six primitive types are stored (full specs in [`PRIMITIVES.md`](./PRIMITIVES.md)):

- **Tool registry** — which data sources exist, what they contain, who owns them, how they refresh
- **Glossary** — the exact definition your org uses for "MRR," "active customer," "churn," etc.
- **Canonical queries** — vetted SQL or API templates with parameters, expected output shapes, and gotchas
- **Query patterns** — cross-source recipes for questions that span multiple tools
- **Guardrails** — rules the agent must respect (access windows, PII scopes, quotas)
- **Decision log** — prose entries explaining *why* past analytical or operational calls were made

**A concrete example.** A salesperson opens Claude Desktop and asks *"what do we mean by 'active customer'?"* Claude's MCP client calls `lexicon.define("active customer")` before answering. The Context Store returns the canonical definition (*"logged in within 30 days AND paying; trials on day 31+ count only if they converted"*), the owner, and when it was last reviewed. Claude answers with the correct, grounded definition — not a plausible guess. Later, a data engineer in their dbt repo asks *"compute MRR for March."* Claude calls `lexicon.get_canonical_query("mrr_by_month", {month_start: "2026-03-01"})` and gets a ready-to-run query with the team's specific gotchas attached. Both users hit the same service. Both get the same ground truth.

## Where it fits in the modern AI stack

Context Stores are an emerging layer in agentic AI infrastructure. They sit between AI clients and everything else the agent might touch:

```
    ┌──────────────────────────────────────────────────────┐
    │  AI clients — Claude Desktop, Cursor, Windsurf,      │
    │  Continue, internal agents, scheduled jobs           │
    └───────────────────────┬──────────────────────────────┘
                            │ MCP
                            ▼
    ┌──────────────────────────────────────────────────────┐
    │  Context Store — lexicon                             │
    │  (grounding: terminology, tools, canonical queries,  │  ← agents query here FIRST
    │   patterns, guardrails, decisions)                   │
    └───────────────────────┬──────────────────────────────┘
                            │ MCP / SQL / REST (executed by the agent)
                            ▼
    ┌────────────┬──────────────┬──────────────┬───────────┐
    │ Warehouses │  SaaS APIs   │  Vector /    │ Semantic  │
    │ Snowflake, │  Salesforce, │  RAG stores  │ layers    │
    │ BigQuery,  │  Stripe,     │  Pinecone,   │ dbt SL,   │
    │ Redshift   │  HubSpot     │  Weaviate    │ Cube      │
    └────────────┴──────────────┴──────────────┴───────────┘
```

### How Context Stores differ from adjacent categories

| Category | What it stores | Primary consumer | Why it's different |
|---|---|---|---|
| **Context Store** (`lexicon`) | Curated, typed, governed organizational knowledge | AI agents (machines) | Cross-tool grounding; governance-first; MCP-native |
| **Vector store** (Pinecone, Weaviate, Qdrant) | Embeddings + metadata | Any retrieval system | Storage primitive only; no governance, typing, or curation — a Context Store uses one of these internally |
| **RAG pipeline** (LangChain, LlamaIndex) | Document chunks indexed for retrieval | A single agent in a single workflow | Retrieves unstructured content per-query; no canonical definitions, guardrails, or decision log |
| **Semantic layer** (dbt SL, Cube, AtScale) | Metric definitions for one warehouse | BI tools + agents querying that warehouse | Metrics only, single-source; answers "what's MRR" but not "which tool do I even ask about MRR" |
| **Data catalog** (Atlan, Alation, Collibra) | Dataset metadata + lineage | Humans browsing via UI | Human-facing UI; not designed for low-latency machine consumption |
| **Agent memory** (LangChain Memory, Claude conversation) | Conversational state for one agent session | That agent, that session | Ephemeral and per-agent; a Context Store is durable, shared company-wide, and governed |
| **Feature store** (Tecton, Feast) | ML features for training + inference | ML models in training/serving pipelines | ML pipeline infrastructure, different runtime, different consumer — the structural analog the name "context store" borrows from |

A Context Store doesn't replace any of these — it sits alongside them. A metric definition in your semantic layer is referenced as a canonical query in the Context Store. A RAG pipeline might use the Context Store's glossary to disambiguate a user's query before retrieval. A data catalog might feed the Context Store via an ingestion adapter. The Context Store is the layer that makes all of them usable *by agents, across tools, with organizational ground truth.*

## What this repo is

**A set of markdown documents that teach an AI coding agent how to stand up a production Context Store for a company.** No application code. No framework. No opinions baked into a runtime. The docs describe schemas, APIs, deployment recipes, governance, and ingestion patterns — the agent generates the code appropriate to the reader's stack.

## What this repo is not

- Not a library or framework to `pip install`
- Not a per-repo or per-machine tool
- Not a hobby project you clone and run locally

The Context Store is a **centralized company service**, deployed once by IT/platform engineering. Every LLM client in the organization (Claude Desktop, Cursor, internal agents, scheduled jobs) connects to the same MCP endpoint. Every user — technical or not — contributes through surfaces that don't require git skills.

## How to use this repo

Point Claude Code (or Cursor, Windsurf, any MCP-capable coding agent) at this repo and say:

> *"Stand up lexicon for my company."*

The agent reads `.claude/skills/setup-lexicon.md`, walks you through provisioning decisions (which cloud, which DB, which SSO), references the specialist docs below as needed, and hands you a working service plus a config blob IT can push to every LLM client in the company.

A human engineer can also read these docs top-to-bottom and implement by hand. They're written agent-first but humans are invited.

## Navigation

| File | What it covers |
|------|----------------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Components, data flow, centralized-service principle |
| [`PRIMITIVES.md`](./PRIMITIVES.md) | The six stored primitives: tool, glossary, canonical query, pattern, guardrail, decision |
| [`STORAGE.md`](./STORAGE.md) | Tradeoff analysis: Postgres+pgvector (default), Mongo Atlas, Elastic, what we rejected and why |
| [`MCP_SPEC.md`](./MCP_SPEC.md) | MCP tool surface (read + write) with JSON Schemas and error contracts |
| [`DEPLOYMENT.md`](./DEPLOYMENT.md) | Reference recipes: Supabase+Fly, Neon+Railway, RDS+ECS; secrets; DNS; CI/CD |
| [`AUTH.md`](./AUTH.md) | OIDC for humans, service tokens for MCP, per-user tokens for attribution, threat model |
| [`CONTRIBUTION.md`](./CONTRIBUTION.md) | Five contribution surfaces: Web UI, agent-assisted MCP writes, Slack/Teams bot, REST, scrapers |
| [`INGESTION.md`](./INGESTION.md) | LLM-driven bootstrap; adapters for file-glob, dbt, Notion, Confluence, Slack, Salesforce |
| [`GOVERNANCE.md`](./GOVERNANCE.md) | Audit log, approval workflow, versioning, RBAC, compliance posture |
| [`COMPLIANCE.md`](./COMPLIANCE.md) | Per-framework implementation patterns: HIPAA, SOC 2 Type II, GDPR |
| [`OPERATIONS.md`](./OPERATIONS.md) | Backups, migrations, observability, staleness TTLs, cost monitoring, incident playbook |
| [`.claude/skills/setup-lexicon.md`](./.claude/skills/setup-lexicon.md) | The orchestration skill that drives the agent's end-to-end install |

## Status

Specification, pre-implementation. The docs are the deliverable. Commercialization and a reference implementation are deferred — this repo stays focused on the spec so any team can build their own on their stack.

## License

Apache 2.0 — see [`LICENSE`](./LICENSE).
