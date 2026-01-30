# Benchmark Scripts

This directory contains benchmark and validation scripts for the CSV Ingestion Engine.

## Connection Overhead Benchmark (SC-007)

**Script**: `benchmark_connection_overhead.py`
**Validates**: SC-007 - "Connection pool reduces connection overhead by 50% for sequential operations"

### Purpose

Measures the connection time overhead for 10 sequential CSV ingestion operations comparing:
1. **Baseline**: Without connection pooling (creates new connection each time)
2. **Optimized**: With connection pooling (reuses connections from pool)

### Prerequisites

1. **Docker Desktop** must be running
2. **PostgreSQL container** must be accessible
3. **Environment variables** configured:
   - `PGHOST` - PostgreSQL host (default: localhost)
   - `PGPORT` - PostgreSQL port (default: 5432)
   - `PGDATABASE` - Database name (required)
   - `PGUSER` - Database user (required)
   - `PGPASSWORD` - Database password (optional)

### Usage

```bash
# Set up environment (example)
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=test_db
export PGUSER=postgres
export PGPASSWORD=postgres

# Run benchmark
python scripts/benchmark_connection_overhead.py
```

### Expected Output

```
======================================================================
Connection Overhead Reduction Benchmark (SC-007)
======================================================================

📝 Creating test CSV file (100 rows)...
✅ Test CSV created: /tmp/tmp_xyz.csv

🔍 Benchmarking WITHOUT pooling (10 iterations)...
  Iteration 1: 0.1234s (100 rows)
  Iteration 2: 0.1189s (100 rows)
  ...
  Iteration 10: 0.1201s (100 rows)
✅ Total time: 1.2043s (avg: 0.1204s per operation)

🔍 Benchmarking WITH pooling (10 iterations)...
  Iteration 1: 0.0567s (100 rows)
  Iteration 2: 0.0523s (100 rows)
  ...
  Iteration 10: 0.0541s (100 rows)
✅ Total time: 0.5412s (avg: 0.0541s per operation)

======================================================================
BENCHMARK RESULTS
======================================================================

Metric                                   Without Pool    With Pool
----------------------------------------------------------------------
Total Time                               1.2043s         0.5412s
Average Time per Operation               0.1204s         0.0541s
Std Dev                                  0.0023s         0.0018s

======================================================================
⚡ Connection Overhead Reduction: 0.6631s
📊 Percentage Improvement: 55.07%
🎯 Target: ≥50% reduction
✅ Status: PASS - Connection pooling achieves target!
======================================================================
```

### Interpretation

- **Without Pooling**: Each operation creates a new database connection, incurring TCP/IP connection overhead and authentication handshake time
- **With Pooling**: Connections are reused from the pool, eliminating connection overhead after the first operation
- **Target**: ≥50% reduction in total time for sequential operations

### Exit Codes

- `0` - **PASS**: Connection pooling achieves ≥50% overhead reduction
- `1` - **FAIL**: Connection pooling below 50% target, or error occurred

### Notes

1. **Small CSV files**: The benchmark uses small 100-row CSV files to isolate connection overhead from data processing time
2. **Sequential operations**: Simulates real-world scenario of running multiple imports sequentially (e.g., nightly batch jobs)
3. **Warm-up**: The first iteration in each benchmark may be slower due to cache effects
4. **Network latency**: Results may vary based on network latency between client and PostgreSQL server (localhost recommended for consistent results)

### Troubleshooting

**Error: "Configuration error"**
- Ensure `PGDATABASE` and `PGUSER` environment variables are set
- Check database connection parameters

**Error: "Connection refused"**
- Verify Docker Desktop is running
- Confirm PostgreSQL container is healthy and accepting connections
- Check port 5432 is not blocked by firewall

**Error: "Database not found"**
- Create the test database: `createdb -U postgres test_db`
- Or use an existing database name

**Pooling improvement < 50%**
- May occur if PostgreSQL is on same machine (very fast local connection)
- Expected behavior: overhead reduction is more pronounced with network latency
- Verify PostgreSQL isn't using Unix domain sockets (force TCP by using 127.0.0.1 instead of localhost)

## Future Benchmarks

Additional benchmarks can be added to validate other success criteria:
- **SC-001**: 100MB CSV ingestion in <60 seconds
- **SC-002**: <100MB memory usage for large files
- **SC-004**: Throughput ≥1.5 MB/s
