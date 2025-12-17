# SCORCH Literature Review System

**Southwest Center on Resilience for Climate Change and Health (SCORCH)**

An AI-powered literature review system for extracting structured data from climate-health research PDFs, with focus on arid and semi-arid regions of the southwestern United States and northern Mexico.

---

## Table of Contents

- [Overview](#overview)
- [Research Focus](#research-focus)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [User Manual](#user-manual)
  - [Interactive Workflow (Claude Code)](#interactive-workflow-claude-code)
  - [Batch Processing Workflow (SDK Scripts)](#batch-processing-workflow-sdk-scripts)
- [Project Architecture](#project-architecture)
- [Extraction Schema](#extraction-schema)
- [Database Schema](#database-schema)
- [Querying Your Data](#querying-your-data)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The SCORCH Literature Review System automates the extraction of structured information from climate-health research articles. Using Claude AI agents, the system:

1. **Analyzes PDF research articles** and extracts 46 structured data points
2. **Converts extractions** to a queryable DuckDB database
3. **Enables natural language queries** for analysis and reporting

### Key Features

- ✅ **Automated extraction** - 46-question structured schema covering study metadata, methods, findings, and relevance
- ✅ **Incremental processing** - Only processes new PDFs and reviews
- ✅ **Parallel execution** - Batch process multiple PDFs simultaneously
- ✅ **Standardized data** - Strict validation, enums, and data types
- ✅ **Multiple query interfaces** - Natural language, SQL, or programmatic access
- ✅ **Portable exports** - DuckDB and Parquet formats

### Supported Workflows

| Workflow | Use Case | Tools |
|----------|----------|-------|
| **Interactive** | One-off analysis, debugging, exploration | Claude Code agents |
| **Batch** | Large-scale processing, automation, CI/CD | Python SDK scripts |

---

## Research Focus

SCORCH addresses three core research questions:

1. **How do extreme weather events impact human health** in arid/semi-arid SW US and northern Mexico regions?
2. **How will the climate-related disease landscape change** over 5-100 year time horizons?
3. **What successful climate resilience solutions** are applicable to these regions?

### Six Research Objectives

1. Climate-health impacts in arid/semi-arid SW US and northern Mexico
2. Extreme weather and temperature/precipitation fluctuation health effects
3. Climate-health forecasts for the next 50-100 years
4. Vulnerable community identification
5. Research gap identification
6. Solutions and adaptations for climate resilience

---

## Quick Start

### Prerequisites

```bash
# Python 3.8+
python --version

# Install dependencies
pip install anthropic duckdb

# Set API key for SDK scripts
export ANTHROPIC_API_KEY='your-api-key-here'
```

### Process Your First PDF

**Option 1: Interactive (Claude Code)**
```bash
# Open Claude Code and use agents
# 1. Place PDF in pdfs/ folder
# 2. Ask: "Analyze the new PDF using scorch-pdf-analyzer"
# 3. Ask: "Convert reviews to database using duckdb-schema-converter"
```

**Option 2: Batch (SDK Scripts)**
```bash
# 1. Add PDFs to pdfs/ directory
cp your_paper.pdf pdfs/

# 2. Extract data
python scripts/batch_process_pdfs.py

# 3. Build database
python scripts/convert_to_duckdb.py

# 4. Query
python scripts/query_literature.py
```

---

## Installation

### 1. Clone or Download Repository

```bash
git clone <repository-url>
cd scorch_lit_review
```

### 2. Install Python Dependencies

```bash
pip install anthropic duckdb
```

**Required packages:**
- `anthropic` (Claude SDK) - For AI-powered extraction and queries
- `duckdb` - For database operations

### 3. Set Up API Key

**For SDK Scripts:**
```bash
# Add to ~/.bashrc or ~/.zshrc for persistence
export ANTHROPIC_API_KEY='sk-ant-api...'
```

**For Claude Code:**
- API key is managed automatically by Claude Code
- No manual configuration needed

### 4. Verify Installation

```bash
# Check Python
python --version  # Should be 3.8+

# Check dependencies
python -c "import anthropic; import duckdb; print('✓ All dependencies installed')"

# Check scripts are executable
ls -l scripts/*.py
```

### Directory Structure

```
scorch_lit_review/
├── pdfs/                    # Input: Place PDF articles here
├── reviews/                 # Output: JSON extraction files
├── duckdb/                  # Output: Database and Parquet files
├── schema/                  # Extraction schema definition
│   └── scorch_extraction_schema.json
├── scripts/                 # SDK scripts for batch processing
│   ├── batch_process_pdfs.py
│   ├── convert_to_duckdb.py
│   ├── query_literature.py
│   └── README.md
├── .claude/agents/          # Claude Code agent definitions
│   ├── scorch-pdf-analyzer.md
│   ├── duckdb-schema-converter.md
│   └── duckdb-literature-analyst.md
├── CLAUDE.md                # Instructions for Claude Code
└── README.md                # This file
```

---

## User Manual

Choose your workflow based on your needs:

### Interactive Workflow (Claude Code)

**Best for:** Ad-hoc analysis, debugging, exploration, learning

#### Step 1: Prepare PDFs

```bash
# Add PDF files to pdfs/ directory
pdfs/
  ├── Smith_2023_HeatMortality.pdf
  ├── Jones_2022_DroughtHealth.pdf
  └── Garcia_2024_UrbanHeat.pdf
```

#### Step 2: Extract Data from PDFs

In Claude Code, use the Task tool to invoke the agent:

```
Can you analyze the PDFs in the pdfs/ folder using the scorch-pdf-analyzer agent?
```

The agent will:
- Identify unprocessed PDFs
- Read each PDF document
- Extract data according to the 46-question schema
- Save JSON files to `reviews/` folder

**Output:** `reviews/Smith_2023_HeatMortality_review.json`

#### Step 3: Convert to Database

```
Convert the new reviews to the database using duckdb-schema-converter
```

The agent will:
- Scan for new JSON files
- Create/update DuckDB database
- Export to Parquet format
- Report statistics

**Output:**
- `duckdb/scorch_reviews.duckdb`
- `duckdb/scorch_reviews.parquet`

#### Step 4: Query Your Data

```
Use duckdb-literature-analyst to show me papers by publication year
```

The agent will:
- Write optimized SQL queries
- Execute against the database
- Format results
- Provide insights

---

### Batch Processing Workflow (SDK Scripts)

**Best for:** Large datasets, automation, scheduled jobs, production

#### Step 1: Prepare Environment

```bash
# Set API key
export ANTHROPIC_API_KEY='your-api-key-here'

# Verify setup
python scripts/batch_process_pdfs.py --help 2>/dev/null || echo "Ready to process"
```

#### Step 2: Batch Extract PDFs

```bash
# Add PDFs to pdfs/ directory
cp /path/to/papers/*.pdf pdfs/

# Process all unreviewed PDFs
python scripts/batch_process_pdfs.py
```

**Features:**
- Processes 4 PDFs in parallel (configurable)
- Each PDF gets independent 1M token context
- Progress reporting per batch
- Error handling with debug files

**Output:**
```
============================================================
Batch 1/3 - Processing 4 PDFs in parallel
============================================================
📄 Processing: Smith_2023.pdf
📄 Processing: Jones_2022.pdf
📄 Processing: Garcia_2024.pdf
📄 Processing: Lee_2021.pdf
  ✓ Success: Smith_2023_review.json (45231 bytes)
  ✓ Success: Jones_2022_review.json (38492 bytes)
  ✓ Success: Garcia_2024_review.json (41203 bytes)
  ✓ Success: Lee_2021_review.json (39847 bytes)

📊 Batch 1 complete: 4/4 succeeded
```

#### Step 3: Convert to Database

```bash
python scripts/convert_to_duckdb.py
```

**Features:**
- Incremental updates (skips existing)
- No API key required
- Automatic schema management
- Parquet export

**Output:**
```
============================================================
SCORCH DuckDB Converter
============================================================
✓ Connected to: duckdb/scorch_reviews.duckdb
✓ Database schema created/verified

📊 Status:
  - Existing reviews in DB: 15
  - New reviews to add: 4

============================================================
Processing new reviews...
============================================================
  ✓ Added: Smith_2023_review.json
  ✓ Added: Jones_2022_review.json
  ✓ Added: Garcia_2024_review.json
  ✓ Added: Lee_2021_review.json

============================================================
✓ Exported to Parquet: duckdb/scorch_reviews.parquet

============================================================
CONVERSION COMPLETE
============================================================
✓ Successfully added: 4
📊 Total reviews in database: 19
```

#### Step 4: Query Interactively

```bash
# Interactive mode
python scripts/query_literature.py

# Single query mode
python scripts/query_literature.py "How many papers were published each year?"
```

**Interactive Example:**
```
============================================================
SCORCH Literature Analyst
============================================================
Database: duckdb/scorch_reviews.duckdb
Rows: 19
============================================================

Ask questions about your literature review data.

🔍 Query: How many papers have high relevance ratings?

💭 Analyzing...

📊 SQL Query:
SELECT relevance_rating, COUNT(*) as count
FROM reviews
GROUP BY relevance_rating
ORDER BY count DESC

✓ Results:
relevance_rating | count
-----------------+------
High             | 12
Medium           | 5
Low              | 2

(3 rows)
```

---

## Project Architecture

### Data Flow

```
┌─────────────┐
│   PDFs/     │  Input: Research articles
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Extraction Layer               │
│  • scorch-pdf-analyzer (agent)  │  AI-powered extraction
│  • batch_process_pdfs.py (SDK)  │  46-question schema
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────┐
│  reviews/   │  Output: JSON files
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Database Layer                 │
│  • duckdb-schema-converter      │  JSON → SQL
│  • convert_to_duckdb.py         │  Normalization
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────┐
│  duckdb/    │  Output: Queryable database
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Query Layer                    │
│  • duckdb-literature-analyst    │  Natural language
│  • query_literature.py          │  SQL generation
│  • Direct SQL (DuckDB CLI)      │  Programmatic access
└─────────────────────────────────┘
```

### Component Comparison

| Component | Interactive | SDK Script | Purpose |
|-----------|-------------|------------|---------|
| **PDF Extraction** | scorch-pdf-analyzer | batch_process_pdfs.py | Parse PDFs → JSON |
| **DB Conversion** | duckdb-schema-converter | convert_to_duckdb.py | JSON → DuckDB |
| **Querying** | duckdb-literature-analyst | query_literature.py | Natural language → SQL |

---

## Extraction Schema

The system extracts **46 structured data points** organized into sections:

### Q1-Q2: Screening
- Focuses on arid/semi-arid SW US/Mexico regions
- Includes primary data for the region

### Q3-Q9: Metadata
- Title, citation (APA 7)
- Spatial scale, geographic areas
- Publication year, data date ranges

### Q10-Q12: Study Characteristics
- Setting (urban/rural/mixed)
- Aridity classification
- Study design (cohort, case-control, cross-sectional, etc.)

### Q13-Q15: Data Tables
- **Health outcome variables** - Disease, mortality, morbidity with spatial resolution
- **Co-factor variables** - Demographics, SES, environmental confounders
- **Climate/weather variables** - Temperature, precipitation, extreme events

### Q16-Q22: Methods & Outcomes
- Analytical methods (regression, time-series, etc.)
- Primary health outcomes
- Climate exposures examined
- Demographics studied

### Q23-Q28: Research Alignment
- Interventions or adaptations evaluated
- SCORCH objectives addressed
- Research questions alignment

### Q29-Q31: Statistical Findings
- Unquantified impacts described
- Effect sizes and correlations
- Significance levels

### Q32-Q35: Climate Projections
- Climate models used (CMIP5, CMIP6, downscaling)
- Emission scenarios (RCP, SSP)
- Time horizons
- Projected health impacts

### Q36-Q39: Vulnerable Populations
- Population groups identified
- Vulnerability reasons
- Resilience measures
- Community-level factors

### Q40-Q46: Overall Assessment
- Relevance rating (High/Medium/Low)
- Relevance justification
- Paper summary
- Conclusions summary
- Research limitations
- Identified gaps
- Overall reviewer comments

### Data Quality Standards

- **N/A Policy:** Use `"N/A"` when information is not present - never fabricate data
- **Boolean fields:** `true`/`false` for yes/no questions
- **Arrays:** Use `[]` for empty lists, respect max items constraints
- **Enums:** Many fields have predefined valid options
- **Validation:** Automatic type checking and constraint enforcement

---

## Database Schema

### Main Tables

#### `reviews` Table
Core metadata and assessments for each paper.

**Key Columns:**
- `source_pdf_filename` (PRIMARY KEY) - Original PDF filename
- `title`, `citation_apa7` - Bibliographic info
- `publication_year` - Publication year
- `spatial_scale` - Study geographic scale
- `geographic_areas[]` - Array of locations
- `study_design` - Research design type
- `relevance_rating` - High/Medium/Low
- `paper_summary` - Paper summary text
- `conclusions_summary` - Key conclusions

#### `health_outcome_variables` Table
Health outcomes tracked in studies.

**Columns:**
- `source_pdf_filename` (FK)
- `variable` - Health outcome name
- `spatial_resolution` - Geographic granularity
- `data_source` - Data source

#### `climate_weather_variables` Table
Climate variables analyzed.

**Columns:**
- `source_pdf_filename` (FK)
- `variable` - Climate variable name
- `spatial_resolution` - Geographic granularity
- `data_source` - Data source

#### `cofactor_variables` Table
Confounding factors considered.

**Columns:**
- `source_pdf_filename` (FK)
- `variable` - Co-factor name
- `spatial_resolution` - Geographic granularity
- `data_source` - Data source

#### `vulnerable_populations` Table
Population groups identified as vulnerable.

**Columns:**
- `source_pdf_filename` (FK)
- `population_group` - Population description
- `vulnerability_reasons` - Why vulnerable

#### `correlations` Table
Statistical relationships reported.

**Columns:**
- `source_pdf_filename` (FK)
- `variable` - Variable name
- `effect_size_correlation` - Effect size or correlation
- `significance` - P-value or significance level
- `confidence_interval` - CI range

### Relationships

```
reviews (1) ──< (N) health_outcome_variables
        (1) ──< (N) climate_weather_variables
        (1) ──< (N) cofactor_variables
        (1) ──< (N) vulnerable_populations
        (1) ──< (N) correlations
```

---

## Querying Your Data

### Method 1: Natural Language (Recommended)

```bash
python scripts/query_literature.py
```

**Example questions:**
- "Show me all papers published after 2020"
- "What are the most common health outcomes?"
- "Which papers focus on vulnerable populations?"
- "Give me papers about heat exposure with high relevance"
- "What climate variables are most frequently studied?"

### Method 2: Direct SQL

```bash
# Open DuckDB CLI
duckdb duckdb/scorch_reviews.duckdb
```

**Example queries:**

```sql
-- Papers by publication year
SELECT publication_year, COUNT(*) as count
FROM reviews
GROUP BY publication_year
ORDER BY publication_year DESC;

-- High relevance papers
SELECT title, relevance_rating, publication_year
FROM reviews
WHERE relevance_rating = 'High'
ORDER BY publication_year DESC;

-- Most common health outcomes
SELECT variable, COUNT(*) as frequency
FROM health_outcome_variables
GROUP BY variable
ORDER BY frequency DESC
LIMIT 10;

-- Papers studying vulnerable populations
SELECT DISTINCT r.title, vp.population_group, vp.vulnerability_reasons
FROM reviews r
JOIN vulnerable_populations vp ON r.source_pdf_filename = vp.source_pdf_filename
ORDER BY r.publication_year DESC;

-- Climate variables by study design
SELECT r.study_design, cv.variable, COUNT(*) as count
FROM reviews r
JOIN climate_weather_variables cv ON r.source_pdf_filename = cv.source_pdf_filename
GROUP BY r.study_design, cv.variable
ORDER BY count DESC;
```

### Method 3: Python/Programmatic

```python
import duckdb

# Connect
con = duckdb.connect('duckdb/scorch_reviews.duckdb')

# Query
results = con.execute("""
    SELECT title, publication_year, relevance_rating
    FROM reviews
    WHERE relevance_rating = 'High'
    ORDER BY publication_year DESC
""").fetchall()

# Process
for title, year, rating in results:
    print(f"{year}: {title} ({rating})")

con.close()
```

### Method 4: Export to Other Formats

```bash
# Export to CSV
duckdb duckdb/scorch_reviews.duckdb << EOF
COPY (SELECT * FROM reviews) TO 'output.csv' (HEADER, DELIMITER ',');
EOF

# Export to JSON
duckdb duckdb/scorch_reviews.duckdb << EOF
COPY (SELECT * FROM reviews) TO 'output.json';
EOF

# Use Parquet directly (already created)
# Compatible with pandas, R, Spark, etc.
cp duckdb/scorch_reviews.parquet /path/to/analysis/
```

---

## Troubleshooting

### Common Issues

#### API Key Not Found

**Error:** `ANTHROPIC_API_KEY not found`

**Solution:**
```bash
export ANTHROPIC_API_KEY='sk-ant-api...'

# For persistence, add to ~/.bashrc or ~/.zshrc
echo "export ANTHROPIC_API_KEY='your-key-here'" >> ~/.bashrc
source ~/.bashrc
```

#### Database Not Found

**Error:** `Database not found: duckdb/scorch_reviews.duckdb`

**Solution:**
```bash
# Create database by converting reviews
python scripts/convert_to_duckdb.py
```

#### JSON Parse Errors

**Error:** `Invalid JSON - {error details}`

**Solution:**
- Check `reviews/*_debug.txt` for raw Claude responses
- Verify PDF is readable and not corrupted
- Try processing single PDF first to isolate issue
- Check schema version matches expected format

#### Memory Issues with Batch Processing

**Error:** System runs out of memory

**Solution:**
```python
# Edit scripts/batch_process_pdfs.py line 234
batch_size = 2  # Reduce from default 4

# Or process one at a time
batch_size = 1
```

#### PDF Reading Errors

**Error:** `Error reading PDF`

**Solution:**
- Verify PDF is not password protected
- Check PDF is not corrupted: `file pdfs/yourfile.pdf`
- Try opening PDF manually to verify it's readable
- Some PDFs may be image-based (scanned) - extraction quality varies

#### DuckDB Table Not Found

**Error:** `Table 'reviews' does not exist`

**Solution:**
```bash
# Schema wasn't created - run converter again
python scripts/convert_to_duckdb.py
```

### Debugging Tips

1. **Test with single PDF first**
   ```bash
   # Move all but one PDF temporarily
   mkdir pdfs_backup
   mv pdfs/*.pdf pdfs_backup/
   cp pdfs_backup/test_paper.pdf pdfs/

   # Process
   python scripts/batch_process_pdfs.py
   ```

2. **Check intermediate outputs**
   ```bash
   # Verify JSON structure
   cat reviews/latest_review.json | python -m json.tool

   # Check review file size
   ls -lh reviews/
   ```

3. **Validate database**
   ```bash
   duckdb duckdb/scorch_reviews.duckdb << EOF
   SHOW TABLES;
   SELECT COUNT(*) FROM reviews;
   EOF
   ```

4. **Enable verbose output** (for debugging)
   ```python
   # Add to scripts for more logging
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## Examples

### Example 1: Process 10 New Papers

```bash
# 1. Add PDFs
cp /research/new_papers/*.pdf pdfs/

# 2. Extract (parallel)
python scripts/batch_process_pdfs.py
# Output: 10 new JSON files in reviews/

# 3. Update database
python scripts/convert_to_duckdb.py
# Output: Database updated with 10 new entries

# 4. Query for insights
python scripts/query_literature.py "What health outcomes are covered in the new papers?"
```

### Example 2: Generate Annual Report

```bash
python scripts/query_literature.py << EOF
Show me a breakdown of papers by publication year with relevance ratings
EOF
```

### Example 3: Find Papers on Specific Topic

```bash
python scripts/query_literature.py "Find papers that study heat exposure and cardiovascular health"
```

### Example 4: Export High-Relevance Papers

```bash
duckdb duckdb/scorch_reviews.duckdb << EOF
COPY (
    SELECT title, citation_apa7, paper_summary, publication_year
    FROM reviews
    WHERE relevance_rating = 'High'
    ORDER BY publication_year DESC
) TO 'high_relevance_papers.csv' (HEADER, DELIMITER ',');
EOF
```

### Example 5: Incremental Daily Updates

```bash
#!/bin/bash
# daily_update.sh - Run as cron job

export ANTHROPIC_API_KEY='your-key'

# Process new PDFs
python scripts/batch_process_pdfs.py >> logs/extraction_$(date +%Y%m%d).log 2>&1

# Update database
python scripts/convert_to_duckdb.py >> logs/database_$(date +%Y%m%d).log 2>&1

# Generate daily report
python scripts/query_literature.py "Show me papers added this week" > reports/weekly_$(date +%Y%m%d).txt
```

---

## Advanced Usage

### Custom Batch Sizes

Edit `scripts/batch_process_pdfs.py`:
```python
# Line 234
batch_size = 8  # Increase for more parallelism (requires more memory)
```

### Custom Schema Modifications

Edit `schema/scorch_extraction_schema.json` to add/modify questions. Both interactive and SDK scripts automatically load the current schema.

### Database Backup

```bash
# Backup database
cp duckdb/scorch_reviews.duckdb duckdb/scorch_reviews_backup_$(date +%Y%m%d).duckdb

# Backup Parquet
cp duckdb/scorch_reviews.parquet duckdb/scorch_reviews_backup_$(date +%Y%m%d).parquet
```

### Integration with Other Tools

**Pandas (Python):**
```python
import pandas as pd
import duckdb

con = duckdb.connect('duckdb/scorch_reviews.duckdb')
df = con.execute("SELECT * FROM reviews").df()
print(df.head())
```

**R:**
```r
library(duckdb)
con <- dbConnect(duckdb::duckdb(), "duckdb/scorch_reviews.duckdb")
reviews <- dbGetQuery(con, "SELECT * FROM reviews")
head(reviews)
```

**Apache Spark:**
```python
df = spark.read.parquet("duckdb/scorch_reviews.parquet")
df.show()
```

---

## Contributing

### Adding New Features

1. **New extraction fields**: Edit `schema/scorch_extraction_schema.json`
2. **New database columns**: Update `scripts/convert_to_duckdb.py` schema
3. **New analysis queries**: Add to `scripts/query_literature.py` examples

### Code Style

- Python: PEP 8
- SQL: Uppercase keywords, snake_case identifiers
- Documentation: Markdown with clear examples

### Testing

```bash
# Test with sample PDF
cp test_data/sample.pdf pdfs/
python scripts/batch_process_pdfs.py

# Verify extraction
cat reviews/sample_review.json | python -m json.tool

# Test database
python scripts/convert_to_duckdb.py
python scripts/query_literature.py "SELECT COUNT(*) FROM reviews"
```

---

## Performance Notes

### Processing Speed

- **Single PDF extraction**: ~30-90 seconds (varies by PDF length)
- **Batch of 4 PDFs**: ~2-3 minutes (parallel)
- **Database conversion**: <5 seconds for 100 reviews
- **Queries**: Milliseconds to seconds depending on complexity

### Resource Requirements

- **Memory**: 2GB minimum, 8GB+ recommended for large batches
- **Storage**: ~50KB per JSON review, ~10MB per 100 papers in database
- **API costs**: ~$0.30-$1.50 per PDF depending on length (Claude Sonnet 4.5)

### Optimization Tips

1. **Batch processing**: Use SDK scripts for >5 PDFs
2. **Parallel execution**: Adjust batch_size based on available RAM
3. **Database queries**: Use indexes on frequently queried columns
4. **API costs**: Process during off-peak hours if running large batches

---

## Citation

If you use this system in your research, please cite:

```bibtex
@software{scorch_lit_review,
  title={SCORCH Literature Review System},
  author={Southwest Center on Resilience for Climate Change and Health},
  year={2024},
  url={https://github.com/your-repo/scorch_lit_review}
}
```

---

## License

[Add your license here]

---

## Support

For issues, questions, or contributions:
- **GitHub Issues**: [repository-url/issues]
- **Documentation**: See `scripts/README.md` for SDK details
- **Schema Reference**: See `schema/scorch_extraction_schema.json`

---

## Acknowledgments

Powered by:
- **Claude AI** (Anthropic) - AI extraction and analysis
- **DuckDB** - High-performance analytical database
- **Python** - Scripting and automation

Developed for the **Southwest Center on Resilience for Climate Change and Health (SCORCH)** research initiative.

---

**Last Updated:** 2024-12-17
**Version:** 1.1
