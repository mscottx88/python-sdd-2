# Quickstart: CSV Ingestion Engine

**Phase**: 1 (Design)
**Date**: 2026-01-27
**Branch**: `001-csv-ingestion-engine`

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd python-sdd-2

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

## Prerequisites

- Python 3.13+
- PostgreSQL server (local or remote)
- Docker (for running tests with PostgreSQL container)

## Quick Start

### 1. Set Database Connection

```bash
# Option A: Environment variables
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=mydb
export PGUSER=admin
export PGPASSWORD=secret

# Option B: Single URL
export DATABASE_URL="postgresql://admin:secret@localhost:5432/mydb"
```

### 2. Ingest a CSV File

```bash
# Basic usage - creates table if it doesn't exist
csv-ingest customers.csv customers

# With explicit connection options
csv-ingest customers.csv customers -h localhost -d mydb -u admin -P secret
```

### 3. Check the Result

```bash
# View row count (quiet mode)
csv-ingest customers.csv customers -v quiet
# Output: 1000

# Get JSON result for scripting
csv-ingest customers.csv customers --json
# Output: {"status": "success", "rows_inserted": 1000, ...}
```

## Common Use Cases

### Ingest with Error Tolerance

```bash
# Skip malformed rows instead of failing
csv-ingest messy_data.csv products --row-mode=skip

# Output shows skipped rows:
# ✓ Inserted 9,850 rows (150 skipped) into 'products'
```

### Update Existing Table

```bash
# Append to existing table (default)
csv-ingest new_customers.csv customers

# Only insert matching columns if schema differs
csv-ingest partial_data.csv customers --schema-mode=match

# Auto-add new columns from CSV
csv-ingest extended_data.csv customers --schema-mode=alter
```

### Large File Handling

```bash
# Adjust chunk size for memory/performance balance
csv-ingest huge_file.csv logs --chunk-size=5000

# Monitor progress with verbose output
csv-ingest huge_file.csv logs -v verbose
```

## Example Workflow

```bash
# 1. Create sample CSV
cat > sample.csv << 'EOF'
id,name,email
1,Alice,alice@example.com
2,Bob,bob@example.com
3,Charlie,charlie@example.com
EOF

# 2. Start PostgreSQL (if using Docker)
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16

# 3. Set connection
export DATABASE_URL="postgresql://postgres:secret@localhost:5432/testdb"

# 4. Ingest the CSV
csv-ingest sample.csv users

# 5. Verify in database
docker exec -it postgres psql -U postgres -d testdb -c "SELECT * FROM users"
```

## Troubleshooting

### Connection Refused

```
Error: Could not connect to database at localhost:5432
```

**Solution**: Ensure PostgreSQL is running and accepting connections.

### Schema Mismatch

```
Error: Table 'users' schema does not match CSV headers
  Missing in table: phone
  Missing in CSV: created_at
```

**Solutions**:
- Use `--schema-mode=match` to insert only matching columns
- Use `--schema-mode=alter` to auto-add missing columns
- Manually alter the table to match CSV structure

### Malformed Rows

```
Error: Row 1523 has 4 columns, expected 3
```

**Solutions**:
- Fix the CSV file
- Use `--row-mode=skip` to skip bad rows
- Use `--row-mode=lenient` to pad/truncate columns

### Empty File

```
Error: CSV file is empty (no data rows)
```

**Solutions**:
- Use `--empty-mode=headers` if file has headers but no data
- Use `--empty-mode=permissive` to allow fully empty files

## Performance Tips

1. **Chunk Size**: Default 1000 works well for most cases. Increase to 5000-10000 for very large files with simple data.

2. **Local Database**: Ingestion is fastest with a local PostgreSQL instance due to network latency.

3. **Indexes**: For repeated ingestions, consider dropping indexes before and recreating after.

4. **Memory**: The tool maintains <100MB memory regardless of file size when using default settings.

## Next Steps

- See [CLI Contract](contracts/cli-contract.md) for full option reference
- See [Data Model](data-model.md) for Pydantic model definitions
- Run tests: `pytest tests/`
