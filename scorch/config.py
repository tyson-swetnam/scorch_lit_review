"""Project configuration: model IDs, filesystem paths, and tunables.

Every value can be overridden with an environment variable so the same code runs
in dev, CI, and batch jobs without edits. Model IDs are current as of the
2026 refresh (Opus 4.8 / Sonnet 4.6 / Haiku 4.5); change them in one place here.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Filesystem layout -------------------------------------------------------
# Repository root = parent of this package.
BASE_DIR = Path(os.environ.get("SCORCH_BASE_DIR", Path(__file__).resolve().parent.parent))

PDF_DIR = BASE_DIR / "pdfs"
REVIEW_DIR = BASE_DIR / "reviews"
DUCKDB_DIR = BASE_DIR / "duckdb"
SCHEMA_DIR = BASE_DIR / "schema"
OKF_DIR = BASE_DIR / "okf"

SCHEMA_PATH = SCHEMA_DIR / "scorch_extraction_schema.json"
DB_PATH = DUCKDB_DIR / "scorch_reviews.duckdb"
PARQUET_PATH = DUCKDB_DIR / "scorch_reviews.parquet"

SCHEMA_VERSION = "1.1"

# --- Models (tiered cascade) -------------------------------------------------
# Screen cheaply, extract at the cost/quality sweet spot, verify with the
# strongest model. Override per-stage with SCORCH_*_MODEL.
SCREEN_MODEL = os.environ.get("SCORCH_SCREEN_MODEL", "claude-haiku-4-5")
EXTRACT_MODEL = os.environ.get("SCORCH_EXTRACT_MODEL", "claude-sonnet-4-6")
VERIFY_MODEL = os.environ.get("SCORCH_VERIFY_MODEL", "claude-opus-4-8")
SYNTHESIS_MODEL = os.environ.get("SCORCH_SYNTHESIS_MODEL", "claude-opus-4-8")

# Max output tokens for a full 46-field extraction. Generous; extractions that
# approach this should stream (the batch runner does).
EXTRACT_MAX_TOKENS = int(os.environ.get("SCORCH_EXTRACT_MAX_TOKENS", "16000"))

# Parallelism for the local async batch runner (the Batch API path ignores this).
BATCH_CONCURRENCY = int(os.environ.get("SCORCH_BATCH_CONCURRENCY", "4"))

# --- Approximate pricing ($ per 1M tokens) for cost estimation only ----------
# Informational; not used for billing. Update alongside the model IDs above.
PRICING = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Rough USD estimate for a single call (cache/batch discounts not applied)."""
    rates = PRICING.get(model)
    if not rates:
        return 0.0
    return input_tokens / 1_000_000 * rates["input"] + output_tokens / 1_000_000 * rates["output"]
