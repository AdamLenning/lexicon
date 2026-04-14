# Primitives

Six primitive types. Every piece of company knowledge an agent needs at grounding time maps onto one of these. Add new primitives only after you've tried and failed to express the knowledge as one of the existing ones.

## Common fields (every primitive has these)

```json
{
  "id": "integer, auto-increment",
  "created_at": "timestamptz",
  "updated_at": "timestamptz",
  "created_by": "string (user id or system)",
  "last_edited_by": "string",
  "status": "draft | pending_review | published | archived",
  "version": "integer, increments on each update",
  "freshness_ttl_days": "integer | null — null means never stale",
  "last_reviewed_at": "timestamptz | null",
  "tags": "string[]",
  "search_text": "generated tsvector (for Postgres FTS)",
  "embedding": "vector(1024) (for pgvector)",
  "embedding_updated_at": "timestamptz"
}
```

`search_text` and `embedding` are generated from primitive-specific source fields — each primitive section below says which.

---

## 1. Tool

A data source or system the agent may query. Warehouse, SaaS API, internal service, reporting tool.

### Purpose
Agent asks *"where do I look for churn?"* or *"what system owns customer email addresses?"* and `lexicon.search` or `lexicon.get_tool` surfaces the right entry.

### Schema
```json
{
  "name": "string, unique, e.g. 'salesforce' or 'snowflake.analytics'",
  "kind": "warehouse | saas | internal_api | reporting | other",
  "description": "string — 2-4 sentences on what this tool is and what's in it",
  "connection_hint": "string | null — how an agent would connect (JDBC URL pattern, API base URL, MCP server name)",
  "owner": "string | null — team or person responsible",
  "refresh_cadence": "string | null — e.g. 'hourly ETL', 'real-time', 'nightly batch'",
  "contains_data_types": "string[] — high-level domains (customers, orders, billing, marketing_events)",
  "pii_sensitivity": "none | low | medium | high",
  "docs_url": "string | null"
}
```

### Example
```json
{
  "name": "snowflake.analytics",
  "kind": "warehouse",
  "description": "Primary analytics warehouse. Holds all curated dbt models — customer metrics, revenue, pipeline. Refreshed from operational systems nightly.",
  "connection_hint": "snowflake://analytics.snowflakecomputing.com/ANALYTICS_DB",
  "owner": "data-platform",
  "refresh_cadence": "nightly 02:00 UTC",
  "contains_data_types": ["customers", "orders", "revenue", "pipeline"],
  "pii_sensitivity": "medium",
  "docs_url": "https://company.atlassian.net/wiki/spaces/DATA/pages/snowflake-analytics"
}
```

### Indexed fields
- `search_text`: `name || ' ' || description || ' ' || array_to_string(contains_data_types, ' ')`
- `embedding`: over the same text

### Cross-references
- Canonical queries reference tools by `name` (soft FK)
- Query patterns reference multiple tools by `name`
- Guardrails may scope to a tool by `name`

---

## 2. Glossary entry

A term with the exact definition this organization uses. The meat of context.

### Purpose
Agent asks *"what do we call an active customer?"* → `lexicon.define("active customer")` → returns the canonical org-specific definition.

### Schema
```json
{
  "term": "string, unique (case-insensitive), e.g. 'active customer'",
  "definition": "string — the canonical definition, 1-5 sentences",
  "synonyms": "string[] — other phrases that map to this term",
  "antonyms": "string[] — explicit opposites, if any (e.g. 'churned customer' for 'active customer')",
  "related_terms": "string[] — other glossary term names for soft linking",
  "owner": "string | null",
  "examples": "string[] — concrete examples or counter-examples",
  "see_also_decisions": "integer[] — decision log IDs explaining why this definition was chosen"
}
```

### Example
```json
{
  "term": "active customer",
  "definition": "An account that (a) has logged in at least once in the past 30 days AND (b) has an active paid subscription (not a trial). Trials on day 31+ still count as 'active' only if they converted.",
  "synonyms": ["active account", "active user", "engaged customer"],
  "antonyms": ["churned customer", "dormant customer"],
  "related_terms": ["MRR", "logo churn", "net revenue retention"],
  "owner": "revenue-ops",
  "examples": [
    "Yes: a Pro plan customer who logged in yesterday",
    "No: a trial user on day 7",
    "No: a former Pro customer who downgraded to free 45 days ago"
  ],
  "see_also_decisions": [12, 47]
}
```

### Indexed fields
- `search_text`: `term || ' ' || definition || ' ' || array_to_string(synonyms, ' ')`
- `embedding`: over the same text

### Cross-references
- Canonical queries often reference glossary terms in their description (soft link)
- Decisions often explain why a glossary definition was chosen (`see_also_decisions`)

---

## 3. Canonical query

A vetted SQL or API call template with parameters. The shape of knowledge senior analysts keep in their heads.

### Purpose
Agent asks *"how do we compute MRR for March?"* → `lexicon.get_canonical_query("mrr_by_month", {start: "2026-03-01"})` → returns a ready-to-run query with gotchas called out.

### Schema
```json
{
  "name": "string, unique snake_case, e.g. 'mrr_by_month'",
  "description": "string — what this query returns, 2-4 sentences",
  "tool": "string — the `tool.name` this runs against",
  "template": "string — the SQL or API call with :named or {braced} parameters",
  "parameters": [
    {
      "name": "string",
      "type": "string | integer | date | etc.",
      "required": "boolean",
      "default": "any | null",
      "description": "string"
    }
  ],
  "expected_output_shape": "string | null — describe columns / keys",
  "gotchas": "string[] — things that bite analysts",
  "related_patterns": "integer[] — IDs of query patterns that use this"
}
```

### Example
```json
{
  "name": "mrr_by_month",
  "description": "Monthly recurring revenue for a given month, using the definition that includes converted trials but excludes not-yet-converted trials. Source of truth for finance reporting.",
  "tool": "snowflake.analytics",
  "template": "SELECT month, SUM(mrr_usd) AS mrr FROM finance.mrr_monthly WHERE month = DATE_TRUNC('month', :month_start::date) GROUP BY month",
  "parameters": [
    {"name": "month_start", "type": "date", "required": true, "description": "First day of the target month"}
  ],
  "expected_output_shape": "one row: {month: date, mrr: numeric(18,2)}",
  "gotchas": [
    "Use `mrr_monthly`, not `mrr_daily` — daily has end-of-day snapshots that can double-count",
    "Truncate to month-start; the table stores month-start not month-end"
  ],
  "related_patterns": [3]
}
```

### Indexed fields
- `search_text`: `name || ' ' || description || ' ' || array_to_string(gotchas, ' ')`
- `embedding`: over `name || ' ' || description`

### Cross-references
- `tool` is a soft FK to `Tool.name`
- Referenced by query patterns (`related_patterns`)

---

## 4. Query pattern

A cross-source recipe. The kind of thing that lives in senior analysts' heads: *"to compute pipeline-to-revenue, join Salesforce opportunities to Stripe charges via `crm_account_id`."*

### Purpose
Agent asks *"how do we compute pipeline-to-revenue?"* → `lexicon.get_pattern("pipeline_to_revenue")` → returns the recipe with the tools it touches and the canonical queries it composes.

### Schema
```json
{
  "name": "string, unique snake_case",
  "description": "string — what question this pattern answers",
  "involves_tools": "string[] — Tool names",
  "composes_canonical_queries": "integer[] — canonical_query IDs",
  "recipe": "string — the step-by-step, in prose and/or pseudocode",
  "when_to_use": "string[] — bullet hints",
  "when_NOT_to_use": "string[] — explicit anti-cases"
}
```

### Example
```json
{
  "name": "pipeline_to_revenue",
  "description": "Join stage-weighted Salesforce pipeline to realized Stripe revenue to measure pipeline conversion.",
  "involves_tools": ["salesforce", "stripe", "snowflake.analytics"],
  "composes_canonical_queries": [5, 8],
  "recipe": "1. Pull SFDC opportunities in stage 'closed_won' with close_date in window\n2. Join to stripe.charges on crm_account_id → stripe_customer_id mapping table\n3. Aggregate realized revenue per opportunity\n4. Compare to pipeline_weighted at T-90",
  "when_to_use": ["Board deck conversion analysis", "Rev ops funnel review"],
  "when_NOT_to_use": ["Monthly MRR reporting — use mrr_by_month instead, this is too slow and too noisy"]
}
```

### Indexed fields
- `search_text`: `name || ' ' || description || ' ' || recipe`
- `embedding`: over the same text

---

## 5. Guardrail

A hard rule the agent must respect. Rules are descriptive in v0; enforcement is a future governance milestone.

### Purpose
Agent sees a matching guardrail in `lexicon.list_guardrails("snowflake.analytics")` or `lexicon.search` and obeys it, OR (future) a policy layer blocks the query outright.

### Schema
```json
{
  "name": "string, unique",
  "scope": "string[] — dotted patterns like 'snowflake.analytics.*' or 'salesforce.contacts'",
  "severity": "info | warn | block",
  "rule": "string — the rule itself, phrased for an LLM to obey",
  "rationale": "string | null — why this rule exists",
  "applies_to_time_windows": "string | null — e.g. 'weekdays 09:00-11:00 America/Los_Angeles'",
  "see_also_decisions": "integer[]"
}
```

### Example
```json
{
  "name": "no_prod_queries_during_etl",
  "scope": ["snowflake.analytics.*"],
  "severity": "block",
  "rule": "Do NOT query snowflake.analytics between 09:00 and 11:00 America/Los_Angeles weekdays. The ETL is running and queries can take 10x longer and burn credits.",
  "rationale": "Reserved compute windows for data-platform ETL. An agent saturating the warehouse during this window delays the nightly report by hours.",
  "applies_to_time_windows": "Mon-Fri 09:00-11:00 America/Los_Angeles",
  "see_also_decisions": [23]
}
```

### Indexed fields
- `search_text`: `name || ' ' || rule || ' ' || rationale`
- `embedding`: over `rule || ' ' || rationale`

---

## 6. Decision

A prose entry explaining *why* a past analytical or operational decision was made. The long-term memory of the data team.

### Purpose
Agent asks *"why do we count trials in MRR starting Q2 2025?"* → `lexicon.search` surfaces the decision entry → agent explains the rationale instead of hallucinating.

### Schema
```json
{
  "title": "string — short summary",
  "body": "string — the full prose",
  "date_decided": "date",
  "author": "string | null",
  "tags": "string[]",
  "related_terms": "string[] — glossary term names",
  "related_tools": "string[] — Tool names",
  "supersedes_decisions": "integer[] — older decision IDs this one overrides",
  "superseded_by": "integer | null"
}
```

### Example
```json
{
  "title": "Count converted trials in MRR starting Q2 2025",
  "body": "In Q2 2025, finance asked for MRR to include trial-to-paid conversions in the month the conversion happened, rather than waiting for the following month's full period of paid revenue. This gives us a leading indicator during the quarter.\n\nThe old metric still exists as `legacy_mrr` for year-over-year comparisons — don't delete it.\n\nSee the glossary entry for 'MRR' for the exact current definition.",
  "date_decided": "2025-04-15",
  "author": "finance-and-data-platform",
  "tags": ["metric-definition", "revenue", "finance"],
  "related_terms": ["MRR", "active customer"],
  "related_tools": ["snowflake.analytics"],
  "supersedes_decisions": [7],
  "superseded_by": null
}
```

### Indexed fields
- `search_text`: `title || ' ' || body`
- `embedding`: over the same text

---

## Primitive relationship diagram

```
         ┌──────────┐
         │  Tool    │◄─────┐
         └──────────┘      │ (soft FK by name)
              ▲             │
              │             │
         ┌────┴─────┐  ┌───┴─────────────┐
         │ Canonical│  │ Query pattern   │
         │  Query   │  │  (composes      │
         └──────────┘  │   canonical     │
              ▲         │   queries)     │
              │         └────────────────┘
              │
         ┌────┴─────┐
         │ Glossary │◄────┐
         └──────────┘      │ (related_terms, see_also_decisions)
              ▲             │
              │             │
         ┌────┴─────┐       │
         │ Decision │───────┘
         └──────────┘
              ▲
              │ (see_also_decisions)
         ┌────┴─────┐
         │ Guardrail│
         └──────────┘
```

References are **soft** (string names or ID arrays in JSON), not hard FKs, to make ingestion forgiving and governance across primitives simpler. Referential integrity is a governance concern, enforced at approval time via lint checks, not at the DB level.

## Adding a new primitive

Before you add one, justify that none of the six above fits. Most "new primitives" end up being specializations of `decision` or variant shapes of `glossary`. If you do add one:
- Same common fields as above
- JSON Schema in this doc
- Hybrid search index fields defined
- Cross-references to existing primitives declared
- MCP read tool spec added to [`MCP_SPEC.md`](./MCP_SPEC.md)
