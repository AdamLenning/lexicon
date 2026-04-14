# Contribution

Five surfaces for getting knowledge into the Context Store. Every surface writes through the same REST API and enforces the same review queue.

The unifying principle: **nothing auto-publishes.** Every write lands as `pending_review`. A curator approves it via any of the surfaces. This is what keeps the store trustworthy as the organization's source of truth.

## Review queue state machine

```
                 ┌──────────────────┐
                 │ any surface      │
                 │ posts a proposal │
                 └────────┬─────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  draft    │ ◄── author is still editing (Web UI / Slack thread)
                    └─────┬─────┘
                          │  submit
                          ▼
                 ┌────────────────────┐
                 │  pending_review    │ ◄── visible to curators; not returned by MCP
                 └──┬───────────┬─────┘
           approve  │           │  reject
                    ▼           ▼
           ┌─────────────┐   ┌───────────┐
           │  published  │   │ rejected  │ (terminal; reason logged)
           └──────┬──────┘   └───────────┘
                  │  edit → bumps version
                  ▼
         ┌─────────────────┐
         │  published + v2 │
         └─────────────────┘
                  │
                  ▼  
            (archive available any time;
             soft-delete, remains in history)
```

`pending_review` entries are invisible to MCP readers by default. Curators can pass `include_drafts: true` on `lexicon.search` to see them while reviewing.

## Surface 1: Web UI

The canonical contribution surface for curators and humans doing focused work.

**Pages:**
- **Home / search** — search across all primitives; filter by type, owner, freshness, status
- **Primitive pages** — CRUD forms for each of the six primitive types (auto-generated from the JSON Schemas in [`PRIMITIVES.md`](./PRIMITIVES.md))
- **Review queue** — list of `pending_review` entries with diff viewers when editing existing ones; one-click approve / reject with reason
- **Audit log** — filterable view of every read/write action with user attribution
- **Admin** — user management, role promotion, service tokens, ingestion source configuration
- **My contributions** — per-user view of drafts, published, rejected, and commented-on entries
- **Settings** — token management, Slack integration link, freshness-TTL policy

**Tech choice:** Next.js + shadcn/ui is the recommended default. The agent can swap to any SPA framework that speaks the REST API.

**Access:** OIDC-gated. Readers can view search + published entries + their own contributions. Curators see the review queue. Admins see admin pages.

## Surface 2: Agent-assisted MCP writes

The wedge for non-technical contributors. Every LLM client becomes a contribution endpoint without teaching users a new UI.

**Flow:**
1. User asks their LLM (Claude Desktop / Cursor / etc.) a question
2. LLM calls `lexicon.define` or `lexicon.search` and gets "not found" or a stale entry
3. LLM asks the user: *"I don't have a canonical definition for this. Want me to propose one?"*
4. User says yes and provides the definition conversationally
5. LLM shapes it into the glossary payload and calls `lexicon.propose_entry`
6. Entry lands in `pending_review`, Slack notifies the likely owner (inferred from tags)
7. Curator approves via Web UI or Slack approve emoji → entry is live within seconds

**Why this matters:** non-technical users never leave Claude Desktop. The workflow is *"answer my question or help me contribute, agent."* No git, no PRs, no new UI to learn.

**Client-side prompt hint:** the agent's system prompt (typically set by IT when distributing MCP configs) should include:

> When the user asks about a term, tool, or query that lexicon doesn't have, proactively offer to propose one on their behalf using `lexicon.propose_entry`. Never submit without the user's confirmation of content.

## Surface 3: Slack / Teams bot

The async-submission channel for teams that live in chat.

**Slash commands:**
- `/lexicon add glossary "active customer" = <definition>`
- `/lexicon add decision "<title>" <body>`
- `/lexicon search <query>`
- `/lexicon status <entry-id>` — check review state
- `/lexicon approve <entry-id>` — curator shortcut (role-gated)

**Threaded contribution:**
- Any message containing "this should be in lexicon" in a configured channel triggers a reply with a "Propose" button
- The button opens a modal pre-filled with the message content; user picks the primitive type and submits
- The proposal lands in `pending_review` with a link back to the original Slack thread

**Review via emoji reaction:**
- `:white_check_mark:` from a curator on a review-queue notification → approves
- `:x:` from a curator → opens a modal for rejection reason

**Owner notifications:**
- When a proposal is submitted, the bot DMs the inferred owner (via the `owner` field or the primitive's tag-to-team mapping) with a one-click review link
- Silence the bot per-user or per-channel via `/lexicon mute`

**Authentication:** Slack user identity → lexicon user identity via email mapping established on first use. User gets a DM asking them to link their accounts.

## Surface 4: REST API

For automation, CI integrations, documentation generators, and any tool not covered by the other surfaces.

**Endpoints (mirrors MCP tool surface, plus CRUD):**

```
GET    /search?q=&types=&limit=
GET    /tools
GET    /tools/{name}
POST   /tools                    (draft)
PATCH  /tools/{id}               (new version)
DELETE /tools/{id}               (archive)

GET    /glossary
GET    /glossary/{term}
POST   /glossary
...

GET    /proposals                (curator-only)
POST   /proposals/{id}/approve   (curator-only)
POST   /proposals/{id}/reject

GET    /audit-log
GET    /users  /users/{id}  (admin)

POST   /tokens/issue              (admin or self-service)
POST   /tokens/revoke
```

**Auth:** per-user token or service token in `Authorization: Bearer`. Same RBAC as the Web UI.

**OpenAPI spec:** the implementation generates and serves `/openapi.json`. Agents can consume it to auto-build client libraries.

## Surface 5: Ingestion scrapers

For pulling from company data sources. Different from the others — these produce large batches of proposals that curators triage.

Covered in depth in [`INGESTION.md`](./INGESTION.md). A one-line summary here:

- **File-glob** (markdown, SQL, schema dumps) — scheduled or one-shot
- **dbt manifest** — pulls from the dbt project's `target/manifest.json`
- **Notion** — pulls from a configured Notion space
- **Confluence** — pulls from a configured Confluence space
- **Slack** — scrapes designated channels for Q&A-shaped content
- **Salesforce** — pulls objects, field descriptions, reports
- **Generic HTTP** — a pattern for adding a custom source

Every scraped entry is a proposal. None auto-publishes. All end up in the review queue.

## Notifications and routing

When a proposal is submitted, the system tries to route it to the right curator:

1. If the primitive has an `owner` field set → notify that owner via Slack DM + email
2. Else if a tag in the proposal maps to a team → notify that team's #curation channel
3. Else → notify a global `#lexicon-review` channel

Notification payloads include: a one-line summary, a permalink to the Web UI review page, and (for Slack) an inline approve/reject button.

## Who can do what (RBAC summary)

See [`AUTH.md`](./AUTH.md) for the full table. One-line summary:

- **Reader** — can search + read published entries, can comment, can propose via `propose_entry`
- **Curator** — can approve/reject proposals, can edit published entries, can delete own entries
- **Admin** — everything above + user management + service tokens + archival

## Anti-patterns to reject

Some workflows look attractive but erode trust in the store. Explicitly reject:

- **Auto-publish from scrapers.** The scraper's job is to propose, not to decide. Always human-in-the-loop at the final step.
- **Silent updates from agents.** When an agent proposes an edit to an existing entry, the change goes through review with a diff view. Never merge silently.
- **Per-user private copies.** A Context Store is shared truth. No per-user forks, no "draft mode" that's invisible to collaborators.
- **Bulk edits without review.** Even admin mass-renames should create a review entry summarizing the change, auto-approvable but audit-logged.

## Metrics to watch

Good indicators the contribution flow is healthy:

- **Time-to-approval:** median should be <24 hours. >72 hours signals curator overload.
- **Approval rate:** 70–90% healthy; <50% means scrapers are too noisy or users need guidance on what belongs in lexicon; >95% means curators aren't exercising judgment.
- **Contribution surface mix:** if >80% of writes come from one surface, the others are broken or underpromoted.
- **Stale entries:** published entries that haven't been reviewed in >TTL days. Trend up = curation is falling behind.

Surface these on the Web UI's admin dashboard; alert on thresholds.
