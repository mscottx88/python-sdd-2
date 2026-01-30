"""Pydantic models for CSV Postgres Pipeline.

Defines configuration, result, and schema models with validation.
All models use Pydantic v2 for type safety and validation per constitution.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import ParseResult, urlparse

from pydantic import BaseModel, Field, SecretStr


def _get_env_port() -> int:
    """Get port from PGPORT environment variable or return default."""
    port_str: str = os.environ.get("PGPORT", "") or "5432"
    try:
        return int(port_str)
    except ValueError:
        return 5432


class DatabaseConfig(BaseModel):
    """PostgreSQL connection configuration.

    Attributes:
        host: Database server hostname (defaults to PGHOST env var or localhost).
        port: Database server port (defaults to PGPORT env var or 5432).
        database: Database name (defaults to PGDATABASE env var).
        user: Database username (defaults to PGUSER env var).
        password: Database password (defaults to PGPASSWORD env var).
        pool_min_size: Minimum connections in pool.
        pool_max_size: Maximum connections in pool.
        pool_timeout: Connection timeout in seconds.
    """

    host: str = Field(
        default_factory=lambda: os.environ.get("PGHOST", "") or "localhost",
        description="Database host",
    )
    port: int = Field(
        default_factory=_get_env_port,
        ge=1,
        le=65535,
        description="Database port",
    )
    database: str = Field(
        default_factory=lambda: os.environ.get("PGDATABASE", "") or "",
        min_length=1,
        description="Database name",
    )
    user: str = Field(
        default_factory=lambda: os.environ.get("PGUSER", "") or "",
        min_length=1,
        description="Database user",
    )
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(os.environ.get("PGPASSWORD", "") or ""),
        description="Database password",
    )

    # Connection pool settings
    pool_min_size: int = Field(default=1, ge=1, le=10)
    pool_max_size: int = Field(default=5, ge=1, le=50)
    pool_timeout: float = Field(default=30.0, gt=0, description="Connection timeout in seconds")

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string.

        Returns:
            Connection URL in postgresql:// format.
        """
        # pylint: disable=no-member  # JUSTIFICATION: Pylint doesn't recognize Pydantic SecretStr.get_secret_value() method
        return (
            f"postgresql://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )
        # pylint: enable=no-member

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        pool_min_size: int = 1,
        pool_max_size: int = 5,
        pool_timeout: float = 30.0,
    ) -> "DatabaseConfig":
        """Create DatabaseConfig from a connection URL.

        Args:
            url: PostgreSQL connection URL (postgresql://user:pass@host:port/db).
            pool_min_size: Minimum pool connections.
            pool_max_size: Maximum pool connections.
            pool_timeout: Connection timeout.

        Returns:
            DatabaseConfig instance.
        """
        parsed: ParseResult = urlparse(url)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=(parsed.path or "/").lstrip("/"),
            user=parsed.username or "",
            password=SecretStr(parsed.password or ""),
            pool_min_size=pool_min_size,
            pool_max_size=pool_max_size,
            pool_timeout=pool_timeout,
        )


class CSVConfig(BaseModel):
    """CSV file configuration and handling options.

    Attributes:
        file_path: Path to the CSV file.
        table_name: Target PostgreSQL table name.
        schema_mode: How to handle schema mismatches.
        row_mode: How to handle malformed rows.
        empty_mode: How to handle empty files.
        chunk_size: Rows per chunk for streaming.
        encoding: File character encoding.
        delimiter: Field delimiter character.
    """

    file_path: Path = Field(..., description="Path to CSV file")
    table_name: str = Field(..., min_length=1, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    # Handling modes (per clarifications)
    schema_mode: Literal["strict", "match", "alter"] = Field(
        default="strict",
        description=(
            "Schema mismatch handling: strict=fail, match=common columns, alter=add columns"
        ),
    )
    row_mode: Literal["strict", "skip", "lenient"] = Field(
        default="strict",
        description=(
            "Malformed row handling: strict=fail, skip=log and continue, lenient=pad/truncate"
        ),
    )
    empty_mode: Literal["strict", "headers", "permissive"] = Field(
        default="strict",
        description=(
            "Empty file handling: "
            "strict=fail, headers=allow headers-only, permissive=always succeed"
        ),
    )

    # Processing options
    chunk_size: int = Field(default=1000, ge=100, le=100000, description="Rows per chunk")
    encoding: str = Field(default="utf-8", description="File encoding")
    delimiter: str = Field(default=",", max_length=1, description="Field delimiter")


class SkippedRow(BaseModel):
    """Information about a skipped row during ingestion.

    Attributes:
        line_number: Line number in the CSV file (1-indexed).
        reason: Why the row was skipped.
        raw_content: Optional raw content of the skipped row.
    """

    line_number: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)
    raw_content: str | None = Field(default=None, max_length=1000)


class IngestionResult(BaseModel):
    """Result of a CSV ingestion operation.

    Attributes:
        status: Overall status (success, partial, failed).
        rows_processed: Total rows read from CSV.
        rows_inserted: Rows successfully inserted.
        rows_skipped: Rows skipped (in skip mode).
        skipped_rows: Details of skipped rows.
        table_name: Target table name.
        table_created: Whether table was created.
        columns_added: Columns added (in alter mode).
        started_at: When ingestion started.
        completed_at: When ingestion completed.
        duration_seconds: Total duration.
        peak_memory_mb: Peak memory usage (verbose mode).
        throughput_rows_per_sec: Processing rate (verbose mode).
        error_message: Error description if failed.
    """

    status: Literal["success", "partial", "failed"] = Field(...)
    rows_processed: int = Field(..., ge=0)
    rows_inserted: int = Field(..., ge=0)
    rows_skipped: int = Field(default=0, ge=0)
    skipped_rows: list[SkippedRow] | None = Field(default=None)

    table_name: str | None = Field(default=None)
    table_created: bool = Field(default=False)
    columns_added: list[str] = Field(default_factory=list)

    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: float = Field(default=0.0, ge=0)

    # Memory/performance stats (for verbose mode)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    throughput_rows_per_sec: float | None = Field(default=None, ge=0)

    error_message: str | None = Field(default=None)


class ColumnInfo(BaseModel):
    """Information about a table column.

    Attributes:
        name: Column name.
        data_type: PostgreSQL data type.
        nullable: Whether column allows NULL.
        ordinal_position: Column position (1-indexed).
    """

    name: str = Field(..., min_length=1)
    data_type: str = Field(default="TEXT")
    nullable: bool = Field(default=True)
    ordinal_position: int = Field(default=0, ge=0)


class TableSchema(BaseModel):
    """Schema information for a PostgreSQL table.

    Attributes:
        table_name: Name of the table.
        columns: List of column definitions.
        exists: Whether the table exists.
    """

    table_name: str = Field(...)
    columns: list[ColumnInfo] = Field(default_factory=list)
    exists: bool = Field(default=False)

    def get_column_names(self) -> list[str]:
        """Return ordered list of column names.

        Returns:
            Column names sorted by ordinal position.
        """
        return [col.name for col in sorted(self.columns, key=lambda c: c.ordinal_position)]

    def has_column(self, name: str) -> bool:
        """Check if column exists (case-insensitive).

        Args:
            name: Column name to check.

        Returns:
            True if column exists, False otherwise.
        """
        return any(col.name.lower() == name.lower() for col in self.columns)
