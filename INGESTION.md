# Ingestion

The hardest engineering problem in a Context Store. If ingestion produces noise, curators drown and the store dies empty. If it produces signal, the store fills itself.

Every adapter follows the same shape: **pull raw content → LLM-driven classifier proposes primitive entries with confidence scores → proposals land in the review queue as `pending_review`**.

Nothing auto-publishes. Ever.

## The bootstrap skill pattern

At the heart of every adapter is an LLM classifier. Implementation-agnostic shape:

```
fetch() -> raw documents
  → chunk_and_normalize() -> ~2-4KB text windows
    → classifier_prompt(window, primitive_schemas, few_shot_examples)
      → Anthropic/OpenAI call with prompt caching on the schemas + few-shot
        → JSON output: zero or more proposal candidates per window
          → dedup_against_existing_entries()
            → enqueue_as_pending_review()
```

### Why LLM-driven (not regex/heuristic)

The same Confluence page can contain a glossary term, a decision, and two canonical queries. A static parser can't tell them apart. An LLM with the primitive schemas in its context can. Prompt caching makes this cheap at scale — ~$0.50 per 1000 document chunks on Claude Haiku with cached schemas and few-shot.

### Classifier prompt shape

```
You are classifying content from <source_kind> for the lexicon Context Store.

The lexicon primitives are:
<<< cached: JSON schemas for all six primitives from PRIMITIVES.md >>>

Examples of good proposals:
<<< cached: 5-10 few-shot examples per primitive type >>>

For the following content, propose zero or more primitive entries. For each:
- type (one of: tool, glossary, canonical_query, pattern, guardrail, decision)
- payload (matching the schema for that type)
- confidence (0.0 to 1.0)
- justification (one sentence)
- suggested_owner (if inferable from the content)

Be conservative. A window that contains no clear primitive should return an empty list. Do not invent fields; only use content actually present in the input.

Content:
<<< the window text >>>
```

### Dedup

Before enqueueing, check if a near-duplicate already exists:
- For glossary entries: embedding similarity >0.85 against existing terms + exact match on `term` field → skip or propose as edit
- For tools: exact `name` match → propose as edit
- For decisions: title similarity + date proximity → propose as supplement, not new entry
- For canonical queries: `name` match OR template similarity >0.9 → propose as edit

Proposed edits are a special proposal type: they include the existing entry id + a diff for the curator to accept.

### Eval methodology

Each adapter has a **golden set** checked into the implementation repo (`tests/eval/<adapter>/`):
- 5–20 hand-curated example inputs (synthetic or redacted real)
- For each input, the expected set of proposals

CI runs the classifier against the golden set and reports:
- **Precision:** of the proposals the classifier emitted, what % matched expected
- **Recall:** of the expected proposals, what % did the classifier emit
- **Noise rate:** % of proposals with confidence >0.5 that are actually garbage

**Ship criteria per adapter:** precision ≥0.8, noise rate <0.15. Don't promote an adapter to production scheduling until it hits these.

### Freshness re-ingestion

Adapters run on a schedule (daily default). On each run, they fetch changed content only (where the source supports `updated_since`). Changed entries re-enter the review queue as proposed edits, not new entries.

---

## Adapter: file-glob

Pulls from a directory of markdown, SQL, or structured text files. Simplest adapter; good for seeding from a git-based wiki or a dumped schema.

**Config:**
```yaml
source_kind: file_glob
name: company-wiki
patterns:
  - "/mnt/wiki/**/*.md"
  - "/mnt/schemas/**/*.sql"
schedule: daily
```

**Behavior:**
- Walk the filesystem (or cloud bucket via `s3://`, `gs://`, `az://` URIs)
- For each file, read + chunk (markdown by section, SQL by statement)
- Send chunks through the classifier
- Track source file path + line range in `proposal.source` for traceability

**Auth:** filesystem permissions or bucket IAM. No secrets in-lexicon.

**Quality notes:** best on curated content (engineering docs, schema dumps). Noisier on raw note dumps; consider filtering to specific subdirectories.

---

## Adapter: dbt manifest

Parses `target/manifest.json` from a dbt project. High-value for data teams because everything in dbt is already documented at the column level.

**Config:**
```yaml
source_kind: dbt
name: analytics-dbt
manifest_path: s3://company-dbt-artifacts/main/target/manifest.json
schedule: on-merge-to-main
```

**Behavior:**
- Load `manifest.json`
- For each model: propose a `Tool` entry (kind=`warehouse`, name = fully-qualified model)
- For each documented column (`description` field): propose a `GlossaryEntry` if the description reads like a definition
- For each exposure with a `query`: propose a `CanonicalQuery`
- For each generic test with metadata: propose a `Guardrail` (e.g. "this column must be unique")

**Auth:** S3/GCS/Azure bucket credentials.

**Quality notes:** precision is high because dbt content is already structured. Recall varies with how thoroughly the team has written descriptions.

---

## Adapter: Notion

Pulls from a configured Notion space.

**Config:**
```yaml
source_kind: notion
name: product-wiki
token_secret_ref: LEXICON_NOTION_TOKEN
root_page_ids:
  - 1a2b3c4d5e6f7g8h
  - 9i0j1k2l3m4n5o6p
schedule: daily
```

**Behavior:**
- Traverse page tree from each root (depth-limited, configurable; default 5)
- Respect Notion rate limits (3 req/s); use pagination tokens
- For each page: fetch blocks, flatten to markdown, chunk
- Send chunks through the classifier
- Track Notion page URL + last-edited timestamp

**Auth:** Notion integration token. Integration must be invited to the target spaces.

**Quality notes:** Notion content is often conversational and meeting-noteish — noise is higher than dbt. Filter to specific parent pages or databases tagged "canonical."

---

## Adapter: Confluence

Pulls from a configured Confluence space.

**Config:**
```yaml
source_kind: confluence
name: engineering-wiki
base_url: https://company.atlassian.net/wiki
token_secret_ref: LEXICON_CONFLUENCE_TOKEN
space_keys:
  - ENG
  - DATA
schedule: daily
```

**Behavior:**
- Use the Confluence REST API to list pages in each space
- For each page: fetch body, convert storage-format XHTML to markdown, chunk
- Same classifier pass

**Auth:** Atlassian API token (personal or service). Per-user tokens recommended for audit attribution of ingestion.

**Quality notes:** Confluence content tends to be more structured than Notion but often stale. Cross-reference `lastModified` with current date — pages older than 18 months should get a lower classifier priority and a "likely stale" annotation on proposals.

---

## Adapter: Slack

Scrapes designated channels for decision- and Q&A-shaped content. The most valuable source for tribal knowledge; also the noisiest.

**Config:**
```yaml
source_kind: slack
name: data-team-slack
token_secret_ref: LEXICON_SLACK_TOKEN
channels:
  - C0123ABCDEF  # #data-questions
  - C0987FEDCBA  # #analytics-decisions
schedule: weekly
lookback_days: 30
min_thread_length: 3  # only threads with 3+ messages
```

**Behavior:**
- For each configured channel, fetch threads updated in the lookback window
- Filter: threads with N+ messages, or threads with a `:lexicon:` emoji reaction
- For each thread: concatenate messages with author + timestamp, chunk
- Classifier prompt specialized for Slack: *"Extract decisions, glossary terms, canonical queries mentioned in the thread. Ignore chitchat."*
- Source reference: Slack permalink + thread timestamp

**Auth:** Slack bot user OAuth token, scopes `channels:history`, `groups:history` for the invited channels. Bot must be invited to each channel.

**Quality notes:** Slack is by far the noisiest source. Require `min_thread_length` and ideally `:lexicon:` emoji tagging as a human prefilter. Classifier threshold higher (confidence >0.7 for auto-enqueue).

**Privacy note:** by default, don't ingest DMs or private channels. Document clearly which channels are being scraped; announce in the channel when first enabled.

---

## Adapter: Salesforce

Pulls Salesforce metadata and reports for tool + glossary + canonical_query entries.

**Config:**
```yaml
source_kind: salesforce
name: sfdc
auth:
  type: oauth
  client_id_ref: LEXICON_SALESFORCE_CLIENT_ID
  client_secret_ref: LEXICON_SALESFORCE_CLIENT_SECRET
  instance_url: https://company.my.salesforce.com
objects:
  - Opportunity
  - Account
  - Contact
include_reports: true
schedule: weekly
```

**Behavior:**
- Use SFDC Metadata API:
  - For each configured object: propose a `Tool` entry with data types + field list
  - For each field with a non-empty `description`: propose a `GlossaryEntry` candidate (filtered: SFDC field descriptions are often trivial)
- If `include_reports`: list SOQL reports, for each extract the query and propose a `CanonicalQuery`
- Source reference: SFDC object/field/report URL

**Auth:** SFDC connected app with OAuth, API access permission set.

**Quality notes:** SFDC field metadata varies wildly in quality across orgs. Expect to filter aggressively on description length and specificity. Reports are higher-signal.

---

## Adapter: generic HTTP

The pattern for adding a custom source. If your company has an internal wiki/docs tool not covered above, implement this interface:

```python
class GenericHTTPSource(Adapter):
    def list_items(self, updated_since: datetime | None) -> list[Item]:
        """Yield URLs or IDs of items to process."""

    def fetch_item(self, item_id: str) -> RawContent:
        """Pull content for a single item."""

    def normalize(self, raw: RawContent) -> list[TextChunk]:
        """Convert to chunkable text; strip nav/menus/noise."""
```

The classifier + dedup + enqueue pipeline is shared; adapter authors only implement these three methods.

**Examples of sources worth wrapping:**
- GitHub wikis + READMEs across the org
- Google Docs (Workspace admin + Drive API)
- Jira (for decision-flavored comments on epics)
- Zendesk / Intercom macros (canonical-answer flavored)
- Looker LookML + Views
- Metabase documentation fields

---

## Running the pipeline

Ingestion workers are scheduled jobs, not long-running processes. Per [`DEPLOYMENT.md`](./DEPLOYMENT.md) they run as:
- Cloud Run Jobs / Cloud Scheduler (GCP)
- Lambda + EventBridge (AWS)
- Cron container (k8s) / Vercel Cron (small scale)

Each run:
1. Reads its source config from the DB (`ingestion_sources` table)
2. Fetches with `updated_since = last successful run`
3. Processes through the classifier pipeline
4. Enqueues proposals in a single transaction
5. Writes a run record with stats: items processed, proposals generated, errors

**Concurrency:** one run per source at a time. Use advisory locks (Postgres `pg_try_advisory_lock`) to prevent overlap.

**Failure handling:** partial failures are logged per-item and don't block the rest. Run records include error counts — if >10% error rate, fail the run and page.

**Cost control:** each adapter has a per-run item cap (default 1000) and a per-day API-cost cap (default $5). Surface these in the admin UI.

## Review queue pressure

A fresh ingestion pass from Confluence can generate 500+ proposals overnight. Curators won't triage 500 in a day.

**Mitigations:**
- **Priority queue:** proposals with confidence >0.9 surface first
- **Batch approve:** curators can select all proposals from one source and approve-all with a single review pass
- **Auto-approve above threshold (optional):** admins can set per-adapter a confidence threshold above which proposals auto-publish. **Default off.** Turn on only after an adapter has proven ≥0.9 precision over 3 months of data.
- **Rate-limit the ingestion:** cap at N proposals per day per source; spillover waits for the next run

**Anti-pattern:** do not train auto-approve on approval rate alone. That creates a feedback loop where curators rubber-stamp to clear the queue and then the store fills with noise.

## What not to ingest

- **PII.** Classifier prompt includes: *"If content contains personal identifiers (names, emails, SSNs, phone numbers), redact them before emitting the proposal. If the content is primarily PII, do not propose anything."*
- **Secrets.** Same rule — scan for common secret patterns (API key shapes, password fields) and skip.
- **Prompt-injection payloads.** The classifier prompt is written to resist common injection patterns; human review is the ultimate defense.
- **Personal notes / drafts.** If a Notion page or Confluence space is tagged "draft" or "personal," skip it.

## Bootstrap strategy (first run)

When a company first stands up lexicon, the first ingestion pass matters. Don't fire-hose.

1. **Start narrow.** Pick the single most-curated source the company has — often `dbt` for data teams, sometimes `Confluence` for engineering orgs
2. **Run once manually** (not on schedule) against a limited scope (one Confluence space, one dbt project)
3. **Curators triage** the first batch together in a single session; this calibrates everyone on what "good" looks like
4. **Tune classifier** prompts based on rejections
5. **Expand** to additional sources one at a time, each with its own triage session

Expect the first pass to take 2–3 days of curator attention. After that, steady-state is 10–30 minutes per day.
