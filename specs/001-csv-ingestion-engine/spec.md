# Feature Specification: CSV Ingestion Engine

**Feature Branch**: `001-csv-ingestion-engine`
**Created**: 2026-01-27
**Status**: Approved (Retroactive)
**Input**: CLI tool for streaming CSV files into PostgreSQL using COPY protocol

**Governance**: This specification adheres to [constitution.md](../../.specify/memory/constitution.md) - Specification-Driven Development principle (Principle I).

**Note**: This specification was created retroactively to document the implemented feature and ensure constitution compliance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic CSV Ingestion (Priority: P1) MVP

As a data engineer, I want to ingest a CSV file into a PostgreSQL table so that I can quickly load data for analysis or application use without writing custom import scripts.

**Why this priority**: This is the core value proposition. Without basic ingestion capability, the tool provides no value. This story delivers a complete, standalone product that can be used immediately.

**Independent Test**: Provide a sample CSV file and verify data appears correctly in PostgreSQL table. Test table creation, data append, and error scenarios. Can be fully tested with a local PostgreSQL instance and sample CSV files.

**Acceptance Scenarios**:

1. **Given** a valid CSV file with headers and data rows, **When** the user runs the ingestion command with valid database credentials, **Then** a new table is created (if it doesn't exist) with columns matching CSV headers, and all data rows are inserted.

2. **Given** a CSV file and an existing table with matching schema, **When** the user runs the ingestion command, **Then** data is appended to the existing table without duplicating the schema.

3. **Given** a CSV file and an existing table with mismatched schema, **When** the user runs with schema-mode=strict (default), **Then** the operation fails with a clear error message listing the schema differences.

4. **Given** a CSV file with an existing table with mismatched schema, **When** the user runs with schema-mode=match, **Then** only common columns are inserted and the operation succeeds.

5. **Given** a CSV file with an existing table with mismatched schema, **When** the user runs with schema-mode=alter, **Then** missing columns are automatically added to the table and all data is inserted.

6. **Given** a CSV file with malformed rows (wrong column count), **When** the user runs with row-mode=strict (default), **Then** the operation fails immediately with a clear error indicating the line number and issue.

7. **Given** a CSV file with malformed rows, **When** the user runs with row-mode=skip, **Then** valid rows are inserted, malformed rows are logged, and the operation completes with partial success status.

8. **Given** a CSV file with malformed rows, **When** the user runs with row-mode=lenient, **Then** short rows are padded with empty values, long rows are truncated, and all rows are inserted.

9. **Given** an empty CSV file (zero bytes), **When** the user runs with empty-mode=strict (default), **Then** the operation fails with a clear error message.

10. **Given** a CSV file with only headers (no data rows), **When** the user runs with empty-mode=headers, **Then** the table is created with the schema but no data is inserted, and the operation succeeds.

11. **Given** any database operation failure, **When** a transaction error occurs, **Then** all changes are rolled back atomically and no partial data is left in the database.

---

### User Story 2 - Large File Handling (Priority: P2)

As a data engineer working with large datasets, I want to ingest CSV files over 100MB without running out of memory so that I can reliably process production-scale data on machines with limited resources.

**Why this priority**: Extends the core functionality to handle real-world data volumes. Without this, the tool is limited to small files and cannot be used in production scenarios.

**Independent Test**: Ingest a 1GB CSV file while monitoring memory usage. Memory should stay below 100MB throughout the entire operation.

**Acceptance Scenarios**:

1. **Given** a large CSV file (100MB+), **When** the user runs the ingestion command, **Then** the file is processed in chunks without loading the entire file into memory.

2. **Given** a large CSV file, **When** the user runs with --chunk-size=5000, **Then** processing occurs in 5000-row batches and memory usage remains bounded.

3. **Given** a large CSV file with normal verbosity, **When** the user runs the ingestion, **Then** a progress indicator shows rows processed, estimated completion, and processing rate.

4. **Given** a large CSV file with verbose output, **When** the ingestion completes, **Then** performance statistics including peak memory usage and throughput are displayed.

---

### User Story 3 - Connection Resilience (Priority: P3)

As a DevOps engineer running multiple ingestion jobs, I want connection pooling so that database connections are efficiently reused across operations without hitting connection limits.

**Why this priority**: Optimizes resource usage for production deployments. Provides efficiency gains for users running multiple sequential imports.

**Independent Test**: Run multiple sequential ingestion operations and verify connections are reused from pool rather than creating new connections each time.

**Acceptance Scenarios**:

1. **Given** a configured connection pool, **When** multiple ingestion operations run sequentially, **Then** database connections are reused from the pool.

2. **Given** pool-size=10 configuration, **When** ingestion runs, **Then** no more than 10 simultaneous database connections are created.

3. **Given** a connection pool, **When** a connection becomes stale or fails, **Then** the pool automatically replaces it with a healthy connection.

---

### Edge Cases

- What happens when the CSV file is not found? System returns clear error with file path and exit code 2.
- What happens when database credentials are invalid? System returns clear connection error with exit code 3.
- What happens when disk space runs out during ingestion? Transaction is rolled back, no partial data remains.
- What happens when the table name contains invalid characters? System validates table name pattern and returns configuration error with exit code 4.
- What happens when CSV contains special characters (quotes, commas, newlines within fields)? Standard CSV escaping (RFC 4180) is handled correctly.
- What happens when the connection drops mid-ingestion? Transaction is rolled back, operation can be retried safely.

## Requirements *(mandatory)*

### Functional Requirements

**Core Ingestion (US1)**

- **FR-001**: System MUST provide a command-line interface for CSV ingestion
- **FR-002**: System MUST accept a CSV file path as input
- **FR-003**: System MUST accept a target table name as input
- **FR-004**: System MUST accept database connection parameters (host, port, database, user, password)
- **FR-005**: System MUST use efficient bulk loading protocol for data transfer
- **FR-006**: System MUST stream data without loading entire file into memory
- **FR-007**: System MUST support connection pooling for efficient resource usage
- **FR-008**: System MUST create the target table if it does not exist
- **FR-009**: System MUST use text data type for all columns when creating tables
- **FR-010**: System MUST report the number of rows successfully inserted
- **FR-011**: System MUST provide clear, actionable error messages including relevant context (file path, line number, column names)
- **FR-012**: System MUST support atomic transactions (all-or-nothing semantics)
- **FR-013**: System MUST roll back all changes on failure, leaving no partial data

**Environment & Configuration**

- **FR-014**: System MUST support standard database environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, DATABASE_URL)
- **FR-015**: Command-line options MUST take precedence over environment variables

**Handling Modes**

- **FR-016**: System MUST support configurable schema mismatch handling:
  - strict (default): Fail if CSV headers don't match table columns
  - match: Insert only columns that exist in both CSV and table
  - alter: Automatically add missing columns to the table

- **FR-017**: System MUST support configurable malformed row handling:
  - strict (default): Fail on first malformed row
  - skip: Log and skip malformed rows, continue processing
  - lenient: Pad short rows with empty values, truncate long rows

- **FR-018**: When rows are skipped, system MUST report line numbers and reasons in output

- **FR-019**: System MUST support configurable empty file handling:
  - strict (default): Fail if file is empty or has no data rows
  - headers: Allow files with headers but no data (creates empty table)
  - permissive: Allow fully empty files (no operation performed)

**Output & Verbosity**

- **FR-020**: System MUST support multiple verbosity levels:
  - quiet: Output only row count (or error message)
  - normal (default): Progress indicator with completion status
  - verbose: Detailed statistics including memory usage and throughput

- **FR-021**: System MUST support JSON output format for scripting and automation
- **FR-022**: System MUST return appropriate exit codes for different outcomes

### Key Entities

- **CSV File**: Input data source with headers defining column names and rows containing data values. Supports standard RFC 4180 CSV format with quoted fields and escaped characters.

- **Database Configuration**: Connection parameters including host, port, database name, credentials, and optional pool settings. Supports both individual parameters and connection URL format.

- **Target Table**: PostgreSQL table where data is inserted. Can be existing (append) or new (created from headers). All columns stored as text type.

- **Ingestion Result**: Outcome of the operation including status (success/partial/failed), row counts (processed, inserted, skipped), timing information, and any error details.

- **Skipped Row**: Record of a row that could not be inserted, including line number, reason for skipping, and optionally the raw row content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can ingest a 100MB CSV file in under 60 seconds on standard hardware (defined as: 4-core CPU, 8GB RAM, SSD storage, modern PostgreSQL on localhost)
- **SC-002**: System maintains less than 100MB memory usage regardless of input file size
- **SC-003**: Users can complete a basic ingestion operation (install, configure, run) in under 5 minutes with documentation on standard hardware
- **SC-004**: System achieves streaming throughput of at least 1.5 MB/second for bulk data loading
- **SC-005**: 95% of user errors result in actionable error messages (message suggests how to fix the issue)
- **SC-006**: All database operations are atomic - no partial data left after failures
- **SC-007**: Connection pool reduces connection overhead by 50% for sequential operations

## Assumptions

- Users have PostgreSQL server access with appropriate permissions to create tables and insert data
- CSV files use UTF-8 encoding by default
- CSV files follow RFC 4180 format (comma-separated, quoted fields for special characters)
- Target PostgreSQL version is modern (supports COPY protocol and standard features)
- Users have basic familiarity with command-line tools
- Standard database environment variables (PG*) follow PostgreSQL conventions
