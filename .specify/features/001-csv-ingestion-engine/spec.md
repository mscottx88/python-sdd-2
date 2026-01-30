# Feature Specification: CSV Ingestion Engine

**Feature Branch**: `001-csv-ingestion-engine`
**Created**: 2026-01-27
**Status**: Draft
**Input**: User description: "Create a python application with a CLI entrypoint that implements a single-file CSV ingestion and streams the file into a Postgres database utilizing connection pooling, and the COPY statement."

**Governance**: This specification adheres to [constitution.md](../../memory/constitution.md) - Specification-Driven Development principle (Principle II).

## Clarifications

### Session 2026-01-27

- Q: If ingestion fails partway through, what should happen to rows already inserted? → A: Atomic (all-or-nothing) - rollback all inserted rows on any failure.
- Q: If the target table exists but has a different schema than the CSV headers, what should happen? → A: Configurable via CLI with three modes: (1) fail with error (default), (2) insert matching columns only, (3) alter table to add missing columns.
- Q: How should malformed rows (inconsistent column counts) be handled? → A: Configurable via CLI with three modes: (1) fail on first error (default), (2) skip bad rows and log them, (3) pad missing columns with NULL / truncate extra columns.
- Q: How should empty CSV files be handled? → A: Configurable via CLI with three modes: (1) fail on any empty file (default), (2) headers-only OK (create table, 0 rows), fail if completely empty, (3) always succeed (report 0 rows).
- Q: What progress feedback should be shown during ingestion? → A: Configurable via CLI flag with three verbosity levels: quiet (minimal output), normal (progress bar with row counts), verbose (detailed logs with timing and memory).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic CSV Ingestion (Priority: P1)

A data engineer needs to ingest a CSV file into a PostgreSQL database table. They run a command specifying the CSV file path and target table name, and the system efficiently streams the data into the database using the COPY protocol.

**Why this priority**: This is the core functionality - without basic ingestion, the tool has no value. All other features build upon this foundation.

**Independent Test**: Can be fully tested by providing a sample CSV file and verifying data appears correctly in the target PostgreSQL table. Delivers immediate value for data loading workflows.

**Acceptance Scenarios**:

1. **Given** a valid CSV file with headers and a PostgreSQL database connection, **When** the user runs the ingestion command with the file path and table name, **Then** the data is loaded into the specified table and a success message is displayed with row count.
2. **Given** a CSV file and a table that does not exist, **When** the user runs the ingestion command, **Then** the system creates the table with columns matching the CSV headers and loads the data.
3. **Given** a CSV file with data, **When** the user runs the ingestion command against an existing table with matching schema, **Then** the data is appended to the existing table contents.

---

### User Story 2 - Large File Handling (Priority: P2)

A data engineer needs to ingest a large CSV file (hundreds of megabytes to gigabytes) without consuming excessive memory. The system streams the file in chunks, maintaining consistent memory usage regardless of file size.

**Why this priority**: Streaming is explicitly requested and critical for production use where file sizes vary. Memory efficiency prevents system crashes and enables processing on resource-constrained environments.

**Independent Test**: Can be tested by ingesting a large CSV file while monitoring memory usage. Memory consumption should remain bounded regardless of file size.

**Acceptance Scenarios**:

1. **Given** a CSV file of any size, **When** the user runs the ingestion command, **Then** the system processes the file in a streaming manner without loading it entirely into memory.
2. **Given** a 1GB CSV file, **When** the user monitors system memory during ingestion, **Then** memory usage remains below a reasonable threshold (e.g., 100MB) throughout the operation.

---

### User Story 3 - Connection Resilience (Priority: P3)

A data engineer running ingestion in a production environment benefits from connection pooling to handle concurrent operations efficiently and recover gracefully from transient connection issues.

**Why this priority**: Connection pooling is explicitly requested. It provides efficiency for repeated operations and resilience, but the tool functions without it (just less efficiently).

**Independent Test**: Can be tested by running multiple sequential ingestion operations and verifying connections are reused from the pool rather than creating new connections each time.

**Acceptance Scenarios**:

1. **Given** multiple sequential ingestion operations, **When** the user runs them in succession, **Then** database connections are reused from a pool rather than creating new connections each time.
2. **Given** a configured connection pool, **When** the system starts, **Then** it establishes a pool of database connections ready for use.

---

### Edge Cases

- What happens when the CSV file is empty (headers only or completely empty)? → Configurable: strict mode (fail), headers mode (allow headers-only), or permissive mode (always succeed).
- How does the system handle CSV files with malformed rows (inconsistent column counts)? → Configurable: strict mode (fail), skip mode (log and continue), or lenient mode (pad/truncate).
- What happens when the database connection fails mid-ingestion? → Transaction is rolled back; no partial data remains in the table.
- How does the system handle CSV files with special characters in headers or data?
- What happens when the target table has a different schema than the CSV headers? → Configurable: strict mode (fail), match mode (common columns only), or alter mode (add missing columns).
- How does the system handle CSV files with extremely long lines or fields?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a command-line interface for invoking CSV ingestion operations
- **FR-002**: System MUST accept a file path to a CSV file as input
- **FR-003**: System MUST accept a target table name as input
- **FR-004**: System MUST accept database connection parameters (host, port, database name, username, password)
- **FR-005**: System MUST use PostgreSQL's COPY protocol for efficient bulk data loading
- **FR-006**: System MUST stream the CSV file without loading it entirely into memory
- **FR-007**: System MUST implement connection pooling for database connections
- **FR-008**: System MUST create the target table if it does not exist, deriving column names from CSV headers
- **FR-009**: System MUST validate that the CSV file exists and is readable before starting ingestion
- **FR-010**: System MUST report the number of rows successfully ingested upon completion
- **FR-011**: System MUST provide clear error messages when ingestion fails, including the reason for failure
- **FR-012**: System MUST handle CSV files with standard comma delimiters and quoted fields
- **FR-013**: System MUST treat the first row of the CSV file as column headers
- **FR-014**: System MUST support database connection configuration via environment variables as an alternative to CLI arguments
- **FR-015**: System MUST execute ingestion within a database transaction; on any failure, all inserted rows MUST be rolled back (atomic/all-or-nothing behavior)
- **FR-016**: System MUST provide a CLI option to configure schema mismatch handling with three modes: "strict" (fail with error listing differences, default), "match" (insert only columns present in both CSV and table), "alter" (add missing columns to existing table)
- **FR-017**: System MUST provide a CLI option to configure malformed row handling with three modes: "strict" (fail on first error, default), "skip" (log and skip bad rows), "lenient" (pad missing columns with NULL, truncate extra columns)
- **FR-018**: When using "skip" mode, system MUST report the count and line numbers of skipped rows upon completion
- **FR-019**: System MUST provide a CLI option to configure empty file handling with three modes: "strict" (fail on any empty file, default), "headers" (allow headers-only files, fail if completely empty), "permissive" (always succeed, report 0 rows)
- **FR-020**: System MUST provide a CLI option to configure output verbosity with three levels: "quiet" (only final result), "normal" (progress indicator with row counts, default), "verbose" (detailed logs including timing and memory usage)

### Key Entities

- **CSV File**: The source data file containing rows of comma-separated values with a header row defining column names
- **Target Table**: The PostgreSQL database table where data will be loaded; may be existing or created by the system
- **Connection Pool**: A managed set of reusable database connections that improves efficiency and enables concurrent operations
- **Ingestion Job**: A single execution of the CSV-to-database loading process, including its configuration and outcome

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can ingest a 100MB CSV file in under 60 seconds on standard hardware with a local database
- **SC-002**: Memory consumption remains below 100MB regardless of input file size
- **SC-003**: Users can successfully ingest a CSV file with a single command invocation (no multi-step process required)
- **SC-004**: System provides feedback within 5 seconds of command execution (either progress indication or completion)
- **SC-005**: 95% of common CSV formats (comma-delimited, quoted strings, UTF-8 encoded) are handled without user configuration
- **SC-006**: Error messages enable users to identify and resolve issues without consulting documentation in 80% of failure cases

## Assumptions

- PostgreSQL database is accessible and user has sufficient permissions to create tables and insert data
- CSV files use UTF-8 encoding (or ASCII-compatible encoding)
- CSV files use comma as the field delimiter
- CSV files use standard quoting conventions (double quotes for fields containing commas or newlines)
- The first row of each CSV file contains column headers
- When creating tables, all columns will be created as TEXT type (users can alter types after ingestion if needed)
- Connection pool size will use sensible defaults appropriate for single-user CLI operation
- Database connection parameters can be provided via CLI arguments or environment variables (DATABASE_URL or individual parameters)
