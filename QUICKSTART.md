# SCORCH Quick Start Guide

Fast reference. See [README.md](README.md) for full docs, [CLAUDE.md](CLAUDE.md)
/ [AGENTS.md](AGENTS.md) for agent conventions, and
[okf/CONVENTIONS.md](okf/CONVENTIONS.md) for the knowledge wiki.

---

## Setup (first time)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY='your-key-here'      # only for API-using steps
echo "export ANTHROPIC_API_KEY='your-key'" >> ~/.bashrc   # persist
```

Models (tiered) are set in `scorch/config.py`: Haiku 4.5 screen → Sonnet 4.6
extract → Opus 4.8 verify/synthesize. Override with `SCORCH_*_MODEL` env vars.

---

## Common Workflows

### 🚀 Process new PDFs (batch)
```bash
cp /path/to/papers/*.pdf pdfs/
python scripts/batch_process_pdfs.py --screen --verify   # extract (Files API + validation)
python scripts/convert_to_duckdb.py                      # load DuckDB (validated)
python scripts/build_okf.py                              # rebuild the OKF wiki
python scripts/query_literature.py                       # analyze
```

### 🔍 Query the database
```bash
python scripts/query_literature.py "How many papers per year?"   # NL → SQL
duckdb duckdb/scorch_reviews.duckdb                              # direct SQL
```

### 📚 Citation-grounded Q&A over the PDFs
```bash
python scripts/ask_papers.py "What adaptations reduce heat-related mortality?"
```

### 🧠 Draft cited synthesis into the wiki
```bash
python scripts/synthesize.py --all          # writes under "## Curator notes"
```

### 🤖 Interactive (Claude Code agents)
`scorch-screener` → `scorch-pdf-analyzer` → `scorch-verifier`
→ `duckdb-schema-converter` → `duckdb-literature-analyst`.

---

## Common queries

**Natural language (`query_literature.py`):**
```
How many papers were published each year?
Show me papers with high relevance ratings
Which papers study heat exposure? vulnerable populations?
```

**Direct SQL:**
```sql
-- Papers per year (publication_year is VARCHAR)
SELECT TRY_CAST(publication_year AS INTEGER) AS yr, COUNT(*)
FROM reviews GROUP BY yr ORDER BY yr DESC;

-- Which papers study heat? (category tables make this a JOIN)
SELECT r.title FROM reviews r
JOIN exposure_categories e ON e.source_pdf_filename = r.source_pdf_filename
WHERE e.category = 'heat';

-- High-relevance papers
SELECT title, citation_apa7 FROM reviews WHERE relevance_rating = 'High';
```

---

## File Locations

| Path | Contents | Tracked? |
|------|----------|----------|
| `pdfs/` | INPUT: PDF articles | gitignored |
| `reviews/` | JSON extractions | gitignored (regenerable) |
| `duckdb/` | Database + Parquet | gitignored (regenerable) |
| `okf/` | **Knowledge wiki (durable, committed)** | ✅ tracked |
| `schema/scorch_extraction_schema.json` | Extraction contract | ✅ |
| `scorch/` | Shared library (source of truth) | ✅ |

---

## Key Scripts

| Script | Purpose | API key? |
|--------|---------|----------|
| `batch_process_pdfs.py` | Extract PDFs → JSON (`--screen`/`--verify`/`--dry-run`) | ✓ |
| `convert_to_duckdb.py` | JSON → DuckDB (validated; `--rebuild`/`--strict`) | ✗ |
| `build_okf.py` | Reviews → OKF wiki (`--include-examples`) | ✗ |
| `synthesize.py` | Cited synthesis → wiki | ✓ |
| `ask_papers.py` | Citation-grounded Q&A | ✓ |
| `query_literature.py` | NL → SQL | ✓ |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ANTHROPIC_API_KEY not found` | `export ANTHROPIC_API_KEY='sk-ant-...'` |
| `Database not found` | `python scripts/convert_to_duckdb.py` |
| `duckdb has no attribute 'connect'` | `duckdb/` dir shadowing the library — run scripts as `python scripts/x.py` |
| Schema validation failures | Converter prints the violation per file; fix the review JSON |
| Want fewer parallel calls | `export SCORCH_BATCH_CONCURRENCY=2` |

---

## Status checks

```bash
ls pdfs/*.pdf | wc -l        # PDFs to process
ls reviews/*_review.json | wc -l   # reviews done
duckdb duckdb/scorch_reviews.duckdb -c "SELECT relevance_rating, COUNT(*) FROM reviews GROUP BY 1"
cat okf/index.md             # wiki catalog
```

---

**Need more?** [README.md](README.md) · [scripts/README.md](scripts/README.md) ·
[schema](schema/scorch_extraction_schema.json) · [wiki conventions](okf/CONVENTIONS.md)
