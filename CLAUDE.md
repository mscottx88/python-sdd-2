# python-sdd-2 Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-26

**Constitution**: This file reflects HOW principles are applied. For WHAT principles govern this project, see [constitution.md](.specify/memory/constitution.md).

## Active Technologies
- PostgreSQL (modern versions supporting COPY, transactions, and advanced types) (001-csv-ingestion-engine)
- Python 3.13 (per constitution and pyproject.toml) + psycopg[pool] 3.x (PostgreSQL driver with native COPY and pooling), Pydantic v2 (data validation per constitution), click (CLI framework) (001-csv-ingestion-engine)
- PostgreSQL (modern versions supporting COPY, transactions, advanced types) (001-csv-ingestion-engine)

- Python 3.13 (per pyproject.toml requirements) (001-csv-ingestion-engine)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.13 (per pyproject.toml requirements): Follow standard conventions

### ⚠️ CRITICAL: NO DOUBLE STANDARDS (NON-NEGOTIABLE)

**Test code MUST meet the EXACT SAME quality standards as production code.**

This is a core constitutional principle (see constitution.md "Test Code Quality Requirements"):

- ❌ **NEVER** relax mypy, pylint, or ruff rules for test files
- ❌ **NEVER** add mypy overrides like `disallow_untyped_defs = false` for tests
- ❌ **NEVER** exclude tests from quality checks in .pre-commit-config.yaml
- ❌ **NEVER** treat test code as "second-class" code

**Requirements for ALL Python files (src/ AND tests/):**
- Type hints: ALL functions must have explicit type annotations including `-> None`
- Mypy: MUST pass `mypy --strict` with zero errors
- Pylint: MUST achieve 10.00/10.00 score
- Ruff: MUST pass with zero violations
- PEP 8: ALL imports at top of file, ZERO inline imports

**Rationale**: Poor quality test code undermines TDD, creates technical debt, blocks refactoring, and provides false confidence. Tests are executed as frequently as production code and must be equally maintainable.

## Recent Changes
- 001-csv-ingestion-engine: Added Python 3.13 (per constitution and pyproject.toml) + psycopg[pool] 3.x (PostgreSQL driver with native COPY and pooling), Pydantic v2 (data validation per constitution), click (CLI framework)
- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
