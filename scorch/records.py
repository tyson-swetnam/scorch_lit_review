"""Canonical mapping from the SCORCH extraction schema to flat records.

This is the single source of truth that the DuckDB converter and the OKF builder
both import. Table DDL **and** INSERT statements are generated from the same
field lists, so the column/value count can never drift (the legacy converter
declared 22 columns but inserted 19, failing on every row).

Every dotted path below was verified against
``schema/scorch_extraction_schema.json`` (schema version 1.1).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


# --- Generic helpers ---------------------------------------------------------
def get_path(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely walk a nested dict by keys, returning ``default`` if any link is missing."""
    cur: Any = data
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key, default)
        else:
            return default
    return cur if cur is not None else default


# --- Main "reviews" table ----------------------------------------------------
# (column_name, (schema path...), duckdb_type). Order defines DDL and INSERT.
MAIN_FIELDS: list[tuple[str, tuple[str, ...], str]] = [
    ("source_pdf_filename", ("extraction_metadata", "source_pdf_filename"), "VARCHAR"),
    ("extraction_date", ("extraction_metadata", "extraction_date"), "VARCHAR"),
    ("extractor_agent", ("extraction_metadata", "extractor_agent"), "VARCHAR"),
    ("extraction_model", ("extraction_metadata", "extraction_model"), "VARCHAR"),
    ("schema_version", ("extraction_metadata", "schema_version"), "VARCHAR"),
    # Screening (Q1-2)
    ("focuses_on_arid_semiarid_sw_us_mexico", ("screening", "focuses_on_arid_semiarid_sw_us_mexico"), "BOOLEAN"),
    ("includes_primary_data_for_region", ("screening", "includes_primary_data_for_region"), "BOOLEAN"),
    # Metadata (Q3-4)
    ("title", ("metadata", "title"), "VARCHAR"),
    ("citation_apa7", ("metadata", "citation_apa7"), "VARCHAR"),
    # Spatial / temporal (Q5-9). publication_year kept as VARCHAR: schema allows
    # an int or the string "N/A"; query with TRY_CAST(publication_year AS INTEGER).
    ("spatial_scale", ("spatial_temporal", "spatial_scale"), "VARCHAR"),
    ("publication_year", ("spatial_temporal", "publication_year"), "VARCHAR"),
    ("data_date_earliest", ("spatial_temporal", "data_date_earliest"), "VARCHAR"),
    ("data_date_latest", ("spatial_temporal", "data_date_latest"), "VARCHAR"),
    # Study characteristics (Q10-12)
    ("setting", ("study_characteristics", "setting"), "VARCHAR"),
    ("arid_semiarid_classification", ("study_characteristics", "arid_semiarid_classification"), "VARCHAR"),
    ("study_design", ("study_characteristics", "study_design"), "VARCHAR"),
    # Flags useful for filtering
    ("analyzes_interventions", ("interventions", "analyzes_interventions"), "BOOLEAN"),
    ("includes_projection_modeling", ("climate_projections", "includes_projection_modeling"), "BOOLEAN"),
    # Overall assessment (Q40-46)
    ("relevance_rating", ("overall_relevance", "relevance_rating"), "VARCHAR"),
    ("relevance_justification", ("overall_relevance", "relevance_justification"), "VARCHAR"),
    ("relevance_summary", ("relevance_summary",), "VARCHAR"),
    ("paper_summary", ("summary", "paper_summary"), "VARCHAR"),
    ("conclusions_summary", ("summary", "conclusions_summary"), "VARCHAR"),
    ("limitations", ("limitations_gaps", "limitations"), "VARCHAR"),
    ("data_gaps", ("limitations_gaps", "data_gaps"), "VARCHAR"),
    ("future_research", ("limitations_gaps", "future_research"), "VARCHAR"),
]

# geographic_areas is an array column, handled separately so it stays VARCHAR[].
GEOGRAPHIC_AREAS_PATH = ("spatial_temporal", "geographic_areas")


# --- Normalized child tables (one row per array item) ------------------------
# table_name -> {path, columns}. Each row is prefixed with source_pdf_filename.
CHILD_TABLES: dict[str, dict[str, Any]] = {
    "health_outcome_variables": {
        "path": ("data_tables", "health_outcome_variables"),
        "columns": ["variable", "spatial_resolution", "data_source"],
    },
    "cofactor_variables": {
        "path": ("data_tables", "cofactor_variables"),
        "columns": ["variable", "spatial_resolution", "data_source"],
    },
    "climate_weather_variables": {
        "path": ("data_tables", "climate_weather_variables"),
        "columns": ["variable", "spatial_resolution", "data_source"],
    },
    "vulnerable_populations": {
        "path": ("vulnerable_populations",),  # top-level array in the schema
        "columns": ["population_group", "vulnerability_reasons"],
    },
    "correlations": {
        "path": ("associations_effects", "correlations_table"),
        "columns": ["variable", "effect_size_correlation", "significance", "confidence_interval"],
    },
}

# Boolean "category" maps -> long-format (source_pdf_filename, category) rows for
# only the categories set to true. Makes "which papers study heat?" a simple JOIN.
CATEGORY_TABLES: dict[str, tuple[str, ...]] = {
    "health_outcome_categories": ("health_outcomes", "health_outcome_categories"),
    "exposure_categories": ("exposures", "exposure_categories"),
    "resilience_categories": ("climate_resilience", "resilience_categories"),
}


def flatten_main(data: dict) -> dict[str, Any]:
    """Return the single ``reviews`` row for one review JSON document."""
    row = {col: get_path(data, *path) for col, path, _ in MAIN_FIELDS}
    areas = get_path(data, *GEOGRAPHIC_AREAS_PATH, default=[])
    row["geographic_areas"] = areas if isinstance(areas, list) else []
    return row


def child_rows(data: dict, filename: str) -> dict[str, list[list[Any]]]:
    """Return {table_name: [positional row, ...]} for all child + category tables."""
    out: dict[str, list[list[Any]]] = {}

    for table, spec in CHILD_TABLES.items():
        items = get_path(data, *spec["path"], default=[]) or []
        rows = []
        for item in items:
            if isinstance(item, dict):
                rows.append([filename] + [item.get(c) for c in spec["columns"]])
        out[table] = rows

    for table, path in CATEGORY_TABLES.items():
        mapping = get_path(data, *path, default={}) or {}
        out[table] = [[filename, cat] for cat, val in mapping.items() if val is True]

    return out


def main_columns() -> list[str]:
    """Ordered column names for the ``reviews`` table (incl. geographic_areas)."""
    return [col for col, _, _ in MAIN_FIELDS] + ["geographic_areas"]


def main_ddl() -> str:
    """CREATE TABLE statement for ``reviews``, generated from MAIN_FIELDS."""
    lines = []
    for col, _, dtype in MAIN_FIELDS:
        pk = " PRIMARY KEY" if col == "source_pdf_filename" else ""
        lines.append(f"    {col} {dtype}{pk}")
    lines.append("    geographic_areas VARCHAR[]")
    return "CREATE TABLE IF NOT EXISTS reviews (\n" + ",\n".join(lines) + "\n)"


def child_ddl() -> list[str]:
    """CREATE TABLE statements for every child + category table."""
    stmts = []
    for table, spec in CHILD_TABLES.items():
        cols = ",\n".join(f"    {c} VARCHAR" for c in spec["columns"])
        stmts.append(
            f"CREATE TABLE IF NOT EXISTS {table} (\n"
            f"    source_pdf_filename VARCHAR,\n{cols}\n)"
        )
    for table in CATEGORY_TABLES:
        stmts.append(
            f"CREATE TABLE IF NOT EXISTS {table} (\n"
            f"    source_pdf_filename VARCHAR,\n    category VARCHAR\n)"
        )
    return stmts


# --- Validation --------------------------------------------------------------
def load_schema(schema_path: str | Path) -> dict:
    with open(schema_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_review(data: dict, schema: dict) -> list[str]:
    """Return a list of human-readable schema violations ([] if valid).

    No-op (returns []) if ``jsonschema`` isn't installed, so the converter still
    runs in minimal environments — it just won't enforce the contract.
    """
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - optional dependency
        return []
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for err in validator.iter_errors(data):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors


def iter_review_files(review_dir: str | Path) -> Iterable[Path]:
    """Yield ``*_review.json`` files in a directory, sorted for determinism."""
    return sorted(Path(review_dir).glob("*_review.json"))
