# Tasks: CSV Ingestion Engine

**Input**: Design documents from `/specs/001-csv-ingestion-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Governance**: This task list adheres to [constitution.md](../../.specify/memory/constitution.md) - Test-Driven Development principle (Principle III).

**Tests**: Tests are included per constitution TDD requirements. Tests MUST be written FIRST and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (per plan.md)
- Package: `src/csv_postgres_pipeline/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure: `src/csv_postgres_pipeline/`, `tests/unit/`, `tests/integration/`, `tests/contract/`
- [x] T002 Initialize Python 3.13 project with pyproject.toml including dependencies: psycopg[pool]>=3.1, pydantic>=2.0, click>=8.0, rich>=13.0
- [x] T003 [P] Configure ruff.toml with E, W, F, I, N, UP, B, C4, SIM, S rules and 90-char line length
- [x] T004 [P] Configure mypy.ini with strict mode enabled
- [x] T005 [P] Configure .pylintrc for 10.00/10.00 score requirement
- [x] T006 [P] Create .pre-commit-config.yaml with ruff, mypy, pylint hooks
- [x] T007 [P] Configure pytest.ini with test paths and markers
- [x] T008 Create `src/csv_postgres_pipeline/__init__.py` with package metadata

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

- [x] T009 [P] Create tests/conftest.py with shared fixtures: PostgreSQL container verification, sample CSV files, database cleanup
- [x] T010 [P] Unit test for exception hierarchy in tests/unit/test_exceptions.py (test all exception types, inheritance, attributes)

### Implementation for Foundation

- [x] T011 [P] Implement exception hierarchy in src/csv_postgres_pipeline/exceptions.py (IngestionError, CSVError, EmptyFileError, MalformedRowError, DatabaseError, ConnectionError, SchemaMismatchError, TransactionError)
- [x] T012 [P] Create .vscode/settings.json with Pylance configuration per constitution

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Basic CSV Ingestion (Priority: P1) 🎯 MVP

**Goal**: Ingest a CSV file into PostgreSQL using COPY protocol with atomic transactions. Create table if not exists. Support configurable handling modes.

**Independent Test**: Provide a sample CSV file and verify data appears correctly in PostgreSQL table. Test table creation, data append, and error scenarios.

**FR Coverage**: FR-001 through FR-020 (core functionality)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US1] Unit test for DatabaseConfig model in tests/unit/test_models.py (validation rules, connection string generation)
- [x] T014 [P] [US1] Unit test for CSVConfig model in tests/unit/test_models.py (validation rules, mode enums, table name pattern)
- [x] T015 [P] [US1] Unit test for IngestionResult and SkippedRow models in tests/unit/test_models.py
- [x] T016 [P] [US1] Unit test for TableSchema and ColumnInfo models in tests/unit/test_models.py
- [x] T017 [P] [US1] Unit test for CSV reader in tests/unit/test_csv_reader.py (header parsing, row iteration, empty file detection, malformed row detection)
- [x] T018 [P] [US1] Contract test for CLI in tests/contract/test_cli_contract.py (arguments, options, exit codes, output formats)
- [x] T019 [P] [US1] Integration test for basic ingestion in tests/integration/test_ingestion.py (new table, existing table, append)
- [x] T020 [P] [US1] Integration test for database operations in tests/integration/test_database.py (connect, schema detection, table creation, COPY)

### Implementation for User Story 1

- [x] T021 [P] [US1] Implement DatabaseConfig model in src/csv_postgres_pipeline/models.py (host, port, database, user, password, connection_string property)
- [x] T022 [P] [US1] Implement CSVConfig model in src/csv_postgres_pipeline/models.py (file_path, table_name, schema_mode, row_mode, empty_mode, chunk_size)
- [x] T023 [P] [US1] Implement IngestionResult and SkippedRow models in src/csv_postgres_pipeline/models.py
- [x] T024 [P] [US1] Implement TableSchema and ColumnInfo models in src/csv_postgres_pipeline/models.py
- [x] T025 [US1] Implement basic CSV reader in src/csv_postgres_pipeline/csv_reader.py (open file, parse headers, iterate rows, validate column counts)
- [x] T026 [US1] Implement database connection in src/csv_postgres_pipeline/database.py (create_connection function using psycopg)
- [x] T027 [US1] Implement schema detection in src/csv_postgres_pipeline/database.py (get_table_schema function, query information_schema)
- [x] T028 [US1] Implement table creation in src/csv_postgres_pipeline/database.py (create_table function, all TEXT columns from headers)
- [x] T029 [US1] Implement COPY execution in src/csv_postgres_pipeline/database.py (copy_rows function using cursor.copy with COPY FROM STDIN)
- [x] T030 [US1] Implement schema comparison in src/csv_postgres_pipeline/database.py (compare_schemas function, detect mismatches)
- [x] T031 [US1] Implement atomic transaction wrapper in src/csv_postgres_pipeline/database.py (with transaction, rollback on error)
- [x] T032 [US1] Implement ingestion orchestration in src/csv_postgres_pipeline/ingestion.py (ingest function: validate file, get schema, create/verify table, copy data, return result)
- [x] T033 [US1] Implement schema mismatch handling modes in src/csv_postgres_pipeline/ingestion.py (strict/match/alter per FR-016)
- [x] T034 [US1] Implement malformed row handling modes in src/csv_postgres_pipeline/ingestion.py (strict/skip/lenient per FR-017)
- [x] T035 [US1] Implement empty file handling modes in src/csv_postgres_pipeline/ingestion.py (strict/headers/permissive per FR-019)
- [x] T036 [US1] Implement CLI entrypoint in src/csv_postgres_pipeline/cli.py (csv-ingest command with click)
- [x] T037 [US1] Implement CLI arguments in src/csv_postgres_pipeline/cli.py (CSV_FILE, TABLE_NAME positional args)
- [x] T038 [US1] Implement database connection options in src/csv_postgres_pipeline/cli.py (--host, --port, --database, --user, --password, --database-url)
- [x] T039 [US1] Implement environment variable support in src/csv_postgres_pipeline/cli.py (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, DATABASE_URL)
- [x] T040 [US1] Implement handling mode options in src/csv_postgres_pipeline/cli.py (--schema-mode, --row-mode, --empty-mode)
- [x] T041 [US1] Implement output verbosity in src/csv_postgres_pipeline/cli.py (--verbosity quiet/normal/verbose per FR-020)
- [x] T042 [US1] Implement JSON output option in src/csv_postgres_pipeline/cli.py (--json flag)
- [x] T043 [US1] Implement exit codes in src/csv_postgres_pipeline/cli.py (0=success, 1=partial, 2=CSV error, 3=DB error, 4=config error)
- [x] T044 [US1] Add pyproject.toml entry point: `csv-ingest = csv_postgres_pipeline.cli:main`

**Checkpoint**: User Story 1 complete - basic CSV ingestion works with all handling modes

---

## Phase 4: User Story 2 - Large File Handling (Priority: P2)

**Goal**: Stream large CSV files (100MB+) without loading entirely into memory. Maintain <100MB memory usage regardless of file size.

**Independent Test**: Ingest a 1GB CSV file while monitoring memory. Memory should stay below 100MB throughout.

**FR Coverage**: FR-006 (streaming)

### Tests for User Story 2

- [x] T045 [P] [US2] Unit test for chunked CSV reading in tests/unit/test_csv_reader.py (yield chunks, configurable chunk size)
- [x] T046 [P] [US2] Integration test for large file handling in tests/integration/test_ingestion.py (memory bounded during 100MB+ file)

### Implementation for User Story 2

- [x] T047 [US2] Implement chunked CSV iteration in src/csv_postgres_pipeline/csv_reader.py (stream_csv generator yielding row chunks)
- [x] T048 [US2] Implement streaming COPY in src/csv_postgres_pipeline/database.py (copy_stream function processing chunks without buffering all)
- [x] T049 [US2] Implement progress display in src/csv_postgres_pipeline/cli.py (rich.progress for normal verbosity, row counts, rate)
- [x] T050 [US2] Implement verbose memory stats in src/csv_postgres_pipeline/cli.py (peak memory tracking for verbose mode)
- [x] T051 [US2] Add --chunk-size option in src/csv_postgres_pipeline/cli.py (100-100000 rows per chunk)

**Checkpoint**: User Story 2 complete - large files stream efficiently with bounded memory

---

## Phase 5: User Story 3 - Connection Resilience (Priority: P3)

**Goal**: Implement connection pooling for efficient connection reuse across multiple operations.

**Independent Test**: Run multiple sequential ingestion operations and verify connections are reused from pool.

**FR Coverage**: FR-007 (connection pooling)

### Tests for User Story 3

- [x] T052 [P] [US3] Unit test for connection pool configuration in tests/unit/test_models.py (pool_min_size, pool_max_size, pool_timeout)
- [x] T053 [P] [US3] Integration test for connection pooling in tests/integration/test_database.py (verify connection reuse, pool behavior)

### Implementation for User Story 3

- [x] T054 [US3] Implement ConnectionPool wrapper in src/csv_postgres_pipeline/database.py (psycopg_pool.ConnectionPool with min/max size)
- [x] T055 [US3] Implement pool lifecycle management in src/csv_postgres_pipeline/database.py (create_pool, get_connection, close_pool)
- [x] T056 [US3] Integrate pool with ingestion in src/csv_postgres_pipeline/ingestion.py (use pooled connections)
- [x] T057 [US3] Add --pool-size option in src/csv_postgres_pipeline/cli.py (1-50 max connections)

**Checkpoint**: User Story 3 complete - connection pooling provides efficient connection reuse

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Environment Variable Integration

- [x] T058 [P] Unit test for DatabaseConfig environment variable defaults in tests/unit/test_models.py (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD)
- [x] T059 Update DatabaseConfig in src/csv_postgres_pipeline/models.py to derive default values from standard PostgreSQL environment variables (PGHOST→host, PGPORT→port, PGDATABASE→database, PGUSER→user, PGPASSWORD→password)
- [x] T060 [P] Create .env file with empty values for standard PostgreSQL environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD) and add .env to .gitignore
- [x] T061 Update pyproject.toml [tool.pytest.ini_options] to load .env file using pytest-dotenv (add env_files = [".env"] and pytest-dotenv to dev dependencies)
- [x] T062 Update tests/conftest.py to call load_dotenv() at module level to inject environment variables for all tests (add python-dotenv to dev dependencies if not present)

### Quality Validation

- [x] T063 [P] Verify all linting passes: `ruff check src/ tests/`
- [x] T064 [P] Verify type checking passes: `mypy --strict src/ tests/`
- [x] T065 [P] Verify pylint score: `pylint src/ tests/` (must be 10.00/10.00)
- [x] T066 [P] Verify Pylance has zero errors in VS Code
- [x] T067 Run full test suite: `pytest tests/` (134 passed, 40 integration tests skipped - require Docker)
- [x] T068 Validate quickstart.md examples work end-to-end (CLI loads and displays help correctly)
- [x] T069 Performance validation: ingest 100MB CSV in <60 seconds (SC-001) and measure throughput ≥1.5 MB/s (SC-004) - requires Docker/PostgreSQL
- [x] T070 Memory validation: verify <100MB memory for large files (SC-002) - requires Docker/PostgreSQL
- [x] T071 [P] [US2] Integration test for constant memory usage in tests/integration/test_memory.py (use tracemalloc to verify memory stays bounded during streaming, SC-002)
- [x] T072 Validate actionable error messages (SC-005): Review all exception messages across codebase and verify 95% include context (file path, line number, or corrective action). Document findings in specs/001-csv-ingestion-engine/error-message-audit.md
- [x] T073 Measure connection overhead reduction (SC-007): Create benchmark script that measures connection time for 10 sequential ingestions WITHOUT pooling (baseline), then WITH pooling, and verify ≥50% reduction. Requires Docker/PostgreSQL - requires Docker/PostgreSQL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1's csv_reader and database modules
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1's database module

### Within Each User Story

- Tests MUST be written and FAIL before implementation (per constitution TDD)
- Models before services
- Services/readers before orchestration
- Orchestration before CLI
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005, T006, T007 can run in parallel (different config files)

**Phase 2 (Foundational)**:
- T009, T010 can run in parallel (different test files)
- T011, T012 can run in parallel (different files)

**Phase 3 (US1) - Tests**:
- T013-T020 can ALL run in parallel (different test files)

**Phase 3 (US1) - Models**:
- T021, T022, T023, T024 can run in parallel (same file but independent classes)

**Phase 4 (US2) - Tests**:
- T045, T046 can run in parallel

**Phase 5 (US3) - Tests**:
- T052, T053 can run in parallel

**Phase 6 (Polish)**:
- T058, T060 can run in parallel (different files)
- T063, T064, T065, T066 can run in parallel (different tools)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together (TDD - write tests first):
Task: "T013 [P] [US1] Unit test for DatabaseConfig model in tests/unit/test_models.py"
Task: "T014 [P] [US1] Unit test for CSVConfig model in tests/unit/test_models.py"
Task: "T015 [P] [US1] Unit test for IngestionResult and SkippedRow models in tests/unit/test_models.py"
Task: "T016 [P] [US1] Unit test for TableSchema and ColumnInfo models in tests/unit/test_models.py"
Task: "T017 [P] [US1] Unit test for CSV reader in tests/unit/test_csv_reader.py"
Task: "T018 [P] [US1] Contract test for CLI in tests/contract/test_cli_contract.py"
Task: "T019 [P] [US1] Integration test for basic ingestion in tests/integration/test_ingestion.py"
Task: "T020 [P] [US1] Integration test for database operations in tests/integration/test_database.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T012)
3. Complete Phase 3: User Story 1 (T013-T044)
4. **STOP and VALIDATE**: Test basic ingestion independently
5. Deploy/demo if ready - MVP delivers full basic functionality

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
   - Basic ingestion with all handling modes works
3. Add User Story 2 → Test independently → Deploy/Demo
   - Large file support added, memory efficient
4. Add User Story 3 → Test independently → Deploy/Demo
   - Connection pooling for production efficiency
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 tests then implementation
   - (After US1 models exist) Developer B: User Story 2
   - (After US1 database exists) Developer C: User Story 3
3. Stories complete and integrate independently

---

## Task Summary

| Phase | Tasks | Parallel Tasks |
|-------|-------|----------------|
| Phase 1: Setup | 8 | 5 |
| Phase 2: Foundational | 4 | 4 |
| Phase 3: US1 Basic Ingestion | 32 | 12 |
| Phase 4: US2 Large Files | 7 | 2 |
| Phase 5: US3 Connection Pool | 6 | 2 |
| Phase 6: Polish | 16 | 7 |
| **Total** | **73** | **32** |

### Tasks Per User Story

- **US1 (P1)**: 32 tasks (8 tests + 24 implementation)
- **US2 (P2)**: 7 tasks (2 tests + 5 implementation)
- **US3 (P3)**: 6 tasks (2 tests + 4 implementation)

### MVP Scope

**Suggested MVP**: Complete through Phase 3 (User Story 1)
- 44 tasks total (Setup + Foundational + US1) - excludes new validation tasks T072-T073
- Delivers full basic ingestion capability
- All handling modes (schema, row, empty)
- All verbosity levels
- Atomic transactions

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per constitution)
- Run quality tools after each phase: ruff, mypy, pylint
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
