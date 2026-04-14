# Rubric 01: Vercel-centric startup, greenfield

Each dimension is pass/fail worth 1 point. Total: 10 points.

## Dimensions

1. **Centralized-service explanation** — Agent explains why lexicon is a company service (not per-repo/per-machine), citing that all LLM clients need to share ground truth. Must reference `ARCHITECTURE.md` or the principle explicitly.

2. **Storage pick: Supabase + pgvector** — Agent picks Supabase (free tier) with pgvector, per `STORAGE.md` decision matrix row "Vercel shop, no DB yet." Neon is an acceptable substitute; any other choice without justification is a fail.

3. **Storage reasoning cites STORAGE.md** — Agent names the doc and explains *why* pgvector fits (ACID governance, free tier, portability) — not just "because the matrix says so."

4. **Deploy plan follows setup-lexicon.md phase order** — The numbered steps reflect Phases 1–10 (or a coherent compression). Must include storage provision → schema → MCP server deploy → Web UI → auth → client config.

5. **Auth: Clerk (or equivalent OIDC provider)** — Agent picks Clerk (preferred in `AUTH.md` §Provider recommendations for "smaller teams, fast setup") or a peer like Auth0/Descope. Self-rolled auth is a fail.

6. **MCP server host: Fly.io (or peer)** — Agent picks Fly.io (matches `DEPLOYMENT.md` §Recipe A) or an equivalent lightweight container host. Heavy-infra picks (ECS, Kubernetes) are inappropriate for 40-person shop.

7. **Explicitly warns against auto-publish** — Anti-pattern called out in the "what not to do" section: no auto-approval of ingestion at launch, everything through review queue.

8. **Narrow first ingestion** — Agent recommends starting with ONE source (likely dbt given the scenario mentions "dbt metrics"), not firing hose. Per `INGESTION.md` §Bootstrap strategy.

9. **Specialist doc citations are correct** — The docs the agent cites actually support the claims made. No hallucinated sections or misattributed recommendations.

10. **Under 800 words** — Respects the user's time constraint without truncating essential content.

## Bonus (not scored)

- Mentions per-user token onboarding flow (`/onboard` page, once-display token UX)
- Flags that "40-person shop" probably means skip Slack bot until week 2
- Notes that Google accounts → SSO can be done via Clerk's Google OAuth, no new auth system needed

## Failure modes to watch for

- **Over-engineering:** recommends Kubernetes or enterprise patterns for a 40-person shop
- **Under-engineering:** suggests running it locally on one laptop, violating centralized-service principle
- **Stack mismatch:** picks an AWS recipe despite the user being Vercel-centric
- **Skipping auth:** "we'll add auth later" — security violation
- **Fake doc sections:** citing `STORAGE.md §Scale Argument` when the doc doesn't have that section name
