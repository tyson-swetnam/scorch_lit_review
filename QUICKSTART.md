# SCORCH Quick Start Guide

Fast reference for common tasks. See [README.md](README.md) for detailed documentation.

---

## Setup (First Time Only)

```bash
# Install dependencies
pip install anthropic duckdb

# Set API key
export ANTHROPIC_API_KEY='your-key-here'

# Add to ~/.bashrc for persistence
echo "export ANTHROPIC_API_KEY='your-key-here'" >> ~/.bashrc
```

---

## Common Workflows

### 🚀 Process New PDFs (Batch)

```bash
# 1. Add PDFs
cp /path/to/papers/*.pdf pdfs/

# 2. Extract
python scripts/batch_process_pdfs.py

# 3. Build database
python scripts/convert_to_duckdb.py

# 4. Query
python scripts/query_literature.py
```

### 🔍 Query Existing Database

```bash
# Interactive mode
python scripts/query_literature.py

# Single query
python scripts/query_literature.py "How many papers by year?"

# Direct SQL
duckdb duckdb/scorch_reviews.duckdb
> SELECT title FROM reviews LIMIT 5;
```

### 📊 Common Queries

**In query_literature.py:**
```
How many papers were published each year?
Show me papers with high relevance ratings
What are the most common health outcomes studied?
Which papers focus on vulnerable populations?
Give me papers about heat exposure
Show papers published after 2020
What climate models are used in projections?
```

**Direct SQL:**
```sql
-- Papers by year
SELECT publication_year, COUNT(*) FROM reviews GROUP BY publication_year;

-- High relevance papers
SELECT title, citation_apa7 FROM reviews WHERE relevance_rating = 'High';

-- Top health outcomes
SELECT variable, COUNT(*) FROM health_outcome_variables GROUP BY variable ORDER BY COUNT(*) DESC LIMIT 10;

-- Papers with vulnerable populations
SELECT DISTINCT r.title FROM reviews r JOIN vulnerable_populations vp ON r.source_pdf_filename = vp.source_pdf_filename;
```

---

## File Locations

| Path | Contents |
|------|----------|
| `pdfs/` | **INPUT:** Place PDF articles here |
| `reviews/` | **OUTPUT:** JSON extraction files |
| `duckdb/scorch_reviews.duckdb` | **OUTPUT:** Main database |
| `duckdb/scorch_reviews.parquet` | **OUTPUT:** Parquet export |
| `schema/scorch_extraction_schema.json` | Extraction schema definition |

---

## Key Scripts

| Script | Purpose | API Key? |
|--------|---------|----------|
| `batch_process_pdfs.py` | Extract PDFs → JSON | ✓ Required |
| `convert_to_duckdb.py` | JSON → Database | ✗ Not needed |
| `query_literature.py` | Natural language queries | ✓ Required |

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY='your-key'
```

### "Database not found"
```bash
python scripts/convert_to_duckdb.py
```

### "No new reviews to process"
```bash
# Already processed! Check:
ls reviews/
```

### Out of memory
```python
# Edit scripts/batch_process_pdfs.py line 234:
batch_size = 2  # Lower from 4
```

---

## Status Checks

```bash
# PDFs ready to process
ls pdfs/*.pdf | wc -l

# Reviews completed
ls reviews/*_review.json | wc -l

# Database stats
duckdb duckdb/scorch_reviews.duckdb << EOF
SELECT COUNT(*) as total_papers FROM reviews;
SELECT relevance_rating, COUNT(*) FROM reviews GROUP BY relevance_rating;
EOF
```

---

## Export Data

```bash
# CSV
duckdb duckdb/scorch_reviews.duckdb << EOF
COPY (SELECT * FROM reviews) TO 'output.csv' (HEADER, DELIMITER ',');
EOF

# JSON
duckdb duckdb/scorch_reviews.duckdb << EOF
COPY (SELECT * FROM reviews) TO 'output.json';
EOF

# Parquet (already available)
cp duckdb/scorch_reviews.parquet /path/to/destination/
```

---

## Daily Workflow

```bash
# Morning: Add new PDFs
cp ~/Downloads/new_papers/*.pdf pdfs/

# Extract
python scripts/batch_process_pdfs.py

# Update database
python scripts/convert_to_duckdb.py

# Analyze
python scripts/query_literature.py "Show me the new papers"
```

---

## Backup

```bash
# Backup database
cp duckdb/scorch_reviews.duckdb backups/scorch_$(date +%Y%m%d).duckdb

# Backup reviews
tar -czf backups/reviews_$(date +%Y%m%d).tar.gz reviews/
```

---

## Performance Tips

- **<5 PDFs:** Use interactive agents in Claude Code
- **5-20 PDFs:** Use SDK batch scripts
- **20+ PDFs:** Increase batch_size to 8, ensure 16GB+ RAM
- **100+ PDFs:** Process in chunks, run overnight

---

## Getting Help

1. **Full documentation:** [README.md](README.md)
2. **SDK scripts guide:** [scripts/README.md](scripts/README.md)
3. **Schema reference:** [schema/scorch_extraction_schema.json](schema/scorch_extraction_schema.json)
4. **Claude Code guide:** [CLAUDE.md](CLAUDE.md)

---

## Database Schema Quick Reference

**Main Table:** `reviews`
- `source_pdf_filename` (PK)
- `title`, `citation_apa7`
- `publication_year`
- `relevance_rating` (High/Medium/Low)
- `paper_summary`, `conclusions_summary`

**Related Tables:**
- `health_outcome_variables` - Health outcomes
- `climate_weather_variables` - Climate variables
- `cofactor_variables` - Confounders
- `vulnerable_populations` - At-risk groups
- `correlations` - Statistical findings

All tables join on `source_pdf_filename`.

---

**Need more detail?** See [README.md](README.md) for comprehensive documentation.
