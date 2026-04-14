# lexicon — Context Store spec

> A specification for a company-wide **Context Store** — the layer every AI agent in your organization queries before it queries anything else.

Feature store is to ML what context store is to agents. `lexicon` stores the terminology, tool registry, canonical queries, guardrails, and decision log your team already uses informally, and serves them to every MCP-capable AI client in the company so that agents ground themselves in *your* organization before they act.

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
| [`OPERATIONS.md`](./OPERATIONS.md) | Backups, migrations, observability, staleness TTLs, cost monitoring, incident playbook |
| [`.claude/skills/setup-lexicon.md`](./.claude/skills/setup-lexicon.md) | The orchestration skill that drives the agent's end-to-end install |

## Status

Specification, pre-implementation. The docs are the deliverable. Commercialization and a reference implementation are deferred — this repo stays focused on the spec so any team can build their own on their stack.

## License

Apache 2.0 — see [`LICENSE`](./LICENSE).
