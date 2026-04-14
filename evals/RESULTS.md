# Eval results — 2026-04-13

First eval pass against the `lexicon` spec. Four scenarios, four parallel general-purpose subagents (claude-sonnet-4), each playing a fresh AI coding agent seeing the repo for the first time. Each agent was explicitly blocked from reading `evals/` to avoid rubric leakage.

## Summary

| Scenario | Dimensions | Score | Notes |
|----------|-----------:|------:|-------|
| 01 — Vercel-centric startup, greenfield | 10 | **10/10** | Clean compression of 10 phases → 9 steps; correct Supabase+Fly+Clerk+Google federation pick; added a round-trip test step not in the spec |
| 02 — AWS enterprise with existing Postgres | 12 | **12/12** | Read all 12 docs; surfaced 6 security-review items (threshold was 3); caught the "bootstrap admin first-login wins" footgun |
| 03 — Already on Mongo Atlas | 10 | **10/10** | Confident Atlas pivot; M10+ tier cost floor surfaced honestly; embedding-inversion caveat added |
| 04 — HIPAA healthtech | 12 | **12/12** | Correctly states spec is not certified; 6-year retention cited from spec; proposed Amazon Comprehend Medical pre-filter as a model-independent PHI gate |
| **Total** | **44** | **44/44** | **100%** |

All four scenarios scored strong-pass. No rubric failed any dimension.

## What this tells us about the spec

The spec is clear enough that a fresh agent with no prior context can produce a production-grade deployment plan for four very different company shapes. Observed strengths:

1. **Decision matrices work.** Every agent correctly navigated `STORAGE.md` §Decision matrix to the right storage pick for the scenario's constraints. No agent picked a rejected option (markdown-in-git, SQLite) when pushed toward a company-service shape.

2. **Cross-doc references are coherent.** Agents consistently chained `setup-lexicon.md` → specialist docs without hitting dead ends or contradictions. No agent hallucinated a section name; every citation verified.

3. **Non-negotiable principles held.** "Never auto-publish," "per-user tokens," "audit everything," and "centralized service" all surfaced naturally in the responses — usually explicitly called out under a "what not to do" heading.

4. **The spec degrades gracefully.** The Mongo Atlas eval demonstrated the spec is storage-agnostic: MCP spec, auth, contribution surfaces, ingestion pattern, governance model all carried over unchanged. Only schema and indexing needed translation.

5. **Agents add value without contradicting.** Every run produced synthesized insights not in the spec (bootstrap-admin risk, embedding-inversion, Comprehend Medical pre-filter, online archival via Atlas tiers). None of these contradicted the spec; all extended it sensibly.

## Spec gaps surfaced

### 1. HIPAA-specific guidance could move from "agent synthesizes it" to "spec provides it"

Eval 04 produced excellent HIPAA reasoning — Comprehend Medical pre-filter, medical-entity extension to the PII redactor, Bedrock as embedding default for healthtech, embedding-inversion caveat. None of this is in the current spec. It's synthesized from general knowledge plus the spec's hooks.

If you want healthtech adopters to get the same quality answer without relying on agent-model knowledge, consider adding either:
- A `COMPLIANCE.md` with per-framework (HIPAA / GDPR / SOC 2) patterns, or
- Expanding `GOVERNANCE.md` §Compliance posture with HIPAA-specific recipes (Comprehend Medical hook, Bedrock embedding default, weekly PHI-leakage sampling job)

Low-priority; the spec works today. But locking in the knowledge protects against model drift.

### 2. The storage "fuzzy match" discussion is buried

Eval 03 (Mongo shop) correctly found and quoted `STORAGE.md`'s fuzzy-match section. But the section title "Fuzzy match quality for LLMs (the question that comes up)" is a good h2 in a long doc — a reader arriving via search might miss it. Consider a short top-level "Quality comparison" table with pg/Atlas/Elastic side-by-side for lexical and semantic, so the answer is scannable without reading the full option-by-option analysis.

### 3. "Bootstrap admin = first-login-wins" is a real security concern

Eval 02 caught this from `AUTH.md` §RBAC. It's phrased neutrally in the spec: "a bootstrap role: the first user to log in becomes admin." The eval correctly elevated this to a security-review item for an enterprise deployment.

Consider promoting this to an explicit operational note in `AUTH.md` §Onboarding flow: *"Before exposing the `/onboard` page, restrict your IdP's lexicon app assignment to a single named platform engineer. Let them bootstrap, then open assignment broader."* Same guidance, moved from implicit to explicit.

### 4. Nothing else

No contradictions between docs. No broken cross-references. No ambiguity that tripped multiple agents. The setup skill orchestrates the specialist docs cleanly.

## What this doesn't test

Stated in `evals/README.md` §"What the evals do NOT test," restating for emphasis:
- Whether the generated application code actually runs
- Whether tool choices (Fly, Clerk, Voyage) stay current
- UX quality of the resulting Web UI

These evals test **spec teachability to an agent** at one point in time against one model. Re-run quarterly or when the spec materially changes.

## Recommendations

1. **Ship the spec.** The scores say the current spec is usable as-is for a v0 launch. Don't gate on perfection.
2. **Log the gaps above as issues** in the lexicon repo under a `spec-improvements` label; work through them incrementally rather than in a big rewrite.
3. **Re-run evals** after any material doc change. Add new scenarios when real users surface gaps not covered by the current four.
4. **Add 2–3 more scenarios over time:** `05-already-elastic`, `06-greenfield-self-hosted-k8s`, `07-eu-gdpr-only` would expand coverage without duplicating existing ground.

## Run artifacts

- `runs/2026-04-13-claude-sonnet-4-01-vercel-greenfield.md`
- `runs/2026-04-13-claude-sonnet-4-02-aws-existing-postgres.md`
- `runs/2026-04-13-claude-sonnet-4-03-already-mongo-atlas.md`
- `runs/2026-04-13-claude-sonnet-4-04-hipaa-constrained.md`
