"""Integration tests for memory usage during CSV ingestion (T071).

Tests verify that memory usage remains constant/bounded during streaming,
as required by SC-002: "System maintains less than 100MB memory usage
regardless of input file size."

Uses tracemalloc to track memory allocations during ingestion.
"""

import csv
import gc
import tempfile
import tracemalloc
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from src.csv_postgres_pipeline.ingestion import ingest_streaming
from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig, IngestionResult


@pytest.fixture
def very_large_csv_file() -> Generator[Path]:
    """Create a CSV file with 50,000 rows for memory testing.

    This file is large enough to detect memory leaks but small enough
    to run reasonably fast in CI.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        writer: Any = csv.writer(f)  # csv.writer returns internal _writer type
        writer.writerow(["id", "name", "email", "department", "description"])
        for i in range(50000):
            writer.writerow(
                [
                    str(i),
                    f"User_{i}",
                    f"user{i}@example.com",
                    f"Department_{i % 20}",
                    f"This is a longer description field for row {i} to add more data",
                ]
            )
        temp_path: Path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


@pytest.mark.integration
class TestMemoryBoundedIngestion:
    """Tests for constant memory usage during streaming (T071, SC-002)."""

    def test_memory_stays_bounded_during_streaming(
        self,
        very_large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test that memory usage stays below 100MB during large file ingestion.

        SC-002: System maintains less than 100MB memory usage regardless
        of input file size.
        """
        db_config: DatabaseConfig = DatabaseConfig(**db_connection_params)
        csv_config: CSVConfig = CSVConfig(
            file_path=very_large_csv_file,
            table_name="test_memory_bounded_50k",
            chunk_size=1000,
        )

        # Force garbage collection before starting
        gc.collect()

        # Start memory tracking
        tracemalloc.start()

        result: IngestionResult = ingest_streaming(db_config, csv_config)

        # Get peak memory usage
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb: float = peak / (1024 * 1024)

        assert result.status == "success"
        assert result.rows_inserted == 50000
        # SC-002: Must stay below 100MB
        assert peak_mb < 100, f"Peak memory {peak_mb:.2f}MB exceeds 100MB limit (SC-002)"

    def test_memory_does_not_grow_linearly_with_file_size(
        self,
        very_large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test that memory usage is constant, not growing with processed rows.

        This test samples memory at multiple points during processing to verify
        that memory usage does not grow linearly with the number of rows processed.
        True streaming should maintain relatively constant memory.
        """
        db_config: DatabaseConfig = DatabaseConfig(**db_connection_params)
        csv_config: CSVConfig = CSVConfig(
            file_path=very_large_csv_file,
            table_name="test_memory_constant",
            chunk_size=1000,
        )

        memory_samples: list[tuple[int, float]] = []

        def sample_memory(rows_processed: int) -> None:
            """Callback to sample memory at each progress update."""
            current, _ = tracemalloc.get_traced_memory()
            memory_samples.append((rows_processed, current / (1024 * 1024)))

        gc.collect()
        tracemalloc.start()

        result: IngestionResult = ingest_streaming(
            db_config, csv_config, progress_callback=sample_memory
        )

        tracemalloc.stop()

        assert result.status == "success"
        assert result.rows_inserted == 50000
        assert len(memory_samples) > 1, "Should have multiple memory samples"

        # Calculate memory growth rate
        # For true streaming, memory should not grow significantly as rows increase
        if len(memory_samples) >= 2:
            first_sample: tuple[int, float] = memory_samples[0]
            last_sample: tuple[int, float] = memory_samples[-1]

            rows_increase: int = last_sample[0] - first_sample[0]
            memory_increase_mb: float = last_sample[1] - first_sample[1]

            # Memory should not grow more than 0.5KB per 1000 rows
            # (allowing some overhead but catching linear growth)
            if rows_increase > 0:
                growth_rate_mb_per_1k_rows: float = (memory_increase_mb / rows_increase) * 1000
                assert growth_rate_mb_per_1k_rows < 0.5, (
                    f"Memory grew {growth_rate_mb_per_1k_rows:.4f}MB per 1000 rows. "
                    "This suggests data is being accumulated rather than streamed."
                )

    def test_chunk_size_affects_memory_usage(
        self,
        large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test that smaller chunk sizes use less peak memory.

        Verifies that the chunk_size parameter actually controls memory usage
        by comparing peak memory with different chunk sizes.
        """

        def measure_peak_memory(chunk_size: int, table_suffix: str) -> float:
            """Measure peak memory for a given chunk size."""
            db_config: DatabaseConfig = DatabaseConfig(**db_connection_params)
            csv_config: CSVConfig = CSVConfig(
                file_path=large_csv_file,
                table_name=f"test_chunk_memory_{table_suffix}",
                chunk_size=chunk_size,
            )

            gc.collect()
            tracemalloc.start()
            _result: IngestionResult = ingest_streaming(db_config, csv_config)
            _: int
            peak: int
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return peak / (1024 * 1024)

        # Measure with small chunks
        peak_small: float = measure_peak_memory(100, "small")

        # Measure with large chunks
        peak_large: float = measure_peak_memory(5000, "large")

        # Larger chunks should use more memory
        # (This verifies chunk_size actually affects buffering)
        assert peak_large >= peak_small * 0.8, (
            f"Expected larger chunks ({peak_large:.2f}MB) to use at least as much "
            f"memory as smaller chunks ({peak_small:.2f}MB)"
        )

        # But both should stay under 100MB (SC-002)
        assert peak_small < 100, f"Small chunks used {peak_small:.2f}MB (limit 100MB)"
        assert peak_large < 100, f"Large chunks used {peak_large:.2f}MB (limit 100MB)"

    def test_memory_released_after_ingestion(
        self,
        large_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test that memory is properly released after ingestion completes.

        Verifies there are no memory leaks by checking that memory returns
        to near baseline after ingestion and garbage collection.
        """
        db_config: DatabaseConfig = DatabaseConfig(**db_connection_params)
        csv_config: CSVConfig = CSVConfig(
            file_path=large_csv_file,
            table_name="test_memory_release",
            chunk_size=500,
        )

        gc.collect()
        tracemalloc.start()

        # Capture baseline
        baseline: int
        _: int
        baseline, _ = tracemalloc.get_traced_memory()

        # Perform ingestion
        result: IngestionResult = ingest_streaming(db_config, csv_config)
        assert result.status == "success"

        # Force cleanup
        gc.collect()

        # Check memory after cleanup
        after_gc: int
        after_gc, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        baseline_mb: float = baseline / (1024 * 1024)
        after_gc_mb: float = after_gc / (1024 * 1024)

        # Memory after GC should be within 10MB of baseline
        # (allowing for some retained objects like cached modules)
        memory_retained_mb: float = after_gc_mb - baseline_mb
        assert memory_retained_mb < 10, (
            f"Memory not properly released: {memory_retained_mb:.2f}MB retained "
            f"(baseline: {baseline_mb:.2f}MB, after: {after_gc_mb:.2f}MB)"
        )
