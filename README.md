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
- [Models & Cost](#models--cost)
- [Knowledge Wiki (OKF)](#knowledge-wiki-okf)
- [Extraction Schema](#extraction-schema)
- [Database Schema](#database-schema)
- [Querying Your Data](#querying-your-data)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The SCORCH Literature Review System automates the extraction of structured information from climate-health research articles. Using a tiered cascade of Claude models, the system:

1. **Screens, extracts, and verifies** PDF research articles against a 46-point schema
2. **Converts validated extractions** to a queryable DuckDB database
3. **Builds a cross-linked knowledge wiki** (OKF) as the durable, version-controlled artifact
4. **Enables natural language queries** and citation-grounded Q&A for analysis and reporting

### Key Features

- ✅ **Tiered extraction** - Haiku screens, Sonnet extracts, Opus verifies/synthesizes (see [Models & Cost](#models--cost))
- ✅ **Schema-validated** - Every review is checked against the JSON Schema with a repair pass; the DuckDB schema is generated from one canonical field list and cannot drift
- ✅ **Incremental processing** - Only processes new PDFs and reviews
- ✅ **Knowledge wiki** - Cross-linked OKF markdown concept docs, the durable git-tracked knowledge layer
- ✅ **Multiple query interfaces** - Natural language → SQL, citation-grounded Q&A, direct SQL, or programmatic access
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
# Python 3.11+ recommended (3.8+ works for the scripts)
python --version

# Install dependencies
pip install -r requirements.txt

# Set API key for SDK scripts
export ANTHROPIC_API_KEY='your-api-key-here'
```

### Process Your First PDF

**Option 1: Interactive (Claude Code)**
```bash
# Open Claude Code and use agents
# 1. Place PDF in pdfs/ folder
# 2. Ask: "Screen the new PDF using scorch-screener"        (PRISMA-style include/exclude)
# 3. Ask: "Analyze the PDF using scorch-pdf-analyzer"
# 4. Ask: "Audit the extraction using scorch-verifier"
# 5. Ask: "Convert reviews to database using duckdb-schema-converter"
```

**Option 2: Batch (SDK Scripts)**
```bash
# 1. Add PDFs to pdfs/ directory
cp your_paper.pdf pdfs/

# 2. Extract data (optionally screen first and verify after)
python scripts/batch_process_pdfs.py --screen --verify

# 3. Build database (validates every review)
python scripts/convert_to_duckdb.py

# 4. Build / refresh the knowledge wiki
python scripts/build_okf.py

# 5. Query
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
pip install -r requirements.txt
```

**Required packages (see `requirements.txt`):**
- `anthropic` - Claude API for extraction, citations, and structured outputs
- `duckdb` - Analytical database and Parquet export
- `jsonschema` - Validates reviews against `schema/scorch_extraction_schema.json`
- `pydantic` - Typed models for structured outputs
- `PyYAML` - Reads/writes OKF YAML frontmatter

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
python -c "import anthropic, duckdb, jsonschema, pydantic, yaml; print('✓ All dependencies installed')"

# Check scripts are executable
ls -l scripts/*.py
```

### Directory Structure

`pdfs/`, `reviews/`, and `duckdb/` are **gitignored** (large and regenerable). The committed
`okf/` wiki, the `scorch/` package, the schema, and the scripts are the durable, version-controlled
artifacts.

```
scorch_lit_review/
├── pdfs/                    # Input: Place PDF articles here          (gitignored)
├── reviews/                 # Intermediate: JSON extraction files     (gitignored)
├── duckdb/                  # Output: Database and Parquet files      (gitignored)
├── okf/                     # Knowledge wiki: cross-linked markdown    (committed)
│   ├── papers/ health-outcomes/ exposures/ resilience/ populations/ regions/
│   ├── datasets/scorch-reviews.md     # generated column reference for the DB
│   ├── schema/extraction-schema.md
│   ├── index.md  log.md  CONVENTIONS.md
├── scorch/                  # Shared package: single source of truth
│   ├── config.py            # Model IDs, paths, cost estimates
│   ├── records.py           # Canonical schema → DB-row mapping (DDL + INSERTs)
│   └── okf.py               # OKF wiki read/write helpers
├── schema/                  # Extraction schema definition
│   └── scorch_extraction_schema.json
├── scripts/                 # SDK scripts for batch processing
│   ├── batch_process_pdfs.py    # tiered screen → extract → verify
│   ├── convert_to_duckdb.py     # JSON → DuckDB (validated)
│   ├── build_okf.py             # reviews → okf/ wiki
│   ├── synthesize.py            # cited evidence syntheses (STORM-inspired)
│   ├── ask_papers.py            # citation-grounded Q&A (PaperQA2-inspired)
│   ├── query_literature.py      # natural language → SQL
│   └── README.md
├── .claude/agents/          # Claude Code agent definitions
│   ├── scorch-screener.md           # Haiku PRISMA-style include/exclude
│   ├── scorch-pdf-analyzer.md
│   ├── scorch-verifier.md           # Opus independent audit
│   ├── duckdb-schema-converter.md
│   └── duckdb-literature-analyst.md
├── requirements.txt         # Python dependencies
├── AGENTS.md                # Condensed conventions for AI agents
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

#### Step 2: Screen, Extract, and Verify

In Claude Code, use the Task tool to invoke the agents in order. Screening and
verification are optional but recommended for quality control.

```
1. Screen the PDFs in pdfs/ using the scorch-screener agent     (include/exclude on Q1-Q2)
2. Analyze the included PDFs using the scorch-pdf-analyzer agent
3. Audit each extraction using the scorch-verifier agent        (Opus, vs. the PDF)
```

The agents will:
- **scorch-screener** (Haiku) — apply a PRISMA-style include/exclude gate on the
  regional-focus and primary-data screening questions
- **scorch-pdf-analyzer** — read each included PDF and extract data according to
  the 46-question schema, saving JSON files to `reviews/`
- **scorch-verifier** (Opus) — independently audit each extraction against the
  source PDF for hallucinations and N/A-policy violations

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

#### Step 5: Build the Knowledge Wiki

```bash
python scripts/build_okf.py
```

Regenerates the cross-linked OKF markdown wiki under `okf/` from the reviews.
Curated prose under `## Curator notes` is preserved across rebuilds. See
[Knowledge Wiki (OKF)](#knowledge-wiki-okf).

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

# Process all unreviewed PDFs (tiered pipeline)
python scripts/batch_process_pdfs.py --screen --verify

# Preview the work without making any API calls
python scripts/batch_process_pdfs.py --dry-run
```

**What it does:**
- Uploads each PDF once via the **Files API** and references it by `file_id` across stages
- Caches the (large, stable) schema prefix with **prompt caching** to cut cost
- `--screen` — cheap Haiku include/exclude gate on the arid-SW screening questions
- Extracts the 46-field schema with Sonnet, then **validates** the result against the
  schema with a one-shot repair pass
- `--verify` — Opus audit pass flagging likely hallucinations / N/A-policy violations
- Records provenance (model, token usage, cost) in `extraction_metadata`
- Processes up to 4 PDFs concurrently (override with `SCORCH_BATCH_CONCURRENCY`)

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

python scripts/convert_to_duckdb.py --rebuild   # drop & rebuild all tables
python scripts/convert_to_duckdb.py --strict    # abort on the first validation error
```

**Features:**
- Validates every review against the schema with `jsonschema` — invalid reviews are
  reported and skipped (use `--strict` to abort instead)
- Incremental updates (skips reviews already in the DB)
- No API key required
- Schema (DDL + INSERTs) generated from `scorch/records.py`, so columns cannot drift
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

#### Step 5: Build / Refresh the Knowledge Wiki

```bash
python scripts/build_okf.py                    # reviews → okf/ wiki (no API key)
python scripts/synthesize.py --all             # draft cited "Curator notes" (needs API key)
python scripts/synthesize.py --all --dry-run   # list targets, no API call
```

`build_okf.py` regenerates the cross-linked OKF markdown under `okf/`.
`synthesize.py` (STORM-inspired) writes cited evidence syntheses into concept pages
under `## Curator notes`; target a single page with `--dimension`/`--concept`.

#### Step 6: Ask the Papers Directly (Citation-Grounded Q&A)

```bash
python scripts/ask_papers.py "What adaptations reduce heat risk in arid cities?"
python scripts/ask_papers.py --max-papers 4 --dry-run "test question"
```

`ask_papers.py` (PaperQA2-inspired) answers questions with inline citations by
attaching the PDFs via the Files API; it falls back to the extracted review
summaries when no PDFs are available.

---

## Project Architecture

### Data Flow

The full pipeline screens, extracts, verifies, loads, and publishes a knowledge wiki.
The shared `scorch/` package (`config.py`, `records.py`, `okf.py`) is the single source
of truth for models, the schema→DB mapping, and OKF helpers used across all stages.

```
┌─────────────┐
│   pdfs/     │  Input: Research articles                         (gitignored)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Screen   [Haiku 4.5]                │  Interactive: scorch-screener
│  • PRISMA-style include / exclude    │  Batch: batch_process_pdfs.py --screen
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Extract  [Sonnet 4.6]               │  Interactive: scorch-pdf-analyzer
│  • 46-field schema + schema validate │  Batch: batch_process_pdfs.py
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Verify   [Opus 4.8]                 │  Interactive: scorch-verifier
│  • independent audit vs. the PDF     │  Batch: batch_process_pdfs.py --verify
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────┐
│  reviews/   │  Intermediate: JSON files                         (gitignored)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Load     (validated)                │  Interactive: duckdb-schema-converter
│  • JSON → DuckDB via scorch/records  │  Batch: convert_to_duckdb.py
└──────┬───────────────────────────────┘
       │
       ├───────────────► ┌─────────────┐
       │                 │  duckdb/    │  Queryable DB + Parquet      (gitignored)
       │                 └──────┬──────┘
       │                        │
       │                        ▼
       │       ┌──────────────────────────────────────┐
       │       │  Query Layer                         │
       │       │  • duckdb-literature-analyst (agent) │  Natural language → SQL
       │       │  • query_literature.py / ask_papers  │  SQL gen / cited Q&A
       │       │  • Direct SQL (DuckDB CLI)           │  Programmatic access
       │       └──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  build_okf.py → okf/  [+ synthesize] │  Knowledge wiki              (committed)
│  • cross-linked markdown concept docs│  durable, version-controlled
└──────────────────────────────────────┘
```

### Component Comparison

| Component | Interactive (agent) | SDK Script | Purpose |
|-----------|---------------------|------------|---------|
| **Screening** | scorch-screener | `batch_process_pdfs.py --screen` | Include/exclude gate (Haiku) |
| **PDF Extraction** | scorch-pdf-analyzer | `batch_process_pdfs.py` | Parse PDFs → JSON (Sonnet) |
| **Verification** | scorch-verifier | `batch_process_pdfs.py --verify` | Audit extraction (Opus) |
| **DB Conversion** | duckdb-schema-converter | `convert_to_duckdb.py` | JSON → DuckDB (validated) |
| **Knowledge Wiki** | — | `build_okf.py` / `synthesize.py` | reviews → okf/ markdown |
| **Querying** | duckdb-literature-analyst | `query_literature.py` / `ask_papers.py` | NL → SQL / cited Q&A |

---

## Models & Cost

Extraction uses a **tiered cascade** of Claude models, configured in `scorch/config.py`.
Each stage can be overridden with an environment variable so the same code runs in dev,
CI, and batch jobs without edits.

| Stage | Default model | Override |
|-------|---------------|----------|
| Screen | `claude-haiku-4-5` | `SCORCH_SCREEN_MODEL` |
| Extract | `claude-sonnet-4-6` | `SCORCH_EXTRACT_MODEL` |
| Verify | `claude-opus-4-8` | `SCORCH_VERIFY_MODEL` |
| Synthesize | `claude-opus-4-8` | `SCORCH_SYNTHESIS_MODEL` |

Batch concurrency is set with `SCORCH_BATCH_CONCURRENCY` (default 4).

**Cost (approximate).** The extraction model (Sonnet 4.6) is roughly $3 / $15 per million
input / output tokens. Two mechanisms cut the per-paper cost substantially:

- **Prompt caching** — the large, stable schema prefix is cached and reused across PDFs
  (~90% cheaper on the cached portion).
- **Batch API** — eligible work runs at ~50% off.

Screening with Haiku filters out-of-scope papers before they reach the more expensive
extract/verify stages, so cost scales with the papers actually worth extracting.

---

## Knowledge Wiki (OKF)

The `okf/` directory is a **knowledge wiki** in the **Open Knowledge Format** — Google's
formalization of Andrej Karpathy's "LLM wiki" idea: a directory of cross-linked markdown
concept documents, each with YAML frontmatter and a markdown body, that is both
human- and agent-readable.

**Why it matters:** `pdfs/`, `reviews/`, and `duckdb/` are all gitignored because they
are large and fully regenerable. The committed `okf/` markdown is therefore the
**durable, version-controlled knowledge layer** — the artifact you share, review, and
diff over time.

**Structure:**

```
okf/
├── papers/            # one page per reviewed paper
├── health-outcomes/   # concept pages by health outcome
├── exposures/         # concept pages by climate exposure
├── resilience/        # concept pages by resilience measure
├── populations/       # concept pages by vulnerable population
├── regions/           # concept pages by region
├── datasets/scorch-reviews.md   # DB column reference (generated from scorch/records.py)
├── schema/extraction-schema.md  # human-readable schema reference
├── index.md           # entry point / table of contents
├── log.md             # build/change log
└── CONVENTIONS.md     # authoring rules for the wiki
```

**Rebuild it from the reviews:**

```bash
python scripts/build_okf.py                  # regenerate okf/ from reviews/
python scripts/build_okf.py --include-examples
```

Curated prose lives under a `## Curator notes` heading on each concept page and is
**preserved across rebuilds**; `synthesize.py` drafts that prose as cited evidence
syntheses. For authoring rules see [`okf/CONVENTIONS.md`](okf/CONVENTIONS.md), and for
the condensed agent workflow see [`AGENTS.md`](AGENTS.md).

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

The DuckDB schema (both DDL and INSERTs) is **generated from `scorch/records.py`**, so the
columns can never drift from the extraction schema. The legacy hand-maintained converter
declared 22 columns but inserted only 19 (and used wrong schema paths); this is fixed. The
full, authoritative column list lives in
[`okf/datasets/scorch-reviews.md`](okf/datasets/scorch-reviews.md), generated from the same
source.

### Main Table

#### `reviews` Table
One row per paper. Core metadata and assessments.

**Key Columns:**
- `source_pdf_filename` (PRIMARY KEY) - Original PDF filename
- `title`, `citation_apa7` - Bibliographic info
- `publication_year` - Stored as **VARCHAR** (the schema allows an integer or `"N/A"`);
  query with `TRY_CAST(publication_year AS INTEGER)`
- `spatial_scale` - Study geographic scale
- `geographic_areas` (VARCHAR[]) - Array of locations
- `study_design` - Research design type
- `relevance_rating` - High/Medium/Low
- `paper_summary` - Paper summary text
- `conclusions_summary` - Key conclusions
- `extraction_model`, `extraction_date` - Provenance recorded during extraction

### Child Tables

Each row carries a foreign key `source_pdf_filename` back to `reviews`.

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

### Category Tables (long format)

Three long-format tables store the boolean category checkboxes as one
`(source_pdf_filename, category)` row per selected category. This turns
"which papers study heat?" into a simple `JOIN`:

- `health_outcome_categories` - selected health-outcome categories
- `exposure_categories` - selected climate-exposure categories
- `resilience_categories` - selected resilience-measure categories

```sql
-- Which papers study heat?
SELECT r.title
FROM reviews r
JOIN exposure_categories e ON e.source_pdf_filename = r.source_pdf_filename
WHERE e.category = 'heat';
```

### Relationships

```
reviews (1) ──< (N) health_outcome_variables
        (1) ──< (N) climate_weather_variables
        (1) ──< (N) cofactor_variables
        (1) ──< (N) vulnerable_populations
        (1) ──< (N) correlations
        (1) ──< (N) health_outcome_categories
        (1) ──< (N) exposure_categories
        (1) ──< (N) resilience_categories
```

---

## Querying Your Data

### Method 1: Natural Language → SQL (Recommended)

```bash
python scripts/query_literature.py
```

Generates and runs SQL against the DuckDB database from plain-English questions.

**Example questions:**
- "Show me all papers published after 2020"
- "What are the most common health outcomes?"
- "Which papers focus on vulnerable populations?"
- "Give me papers about heat exposure with high relevance"
- "What climate variables are most frequently studied?"

### Method 2: Citation-Grounded Q&A (`ask_papers.py`)

```bash
python scripts/ask_papers.py "What adaptations reduce heat risk in arid cities?"
```

Answers from the **full text of the PDFs** with inline citations (Files API + citations
enabled), falling back to the extracted review summaries when no PDFs are present. Best
for evidence questions where you want sources, not aggregate counts. Flags: `--max-papers`,
`--dry-run`.

### Method 3: Direct SQL

```bash
# Open DuckDB CLI
duckdb duckdb/scorch_reviews.duckdb
```

**Example queries:**

```sql
-- Papers by publication year
-- publication_year is VARCHAR (may be "N/A"); cast for numeric ordering.
SELECT TRY_CAST(publication_year AS INTEGER) AS year, COUNT(*) AS count
FROM reviews
GROUP BY year
ORDER BY year DESC;

-- High relevance papers
SELECT title, relevance_rating, publication_year
FROM reviews
WHERE relevance_rating = 'High'
ORDER BY TRY_CAST(publication_year AS INTEGER) DESC;

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
ORDER BY TRY_CAST(r.publication_year AS INTEGER) DESC;

-- Which papers study heat? (long-format category table → simple JOIN)
SELECT r.title
FROM reviews r
JOIN exposure_categories e ON e.source_pdf_filename = r.source_pdf_filename
WHERE e.category = 'heat';

-- Climate variables by study design
SELECT r.study_design, cv.variable, COUNT(*) as count
FROM reviews r
JOIN climate_weather_variables cv ON r.source_pdf_filename = cv.source_pdf_filename
GROUP BY r.study_design, cv.variable
ORDER BY count DESC;
```

### Method 4: Python/Programmatic

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

### Method 5: Export to Other Formats

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

#### Memory / Rate-Limit Issues with Batch Processing

**Error:** System runs out of memory, or you hit API rate limits

**Solution:** lower the concurrency via the environment variable (no code edits):
```bash
SCORCH_BATCH_CONCURRENCY=2 python scripts/batch_process_pdfs.py   # reduce from default 4
SCORCH_BATCH_CONCURRENCY=1 python scripts/batch_process_pdfs.py   # one at a time
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

### Custom Batch Concurrency

Set the environment variable (no code edits needed):
```bash
SCORCH_BATCH_CONCURRENCY=8 python scripts/batch_process_pdfs.py   # more parallelism, more memory/RPM
```

### Custom Model Selection

Override any stage of the cascade per-run; see [Models & Cost](#models--cost):
```bash
SCORCH_EXTRACT_MODEL=claude-opus-4-8 python scripts/batch_process_pdfs.py
```

### Custom Schema Modifications

Edit `schema/scorch_extraction_schema.json` to add/modify questions. The shared
`scorch/` package and all scripts load the current schema automatically. If you add a
field that should land in the DB, add it to the field list in `scorch/records.py` (the
DDL and INSERTs are generated from there).

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
2. **New database columns**: Add the field to the field list in `scorch/records.py`
   (DDL and INSERTs are generated from it — do not hand-edit a column list)
3. **New analysis queries**: Add to `scripts/query_literature.py` examples
4. **New wiki content**: Curate under `## Curator notes`; see `okf/CONVENTIONS.md`

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
- **API costs**: roughly a few dimes to ~$1.50 per PDF (Sonnet 4.6, ~$3/$15 per 1M
  input/output tokens), **before** discounts. Prompt caching of the schema prefix
  (~90% cheaper on the cached portion) and the Batch API (~50% off) reduce this
  substantially; Haiku screening drops out-of-scope papers before they incur extract cost.
  See [Models & Cost](#models--cost).

### Optimization Tips

1. **Screen first**: `--screen` filters out-of-scope papers with cheap Haiku before extraction
2. **Batch processing**: Use SDK scripts for >5 PDFs
3. **Parallel execution**: Tune `SCORCH_BATCH_CONCURRENCY` for available RAM / rate limits
4. **Caching & Batch API**: Reuse the cached schema prefix; run eligible work via the Batch API
5. **Database queries**: Use indexes on frequently queried columns

---

## Citation

If you use this system in your research, please cite:

```bibtex
@software{scorch_lit_review,
  title={SCORCH Literature Review System},
  author={Southwest Center on Resilience for Climate Change and Health},
  year={2026},
  url={https://github.com/your-repo/scorch_lit_review}
}
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Support

For issues, questions, or contributions:
- **GitHub Issues**: [repository-url/issues]
- **Documentation**: See `scripts/README.md` for SDK details
- **Schema Reference**: See `schema/scorch_extraction_schema.json`

---

## Acknowledgments

Powered by:
- **Claude** (Anthropic) - Tiered extraction, verification, synthesis, and analysis
- **DuckDB** - High-performance analytical database
- **Open Knowledge Format (OKF)** - Cross-linked markdown knowledge wiki
- **Python** - Scripting and automation

Methodologically inspired by PRISMA (screening), STORM (cited synthesis), and PaperQA2
(citation-grounded Q&A) — re-implemented natively here, not vendored.

Developed for the **Southwest Center on Resilience for Climate Change and Health (SCORCH)** research initiative.

---

**Last Updated:** 2026-06-16
**Version:** 2.0
