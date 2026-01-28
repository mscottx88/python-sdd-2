"""Unit tests for the CSV reader module.

Tests header parsing, row iteration, empty file detection, and malformed row handling.
Written following TDD - these tests should FAIL before implementation.
"""

from pathlib import Path

import pytest


class TestCSVReader:
    """Tests for CSV reader functionality (T017)."""

    def test_csv_reader_module_exists(self) -> None:
        """Test that csv_reader module can be imported."""
        from src.csv_postgres_pipeline import csv_reader

        assert csv_reader is not None

    def test_read_headers(self, sample_csv_file: Path) -> None:
        """Test reading headers from a CSV file."""
        from src.csv_postgres_pipeline.csv_reader import read_headers

        headers = read_headers(sample_csv_file)
        assert headers == ["id", "name", "email"]

    def test_read_headers_empty_file(self, empty_csv_file: Path) -> None:
        """Test reading headers from an empty file raises error."""
        from src.csv_postgres_pipeline.csv_reader import read_headers
        from src.csv_postgres_pipeline.exceptions import EmptyFileError

        with pytest.raises(EmptyFileError):
            read_headers(empty_csv_file)

    def test_read_headers_file_not_found(self) -> None:
        """Test reading headers from non-existent file raises error."""
        from src.csv_postgres_pipeline.csv_reader import read_headers

        with pytest.raises(FileNotFoundError):
            read_headers(Path("/nonexistent/file.csv"))

    def test_iterate_rows(self, sample_csv_file: Path) -> None:
        """Test iterating over CSV rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows

        rows = list(iterate_rows(sample_csv_file))
        assert len(rows) == 3
        assert rows[0] == ["1", "Alice", "alice@example.com"]
        assert rows[1] == ["2", "Bob", "bob@example.com"]
        assert rows[2] == ["3", "Charlie", "charlie@example.com"]

    def test_iterate_rows_skips_header(self, sample_csv_file: Path) -> None:
        """Test that iterate_rows skips the header row."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows

        rows = list(iterate_rows(sample_csv_file))
        # Should not include header row
        assert ["id", "name", "email"] not in rows

    def test_iterate_rows_empty_file(self, empty_csv_file: Path) -> None:
        """Test iterating over an empty file."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows
        from src.csv_postgres_pipeline.exceptions import EmptyFileError

        with pytest.raises(EmptyFileError):
            list(iterate_rows(empty_csv_file))

    def test_iterate_rows_headers_only(self, headers_only_csv_file: Path) -> None:
        """Test iterating over a headers-only file yields no rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows

        rows = list(iterate_rows(headers_only_csv_file, allow_empty=True))
        assert len(rows) == 0

    def test_validate_row_column_count(self) -> None:
        """Test row validation for column count."""
        from src.csv_postgres_pipeline.csv_reader import validate_row

        # Valid row
        valid, _ = validate_row(["1", "Alice", "alice@test.com"], expected_columns=3)
        assert valid is True

        # Too few columns
        valid, reason = validate_row(["1", "Alice"], expected_columns=3)
        assert valid is False
        assert "columns" in reason.lower()

        # Too many columns
        valid, reason = validate_row(
            ["1", "Alice", "alice@test.com", "extra"], expected_columns=3
        )
        assert valid is False
        assert "columns" in reason.lower()

    def test_count_rows(self, sample_csv_file: Path) -> None:
        """Test counting rows in a CSV file (excluding header)."""
        from src.csv_postgres_pipeline.csv_reader import count_rows

        count = count_rows(sample_csv_file)
        assert count == 3

    def test_count_rows_headers_only(self, headers_only_csv_file: Path) -> None:
        """Test counting rows in a headers-only file."""
        from src.csv_postgres_pipeline.csv_reader import count_rows

        count = count_rows(headers_only_csv_file)
        assert count == 0

    def test_is_file_empty(self, empty_csv_file: Path) -> None:
        """Test detecting an empty file."""
        from src.csv_postgres_pipeline.csv_reader import is_file_empty

        assert is_file_empty(empty_csv_file) is True

    def test_is_file_empty_with_content(self, sample_csv_file: Path) -> None:
        """Test detecting a non-empty file."""
        from src.csv_postgres_pipeline.csv_reader import is_file_empty

        assert is_file_empty(sample_csv_file) is False

    def test_has_data_rows(self, sample_csv_file: Path) -> None:
        """Test detecting a file with data rows."""
        from src.csv_postgres_pipeline.csv_reader import has_data_rows

        assert has_data_rows(sample_csv_file) is True

    def test_has_data_rows_headers_only(self, headers_only_csv_file: Path) -> None:
        """Test detecting a headers-only file."""
        from src.csv_postgres_pipeline.csv_reader import has_data_rows

        assert has_data_rows(headers_only_csv_file) is False

    def test_iterate_rows_with_line_numbers(self, sample_csv_file: Path) -> None:
        """Test iterating rows with line numbers."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows_with_line_numbers

        rows = list(iterate_rows_with_line_numbers(sample_csv_file))
        assert len(rows) == 3
        # Line numbers should be 2, 3, 4 (line 1 is header)
        assert rows[0][0] == 2  # First data row at line 2
        assert rows[1][0] == 3
        assert rows[2][0] == 4
        assert rows[0][1] == ["1", "Alice", "alice@example.com"]


class TestChunkedCSVReading:
    """Tests for chunked CSV reading (T045) - streaming large files."""

    def test_iterate_chunks_function_exists(self) -> None:
        """Test that iterate_chunks function exists in csv_reader module."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        assert iterate_chunks is not None

    def test_iterate_chunks_yields_lists(self, sample_csv_file: Path) -> None:
        """Test that iterate_chunks yields lists of rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        chunks = list(iterate_chunks(sample_csv_file, chunk_size=2))
        assert all(isinstance(chunk, list) for chunk in chunks)

    def test_iterate_chunks_respects_chunk_size(self, sample_csv_file: Path) -> None:
        """Test that chunks do not exceed the specified size."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        chunk_size = 2
        chunks = list(iterate_chunks(sample_csv_file, chunk_size=chunk_size))
        for chunk in chunks[:-1]:  # All but last chunk should be full
            assert len(chunk) == chunk_size
        # Last chunk can be smaller
        assert len(chunks[-1]) <= chunk_size

    def test_iterate_chunks_returns_all_rows(self, sample_csv_file: Path) -> None:
        """Test that all rows are returned across chunks."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        chunks = list(iterate_chunks(sample_csv_file, chunk_size=2))
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 3  # Sample file has 3 data rows

    def test_iterate_chunks_with_large_file(self, large_csv_file: Path) -> None:
        """Test chunked iteration with a large file."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        chunk_size = 1000
        chunks = list(iterate_chunks(large_csv_file, chunk_size=chunk_size))
        total_rows = sum(len(chunk) for chunk in chunks)
        assert total_rows == 10000  # Large file has 10000 rows
        assert len(chunks) == 10  # 10000 / 1000 = 10 chunks

    def test_iterate_chunks_default_chunk_size(self, sample_csv_file: Path) -> None:
        """Test that default chunk size is used when not specified."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        # Should not raise error with default chunk size
        chunks = list(iterate_chunks(sample_csv_file))
        assert len(chunks) >= 1

    def test_iterate_chunks_with_validation(self, sample_csv_file: Path) -> None:
        """Test chunked iteration with row validation."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks_validated

        chunks_result = iterate_chunks_validated(
            sample_csv_file, chunk_size=2, mode="strict"
        )
        chunks_list: list[list[list[str]]] = list(chunks_result)  # type: ignore[arg-type]
        total_rows: int = sum(len(chunk) for chunk in chunks_list)
        assert total_rows == 3

    def test_iterate_chunks_validated_skip_mode(self, malformed_csv_file: Path) -> None:
        """Test chunked validation skips malformed rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks_validated

        result = iterate_chunks_validated(malformed_csv_file, chunk_size=2, mode="skip")
        chunks, skipped = result
        chunks_list: list[list[list[str]]] = list(chunks)  # type: ignore[arg-type]
        total_valid_rows: int = sum(len(chunk) for chunk in chunks_list)
        assert total_valid_rows == 1  # Only one valid row
        assert len(skipped) == 2  # Two malformed rows

    def test_iterate_chunks_empty_file(self, empty_csv_file: Path) -> None:
        """Test chunked iteration on empty file raises error."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks
        from src.csv_postgres_pipeline.exceptions import EmptyFileError

        with pytest.raises(EmptyFileError):
            list(iterate_chunks(empty_csv_file, chunk_size=2))

    def test_iterate_chunks_headers_only(self, headers_only_csv_file: Path) -> None:
        """Test chunked iteration on headers-only file yields empty list."""
        from src.csv_postgres_pipeline.csv_reader import iterate_chunks

        chunks = list(iterate_chunks(headers_only_csv_file, chunk_size=2))
        assert chunks == [] or (len(chunks) == 0)


class TestCSVReaderMalformedHandling:
    """Tests for malformed row handling in CSV reader."""

    def test_iterate_rows_strict_mode(self, malformed_csv_file: Path) -> None:
        """Test strict mode fails on malformed rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows_validated
        from src.csv_postgres_pipeline.exceptions import MalformedRowError

        with pytest.raises(MalformedRowError):
            list(iterate_rows_validated(malformed_csv_file, mode="strict"))

    def test_iterate_rows_skip_mode(self, malformed_csv_file: Path) -> None:
        """Test skip mode skips malformed rows and continues."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows_validated

        rows, skipped = iterate_rows_validated(malformed_csv_file, mode="skip")
        rows_list = list(rows)
        # Should have only the valid row
        assert len(rows_list) == 1
        assert rows_list[0] == ["1", "Alice", "alice@example.com"]
        # Should have skipped 2 rows
        assert len(skipped) == 2

    def test_iterate_rows_lenient_mode(self, malformed_csv_file: Path) -> None:
        """Test lenient mode pads/truncates rows."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows_validated

        rows, _ = iterate_rows_validated(malformed_csv_file, mode="lenient")
        rows_list = list(rows)
        # Should have all rows, adjusted
        assert len(rows_list) == 3
        # Second row should be padded with None/empty
        assert len(rows_list[1]) == 3
        # Third row should be truncated
        assert len(rows_list[2]) == 3
