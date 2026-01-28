# Research: CSV Ingestion Engine

**Phase**: 0 (Research)
**Date**: 2026-01-27
**Branch**: `001-csv-ingestion-engine`

## Research Questions

### 1. PostgreSQL Driver Selection

**Decision**: psycopg 3.x (psycopg[pool])

**Rationale**:
- Native support for PostgreSQL COPY protocol via `cursor.copy()` API
- Built-in connection pooling via `psycopg_pool.ConnectionPool`
- Modern async support (not needed for CLI but available)
- Type stubs included for mypy strict mode compatibility
- Active development, Python 3.13 compatible

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| psycopg2 | Legacy, no native async, separate pool library needed |
| asyncpg | Async-only, overkill for CLI tool, complex COPY API |
| SQLAlchemy | ORM overhead unnecessary, COPY support requires raw connection |

### 2. CLI Framework Selection

**Decision**: click

**Rationale**:
- Mature, well-documented CLI framework
- Excellent type hints support
- Built-in support for environment variables
- Simple decorator-based API
- No external dependencies beyond standard library

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| typer | Built on click, adds typing magic that can conflict with mypy strict |
| argparse | Verbose, less intuitive API, manual env var handling |
| fire | Auto-generates CLI from functions, less control over UX |

### 3. Streaming CSV Implementation

**Decision**: Python built-in `csv` module with chunked reading

**Rationale**:
- Standard library, no additional dependencies
- Handles quoted fields, escaping per RFC 4180
- Memory-efficient when combined with file iteration
- Universal newline support (handles LF and CRLF per constitution)
- Type stubs available for mypy

**Implementation Pattern**:
```python
def stream_csv(file_path: Path, chunk_size: int = 1000) -> Iterator[list[list[str]]]:
    """Yield chunks of rows from CSV file without loading entire file."""
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        chunk: list[list[str]] = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
```

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| pandas | Heavy dependency, loads entire file by default, overkill |
| polars | Rust dependency, complex build, unnecessary for simple CSV |
| aiofiles | Async not needed for single-file CLI tool |

### 4. COPY Protocol Implementation

**Decision**: psycopg3 `cursor.copy()` with `COPY FROM STDIN`

**Rationale**:
- Most efficient bulk loading method for PostgreSQL
- Streams data directly to server without intermediate storage
- Supports transaction semantics (rollback on failure)
- Native support in psycopg3

**Implementation Pattern**:
```python
def copy_to_table(
    conn: Connection,
    table_name: str,
    columns: list[str],
    rows: Iterator[list[str]]
) -> int:
    """Stream rows to PostgreSQL using COPY protocol."""
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table_name} ({','.join(columns)}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
    return cur.rowcount
```

### 5. Connection Pooling Strategy

**Decision**: psycopg_pool.ConnectionPool with min=1, max=5

**Rationale**:
- Single-user CLI tool doesn't need large pool
- min=1 ensures one connection ready immediately
- max=5 allows for potential future concurrent operations
- Pool handles connection health checks automatically

**Configuration**:
```python
pool = ConnectionPool(
    conninfo=connection_string,
    min_size=1,
    max_size=5,
    timeout=30.0,  # seconds to wait for connection
)
```

### 6. Progress Bar Implementation

**Decision**: rich.progress for "normal" verbosity mode

**Rationale**:
- Modern, beautiful terminal output
- Built-in progress bar with transfer rate display
- Minimal overhead
- Falls back gracefully in non-TTY environments

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| tqdm | Less visual appeal, similar functionality |
| click.progressbar | Basic, less informative |
| custom print | Poor UX, no rate estimation |

### 7. Error Handling Architecture

**Decision**: Custom exception hierarchy with context

**Rationale**:
- Enables specific error handling per FR-011
- Preserves context (file path, line number, column)
- Maps to clear user-facing error messages

**Exception Hierarchy**:
```
IngestionError (base)
├── CSVError
│   ├── FileNotFoundError
│   ├── EmptyFileError
│   └── MalformedRowError
├── DatabaseError
│   ├── ConnectionError
│   ├── SchemaMismatchError
│   └── TransactionError
└── ConfigurationError
```

## Technology Stack Summary

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.13 |
| Database Driver | psycopg[pool] | 3.x |
| Data Validation | Pydantic | 2.x |
| CLI Framework | click | 8.x |
| Progress Display | rich | 13.x |
| Testing | pytest, pytest-postgresql | latest |
| Type Checking | mypy, Pylance | strict mode |
| Linting | ruff, pylint | per constitution |

## Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    "psycopg[pool]>=3.1",
    "pydantic>=2.0",
    "click>=8.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-postgresql>=6.0",
    "mypy>=1.8",
    "ruff>=0.1",
    "pylint>=3.0",
]
```

## Open Questions Resolved

All NEEDS CLARIFICATION items from Technical Context have been resolved:
- ✅ PostgreSQL driver: psycopg3
- ✅ CLI framework: click
- ✅ Streaming approach: built-in csv module with chunked iteration
- ✅ Connection pooling: psycopg_pool
- ✅ Progress display: rich (for normal verbosity)
