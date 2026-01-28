"""Custom exception hierarchy for CSV Postgres Pipeline.

Provides specific exception types for different error categories:
- CSV errors (file issues, malformed data)
- Database errors (connection, schema, transaction)
- Configuration errors (invalid options)
"""

from pathlib import Path


class IngestionError(Exception):
    """Base exception for all CSV ingestion errors.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch all ingestion-related errors with a single handler.
    """


class CSVError(IngestionError):
    """Base exception for CSV-related errors.

    Attributes:
        file_path: Path to the CSV file that caused the error.
        line_number: Optional line number where the error occurred.
    """

    def __init__(
        self,
        message: str,
        *,
        file_path: Path,
        line_number: int | None = None,
    ) -> None:
        """Initialize CSVError with file context.

        Args:
            message: Human-readable error description.
            file_path: Path to the problematic CSV file.
            line_number: Optional line number where error occurred.
        """
        super().__init__(message)
        self.file_path: Path = file_path
        self.line_number: int | None = line_number


class EmptyFileError(CSVError):
    """Raised when a CSV file is empty or contains only headers.

    This error is raised when the empty file handling mode is 'strict'
    and the file has no data rows.
    """


class MalformedRowError(CSVError):
    """Raised when a CSV row has an inconsistent column count.

    Attributes:
        expected_columns: Number of columns expected (from header row).
        actual_columns: Number of columns found in the problematic row.
    """

    def __init__(
        self,
        message: str,
        *,
        file_path: Path,
        line_number: int | None = None,
        expected_columns: int,
        actual_columns: int,
    ) -> None:
        """Initialize MalformedRowError with column count details.

        Args:
            message: Human-readable error description.
            file_path: Path to the CSV file.
            line_number: Line number of the malformed row.
            expected_columns: Expected column count from headers.
            actual_columns: Actual column count in the row.
        """
        super().__init__(message, file_path=file_path, line_number=line_number)
        self.expected_columns: int = expected_columns
        self.actual_columns: int = actual_columns


class DatabaseError(IngestionError):
    """Base exception for database-related errors.

    Covers connection issues, schema problems, and transaction failures.
    """


class ConnectionError(DatabaseError):  # noqa: A001
    """Raised when database connection cannot be established.

    Note: This shadows the built-in ConnectionError intentionally
    to provide domain-specific error handling within the pipeline.
    Import with alias if needed alongside built-in.
    """


class SchemaMismatchError(DatabaseError):
    """Raised when CSV headers don't match the target table schema.

    Attributes:
        csv_columns: List of column names from the CSV file.
        table_columns: List of column names from the database table.
        missing_in_table: Columns in CSV but not in table.
        missing_in_csv: Columns in table but not in CSV.
    """

    def __init__(
        self,
        message: str,
        *,
        csv_columns: list[str],
        table_columns: list[str],
        missing_in_table: list[str],
        missing_in_csv: list[str],
    ) -> None:
        """Initialize SchemaMismatchError with schema comparison details.

        Args:
            message: Human-readable error description.
            csv_columns: Column names from the CSV file.
            table_columns: Column names from the database table.
            missing_in_table: Columns present in CSV but missing in table.
            missing_in_csv: Columns present in table but missing in CSV.
        """
        super().__init__(message)
        self.csv_columns: list[str] = csv_columns
        self.table_columns: list[str] = table_columns
        self.missing_in_table: list[str] = missing_in_table
        self.missing_in_csv: list[str] = missing_in_csv


class TransactionError(DatabaseError):
    """Raised when a database transaction fails and is rolled back.

    This indicates that all changes made during the ingestion
    have been reverted to maintain data integrity.
    """


class ConfigurationError(IngestionError):
    """Raised when CLI options or configuration are invalid.

    Examples include missing required parameters, invalid option values,
    or conflicting configuration settings.
    """
