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
- ALL module-level variables MUST have explicit type annotations
- ALL local variables MUST have explicit type annotations (even when the type appears obvious from assignment)
  - Including variables in test functions: `result: SomeType = function_call()`
  - Including loop variables where practical: `item: ItemType`
  - Including comprehension results: `items: list[str] = [x for x in source]`
- Generator types must be fully specified: `Generator[YieldType, SendType, ReturnType]`
- Type hints are required in ALL cases unless there is a specific technical reason preventing it

**Verification Protocol** (CRITICAL):
When verifying type hint compliance, you MUST check ALL Python files systematically:

1. Run `mypy --strict src/ tests/ scripts/` to catch function-level violations
2. Run `python scripts/check_local_var_types.py src/**/*.py tests/**/*.py scripts/**/*.py` to catch missing local variable type hints
3. **AUTOMATED ENFORCEMENT**: The pre-commit hook `check-local-var-types` automatically enforces local variable type annotations
4. Search for patterns: `= ` without `: Type =` on the same line
5. Test files are ESPECIALLY prone to missing local variable hints - the checker double-checks every test function

**Static Analysis** (Required):

- `mypy --strict`: MUST pass with ZERO errors
- `pylint`: MUST achieve 10.00/10.00 score
- `ruff check`: MUST pass with ZERO violations
- `ruff format`: MUST pass (code auto-formatted)
- `python scripts/check_local_var_types.py <files>`: MUST pass (enforces local variable type hints)

**Automated Enforcement** (NEW):

Since mypy, ruff, and pylint don't enforce local variable type annotations (they allow type inference per PEP 484), this project uses a **custom AST-based checker**:

- **Script**: `scripts/check_local_var_types.py`
- **Pre-commit hook**: `check-local-var-types` (runs automatically on commit)
- **Purpose**: Enforces "ALL local variables MUST have explicit type annotations"
- **Usage**: `python scripts/check_local_var_types.py src/**/*.py tests/**/*.py scripts/**/*.py`

The checker uses a **pragmatic approach** to balance strictness with practicality:
- ✅ **Allows**: Obvious constructor calls like `config = DatabaseConfig(...)` (self-documenting)
- ❌ **Requires annotations**: Non-obvious types like `peak_mb = peak / (1024 * 1024)`, `result = some_function()`

**Exemptions** (allowed by the checker):
- **Obvious constructor calls**: `config = ClassName(...)`, `obj = module.Type(...)` (pragmatic)
- Unpacking assignments: `_, x = func()` (tuple returns)
- Loop variables in for loops (optional per constitution: "where practical")
- Context manager targets: `with ... as var:`
- Exception handlers: `except Exception as e:`
- Augmented assignments: `x += 1` (variable already exists)

**Code Standards** (Required):

- PEP 8: ALL imports at top of file (no inline imports except where absolutely necessary with justification)
- Docstrings: ALL public functions, classes, and modules
- Line length: Maximum 100 characters
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

### ⚠️ CRITICAL: CONFIGURATION MANAGEMENT - NO RULE RELAXATION (NON-NEGOTIABLE)

**NEVER modify pyproject.toml, ruff.toml, or other configuration files to relax quality standards.**

#### Absolute Prohibitions

You MUST NEVER:

- ❌ **Add rules to disable lists** in pyproject.toml `[tool.pylint."messages control"]`
- ❌ **Add blanket `# pylint: disable` comments** without line-level justification
- ❌ **Disable PEP 8 checks** (import-outside-toplevel, line-too-long, etc.)
- ❌ **Relax mypy strictness** (no-warn-return-any, allow-untyped-defs, etc.)
- ❌ **Exclude files from quality checks** without explicit constitutional amendment
- ❌ **Increase complexity thresholds** (max-args, max-locals, max-branches)
- ❌ **Add ruff `--fix` auto-suppressions** (type: ignore, noqa, etc.)
- ❌ **Justify rule relaxation with "performance", "convenience", or "it's just a test"**

#### When You Encounter Quality Violations

**The ONLY acceptable response:**

1. **Fix the code** to comply with the standard
2. **Refactor** if the code is legitimately too complex
3. **Ask the user** if you genuinely cannot comply without architectural changes

**NEVER:**

- Disable the rule globally
- Add the rule to a disable list
- Exclude files or directories from checks
- Suggest "temporarily" disabling the rule

#### Line-Level Exceptions (Rare)

If a violation is **truly unavoidable** (e.g., external API requires specific pattern):

```python
# pylint: disable=rule-name  # JUSTIFICATION: Specific technical reason why this is required
problematic_code()
# pylint: enable=rule-name
```

**Requirements for line-level exceptions:**

- ✅ Must have explicit `# JUSTIFICATION:` comment explaining why
- ✅ Must be narrowly scoped (1-5 lines maximum)
- ✅ Must re-enable the rule immediately after
- ✅ Must have technical justification (not "convenience" or "performance")
- ✅ Must be reviewed in code review

#### Why This Matters

Configuration-based rule relaxation:

- Creates **invisible violations** that pass quality checks
- Violates the **NO DOUBLE STANDARDS** policy
- Makes the **constitution meaningless** (rules exist but aren't enforced)
- Allows **technical debt** to accumulate silently
- **Misleads developers** into thinking 10.00/10.00 means compliant code
- Creates **false confidence** in code quality

#### Enforcement

- Any PR that modifies disable lists will be rejected
- Quality gates MUST catch constitutional violations
- Configuration changes require explicit constitutional amendment
- Line-level exceptions must be justified in code review

**Bottom line**: The constitution defines the standards. Configuration enforces them. Never modify configuration to avoid compliance.

## Recent Changes

- 001-csv-ingestion-engine: Added Python 3.13 (per constitution and pyproject.toml) + psycopg[pool] 3.x (PostgreSQL driver with native COPY and pooling), Pydantic v2 (data validation per constitution), click (CLI framework)
- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

- 001-csv-ingestion-engine: Added Python 3.13 (per pyproject.toml requirements)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
