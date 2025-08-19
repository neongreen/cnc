#!/usr/bin/env -S mise exec uv@latest -- uv run --script

# fmt: off
#MISE description="Validate SQL schema syntax"
# fmt: on

# /// script
# requires-python = ">=3.13"
# dependencies = ["duckdb"]
# ///

"""Validate SQL schema syntax using DuckDB."""

import duckdb
from pathlib import Path


def main():
    """Validate the SQL schema by attempting to execute it."""
    try:
        # Get the schema file path
        schema_file = (
            Path(__file__).parent.parent / "src" / "cnc" / "hive" / "schema.sql"
        )

        if not schema_file.exists():
            print(f"Error: Schema file not found at {schema_file}")
            return 1

        # Read and execute the schema
        schema_sql = schema_file.read_text()
        conn = duckdb.connect(":memory:")
        conn.execute(schema_sql)

        print("✅ Schema validation successful!")
        print(f"Schema file: {schema_file}")

        # Show the tables that were created
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"Tables created: {[table[0] for table in tables]}")

        conn.close()
        return 0

    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
