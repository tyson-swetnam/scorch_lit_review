#!/usr/bin/env python3
"""Convert JSON review files into the SCORCH DuckDB database.

Incremental and idempotent: only reviews whose ``source_pdf_filename`` is not
already present are added. Exports a Parquet copy of the main table for
interoperability. No API key required.

Table DDL and inserts are both generated from ``scorch.records`` so they can
never drift from ``schema/scorch_extraction_schema.json`` (or each other).
Every review is validated against the schema before insert; invalid reviews are
reported and skipped rather than silently corrupting the database.

Usage:
    python scripts/convert_to_duckdb.py            # add new reviews
    python scripts/convert_to_duckdb.py --rebuild  # drop & rebuild from scratch
    python scripts/convert_to_duckdb.py --strict   # abort on any validation error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

# Allow running as a standalone script (python scripts/convert_to_duckdb.py).
# Append (don't insert) so the repo root never shadows site-packages — the
# top-level duckdb/ data directory would otherwise mask the duckdb library.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scorch import config, records  # noqa: E402


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(records.main_ddl())
    for stmt in records.child_ddl():
        con.execute(stmt)


def existing_filenames(con: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        return {r[0] for r in con.execute("SELECT source_pdf_filename FROM reviews").fetchall()}
    except duckdb.Error:
        return set()


def insert_review(con: duckdb.DuckDBPyConnection, data: dict) -> None:
    """Insert one review (main row + all child rows) inside the caller's transaction."""
    main = records.flatten_main(data)
    columns = records.main_columns()
    placeholders = ", ".join("?" for _ in columns)
    con.execute(
        f"INSERT INTO reviews ({', '.join(columns)}) VALUES ({placeholders})",
        [main[c] for c in columns],
    )

    filename = main["source_pdf_filename"]
    for table, rows in records.child_rows(data, filename).items():
        if not rows:
            continue
        ph = ", ".join("?" for _ in rows[0])
        con.executemany(f"INSERT INTO {table} VALUES ({ph})", rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert SCORCH reviews to DuckDB.")
    parser.add_argument("--rebuild", action="store_true", help="Drop and rebuild all tables.")
    parser.add_argument("--strict", action="store_true", help="Abort on the first validation error.")
    args = parser.parse_args()

    print("=" * 60)
    print("SCORCH DuckDB Converter")
    print("=" * 60)

    if not config.REVIEW_DIR.exists():
        print(f"✗ Reviews directory not found: {config.REVIEW_DIR}")
        return 1

    config.DUCKDB_DIR.mkdir(exist_ok=True)
    schema = records.load_schema(config.SCHEMA_PATH)

    con = duckdb.connect(str(config.DB_PATH))
    print(f"✓ Connected to: {config.DB_PATH}")

    if args.rebuild:
        for table in ["reviews", *records.CHILD_TABLES, *records.CATEGORY_TABLES]:
            con.execute(f"DROP TABLE IF EXISTS {table}")
        print("✓ Dropped existing tables (--rebuild)")

    create_schema(con)
    print("✓ Schema created/verified")

    existing = existing_filenames(con)
    review_files = list(records.iter_review_files(config.REVIEW_DIR))

    added = skipped = invalid = errors = 0
    print(f"\n\U0001f4ca {len(review_files)} review file(s) found; {len(existing)} already in DB\n")

    for path in review_files:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ✗ Unreadable {path.name}: {exc}")
            errors += 1
            continue

        filename = records.get_path(data, "extraction_metadata", "source_pdf_filename")
        if not filename:
            print(f"  ✗ {path.name}: missing extraction_metadata.source_pdf_filename")
            errors += 1
            continue
        if filename in existing:
            skipped += 1
            continue

        violations = records.validate_review(data, schema)
        if violations:
            print(f"  ⚠ Invalid {path.name} ({len(violations)} issue(s)): {violations[0]}")
            invalid += 1
            if args.strict:
                con.close()
                return 2
            continue

        try:
            con.execute("BEGIN")
            insert_review(con, data)
            con.execute("COMMIT")
            existing.add(filename)
            added += 1
            print(f"  ✓ Added: {path.name}")
        except duckdb.Error as exc:
            con.execute("ROLLBACK")
            print(f"  ✗ Insert failed for {path.name}: {exc}")
            errors += 1

    if added:
        con.execute(f"COPY reviews TO '{config.PARQUET_PATH}' (FORMAT PARQUET)")
        print(f"\n✓ Exported Parquet: {config.PARQUET_PATH}")

    total = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    con.close()

    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"  ✓ Added:   {added}")
    print(f"  → Skipped: {skipped} (already present)")
    if invalid:
        print(f"  ⚠ Invalid: {invalid} (schema violations)")
    if errors:
        print(f"  ✗ Errors:  {errors}")
    print(f"  \U0001f4ca Total in DB: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
