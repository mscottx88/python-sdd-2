"""Database operations module for PostgreSQL.

Provides connection management, schema detection, table creation, and COPY execution.
Uses psycopg3 for efficient PostgreSQL operations with connection pooling.
"""

from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from typing import Any

import psycopg
from psycopg import Connection, sql
from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.exceptions import (
    ConnectionError as PipelineConnectionError,
)
from src.csv_postgres_pipeline.models import ColumnInfo, DatabaseConfig, TableSchema


@contextmanager
def create_connection(config: DatabaseConfig) -> Generator[Connection]:
    """Create a database connection from configuration.

    Args:
        config: Database configuration with connection parameters.

    Yields:
        Active database connection.

    Raises:
        ConnectionError: If connection cannot be established.
    """
    try:
        conn: Connection = psycopg.connect(config.connection_string)
        try:
            yield conn
        finally:
            conn.close()  # pylint: disable=no-member  # JUSTIFICATION: Pylint doesn't recognize psycopg Connection.close() method
    except psycopg.OperationalError as e:
        raise PipelineConnectionError(str(e)) from e
    except psycopg.Error as e:
        raise PipelineConnectionError(str(e)) from e


def get_table_schema(conn: Connection, table_name: str) -> TableSchema | None:
    """Get the schema of an existing table.

    Args:
        conn: Active database connection.
        table_name: Name of the table to inspect.

    Returns:
        TableSchema if table exists, None otherwise.
    """
    query: str = """
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """

    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        rows: list[Any] = cur.fetchall()

    if not rows:
        return None

    columns: list[ColumnInfo] = [
        ColumnInfo(
            name=row[0],
            data_type=row[1],
            nullable=row[2] == "YES",
            ordinal_position=row[3],
        )
        for row in rows
    ]

    return TableSchema(table_name=table_name, columns=columns)


def create_table(conn: Connection, table_name: str, headers: list[str]) -> None:
    """Create a table with TEXT columns from headers.

    Args:
        conn: Active database connection.
        table_name: Name of the table to create.
        headers: List of column names.
    """
    # Build column definitions (all TEXT)
    columns: list[sql.Composable] = [
        sql.SQL("{} TEXT").format(sql.Identifier(header)) for header in headers
    ]

    query: sql.Composed = sql.SQL("CREATE TABLE {} ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(columns),
    )

    with conn.cursor() as cur:
        cur.execute(query)


def copy_rows(
    conn: Connection,
    table_name: str,
    headers: list[str],
    rows: Sequence[Sequence[str]],
) -> int:
    """Copy rows into table using COPY protocol.

    Args:
        conn: Active database connection.
        table_name: Target table name.
        headers: Column names for COPY.
        rows: Rows to insert.

    Returns:
        Number of rows copied.
    """
    if not rows:
        return 0

    # Build COPY command with column names
    columns: sql.Composable = sql.SQL(", ").join(sql.Identifier(h) for h in headers)
    copy_sql: sql.Composed = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV)").format(
        sql.Identifier(table_name),
        columns,
    )

    # Prepare CSV data in memory
    buffer = StringIO()
    for row in rows:
        # Escape fields and write CSV line
        escaped: list[str] = []
        for field in row:
            if field is None:
                escaped.append("")
            elif '"' in field or "," in field or "\n" in field:
                escaped.append('"' + field.replace('"', '""') + '"')
            else:
                escaped.append(field)
        buffer.write(",".join(escaped) + "\n")

    buffer.seek(0)

    with conn.cursor() as cur, cur.copy(copy_sql) as copy:
        while data := buffer.read(8192):
            copy.write(data)

    return len(rows)


def copy_rows_streaming(
    conn: Connection,
    table_name: str,
    headers: list[str],
    rows_iterator: Iterator[Sequence[str]],
) -> int:
    """Copy rows into table using streaming COPY protocol.

    Args:
        conn: Active database connection.
        table_name: Target table name.
        headers: Column names for COPY.
        rows_iterator: Iterator yielding rows.

    Returns:
        Number of rows copied.
    """
    columns: sql.Composable = sql.SQL(", ").join(sql.Identifier(h) for h in headers)
    copy_sql: sql.Composed = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV)").format(
        sql.Identifier(table_name),
        columns,
    )

    count: int = 0
    with conn.cursor() as cur, cur.copy(copy_sql) as copy:
        for row in rows_iterator:
            # Escape and format row
            escaped: list[str] = []
            for field in row:
                if field is None:
                    escaped.append("")
                elif '"' in str(field) or "," in str(field) or "\n" in str(field):
                    escaped.append('"' + str(field).replace('"', '""') + '"')
                else:
                    escaped.append(str(field))
            line: str = ",".join(escaped) + "\n"
            copy.write(line.encode("utf-8"))
            count += 1

    return count


@dataclass
class SchemaComparisonResult:
    """Result of comparing CSV headers with table schema."""

    is_match: bool
    missing_in_table: list[str]
    missing_in_csv: list[str]
    common_columns: list[str]


def compare_schemas(
    csv_headers: list[str],
    table_schema: TableSchema,
) -> SchemaComparisonResult:
    """Compare CSV headers with existing table schema.

    Args:
        csv_headers: Column names from CSV file.
        table_schema: Schema of the existing table.

    Returns:
        SchemaComparisonResult with match status and differences.
    """
    table_columns: set[str] = set(table_schema.get_column_names())
    csv_columns: set[str] = set(csv_headers)

    missing_in_table: list[str] = list(csv_columns - table_columns)
    missing_in_csv: list[str] = list(table_columns - csv_columns)
    common_columns: list[str] = list(csv_columns & table_columns)

    is_match: bool = len(missing_in_table) == 0 and len(missing_in_csv) == 0

    return SchemaComparisonResult(
        is_match=is_match,
        missing_in_table=missing_in_table,
        missing_in_csv=missing_in_csv,
        common_columns=common_columns,
    )


def add_columns_to_table(
    conn: Connection,
    table_name: str,
    column_names: list[str],
) -> None:
    """Add new TEXT columns to an existing table.

    Args:
        conn: Active database connection.
        table_name: Name of the table to alter.
        column_names: Names of columns to add.
    """
    for col_name in column_names:
        query: sql.Composed = sql.SQL("ALTER TABLE {} ADD COLUMN {} TEXT").format(
            sql.Identifier(table_name),
            sql.Identifier(col_name),
        )
        with conn.cursor() as cur:
            cur.execute(query)


def table_exists(conn: Connection, table_name: str) -> bool:
    """Check if a table exists in the database.

    Args:
        conn: Active database connection.
        table_name: Name of the table to check.

    Returns:
        True if table exists, False otherwise.
    """
    query: str = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        )
    """
    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        result: tuple[Any, ...] | None = cur.fetchone()
        return result[0] if result else False


# Connection Pool Management (T054-T055)


def create_pool(config: DatabaseConfig) -> ConnectionPool:
    """Create a connection pool from database configuration.

    Args:
        config: Database configuration with pool settings.

    Returns:
        ConnectionPool instance ready for use.

    Raises:
        ConnectionError: If pool cannot be created.
    """
    try:
        pool = ConnectionPool(
            conninfo=config.connection_string,
            min_size=config.pool_min_size,
            max_size=config.pool_max_size,
            timeout=config.pool_timeout,
            open=True,
        )
        return pool
    except psycopg.OperationalError as e:
        raise PipelineConnectionError(f"Failed to create connection pool: {e}") from e
    except psycopg.Error as e:
        raise PipelineConnectionError(f"Failed to create connection pool: {e}") from e


def close_pool(pool: ConnectionPool) -> None:
    """Close a connection pool and release all connections.

    Args:
        pool: ConnectionPool instance to close.
    """
    pool.close()


@contextmanager
def get_pooled_connection(pool: ConnectionPool) -> Generator[Connection]:
    """Get a connection from the pool.

    This is a context manager that automatically returns the connection
    to the pool when the context exits.

    Args:
        pool: ConnectionPool to get connection from.

    Yields:
        Active database connection from the pool.

    Raises:
        ConnectionError: If a connection cannot be obtained.
    """
    try:
        with pool.connection() as conn:
            yield conn
    except psycopg.OperationalError as e:
        raise PipelineConnectionError(str(e)) from e
    except psycopg.Error as e:
        raise PipelineConnectionError(str(e)) from e
