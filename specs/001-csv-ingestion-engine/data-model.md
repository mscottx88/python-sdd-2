# Data Model: CSV Ingestion Engine

**Phase**: 1 (Design)
**Date**: 2026-01-27
**Branch**: `001-csv-ingestion-engine`

## Overview

All data models use Pydantic v2 for validation, serialization, and type safety per constitution requirements.

## Core Entities

### 1. DatabaseConfig

Configuration for PostgreSQL connection.

```python
from pydantic import BaseModel, Field, SecretStr
from typing import Literal

class DatabaseConfig(BaseModel):
    """PostgreSQL connection configuration."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(..., min_length=1, description="Database name")
    user: str = Field(..., min_length=1, description="Database user")
    password: SecretStr = Field(..., description="Database password")

    # Connection pool settings
    pool_min_size: int = Field(default=1, ge=1, le=10)
    pool_max_size: int = Field(default=5, ge=1, le=50)
    pool_timeout: float = Field(default=30.0, gt=0, description="Connection timeout in seconds")

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"
```

**Validation Rules**:
- `port`: 1-65535 (valid port range)
- `database`, `user`: non-empty strings
- `pool_min_size`: 1-10, must be <= pool_max_size
- `pool_max_size`: 1-50
- `pool_timeout`: positive float

### 2. CSVConfig

Configuration for CSV parsing and handling modes.

```python
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal

class CSVConfig(BaseModel):
    """CSV file configuration and handling options."""

    file_path: Path = Field(..., description="Path to CSV file")
    table_name: str = Field(..., min_length=1, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    # Handling modes (per clarifications)
    schema_mode: Literal["strict", "match", "alter"] = Field(
        default="strict",
        description="Schema mismatch handling: strict=fail, match=common columns, alter=add columns"
    )
    row_mode: Literal["strict", "skip", "lenient"] = Field(
        default="strict",
        description="Malformed row handling: strict=fail, skip=log and continue, lenient=pad/truncate"
    )
    empty_mode: Literal["strict", "headers", "permissive"] = Field(
        default="strict",
        description="Empty file handling: strict=fail, headers=allow headers-only, permissive=always succeed"
    )

    # Processing options
    chunk_size: int = Field(default=1000, ge=100, le=100000, description="Rows per chunk")
    encoding: str = Field(default="utf-8", description="File encoding")
    delimiter: str = Field(default=",", max_length=1, description="Field delimiter")
```

**Validation Rules**:
- `file_path`: Must exist and be readable (validated at runtime)
- `table_name`: Valid PostgreSQL identifier (alphanumeric + underscore, starts with letter/underscore)
- `chunk_size`: 100-100,000 rows per chunk
- `delimiter`: Single character

### 3. IngestionResult

Result of a completed ingestion operation.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class SkippedRow(BaseModel):
    """Information about a skipped row."""
    line_number: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)
    raw_content: str | None = Field(default=None, max_length=1000)

class IngestionResult(BaseModel):
    """Result of CSV ingestion operation."""

    status: Literal["success", "partial", "failed"] = Field(...)
    rows_processed: int = Field(..., ge=0)
    rows_inserted: int = Field(..., ge=0)
    rows_skipped: int = Field(default=0, ge=0)
    skipped_rows: list[SkippedRow] = Field(default_factory=list)

    table_name: str = Field(...)
    table_created: bool = Field(default=False)
    columns_added: list[str] = Field(default_factory=list)  # For "alter" mode

    started_at: datetime = Field(...)
    completed_at: datetime = Field(...)
    duration_seconds: float = Field(..., ge=0)

    # Memory/performance stats (for verbose mode)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    throughput_rows_per_sec: float | None = Field(default=None, ge=0)

    error_message: str | None = Field(default=None)
```

**State Transitions**:
- `status="success"`: All rows inserted, no errors
- `status="partial"`: Some rows skipped (only in "skip" mode)
- `status="failed"`: Ingestion aborted, transaction rolled back

### 4. TableSchema

Represents the schema of a target table.

```python
from pydantic import BaseModel, Field

class ColumnInfo(BaseModel):
    """Information about a table column."""
    name: str = Field(..., min_length=1)
    data_type: str = Field(default="TEXT")
    nullable: bool = Field(default=True)
    ordinal_position: int = Field(..., ge=1)

class TableSchema(BaseModel):
    """Schema information for a PostgreSQL table."""

    table_name: str = Field(...)
    columns: list[ColumnInfo] = Field(default_factory=list)
    exists: bool = Field(default=False)

    def get_column_names(self) -> list[str]:
        """Return ordered list of column names."""
        return [col.name for col in sorted(self.columns, key=lambda c: c.ordinal_position)]

    def has_column(self, name: str) -> bool:
        """Check if column exists (case-insensitive)."""
        return any(col.name.lower() == name.lower() for col in self.columns)
```

## Entity Relationships

```
┌─────────────────┐
│  DatabaseConfig │
└────────┬────────┘
         │ configures
         ▼
┌─────────────────┐     validates against     ┌─────────────────┐
│  CSVConfig      │◄─────────────────────────►│  TableSchema    │
└────────┬────────┘                           └─────────────────┘
         │ produces
         ▼
┌─────────────────┐
│IngestionResult  │
│  └─SkippedRow[] │
└─────────────────┘
```

## Validation Summary

| Entity | Key Validations |
|--------|-----------------|
| DatabaseConfig | Port range, non-empty credentials, pool size limits |
| CSVConfig | Valid table identifier, mode enums, chunk size bounds |
| IngestionResult | Non-negative counts, valid status enum |
| TableSchema | Column ordering, case-insensitive lookup |

## Error Types

```python
class IngestionError(Exception):
    """Base exception for all ingestion errors."""
    pass

class CSVError(IngestionError):
    """CSV-related errors."""
    file_path: Path
    line_number: int | None = None

class EmptyFileError(CSVError):
    """CSV file is empty or headers-only when not permitted."""
    pass

class MalformedRowError(CSVError):
    """CSV row has incorrect column count."""
    expected_columns: int
    actual_columns: int

class DatabaseError(IngestionError):
    """Database-related errors."""
    pass

class ConnectionError(DatabaseError):
    """Cannot connect to database."""
    pass

class SchemaMismatchError(DatabaseError):
    """Table schema doesn't match CSV headers."""
    csv_columns: list[str]
    table_columns: list[str]
    missing_in_table: list[str]
    missing_in_csv: list[str]

class TransactionError(DatabaseError):
    """Transaction failed and was rolled back."""
    pass
```
