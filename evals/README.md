# Evals

Scenario-based evaluation of whether the `lexicon` spec is clear, complete, and unambiguous enough for a fresh AI coding agent to produce a correct deployment plan from it.

## What the evals test

This repo is a specification, not code. The "correctness" question is whether an AI agent reading the repo for the first time can:

1. Apply the decision matrices correctly (pick the right storage for the user's stack)
2. Follow the setup skill's phases in order without skipping prerequisites
3. Cite the correct specialist docs for each decision
4. Ask appropriate preflight questions before recommending
5. Honor the non-negotiable design principles (audit everything, never auto-publish, per-user tokens, centralized service)
6. Avoid contradicting spec content

If agents consistently fail a scenario, the spec has a gap — tighten the relevant doc.

## Structure

```
evals/
├── README.md           # this file
├── scenarios/          # one markdown file per scenario; user-facing prompts
├── rubrics/            # one markdown file per scenario; grading criteria
└── runs/               # outputs from subagent runs (gitignored? no — keep for comparison across versions)
```

Scenarios and rubrics pair by filename stem: `01-vercel-greenfield.md` in each directory.

## Running the evals

### Manual (canonical)

For each scenario:

1. Open a fresh AI coding agent session (Claude Code, Cursor, etc.) with no prior context
2. Point it at the repo: `cd /path/to/lexicon`
3. Paste the scenario's `## Prompt` section verbatim
4. Ask for a deployment plan in the response format specified in the scenario
5. Compare the agent's output against the paired rubric
6. Record the score in `runs/<YYYY-MM-DD>-<model>-<scenario>.md`

### Automated (via subagent)

The repo maintainer can run `Agent(general-purpose)` subagents in parallel, one per scenario, with a prompt template like:

> You are a fresh AI coding agent. The user has told you: *"{scenario_prompt}"*. Read only the `lexicon` repo at `{path}`. Produce a deployment plan in the format specified in the scenario. Cite which docs you referenced for each decision.

Then grade outputs against `rubrics/` files.

## Scoring

Each rubric defines dimensions worth 1 point each (pass/fail). Total rubric score is out of the dimension count.

- **Strong pass:** ≥90% of dimensions
- **Acceptable:** 70–89%
- **Spec gap identified:** <70% — the spec needs work, not the agent

Don't chase 100%. Agents have real judgment and a scenario that everyone passes perfectly is probably a rubric that's too permissive.

## What the evals do NOT test

- Whether the generated application code actually runs (that's a downstream concern per implementation)
- Whether the UX of the resulting Web UI is good (subjective)
- Whether the specific tool choices (Fly vs Railway, Clerk vs Auth0) remain current (landscape drifts)

These evals test the **spec's teachability to an agent** — nothing more.

## Adding a new scenario

1. Pick a real company situation not covered by existing scenarios
2. Write `scenarios/NN-short-name.md` with a realistic user prompt
3. Write `rubrics/NN-short-name.md` with 6–12 dimensions worth grading
4. Run it, tune the scenario prompt until agents can succeed on a well-written spec
5. Commit both files
