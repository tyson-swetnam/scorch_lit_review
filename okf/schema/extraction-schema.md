---
type: Schema
title: SCORCH Extraction Schema (46 questions)
description: The contract every review JSON must satisfy; maps Q1-Q46 to schema sections.
resource: schema/scorch_extraction_schema.json
tags: [schema, extraction, contract]
schema_version: "1.1"
timestamp: 2026-06-16
---

# Extraction schema

The authoritative contract is `schema/scorch_extraction_schema.json` (JSON
Schema draft-07). Every review in `reviews/*.json` is validated against it
before entering the database. This page is the human-readable map.

## Core policy

- **N/A policy:** use the string `"N/A"` when information is absent — never
  fabricate. Empty arrays `[]` for absent lists; `null` for absent numbers.
- **Booleans** for checkbox questions; **enums** are closed sets (validation
  rejects out-of-vocabulary values).

## Sections (Q1-Q46)

| Schema section | Questions | Captures |
|----------------|-----------|----------|
| `screening` | Q1-Q2 | Arid-SW focus; primary regional data (the inclusion gate) |
| `metadata` | Q3-Q4 | Title, APA-7 citation |
| `spatial_temporal` | Q5-Q9 | Spatial scale, geographic areas, year, data date range |
| `study_characteristics` | Q10-Q12 | Setting, aridity classification, study design |
| `data_tables` | Q13-Q15 | Health-outcome / co-factor / climate variable tables |
| `methods` | Q16 | Analytical methods |
| `health_outcomes` | Q17-Q18 | Specific outcomes + 32 outcome-category booleans |
| `exposures` | Q19-Q20 | Direct exposures + 13 exposure-category booleans |
| `demographics` | Q21-Q22 | Sample size, sex, race/ethnicity |
| `interventions` | Q23 | Interventions/adaptations evaluated |
| `objectives_met` | Q24 | SCORCH objectives 1-6: Met / Partially Met / Not Met |
| `research_questions` | Q25-Q28 | Alignment to the 3 core research questions |
| `unquantified_health_impacts` | Q29 | Mentioned-but-not-quantified impacts |
| `associations_effects` | Q30-Q31 | Effect sizes + correlations table |
| `climate_projections` | Q32-Q35 | Models, scenarios (RCP/SSP), horizons |
| `vulnerable_populations` | Q36 | At-risk groups + reasons |
| `climate_resilience` | Q37-Q39 | Resilience-category booleans, strategies, adaptations |
| `relevance_summary` | Q40 | Why relevant to the arid SW |
| `limitations_gaps` | Q41-Q43 | Limitations, data gaps, future research |
| `overall_relevance` | Q44 | Rating (High/Medium/Low) + justification |
| `summary` | Q45-Q46 | Paper summary, conclusions |
| `extraction_metadata` | — | Provenance: date, agent, model, source PDF, schema version |

## How sections map downstream

- The boolean category maps (`health_outcomes.health_outcome_categories`,
  `exposures.exposure_categories`, `climate_resilience.resilience_categories`)
  become the [health outcome](../health-outcomes/), [exposure](../exposures/),
  and [resilience](../resilience/) concept pages, and long-format DuckDB tables.
- `vulnerable_populations[]` → [population](../populations/) concepts;
  `spatial_temporal.geographic_areas` → [region](../regions/) concepts.
- See [scorch_reviews dataset](../datasets/scorch-reviews.md) for the table layout.
