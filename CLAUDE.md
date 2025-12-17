# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **SCORCH Literature Review** repository for the Southwest Center on Resilience for Climate Change and Health. The project uses AI agents to extract structured data from climate-health research PDFs focused on arid/semi-arid regions of the US Southwest and northern Mexico.

## Repository Structure

```
pdfs/           # Input PDF research articles to be analyzed
reviews/        # Output JSON files containing extracted data
duckdb/         # DuckDB database and Parquet exports
schema/         # SCORCH extraction schema definition
scripts/        # Standalone SDK scripts for batch processing
.claude/agents/ # Custom Claude Code agent definitions
```

## Automated Pipeline

There are two ways to run the pipeline:

### Option 1: Interactive (Claude Code Agents)
```
pdfs/ → scorch-pdf-analyzer → reviews/ → duckdb-schema-converter → duckdb/
```

1. Place PDF research articles in `pdfs/`
2. Run `scorch-pdf-analyzer` to extract data → creates `reviews/*_review.json`
3. Run `duckdb-schema-converter` to update database → updates `duckdb/scorch_reviews.duckdb`
4. Query with `duckdb-literature-analyst` for analysis

### Option 2: Batch Processing (SDK Scripts)
```
pdfs/ → batch_process_pdfs.py → reviews/ → convert_to_duckdb.py → duckdb/
```

1. Set `ANTHROPIC_API_KEY` environment variable
2. Run `python scripts/batch_process_pdfs.py` for parallel PDF processing
3. Run `python scripts/convert_to_duckdb.py` to update database
4. Run `python scripts/query_literature.py` for interactive SQL queries

The pipeline supports incremental updates - new PDFs are processed and added to the existing database without rebuilding.

## Processing Tools

### Interactive Claude Code Agents (`.claude/agents/`)

#### scorch-pdf-analyzer
Analyzes PDF documents and extracts information according to the SCORCH extraction schema. Produces JSON review files with 46 structured questions covering:
- Screening criteria (regional focus, primary data)
- Metadata (title, citation, spatial/temporal info)
- Study characteristics (setting, design, aridity classification)
- Data tables (health outcomes, co-factors, climate variables)
- Health outcomes and exposures
- Demographics and interventions
- Research question alignment
- Climate projections
- Vulnerable populations
- Climate resilience measures

#### duckdb-schema-converter
Converts JSON review files from `reviews/` into a DuckDB database. Use for:
- Converting completed JSON extractions to queryable database format
- Incremental updates (only processes new reviews)
- Parquet export for interoperability

#### duckdb-literature-analyst
Queries and analyzes data in `duckdb/scorch_reviews.duckdb`. Use for:
- Exploring database schema (`SHOW TABLES`, `DESCRIBE`)
- Writing SQL queries against extraction data
- Generating aggregate reports across papers
- Query optimization

### Standalone SDK Scripts (`scripts/`)

#### batch_process_pdfs.py
Direct API batch processing script for parallel PDF extraction.
- Processes 4 PDFs concurrently (configurable)
- Independent 1M context per PDF
- Requires `ANTHROPIC_API_KEY` environment variable
- Usage: `python scripts/batch_process_pdfs.py`

#### convert_to_duckdb.py
Converts JSON reviews to DuckDB database.
- Incremental updates (skips existing reviews)
- Exports to Parquet format
- No API key required
- Usage: `python scripts/convert_to_duckdb.py`

#### query_literature.py
Interactive natural language database queries powered by Claude.
- Ask questions in plain English
- Automatic SQL generation and execution
- Requires `ANTHROPIC_API_KEY` environment variable
- Usage: `python scripts/query_literature.py` (interactive) or `python scripts/query_literature.py "your question"` (single query)

**Output files:**
- `duckdb/scorch_reviews.duckdb` - Main database
- `duckdb/scorch_reviews.parquet` - Parquet export

## Schema Details

The extraction schema (`schema/scorch_extraction_schema.json`) defines strict data types and validation rules:

- **N/A Policy**: Use `"N/A"` when information is not present - never fabricate data
- **Boolean fields**: Use `true`/`false` for checkbox-style questions
- **Arrays**: Use `[]` for empty lists, max items specified per field (typically 6-10)
- **Enums**: Many fields have predefined options (spatial_scale, study_design, relevance_rating, etc.)

Key schema sections map to questions Q1-Q46 in the extraction prompts.

## Output File Naming

For a PDF named `Smith_2023_HeatMortality.pdf`, create:
`reviews/Smith_2023_HeatMortality_review.json`

## Extraction Metadata

All review files should include:
```json
{
  "extraction_metadata": {
    "extraction_date": "YYYY-MM-DD",
    "extractor_agent": "scorch-pdf-analyzer",
    "source_pdf_filename": "original_filename.pdf",
    "schema_version": "1.1"
  }
}
```

## SCORCH Research Focus

The project addresses three core research questions:
1. How do extreme weather events impact human health in arid SW US/Mexico regions?
2. How will climate-related disease landscape change over 5-100 year horizons?
3. What successful climate resilience solutions apply to these regions?

Six objectives guide relevance assessment:
1. Climate-health impacts in arid/semi-arid SW US and northern Mexico
2. Extreme weather and temperature/precipitation fluctuation health effects
3. Climate-health forecasts for next 50-100 years
4. Vulnerable community identification
5. Research gap identification
6. Solutions and adaptations for climate resilience
