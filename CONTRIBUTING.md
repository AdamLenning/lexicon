# Contributing to lexicon

Thanks for the interest. This project is pre-alpha — the scaffold exists but most functionality is not yet implemented. Issues, discussion, and design feedback are more valuable than PRs at this stage.

## The short version

- Read [`DESIGN.md`](./DESIGN.md) first. If your change cuts against the design, open an issue for discussion before writing code.
- Use `uv` for dependency management.
- Keep PRs small. One conceptual change per PR.

## Local development

```bash
git clone https://github.com/AdamLenning/lexicon
cd lexicon
uv sync --extra dev
docker compose up -d
# (migrations ship in v0.1 — for now this is a scaffold only)
```

## Running checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Design principles

1. **Agents first.** Every API surface is consumed by an LLM. Optimize for machine-readable output and clear tool boundaries.
2. **Postgres is the foundation.** Don't introduce a second datastore unless absolutely necessary. `pgvector` + FTS + relational = all six primitives in one engine.
3. **Bootstrap from docs, not from UI.** Humans won't populate this by hand. The LLM-driven ingestion skill is the whole game.
4. **Governance is not optional.** Audit, versioning, approval. Without these, `lexicon` is a toy.
5. **Commit to the trust boundary.** v0 is localhost-only, no auth. Anything that expands that surface requires a proper threat model, not a guess.

## What we need most (right now)

- Design review on the primitive schemas in `src/lexicon/models/`
- Examples of what a canonical query / guardrail / decision looks like in *your* org
- Ingestion adapter prototypes (file-glob + dbt are v0.2 priorities)

## Code of conduct

Be kind. Assume good faith. Bring data to disagreements.
