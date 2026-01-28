"""Unit tests for the exception hierarchy.

Tests all exception types, inheritance relationships, and attributes.
Written following TDD - these tests should FAIL before implementation.
"""

from pathlib import Path


class TestIngestionError:
    """Tests for the base IngestionError exception."""

    def test_ingestion_error_exists(self) -> None:
        """Test that IngestionError can be imported."""
        from src.csv_postgres_pipeline.exceptions import IngestionError

        assert IngestionError is not None

    def test_ingestion_error_is_exception(self) -> None:
        """Test that IngestionError inherits from Exception."""
        from src.csv_postgres_pipeline.exceptions import IngestionError

        assert issubclass(IngestionError, Exception)

    def test_ingestion_error_with_message(self) -> None:
        """Test that IngestionError accepts a message."""
        from src.csv_postgres_pipeline.exceptions import IngestionError

        error = IngestionError("Test error message")
        assert str(error) == "Test error message"


class TestCSVError:
    """Tests for CSV-related exceptions."""

    def test_csv_error_exists(self) -> None:
        """Test that CSVError can be imported."""
        from src.csv_postgres_pipeline.exceptions import CSVError

        assert CSVError is not None

    def test_csv_error_inherits_from_ingestion_error(self) -> None:
        """Test that CSVError inherits from IngestionError."""
        from src.csv_postgres_pipeline.exceptions import CSVError, IngestionError

        assert issubclass(CSVError, IngestionError)

    def test_csv_error_has_file_path_attribute(self) -> None:
        """Test that CSVError stores the file path."""
        from src.csv_postgres_pipeline.exceptions import CSVError

        path = Path("/path/to/file.csv")
        error = CSVError("Error", file_path=path)
        assert error.file_path == path

    def test_csv_error_has_optional_line_number(self) -> None:
        """Test that CSVError can store line number."""
        from src.csv_postgres_pipeline.exceptions import CSVError

        path = Path("/path/to/file.csv")
        error = CSVError("Error", file_path=path, line_number=42)
        assert error.line_number == 42

    def test_csv_error_line_number_defaults_to_none(self) -> None:
        """Test that line_number defaults to None."""
        from src.csv_postgres_pipeline.exceptions import CSVError

        path = Path("/path/to/file.csv")
        error = CSVError("Error", file_path=path)
        assert error.line_number is None


class TestEmptyFileError:
    """Tests for EmptyFileError exception."""

    def test_empty_file_error_exists(self) -> None:
        """Test that EmptyFileError can be imported."""
        from src.csv_postgres_pipeline.exceptions import EmptyFileError

        assert EmptyFileError is not None

    def test_empty_file_error_inherits_from_csv_error(self) -> None:
        """Test that EmptyFileError inherits from CSVError."""
        from src.csv_postgres_pipeline.exceptions import CSVError, EmptyFileError

        assert issubclass(EmptyFileError, CSVError)

    def test_empty_file_error_with_file_path(self) -> None:
        """Test EmptyFileError stores file path."""
        from src.csv_postgres_pipeline.exceptions import EmptyFileError

        path = Path("/path/to/empty.csv")
        error = EmptyFileError("File is empty", file_path=path)
        assert error.file_path == path


class TestMalformedRowError:
    """Tests for MalformedRowError exception."""

    def test_malformed_row_error_exists(self) -> None:
        """Test that MalformedRowError can be imported."""
        from src.csv_postgres_pipeline.exceptions import MalformedRowError

        assert MalformedRowError is not None

    def test_malformed_row_error_inherits_from_csv_error(self) -> None:
        """Test that MalformedRowError inherits from CSVError."""
        from src.csv_postgres_pipeline.exceptions import CSVError, MalformedRowError

        assert issubclass(MalformedRowError, CSVError)

    def test_malformed_row_error_has_column_counts(self) -> None:
        """Test MalformedRowError stores expected and actual column counts."""
        from src.csv_postgres_pipeline.exceptions import MalformedRowError

        path = Path("/path/to/file.csv")
        error = MalformedRowError(
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
        from src.csv_postgres_pipeline.exceptions import DatabaseError

        assert DatabaseError is not None

    def test_database_error_inherits_from_ingestion_error(self) -> None:
        """Test that DatabaseError inherits from IngestionError."""
        from src.csv_postgres_pipeline.exceptions import DatabaseError, IngestionError

        assert issubclass(DatabaseError, IngestionError)

    def test_database_error_with_message(self) -> None:
        """Test DatabaseError accepts a message."""
        from src.csv_postgres_pipeline.exceptions import DatabaseError

        error = DatabaseError("Connection failed")
        assert str(error) == "Connection failed"


class TestConnectionError:
    """Tests for ConnectionError exception."""

    def test_connection_error_exists(self) -> None:
        """Test that ConnectionError can be imported."""
        from src.csv_postgres_pipeline.exceptions import (
            ConnectionError as PipelineConnectionError,
        )

        assert PipelineConnectionError is not None

    def test_connection_error_inherits_from_database_error(self) -> None:
        """Test that ConnectionError inherits from DatabaseError."""
        from src.csv_postgres_pipeline.exceptions import (
            ConnectionError as PipelineConnectionError,
        )
        from src.csv_postgres_pipeline.exceptions import DatabaseError

        assert issubclass(PipelineConnectionError, DatabaseError)


class TestSchemaMismatchError:
    """Tests for SchemaMismatchError exception."""

    def test_schema_mismatch_error_exists(self) -> None:
        """Test that SchemaMismatchError can be imported."""
        from src.csv_postgres_pipeline.exceptions import SchemaMismatchError

        assert SchemaMismatchError is not None

    def test_schema_mismatch_error_inherits_from_database_error(self) -> None:
        """Test that SchemaMismatchError inherits from DatabaseError."""
        from src.csv_postgres_pipeline.exceptions import (
            DatabaseError,
            SchemaMismatchError,
        )

        assert issubclass(SchemaMismatchError, DatabaseError)

    def test_schema_mismatch_error_has_column_lists(self) -> None:
        """Test SchemaMismatchError stores column comparison details."""
        from src.csv_postgres_pipeline.exceptions import SchemaMismatchError

        error = SchemaMismatchError(
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
        from src.csv_postgres_pipeline.exceptions import TransactionError

        assert TransactionError is not None

    def test_transaction_error_inherits_from_database_error(self) -> None:
        """Test that TransactionError inherits from DatabaseError."""
        from src.csv_postgres_pipeline.exceptions import DatabaseError, TransactionError

        assert issubclass(TransactionError, DatabaseError)

    def test_transaction_error_with_message(self) -> None:
        """Test TransactionError accepts a message."""
        from src.csv_postgres_pipeline.exceptions import TransactionError

        error = TransactionError("Transaction rolled back")
        assert str(error) == "Transaction rolled back"


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_exists(self) -> None:
        """Test that ConfigurationError can be imported."""
        from src.csv_postgres_pipeline.exceptions import ConfigurationError

        assert ConfigurationError is not None

    def test_configuration_error_inherits_from_ingestion_error(self) -> None:
        """Test that ConfigurationError inherits from IngestionError."""
        from src.csv_postgres_pipeline.exceptions import (
            ConfigurationError,
            IngestionError,
        )

        assert issubclass(ConfigurationError, IngestionError)

    def test_configuration_error_with_message(self) -> None:
        """Test ConfigurationError accepts a message."""
        from src.csv_postgres_pipeline.exceptions import ConfigurationError

        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
