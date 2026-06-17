# AGENTS.md

Condensed conventions for AI agents working in this repo. Full guidance:
`CLAUDE.md`. Knowledge-wiki rules: `okf/CONVENTIONS.md`.

## Ground truth

- **Schema contract:** `schema/scorch_extraction_schema.json` (v1.1). Never
  fabricate — use `"N/A"` / `[]` / `null` when the source is silent.
- **Schema↔DB mapping:** `scorch/records.py` is the *single source of truth*.
  DDL and INSERTs are generated from it. Do not hand-write column lists.
- **Models / paths / cost:** `scorch/config.py` (tiered: Haiku screen → Sonnet
  extract → Opus verify/synthesize; override with `SCORCH_*_MODEL`).

## Pipeline

```
pdfs/ → [screen] → extract → [verify] → reviews/*.json
      → convert_to_duckdb.py → duckdb/   → build_okf.py → okf/
```

Commands (no API key needed for convert/build_okf):
```bash
python scripts/batch_process_pdfs.py --screen --verify   # extract
python scripts/convert_to_duckdb.py                      # load DB (validated)
python scripts/build_okf.py                              # rebuild wiki
```

## Conventions

- **Commit** `okf/` and code; `pdfs/`, `reviews/`, `duckdb/` are gitignored
  (regenerable). The OKF wiki is the durable, shareable artifact.
- After changing reviews, run **both** `convert_to_duckdb.py` and `build_okf.py`.
- Put curated wiki prose under `## Curator notes` in concept pages — it survives
  `build_okf.py` rebuilds (`synthesize.py` drafts it).
- Python 3.11+: no same-quote nested f-strings.
- The top-level `duckdb/` directory shadows the `duckdb` library if the repo root
  precedes site-packages on `sys.path` — import `duckdb` before appending the
  repo root (scripts already do).

## Agents (`.claude/agents/`)

`scorch-screener` (Haiku) · `scorch-pdf-analyzer` · `scorch-verifier` (Opus) ·
`duckdb-schema-converter` · `duckdb-literature-analyst`.
