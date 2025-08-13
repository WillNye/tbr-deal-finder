from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

import click
import duckdb

from tbr_deal_finder.utils import get_duckdb_conn


@dataclass
class TableMigration:
    version: int
    table_name: str
    sql: str


_MIGRATIONS = [
    TableMigration(
        version=1,
        table_name="retailer_deal",
        sql="""
            CREATE TABLE retailer_deal
            (
                retailer          VARCHAR,
                title           VARCHAR,
                authors         VARCHAR,
                list_price      FLOAT,
                current_price   FLOAT,
                timepoint       TIMESTAMP_NS,
                format          VARCHAR,
                deleted         BOOLEAN,
                deal_id         VARCHAR
            );
            """
    ),
    TableMigration(
        version=1,
        table_name="latest_deal_run_history",
        sql="""
            CREATE TABLE latest_deal_run_history
            (
                timepoint           TIMESTAMP_NS,
                ran_successfully    BOOLEAN,
                details             VARCHAR
            );
            """
    ),
    TableMigration(
        version=1,
        table_name="tbr_book",
        sql="""
            CREATE TABLE tbr_book
            (
                title                VARCHAR,
                authors              VARCHAR,
                format               VARCHAR,
                ebook_asin           VARCHAR,
                audiobook_isbn       VARCHAR,
                audiobook_list_price FLOAT,
                book_id              VARCHAR
            );
            """
    ),
]


def apply_migration(migration: TableMigration, cursor: duckdb.DuckDBPyConnection) -> None:
    """Apply a single migration to the database."""
    click.echo(
        f"Applying migration - version: {migration.version}, table: {migration.table_name}"
    )

    try:
        # Execute the migration SQL
        cursor.execute(migration.sql)

        # Update schema_versions table
        cursor.execute("""
                       INSERT INTO schema_versions (table_name, version)
                       VALUES (?, ?) ON CONFLICT(table_name) DO
                       UPDATE SET version = EXCLUDED.version
                       """, (migration.table_name, migration.version))

        click.echo(
            f"Migration applied successfully - version: {migration.version}, table: {migration.table_name}"
        )

    except duckdb.Error as e:
        raise RuntimeError(
            f"Failed to apply migration {migration.version} to {migration.table_name}: {e}"
        )


def make_migrations():
    db_conn = get_duckdb_conn()

    try:
        # Create schema_versions table if it doesn't exist
        db_conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions
        (
          table_name
          VARCHAR
          PRIMARY
          KEY,
          version
          INTEGER
        );
        """)

        # Group migrations by table name
        table_migration_map: Dict[str, List[TableMigration]] = defaultdict(list)
        for migration in _MIGRATIONS:
            table_migration_map[migration.table_name].append(migration)

        # Begin transaction
        with db_conn:
            cursor = db_conn.cursor()

            for table_name, table_migrations in table_migration_map.items():
                # Sort migrations by version
                table_migrations.sort(key=lambda m: m.version)

                # Get current version for this table
                cursor.execute("""
                               SELECT COALESCE(MAX(version), 0)
                               FROM schema_versions
                               WHERE table_name = ?
                               """, (table_name,))

                result = cursor.fetchone()
                current_version = result[0] if result else 0

                # Apply pending migrations
                for migration in table_migrations:
                    if migration.version > current_version:
                        apply_migration(migration, cursor)

    except duckdb.Error as e:
        raise RuntimeError(f"Failed to apply migrations: {e}")
