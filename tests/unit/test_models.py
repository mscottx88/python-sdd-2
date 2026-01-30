"""Unit tests for Pydantic models.

Tests validation rules, serialization, and business logic.
Written following TDD - these tests should FAIL before implementation.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from src.csv_postgres_pipeline.models import (
    ColumnInfo,
    CSVConfig,
    DatabaseConfig,
    IngestionResult,
    SkippedRow,
    TableSchema,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig model (T013)."""

    def test_database_config_exists(self) -> None:
        """Test that DatabaseConfig can be imported."""
        assert DatabaseConfig is not None

    def test_database_config_with_required_fields(self) -> None:
        """Test creating DatabaseConfig with required fields."""
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.database == "testdb"
        assert config.user == "admin"
        assert config.password.get_secret_value() == "secret"

    def test_database_config_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test DatabaseConfig default values for optional fields."""
        # Clear environment variables to test true defaults
        monkeypatch.delenv("PGHOST", raising=False)
        monkeypatch.delenv("PGPORT", raising=False)
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.pool_min_size == 1
        assert config.pool_max_size == 5
        assert config.pool_timeout == 30.0

    def test_database_config_port_validation(self) -> None:
        """Test port number validation (1-65535)."""
        # Valid port
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            port=5433,
        )
        assert config.port == 5433

        # Invalid port - too low
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                port=0,
            )

        # Invalid port - too high
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                port=70000,
            )

    def test_database_config_connection_string(self) -> None:
        """Test connection string generation."""
        config: DatabaseConfig = DatabaseConfig(
            host="db.example.com",
            port=5433,
            database="mydb",
            user="admin",
            password=SecretStr("secret123"),
        )
        conn_str: str = config.connection_string
        assert "postgresql://" in conn_str
        assert "admin" in conn_str
        assert "secret123" in conn_str
        assert "db.example.com" in conn_str
        assert "5433" in conn_str
        assert "mydb" in conn_str

    def test_database_config_empty_database_fails(self) -> None:
        """Test that empty database name is rejected."""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="",
                user="admin",
                password=SecretStr("secret"),
            )


class TestConnectionPoolConfig:
    """Tests for connection pool configuration (T052)."""

    def test_pool_config_default_values(self) -> None:
        """Test default pool configuration values."""
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.pool_min_size == 1
        assert config.pool_max_size == 5
        assert config.pool_timeout == 30.0

    def test_pool_min_size_validation(self) -> None:
        """Test pool_min_size validation bounds (1-10)."""
        # Valid min size
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            pool_min_size=5,
        )
        assert config.pool_min_size == 5

        # Invalid - too low
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_min_size=0,
            )

        # Invalid - too high
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_min_size=15,
            )

    def test_pool_max_size_validation(self) -> None:
        """Test pool_max_size validation bounds (1-50)."""
        # Valid max size
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            pool_max_size=25,
        )
        assert config.pool_max_size == 25

        # Edge case - max allowed
        config = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            pool_max_size=50,
        )
        assert config.pool_max_size == 50

        # Invalid - too low
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_max_size=0,
            )

        # Invalid - too high
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_max_size=100,
            )

    def test_pool_timeout_validation(self) -> None:
        """Test pool_timeout validation (must be positive)."""
        # Valid timeout
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            pool_timeout=60.0,
        )
        assert config.pool_timeout == 60.0

        # Invalid - zero
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_timeout=0,
            )

        # Invalid - negative
        with pytest.raises(ValidationError):
            DatabaseConfig(
                database="testdb",
                user="admin",
                password=SecretStr("secret"),
                pool_timeout=-10.0,
            )

    def test_pool_config_from_url(self) -> None:
        """Test pool configuration through from_url method."""
        config: DatabaseConfig = DatabaseConfig.from_url(
            "postgresql://user:pass@localhost:5432/mydb",
            pool_min_size=2,
            pool_max_size=20,
            pool_timeout=45.0,
        )
        assert config.pool_min_size == 2
        assert config.pool_max_size == 20
        assert config.pool_timeout == 45.0

    def test_pool_config_custom_values(self) -> None:
        """Test custom pool configuration values."""
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
            pool_min_size=3,
            pool_max_size=15,
            pool_timeout=120.0,
        )
        assert config.pool_min_size == 3
        assert config.pool_max_size == 15
        assert config.pool_timeout == 120.0


class TestCSVConfig:
    """Tests for CSVConfig model (T014)."""

    def test_csv_config_exists(self) -> None:
        """Test that CSVConfig can be imported."""
        assert CSVConfig is not None

    def test_csv_config_with_required_fields(self) -> None:
        """Test creating CSVConfig with required fields."""
        config: CSVConfig = CSVConfig(
            file_path=Path("/data/test.csv"),
            table_name="users",
        )
        assert config.file_path == Path("/data/test.csv")
        assert config.table_name == "users"

    def test_csv_config_default_modes(self) -> None:
        """Test default handling mode values."""
        config: CSVConfig = CSVConfig(
            file_path=Path("/data/test.csv"),
            table_name="users",
        )
        assert config.schema_mode == "strict"
        assert config.row_mode == "strict"
        assert config.empty_mode == "strict"

    def test_csv_config_mode_enums(self) -> None:
        """Test valid mode values."""
        config: CSVConfig = CSVConfig(
            file_path=Path("/data/test.csv"),
            table_name="users",
            schema_mode="alter",
            row_mode="skip",
            empty_mode="permissive",
        )
        assert config.schema_mode == "alter"
        assert config.row_mode == "skip"
        assert config.empty_mode == "permissive"

    def test_csv_config_invalid_mode_fails(self) -> None:
        """Test that invalid mode values are rejected."""
        with pytest.raises(ValidationError):
            CSVConfig(
                file_path=Path("/data/test.csv"),
                table_name="users",
                schema_mode="invalid",  # type: ignore[arg-type]
            )

    def test_csv_config_table_name_pattern(self) -> None:
        """Test table name validation (valid PostgreSQL identifier)."""
        # Valid table names
        CSVConfig(file_path=Path("/data/test.csv"), table_name="users")
        CSVConfig(file_path=Path("/data/test.csv"), table_name="_private_table")
        CSVConfig(file_path=Path("/data/test.csv"), table_name="table_123")

        # Invalid table names
        with pytest.raises(ValidationError):
            CSVConfig(file_path=Path("/data/test.csv"), table_name="123table")

        with pytest.raises(ValidationError):
            CSVConfig(file_path=Path("/data/test.csv"), table_name="table-name")

    def test_csv_config_chunk_size_bounds(self) -> None:
        """Test chunk size validation (100-100000)."""
        # Valid chunk size
        config: CSVConfig = CSVConfig(
            file_path=Path("/data/test.csv"),
            table_name="users",
            chunk_size=5000,
        )
        assert config.chunk_size == 5000

        # Invalid - too small
        with pytest.raises(ValidationError):
            CSVConfig(
                file_path=Path("/data/test.csv"),
                table_name="users",
                chunk_size=50,
            )

        # Invalid - too large
        with pytest.raises(ValidationError):
            CSVConfig(
                file_path=Path("/data/test.csv"),
                table_name="users",
                chunk_size=200000,
            )


class TestIngestionResult:
    """Tests for IngestionResult and SkippedRow models (T015)."""

    def test_ingestion_result_exists(self) -> None:
        """Test that IngestionResult can be imported."""
        assert IngestionResult is not None

    def test_skipped_row_exists(self) -> None:
        """Test that SkippedRow can be imported."""
        assert SkippedRow is not None

    def test_ingestion_result_success(self) -> None:
        """Test creating a successful IngestionResult."""
        now: datetime = datetime.now()
        result: IngestionResult = IngestionResult(
            status="success",
            rows_processed=1000,
            rows_inserted=1000,
            table_name="users",
            started_at=now,
            completed_at=now,
            duration_seconds=5.5,
        )
        assert result.status == "success"
        assert result.rows_processed == 1000
        assert result.rows_inserted == 1000
        assert result.rows_skipped == 0

    def test_ingestion_result_partial(self) -> None:
        """Test creating a partial success IngestionResult."""
        now: datetime = datetime.now()
        skipped: list[Any] = [
            SkippedRow(line_number=5, reason="Malformed row"),
            SkippedRow(line_number=10, reason="Missing column"),
        ]
        result: IngestionResult = IngestionResult(
            status="partial",
            rows_processed=100,
            rows_inserted=98,
            rows_skipped=2,
            skipped_rows=skipped,
            table_name="users",
            started_at=now,
            completed_at=now,
            duration_seconds=1.2,
        )
        assert result.status == "partial"
        assert result.rows_skipped == 2
        assert result.skipped_rows is not None
        assert len(result.skipped_rows) == 2

    def test_ingestion_result_failed(self) -> None:
        """Test creating a failed IngestionResult."""
        now: datetime = datetime.now()
        result: IngestionResult = IngestionResult(
            status="failed",
            rows_processed=50,
            rows_inserted=0,
            table_name="users",
            started_at=now,
            completed_at=now,
            duration_seconds=0.5,
            error_message="Schema mismatch",
        )
        assert result.status == "failed"
        assert result.error_message == "Schema mismatch"

    def test_ingestion_result_table_created_flag(self) -> None:
        """Test table_created flag."""
        now: datetime = datetime.now()
        result: IngestionResult = IngestionResult(
            status="success",
            rows_processed=100,
            rows_inserted=100,
            table_name="new_table",
            table_created=True,
            started_at=now,
            completed_at=now,
            duration_seconds=2.0,
        )
        assert result.table_created is True

    def test_skipped_row_with_content(self) -> None:
        """Test SkippedRow with raw content."""
        row: SkippedRow = SkippedRow(
            line_number=42,
            reason="Too many columns",
            raw_content="1,Alice,alice@test.com,extra,data",
        )
        assert row.line_number == 42
        assert row.reason == "Too many columns"
        assert row.raw_content is not None


class TestTableSchema:
    """Tests for TableSchema and ColumnInfo models (T016)."""

    def test_table_schema_exists(self) -> None:
        """Test that TableSchema can be imported."""
        assert TableSchema is not None

    def test_column_info_exists(self) -> None:
        """Test that ColumnInfo can be imported."""
        assert ColumnInfo is not None

    def test_table_schema_basic(self) -> None:
        """Test creating a basic TableSchema."""
        columns: list[Any] = [
            ColumnInfo(name="id", data_type="INTEGER", ordinal_position=1),
            ColumnInfo(name="name", data_type="TEXT", ordinal_position=2),
        ]
        schema: TableSchema = TableSchema(
            table_name="users",
            columns=columns,
            exists=True,
        )
        assert schema.table_name == "users"
        assert len(schema.columns) == 2
        assert schema.exists is True

    def test_table_schema_get_column_names(self) -> None:
        """Test get_column_names returns ordered list."""
        columns: list[ColumnInfo] = [
            ColumnInfo(name="email", ordinal_position=3),
            ColumnInfo(name="id", ordinal_position=1),
            ColumnInfo(name="name", ordinal_position=2),
        ]
        schema: TableSchema = TableSchema(table_name="users", columns=columns, exists=True)
        names: list[str] = schema.get_column_names()
        assert names == ["id", "name", "email"]

    def test_table_schema_has_column(self) -> None:
        """Test has_column case-insensitive lookup."""
        columns: list[ColumnInfo] = [
            ColumnInfo(name="ID", ordinal_position=1),
            ColumnInfo(name="Name", ordinal_position=2),
        ]
        schema: TableSchema = TableSchema(table_name="users", columns=columns, exists=True)

        assert schema.has_column("ID") is True
        assert schema.has_column("id") is True
        assert schema.has_column("name") is True
        assert schema.has_column("NAME") is True
        assert schema.has_column("email") is False

    def test_column_info_defaults(self) -> None:
        """Test ColumnInfo default values."""
        col: Any = ColumnInfo(name="data", ordinal_position=1)
        assert col.data_type == "TEXT"
        assert col.nullable is True

    def test_table_schema_not_exists(self) -> None:
        """Test TableSchema for non-existent table."""
        schema: TableSchema = TableSchema(table_name="new_table", exists=False)
        assert schema.exists is False
        assert len(schema.columns) == 0


class TestDatabaseConfigEnvironmentVariables:
    """Tests for DatabaseConfig environment variable defaults (T058)."""

    def test_host_from_pghost_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test host defaults to PGHOST environment variable."""
        monkeypatch.setenv("PGHOST", "db.example.com")
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.host == "db.example.com"

    def test_port_from_pgport_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test port defaults to PGPORT environment variable."""
        monkeypatch.setenv("PGPORT", "5433")
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.port == 5433

    def test_database_from_pgdatabase_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database defaults to PGDATABASE environment variable."""
        monkeypatch.setenv("PGDATABASE", "mydb")
        config: DatabaseConfig = DatabaseConfig(
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.database == "mydb"

    def test_user_from_pguser_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test user defaults to PGUSER environment variable."""
        monkeypatch.setenv("PGUSER", "dbuser")
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            password=SecretStr("secret"),
        )
        assert config.user == "dbuser"

    def test_password_from_pgpassword_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test password defaults to PGPASSWORD environment variable."""
        monkeypatch.setenv("PGPASSWORD", "secretpass")
        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
        )
        assert config.password.get_secret_value() == "secretpass"

    def test_explicit_values_override_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test explicit values override environment variables."""
        monkeypatch.setenv("PGHOST", "env-host")
        monkeypatch.setenv("PGPORT", "5433")
        monkeypatch.setenv("PGDATABASE", "envdb")
        monkeypatch.setenv("PGUSER", "envuser")
        monkeypatch.setenv("PGPASSWORD", "envpass")

        config: DatabaseConfig = DatabaseConfig(
            host="explicit-host",
            port=5434,
            database="explicitdb",
            user="explicituser",
            password=SecretStr("explicitpass"),
        )
        assert config.host == "explicit-host"
        assert config.port == 5434
        assert config.database == "explicitdb"
        assert config.user == "explicituser"
        assert config.password.get_secret_value() == "explicitpass"

    def test_all_env_vars_together(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test all environment variables work together."""
        monkeypatch.setenv("PGHOST", "testhost")
        monkeypatch.setenv("PGPORT", "5435")
        monkeypatch.setenv("PGDATABASE", "testdb")
        monkeypatch.setenv("PGUSER", "testuser")
        monkeypatch.setenv("PGPASSWORD", "testpass")

        config: DatabaseConfig = DatabaseConfig()
        assert config.host == "testhost"
        assert config.port == 5435
        assert config.database == "testdb"
        assert config.user == "testuser"
        assert config.password.get_secret_value() == "testpass"

    def test_fallback_to_defaults_without_env(self) -> None:
        """Test fallback to hardcoded defaults when env vars not set."""
        # Ensure env vars are not set
        var: str
        for var in ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]:
            os.environ.pop(var, None)

        config: DatabaseConfig = DatabaseConfig(
            database="testdb",
            user="admin",
            password=SecretStr("secret"),
        )
        assert config.host == "localhost"
        assert config.port == 5432
