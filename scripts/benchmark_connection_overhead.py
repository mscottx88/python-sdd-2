"""Benchmark script for measuring connection overhead reduction with pooling.

This script validates SC-007: "Connection pool reduces connection overhead by 50%
for sequential operations."

Requirements:
- Docker Desktop running
- PostgreSQL container accessible at localhost:5432
- Test database and user configured (via environment variables)

Usage:
    python scripts/benchmark_connection_overhead.py

Environment Variables:
    PGHOST - PostgreSQL host (default: localhost)
    PGPORT - PostgreSQL port (default: 5432)
    PGDATABASE - Database name (required)
    PGUSER - Database user (required)
    PGPASSWORD - Database password (required)
"""

import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import SecretStr

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.csv_postgres_pipeline.database import close_pool, create_pool
from src.csv_postgres_pipeline.ingestion import ingest, ingest_streaming
from src.csv_postgres_pipeline.models import CSVConfig, DatabaseConfig


def create_test_csv(file_path: Path, rows: int = 100) -> None:
    """Create a small test CSV file for benchmarking.

    Args:
        file_path: Path where CSV will be created.
        rows: Number of data rows to generate.
    """
    with file_path.open("w", encoding="utf-8") as f:
        # Write header
        f.write("id,name,email,value\n")
        # Write data rows
        for i in range(rows):
            f.write(f"{i},User{i},user{i}@example.com,{i * 100}\n")


def benchmark_without_pooling(
    db_config: DatabaseConfig,
    csv_file: Path,
    iterations: int = 10,
) -> tuple[float, list[float]]:
    """Measure connection time WITHOUT pooling (baseline).

    Args:
        db_config: Database configuration.
        csv_file: Path to test CSV file.
        iterations: Number of sequential ingestions to perform.

    Returns:
        Tuple of (total_time_seconds, list_of_individual_times).
    """
    table_name = "benchmark_no_pool"
    times: list[float] = []

    print(f"\n🔍 Benchmarking WITHOUT pooling ({iterations} iterations)...")

    for i in range(iterations):
        csv_config = CSVConfig(
            file_path=csv_file,
            table_name=f"{table_name}_{i}",  # Unique table per iteration
            schema_mode="strict",
            row_mode="strict",
            empty_mode="strict",
            chunk_size=1000,
        )

        start = time.perf_counter()
        result = ingest(db_config, csv_config)
        elapsed = time.perf_counter() - start

        times.append(elapsed)
        print(f"  Iteration {i + 1}: {elapsed:.4f}s ({result.rows_inserted} rows)")

    total_time = sum(times)
    avg_time = statistics.mean(times)
    print(f"✅ Total time: {total_time:.4f}s (avg: {avg_time:.4f}s per operation)")

    return total_time, times


def benchmark_with_pooling(
    db_config: DatabaseConfig,
    csv_file: Path,
    iterations: int = 10,
) -> tuple[float, list[float]]:
    """Measure connection time WITH pooling.

    Args:
        db_config: Database configuration.
        csv_file: Path to test CSV file.
        iterations: Number of sequential ingestions to perform.

    Returns:
        Tuple of (total_time_seconds, list_of_individual_times).
    """
    table_name = "benchmark_with_pool"
    times: list[float] = []

    print(f"\n🔍 Benchmarking WITH pooling ({iterations} iterations)...")

    # Create connection pool once
    pool = create_pool(db_config)

    try:
        for i in range(iterations):
            csv_config = CSVConfig(
                file_path=csv_file,
                table_name=f"{table_name}_{i}",  # Unique table per iteration
                schema_mode="strict",
                row_mode="strict",
                empty_mode="strict",
                chunk_size=1000,
            )

            start = time.perf_counter()
            result = ingest_streaming(db_config, csv_config, pool=pool)
            elapsed = time.perf_counter() - start

            times.append(elapsed)
            print(f"  Iteration {i + 1}: {elapsed:.4f}s ({result.rows_inserted} rows)")
    finally:
        close_pool(pool)

    total_time = sum(times)
    avg_time = statistics.mean(times)
    print(f"✅ Total time: {total_time:.4f}s (avg: {avg_time:.4f}s per operation)")

    return total_time, times


def calculate_improvement(
    baseline_time: float,
    pooled_time: float,
) -> tuple[float, float, Literal["PASS", "FAIL"]]:
    """Calculate connection overhead reduction percentage.

    Args:
        baseline_time: Total time without pooling.
        pooled_time: Total time with pooling.

    Returns:
        Tuple of (reduction_seconds, reduction_percentage, pass_fail_status).
    """
    reduction_seconds = baseline_time - pooled_time
    reduction_percentage = (reduction_seconds / baseline_time) * 100

    status: Literal["PASS", "FAIL"] = "PASS" if reduction_percentage >= 50.0 else "FAIL"

    return reduction_seconds, reduction_percentage, status


def main() -> int:
    """Run connection overhead benchmark.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("=" * 70)
    print("Connection Overhead Reduction Benchmark (SC-007)")
    print("=" * 70)

    # Build database config from environment
    try:
        db_config = DatabaseConfig(
            host=os.getenv("PGHOST", "localhost") or "localhost",
            port=int(os.getenv("PGPORT", "5432")),
            database=os.getenv("PGDATABASE") or "",
            user=os.getenv("PGUSER") or "",
            password=SecretStr(os.getenv("PGPASSWORD", "")),
            pool_max_size=10,
        )
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nRequired environment variables:")
        print("  PGDATABASE - Database name")
        print("  PGUSER - Database user")
        print("  PGPASSWORD - Database password (optional)")
        return 1

    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        csv_path = Path(tmp.name)

    try:
        # Create test CSV with 100 rows
        print("\n📝 Creating test CSV file (100 rows)...")
        create_test_csv(csv_path, rows=100)
        print(f"✅ Test CSV created: {csv_path}")

        # Benchmark without pooling (baseline)
        baseline_time, baseline_times = benchmark_without_pooling(
            db_config,
            csv_path,
            iterations=10,
        )

        # Benchmark with pooling
        pooled_time, pooled_times = benchmark_with_pooling(
            db_config,
            csv_path,
            iterations=10,
        )

        # Calculate improvement
        reduction_seconds, reduction_percentage, status = calculate_improvement(
            baseline_time,
            pooled_time,
        )

        # Display results
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)
        print(f"\n{'Metric':<40} {'Without Pool':<15} {'With Pool':<15}")
        print("-" * 70)
        print(f"{'Total Time':<40} {baseline_time:.4f}s{'':<10} {pooled_time:.4f}s")
        print(
            f"{'Average Time per Operation':<40} "
            f"{statistics.mean(baseline_times):.4f}s{'':<10} "
            f"{statistics.mean(pooled_times):.4f}s"
        )
        print(
            f"{'Std Dev':<40} "
            f"{statistics.stdev(baseline_times):.4f}s{'':<10} "
            f"{statistics.stdev(pooled_times):.4f}s"
        )

        print("\n" + "=" * 70)
        print(f"⚡ Connection Overhead Reduction: {reduction_seconds:.4f}s")
        print(f"📊 Percentage Improvement: {reduction_percentage:.2f}%")
        print("🎯 Target: ≥50% reduction")

        if status == "PASS":
            print(f"✅ Status: {status} - Connection pooling achieves target!")
            print("=" * 70)
            return 0
        else:
            print(
                f"❌ Status: {status} - Connection pooling below 50% target "
                f"({reduction_percentage:.2f}%)"
            )
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if csv_path.exists():
            csv_path.unlink()
            print(f"\n🧹 Cleaned up test CSV: {csv_path}")


if __name__ == "__main__":
    import os

    sys.exit(main())
