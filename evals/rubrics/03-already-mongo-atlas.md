# Rubric 03: Already running Mongo Atlas

Each dimension is pass/fail worth 1 point. Total: 10 points.

## Dimensions

1. **Recommends Atlas for this user** — Per `STORAGE.md` decision matrix row "Mongo Atlas in production," the recommendation is to use what they have. Agent picks Yes.

2. **Atlas recommendation is nuanced, not zealous** — Agent doesn't pretend Atlas is "just as good" at everything; surfaces the honest tradeoffs from `STORAGE.md` (governance complexity, cross-primitive queries, vendor lock-in).

3. **Calls out Atlas Vector Search specifically** — Not plain Mongo. Atlas Vector Search is what makes this viable, per `STORAGE.md` §Mongo Atlas.

4. **Translates Postgres-specific pieces** — Identifies which spec pieces need changes:
   - Schema migrations → collection schema validators (or nothing — flexibility is Mongo's appeal)
   - `_versions` tables → a versioning collection or per-doc embedded history
   - `tsvector` + GIN → Atlas Search text indexes
   - `vector(1024)` + IVFFlat → Atlas Vector Search k-NN index
   - Multi-table ACID → Atlas multi-document transactions (with caveats)

5. **Identifies what carries over unchanged** — At minimum:
   - MCP tool contract (`MCP_SPEC.md` is store-agnostic)
   - Primitive data shapes (`PRIMITIVES.md` translates to doc shapes trivially)
   - Contribution surfaces (`CONTRIBUTION.md`)
   - Auth model (`AUTH.md`)
   - Ingestion classifier pattern (`INGESTION.md`)

6. **Acknowledges governance is the real cost** — From `STORAGE.md` + `GOVERNANCE.md`: audit log integrity, approval workflow atomicity, version history — all need app-layer care with Mongo that Postgres gives for free.

7. **Cross-primitive queries called out as harder** — Mongo `$lookup` vs SQL joins. Honest tradeoff per `STORAGE.md`.

8. **Doesn't recommend adding Postgres against the user's stated preference** — The user explicitly said they don't want Postgres. Agent respects this. Acceptable to note "here's what you lose" but not "you should use Postgres anyway."

9. **Deployment pieces still work** — MCP server + REST still deploy the same way (ECS/Cloud Run/whatever they use). Only the DB backing store changes.

10. **Doc citations accurate** — No invented sections, no misattributed claims.

## Failure modes to watch for

- Pretends Atlas is "just as governance-friendly" as Postgres — it's not, be honest
- Recommends adding Postgres despite user's clear preference
- Misses that plain Mongo (without Atlas Search) isn't viable for this use case
- Claims Atlas has "ACID across collections" — multi-doc transactions exist but have real limits
- Recommends a separate vector DB (Pinecone) stitched to Mongo — unnecessary, Atlas Vector Search works
