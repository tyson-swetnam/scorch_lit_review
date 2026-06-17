# CLAUDE.md

This file guides Claude Code (claude.ai/code) when working in this repository.
See `AGENTS.md` for the condensed agent conventions and `okf/CONVENTIONS.md` for
the knowledge-wiki rules.

## Project Overview

**SCORCH Literature Review** — for the Southwest Center on Resilience for Climate
Change and Health. AI agents extract structured data from climate-health research
PDFs focused on arid/semi-arid regions of the US Southwest and northern Mexico,
into a queryable database and a cross-linked knowledge wiki.

## Repository Structure

```
pdfs/             # Input PDFs (gitignored — proprietary/large)
reviews/          # Output: JSON extractions (gitignored — regenerable)
duckdb/           # Output: DuckDB database + Parquet (gitignored — regenerable)
okf/              # Committed knowledge wiki (Open Knowledge Format markdown)
schema/           # scorch_extraction_schema.json — the 46-question contract
scorch/           # Shared library: config, records (schema<->row map), okf helpers
scripts/          # SDK scripts (batch extract, convert, build wiki, synthesize, ask)
examples/         # Synthetic demo records (committed; clearly labeled)
.claude/agents/   # Interactive Claude Code agent definitions
```

`pdfs/`, `reviews/`, and `duckdb/` are gitignored as regenerable. **`okf/` is the
durable, committed knowledge layer** — treat it as the shareable artifact.

## The `scorch/` package is the source of truth

- `scorch/config.py` — model IDs, paths, cost helper (`estimate_cost`), and tunables
  (`SCORCH_BATCH_CONCURRENCY`, `SCORCH_EXTRACT_MAX_TOKENS`, `SCORCH_BASE_DIR`). Every
  value is env-overridable; see `.env.example`. Change models in ONE place.
- `scorch/records.py` — canonical mapping from the extraction schema to DB rows.
  Table DDL **and** INSERTs are generated from the same field list, so they cannot
  drift from the schema. Do not hand-write column lists elsewhere. The DB is not one
  flat table: `flatten_main`/`MAIN_FIELDS` produce one `reviews` row per paper, while
  `child_rows` fans array data into normalized child tables (`health_outcome_variables`,
  `cofactor_variables`, `climate_weather_variables`, `vulnerable_populations`,
  `correlations`) plus long-format category tables (`health_outcome_categories`,
  `exposure_categories`, `resilience_categories`) so "which papers study heat?" is a JOIN.
- `scorch/okf.py` — read/write OKF documents (YAML frontmatter + markdown body).

## Models (tiered cascade)

| Stage | Default model | Override env |
|-------|---------------|--------------|
| Screen (Q1-Q2 gate) | `claude-haiku-4-5` | `SCORCH_SCREEN_MODEL` |
| Extract (46 fields) | `claude-sonnet-4-6` | `SCORCH_EXTRACT_MODEL` |
| Verify / synthesize | `claude-opus-4-8` | `SCORCH_VERIFY_MODEL` / `SCORCH_SYNTHESIS_MODEL` |

This cascade governs the **batch SDK** scripts. The **interactive** agents set their
own model in `.claude/agents/*.md` frontmatter independent of `scorch/config.py` — most
notably `scorch-pdf-analyzer` runs Opus (not the batch Extract default of Sonnet).

## Pipelines

```
pdfs/ → [screen] → extract → [verify] → reviews/*.json
      → convert_to_duckdb.py → duckdb/   (queryable DB + Parquet)
      → build_okf.py          → okf/     (knowledge wiki)
```

### Interactive (Claude Code agents)
1. `scorch-screener` (Haiku) — cheap include/exclude on the arid-SW gate.
2. `scorch-pdf-analyzer` (Opus) — full 46-field extraction → `reviews/*_review.json`.
3. `scorch-verifier` (Opus) — independent audit of the extraction vs. the PDF.
4. `duckdb-schema-converter` (Opus) — load reviews into DuckDB (validated).
5. `duckdb-literature-analyst` (Opus) — SQL/analysis over the database.

### Batch (SDK scripts)
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/batch_process_pdfs.py --screen --verify   # extract
python scripts/convert_to_duckdb.py                      # load DB (validated)
python scripts/build_okf.py                              # rebuild wiki
python scripts/query_literature.py "..."                 # NL query
```

Both pipelines are incremental — new PDFs/reviews are added without rebuilding.

## Scripts

- `batch_process_pdfs.py` — tiered extraction (Files API, caching, validation +
  repair, optional `--screen`/`--verify`, `--dry-run`). Needs `ANTHROPIC_API_KEY`.
- `convert_to_duckdb.py` — JSON → DuckDB via `scorch.records`; validates every
  review; `--rebuild`, `--strict`. No API key.
- `build_okf.py` — reviews → OKF wiki (`--include-examples`). No API key.
- `synthesize.py` — STORM-inspired cited syntheses into OKF `## Curator notes`
  (`--all`, `--dry-run`, or target one `--dimension`/`--concept`). Needs API key.
- `ask_papers.py` — PaperQA2-inspired citation-grounded Q&A over the PDFs
  (`--max-papers N`, default 6). Needs API key.
- `query_literature.py` — natural-language → SQL over the database.

## Schema (`schema/scorch_extraction_schema.json`, v1.2)

Strict types/enums; **N/A policy: never fabricate** — use `"N/A"`, `[]`, or
`null` when the source is silent. 46 questions across screening, metadata,
spatial/temporal, study characteristics, data tables, methods, outcomes,
exposures, demographics, interventions, objectives, research questions,
associations, projections, vulnerable populations, resilience, and summaries.
Human map: `okf/schema/extraction-schema.md`. Every review is validated against
the schema before entering the database.

**Provenance (v1.2):** every substantive (non-`"N/A"`, non-`false`, non-empty)
value must have a matching `extraction_metadata.evidence_log` entry citing the
source PDF **page number** (1-based PDF sheet index) and a **verbatim quote**
(char offsets when available; `line_hint` only when the PDF prints line numbers).
The JSON Schema checks each entry's *shape*; `scorch.records.validate_evidence_coverage`
checks *coverage* — `convert_to_duckdb.py` warns on uncited substantive fields and
`--strict` rejects them. Entries normalize into the `field_evidence` DuckDB table and
render as a `## Sources` block on OKF paper pages and a "Sources" section in the
review PDFs (`scripts/export_review_pdfs.py`).

## Output File Naming

For `Smith_2023_HeatMortality.pdf` → `reviews/Smith_2023_HeatMortality_review.json`.

## Extraction Metadata

Every review carries an `extraction_metadata` block. The schema **requires** four
fields (`extraction_date`, `extractor_agent`, `source_pdf_filename`,
`schema_version`) and allows an optional `notes`. The pipeline also writes
`extraction_model` (read into the DB by `scorch/records.py`) even though it is not a
schema field, so include it:

```json
{
  "extraction_metadata": {
    "extraction_date": "YYYY-MM-DD",
    "extractor_agent": "scorch-pdf-analyzer",
    "extraction_model": "claude-sonnet-4-6",
    "source_pdf_filename": "original_filename.pdf",
    "schema_version": "1.2",
    "notes": "N/A",
    "evidence_log": [
      {"field_path": "metadata.title", "claim": "...", "page_start": 1,
       "page_end": null, "quote": "<verbatim from PDF>",
       "char_start": null, "char_end": null, "line_hint": null}
    ]
  }
}
```

## SCORCH Research Focus

Three core questions: (1) how extreme weather impacts health in the arid SW
US/Mexico; (2) how the climate-disease landscape changes over 5-100 years;
(3) which climate-resilience solutions apply. Six objectives guide relevance
(climate-health impacts, extreme-weather effects, 50-100yr forecasts, vulnerable
communities, research gaps, solutions/adaptations).

## Working in this repo

- Edit the schema mapping in `scorch/records.py`, never inline DDL.
- After adding reviews, run `convert_to_duckdb.py` **and** `build_okf.py`.
- No test/lint/CI harness is configured. The contract check is
  `convert_to_duckdb.py`, which validates every review against the schema
  (`--strict` fails on the first violation); API-calling scripts accept
  `--dry-run`. Fix bad data in the review JSON, not in `scorch/records.py`.
- Python 3.11+: avoid same-quote nested f-strings.
- The top-level `duckdb/` data dir can shadow the `duckdb` library — import the
  library before putting the repo root on `sys.path` (scripts already do this).
