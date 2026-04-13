"""FastAPI REST API for human curation of lexicon primitives.

v0 scaffold — endpoints are stubs. Full CRUD and search ships in v0.1.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="lexicon",
    description="REST API for curating the Context Store. See /docs for the OpenAPI schema.",
    version="0.0.1",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "lexicon",
        "version": "0.0.1",
        "docs": "/docs",
        "repo": "https://github.com/AdamLenning/lexicon",
    }
