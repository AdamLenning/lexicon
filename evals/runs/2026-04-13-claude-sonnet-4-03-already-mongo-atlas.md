# Run: 03-already-mongo-atlas (2026-04-13, claude-sonnet-4)

## Agent output (condensed)

### 1. Should we use Mongo Atlas?

**Yes.** Cites `STORAGE.md` decision matrix row for "Mongo Atlas in production." Honest math: at 10K–50K entries, Atlas Vector Search ≈ pgvector on retrieval quality; fighting 5 years of Mongo expertise and ops runbooks for marginal improvement is the wrong trade. Caveat: don't go Atlas if you're separately evaluating migrating off Mongo anyway.

### 2. Translations needed

- Schema: tables → collections; `tsvector` / `vector(1024)` → app-layer `embedding: double[]` + text-indexed field; `id` → `ObjectId` (or counter for stable FK-style refs)
- Indexing: GIN → Atlas Search (Lucene), IVFFlat → Atlas Vector Search (`numDimensions: 1024, similarity: cosine`), B-tree → standard Mongo indexes, `CREATE EXTENSION vector` → M10+ tier requirement
- Hybrid search: pgvector+SQL RRF → `$rankFusion` aggregation (caveat: syntax evolved through 2024, verify against current docs)
- Governance: `audit_log` → indexed (or capped) collection; per-primitive `*_versions` → single `versions` collection; no `GENERATED ALWAYS AS` columns (compute in app or use Atlas Search covering multi-field)
- Version history triggers: app-layer wrapper OR Atlas database triggers with pre-image
- Transactions: use `session.withTransaction()`; keep short; never call embedding APIs inside a transaction
- Cross-primitive queries: JOIN → `$lookup` pipelines (uglier, fine at scale)
- Deployment: Atlas M10+ on existing Atlas org, same VPC peering; MCP/REST/Web UI/bot unchanged
- Migration tooling: `migrate-mongo` or similar; `$jsonSchema` validators as safety net
- Embedding migrations: dual-field on same doc + second Vector Search index

### 3. Unchanged

- MCP spec (`MCP_SPEC.md`) entirely — storage-agnostic by design
- `ARCHITECTURE.md` (swap box label), `AUTH.md` (all), `CONTRIBUTION.md` (all 5 surfaces, review-queue state machine lives in app code)
- `INGESTION.md` — all adapters, classifier shape, dedup, eval methodology
- `GOVERNANCE.md` conceptually; schemas translate, model identical
- `OPERATIONS.md` conceptually (swap "Postgres" for "Atlas cluster")
- Setup skill phases 0, 4, 5, 6, 7, 8, 9, 10 — only 2 and 3 need rewrite

### 4. Specifically harder with Atlas

1. Multi-document ACID weaker — transaction size/op count/timeout limits
2. Cross-primitive queries need `$lookup` pipelines or multi-round-trips
3. No DB-level triggers as blocking constraints (app-layer enforcement)
4. `audit_log` grows unbounded — plan online archival / TTL from day one
5. Atlas Vector Search needs M10+ ($60/mo floor, no free tier)
6. Portability story worse (Atlas-specific APIs, self-hosted Mongo's vector story weaker)
7. Full-text tuning (Lucene analyzers, synonym mappings) has learning curve
8. Schema enforcement opt-in — add `$jsonSchema` validators on every collection day one

### 5. Atlas features to lean on

- Atlas Vector Search, Atlas Search, `$rankFusion`, `$jsonSchema` validation
- Atlas Triggers (version-copy, async side effects)
- Change streams (Slack bot subscribe to new proposals)
- Online Archive (audit log cold tier)
- Atlas private endpoints / VPC peering
- Atlas RBAC + DB users (narrow service accounts; audit_log writer separate)
- Atlas Backup / PITR
- Atlas Application Services (optional REST/webhook hosting)
- Queryable Encryption / CSFLE (optional for PCI/PII)

### 6. Docs consulted

All 12 repo docs.

---EVAL METADATA---

Agent hit Context7 quota for MongoDB docs lookup; correctly flagged uncertainty and told user to validate `$rankFusion` syntax against current MongoDB docs before implementation.

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | Recommends Atlas for this user | PASS | Decisive "Yes." |
| 2 | Nuanced, not zealous | PASS | Names governance complexity, cross-primitive cost, vendor lock-in. |
| 3 | Calls out Atlas Vector Search specifically | PASS | Multiple mentions; flags M10+ tier requirement. |
| 4 | Translates Postgres-specific pieces | PASS | Schema, indexing, hybrid merge, governance, triggers, transactions — all mapped. |
| 5 | Identifies what carries over unchanged | PASS | MCP spec, auth, contribution, ingestion, architecture (with box swap), governance and operations conceptually. |
| 6 | Acknowledges governance is the real cost | PASS | "Multi-document ACID is weaker" + "No DB-level triggers as safety net." |
| 7 | Cross-primitive queries called out as harder | PASS | SQL joins → `$lookup` pipelines, uglier and slower. |
| 8 | Doesn't recommend adding Postgres | PASS | "Bite the bullet on Atlas, not on Postgres." |
| 9 | Deployment pieces still work | PASS | "MCP server, REST API, Web UI, Slack bot all deploy unchanged." |
| 10 | Doc citations accurate | PASS | All sections verified. |

**Score: 10/10**

## Notes

Strongest insights:
- **M10+ tier requirement surfaced** — cost floor ~$60/mo vs $0 on Supabase/Neon. Not in the spec but an honest tradeoff.
- **Embedding-inversion caveat** — "embeddings are not a one-way hash" — sophisticated security thinking.
- **Forthright about quota limitation** — agent hit Context7 quota, didn't hide it, told the user to verify `$rankFusion` syntax before implementation.
- **Schema validators on day one** — catch the fact that Mongo schema enforcement is opt-in, unlike Postgres.
- **Audit log online-archival** via Atlas native tiering replaces the spec's "ship to S3 after 2 years" pattern with a cleaner vendor-native equivalent.

No spec gaps surfaced. The agent demonstrated the spec is storage-agnostic enough to support a clean Atlas pivot.
