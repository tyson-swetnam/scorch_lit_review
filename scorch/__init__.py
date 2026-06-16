"""SCORCH Literature Review — shared library.

This package is the single source of truth for the project's conventions so the
extraction pipeline, the DuckDB converter, and the OKF wiki builder all agree:

- ``config``      — model IDs, paths, tunables (override via environment).
- ``records``     — canonical mapping from the extraction schema to flat rows.
- ``okf``         — helpers for reading/writing Open Knowledge Format documents.

Keeping the schema→record mapping in one place is deliberate: the legacy
converter drifted out of sync with ``schema/scorch_extraction_schema.json`` and
silently failed on every insert. Everything downstream now imports ``records``.
"""

__all__ = ["config", "records", "okf"]
__version__ = "2.0.0"
