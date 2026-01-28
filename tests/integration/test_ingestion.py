"""Integration tests for CSV ingestion functionality.

Tests full ingestion workflow including database operations.
Requires PostgreSQL (via Docker/testcontainers or local instance).
Written following TDD - these tests should FAIL before implementation.
"""

from pathlib import Path
from typing import Any

import pytest


@pytest.mark.integration
class TestBasicIngestion:
    """Integration tests for basic CSV ingestion (T019)."""

    def test_ingestion_module_exists(self) -> None:
        """Test that ingestion module can be imported."""
        from src.csv_postgres_pipeline import ingestion

        assert ingestion is not None

    def test_ingest_function_exists(self) -> None:
        """Test that ingest function exists."""
        from src.csv_postgres_pipeline.ingestion import ingest

        assert ingest is not None

    def test_ingest_creates_new_table(
        self,
        sample_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion creates a new table when it doesn't exist."""
        from src.csv_postgres_pipeline.database import create_connection
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)

        # Drop table if it exists from previous test runs
        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_new_table")
            conn.commit()

        csv_config = CSVConfig(
            file_path=sample_csv_file,
            table_name="test_new_table",
        )

        result = ingest(db_config, csv_config)

        assert result.status == "success"
        assert result.rows_inserted == 3
        assert result.table_created is True

    def test_ingest_appends_to_existing_table(
        self,
        sample_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion appends data to an existing table."""
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=sample_csv_file,
            table_name="test_append_table",
        )

        # First ingestion creates table
        result1 = ingest(db_config, csv_config)
        assert result1.rows_inserted == 3

        # Second ingestion appends
        result2 = ingest(db_config, csv_config)
        assert result2.rows_inserted == 3
        assert result2.table_created is False

    def test_ingest_returns_result_with_row_count(
        self,
        sample_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion returns result with correct row count."""
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=sample_csv_file,
            table_name="test_row_count_table",
        )

        result = ingest(db_config, csv_config)

        assert result.rows_processed == 3
        assert result.rows_inserted == 3
        assert result.rows_skipped == 0


@pytest.mark.integration
class TestIngestionErrorHandling:
    """Integration tests for ingestion error handling."""

    def test_ingest_file_not_found_raises_error(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion raises error for non-existent file."""
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=Path("/nonexistent/file.csv"),
            table_name="test_table",
        )

        with pytest.raises(FileNotFoundError):
            ingest(db_config, csv_config)

    def test_ingest_empty_file_strict_mode(
        self,
        empty_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion fails for empty file in strict mode."""
        from src.csv_postgres_pipeline.exceptions import EmptyFileError
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=empty_csv_file,
            table_name="test_empty_table",
            empty_mode="strict",
        )

        with pytest.raises(EmptyFileError):
            ingest(db_config, csv_config)

    def test_ingest_malformed_file_strict_mode(
        self,
        malformed_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion fails for malformed file in strict mode."""
        from src.csv_postgres_pipeline.exceptions import MalformedRowError
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=malformed_csv_file,
            table_name="test_malformed_table",
            row_mode="strict",
        )

        with pytest.raises(MalformedRowError):
            ingest(db_config, csv_config)

    def test_ingest_malformed_file_skip_mode(
        self,
        malformed_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test ingestion skips malformed rows in skip mode."""
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=malformed_csv_file,
            table_name="test_skip_table",
            row_mode="skip",
        )

        result = ingest(db_config, csv_config)

        assert result.status in ("success", "partial")
        assert result.rows_skipped > 0
        assert result.rows_inserted == 1  # Only valid row


@pytest.mark.integration
class TestIngestionAtomicity:
    """Integration tests for atomic transaction behavior."""

    def test_ingest_rollback_on_error(
        self,
        malformed_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test that failed ingestion rolls back all rows."""
        from src.csv_postgres_pipeline.exceptions import MalformedRowError
        from src.csv_postgres_pipeline.ingestion import ingest
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=malformed_csv_file,
            table_name="test_rollback_table",
            row_mode="strict",
        )

        # Attempt ingestion that will fail
        with pytest.raises(MalformedRowError):
            ingest(db_config, csv_config)

        # Verify no data was committed (table should be empty or not exist)
        # This requires checking the database directly
        from src.csv_postgres_pipeline.database import create_connection, get_table_schema

        with create_connection(db_config) as conn:
            schema = get_table_schema(conn, "test_rollback_table")
            # Table either doesn't exist or has no rows
            if schema is not None:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM test_rollback_table")
                    result = cur.fetchone()
                    assert result is not None
                    count = result[0]
                    assert count == 0


@pytest.mark.integration
class TestLargeFileHandling:
    """Integration tests for large file handling (T046) - memory bounded streaming."""

    def test_ingest_streaming_function_exists(self) -> None:
        """Test that ingest_streaming function exists."""
        from src.csv_postgres_pipeline.ingestion import ingest_streaming

        assert ingest_streaming is not None

    def test_ingest_streaming_large_file(
        self,
        large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test streaming ingestion handles large files efficiently."""
        from src.csv_postgres_pipeline.ingestion import ingest_streaming
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=large_csv_file,
            table_name="test_large_streaming",
            chunk_size=1000,
        )

        result = ingest_streaming(db_config, csv_config)

        assert result.status == "success"
        assert result.rows_inserted == 10000

    def test_ingest_streaming_memory_bounded(
        self,
        large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test streaming ingestion stays within memory bounds.

        Note: This test verifies that peak memory stays below 100MB
        even for large files (the large_csv_file fixture has 10000 rows).
        """
        import tracemalloc

        from src.csv_postgres_pipeline.ingestion import ingest_streaming
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=large_csv_file,
            table_name="test_memory_bounded",
            chunk_size=500,  # Smaller chunks for memory efficiency
        )

        # Track memory usage
        tracemalloc.start()

        result = ingest_streaming(db_config, csv_config)

        # Get peak memory usage
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)

        assert result.status == "success"
        assert result.rows_inserted == 10000
        # Peak memory should be well under 100MB for this test file
        # Using a generous limit since the file is only ~400KB
        assert peak_mb < 50, f"Peak memory usage was {peak_mb:.2f}MB"

    def test_ingest_streaming_with_validation(
        self,
        malformed_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test streaming ingestion with row validation in skip mode."""
        from src.csv_postgres_pipeline.ingestion import ingest_streaming
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=malformed_csv_file,
            table_name="test_streaming_skip",
            row_mode="skip",
            chunk_size=100,
        )

        result = ingest_streaming(db_config, csv_config)

        assert result.status == "partial"
        assert result.rows_inserted == 1
        assert result.rows_skipped == 2

    def test_ingest_streaming_tracks_progress(
        self,
        large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test streaming ingestion can track progress via callback."""
        from src.csv_postgres_pipeline.ingestion import ingest_streaming
        from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_config = CSVConfig(
            file_path=large_csv_file,
            table_name="test_progress_tracking",
            chunk_size=1000,
        )

        progress_updates: list[int] = []

        def on_progress(rows_processed: int) -> None:
            progress_updates.append(rows_processed)

        result = ingest_streaming(db_config, csv_config, progress_callback=on_progress)

        assert result.status == "success"
        # Should have received multiple progress updates
        assert len(progress_updates) > 0
        # Final update should match total rows
        assert progress_updates[-1] == 10000
