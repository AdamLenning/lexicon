---
name: setup-lexicon
description: Stand up a production Context Store (lexicon) for a company. Use when the user says "set up lexicon," "implement the context store from this repo," "deploy lexicon for my company," or asks for help provisioning the Context Store described in this repo. Orchestrates storage selection, schema deployment, MCP server + REST API deployment, Web UI, auth wiring, and initial ingestion. References the specialist docs in this repo (ARCHITECTURE.md, PRIMITIVES.md, STORAGE.md, MCP_SPEC.md, DEPLOYMENT.md, AUTH.md, CONTRIBUTION.md, INGESTION.md, GOVERNANCE.md, COMPLIANCE.md, OPERATIONS.md) as needed.
---

# Setting up lexicon — end-to-end

Your job: take the user from "this repo contains a spec" to "my company has a running Context Store that every agent queries, with auth, contribution surfaces, and a first batch of ingested entries." Target timeframe: one focused working session for the core service; ingestion and rollout follow over the next week.

This skill is an **orchestrator**. It decides when to pull in the specialist docs and keeps the user oriented. Don't paste the specialist docs wholesale into the conversation — reference them by filename and read specific sections as needed.

## Non-negotiable design principles (read these first, apply throughout)

1. **Centralized service, not per-machine.** One deployment, every LLM client in the company connects. See [`ARCHITECTURE.md`](../../ARCHITECTURE.md) §Centralized-service principle.
2. **Nothing auto-publishes.** Every write lands in a review queue. See [`CONTRIBUTION.md`](../../CONTRIBUTION.md) and [`GOVERNANCE.md`](../../GOVERNANCE.md).
3. **Audit everything.** Reads and writes all land in the audit log. See [`GOVERNANCE.md`](../../GOVERNANCE.md) §Audit log.
4. **Per-user tokens.** No shared tokens; auth attributes every action. See [`AUTH.md`](../../AUTH.md).
5. **Ground truth, not a wiki.** Picks matter — curate carefully, bias toward "fewer, better entries" over volume.

## Phase 0 — Preflight and stack discovery

Before proposing any deployment, find out what the user has.

Ask (and wait for answers before moving on):

1. **Cloud:** "Which cloud does your company run on? AWS / GCP / Azure / Vercel-centric / on-prem Kubernetes / mixed?"
2. **Databases:** "What databases are you already running in production? Postgres? Mongo Atlas? Elasticsearch? Anything else?"
3. **Auth:** "What's your current SSO / identity provider? Okta, Entra/Azure AD, Google Workspace, Clerk, Auth0, Descope, custom OIDC, something else?"
4. **Scale:** "Roughly how many employees will use this? How many agent queries per day would you guess?" (Most answers here mean "small enough to not matter" — confirm this.)
5. **Compliance:** "Any compliance framework in play? SOC 2, HIPAA, GDPR residency constraints?"

If the user names a framework, **read [`COMPLIANCE.md`](../../COMPLIANCE.md)** before proposing an architecture — the framework-specific pattern (especially HIPAA's embedding-provider constraint and five-layer PHI-avoidance) changes storage, compute, identity, embedding, and ingestion choices in ways the default recipes don't cover. Do not try to re-derive these patterns from first principles; the doc exists for exactly this moment.

Report back a summary of what you heard before making recommendations. If the user is unsure, assume: Vercel-centric, no existing DB, Clerk for auth, <500 employees, no compliance obligation. Flag that assumption explicitly.

## Phase 1 — Storage decision

Pull from [`STORAGE.md`](../../STORAGE.md) §Decision matrix. Apply the matrix to what the user reported.

Default recommendation: **Postgres + pgvector on Supabase or Neon free tier.**

Override when:
- User already runs Postgres → use their instance (add pgvector extension)
- User runs Mongo Atlas and strongly prefers it → pivot to Atlas Vector Search path (all other docs still apply; schema translates to collections)
- User runs Elasticsearch with k-NN → pivot to Elastic path
- User is AWS-only enterprise → RDS PostgreSQL 16 with pgvector

Document the choice as a two-sentence ADR the user can commit to their infra repo. Example:

> **ADR-0001: Context Store storage**
> We use Postgres + pgvector (Supabase) for the company Context Store. Picked for ACID governance across primitives and portability; alternatives considered were Mongo Atlas (team preference did not exist) and Elasticsearch (ops complexity not justified at our scale).

## Phase 2 — Provision storage

For Supabase (recommended default):

1. `supabase projects create lexicon-<company>` (the user may need to run this in their Supabase dashboard rather than CLI if they prefer)
2. Note the connection string; it goes into `LEXICON_DATABASE_URL`
3. In the SQL editor: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Verify: `SELECT extname FROM pg_extension WHERE extname = 'vector';` returns one row

For other providers: equivalent steps from [`DEPLOYMENT.md`](../../DEPLOYMENT.md) §"Recipe A/B/C."

## Phase 3 — Deploy schema

Read [`PRIMITIVES.md`](../../PRIMITIVES.md) to get the six primitive schemas. Generate migration files for the user's chosen ORM / migration tool (Alembic for Python, Drizzle for TS, Prisma, etc.). The choice should reflect the rest of their backend stack — don't force Python if they're a TS shop.

The migration covers:
- One table per primitive with the fields from `PRIMITIVES.md` §§1–6 + common fields
- One `*_versions` table per primitive (governance — see [`GOVERNANCE.md`](../../GOVERNANCE.md) §Version history)
- One `audit_log` table (see [`GOVERNANCE.md`](../../GOVERNANCE.md) §Audit log)
- Indexes: B-tree on `name`/`term`, GIN on `search_text`, IVFFlat on `embedding`
- Triggers to copy old rows into `_versions` on update

Apply the migration. Verify by listing tables and confirming row counts are zero.

## Phase 4 — Deploy the MCP + REST server

Generate the server code in the user's preferred language. Pick a default that matches their stack:
- TS shop → Node + Hono or Express + official `@modelcontextprotocol/sdk` + Drizzle
- Python shop → FastAPI + `mcp` Python SDK + SQLAlchemy
- Go shop → Go + `mcp-go` + sqlc
- Rust shop → axum + `rmcp` + sqlx

Structure:
- Single container exposes MCP (stdio/SSE) + REST
- Routes mirror [`MCP_SPEC.md`](../../MCP_SPEC.md) (for MCP tools) and [`CONTRIBUTION.md`](../../CONTRIBUTION.md) §"Surface 4: REST API" (for REST endpoints)
- Auth middleware validates per-user / service tokens per [`AUTH.md`](../../AUTH.md)
- Audit middleware logs every call per [`GOVERNANCE.md`](../../GOVERNANCE.md)

Deploy per [`DEPLOYMENT.md`](../../DEPLOYMENT.md). For the default (Vercel-centric) path: Fly.io.

Verify health: `curl https://lexicon-mcp.company.internal/healthz` returns `{status: "ok", db: "ok"}`.

## Phase 5 — Deploy the Web UI

Next.js + shadcn/ui is the recommended default (per [`CONTRIBUTION.md`](../../CONTRIBUTION.md) §"Surface 1: Web UI"). The user can swap if they have a house framework.

Pages in order of priority (ship them progressively):
1. **Home / search** — non-blocking, covers reader + curator reading needs
2. **Primitive CRUD pages** — six forms, auto-generated from the JSON Schemas
3. **Review queue** — curator bread and butter
4. **Audit log view** — admin utility
5. **Admin** (user mgmt, service tokens, ingestion config) — admin utility
6. **Settings / my tokens** — onboarding surface

Deploy to Vercel (or user's equivalent).

## Phase 6 — Wire auth

Follow [`AUTH.md`](../../AUTH.md).

Quick start with Clerk:
1. Create a Clerk app, enable the company's SSO provider (Google Workspace / Okta / Entra) as identity provider
2. Set the Vercel Web UI's `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`
3. Configure the MCP/REST server with `LEXICON_OIDC_ISSUER_URL` pointing at Clerk
4. Implement the token-issuance page at `/onboard` in the Web UI — user logs in, gets a token, gets MCP client configs
5. First user to log in is bootstrapped as `admin` — prompt the user for their email so you can confirm the bootstrap account

Test: sign in as yourself, hit `/onboard`, grab a token, add it to Claude Desktop config, restart, ask Claude `search lexicon for test` — should get an empty-but-wellformed response.

## Phase 7 — Enable contribution surfaces

Prioritize in this order:

1. **Web UI** (already done in Phase 5)
2. **Agent-assisted MCP writes** — already done by Phase 4 (the `propose_entry` tool is part of the MCP server)
3. **Slack bot** — pull [`CONTRIBUTION.md`](../../CONTRIBUTION.md) §"Surface 3" for the spec. Deploy as Vercel serverless.
4. **Ingestion scrapers** — see Phase 8

Skip Slack bot at launch if the user's company isn't on Slack, or defer it to week 2.

## Phase 8 — First ingestion pass

Follow [`INGESTION.md`](../../INGESTION.md) §Bootstrap strategy:

1. **Start narrow.** Pick ONE source the company has the most curated content in. Most common: `dbt` for data teams, `Confluence` for engineering orgs, `Notion` for product orgs.
2. **Run a manual one-shot** limited to a small scope (one dbt project, one Confluence space, one Notion parent page).
3. **Gather curators** for a triage session. Walk through the first 20–50 proposals together. This calibrates what "good" means and shakes out prompt issues early.
4. **Ship fixes** to the classifier prompt based on triage feedback.
5. **Expand** to one more source per week.

Don't fire-hose. Don't connect five sources on day one.

## Phase 9 — Client config distribution

Pick one of the three strategies from [`DEPLOYMENT.md`](../../DEPLOYMENT.md) §"Client configuration distribution":
- MDM push (best for companies with device management)
- Self-service onboarding page (best for most)
- Internal MCP gateway (best for large enterprises with existing gateway infra)

The self-service onboarding page is already built from Phase 6. If that's the chosen strategy, you're done.

Announce: pilot team first (3–10 users), then full rollout after one week of observation.

## Phase 10 — Handoff

Summarize for the user:

- What was built (services, URLs, tokens)
- What's live (which primitive types have entries, which ingestion sources are active)
- What needs ongoing care (curator time commitment per [`OPERATIONS.md`](../../OPERATIONS.md), the review queue)
- What's deferred (any phase skipped, documented as "TODO next week")
- Where to read more (link back to the specialist docs in this repo)

Recommend the user commit:
- The generated server code to their infra repo (or a new `<company>/lexicon` repo)
- The ADR from Phase 1
- A brief runbook pointing at this repo's [`OPERATIONS.md`](../../OPERATIONS.md)

## Recovery paths

| Symptom | Fix |
|---|---|
| `CREATE EXTENSION vector` fails | Provider doesn't support pgvector — confirm Postgres version ≥14, or switch provider |
| Migration fails on `audit_log` | Usually a type mismatch; verify `inet` type is supported (Postgres yes, some aliases no) |
| MCP server starts but `healthz` returns `db: error` | Check `LEXICON_DATABASE_URL` env; confirm outbound connectivity from the host |
| Claude Desktop doesn't show lexicon tools | MCP config path wrong (per OS); or token not valid; try CLI verification first |
| Classifier returns `[]` on every run | Check adapter fetching is returning content; check prompt caching actually enabled; the classifier shouldn't be silent on healthy input |
| Review queue backlog >500 after first ingestion | Expected; curators triage together over a few sessions, not one marathon |
| User gets 403 on every MCP call | Token expired or not issued — re-issue from `/onboard` |

## What you're NOT allowed to do

- Skip the review queue. No auto-publish until the ingestion adapter has demonstrated ≥0.9 precision over a meaningful period per [`GOVERNANCE.md`](../../GOVERNANCE.md) §Approval workflow.
- Deploy without auth. Even "internal" deployments require per-user tokens.
- Put the MCP server on public DNS without an extra layer of defense (internal DNS + VPN / SSO gateway).
- Copy an old DB dump over live data — it destroys audit continuity.
- Auto-generate 500 glossary entries from a "vibe-classify our whole wiki" run on day one. Start narrow.

## When in doubt

Ask the user. Every doubt you paper over becomes an incident later. A 30-second pause to confirm is always better than a mess.
