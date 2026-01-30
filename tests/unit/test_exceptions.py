"""Unit tests for the exception hierarchy.

Tests all exception types, inheritance relationships, and attributes.
Written following TDD - these tests should FAIL before implementation.
"""

from pathlib import Path

from src.csv_postgres_pipeline.exceptions import (
    ConfigurationError,
    CSVError,
    DatabaseError,
    EmptyFileError,
    IngestionError,
    MalformedRowError,
    SchemaMismatchError,
    TransactionError,
)
from src.csv_postgres_pipeline.exceptions import (
    ConnectionError as PipelineConnectionError,
)


class TestIngestionError:
    """Tests for the base IngestionError exception."""

    def test_ingestion_error_exists(self) -> None:
        """Test that IngestionError can be imported."""
        assert IngestionError is not None

    def test_ingestion_error_is_exception(self) -> None:
        """Test that IngestionError inherits from Exception."""
        assert issubclass(IngestionError, Exception)

    def test_ingestion_error_with_message(self) -> None:
        """Test that IngestionError accepts a message."""
        error: IngestionError = IngestionError("Test error message")
        assert str(error) == "Test error message"


class TestCSVError:
    """Tests for CSV-related exceptions."""

    def test_csv_error_exists(self) -> None:
        """Test that CSVError can be imported."""
        assert CSVError is not None

    def test_csv_error_inherits_from_ingestion_error(self) -> None:
        """Test that CSVError inherits from IngestionError."""
        assert issubclass(CSVError, IngestionError)

    def test_csv_error_has_file_path_attribute(self) -> None:
        """Test that CSVError stores the file path."""
        path: Path = Path("/path/to/file.csv")
        error: CSVError = CSVError("Error", file_path=path)
        assert error.file_path == path

    def test_csv_error_has_optional_line_number(self) -> None:
        """Test that CSVError can store line number."""
        path: Path = Path("/path/to/file.csv")
        error: CSVError = CSVError("Error", file_path=path, line_number=42)
        assert error.line_number == 42

    def test_csv_error_line_number_defaults_to_none(self) -> None:
        """Test that line_number defaults to None."""
        path: Path = Path("/path/to/file.csv")
        error: CSVError = CSVError("Error", file_path=path)
        assert error.line_number is None


class TestEmptyFileError:
    """Tests for EmptyFileError exception."""

    def test_empty_file_error_exists(self) -> None:
        """Test that EmptyFileError can be imported."""
        assert EmptyFileError is not None

    def test_empty_file_error_inherits_from_csv_error(self) -> None:
        """Test that EmptyFileError inherits from CSVError."""
        assert issubclass(EmptyFileError, CSVError)

    def test_empty_file_error_with_file_path(self) -> None:
        """Test EmptyFileError stores file path."""
        path: Path = Path("/path/to/empty.csv")
        error: EmptyFileError = EmptyFileError("File is empty", file_path=path)
        assert error.file_path == path


class TestMalformedRowError:
    """Tests for MalformedRowError exception."""

    def test_malformed_row_error_exists(self) -> None:
        """Test that MalformedRowError can be imported."""
        assert MalformedRowError is not None

    def test_malformed_row_error_inherits_from_csv_error(self) -> None:
        """Test that MalformedRowError inherits from CSVError."""
        assert issubclass(MalformedRowError, CSVError)

    def test_malformed_row_error_has_column_counts(self) -> None:
        """Test MalformedRowError stores expected and actual column counts."""
        path: Path = Path("/path/to/file.csv")
        error: MalformedRowError = MalformedRowError(
            "Row has wrong column count",
            file_path=path,
            line_number=5,
            expected_columns=3,
            actual_columns=2,
        )
        assert error.expected_columns == 3
        assert error.actual_columns == 2
        assert error.line_number == 5


class TestDatabaseError:
    """Tests for database-related exceptions."""

    def test_database_error_exists(self) -> None:
        """Test that DatabaseError can be imported."""
        assert DatabaseError is not None

    def test_database_error_inherits_from_ingestion_error(self) -> None:
        """Test that DatabaseError inherits from IngestionError."""
        assert issubclass(DatabaseError, IngestionError)

    def test_database_error_with_message(self) -> None:
        """Test DatabaseError accepts a message."""
        error: DatabaseError = DatabaseError("Connection failed")
        assert str(error) == "Connection failed"


class TestConnectionError:
    """Tests for ConnectionError exception."""

    def test_connection_error_exists(self) -> None:
        """Test that ConnectionError can be imported."""
        assert PipelineConnectionError is not None

    def test_connection_error_inherits_from_database_error(self) -> None:
        """Test that ConnectionError inherits from DatabaseError."""
        assert issubclass(PipelineConnectionError, DatabaseError)


class TestSchemaMismatchError:
    """Tests for SchemaMismatchError exception."""

    def test_schema_mismatch_error_exists(self) -> None:
        """Test that SchemaMismatchError can be imported."""
        assert SchemaMismatchError is not None

    def test_schema_mismatch_error_inherits_from_database_error(self) -> None:
        """Test that SchemaMismatchError inherits from DatabaseError."""
        assert issubclass(SchemaMismatchError, DatabaseError)

    def test_schema_mismatch_error_has_column_lists(self) -> None:
        """Test SchemaMismatchError stores column comparison details."""
        error: SchemaMismatchError = SchemaMismatchError(
            "Schema mismatch",
            csv_columns=["id", "name", "email", "phone"],
            table_columns=["id", "name", "email"],
            missing_in_table=["phone"],
            missing_in_csv=[],
        )
        assert error.csv_columns == ["id", "name", "email", "phone"]
        assert error.table_columns == ["id", "name", "email"]
        assert error.missing_in_table == ["phone"]
        assert error.missing_in_csv == []


class TestTransactionError:
    """Tests for TransactionError exception."""

    def test_transaction_error_exists(self) -> None:
        """Test that TransactionError can be imported."""
        assert TransactionError is not None

    def test_transaction_error_inherits_from_database_error(self) -> None:
        """Test that TransactionError inherits from DatabaseError."""
        assert issubclass(TransactionError, DatabaseError)

    def test_transaction_error_with_message(self) -> None:
        """Test TransactionError accepts a message."""
        error: TransactionError = TransactionError("Transaction rolled back")
        assert str(error) == "Transaction rolled back"


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_exists(self) -> None:
        """Test that ConfigurationError can be imported."""
        assert ConfigurationError is not None

    def test_configuration_error_inherits_from_ingestion_error(self) -> None:
        """Test that ConfigurationError inherits from IngestionError."""
        assert issubclass(ConfigurationError, IngestionError)

    def test_configuration_error_with_message(self) -> None:
        """Test ConfigurationError accepts a message."""
        error: ConfigurationError = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
