---
type: Schema
title: OKF Conventions for the SCORCH Knowledge Base
description: How this wiki is structured, what the document types are, and the workflow agents follow to maintain it.
tags: [okf, conventions, meta]
timestamp: 2026-06-16
---

# OKF Conventions

This directory is an **Open Knowledge Format (OKF)** bundle — Google's
formalization of Andrej Karpathy's "LLM wiki" pattern. It is the durable,
human- and agent-readable knowledge layer of the SCORCH literature review.

> Karpathy's insight: keep **raw sources** (immutable), a **wiki** (LLM-maintained
> markdown), and a **schema** (this conventions doc). OKF makes that portable:
> *just markdown, just files* — no platform, no SDK, readable on GitHub, parseable
> by any agent.

## The three layers in this repo

| Layer | Where | Maintained by |
|-------|-------|---------------|
| Raw sources (immutable) | `pdfs/` | Humans (curate the corpus) |
| Structured extraction | `reviews/*.json`, `duckdb/` | The extraction pipeline |
| Knowledge wiki (this) | `okf/` | `scripts/build_okf.py` + agents |

`pdfs/`, `reviews/`, and `duckdb/` are gitignored as regenerable. **`okf/` is
committed** — it is the shareable artifact.

## Document model

Every file is one **concept**. Two parts:

1. **YAML frontmatter** — structured, queryable. The only required field is
   `type`. We use: `Paper`, `Concept`, `Dataset`, `Schema`, `Index`.
2. **Markdown body** — prose for humans and agents.

Concepts cross-link with ordinary relative markdown links
(`[Heat](../exposures/heat.md)`), forming a graph richer than the folder tree.

## Reserved files

- `index.md` — the catalog (regenerated each build).
- `log.md` — append-only ingest history (`## [DATE] ingest | Title`).

## Directory map

```
okf/
├── CONVENTIONS.md            ← you are here (hand-authored)
├── index.md                  ← catalog            (generated)
├── log.md                    ← ingest history     (append-only)
├── schema/extraction-schema.md   the 46-question contract (hand-authored)
├── datasets/scorch-reviews.md    the DuckDB tables       (hand-authored)
├── papers/<slug>.md          one per reviewed article    (generated)
├── health-outcomes/<slug>.md aggregated concepts         (generated)
├── exposures/<slug>.md       "                           (generated)
├── resilience/<slug>.md      "                           (generated)
├── populations/<slug>.md     "                           (generated)
└── regions/<slug>.md         "                           (generated)
```

## Workflow for agents

1. **Read before regenerating.** `index.md` is the entry point; follow links.
2. **Generated pages** (`papers/`, concept dirs, `index.md`) are rebuilt by
   `python scripts/build_okf.py` from the reviews — do not hand-edit their
   structured parts.
3. **Curated prose is preserved.** Anything under a `## Curator notes` heading in
   a generated concept page survives rebuilds — put synthesis, caveats, and
   cross-domain insight there. (`scripts/synthesize.py` drafts these.)
4. **Hand-authored docs** (`CONVENTIONS.md`, `schema/`, `datasets/`) are owned by
   maintainers; the builder never overwrites them.

The point (Karpathy): *the LLM does the bookkeeping — updating cross-references,
keeping pages consistent, touching many files in one pass — while humans curate
sources and ask the right questions.*
