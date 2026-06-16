# SCORCH SDK Scripts

Standalone Python scripts for the SCORCH pipeline. They share the `scorch/`
package (`config`, `records`, `okf`) as the single source of truth for models,
paths, and the schema↔database mapping.

## Prerequisites

```bash
pip install -r requirements.txt          # anthropic, duckdb, jsonschema, pydantic, PyYAML
export ANTHROPIC_API_KEY='your-api-key'  # only for the API-using scripts
```

Models are a tiered cascade configured in `scorch/config.py` (override per stage
with `SCORCH_SCREEN_MODEL` / `SCORCH_EXTRACT_MODEL` / `SCORCH_VERIFY_MODEL` /
`SCORCH_SYNTHESIS_MODEL`):

| Stage | Default |
|-------|---------|
| Screen | `claude-haiku-4-5` |
| Extract | `claude-sonnet-4-6` |
| Verify / synthesize | `claude-opus-4-8` |

## Scripts

### batch_process_pdfs.py  *(needs API key)*
Tiered extraction of `pdfs/*.pdf` → `reviews/*_review.json`.
- Uploads each PDF once via the **Files API**; references it by `file_id` across stages.
- **Prompt caching** on the large schema/system prefix (~90% cheaper prefix).
- **Validates** each extraction against the schema with a one-shot repair pass.
- Records provenance (model, token usage, est. cost) in `extraction_metadata`.

```bash
python scripts/batch_process_pdfs.py --screen --verify   # full pipeline
python scripts/batch_process_pdfs.py --dry-run           # list work, no API calls
```
Flags: `--screen` (Haiku include/exclude gate), `--verify` (Opus audit), `--dry-run`.

### convert_to_duckdb.py  *(no API key)*
`reviews/*.json` → DuckDB + Parquet. DDL and INSERTs are generated from
`scorch/records.py`, and every review is validated with `jsonschema` (invalid
ones are reported and skipped).

```bash
python scripts/convert_to_duckdb.py            # incremental
python scripts/convert_to_duckdb.py --rebuild  # drop & rebuild
python scripts/convert_to_duckdb.py --strict   # abort on first validation error
```

**Tables:** `reviews` (PK `source_pdf_filename`); child tables
`health_outcome_variables`, `climate_weather_variables`, `cofactor_variables`,
`vulnerable_populations`, `correlations`; long-format category tables
`health_outcome_categories`, `exposure_categories`, `resilience_categories`.
Full column list: `okf/datasets/scorch-reviews.md`. Note `publication_year` is
VARCHAR — query with `TRY_CAST(publication_year AS INTEGER)`.

### build_okf.py  *(no API key)*
`reviews/*.json` → the OKF knowledge wiki under `okf/` (paper + concept pages,
`index.md`, `log.md`). Idempotent; preserves `## Curator notes` prose.

```bash
python scripts/build_okf.py                  # from reviews/
python scripts/build_okf.py --include-examples
```

### synthesize.py  *(needs API key)*
STORM-inspired: writes inline-cited evidence syntheses into OKF concept pages
under `## Curator notes`.

```bash
python scripts/synthesize.py --dimension exposures --concept heat
python scripts/synthesize.py --all --dry-run
```

### ask_papers.py  *(needs API key)*
PaperQA2-inspired: citation-grounded Q&A over the PDFs (Files API + citations),
falling back to extracted review summaries when no PDFs are present.

```bash
python scripts/ask_papers.py "How does extreme heat affect mortality in Phoenix?"
python scripts/ask_papers.py --max-papers 4 "What adaptations reduce heat risk?"
```

### query_literature.py  *(needs API key)*
Natural-language → SQL over the DuckDB database (interactive or single-query).

```bash
python scripts/query_literature.py
python scripts/query_literature.py "How many papers per year?"
```

## Complete Workflow

```bash
# 1. Add PDFs to pdfs/
# 2. Extract (screen + verify)
python scripts/batch_process_pdfs.py --screen --verify
# 3. Load the database
python scripts/convert_to_duckdb.py
# 4. Rebuild the knowledge wiki
python scripts/build_okf.py
# 5. Analyze
python scripts/query_literature.py "Show me high-relevance heat papers"
```

All steps are incremental — re-running only processes what's new.

## Troubleshooting

- **API key error:** `export ANTHROPIC_API_KEY='sk-ant-...'`.
- **`duckdb has no attribute 'connect'`:** the top-level `duckdb/` data dir is
  shadowing the library. The scripts import `duckdb` before adding the repo root
  to `sys.path`; if you write your own, do the same.
- **Validation failures:** the converter prints the schema violation per file;
  fix the review JSON at the source (don't relax `scorch/records.py`).
- **Database not found:** run `convert_to_duckdb.py` first.

## Development

- Models/paths/cost: `scorch/config.py`.
- Schema↔row mapping: `scorch/records.py` (single source of truth — edit here,
  never hand-write column lists).
- Extraction contract: `schema/scorch_extraction_schema.json`.
