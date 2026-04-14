# Eval results

## Summary of runs

| Run | Date | Spec state | Scores |
|---|---|---|---|
| First | 2026-04-13 | pre-gap-fixes | 44/44 (all strong pass) |
| Re-run | 2026-04-13 (b) | post-gap-fixes | 44/44 (all strong pass) |

Both runs scored 100% — the spec was already teachable to an agent before the gap fixes, and the fixes targeted *where knowledge comes from* (spec vs agent synthesis) rather than fixing outright failures.

## Per-scenario scores

| Scenario | Dimensions | First run | Re-run | Notes |
|---|---:|---:|---:|---|
| 01 — Vercel greenfield | 10 | 10/10 | 10/10 | Re-run adds bootstrap-admin as explicit deploy step (from AUTH.md update) |
| 02 — AWS + existing Postgres | 12 | 12/12 | 12/12 | Re-run quotes COMPLIANCE.md §SOC 2 directly; previously synthesized |
| 03 — Mongo Atlas shop | 10 | 10/10 | 10/10 | Re-run cites STORAGE.md quality table + COMPLIANCE.md PCI-DSS note |
| 04 — HIPAA healthtech | 12 | 12/12 | 12/12 | Re-run sources all HIPAA patterns from COMPLIANCE.md; previously agent-synthesized from scratch |
| **Total** | **44** | **44/44** | **44/44** | |

## What the re-run verified

The three spec gaps surfaced after the first run have all been addressed, and the re-run demonstrates the fixes flow through to agent behavior.

### Gap #1 — HIPAA guidance should be spec content, not agent synthesis

**Before:** eval 04 produced excellent HIPAA reasoning (Comprehend Medical pre-filter, medical-entity PII extension, Bedrock-as-default, embedding-inversion caveat, 7-phase rollout), but *all of it was synthesized* from agent general knowledge plus the spec's governance hooks.

**After:** [`COMPLIANCE.md`](../COMPLIANCE.md) was added. Eval 04 re-run sources every HIPAA pattern from the spec:

- Comprehend Medical pre-filter → now the third layer of a documented 5-layer defense-in-depth
- Medical-entity extension to PII redactor → documented in §HIPAA → "PHI-avoidance: defense in depth"
- Bedrock Titan / Cohere-on-Bedrock / SageMaker as embedding default → documented in §HIPAA → "Embedding provider (the critical choice)"
- Embedding-inversion caveat → quoted verbatim by the agent: *"embeddings are not one-way hashes. Modern inversion attacks can partially reconstruct input text from vectors."*
- 8-phase rollout → documented in §HIPAA → "Phased rollout (healthtech-specific)"
- BAA matrix for 13+ common third-party services → documented as a table

Re-run agent names COMPLIANCE.md as the **primary** doc: *"the HIPAA section answered most of the brief directly."*

**Durability gain:** a model with weaker HIPAA knowledge will now produce the same answer because the patterns live in the spec.

### Gap #2 — STORAGE quality comparison was buried

**Before:** the "Fuzzy match quality for LLMs" discussion existed but was several screens deep; agents had to read the whole option-by-option analysis to extract the "no meaningful difference at this scale" conclusion.

**After:** new "Quick quality comparison" table near the top of [`STORAGE.md`](../STORAGE.md) with scannable rows for pgvector, Atlas, Elastic, SQLite, plain Mongo across lexical, semantic, hybrid, LLM retrieval quality, and governance story.

Re-run evals 01 and 03 both quote the new table's phrasing in their justifications:
- Eval 01: *"At your scale, all viable engines land within 5% on retrieval quality, so governance and ops fit decide."*
- Eval 03: *"both land within 5% of optimal retrieval quality."*

**Durability gain:** any agent triaging a storage question now has a scannable answer at the top of the doc instead of needing a full read.

### Gap #3 — Bootstrap-admin "first-login-wins" was implicit

**Before:** `AUTH.md` §RBAC said *"`admin` is a bootstrap role: the first user to log in becomes admin"* — neutral phrasing, easy to miss, not called out as a risk.

**After:** `AUTH.md` §RBAC now explicitly frames this as *"a real privilege-escalation footgun if left unguarded"* with per-IdP mitigation guidance (Okta "Assignments" tab, Entra "Users and groups," Clerk invitation mode). `AUTH.md` §Onboarding gets a visible callout block at the top.

Re-run evals:
- Eval 01: agent now makes bootstrap-admin guardrail a **numbered deploy step** (step 8: *"before first login, restrict the Clerk app to invitation-only..."*), up from being nearly absent in first run.
- Eval 02: agent quotes the new callout language verbatim in security-review item #1: *"The first user to complete SSO becomes admin by default — this is a real privilege-escalation footgun if left unguarded."*

**Durability gain:** a real deployment risk is now explicit rather than synthesized-from-implication.

## Overall observations

1. **The spec is both teachable and durable.** The first run proved the spec could be used by a fresh agent; the re-run proves the fixes make that use less dependent on the agent's own knowledge.

2. **Gap fixes landed without regressions.** No scenario lost points on the re-run. COMPLIANCE.md didn't add contradictions elsewhere; the STORAGE quality table didn't muddy the deeper option-by-option analysis; the AUTH callout didn't disrupt the onboarding flow narrative.

3. **Cross-doc integrity held.** Agents followed README → setup skill → specialist docs cleanly. When COMPLIANCE.md was added, the setup skill's Phase 0 reference and the README nav both pointed at it, and agents correctly picked it up for framework-specific scenarios.

4. **Agent depth varies by scenario.** Eval 01 (40-person startup, time-constrained) agent read 6 docs. Eval 04 (HIPAA, high-stakes) agent read 7 docs but focused deeply on COMPLIANCE.md. Eval 02 (AWS enterprise SOC 2) and Eval 03 (Atlas migration) agents both read all 13 files. The spec supports both fast-scan and deep-dive usage patterns.

## What this still doesn't test

Restating from the first run:
- Whether the generated application code actually runs
- Whether tool choices (Fly, Clerk, Voyage, Bedrock) remain current as the landscape drifts
- UX quality of the resulting Web UI
- Whether the spec remains teachable to a *different* model (haiku, sonnet-lite, or a weaker competitor)

Consider adding these to future eval passes:
- **Cross-model eval:** run the same four scenarios against haiku to test whether weaker models still produce strong-pass responses
- **Adversarial scenario:** a user who actively misrepresents their stack ("we definitely run Postgres" but actually they don't) to test whether preflight questioning holds up
- **Maintenance scenario:** six months into an existing lexicon deployment, something broke — can the agent triage using `OPERATIONS.md` §Incident playbook?

## Recommendations

1. **Lock in the spec as-is for v0.** Both eval runs support shipping. No remaining gaps block release.
2. **Schedule quarterly re-runs** of these evals (or after any material doc change) to catch drift.
3. **Add the cross-model and adversarial scenarios** before adding *new* scenarios — more signal per unit of doc effort.
4. **Watch for vendor drift.** BAA status, pricing tiers, specific product names (Voyage-3, Bedrock Titan, etc.) will go stale. Re-run may start losing points when that happens; use those as editing triggers.

## Run artifacts

- **First run:** `runs/2026-04-13-claude-sonnet-4-0{1-4}-*.md`
- **Re-run:** `runs/2026-04-13b-claude-sonnet-4-0{1-4}-*.md`
