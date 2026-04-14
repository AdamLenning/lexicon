# Storage

This doc presents the tradeoffs honestly, names a default, and gives the agent a decision matrix to adapt when the user's shop has existing infra.

## TL;DR for the agent

**Default recommendation: Postgres + pgvector.** Picked for governance (ACID), cross-primitive joins, portability across managed Postgres services, cheap cost at this scale, and mature ops tooling.

**Swap the default if the user already runs:**
- Mongo Atlas with Atlas Vector Search → use it (doc DB path)
- Elasticsearch with k-NN → use it (great for lexical fuzzy)
- Only BigQuery/Snowflake → still use Postgres for the store (warehouses are wrong shape for mutable application state)

**Never pick these for a company-wide Context Store:**
- Markdown files in git — can't be an MCP service, no non-technical contribution surface, fork drift
- SQLite (even with sqlite-vec) — single-writer/local, can't be shared across a company
- Pinecone / Weaviate alone — vector DB alone gives you no governance story for the metadata

## Quick quality comparison (for LLM retrieval at 10K–50K entries)

| Engine | Lexical fuzzy | Semantic (vector) | Hybrid merge | LLM retrieval quality | Governance story |
|---|---|---|---|---|---|
| Postgres + pgvector | Good (FTS + `pg_trgm`) | Excellent | Manual RRF (~20 lines SQL) | ~95% of optimal | Strong — ACID, real joins |
| Mongo Atlas (+ Search + Vector Search) | Excellent (Lucene) | Excellent | Native `$rankFusion` | ~95% of optimal | Weaker — app-layer sagas for multi-doc |
| Elasticsearch (+ k-NN) | Best (fuzzy, synonyms, stemming, learning-to-rank) | Excellent | Native hybrid | ~95% of optimal | Weak — heavy ops, non-ACID |
| SQLite + sqlite-vec | Basic | Excellent | Manual | ~90% of optimal | N/A — single-writer, not a service |
| Plain Mongo (no Atlas Search) | Weak (regex only) | Requires separate vector DB | Multi-system | ~70% of optimal | Weak |

**Upshot:** at company-scale (small), every viable hybrid-capable option lands within 5% of optimal LLM retrieval quality. Embeddings and LLM-forgiveness dominate; lexical-engine sophistication is near-invisible to an LLM consumer. **Pick based on governance, portability, ops fit, and what your team already runs — not search quality.** The section below explains why that leads to Postgres + pgvector as the default.

## The scale assumption (critical)

A typical company Context Store tops out around **10K–50K entries** total:
- 500–5,000 Confluence/Notion pages worth of decision/how-to content
- 100–500 dbt models / metrics / tools
- 50–500 glossary terms
- 10–100 canonical queries
- 10–100 guardrails
- ~200–1000 decisions accumulated over 2 years

Each entry: ~1–3KB text + a 4KB embedding. **Total dataset: 50MB–200MB.**

At this scale, virtually any modern store runs sub-10ms hybrid queries with room to spare. Scale is not the deciding factor — governance, portability, and contribution concurrency are.

## Fuzzy match quality for LLMs (the question that comes up)

Does an LLM get better fuzzy matches from a relational DB or a document DB?

**At this scale, no meaningful difference.** Here's the breakdown:

- **Lexical fuzzy (typos, stems):** Elasticsearch > Postgres FTS + `pg_trgm` > plain Mongo > Firestore. Elastic's `fuzziness: AUTO` is best-in-class. pg_trgm gets you ~90% of Elastic's quality for English.
- **Semantic fuzzy (vector):** pgvector ≈ Atlas Vector Search ≈ Elastic k-NN ≈ sqlite-vec. All use cosine similarity against the same class of embeddings. Quality is a function of the embedding model (Voyage-3, text-embedding-3-large), not the store.
- **Hybrid merge (what matters for LLMs):** both relational and doc-DB stacks can do RRF (reciprocal rank fusion). Elastic ships it wired; pgvector needs ~20 lines of SQL.

**LLM forgiveness factor:** if you return the top 20 candidates with decent recall, the LLM picks the right one even at 70% retrieval precision. This makes the last 5–10% of "perfect fuzzy match" quality essentially free optionality. Don't choose a store to chase it.

## Option-by-option tradeoff analysis

### Postgres + pgvector (recommended default)

**Wins:**
- **ACID across primitives.** Audit log, approval state, versioning — all require multi-table atomicity. Postgres is free; every doc DB requires application-layer sagas.
- **Cross-primitive SQL.** "Find canonical queries that reference tool X and have a block-severity guardrail" is one join in SQL; multiple pipeline stages in Mongo.
- **Portable.** Supabase, Neon, RDS, Cloud SQL, Azure Database for PostgreSQL — identical SQL, different managed service. Avoids lock-in.
- **Mature tooling.** Alembic, SQLAlchemy, pgAdmin, Datadog integration, every ORM in existence.
- **Cheap.** Supabase free tier handles it, Neon free tier handles it, RDS t4g.micro ~$15/mo. Pricing is predictable.
- **Structured primitives fit.** Schema gives you documentation for free.

**Loses:**
- Schema migrations have ops cost. Every primitive field change → Alembic migration.
- Vector index tuning (IVFFlat vs HNSW parameters) matters past ~100K vectors; but you're not there.
- Full-text search weaker than Elastic for advanced relevance tuning.
- Horizontal write scale is a project if you ever hit it (you won't at this scale).

**Cost at 10K–50K entries:**
- Supabase free: $0/mo (500MB storage, 1GB bandwidth, enough)
- Neon free: $0/mo (3GB storage, fine)
- RDS t4g.micro: ~$15/mo
- Managed enterprise (Cloud SQL, Aurora): $50–200/mo

### Mongo Atlas + Atlas Vector Search

**Wins:**
- Entries-as-documents matches the natural shape of primitives
- Schema flexibility — add fields without migrations (useful while the primitive model evolves)
- Atlas Vector Search is genuinely good (Lucene + k-NN, hybrid queries supported natively)
- Horizontal scale built in (not needed, but free)

**Loses:**
- Multi-document transactions exist but are slower and more fragile than Postgres transactions
- Cross-primitive queries via `$lookup` are clunky and slow
- Vendor lock-in to Atlas (self-hosted Mongo's Vector Search story is worse)
- Costs jump past free tier: Atlas M10 starts at ~$60/mo, Vector Search adds more
- Less portable than Postgres

**Use it if:** your team already runs Mongo Atlas in production. Don't stand it up fresh just for this.

### Elasticsearch (with k-NN)

**Wins:**
- Best-in-class lexical search (fuzzy, synonyms, stemming per language, learning-to-rank plugin)
- k-NN for vectors is solid, hybrid queries native
- Powerful aggregations if you want analytics over the store itself

**Loses:**
- Ops-heavy — node sizing, shard management, JVM tuning
- Weaker transactional story than Postgres
- Elastic Cloud starts ~$95/mo (deployment tier) — meaningfully more expensive
- Self-hosted Elastic is a commitment

**Use it if:** your team already runs Elasticsearch and has ops bandwidth. Not a greenfield pick.

### Postgres + JSONB + pgvector (hybrid)

**Wins:**
- Schema flexibility per-entry inside a relational engine — get doc-DB feel for the field bag while keeping SQL for relations
- Full ACID, cross-primitive joins, pgvector all still work
- No second database to operate

**Loses:**
- JSONB query syntax is awkward (`->`, `->>`, `@>`) compared to typed columns
- You give up some of the schema-as-documentation value
- Validation happens at the application layer instead of the DB

**Use it if:** you're early and expect primitive schemas to churn frequently. Migrate to typed columns once things stabilize.

### Vector DB (Pinecone/Weaviate/Qdrant) + separate metadata store

**Wins:**
- Best-in-class vector recall at very high scale
- Many support metadata filtering that rivals doc DBs

**Loses:**
- Two systems to operate
- No strong governance story without building it yourself
- Overkill at 10K–50K entries
- Cost: Pinecone starts ~$70/mo for production

**Use it if:** you're past 10M vectors or have extreme latency requirements. Not for a company Context Store v1.

## Options explicitly rejected (and why)

### Markdown files in git

Tempting because the content *is* markdown-shaped. But:
- Can't be an MCP service — the centralized-service requirement fails immediately
- Non-technical users can't contribute — requires clone, edit, PR, merge, wait for CI
- Ground truth forks across users' local clones; "did you pull latest?" becomes a question people ask
- No audit of who read what
- No approval flow that isn't a PR (which has high friction for a glossary entry)
- Search requires a local embedding cache that each user has to maintain

Works only for a single-person repo. Fails for a company service.

### SQLite + sqlite-vec

Tempting because zero-ops. But:
- Single-writer concurrency — one writer at a time, the library is for embedded use
- Not shareable across a company — each machine would have its own DB
- If you access it over a network you've rebuilt a DB server out of SQLite, at which point just use Postgres

Works for a personal-use Context Store on one laptop. Fails for a company service.

### A plain vector DB with no metadata store

Pinecone et al. store `{id, vector, metadata-blob}`. They're not designed for the audit-log, approval-state, version-history needs of governance. You'd end up with Pinecone + Postgres anyway. Just use Postgres + pgvector and skip the second system.

## Decision matrix (the agent applies this)

| User's existing stack | Recommend |
|---|---|
| Postgres (any managed or self-hosted, ≥14) | Add `pgvector` extension, use existing instance in a dedicated database |
| Mongo Atlas in production | Use Atlas with Vector Search — doc DB path |
| Elasticsearch in production with k-NN available | Use Elastic |
| BigQuery/Snowflake only (no OLTP store) | Stand up Supabase or Neon (Postgres + pgvector) — don't put mutable app state in the warehouse |
| Kubernetes with existing operators | Consider CNPG (cloud-native-pg) for Postgres |
| Vercel shop, no DB yet | Supabase or Neon (one-click from Vercel) |
| AWS-only enterprise | RDS PostgreSQL with pgvector (supported since PG 15) |
| Azure enterprise | Azure Database for PostgreSQL + pgvector |
| GCP enterprise | Cloud SQL for PostgreSQL + pgvector |
| Truly nothing; greenfield; small team | Supabase free tier |

## Migration paths (for later, not blocking)

- **pgvector IVFFlat → HNSW:** when vector count crosses ~100K, swap index type. Zero app-code changes.
- **Single Postgres → read replica:** when read QPS crosses single-instance capacity. Zero app-code changes if reads are routed by DSN.
- **Single Postgres → sharded Postgres (Citus):** when writes saturate a single node. This is far in the future and may never come.
- **Pgvector → dedicated vector DB (Pinecone/Weaviate):** only if recall@k becomes measurably worse than acceptable at scale. This is a real migration, not cheap.

## What the agent should actually do

1. Ask the user what databases their company already runs
2. Apply the matrix above
3. Unless the user has a strong existing preference, default to Postgres + pgvector via Supabase or Neon
4. Document the choice in a short ADR committed to the company's infra repo — the Context Store's storage is a decision that deserves preservation
