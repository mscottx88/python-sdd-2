"""CSV reader module for streaming CSV files.

Provides functions for reading headers, iterating rows, and validating CSV data.
Supports configurable handling modes for malformed rows.
"""

import csv
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Literal

from src.csv_postgres_pipeline.exceptions import EmptyFileError, MalformedRowError


def is_file_empty(file_path: Path) -> bool:
    """Check if a file is empty (zero bytes).

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file is empty, False otherwise.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return file_path.stat().st_size == 0


def read_headers(file_path: Path) -> list[str]:
    """Read the header row from a CSV file.

    Args:
        file_path: Path to the CSV file.

    Returns:
        List of header column names.

    Raises:
        FileNotFoundError: If the file does not exist.
        EmptyFileError: If the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        raise EmptyFileError(f"CSV file is empty: {file_path}", file_path=file_path)

    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            return headers
        except StopIteration:
            raise EmptyFileError(
                f"CSV file is empty: {file_path}", file_path=file_path
            ) from None


def iterate_rows(
    file_path: Path,
    *,
    allow_empty: bool = False,  # noqa: ARG001
) -> Generator[list[str]]:
    """Iterate over data rows in a CSV file, skipping the header.

    Args:
        file_path: Path to the CSV file.
        allow_empty: If True, allow files with only headers (unused, for API).

    Yields:
        Each data row as a list of strings.

    Raises:
        FileNotFoundError: If the file does not exist.
        EmptyFileError: If the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        raise EmptyFileError(f"CSV file is empty: {file_path}", file_path=file_path)

    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        # Skip header row
        try:
            next(reader)
        except StopIteration:
            raise EmptyFileError(
                f"CSV file is empty: {file_path}", file_path=file_path
            ) from None

        # Yield data rows
        yield from reader


def iterate_rows_with_line_numbers(
    file_path: Path,
) -> Generator[tuple[int, list[str]]]:
    """Iterate over data rows with their line numbers.

    Line numbers are 1-indexed, where line 1 is the header row.
    Data rows start at line 2.

    Args:
        file_path: Path to the CSV file.

    Yields:
        Tuples of (line_number, row_data).

    Raises:
        FileNotFoundError: If the file does not exist.
        EmptyFileError: If the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        raise EmptyFileError(f"CSV file is empty: {file_path}", file_path=file_path)

    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        # Skip header row (line 1)
        try:
            next(reader)
        except StopIteration:
            raise EmptyFileError(
                f"CSV file is empty: {file_path}", file_path=file_path
            ) from None

        # Yield data rows with line numbers starting at 2
        for line_number, row in enumerate(reader, start=2):  # noqa: UP028
            yield line_number, row


def validate_row(
    row: list[str],
    *,
    expected_columns: int,
) -> tuple[bool, str]:
    """Validate a row has the expected number of columns.

    Args:
        row: The row data to validate.
        expected_columns: The expected number of columns.

    Returns:
        Tuple of (is_valid, reason). If valid, reason is empty string.
    """
    actual_columns = len(row)
    if actual_columns == expected_columns:
        return True, ""
    return (
        False,
        f"Expected {expected_columns} columns, got {actual_columns} columns",
    )


def count_rows(file_path: Path) -> int:
    """Count the number of data rows in a CSV file (excluding header).

    Args:
        file_path: Path to the CSV file.

    Returns:
        Number of data rows.

    Raises:
        FileNotFoundError: If the file does not exist.
        EmptyFileError: If the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        raise EmptyFileError(f"CSV file is empty: {file_path}", file_path=file_path)

    count = 0
    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        # Skip header
        try:
            next(reader)
        except StopIteration:
            return 0

        for _ in reader:
            count += 1

    return count


def has_data_rows(file_path: Path) -> bool:
    """Check if a CSV file has data rows (beyond the header).

    Args:
        file_path: Path to the CSV file.

    Returns:
        True if the file has at least one data row, False otherwise.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        return False

    with file_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        # Skip header
        try:
            next(reader)
        except StopIteration:
            return False

        # Check if there's at least one data row
        try:
            next(reader)
            return True
        except StopIteration:
            return False


RowMode = Literal["strict", "skip", "lenient"]


def iterate_rows_validated(
    file_path: Path,
    *,
    mode: RowMode = "strict",
) -> tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]] | Iterator[list[str]]:
    """Iterate over CSV rows with validation and configurable error handling.

    Args:
        file_path: Path to the CSV file.
        mode: How to handle malformed rows:
            - "strict": Raise MalformedRowError on first invalid row
            - "skip": Skip invalid rows, return them in a separate list
            - "lenient": Pad short rows with empty strings, truncate long rows

    Returns:
        In "strict" mode: Just the row iterator (raises on error)
        In "skip" mode: Tuple of (valid_rows_iterator, skipped_rows_list)
        In "lenient" mode: Tuple of (adjusted_rows_iterator, empty list)

    Raises:
        MalformedRowError: In strict mode when a row has wrong column count.
        EmptyFileError: If the file is empty.
    """
    headers = read_headers(file_path)
    expected_columns = len(headers)

    if mode == "strict":
        return _iterate_strict(file_path, expected_columns)
    if mode == "skip":
        return _iterate_skip(file_path, expected_columns)
    # lenient mode
    return _iterate_lenient(file_path, expected_columns)


def _iterate_strict(
    file_path: Path,
    expected_columns: int,
) -> Iterator[list[str]]:
    """Iterate rows in strict mode - raise on any malformed row."""

    def generator() -> Generator[list[str]]:
        for line_number, row in iterate_rows_with_line_numbers(file_path):
            is_valid, _ = validate_row(row, expected_columns=expected_columns)
            if not is_valid:
                msg = (
                    f"Row at line {line_number} has {len(row)} columns, "
                    f"expected {expected_columns}"
                )
                raise MalformedRowError(
                    msg,
                    file_path=file_path,
                    line_number=line_number,
                    expected_columns=expected_columns,
                    actual_columns=len(row),
                )
            yield row

    return generator()


def _iterate_skip(
    file_path: Path,
    expected_columns: int,
) -> tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]]:
    """Iterate rows in skip mode - collect invalid rows separately."""
    skipped: list[tuple[int, str, list[str]]] = []

    def generator() -> Generator[list[str]]:
        for line_number, row in iterate_rows_with_line_numbers(file_path):
            is_valid, reason = validate_row(row, expected_columns=expected_columns)
            if is_valid:
                yield row
            else:
                skipped.append((line_number, reason, row))

    return generator(), skipped


def _iterate_lenient(
    file_path: Path,
    expected_columns: int,
) -> tuple[Iterator[list[str]], list[tuple[int, str, list[str]]]]:
    """Iterate rows in lenient mode - pad/truncate to match expected columns."""

    def generator() -> Generator[list[str]]:
        for _line_number, row in iterate_rows_with_line_numbers(file_path):
            actual_columns = len(row)
            if actual_columns < expected_columns:
                # Pad with empty strings
                row = row + [""] * (expected_columns - actual_columns)
            elif actual_columns > expected_columns:
                # Truncate
                row = row[:expected_columns]
            yield row

    return generator(), []


def iterate_chunks(
    file_path: Path,
    chunk_size: int = 1000,
) -> Generator[list[list[str]]]:
    """Iterate over CSV rows in chunks for memory-efficient processing.

    This function enables streaming large CSV files without loading
    the entire file into memory.

    Args:
        file_path: Path to the CSV file.
        chunk_size: Number of rows per chunk (default 1000).

    Yields:
        Lists of rows, each list containing up to chunk_size rows.

    Raises:
        FileNotFoundError: If the file does not exist.
        EmptyFileError: If the file is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_file_empty(file_path):
        raise EmptyFileError(f"CSV file is empty: {file_path}", file_path=file_path)

    chunk: list[list[str]] = []
    for row in iterate_rows(file_path):
        chunk.append(row)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    # Yield any remaining rows
    if chunk:
        yield chunk


def iterate_chunks_validated(
    file_path: Path,
    chunk_size: int = 1000,
    *,
    mode: RowMode = "strict",
) -> (
    Generator[list[list[str]]]
    | tuple[Generator[list[list[str]]], list[tuple[int, str, list[str]]]]
):
    """Iterate over CSV rows in validated chunks with configurable error handling.

    This function combines chunked iteration with row validation for
    memory-efficient processing of large files with validation.

    Args:
        file_path: Path to the CSV file.
        chunk_size: Number of rows per chunk (default 1000).
        mode: How to handle malformed rows:
            - "strict": Raise MalformedRowError on first invalid row
            - "skip": Skip invalid rows, return them in a separate list
            - "lenient": Pad short rows with empty strings, truncate long rows

    Returns:
        In "strict" mode: Generator yielding validated chunks
        In "skip" mode: Tuple of (chunk_generator, skipped_rows_list)
        In "lenient" mode: Tuple of (adjusted_chunk_generator, empty list)

    Raises:
        MalformedRowError: In strict mode when a row has wrong column count.
        EmptyFileError: If the file is empty.
    """
    headers = read_headers(file_path)
    expected_columns = len(headers)

    if mode == "strict":
        return _iterate_chunks_strict(file_path, chunk_size, expected_columns)
    if mode == "skip":
        return _iterate_chunks_skip(file_path, chunk_size, expected_columns)
    # lenient mode
    return _iterate_chunks_lenient(file_path, chunk_size, expected_columns)


def _iterate_chunks_strict(
    file_path: Path,
    chunk_size: int,
    expected_columns: int,
) -> Generator[list[list[str]]]:
    """Iterate chunks in strict mode - raise on any malformed row."""
    chunk: list[list[str]] = []

    for line_number, row in iterate_rows_with_line_numbers(file_path):
        is_valid, _ = validate_row(row, expected_columns=expected_columns)
        if not is_valid:
            msg = (
                f"Row at line {line_number} has {len(row)} columns, "
                f"expected {expected_columns}"
            )
            raise MalformedRowError(
                msg,
                file_path=file_path,
                line_number=line_number,
                expected_columns=expected_columns,
                actual_columns=len(row),
            )
        chunk.append(row)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


def _iterate_chunks_skip(
    file_path: Path,
    chunk_size: int,
    expected_columns: int,
) -> tuple[Generator[list[list[str]]], list[tuple[int, str, list[str]]]]:
    """Iterate chunks in skip mode - collect invalid rows separately."""
    skipped: list[tuple[int, str, list[str]]] = []

    def generator() -> Generator[list[list[str]]]:
        chunk: list[list[str]] = []

        for line_number, row in iterate_rows_with_line_numbers(file_path):
            is_valid, reason = validate_row(row, expected_columns=expected_columns)
            if is_valid:
                chunk.append(row)
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            else:
                skipped.append((line_number, reason, row))

        if chunk:
            yield chunk

    return generator(), skipped


def _iterate_chunks_lenient(
    file_path: Path,
    chunk_size: int,
    expected_columns: int,
) -> tuple[Generator[list[list[str]]], list[tuple[int, str, list[str]]]]:
    """Iterate chunks in lenient mode - pad/truncate to match expected columns."""

    def generator() -> Generator[list[list[str]]]:
        chunk: list[list[str]] = []

        for _line_number, row in iterate_rows_with_line_numbers(file_path):
            actual_columns = len(row)
            if actual_columns < expected_columns:
                row = row + [""] * (expected_columns - actual_columns)
            elif actual_columns > expected_columns:
                row = row[:expected_columns]
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

        if chunk:
            yield chunk

    return generator(), []
