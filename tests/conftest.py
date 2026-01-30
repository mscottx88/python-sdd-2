"""Shared pytest fixtures for CSV Postgres Pipeline tests."""

import csv
import os
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, TypedDict

import pytest
from dotenv import load_dotenv
from pydantic import SecretStr

from src.csv_postgres_pipeline.models import DatabaseConfig

# Load environment variables from .env file for all tests
load_dotenv()


class DBConnectionParams(TypedDict):
    """Type-safe database connection parameters."""

    host: str
    port: int
    database: str
    user: str
    password: str


def is_docker_running() -> bool:
    """Check if Docker Desktop is running and accessible."""
    try:
        result: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603
            ["docker", "info"],  # noqa: S607
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_postgres_container_running() -> bool:
    """Check if a PostgreSQL container is running and healthy."""
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "docker",
                "ps",
                "--filter",
                "ancestor=postgres",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def docker_available() -> bool:
    """Session-scoped fixture to check Docker availability.

    If SKIP_DOCKER_CHECK environment variable is set to a truthy value,
    skips the Docker check and returns True. This is useful in CI/CD
    environments where PostgreSQL is provided as a service.
    """
    skip_check: str = os.environ.get("SKIP_DOCKER_CHECK", "").lower()
    if skip_check in ("true", "1", "yes"):
        return True
    return is_docker_running()


@pytest.fixture(scope="session")
def postgres_available(docker_available: bool) -> bool:  # pylint: disable=redefined-outer-name
    """Session-scoped fixture to check PostgreSQL container availability.

    If SKIP_DOCKER_CHECK environment variable is set to a truthy value,
    skips the Docker check and returns True. This is useful in CI/CD
    environments where PostgreSQL is provided as a service.
    """
    skip_check: str = os.environ.get("SKIP_DOCKER_CHECK", "").lower()
    if skip_check in ("true", "1", "yes"):
        return True
    if not docker_available:
        return False
    return is_postgres_container_running()


@pytest.fixture
def sample_csv_file() -> Generator[Path]:
    """Create a temporary CSV file with sample data."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        writer: Any = csv.writer(f)  # csv.writer returns internal _writer type
        writer.writerow(["id", "name", "email"])
        writer.writerow(["1", "Alice", "alice@example.com"])
        writer.writerow(["2", "Bob", "bob@example.com"])
        writer.writerow(["3", "Charlie", "charlie@example.com"])
        temp_path: Path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def empty_csv_file() -> Generator[Path]:
    """Create a completely empty CSV file."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        temp_path: Path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def headers_only_csv_file() -> Generator[Path]:
    """Create a CSV file with headers but no data rows."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        writer: Any = csv.writer(f)  # csv.writer returns internal _writer type
        writer.writerow(["id", "name", "email"])
        temp_path: Path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def malformed_csv_file() -> Generator[Path]:
    """Create a CSV file with inconsistent column counts."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        writer: Any = csv.writer(f)  # csv.writer returns internal _writer type
        writer.writerow(["id", "name", "email"])
        writer.writerow(["1", "Alice", "alice@example.com"])
        writer.writerow(["2", "Bob"])  # Missing email column
        writer.writerow(["3", "Charlie", "charlie@example.com", "extra"])  # Extra column
        temp_path: Path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def large_csv_file() -> Generator[Path]:
    """Create a larger CSV file for performance testing."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8",
    ) as f:
        writer: Any = csv.writer(f)  # csv.writer returns internal _writer type
        writer.writerow(["id", "name", "email", "department"])
        for i in range(10000):
            writer.writerow(
                [
                    str(i),
                    f"User_{i}",
                    f"user{i}@example.com",
                    f"Dept_{i % 10}",
                ]
            )
        temp_path: Path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def db_connection_params() -> DBConnectionParams:
    """Return database connection parameters from environment or defaults."""
    return DBConnectionParams(
        host=os.environ.get("PGHOST", "localhost") or "localhost",
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "testdb") or "testdb",
        user=os.environ.get("PGUSER", "postgres") or "postgres",
        password=os.environ.get("PGPASSWORD", "postgres") or "postgres",
    )


@pytest.fixture
def db_config(
    db_connection_params: DBConnectionParams,  # pylint: disable=redefined-outer-name
) -> DatabaseConfig:
    """Return DatabaseConfig instance from connection parameters.

    This fixture provides a properly typed DatabaseConfig for tests,
    avoiding mypy issues with dict unpacking.
    """
    return DatabaseConfig(
        host=db_connection_params["host"],
        port=db_connection_params["port"],
        database=db_connection_params["database"],
        user=db_connection_params["user"],
        password=SecretStr(db_connection_params["password"]),
    )
