"""CLI entrypoint for CSV ingestion.

Provides the csv-ingest command with all configuration options.
"""

import json
import sys
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click
from pydantic import SecretStr

from src.csv_postgres_pipeline.csv_reader import count_rows
from src.csv_postgres_pipeline.exceptions import (
    ConfigurationError,
    CSVError,
    DatabaseError,
    EmptyFileError,
    IngestionError,
    MalformedRowError,
    SchemaMismatchError,
)
from src.csv_postgres_pipeline.ingestion import ingest_streaming_with_pool
from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig, IngestionResult

# Exit codes per contract
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_CSV_ERROR = 2
EXIT_DB_ERROR = 3
EXIT_CONFIG_ERROR = 4


@click.command()
@click.argument("csv_file", type=click.Path(exists=False))
@click.argument("table_name", type=str)
@click.option(
    "-h",
    "--host",
    default="localhost",
    envvar="PGHOST",
    help="Database host",
)
@click.option(
    "-p",
    "--port",
    default=5432,
    type=int,
    envvar="PGPORT",
    help="Database port",
)
@click.option(
    "-d",
    "--database",
    envvar="PGDATABASE",
    help="Database name",
)
@click.option(
    "-u",
    "--user",
    envvar="PGUSER",
    help="Database user",
)
@click.option(
    "-P",
    "--password",
    envvar="PGPASSWORD",
    help="Database password",
)
@click.option(
    "--database-url",
    envvar="DATABASE_URL",
    help="Full database connection URL",
)
@click.option(
    "--schema-mode",
    type=click.Choice(["strict", "match", "alter"]),
    default="strict",
    help="Schema mismatch handling mode",
)
@click.option(
    "--row-mode",
    type=click.Choice(["strict", "skip", "lenient"]),
    default="strict",
    help="Malformed row handling mode",
)
@click.option(
    "--empty-mode",
    type=click.Choice(["strict", "headers", "permissive"]),
    default="strict",
    help="Empty file handling mode",
)
@click.option(
    "--verbosity",
    "-v",
    type=click.Choice(["quiet", "normal", "verbose"]),
    default="normal",
    help="Output verbosity level",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output result as JSON",
)
@click.option(
    "--chunk-size",
    type=click.IntRange(100, 100000),
    default=1000,
    help="Rows per chunk (100-100000)",
)
@click.option(
    "--pool-size",
    type=click.IntRange(1, 50),
    default=5,
    help="Max connection pool size (1-50)",
)
# pylint: disable=too-many-positional-arguments  # JUSTIFICATION: Click decorator pattern requires one parameter per CLI option
def main(
    csv_file: str,
    table_name: str,
    host: str,
    port: int,
    database: str | None,
    user: str | None,
    password: str | None,
    database_url: str | None,
    schema_mode: str,
    row_mode: str,
    empty_mode: str,
    verbosity: str,
    json_output: bool,
    chunk_size: int,
    pool_size: int,
) -> None:
    """Ingest CSV_FILE into PostgreSQL TABLE_NAME.

    Streams CSV data into PostgreSQL using the COPY protocol for efficient
    bulk loading. Supports configurable handling of schema mismatches,
    malformed rows, and empty files.
    """
    try:
        # Validate CSV file exists first
        file_path = Path(csv_file)
        if not file_path.exists():
            _handle_error(
                CSVError(
                    f"CSV file not found: {csv_file}",
                    file_path=file_path,
                ),
                json_output,
                verbosity,
            )
            sys.exit(EXIT_CSV_ERROR)

        # Build database config
        db_config: DatabaseConfig = _build_db_config(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            database_url=database_url,
            pool_max_size=pool_size,
        )

        # Build CSV config
        csv_config = CSVConfig(
            file_path=file_path,
            table_name=table_name,
            schema_mode=schema_mode,  # type: ignore[arg-type]
            row_mode=row_mode,  # type: ignore[arg-type]
            empty_mode=empty_mode,  # type: ignore[arg-type]
            chunk_size=chunk_size,
        )

        # Start memory tracking for verbose mode
        peak_memory_mb: float | None = None
        if verbosity == "verbose":
            tracemalloc.start()

        # Show progress message
        if verbosity != "quiet" and not json_output:
            click.echo(f"Ingesting {csv_file} into table '{table_name}'...")

        # Perform streaming ingestion with optional progress callback
        progress_callback: Callable[[int], None] | None = None
        if verbosity == "normal" and not json_output:
            # Try to get total row count for progress bar
            try:
                total_rows: int = count_rows(file_path)
                progress_callback = _create_progress_callback(total_rows)
            # pylint: disable=broad-exception-caught
            # JUSTIFICATION: Must continue without progress bar if row counting fails
            except Exception:  # noqa: S110
                # If we can't count rows, proceed without progress bar
                pass
            # pylint: enable=broad-exception-caught

        result: IngestionResult = ingest_streaming_with_pool(
            db_config, csv_config, progress_callback
        )

        # Get memory stats for verbose mode
        if verbosity == "verbose":
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_memory_mb = peak / (1024 * 1024)

        # Output result
        _output_result(result, json_output, verbosity, table_name, peak_memory_mb)

        # Set exit code
        if result.status == "partial":
            sys.exit(EXIT_PARTIAL)
        sys.exit(EXIT_SUCCESS)

    except EmptyFileError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_CSV_ERROR)
    except MalformedRowError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_CSV_ERROR)
    except CSVError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_CSV_ERROR)
    except SchemaMismatchError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_DB_ERROR)
    except DatabaseError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_DB_ERROR)
    except ConfigurationError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_CONFIG_ERROR)
    except IngestionError as e:
        _handle_error(e, json_output, verbosity)
        sys.exit(EXIT_CSV_ERROR)


# pylint: disable=too-many-positional-arguments  # JUSTIFICATION: Mirrors CLI parameters for database connection configuration
def _build_db_config(
    host: str,
    port: int,
    database: str | None,
    user: str | None,
    password: str | None,
    database_url: str | None,
    pool_max_size: int,
) -> DatabaseConfig:
    """Build DatabaseConfig from CLI options."""
    if database_url:
        # Parse DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        return DatabaseConfig.from_url(database_url, pool_max_size=pool_max_size)

    if not all([database, user]):
        raise ConfigurationError(
            "Database connection requires --database and --user (or --database-url / DATABASE_URL)"
        )

    return DatabaseConfig(
        host=host,
        port=port,
        database=database,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
        password=SecretStr(password or ""),
        pool_max_size=pool_max_size,
    )


def _create_progress_callback(total_rows: int) -> Callable[[int], None]:
    """Create a progress callback with a rich progress bar.

    Args:
        total_rows: Total number of rows to process.

    Returns:
        A callback function that updates the progress bar.
    """
    # pylint: disable=import-outside-toplevel  # JUSTIFICATION: Lazy import for CLI performance - only load rich when progress bar is needed
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    # pylint: enable=import-outside-toplevel

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total} rows)"),
    )
    task_id: Any = progress.add_task("Processing", total=total_rows)
    progress.start()

    def callback(rows_processed: int) -> None:
        progress.update(task_id, completed=rows_processed)
        if rows_processed >= total_rows:
            progress.stop()

    return callback


def _output_result(
    result: Any,
    json_output: bool,
    verbosity: str,
    table_name: str,
    peak_memory_mb: float | None = None,
) -> None:
    """Output ingestion result based on format and verbosity."""
    if json_output:
        output: dict[str, Any] = {
            "status": result.status,
            "rows_processed": result.rows_processed,
            "rows_inserted": result.rows_inserted,
            "rows_skipped": result.rows_skipped,
            "table_name": table_name,
            "table_created": result.table_created,
            "duration_seconds": round(result.duration_seconds, 2),
        }
        if peak_memory_mb is not None:
            output["peak_memory_mb"] = round(peak_memory_mb, 2)
        if result.skipped_rows:
            output["skipped_rows"] = [
                {
                    "line": sr.line_number,
                    "reason": sr.reason,
                }
                for sr in result.skipped_rows
            ]
        click.echo(json.dumps(output, indent=2))
    elif verbosity == "quiet":
        click.echo(result.rows_inserted)
    else:
        # Normal or verbose
        if result.status == "success":
            click.echo(
                f"Successfully inserted {result.rows_inserted} rows "
                f"into '{table_name}' in {result.duration_seconds:.1f} seconds"
            )
        else:
            click.echo(
                f"Partially completed: {result.rows_inserted} rows inserted, "
                f"{result.rows_skipped} rows skipped"
            )

        # Show verbose stats
        if verbosity == "verbose":
            throughput: float = (
                result.rows_inserted / result.duration_seconds if result.duration_seconds > 0 else 0
            )
            click.echo("\nPerformance stats:")
            click.echo(f"  Throughput: {throughput:.0f} rows/second")
            if peak_memory_mb is not None:
                click.echo(f"  Peak memory: {peak_memory_mb:.2f} MB")

            if result.skipped_rows:
                click.echo("\nSkipped rows:")
                for sr in result.skipped_rows[:10]:  # Show first 10
                    click.echo(f"  Line {sr.line_number}: {sr.reason}")
                if len(result.skipped_rows) > 10:
                    click.echo(f"  ... and {len(result.skipped_rows) - 10} more")


def _handle_error(
    error: Exception,
    json_output: bool,
    verbosity: str,
) -> None:
    """Handle and output error based on format."""
    if json_output:
        output: dict[str, Any] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        # Add details for specific error types
        if isinstance(error, SchemaMismatchError):
            output["details"] = {
                "csv_columns": error.csv_columns,
                "table_columns": error.table_columns,
                "missing_in_table": error.missing_in_table,
                "missing_in_csv": error.missing_in_csv,
            }
        elif isinstance(error, MalformedRowError):
            output["details"] = {
                "line_number": error.line_number,
                "expected_columns": error.expected_columns,
                "actual_columns": error.actual_columns,
            }

        click.echo(json.dumps(output, indent=2))
    else:
        if verbosity != "quiet":
            click.echo(f"Error: {error}", err=True)
        else:
            click.echo(str(error), err=True)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter  # JUSTIFICATION: Click decorator injects parameters at runtime
