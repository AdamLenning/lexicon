# Architecture

A Context Store is a centralized company service with one backend and multiple client-facing surfaces. IT deploys it once; every human and every agent in the company connects to the same instance.

## The centralized-service principle

This is the core design constraint. Everything else follows from it.

- **One source of truth.** Every LLM in the company gets the same answers to the same questions. Ground truth cannot fork.
- **No per-machine state.** A salesperson on a laptop, a data engineer in a repo, and a scheduled job in a CI runner all reach the same service.
- **Async contribution from anywhere.** Non-technical users contribute without cloning repos, opening PRs, or restarting anything.
- **IT-deployable.** A single service, known ops story, auth, RBAC. Not a scattering of per-team snowflakes.

Rejected shapes (and why):
- **Markdown-in-git + local embedding caches:** forks drift, non-technical users can't PR, no MCP service story.
- **SQLite on each user's machine:** single-writer, not shareable, defeats "one source of truth."
- **A library per-repo:** each team becomes an island, ground truth fragments immediately.

## Component diagram

```
   ┌────────────────────┐   ┌─────────────────┐   ┌──────────────────┐
   │  Claude Desktop    │   │  Cursor / Code  │   │ Internal agents  │
   │  (human asks)      │   │  (agent asks)   │   │ (scheduled jobs) │
   └────────────────────┘   └─────────────────┘   └──────────────────┘
            │                       │                      │
            └───────────────────────┴──────────────────────┘
                                    │
                             MCP (stdio/SSE/HTTP)
                                    │
                                    ▼
                         ┌───────────────────────┐
                         │   lexicon MCP server  │  ← reads + writes
                         │   (stateless)         │
                         └───────────────────────┘
                                    │
                                SQL / pgvector
                                    │
                                    ▼
                         ┌───────────────────────┐
                         │   Postgres + pgvector │  ← single source of truth
                         │   (managed or self)   │
                         └───────────────────────┘
                                    ▲
                   ┌────────────────┴─────────────────┐
                   │                                  │
                   │                                  │
   ┌───────────────┴───────────────┐  ┌───────────────┴──────────────┐
   │   REST API (FastAPI/Express)  │  │   Ingestion workers          │
   │   ↓                           │  │   ↓                          │
   │   Web UI (Next.js)            │  │   Adapters:                  │
   │   Slack/Teams bot             │  │     file-glob, dbt, Notion,  │
   │   Automations / CI            │  │     Confluence, Slack,       │
   └───────────────────────────────┘  │     Salesforce, generic HTTP │
                                      └──────────────────────────────┘

   Auth plane: OIDC (humans), per-user tokens (MCP identity), service tokens (server-to-server)
```

## Component responsibilities

**MCP server** — stateless frontend for agents. Read tools query Postgres directly; write tools enqueue proposals for review. Runs anywhere (Fly, Cloud Run, ECS, Kubernetes). Horizontally scalable.

**Postgres + pgvector** — single source of truth. Stores every primitive, every version, every audit log entry. Hosts embeddings in `vector` columns and full-text indexes in `tsvector` generated columns. See [`STORAGE.md`](./STORAGE.md) for why this and not something else.

**REST API** — the contribution-surface backplane. The Web UI, Slack/Teams bot, automations, and ingestion workers all write through this one API. Not exposed to the internet by default — lives behind the same auth as the Web UI.

**Web UI (Next.js)** — human-facing admin. Search, create, edit, approve, review audit log, manage users. Covered in [`CONTRIBUTION.md`](./CONTRIBUTION.md).

**Slack/Teams bot** — async submission surface for non-technical contributors. `/lexicon add glossary "active customer" = "..."` drops a proposal in the review queue with threaded Slack approval.

**Ingestion workers** — scheduled or on-demand jobs that pull from company data sources (wikis, CRM, warehouses) and run LLM-driven classification to propose primitive entries. See [`INGESTION.md`](./INGESTION.md).

**Auth plane** — OIDC for human logins (Clerk/Auth0/Descope), per-user MCP tokens for agent attribution, service tokens for worker-to-DB calls. See [`AUTH.md`](./AUTH.md).

## Representative data flow

A salesperson opens Claude Desktop and asks: *"What does our team mean by 'active customer'?"*

1. Claude Desktop's MCP client sends `tools/call` for `lexicon.define` with `{term: "active customer"}` over the lexicon MCP server's transport
2. MCP server authenticates the request via the user's per-user token, extracts the user identity for audit logging
3. Server runs: `SELECT * FROM glossary WHERE term ILIKE :term OR :term = ANY(synonyms) ORDER BY updated_at DESC LIMIT 1`
4. Found: returns `{term, definition, synonyms, owner, last_reviewed_at, freshness_status}`
5. Server inserts an audit log row: `{user, agent, tool, args, result_id, ts}`
6. Claude Desktop renders the grounded definition; the salesperson gets the right answer

If the term were ambiguous (multiple matches), `lexicon.define` returns a disambiguation array, and Claude asks the user which meaning they want.

If the term were missing, Claude offers to call `lexicon.propose_entry` to submit a draft definition (the salesperson describes it; Claude shapes it; it lands in the review queue for a curator to approve via Web UI or Slack).

## Non-functional requirements

- **Read latency:** p50 < 50ms, p95 < 150ms for `lexicon.search` at 10K–50K entries (pgvector IVFFlat on warm cache)
- **Write latency:** p95 < 200ms for proposal submission (embedding happens async after approval)
- **Availability target:** 99.9% (43 min/month) — stretch goal, depends on hosting choice
- **Durability:** daily PITR-capable Postgres backups, 30-day retention minimum (see [`OPERATIONS.md`](./OPERATIONS.md))
- **Observability:** OpenTelemetry traces MCP → DB; audit log also serves as a usage metric source
- **Security:** MCP server localhost by default in v0 of a deployment, auth-gated before going cross-network — see [`AUTH.md`](./AUTH.md)

## Scaling notes

At 10K–50K entries (typical for mid-size companies), all of the above runs on a single Postgres instance with a single MCP server container. Horizontal scale is a future problem.

If the company is >5000 engineers or the context store grows past ~500K entries, the scaling axes in order of likelihood:
1. Add a cache (Redis) in front of read paths — `lexicon.define` and `lexicon.get_tool` have very high hit rates
2. Promote MCP server to multi-replica (stateless, trivial)
3. Consider read replicas on Postgres
4. Consider partitioning the `audit_log` table by month
5. Migrate vector index from IVFFlat to HNSW

None of these are needed at launch. The docs here assume the single-instance starting point.
