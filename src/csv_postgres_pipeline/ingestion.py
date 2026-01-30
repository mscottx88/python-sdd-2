"""Ingestion orchestration module.

Coordinates CSV reading, database operations, and error handling modes.
Implements atomic transaction semantics.
"""

import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Literal, cast

from psycopg_pool import ConnectionPool

from src.csv_postgres_pipeline.csv_reader import (
    has_data_rows,
    is_file_empty,
    iterate_chunks_validated,
    iterate_rows_validated,
    read_headers,
)
from src.csv_postgres_pipeline.database import (
    add_columns_to_table,
    close_pool,
    compare_schemas,
    copy_rows,
    create_connection,
    create_pool,
    create_table,
    get_pooled_connection,
    get_table_schema,
    table_exists,
)
from src.csv_postgres_pipeline.exceptions import EmptyFileError, SchemaMismatchError
from src.csv_postgres_pipeline.models import (
    CSVConfig,
    DatabaseConfig,
    IngestionResult,
    SkippedRow,
    TableSchema,
)

SchemaMode = Literal["strict", "match", "alter"]
RowMode = Literal["strict", "skip", "lenient"]
EmptyMode = Literal["strict", "headers", "permissive"]


def ingest(
    db_config: DatabaseConfig,
    csv_config: CSVConfig,
) -> IngestionResult:
    """Ingest CSV file into PostgreSQL table.

    Args:
        db_config: Database connection configuration.
        csv_config: CSV file and ingestion configuration.

    Returns:
        IngestionResult with status and statistics.

    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        EmptyFileError: If file is empty and empty_mode is strict.
        MalformedRowError: If rows are malformed and row_mode is strict.
        SchemaMismatchError: If schema doesn't match and schema_mode is strict.
    """
    start_time: float = time.time()
    file_path: Path = Path(csv_config.file_path)

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    # Handle empty file based on mode
    empty_mode: EmptyMode = csv_config.empty_mode or "strict"
    if is_file_empty(file_path):
        if empty_mode == "strict":
            raise EmptyFileError(
                f"CSV file is empty: {file_path}",
                file_path=file_path,
            )
        if empty_mode == "permissive":
            return IngestionResult(
                status="success",
                rows_processed=0,
                rows_inserted=0,
                rows_skipped=0,
                table_created=False,
                duration_seconds=time.time() - start_time,
            )
        # headers mode falls through but will fail on read_headers

    # Read headers
    headers: list[str] = read_headers(file_path)

    # Handle headers-only file
    if not has_data_rows(file_path):
        if empty_mode == "strict":
            raise EmptyFileError(
                f"CSV file has no data rows: {file_path}",
                file_path=file_path,
            )
        if empty_mode in ("headers", "permissive"):
            # Create table if needed, return success with 0 rows
            with create_connection(db_config) as conn:
                table_created: bool = False
                if not table_exists(conn, csv_config.table_name):
                    create_table(conn, csv_config.table_name, headers)
                    table_created = True
                conn.commit()

            return IngestionResult(
                status="success",
                rows_processed=0,
                rows_inserted=0,
                rows_skipped=0,
                table_created=table_created,
                duration_seconds=time.time() - start_time,
            )

    # Process rows based on row_mode
    row_mode: RowMode = csv_config.row_mode or "strict"
    skipped_rows: list[SkippedRow] = []
    rows: list[list[str]] = []

    if row_mode == "strict":
        # Use validated iterator that raises on error (returns Iterator directly)
        strict_result: (
            Iterator[list[str]] | tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]]
        ) = iterate_rows_validated(file_path, mode="strict")
        strict_iter: Iterator[list[str]] = cast(Iterator[list[str]], strict_result)
        rows = list(strict_iter)
    elif row_mode == "skip":
        # In skip mode, returns tuple of (iterator, skipped_list)
        skip_result: (
            Iterator[list[str]] | tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]]
        ) = iterate_rows_validated(file_path, mode="skip")
        skip_tuple: tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]] = cast(
            tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]],
            skip_result,
        )
        skip_iter, skipped_list = skip_tuple
        rows = list(skip_iter)
        skipped_rows = [
            SkippedRow(line_number=line, reason=reason, raw_content=",".join(raw))
            for line, reason, raw in skipped_list
        ]
    else:  # lenient
        # In lenient mode, returns tuple of (iterator, empty_list)
        lenient_result: (
            Iterator[list[str]] | tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]]
        ) = iterate_rows_validated(file_path, mode="lenient")
        lenient_tuple: tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]] = cast(
            tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]],
            lenient_result,
        )
        lenient_iter, _ = lenient_tuple
        rows = list(lenient_iter)

    # Connect and perform ingestion
    with create_connection(db_config) as conn:
        table_created = False
        schema_mode: SchemaMode = csv_config.schema_mode or "strict"

        # Check if table exists
        existing_schema: TableSchema | None = get_table_schema(conn, csv_config.table_name)

        if existing_schema is None:
            # Create new table
            create_table(conn, csv_config.table_name, headers)
            table_created = True
        else:
            # Compare schemas
            comparison: Any = compare_schemas(headers, existing_schema)

            if not comparison.is_match:
                if schema_mode == "strict":
                    raise SchemaMismatchError(
                        f"Schema mismatch for table '{csv_config.table_name}'",
                        csv_columns=headers,
                        table_columns=existing_schema.get_column_names(),
                        missing_in_table=comparison.missing_in_table,
                        missing_in_csv=comparison.missing_in_csv,
                    )
                if schema_mode == "alter" and comparison.missing_in_table:
                    # Add missing columns to table
                    add_columns_to_table(
                        conn,
                        csv_config.table_name,
                        comparison.missing_in_table,
                    )
                if schema_mode == "match":
                    # Only use common columns
                    headers = comparison.common_columns
                    # Filter rows to only include common columns
                    original_headers: list[str] = read_headers(file_path)
                    common_indices: list[int] = [
                        original_headers.index(h) for h in headers if h in original_headers
                    ]
                    rows = [[row[i] for i in common_indices] for row in rows]

        # Copy data
        rows_inserted: int = copy_rows(conn, csv_config.table_name, headers, rows)
        conn.commit()

    duration: float = time.time() - start_time
    result_status: Literal["success", "partial", "failed"] = (
        "success" if not skipped_rows else "partial"
    )

    return IngestionResult(
        status=result_status,
        rows_processed=len(rows) + len(skipped_rows),
        rows_inserted=rows_inserted,
        rows_skipped=len(skipped_rows),
        skipped_rows=skipped_rows if skipped_rows else None,
        table_created=table_created,
        duration_seconds=duration,
    )


def ingest_streaming(
    db_config: DatabaseConfig,
    csv_config: CSVConfig,
    progress_callback: Callable[[int], None] | None = None,
    *,
    pool: ConnectionPool | None = None,
) -> IngestionResult:
    """Ingest CSV file into PostgreSQL using streaming for memory efficiency.

    This function processes the CSV file in chunks, maintaining bounded
    memory usage regardless of file size. Suitable for large files (100MB+).

    Args:
        db_config: Database connection configuration.
        csv_config: CSV file and ingestion configuration.
        progress_callback: Optional callback called with rows processed count.
        pool: Optional connection pool for connection reuse. If provided,
            connections are obtained from the pool instead of creating new ones.

    Returns:
        IngestionResult with status and statistics.

    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        EmptyFileError: If file is empty and empty_mode is strict.
        MalformedRowError: If rows are malformed and row_mode is strict.
        SchemaMismatchError: If schema doesn't match and schema_mode is strict.
    """
    start_time: float = time.time()
    file_path: Path = Path(csv_config.file_path)

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    # Handle empty file based on mode
    empty_mode: EmptyMode = csv_config.empty_mode or "strict"
    if is_file_empty(file_path):
        if empty_mode == "strict":
            raise EmptyFileError(
                f"CSV file is empty: {file_path}",
                file_path=file_path,
            )
        if empty_mode == "permissive":
            return IngestionResult(
                status="success",
                rows_processed=0,
                rows_inserted=0,
                rows_skipped=0,
                table_created=False,
                duration_seconds=time.time() - start_time,
            )

    # Read headers
    headers: list[str] = read_headers(file_path)

    # Helper to get connection - uses pool if provided, otherwise creates new
    def get_connection_ctx() -> AbstractContextManager[Any]:
        if pool is not None:
            return get_pooled_connection(pool)
        return create_connection(db_config)

    # Handle headers-only file
    if not has_data_rows(file_path):
        if empty_mode == "strict":
            raise EmptyFileError(
                f"CSV file has no data rows: {file_path}",
                file_path=file_path,
            )
        if empty_mode in ("headers", "permissive"):
            with get_connection_ctx() as conn:
                table_created: bool = False
                if not table_exists(conn, csv_config.table_name):
                    create_table(conn, csv_config.table_name, headers)
                    table_created = True
                conn.commit()

            return IngestionResult(
                status="success",
                rows_processed=0,
                rows_inserted=0,
                rows_skipped=0,
                table_created=table_created,
                duration_seconds=time.time() - start_time,
            )

    # Get chunk size from config
    chunk_size: int = csv_config.chunk_size or 1000
    row_mode: RowMode = csv_config.row_mode or "strict"
    skipped_rows: list[SkippedRow] = []
    skipped_list: list[tuple[int, str, list[str]]] = []

    # Connect and perform streaming ingestion (uses pool if provided)
    with get_connection_ctx() as conn:
        table_created = False
        schema_mode: SchemaMode = csv_config.schema_mode or "strict"

        # Check if table exists
        existing_schema: TableSchema | None = get_table_schema(conn, csv_config.table_name)
        use_column_filtering: bool = False
        original_headers_for_filtering: list[str] = []

        if existing_schema is None:
            create_table(conn, csv_config.table_name, headers)
            table_created = True
        else:
            comparison: Any = compare_schemas(headers, existing_schema)

            if not comparison.is_match:
                if schema_mode == "strict":
                    raise SchemaMismatchError(
                        f"Schema mismatch for table '{csv_config.table_name}'",
                        csv_columns=headers,
                        table_columns=existing_schema.get_column_names(),
                        missing_in_table=comparison.missing_in_table,
                        missing_in_csv=comparison.missing_in_csv,
                    )
                if schema_mode == "alter" and comparison.missing_in_table:
                    add_columns_to_table(
                        conn,
                        csv_config.table_name,
                        comparison.missing_in_table,
                    )
                if schema_mode == "match":
                    # Only use common columns - filter headers
                    use_column_filtering = True
                    original_headers_for_filtering = headers[:]
                    headers = comparison.common_columns

        # Get chunk iterator based on mode
        chunks_iter: Any
        if row_mode == "strict":
            chunks_iter = iterate_chunks_validated(file_path, chunk_size=chunk_size, mode="strict")
        elif row_mode == "skip":
            skip_chunks_result: Any = iterate_chunks_validated(
                file_path, chunk_size=chunk_size, mode="skip"
            )
            skip_chunks_tuple: tuple[Any, list[tuple[int, str, list[str]]]] = cast(
                tuple[Any, list[tuple[int, str, list[str]]]],
                skip_chunks_result,
            )
            chunks_iter, skipped_list = skip_chunks_tuple
        else:  # lenient
            lenient_chunks_result: Any = iterate_chunks_validated(
                file_path, chunk_size=chunk_size, mode="lenient"
            )
            lenient_chunks_tuple: tuple[Any, list[tuple[int, str, list[str]]]] = cast(
                tuple[Any, list[tuple[int, str, list[str]]]],
                lenient_chunks_result,
            )
            chunks_iter, _ = lenient_chunks_tuple

        # Stream data in chunks using COPY protocol
        total_inserted: int = 0
        total_processed: int = 0

        for chunk in chunks_iter:
            # Ensure chunk is properly typed as list of rows
            rows_chunk: list[list[str]] = list(chunk)

            # Filter columns if in match mode
            if use_column_filtering:
                column_indices: list[int] = [
                    original_headers_for_filtering.index(h)
                    for h in headers
                    if h in original_headers_for_filtering
                ]
                rows_chunk = [[row[i] for i in column_indices] for row in rows_chunk]

            # Use copy_rows for each chunk (more reliable than streaming)
            rows_copied: int = copy_rows(
                conn,
                csv_config.table_name,
                headers,
                rows_chunk,
            )
            total_inserted += rows_copied
            total_processed += len(rows_chunk)

            if progress_callback:
                progress_callback(total_processed)

        conn.commit()

    # Convert skipped list to SkippedRow objects
    if skipped_list:
        skipped_rows = [
            SkippedRow(line_number=line, reason=reason, raw_content=",".join(raw))
            for line, reason, raw in skipped_list  # pylint: disable=not-an-iterable
        ]

    duration: float = time.time() - start_time
    result_status: Literal["success", "partial", "failed"] = (
        "success" if not skipped_rows else "partial"
    )

    return IngestionResult(
        status=result_status,
        rows_processed=total_processed + len(skipped_rows),
        rows_inserted=total_inserted,
        rows_skipped=len(skipped_rows),
        skipped_rows=skipped_rows if skipped_rows else None,
        table_created=table_created,
        duration_seconds=duration,
    )


def ingest_streaming_with_pool(
    db_config: DatabaseConfig,
    csv_config: CSVConfig,
    progress_callback: Callable[[int], None] | None = None,
) -> IngestionResult:
    """Ingest CSV file using a managed connection pool.

    This convenience function creates a connection pool, performs the ingestion,
    and then closes the pool. Useful for single-use scenarios where you want
    the benefits of pooling without managing the pool lifecycle manually.

    For multiple sequential ingestions, consider using ingest_streaming with
    a pre-created pool for better efficiency.

    Args:
        db_config: Database connection configuration (includes pool settings).
        csv_config: CSV file and ingestion configuration.
        progress_callback: Optional callback called with rows processed count.

    Returns:
        IngestionResult with status and statistics.

    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        EmptyFileError: If file is empty and empty_mode is strict.
        MalformedRowError: If rows are malformed and row_mode is strict.
        SchemaMismatchError: If schema doesn't match and schema_mode is strict.
    """
    pool: ConnectionPool = create_pool(db_config)
    try:
        return ingest_streaming(
            db_config,
            csv_config,
            progress_callback,
            pool=pool,
        )
    finally:
        close_pool(pool)
