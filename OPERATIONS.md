# Operations

What you run, watch, back up, and fix when something breaks.

## Backups

### Postgres

**Managed providers (Supabase, Neon, RDS, Cloud SQL):**
- All support Point-In-Time Recovery (PITR) out of the box
- **Required retention:** 7 days minimum (all providers default to this or better)
- **Recommended retention:** 30 days for company data
- Verify the configuration — providers default to on, but the retention window varies by tier

**Self-hosted Postgres:**
- `pg_basebackup` nightly + WAL archiving to object storage
- Retention: 30 days full, 90 days WAL for PITR
- **Test restores monthly.** Untested backups are not backups.

### Embedding data is derivative

Embeddings can be regenerated from text any time (at the cost of an embedding API run). You do not need to back them up separately. If a restore brings back text without embeddings, trigger a re-embed job.

### Audit log is special

The audit log is append-only and should never be restored *over* live data — that would lose audit events from between backup and restore. If you need to restore the primitive tables, preserve the live audit log.

## Migrations

### Schema migrations

- **Tool:** Alembic (Python stack), Drizzle Kit (TS stack), or Prisma Migrate. Any proper migration tool.
- **Policy:** every schema change in a migration file, reviewed in a PR, applied on deploy
- **Zero-downtime pattern:** expand-contract
  1. Expand: add new column/table nullable, deploy app that writes both, deploy migration
  2. Backfill: populate new column from old
  3. Contract: app switches reads to new, old column dropped in a later migration after validation window

### Embedding-model migrations

Upgrading the embedding model (Voyage-3 → Voyage-next, OpenAI text-embedding-3 → newer) invalidates existing vectors. Strategy:

1. **Dual-column phase:** add `embedding_next vector(N)` column alongside the existing `embedding`
2. **Background re-embed:** batch job reads each primitive's `search_text`, calls the new model, writes `embedding_next`. Rate-limited to respect API quotas (~1000 rows/min at most providers). Runs over hours or days.
3. **Dual-read phase:** search service queries both columns, merges with RRF for a configurable period (default 1 week)
4. **Cutover:** swap the live column, drop the old one in the next migration
5. **Telemetry check:** compare retrieval recall on known queries before and after; roll back if >5% degradation

Budget for an embedding migration: 1–2 engineer-weeks, $50–200 in API costs depending on store size.

### Primitive schema migrations

Adding a field to an existing primitive:
1. Migration adds the column nullable
2. Classifier prompts updated to emit the new field on future proposals
3. Existing rows have `NULL` for the field — documented behavior
4. Optionally: a one-shot ingestion pass re-proposes fills for existing rows (this goes through the review queue like anything else)

## Observability

### Traces

OpenTelemetry instrumentation from MCP server through REST API through DB. Key spans:
- `mcp.call_tool` — outer span per MCP request
- `rest.handler` — outer span per REST request
- `search.semantic` / `search.lexical` / `search.rerank` — inner spans for search pipeline
- `db.query` — auto-instrumented from the ORM

Export via OTLP to Honeycomb / Datadog / Grafana Tempo.

### Metrics

Derived from traces (via OTel metrics) or Postgres queries:

| Metric | Source | Alert threshold |
|---|---|---|
| `lexicon.mcp.requests.rate` | OTel counter | none (dashboard only) |
| `lexicon.mcp.latency.p95` | OTel histogram | >500ms for 5 min |
| `lexicon.mcp.error_rate` | OTel counter | >1% for 5 min |
| `lexicon.search.recall@10` | synthetic canary | <0.9 for 1 hour |
| `lexicon.db.connections` | Postgres `pg_stat_activity` | >80% of pool for 5 min |
| `lexicon.embedding.api_errors` | OTel counter | >5% for 10 min |
| `lexicon.queue.pending_reviews` | DB count | >500 for 24 hours |

### Logs

Structured JSON. Standard fields: `ts`, `level`, `request_id`, `user_id`, `action`, `latency_ms`, `error`.

Ship to the same destination as traces. Correlate via `request_id`.

### Usage metrics from the audit log

The audit log doubles as a usage analytics source:
- Most-queried terms / tools (for prioritizing curation effort)
- Per-user MCP activity (for spotting disengaged users who haven't adopted)
- Tool-surface mix (MCP vs REST vs Slack — see if any surface is withering)

Surface these on the admin dashboard.

## Staleness TTLs

Default TTLs by primitive type, override per-entry:

| Primitive | Default TTL | Rationale |
|---|---|---|
| `Tool` | 180 days | Tools change slowly; yearly review sufficient |
| `GlossaryEntry` | 365 days | Definitions should be stable; review annually |
| `CanonicalQuery` | 90 days | Queries drift when underlying tables do |
| `QueryPattern` | 180 days | Cross-source recipes change when their components do |
| `Guardrail` | 90 days | Rules about ops windows and access change often |
| `Decision` | `null` (never stale) | Decisions are historical; they don't go stale, they get superseded |

TTL semantics are soft — see [`GOVERNANCE.md`](./GOVERNANCE.md) §Freshness. Stale ≠ hidden.

## Cost monitoring

### Embedding API spend

- Budget alarm per provider at 80% of monthly cap
- Dashboard tile: cumulative spend, rate, top-5 primitives by re-embed frequency
- **Cap:** per-source ingestion has a per-day API spend cap (default $5/source/day); spillover waits for the next run

### Infrastructure spend

- One line per cost center: DB, compute, embeddings, logs, backups, OIDC
- Alert on >30% month-over-month increase

### Cost at reference scale

At 10K–50K entries, ~10K agent queries/day:
- DB: $0–$60/mo (Supabase/Neon free → RDS small)
- Compute: $5–$40/mo (Fly/Railway small)
- Embeddings (steady state, only re-embedding stale entries): $5–$15/mo
- OIDC: $0–$50/mo
- Logs + traces: $0–$25/mo

**Expected total: $20–$200/mo for most deployments.**

## Incident playbook

### "MCP server is down"

1. Check the hosting provider dashboard (Fly / Railway / ECS) — deployment failed? OOM?
2. If healthy but returning 5xx: DB connection pool exhausted? Check `pg_stat_activity`
3. If DB is the culprit: check DB provider status page
4. Restart the MCP server pods. Most issues resolve on restart within minutes.
5. Post-mortem within 48 hours if downtime exceeded 15 min.

### "DB is out of capacity"

Symptoms: slow queries, connection timeouts, provider dashboard showing red.

1. Immediate: scale up the DB tier (all managed providers support this live)
2. Investigate: long-running queries? `SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '30 seconds'`
3. Common cause: a runaway ingestion worker. Kill the run, investigate its classifier loop
4. If data volume is the cause: add a read replica (managed providers support this with a click)

### "Embedding provider outage"

1. `lexicon.search` still returns results via FTS-only — no reads go down
2. Disable ingestion temporarily (admin UI toggle)
3. Resume ingestion when the provider recovers; re-embed queue drains in the background

### "A primitive entry is wrong"

Process matters here. Don't `UPDATE` the DB directly:

1. Open the entry in the Web UI, click "Propose Edit"
2. Fill the correction, submit
3. Self-approve if you're a curator and the change is minor (typo, clarification), otherwise request review from the owner
4. Audit log captures the change; version history preserves the old version

### "Someone leaked a per-user token"

1. Revoke the token via admin UI → it hits the revocation list immediately
2. Issue the user a new token
3. Grep audit log for any suspicious activity under that token's window; check for unusual read volume or writes
4. If writes happened, curators review them; revert via version history if needed
5. Post-mortem on how the token leaked (shared Slack message? committed to repo?) and close the door

### "Classifier is producing garbage"

1. Look at the last N=100 rejected proposals from the affected adapter
2. Identify pattern: is it hallucinating fields? Misclassifying type? Returning empty?
3. Update the classifier prompt in the implementation repo, bump version
4. Re-run the eval golden set — confirm precision/recall unchanged or improved
5. Deploy the updated ingestion worker

## Routine maintenance

### Weekly
- Review the admin dashboard for stale entries, queue depth, usage trends
- Check backup test-restore cron results
- Review audit log anomaly alerts

### Monthly
- Test-restore from backup into a staging DB; verify search works end-to-end
- Rotate service tokens that are past the 180-day mark
- Review cost dashboard for trends

### Quarterly
- Access review: list all users with `curator` and `admin` roles; re-confirm with managers
- Re-evaluate embedding model freshness — has a meaningfully better one shipped?
- Review ingestion adapter golden-set eval numbers; retrain prompts as needed

### Annually
- Rotate HMAC signing secret for service tokens (dual-verify during overlap)
- Full auth flow audit: who can get a token, how it's stored, how it's revoked
- Capacity planning based on growth metrics from audit log

## What an IT/platform team is signing up for

Honest estimate of ongoing ops cost for a mid-size company deployment:

- **Month 1:** ~20 hours (stand-up, initial ingestion, pilot team onboarding)
- **Months 2–3:** ~5 hours/week (curator training, ingestion tuning, Slack bot rollout)
- **Steady state:** ~2 hours/week for one IT/platform engineer (dashboard checks, incident triage, user support) + ~5 hours/week of distributed curator time across the company
- **Quarterly:** ~8 hours for access review, embedding-model review, prompt tuning

It's a real system. Not a hobby-scale one.
