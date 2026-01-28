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

### ⚠️ CRITICAL: NO DOUBLE STANDARDS - ALL PYTHON CODE (NON-NEGOTIABLE)

**ALL Python files MUST meet the EXACT SAME strict quality standards. ZERO EXCEPTIONS.**

This is a core constitutional principle (see constitution.md "Test Code Quality Requirements").

#### What "ALL Python files" means:

- ✅ `src/` - Production code
- ✅ `tests/` - Test code (unit, integration, contract)
- ✅ `scripts/` - Utility scripts, benchmarks, migrations, data processing
- ✅ `tools/` - Development tools, code generators, analyzers
- ✅ `examples/` - Example code, demos, tutorials
- ✅ `docs/` - Documentation code snippets (if executable)
- ✅ `benchmarks/` - Performance benchmarks
- ✅ `config/` - Configuration scripts
- ✅ Root-level Python files - `setup.py`, `conftest.py`, etc.
- ✅ **ANY `.py` file ANYWHERE in the repository**

#### What you MUST NEVER do:

- ❌ **NEVER** relax mypy, pylint, or ruff rules for ANY Python files
- ❌ **NEVER** add mypy overrides like `disallow_untyped_defs = false` for ANY directory
- ❌ **NEVER** exclude ANY Python files from quality checks in .pre-commit-config.yaml
- ❌ **NEVER** treat ANY Python code as "second-class" code
- ❌ **NEVER** say "it's just a script" or "it's just a benchmark" as justification for lower quality
- ❌ **NEVER** add `# type: ignore` without specific, justified type codes
- ❌ **NEVER** skip type hints because "the file is small" or "it's temporary"

#### Requirements for EVERY Python file in the repository:

**Type Annotations** (Required):
- ALL functions must have explicit return type annotations (including `-> None`)
- ALL function parameters must have type annotations
- ALL module-level variables should have type annotations where type isn't obvious
- Generator types must be fully specified: `Generator[YieldType, SendType, ReturnType]`

**Static Analysis** (Required):
- `mypy --strict`: MUST pass with ZERO errors
- `pylint`: MUST achieve 10.00/10.00 score
- `ruff check`: MUST pass with ZERO violations
- `ruff format`: MUST pass (code auto-formatted)

**Code Standards** (Required):
- PEP 8: ALL imports at top of file (no inline imports except where absolutely necessary with justification)
- Docstrings: ALL public functions, classes, and modules
- Line length: Maximum 90 characters
- File encoding: UTF-8 with LF line endings (not CRLF)

#### Rationale:

**Why this matters:**
1. **Scripts are code** - They run in production environments, CI/CD, and developer machines
2. **Benchmarks are code** - They validate performance requirements and influence architecture decisions
3. **Tests are code** - They execute as frequently as production code and must be maintainable
4. **Tools are code** - They shape development workflow and can introduce bugs if poorly written
5. **Examples are code** - They teach users and represent the project's quality standards

**Consequences of poor quality "utility" code:**
- ❌ Scripts fail silently in CI/CD pipelines
- ❌ Benchmarks give misleading performance data
- ❌ Tests provide false confidence
- ❌ Tools introduce bugs into the development process
- ❌ Technical debt spreads from "quick scripts" to the entire codebase
- ❌ New contributors learn bad patterns from low-quality examples

**Bottom line**: If it's written in Python and checked into this repository, it meets our strict quality standards. No exceptions.

## Recent Changes
- 001-csv-ingestion-engine: Added Python 3.13 (per constitution and pyproject.toml) + psycopg[pool] 3.x (PostgreSQL driver with native COPY and pooling), Pydantic v2 (data validation per constitution), click (CLI framework)
- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
