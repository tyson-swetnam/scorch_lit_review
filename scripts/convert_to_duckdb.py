#!/usr/bin/env python3
"""
Convert JSON review files to DuckDB database.

Incrementally adds new reviews to the database without duplicating
existing entries. Exports to Parquet format for interoperability.
"""
import json
import duckdb
from pathlib import Path
from datetime import datetime


class DuckDBConverter:
    """Converts JSON reviews to DuckDB database with incremental updates"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.reviews_dir = base_dir / "reviews"
        self.duckdb_dir = base_dir / "duckdb"
        self.db_path = self.duckdb_dir / "scorch_reviews.duckdb"
        self.parquet_path = self.duckdb_dir / "scorch_reviews.parquet"

        # Ensure duckdb directory exists
        self.duckdb_dir.mkdir(exist_ok=True)

    def create_schema(self, con):
        """Create database schema if it doesn't exist"""

        con.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                -- Primary key from extraction_metadata
                source_pdf_filename VARCHAR PRIMARY KEY,
                extraction_date DATE,
                extractor_agent VARCHAR,
                schema_version VARCHAR,

                -- Screening (Q1-2)
                focuses_on_arid_semiarid_sw_us_mexico BOOLEAN,
                includes_primary_data_for_region BOOLEAN,

                -- Metadata (Q3-4)
                title VARCHAR,
                citation_apa7 VARCHAR,

                -- Spatial/Temporal (Q5-9)
                spatial_scale VARCHAR,
                geographic_areas VARCHAR[],
                publication_year INTEGER,
                data_date_earliest VARCHAR,
                data_date_latest VARCHAR,

                -- Study characteristics (Q10-12)
                setting VARCHAR,
                arid_semiarid_classification VARCHAR,
                study_design VARCHAR,

                -- Overall assessment (Q40-46)
                relevance_rating VARCHAR,
                relevance_justification VARCHAR,
                paper_summary VARCHAR,
                conclusions_summary VARCHAR,

                -- Additional fields from schema
                research_limitations VARCHAR,
                identified_gaps VARCHAR
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS health_outcome_variables (
                source_pdf_filename VARCHAR,
                variable VARCHAR,
                spatial_resolution VARCHAR,
                data_source VARCHAR,
                FOREIGN KEY (source_pdf_filename) REFERENCES reviews(source_pdf_filename)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS climate_weather_variables (
                source_pdf_filename VARCHAR,
                variable VARCHAR,
                spatial_resolution VARCHAR,
                data_source VARCHAR,
                FOREIGN KEY (source_pdf_filename) REFERENCES reviews(source_pdf_filename)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS cofactor_variables (
                source_pdf_filename VARCHAR,
                variable VARCHAR,
                spatial_resolution VARCHAR,
                data_source VARCHAR,
                FOREIGN KEY (source_pdf_filename) REFERENCES reviews(source_pdf_filename)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS vulnerable_populations (
                source_pdf_filename VARCHAR,
                population_group VARCHAR,
                vulnerability_reasons VARCHAR,
                FOREIGN KEY (source_pdf_filename) REFERENCES reviews(source_pdf_filename)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                source_pdf_filename VARCHAR,
                variable VARCHAR,
                effect_size_correlation VARCHAR,
                significance VARCHAR,
                confidence_interval VARCHAR,
                FOREIGN KEY (source_pdf_filename) REFERENCES reviews(source_pdf_filename)
            )
        """)

        print("✓ Database schema created/verified")

    def get_existing_files(self, con) -> set:
        """Get set of already processed PDF filenames"""
        try:
            result = con.execute("SELECT source_pdf_filename FROM reviews").fetchall()
            return {r[0] for r in result}
        except:
            return set()

    def find_new_reviews(self, existing: set) -> list:
        """Find JSON files not yet in database"""
        new_files = []

        for json_file in self.reviews_dir.glob("*_review.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    metadata = data.get('extraction_metadata', {})
                    filename = metadata.get('source_pdf_filename')

                    if filename and filename not in existing:
                        new_files.append((json_file, data))
            except Exception as e:
                print(f"  ✗ Error reading {json_file.name}: {e}")

        return new_files

    def safe_get(self, data: dict, *keys, default=None):
        """Safely navigate nested dictionary"""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                return default
        return current if current is not None else default

    def insert_review(self, con, data: dict, filename: str):
        """Insert a single review into the database"""

        metadata = data.get('extraction_metadata', {})

        # Extract main review data
        con.execute("""
            INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            filename,
            self.safe_get(metadata, 'extraction_date'),
            self.safe_get(metadata, 'extractor_agent'),
            self.safe_get(metadata, 'schema_version'),
            self.safe_get(data, 'screening', 'focuses_on_arid_semiarid_sw_us_mexico'),
            self.safe_get(data, 'screening', 'includes_primary_data_for_region'),
            self.safe_get(data, 'metadata', 'title'),
            self.safe_get(data, 'metadata', 'citation_apa7'),
            self.safe_get(data, 'metadata', 'spatial_scale'),
            self.safe_get(data, 'metadata', 'geographic_areas', default=[]),
            self.safe_get(data, 'metadata', 'publication_year'),
            self.safe_get(data, 'metadata', 'data_date_earliest'),
            self.safe_get(data, 'metadata', 'data_date_latest'),
            self.safe_get(data, 'study_characteristics', 'setting'),
            self.safe_get(data, 'study_characteristics', 'arid_semiarid_classification'),
            self.safe_get(data, 'study_characteristics', 'study_design'),
            self.safe_get(data, 'overall_assessment', 'relevance_rating'),
            self.safe_get(data, 'overall_assessment', 'relevance_justification'),
            self.safe_get(data, 'overall_assessment', 'paper_summary'),
        ])

        # Insert health outcome variables
        health_outcomes = self.safe_get(data, 'data_tables', 'health_outcome_variables', default=[])
        for item in health_outcomes:
            if isinstance(item, dict):
                con.execute("""
                    INSERT INTO health_outcome_variables VALUES (?, ?, ?, ?)
                """, [
                    filename,
                    item.get('variable'),
                    item.get('spatial_resolution'),
                    item.get('data_source')
                ])

        # Insert climate/weather variables
        climate_vars = self.safe_get(data, 'data_tables', 'climate_weather_variables', default=[])
        for item in climate_vars:
            if isinstance(item, dict):
                con.execute("""
                    INSERT INTO climate_weather_variables VALUES (?, ?, ?, ?)
                """, [
                    filename,
                    item.get('variable'),
                    item.get('spatial_resolution'),
                    item.get('data_source')
                ])

        # Insert cofactor variables
        cofactors = self.safe_get(data, 'data_tables', 'cofactor_variables', default=[])
        for item in cofactors:
            if isinstance(item, dict):
                con.execute("""
                    INSERT INTO cofactor_variables VALUES (?, ?, ?, ?)
                """, [
                    filename,
                    item.get('variable'),
                    item.get('spatial_resolution'),
                    item.get('data_source')
                ])

        # Insert vulnerable populations
        populations = self.safe_get(data, 'vulnerable_populations', 'populations_identified', default=[])
        for item in populations:
            if isinstance(item, dict):
                con.execute("""
                    INSERT INTO vulnerable_populations VALUES (?, ?, ?)
                """, [
                    filename,
                    item.get('population_group'),
                    item.get('vulnerability_reasons')
                ])

        # Insert correlations
        correlations = self.safe_get(data, 'statistical_findings', 'correlations_reported', default=[])
        for item in correlations:
            if isinstance(item, dict):
                con.execute("""
                    INSERT INTO correlations VALUES (?, ?, ?, ?, ?)
                """, [
                    filename,
                    item.get('variable'),
                    item.get('effect_size_correlation'),
                    item.get('significance'),
                    item.get('confidence_interval')
                ])

    def export_parquet(self, con):
        """Export database to Parquet format"""
        try:
            con.execute(f"""
                COPY reviews TO '{self.parquet_path}' (FORMAT PARQUET)
            """)
            print(f"✓ Exported to Parquet: {self.parquet_path}")
        except Exception as e:
            print(f"  ⚠ Parquet export warning: {e}")

    def run(self):
        """Main conversion workflow"""
        print("="*60)
        print("SCORCH DuckDB Converter")
        print("="*60)

        if not self.reviews_dir.exists():
            print(f"✗ Reviews directory not found: {self.reviews_dir}")
            return

        # Connect to database
        con = duckdb.connect(str(self.db_path))
        print(f"✓ Connected to: {self.db_path}")

        # Create schema
        self.create_schema(con)

        # Find new reviews
        existing = self.get_existing_files(con)
        new_reviews = self.find_new_reviews(existing)

        print(f"\n📊 Status:")
        print(f"  - Existing reviews in DB: {len(existing)}")
        print(f"  - New reviews to add: {len(new_reviews)}")

        if not new_reviews:
            print("\n✓ No new reviews to process. Database is up to date!")
            con.close()
            return

        # Process new reviews
        print(f"\n{'='*60}")
        print("Processing new reviews...")
        print(f"{'='*60}")

        success_count = 0
        error_count = 0

        for json_file, data in new_reviews:
            try:
                filename = data['extraction_metadata']['source_pdf_filename']
                self.insert_review(con, data, filename)
                print(f"  ✓ Added: {json_file.name}")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Error adding {json_file.name}: {e}")
                error_count += 1

        # Export to Parquet
        if success_count > 0:
            print(f"\n{'='*60}")
            self.export_parquet(con)

        # Final summary
        total_count = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

        print(f"\n{'='*60}")
        print("CONVERSION COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully added: {success_count}")
        if error_count > 0:
            print(f"✗ Errors: {error_count}")
        print(f"📊 Total reviews in database: {total_count}")
        print(f"\n📁 Database: {self.db_path}")
        print(f"📁 Parquet: {self.parquet_path}")

        con.close()


def main():
    # Dynamically determine base directory (parent of scripts/)
    base_dir = Path(__file__).parent.parent.resolve()
    converter = DuckDBConverter(base_dir)
    converter.run()


if __name__ == "__main__":
    main()
