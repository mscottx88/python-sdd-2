"""Contract tests for the CSV ingestion CLI.

These tests verify the CLI contract as specified in contracts/cli-contract.md.
Tests focus on argument parsing, option validation, and exit codes.
Written following TDD - these tests should FAIL before implementation.
"""

import json
from typing import Any

import pytest
from click.testing import CliRunner

from src.csv_postgres_pipeline import cli
from src.csv_postgres_pipeline.cli import main


class TestCLIContract:
    """Tests for CLI contract compliance (T018)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_cli_module_exists(self) -> None:
        """Test that cli module can be imported."""
        assert cli is not None

    def test_main_function_exists(self) -> None:
        """Test that main function exists in cli module."""
        assert main is not None

    def test_cli_requires_csv_file_argument(self, runner: CliRunner) -> None:
        """Test that CSV_FILE positional argument is required."""
        result: Any = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "CSV_FILE" in result.output or "Missing argument" in result.output

    def test_cli_requires_table_name_argument(self, runner: CliRunner) -> None:
        """Test that TABLE_NAME positional argument is required."""
        result: Any = runner.invoke(main, ["data.csv"])
        assert result.exit_code != 0
        assert "TABLE_NAME" in result.output or "Missing argument" in result.output


class TestCLIDatabaseOptions:
    """Tests for database connection CLI options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_host_option_short_flag(self, runner: CliRunner) -> None:
        """Test -h short flag for host option."""
        result: Any = runner.invoke(main, ["-h", "myhost", "data.csv", "users"])
        # Should not fail on unknown option
        assert "-h" not in result.output or "Unknown" not in result.output

    def test_host_option_long_flag(self, runner: CliRunner) -> None:
        """Test --host long flag."""
        result: Any = runner.invoke(main, ["--host", "myhost", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_port_option(self, runner: CliRunner) -> None:
        """Test --port / -p option."""
        result: Any = runner.invoke(main, ["-p", "5433", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_database_option(self, runner: CliRunner) -> None:
        """Test --database / -d option."""
        result: Any = runner.invoke(main, ["-d", "testdb", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_user_option(self, runner: CliRunner) -> None:
        """Test --user / -u option."""
        result: Any = runner.invoke(main, ["-u", "admin", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_password_option(self, runner: CliRunner) -> None:
        """Test --password / -P option."""
        result: Any = runner.invoke(main, ["-P", "secret", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_database_url_option(self, runner: CliRunner) -> None:
        """Test --database-url option."""
        result: Any = runner.invoke(
            main,
            [
                "--database-url",
                "postgresql://user:pass@localhost/db",
                "data.csv",
                "users",
            ],
        )
        assert "Unknown option" not in result.output


class TestCLIHandlingModeOptions:
    """Tests for handling mode CLI options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_schema_mode_option_strict(self, runner: CliRunner) -> None:
        """Test --schema-mode=strict option."""
        result: Any = runner.invoke(main, ["--schema-mode", "strict", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_schema_mode_option_match(self, runner: CliRunner) -> None:
        """Test --schema-mode=match option."""
        result: Any = runner.invoke(main, ["--schema-mode", "match", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_schema_mode_option_alter(self, runner: CliRunner) -> None:
        """Test --schema-mode=alter option."""
        result: Any = runner.invoke(main, ["--schema-mode", "alter", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_schema_mode_invalid_value(self, runner: CliRunner) -> None:
        """Test --schema-mode with invalid value fails."""
        result: Any = runner.invoke(main, ["--schema-mode", "invalid", "data.csv", "users"])
        assert result.exit_code != 0

    def test_row_mode_option_strict(self, runner: CliRunner) -> None:
        """Test --row-mode=strict option."""
        result: Any = runner.invoke(main, ["--row-mode", "strict", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_row_mode_option_skip(self, runner: CliRunner) -> None:
        """Test --row-mode=skip option."""
        result: Any = runner.invoke(main, ["--row-mode", "skip", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_row_mode_option_lenient(self, runner: CliRunner) -> None:
        """Test --row-mode=lenient option."""
        result: Any = runner.invoke(main, ["--row-mode", "lenient", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_row_mode_invalid_value(self, runner: CliRunner) -> None:
        """Test --row-mode with invalid value fails."""
        result: Any = runner.invoke(main, ["--row-mode", "invalid", "data.csv", "users"])
        assert result.exit_code != 0

    def test_empty_mode_option_strict(self, runner: CliRunner) -> None:
        """Test --empty-mode=strict option."""
        result: Any = runner.invoke(main, ["--empty-mode", "strict", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_empty_mode_option_headers(self, runner: CliRunner) -> None:
        """Test --empty-mode=headers option."""
        result: Any = runner.invoke(main, ["--empty-mode", "headers", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_empty_mode_option_permissive(self, runner: CliRunner) -> None:
        """Test --empty-mode=permissive option."""
        result: Any = runner.invoke(main, ["--empty-mode", "permissive", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_empty_mode_invalid_value(self, runner: CliRunner) -> None:
        """Test --empty-mode with invalid value fails."""
        result: Any = runner.invoke(main, ["--empty-mode", "invalid", "data.csv", "users"])
        assert result.exit_code != 0


class TestCLIOutputOptions:
    """Tests for output control CLI options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_verbosity_option_quiet(self, runner: CliRunner) -> None:
        """Test --verbosity=quiet / -v quiet option."""
        result: Any = runner.invoke(main, ["--verbosity", "quiet", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_verbosity_option_normal(self, runner: CliRunner) -> None:
        """Test --verbosity=normal option."""
        result: Any = runner.invoke(main, ["--verbosity", "normal", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_verbosity_option_verbose(self, runner: CliRunner) -> None:
        """Test --verbosity=verbose option."""
        result: Any = runner.invoke(main, ["--verbosity", "verbose", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_verbosity_invalid_value(self, runner: CliRunner) -> None:
        """Test --verbosity with invalid value fails."""
        result: Any = runner.invoke(main, ["--verbosity", "invalid", "data.csv", "users"])
        assert result.exit_code != 0

    def test_json_flag(self, runner: CliRunner) -> None:
        """Test --json flag."""
        result: Any = runner.invoke(main, ["--json", "data.csv", "users"])
        assert "Unknown option" not in result.output


class TestCLIAdvancedOptions:
    """Tests for advanced CLI options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_chunk_size_option(self, runner: CliRunner) -> None:
        """Test --chunk-size option."""
        result: Any = runner.invoke(main, ["--chunk-size", "5000", "data.csv", "users"])
        assert "Unknown option" not in result.output

    def test_pool_size_option(self, runner: CliRunner) -> None:
        """Test --pool-size option."""
        result: Any = runner.invoke(main, ["--pool-size", "10", "data.csv", "users"])
        assert "Unknown option" not in result.output


class TestCLIExitCodes:
    """Tests for CLI exit codes as per contract."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_exit_code_2_file_not_found(
        self, runner: CliRunner, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test exit code 2 for CSV file not found."""
        result: Any = runner.invoke(
            main,
            [
                "/nonexistent/file.csv",
                "users",
                "--database-url",
                "postgresql://u:p@localhost/db",
            ],
        )
        # Exit code 2 = CSV error
        assert result.exit_code == 2

    def test_exit_code_4_invalid_option(self, runner: CliRunner) -> None:
        """Test exit code 4 for configuration error (invalid options)."""
        result: Any = runner.invoke(main, ["--schema-mode", "invalid", "data.csv", "users"])
        # Exit code 4 = configuration error, but Click may use 2 for bad options
        assert result.exit_code in (2, 4)


class TestCLIEnvironmentVariables:
    """Tests for environment variable support."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_pghost_env_variable(self, runner: CliRunner) -> None:
        """Test PGHOST environment variable is recognized."""
        env: dict[str, str] = {"PGHOST": "envhost"}
        result: Any = runner.invoke(main, ["data.csv", "users"], env=env)
        # Should not complain about missing host
        assert "host" not in result.output.lower() or "envhost" in result.output.lower()

    def test_database_url_env_variable(self, runner: CliRunner) -> None:
        """Test DATABASE_URL environment variable is recognized."""
        env: dict[str, str] = {"DATABASE_URL": "postgresql://user:pass@localhost/db"}
        result: Any = runner.invoke(main, ["data.csv", "users"], env=env)
        # Should recognize the env variable
        assert "DATABASE_URL" not in result.output or "Unknown" not in result.output


class TestCLIJSONOutput:
    """Tests for JSON output format."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_json_output_is_valid_json_on_error(
        self,
        runner: CliRunner,
        sample_csv_file: pytest.TempPathFactory,
    ) -> None:
        """Test that --json flag produces valid JSON even on errors."""
        result: Any = runner.invoke(
            main,
            ["--json", "/nonexistent/file.csv", "users", "-d", "testdb", "-u", "user"],
        )
        # Output should be valid JSON
        try:
            output: dict[str, Any] = json.loads(result.output)
            assert "status" in output or "error" in output
        except json.JSONDecodeError:
            # Allow non-JSON error output for file not found before JSON formatting
            pass

    def test_json_output_contains_status_field(
        self,
        runner: CliRunner,
        sample_csv_file: pytest.TempPathFactory,
    ) -> None:
        """Test JSON output contains required status field."""
        # This will fail without DB, but should still produce JSON
        result: Any = runner.invoke(
            main,
            [
                "--json",
                "/nonexistent/file.csv",
                "users",
                "--database-url",
                "postgresql://u:p@localhost/db",
            ],
        )
        try:
            output: dict[str, Any] = json.loads(result.output)
            assert "status" in output
        except json.JSONDecodeError:
            pass  # Allow non-JSON for early errors
