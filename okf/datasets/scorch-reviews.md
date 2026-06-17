---
type: Dataset
title: scorch_reviews (DuckDB)
description: Queryable database of extracted SCORCH literature reviews; one row per paper plus normalized child tables.
resource: duckdb/scorch_reviews.duckdb
tags: [duckdb, parquet, dataset]
timestamp: 2026-06-17
---

# scorch_reviews

Built by `scripts/convert_to_duckdb.py` from `reviews/*.json`. Schema is
generated from `scorch/records.py` (the single source of truth), so this page,
the table DDL, and the inserts cannot drift. Parquet export:
`duckdb/scorch_reviews.parquet`.

## `reviews` (one row per paper)

Primary key: `source_pdf_filename`. Key columns:

| Column | Type | Notes |
|--------|------|-------|
| `source_pdf_filename` | VARCHAR | PK; original PDF filename |
| `title`, `citation_apa7` | VARCHAR | Bibliographic |
| `publication_year` | VARCHAR | Stored raw; query `TRY_CAST(publication_year AS INTEGER)` |
| `spatial_scale`, `setting`, `study_design` | VARCHAR | Enumerated in the schema |
| `arid_semiarid_classification` | VARCHAR | Yes / No / Mixed / Unclear |
| `focuses_on_arid_semiarid_sw_us_mexico` | BOOLEAN | Screening Q1 |
| `includes_primary_data_for_region` | BOOLEAN | Screening Q2 |
| `analyzes_interventions`, `includes_projection_modeling` | BOOLEAN | Filters |
| `relevance_rating` | VARCHAR | High / Medium / Low |
| `geographic_areas` | VARCHAR[] | Array |
| `paper_summary`, `conclusions_summary`, `limitations`, `data_gaps`, `future_research` | VARCHAR | Synthesis text |
| `extraction_model`, `extractor_agent`, `extraction_date`, `schema_version` | VARCHAR | Provenance |

## Child tables (FK `source_pdf_filename`)

| Table | Columns | Source schema path |
|-------|---------|--------------------|
| [health_outcome_variables](../health-outcomes/) | variable, spatial_resolution, data_source | `data_tables.health_outcome_variables` |
| climate_weather_variables | variable, spatial_resolution, data_source | `data_tables.climate_weather_variables` |
| cofactor_variables | variable, spatial_resolution, data_source | `data_tables.cofactor_variables` |
| [vulnerable_populations](../populations/) | population_group, vulnerability_reasons | `vulnerable_populations[]` |
| correlations | variable, effect_size_correlation, significance, confidence_interval | `associations_effects.correlations_table` |
| field_evidence | field_path, claim, page_start, page_end, quote, char_start, char_end, line_hint | `extraction_metadata.evidence_log[]` (schema v1.2 per-claim provenance; page/char columns are INTEGER) |

## Long-format category tables

`health_outcome_categories`, `exposure_categories`, `resilience_categories` —
each `(source_pdf_filename, category)`, one row per *true* category. Makes
membership a simple JOIN.

## Example queries

```sql
-- Papers per year
SELECT TRY_CAST(publication_year AS INTEGER) AS yr, COUNT(*)
FROM reviews GROUP BY yr ORDER BY yr DESC;

-- High-relevance heat papers
SELECT r.title
FROM reviews r
JOIN exposure_categories e ON e.source_pdf_filename = r.source_pdf_filename
WHERE e.category = 'heat' AND r.relevance_rating = 'High';

-- Most-studied vulnerable populations
SELECT population_group, COUNT(*) AS n
FROM vulnerable_populations GROUP BY population_group ORDER BY n DESC;

-- Source provenance for a paper (page + verbatim quote per claim)
SELECT field_path, page_start, quote
FROM field_evidence
WHERE source_pdf_filename = 'BAMS-D-24-0216.1.pdf'
ORDER BY page_start, field_path;

-- Provenance coverage: how many distinct fields each paper cites
SELECT r.source_pdf_filename, COUNT(DISTINCT fe.field_path) AS cited_fields
FROM reviews r LEFT JOIN field_evidence fe USING (source_pdf_filename)
GROUP BY 1 ORDER BY 1;
```
