# Governance

What makes the Context Store trustworthy as company ground truth. Without governance, it's just a shared doc DB; with it, it's infrastructure.

Four pillars:
1. **Audit log** — every read and write, attributed
2. **Approval workflow** — nothing publishes without a human
3. **Version history** — every change preserved
4. **RBAC** — who can do what, enforced

## Audit log

Every MCP tool call, every REST write, every admin action generates an audit log row.

### Schema

```sql
CREATE TABLE audit_log (
  id               BIGSERIAL PRIMARY KEY,
  ts               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_type       TEXT NOT NULL CHECK (actor_type IN ('user', 'service')),
  actor_id         TEXT NOT NULL,           -- user_id or service_name
  on_behalf_of     TEXT,                     -- user_id if service acting for a user
  agent_hint       TEXT,                     -- "claude-desktop", "cursor", "web-ui", "slack-bot"
  action           TEXT NOT NULL,            -- e.g. "mcp.lexicon.search", "rest.glossary.create"
  target_type      TEXT,                     -- primitive type if applicable
  target_id        BIGINT,                   -- primitive row id if applicable
  args             JSONB NOT NULL,           -- request args, PII-redacted
  result_summary   JSONB,                    -- response summary (counts, ids; not full payloads)
  status           TEXT NOT NULL,            -- "ok", "error", "denied"
  error_code       TEXT,
  ip_address       INET,
  user_agent       TEXT,
  request_id       UUID                      -- ties together request tree
);

CREATE INDEX ON audit_log (ts DESC);
CREATE INDEX ON audit_log (actor_id, ts DESC);
CREATE INDEX ON audit_log (target_type, target_id, ts DESC);
CREATE INDEX ON audit_log (action, ts DESC);
```

### PII handling in args

The `args` column is `JSONB` but filtered through a PII redactor before insert. Rules:
- Free-text fields (`query` on `lexicon.search`, `text` on `lexicon.comment`) are stored as-is — they're already visible to the actor
- Payloads containing `email`, `phone`, `ssn`, `address` keys → values redacted to `"<REDACTED>"`
- Payloads larger than 10KB → truncated with an `_args_truncated: true` marker

### Retention

- **Default:** 2 years hot, 5 years cold (ship to S3/GCS after 2 years via nightly export)
- **Compliance-driven extensions:** SOC 2 wants 1 year minimum; HIPAA 6 years; tune to your frameworks

### Query patterns

- **Per-user activity:** `WHERE actor_id = :user_id ORDER BY ts DESC LIMIT 100`
- **Per-entry history:** `WHERE target_type = 'glossary' AND target_id = 42 ORDER BY ts`
- **Usage metrics:** `SELECT action, COUNT(*) FROM audit_log WHERE ts > NOW() - INTERVAL '7 days' GROUP BY 1`
- **Unusual activity:** `SELECT actor_id, COUNT(*) FROM audit_log WHERE ts > NOW() - INTERVAL '1 hour' GROUP BY 1 HAVING COUNT(*) > 500`

### Export to SIEM

A nightly job exports the last day's audit log as newline-delimited JSON to a configured destination (S3 bucket, Splunk HEC, Datadog logs). Schema:

```json
{"ts": "...", "actor": {"type": "user", "id": "..."}, "action": "...", "target": {...}, "status": "ok"}
```

## Approval workflow

Proposed primitives never reach MCP readers until approved.

### States (recap from CONTRIBUTION.md)

```
draft → pending_review → published → (edit) → published@v2 → ...
                      ↘ rejected (terminal)
                              
published → archived (soft-delete; hidden from search but queryable by ID)
```

### Who can approve

- Any `curator` or `admin` can approve any proposal
- A curator cannot approve their own proposal (prevents self-serve), unless the proposal is an edit to their own existing entry below a minor threshold (typo fixes, grammar)
- Admins can override the self-approval restriction with a logged reason

### Approval UX obligations

The UI presents the curator with:
- The proposed content
- Any existing entries that might be duplicates or supersessions (from dedup step in ingestion)
- The source reference (what surface it came from — Web UI, Slack, which ingestion adapter, which document)
- A diff view if this is an edit to an existing entry
- A comment field for notes on the approval or rejection reason

### Auto-approve (off by default)

Per-source configuration can enable auto-approve above a confidence threshold. See [`INGESTION.md`](./INGESTION.md) §"Review queue pressure" for when to turn this on — generally, not at launch.

## Version history

Every update to a published primitive creates a new row in its `_versions` table, not an update-in-place.

### Schema pattern

For each primitive table (`glossary`, `tools`, `canonical_queries`, `query_patterns`, `guardrails`, `decisions`):

```sql
CREATE TABLE glossary_versions (
  version_id     BIGSERIAL PRIMARY KEY,
  glossary_id    BIGINT NOT NULL REFERENCES glossary(id),
  version        INTEGER NOT NULL,
  valid_from     TIMESTAMPTZ NOT NULL,
  valid_until    TIMESTAMPTZ,                    -- NULL = current
  edited_by      TEXT NOT NULL,
  approved_by    TEXT NOT NULL,
  change_reason  TEXT,
  payload        JSONB NOT NULL,                 -- full snapshot of the row at this version
  UNIQUE (glossary_id, version)
);
```

The `glossary` table itself holds only the current version. Old versions live in `glossary_versions`. This keeps hot-path queries fast while preserving history.

### Diff rendering

The Web UI renders diffs between two versions for curator review. For structured fields (`synonyms: string[]`, `related_terms: string[]`), show array diffs. For prose fields (`definition`, `body`), show text diffs.

### Version-aware queries

- `GET /glossary/:id` → current
- `GET /glossary/:id/versions` → list of all versions with authors + timestamps
- `GET /glossary/:id/versions/:version` → specific historical version
- `GET /glossary/:id?as_of=2025-12-01` → snapshot at a specific time

### Restoration

Admins can "restore" an old version, which creates a new version with payload copied from the old one and a `change_reason` pointing at the source version. No direct overwrite.

## RBAC

See [`AUTH.md`](./AUTH.md) §RBAC for role definitions. Governance concerns:

- **Role changes are audit events.** Admins promoting curators, demotions, adding/removing admins — all logged with justification.
- **RBAC evaluation is per-request.** Don't cache role decisions beyond the token TTL.
- **Service roles are narrow.** Each service token has one role: `service`. Service actions that need user-level authority must pass `on_behalf_of`.

## Referential integrity

Because primitive cross-references are soft (string names in JSON, not hard FKs), integrity is a governance concern.

### Lint checks on approval

Before a proposal can be approved, a lint pass runs:
- `Tool` names referenced by `CanonicalQuery.tool` must exist
- `CanonicalQuery` IDs in `QueryPattern.composes_canonical_queries` must exist
- `Decision` IDs in `Glossary.see_also_decisions` must exist
- Circular superseding (`Decision.supersedes_decisions` + `superseded_by`) must be acyclic

Failures surface to the curator with a fix suggestion. The curator can override with a logged reason (e.g., "the tool referenced is being added in a parallel proposal").

### Dangling reference cleanup

A weekly background job finds dangling references and surfaces them on the admin dashboard. Does not auto-fix.

## Freshness and staleness

Entries have a `freshness_ttl_days` field per [`PRIMITIVES.md`](./PRIMITIVES.md). Once `now() - last_reviewed_at > freshness_ttl_days`, the entry is `stale`.

### What staleness does

- **MCP responses** include a `freshness_status` field (`fresh` | `stale` | `never_reviewed`)
- Agents should surface staleness to the user: *"Per the lexicon (last reviewed 18 months ago, marked stale): active customer means …"*
- **Web UI admin dashboard** surfaces stale entries sorted by impact (most-queried stale entries first)
- **Slack nudges** go to entry owners weekly with their stale-entry list

### What staleness doesn't do

- Does not remove the entry from search results
- Does not block reads
- Does not auto-archive

Staleness is a signal, not a gate. Don't over-rotate on this — users prefer a stale-but-known definition over an empty search result.

## Compliance posture

lexicon is **not certified** — it's a specification. What the spec enables:

- **SOC 2 Type II alignment:** audit log, RBAC, access reviews, change management are all hooks; a company implementing this spec has the necessary primitives to pursue SOC 2
- **GDPR readiness:** PII redaction in audit args, right-to-erasure handled by user deactivation + attribution anonymization, data retention policy expressible per-source
- **HIPAA hooks (if needed):** audit log retention ≥6 years, BAA-covered hosting (AWS/GCP/Azure tiers), encryption at rest (provider default) + in transit (TLS)

A company pursuing certification implements this spec in a way that satisfies its auditor. The spec does not include the auditor.

## Anti-patterns

### Silent mass-edit

An admin running `UPDATE glossary SET ...` directly against the DB bypasses audit + version history. **Enforce:** DB-level triggers that block direct writes from non-service identities, OR a lint CI check on any migration PR that modifies data.

### "Trust me" approval

A curator marking every proposal as "approved without review" in a batch panic-clear. **Detect:** dashboard flag when a single curator's median time-to-approve drops below 10 seconds.

### Role inflation

Giving every engineer curator role to reduce curation backlog. **Alternative:** scale curators by domain (one curator per business area), not by volume.

### Store as secret substrate

Putting API keys or passwords in `CanonicalQuery.template`. **Enforce:** proposal-time lint scans for secret patterns (API key shapes, connection strings with passwords); auto-reject with explanation.

## Implementation checklist

For the agent standing this up:

- [ ] `audit_log` table created with indexes
- [ ] Audit middleware wired into MCP server (logs every `call_tool`)
- [ ] Audit middleware wired into REST API (logs every write)
- [ ] PII redactor runs on `args` before insert
- [ ] Per-primitive `_versions` table + trigger to copy old row on update
- [ ] Approval workflow state machine enforced at API layer (can't PATCH without approval path)
- [ ] RBAC decorator on REST endpoints; MCP tools check role for write tools
- [ ] Lint pass on proposal approval (referential integrity checks)
- [ ] Admin dashboard shows audit feed, stale entries, role changes
- [ ] Nightly SIEM export configured
- [ ] Retention policy scheduled job (deletes/archives after TTL)
