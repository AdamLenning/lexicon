# MCP specification

The contract between agents and the Context Store. An implementation that conforms to this spec will work with any MCP-capable client.

## Transport

- **stdio** for per-user local clients (Claude Desktop subprocess, Cursor child process)
- **HTTP + SSE** for shared deployments that many clients connect to
- Both transports carry the same JSON-RPC 2.0 message format per the MCP standard

## Server identity

- **Name:** `lexicon`
- **Version:** the deployed server reports its own version
- **Tools namespace:** all tools prefixed `lexicon.` (e.g., `lexicon.search`)

## Auth

Every request must carry a per-user token. See [`AUTH.md`](./AUTH.md) for how tokens are issued and validated.

- **stdio transport:** token in env var `LEXICON_TOKEN` at server launch. The client (Claude Desktop config, Cursor config) supplies it.
- **HTTP transport:** `Authorization: Bearer <token>` header. SSE streams require the token on connect.

The server logs the authenticated user identity into the audit log for every tool call.

---

## Read tools

Agents call these to ground themselves. All reads count toward audit log.

### `lexicon.search`

Hybrid semantic + lexical search across all primitives.

```json
{
  "name": "lexicon.search",
  "description": "Hybrid semantic + lexical search across all lexicon primitives (tool, glossary, canonical_query, pattern, guardrail, decision). Returns ranked candidates with snippets.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Natural-language query"},
      "types": {
        "type": "array",
        "items": {"type": "string", "enum": ["tool", "glossary", "canonical_query", "pattern", "guardrail", "decision"]},
        "description": "Restrict to these primitive types. Omit or empty array to search all."
      },
      "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
      "include_drafts": {"type": "boolean", "default": false, "description": "Only honored for callers with curator or admin role"}
    },
    "required": ["query"]
  }
}
```

Response:
```json
{
  "results": [
    {
      "type": "glossary",
      "id": 42,
      "name": "active customer",
      "snippet": "An account that (a) has logged in at least once in the past 30 days AND (b) has an active paid subscription...",
      "score": 0.92,
      "freshness_status": "fresh | stale | never_reviewed",
      "last_reviewed_at": "2026-02-15T10:00:00Z"
    }
  ],
  "query_id": "uuid — for feedback/telemetry"
}
```

### `lexicon.get_tool`

```json
{
  "name": "lexicon.get_tool",
  "description": "Return the full tool registry entry for a given tool name. Use when an agent needs connection hints, ownership, refresh cadence, or PII sensitivity of a data source.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"}
    },
    "required": ["name"]
  }
}
```

Response: full `Tool` object per [`PRIMITIVES.md`](./PRIMITIVES.md) §1, or `{"error": "not_found", "suggestions": [...]}` with the top-3 fuzzy-matched names.

### `lexicon.define`

```json
{
  "name": "lexicon.define",
  "description": "Look up the organization's canonical definition of a term. Matches by term, synonym, or fuzzy — returns disambiguation list if multiple matches.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "term": {"type": "string"}
    },
    "required": ["term"]
  }
}
```

Response:
```json
{
  "match_type": "exact | synonym | fuzzy",
  "entry": { /* full GlossaryEntry */ },
  "disambiguation": [ /* alt matches if multiple candidates, otherwise omitted */ ]
}
```

### `lexicon.get_canonical_query`

```json
{
  "name": "lexicon.get_canonical_query",
  "description": "Return a vetted query template with parameter schema, execution hints, and gotchas. Does NOT execute the query — agents run it themselves against the underlying tool.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "params": {"type": "object", "description": "Optional parameter values for the template. If supplied, the response includes a bound preview."}
    },
    "required": ["name"]
  }
}
```

Response: full `CanonicalQuery` object plus an optional `bound_preview` field that shows what the template looks like with the provided params interpolated.

### `lexicon.get_pattern`

```json
{
  "name": "lexicon.get_pattern",
  "description": "Return a cross-source query pattern — a recipe for computing something that spans multiple tools.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"}
    },
    "required": ["name"]
  }
}
```

Response: full `QueryPattern` object per `PRIMITIVES.md` §4.

### `lexicon.list_guardrails`

```json
{
  "name": "lexicon.list_guardrails",
  "description": "List guardrails matching a given scope (tool name, data domain, or '*' for all). Agents MUST call this before executing any query against a scoped tool.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "scope": {"type": "string", "description": "Dotted scope pattern, e.g. 'snowflake.analytics' or '*'"}
    },
    "required": ["scope"]
  }
}
```

Response:
```json
{
  "guardrails": [
    {"id": 17, "name": "no_prod_queries_during_etl", "severity": "block", "rule": "...", "applies_now": true}
  ]
}
```

`applies_now` is computed server-side based on `applies_to_time_windows`.

### `lexicon.recent_decisions`

```json
{
  "name": "lexicon.recent_decisions",
  "description": "Surface recent decision-log entries. Use to answer 'why do we do X this way?' questions.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
      "tags": {"type": "array", "items": {"type": "string"}, "description": "Restrict to entries with any of these tags"}
    }
  }
}
```

---

## Write tools

For agent-assisted contribution. Writes land in the review queue as `draft` or `pending_review`, never auto-publishing.

### `lexicon.propose_entry`

```json
{
  "name": "lexicon.propose_entry",
  "description": "Propose a new primitive entry. Lands in the review queue as pending_review. A curator approves via Web UI or Slack for it to appear in future searches.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "type": {"type": "string", "enum": ["tool", "glossary", "canonical_query", "pattern", "guardrail", "decision"]},
      "payload": {"type": "object", "description": "The primitive-specific fields per PRIMITIVES.md"},
      "source": {"type": "string", "description": "Free text: where this proposal originated (e.g. 'user asked in Claude Desktop')"},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Self-reported confidence"}
    },
    "required": ["type", "payload"]
  }
}
```

Response:
```json
{
  "proposal_id": 123,
  "status": "pending_review",
  "review_url": "https://lexicon.company.internal/review/123",
  "message": "Your proposal is in the review queue. The team owner (if known) has been notified in Slack."
}
```

### `lexicon.comment`

```json
{
  "name": "lexicon.comment",
  "description": "Add a comment to an existing entry — corrections, questions, additional context. Comments are visible to curators and show up in the review queue for attention.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entry_type": {"type": "string", "enum": ["tool", "glossary", "canonical_query", "pattern", "guardrail", "decision"]},
      "entry_id": {"type": "integer"},
      "text": {"type": "string"}
    },
    "required": ["entry_type", "entry_id", "text"]
  }
}
```

Response:
```json
{
  "comment_id": 456,
  "status": "posted"
}
```

---

## Error contracts

All tools return errors as:

```json
{
  "error": {
    "code": "not_found | bad_request | unauthorized | forbidden | rate_limited | internal",
    "message": "human-readable explanation",
    "retry_after_seconds": 10
  }
}
```

Retry semantics:
- `rate_limited`: retry after `retry_after_seconds` with jitter
- `internal` on `search`/`get_*`: retry once immediately, then back off
- `unauthorized`/`forbidden`: do not retry; surface to the user
- `not_found`: not an error on lookups; return `suggestions` if the name was fuzzy-close

## Versioning

The MCP server advertises `server.version` in its initialization response. Breaking tool-signature changes bump the major version; new tools bump minor. Agents should tolerate extra fields in response objects.

## Pagination

Not in v1. Limit capped at 50. If users hit the limit, they refine the query.

## Agent behavior expectations

The server enforces what it can; the rest is social contract. Well-behaved agents:

1. **Call `lexicon.list_guardrails` before executing any query** that touches a real tool (Snowflake, Salesforce, etc.), filtered to that tool's scope
2. **Respect `severity: block` guardrails** by refusing to execute and telling the user why
3. **Prefer canonical queries** from `lexicon.get_canonical_query` over writing their own SQL when one exists for the task
4. **Cite their context sources** in the answer they return to the user (e.g., "per our glossary, active customer means...")
5. **Propose a glossary entry via `lexicon.propose_entry`** when they notice the user using a term that isn't defined

Compliance with the last four is a matter of the client agent's system prompt, not something the server can force.
