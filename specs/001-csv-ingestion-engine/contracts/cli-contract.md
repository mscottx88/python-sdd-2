# CLI Contract: CSV Ingestion Engine

**Phase**: 1 (Design)
**Date**: 2026-01-27
**Branch**: `001-csv-ingestion-engine`

## Command Overview

```
csv-ingest [OPTIONS] CSV_FILE TABLE_NAME
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CSV_FILE` | Path | Yes | Path to the CSV file to ingest |
| `TABLE_NAME` | String | Yes | Target PostgreSQL table name |

## Options

### Database Connection

| Option | Short | Type | Default | Env Variable | Description |
|--------|-------|------|---------|--------------|-------------|
| `--host` | `-h` | String | localhost | `PGHOST` | Database host |
| `--port` | `-p` | Integer | 5432 | `PGPORT` | Database port |
| `--database` | `-d` | String | *required* | `PGDATABASE` | Database name |
| `--user` | `-u` | String | *required* | `PGUSER` | Database user |
| `--password` | `-P` | String | *required* | `PGPASSWORD` | Database password |
| `--database-url` | | String | | `DATABASE_URL` | Full connection URL (overrides individual options) |

### Handling Modes

| Option | Type | Default | Values | Description |
|--------|------|---------|--------|-------------|
| `--schema-mode` | Choice | strict | strict, match, alter | Schema mismatch handling |
| `--row-mode` | Choice | strict | strict, skip, lenient | Malformed row handling |
| `--empty-mode` | Choice | strict | strict, headers, permissive | Empty file handling |

### Output Control

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbosity` | `-v` | Choice | normal | Output level: quiet, normal, verbose |
| `--json` | | Flag | False | Output result as JSON |

### Advanced

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--chunk-size` | Integer | 1000 | Rows per chunk (100-100000) |
| `--pool-size` | Integer | 5 | Max connection pool size (1-50) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all rows ingested |
| 1 | Partial success - some rows skipped (only with `--row-mode=skip`) |
| 2 | CSV error - file not found, empty, or malformed |
| 3 | Database error - connection, schema mismatch, or transaction failure |
| 4 | Configuration error - invalid options or missing required values |

## Output Formats

### Normal Mode (default)

```
Ingesting data.csv into table 'users'...
Progress: [████████████████████████████████] 100% | 50,000 rows | 1,234 rows/s
✓ Successfully inserted 50,000 rows into 'users' in 40.5 seconds
```

### Quiet Mode (`-v quiet`)

```
50000
```
(Just the row count, or error message on failure)

### Verbose Mode (`-v verbose`)

```
Ingesting data.csv into table 'users'...
  File size: 15.2 MB
  Detected columns: id, name, email, created_at
  Table 'users' exists with matching schema
  Starting transaction...
Progress: [████████████████████████████████] 100% | 50,000 rows | 1,234 rows/s
  Peak memory: 45.2 MB
  Throughput: 1,234 rows/sec (0.37 MB/sec)
  Transaction committed
✓ Successfully inserted 50,000 rows into 'users' in 40.5 seconds
```

### JSON Mode (`--json`)

```json
{
  "status": "success",
  "rows_processed": 50000,
  "rows_inserted": 50000,
  "rows_skipped": 0,
  "table_name": "users",
  "table_created": false,
  "duration_seconds": 40.5,
  "peak_memory_mb": 45.2,
  "throughput_rows_per_sec": 1234
}
```

### Error Output (JSON)

```json
{
  "status": "failed",
  "error_type": "SchemaMismatchError",
  "error_message": "Table 'users' schema does not match CSV headers",
  "details": {
    "csv_columns": ["id", "name", "email", "phone"],
    "table_columns": ["id", "name", "email"],
    "missing_in_table": ["phone"],
    "missing_in_csv": []
  }
}
```

## Usage Examples

### Basic Usage

```bash
# Using environment variables
export PGHOST=localhost PGPORT=5432 PGDATABASE=mydb PGUSER=admin PGPASSWORD=secret
csv-ingest data.csv users

# Using command-line options
csv-ingest data.csv users -h localhost -d mydb -u admin -P secret

# Using DATABASE_URL
csv-ingest data.csv users --database-url "postgresql://admin:secret@localhost:5432/mydb"
```

### Handling Modes

```bash
# Skip malformed rows instead of failing
csv-ingest data.csv users --row-mode=skip

# Auto-add missing columns to existing table
csv-ingest data.csv users --schema-mode=alter

# Allow headers-only files (creates empty table)
csv-ingest data.csv users --empty-mode=headers
```

### Output Control

```bash
# Quiet mode for scripting
ROWS=$(csv-ingest data.csv users -v quiet)

# JSON output for automation
csv-ingest data.csv users --json | jq '.rows_inserted'

# Verbose for debugging
csv-ingest data.csv users -v verbose
```

## Environment Variables

| Variable | Corresponds To | Description |
|----------|----------------|-------------|
| `DATABASE_URL` | `--database-url` | Full PostgreSQL connection URL |
| `PGHOST` | `--host` | Database host |
| `PGPORT` | `--port` | Database port |
| `PGDATABASE` | `--database` | Database name |
| `PGUSER` | `--user` | Database user |
| `PGPASSWORD` | `--password` | Database password |

**Priority**: Command-line options > `DATABASE_URL` > Individual `PG*` variables

## Behavioral Contract

### FR Mapping

| Requirement | CLI Implementation |
|-------------|-------------------|
| FR-001 | `csv-ingest` command with Click |
| FR-002 | `CSV_FILE` positional argument |
| FR-003 | `TABLE_NAME` positional argument |
| FR-004 | `--host`, `--port`, `--database`, `--user`, `--password` options |
| FR-005 | Uses psycopg3 COPY protocol internally |
| FR-006 | `--chunk-size` controls streaming batch size |
| FR-007 | `--pool-size` controls connection pool |
| FR-010 | Row count in output (all verbosity levels) |
| FR-011 | Clear error messages with context |
| FR-014 | `PG*` and `DATABASE_URL` environment variables |
| FR-016 | `--schema-mode` option |
| FR-017 | `--row-mode` option |
| FR-018 | Skipped row details in verbose/JSON output |
| FR-019 | `--empty-mode` option |
| FR-020 | `--verbosity` option |
