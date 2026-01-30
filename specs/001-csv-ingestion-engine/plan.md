# Implementation Plan: CSV Ingestion Engine

**Branch**: `001-csv-ingestion-engine` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-csv-ingestion-engine/spec.md`

## Summary

Build a Python CLI tool that ingests single CSV files into PostgreSQL using streaming (COPY protocol) with connection pooling. The tool supports configurable error handling modes for schema mismatches, malformed rows, and empty files, with atomic transaction semantics ensuring data integrity on failures.

## Technical Context

**Language/Version**: Python 3.13 (per constitution and pyproject.toml)
**Primary Dependencies**: psycopg[pool] 3.x (PostgreSQL driver with native COPY and pooling), Pydantic v2 (data validation per constitution), click (CLI framework)
**Storage**: PostgreSQL (modern versions supporting COPY, transactions, advanced types)
**Testing**: pytest with pytest-postgresql for integration tests
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)
**Project Type**: single (src/, tests/ layout per constitution)
**Performance Goals**: 100MB CSV in <60 seconds (SC-001), streaming throughput >1.5 MB/s
**Constraints**: <100MB memory regardless of input file size (SC-002), atomic transactions
**Scale/Scope**: Single-user CLI tool, single-file ingestion per invocation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with [constitution.md](../../.specify/memory/constitution.md):

- [x] **Type Safety First** - Plan includes mypy strict mode verification, all code will have explicit type hints including test code
- [x] **Specification-Driven Development** - This plan follows spec.md with prioritized user stories (P1: Basic Ingestion, P2: Large Files, P3: Connection Pooling)
- [x] **Test-Driven Development** - Test strategy confirms tests will be written BEFORE implementation (Red-Green-Refactor), pytest-postgresql for integration tests
- [x] **Code Quality Standards** - Plan confirms Ruff linting/formatting (90 char), pylint 10.00/10.00, Pylance zero errors, PEP 8 compliance
- [x] **Automation** - Pre-commit hooks (ruff, mypy, pylint) and CI/CD gates will be configured

**Complexity Justification Required?** No violations. All constitution principles will be followed.

## Project Structure

### Documentation (this feature)

```text
specs/001-csv-ingestion-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contract)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── csv_postgres_pipeline/
│   ├── __init__.py
│   ├── cli.py           # Click CLI entrypoint
│   ├── models.py        # Pydantic models (DatabaseConfig, CSVConfig, IngestionResult)
│   ├── database.py      # Connection pool management, COPY execution
│   ├── csv_reader.py    # Streaming CSV reader with validation
│   ├── ingestion.py     # Main ingestion orchestration
│   └── exceptions.py    # Custom exception hierarchy

tests/
├── conftest.py          # Shared fixtures, Docker/DB verification
├── contract/
│   └── test_cli_contract.py
├── integration/
│   ├── test_ingestion.py
│   └── test_database.py
└── unit/
    ├── test_models.py
    ├── test_csv_reader.py
    └── test_exceptions.py
```

**Structure Decision**: Single project layout selected per constitution. CLI tool with clear separation: models (Pydantic), database (psycopg pool + COPY), CSV reading (streaming), and orchestration (ingestion service).

## Complexity Tracking

> No violations identified. All features implementable within constitution guidelines.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
