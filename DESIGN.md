# Design: `lexicon` — a Context Store for AI agents

This is the long form. The README is for adoption; this file is for people deciding whether the idea holds up.

## 1. The problem

An AI agent connected to your organization's data tools has no idea:

- **Where things live.** Is customer lifetime value in Snowflake? In Salesforce? In a Stripe export?
- **What things mean.** Your "active customer" might be "logged in within 30 days AND paying." Theirs might be "any account not explicitly churned." The agent doesn't know.
- **How to ask.** SQL against your warehouse has 12 gotchas the senior analyst knows and nobody wrote down.
- **When not to ask.** Nobody told the agent that hitting the prod replica between 9–11 AM PT during nightly ETL is a fireable offense.

Without grounding, the agent generates plausible-looking queries against plausible-looking tools and returns plausible-looking answers. "Plausible-looking" is the whole hallucination problem in a new dress.

## 2. Why now

In late 2024 Anthropic open-sourced the Model Context Protocol (MCP). By early 2026 every meaningful data platform has shipped an MCP server — dbt, Omni, Looker, BigQuery, Snowflake Cortex, Cube. Gartner projects 75% of gateway vendors will ship MCP features by end of 2026.

All of those MCP servers are **single-source**. They wrap one warehouse or one BI tool. They are excellent at answering "what's MRR?" given a curated metrics definition in that system. They are useless at answering:

- "Which tool do I even ask about MRR?"
- "When I got conflicting MRR numbers from two tools, which is authoritative?"
- "What's the canonical way our team computes pipeline-to-revenue across Salesforce and Stripe?"

Those are context-store questions. The category doesn't have a name yet. This repo is a bet that it's about to.

## 3. Core primitives

`lexicon` stores six primitive types. Everything the agent needs at context-construction time maps onto one of these.

### 3.1 Tool registry
What tools/sources exist, what data lives where, refresh cadence, ownership, connection hints. Agent asks: *"Where do I look for churn?"*

### 3.2 Glossary / terminology
"active customer", "MRR", "churn", "SQO" — with the exact definition *this* org uses, the date the definition was last revised, and who owns it.

### 3.3 Canonical queries
Vetted SQL/API templates. Parameters. Expected output shape. Known gotchas ("this query ignores trial accounts; use `mrr_with_trials` if you need them").

### 3.4 Query patterns
Cross-source recipes. "To compute pipeline-to-revenue, join `salesforce.opportunities` to `stripe.charges` via `crm_account_id`, keeping only opportunities in stage `closed_won`." These are the pieces that live in senior analysts' heads.

### 3.5 Guardrails
Hard rules. "Never query the prod replica between 9–11 AM PT." "Always filter by `tenant_id`." "PII columns: email, phone, ssn — redact before returning to LLM." Scope-keyed so `list_guardrails("salesforce.contacts")` returns what applies.

### 3.6 Decision log
Prose entries explaining *why* past analytical decisions were made. "In 2025-Q2 we started counting trials in MRR because finance wanted leading indicators — the old metric lives in `legacy_mrr` for year-over-year continuity."

## 4. Architecture

- **Storage:** Postgres + `pgvector`. The dedicated docker-compose container runs on port 5433 to avoid conflict with existing local Postgres instances. Volumes are persistent by default. BYO Postgres is supported via `LEXICON_DATABASE_URL`.
- **Retrieval:** hybrid search — pgvector for semantic, Postgres FTS for lexical, entity-type-aware ranking that learns which primitive types match which query shapes.
- **Serving:** MCP-first. Five tools (Section 6 of README). REST API mirrors the same primitives for human curation.
- **Auth (v0):** localhost-only, no auth. Documented trust boundary: if you let untrusted code run on the box, it can read and write your context store. For v1, API-token mode when binding to non-loopback.
- **Ingestion:** a separate pipeline, described in Section 5.

## 5. The bootstrap skill

The single riskiest engineering bet in this project: can an LLM, given a pile of your existing docs (dbt-docs, Notion, Confluence, file-glob of markdown, SQL schema dumps), propose high-precision draft entries that a human only needs to lightly review?

**Flow:**
1. User points `lexicon ingest <adapter>` at a source
2. Adapter pulls raw content
3. An Anthropic-API-driven skill (with aggressive prompt caching) proposes entries, one per primitive type, with confidence scores
4. Proposals land in a review queue (`lexicon review`)
5. Human accepts, edits, or rejects — accepted entries write to the primitive tables
6. Rejected proposals feed back into the eval set

**Eval methodology:**
- A small hand-curated golden dataset per adapter (dbt manifest → expected glossary/tool entries)
- Precision-oriented: false positives are worse than false negatives
- Tracked across model versions so prompt improvements are visible

**Why it matters:** curation is the real labor. If bootstrap produces noise, customers never populate the store and the product fails. If it produces clean drafts, the store fills up in hours instead of quarters, and curation becomes a background chore instead of a blocking project.

## 6. Governance & trust

- **Audit log:** every read and write, with agent identity when MCP context supplies it
- **Versioning:** every primitive has a version history; changes include author, timestamp, diff
- **Approval workflow:** draft entries (from bootstrap or REST POST) require approval before they're served to MCP clients by default
- **RBAC (v1+):** team-scoped entries, read-only vs curator vs admin roles

## 7. Competitive landscape

| Product | Category | Overlap with `lexicon` |
|---|---|---|
| dbt Semantic Layer + dbt MCP | Metrics layer for dbt warehouses | Metrics only, single-warehouse |
| Cube.dev ($80/dev/mo Premium) | Semantic layer + caching for BI | BI-focused; agent story is secondary |
| Omni MCP | BI tool with native MCP | Tied to Omni; single source |
| Snowflake Cortex / BigQuery MCP | Warehouse-native agent connectors | Warehouse-locked; no cross-tool story |
| LangChain / LlamaIndex memory | Runtime agent memory | Conversational state, not curated org knowledge |
| Atlan / Alation / Collibra / Secoda | Data catalogs | Human-facing UI; `lexicon` is machine-facing API |

**Differentiator axes:**
- LLM-native (designed for MCP, not retrofitted)
- Cross-source (not warehouse-bound)
- Governance built in (audit, versioning, approval)
- Bootstrap-from-docs (LLM-driven ingestion, not manual catalog curation)
- OSS, self-hosted, BYO-or-bundled Postgres

## 8. Open questions & risks

- **Non-determinism in consumption.** Even with curated context, the LLM may misuse it. We reduce variance but can't eliminate it. Mitigation: structured tool outputs, forcing the LLM to cite which primitive it used.
- **Who owns curation?** Data teams hate owning yet another catalog. Engineering teams don't know the terminology. Analytics engineers are the natural owner, but they're already overloaded. The bootstrap skill + Claude skill workflow is our bet that curation becomes low-friction enough that *anyone* can do it.
- **Staleness.** A glossary entry from 2024 that describes how "active customer" was defined then is worse than no entry if the definition has changed. Mitigation: freshness scores, TTLs per primitive type, agent can be told "only surface entries updated within N days."
- **Category absorption risk.** dbt could add cross-tool context features. BigQuery/Snowflake could add an "org context" MCP layer. If any of them does this well, `lexicon` needs a stronger wedge. Current wedge: the OSS + multi-source + bootstrap story is hard for a cloud vendor to match without cannibalizing their own platform lock-in.

## 9. Roadmap

- **v0 (this scaffold):** repo, MCP stubs, docker-compose, Claude skill, empty primitive schemas. No business logic.
- **v0.1:** working MCP server — all 5 tools functional against seeded DB. REST admin CRUD. pgvector hybrid search.
- **v0.2:** bootstrap skill GA — file-glob + dbt adapters working end-to-end with eval harness.
- **v0.3:** Notion + Confluence adapters. Audit log. Approval workflow.
- **v0.4:** policy enforcement (guardrails block queries, not just describe them).
- **v1.0:** admin UI, RBAC, API-token auth.

## Appendix A: Why "Context Store" and not another name

- "Knowledge layer" / "semantic layer" — people will assume it's a metrics layer like dbt/Cube and stop reading.
- "Agent memory" — overloaded. Memory usually means conversational or episodic state.
- "AI schema registry" — too narrow. Schemas are one of six primitives.
- "Data context protocol" — sounds like a protocol competitor to MCP, which it isn't.

"Context store" mirrors the `<X> store` pattern (feature store, vector store) and describes what the thing *does* — dynamically assemble an agent's context from durable curated sources.
