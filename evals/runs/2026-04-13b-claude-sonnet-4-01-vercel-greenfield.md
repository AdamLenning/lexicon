# Re-run: 01-vercel-greenfield (2026-04-13 post-gap-fixes, claude-sonnet-4)

## Agent output (summary)

Same storage pick (Supabase + pgvector), same compute (Fly.io), same auth (Clerk + Google Workspace), 12-step plan covering phases 2–9 of the setup skill.

**Key differences from first run:**

1. **Cites the new quality-comparison table explicitly.** From the response: *"At your scale, all viable engines land within 5% on retrieval quality, so governance and ops fit decide — and those favor Postgres."* Directly maps to the new `STORAGE.md` "Quick quality comparison" section.

2. **Adds bootstrap-admin safety as explicit deploy step 8.** From the response:
   > **Critical bootstrap-admin safety step** (`AUTH.md`): before first login, restrict the Clerk app to invitation-only or assign a single user (you) so the first-SSO-becomes-admin rule can't be hijacked. Log in, confirm you're admin, then open assignment up.

   This was not present in the first run. The new explicit callout in `AUTH.md` §Onboarding surfaced the guardrail correctly.

3. **Bootstrap-admin also appears in "do NOT" list** — double-layer reinforcement.

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | Centralized-service explanation | PASS | "Ground truth cannot fork" language. |
| 2 | Storage pick | PASS | Supabase + pgvector. |
| 3 | Storage reasoning cites STORAGE.md | PASS | Plus explicit reference to "within 5% on retrieval quality" from the new quality-comparison table. |
| 4 | Deploy plan follows phase order | PASS | 12 numbered steps, coherent ordering. |
| 5 | Auth: Clerk | PASS | Explicit, with Google Workspace federation. |
| 6 | MCP server host: Fly.io | PASS | Explicit. |
| 7 | Warns against auto-publish | PASS | First item in §5. |
| 8 | Narrow first ingestion | PASS | "Start with dbt only." |
| 9 | Doc citations accurate | PASS | All verified. |
| 10 | Under 800 words | PASS | ~780 words. |

**Score: 10/10**

Spec gap #3 (bootstrap-admin) verified closed: agent now elevates it to a numbered step instead of burying it.

Spec gap #2 (STORAGE quality table) verified closed: agent quotes the "within 5%" framing directly in §2 reasoning.
