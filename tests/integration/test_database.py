"""Integration tests for database operations.

Tests database connection, schema detection, table creation, and COPY execution.
Requires PostgreSQL (via Docker/testcontainers or local instance).
Written following TDD - these tests should FAIL before implementation.
"""

from pathlib import Path
from typing import Any

import pytest


@pytest.mark.integration
class TestDatabaseConnection:
    """Integration tests for database connection (T020)."""

    def test_database_module_exists(self) -> None:
        """Test that database module can be imported."""
        from src.csv_postgres_pipeline import database

        assert database is not None

    def test_create_connection_function_exists(self) -> None:
        """Test that create_connection function exists."""
        from src.csv_postgres_pipeline.database import create_connection

        assert create_connection is not None

    def test_create_connection_success(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test successful database connection."""
        from src.csv_postgres_pipeline.database import create_connection
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        with create_connection(db_config) as conn:
            assert conn is not None
            # Verify connection works
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result is not None
                assert result[0] == 1

    def test_create_connection_invalid_credentials(self) -> None:
        """Test connection failure with invalid credentials."""
        from pydantic import SecretStr

        from src.csv_postgres_pipeline.database import create_connection
        from src.csv_postgres_pipeline.exceptions import ConnectionError
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="nonexistent_db",
            user="invalid_user",
            password=SecretStr("invalid_password"),  # noqa: S106
        )

        with (  # noqa: SIM117
            pytest.raises((ConnectionError, Exception)),
            create_connection(db_config),
        ):
            pass


@pytest.mark.integration
class TestSchemaDetection:
    """Integration tests for schema detection."""

    def test_get_table_schema_function_exists(self) -> None:
        """Test that get_table_schema function exists."""
        from src.csv_postgres_pipeline.database import get_table_schema

        assert get_table_schema is not None

    def test_get_table_schema_existing_table(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test schema detection for existing table."""
        from src.csv_postgres_pipeline.database import create_connection, get_table_schema
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)

        with create_connection(db_config) as conn:
            # Create a test table
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_schema_table (
                        id TEXT,
                        name TEXT,
                        email TEXT
                    )
                """)
            conn.commit()

            schema = get_table_schema(conn, "test_schema_table")

            assert schema is not None
            assert "id" in schema.get_column_names()
            assert "name" in schema.get_column_names()
            assert "email" in schema.get_column_names()

            # Cleanup
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_schema_table")
            conn.commit()

    def test_get_table_schema_nonexistent_table(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test schema detection returns None for non-existent table."""
        from src.csv_postgres_pipeline.database import create_connection, get_table_schema
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)

        with create_connection(db_config) as conn:
            schema = get_table_schema(conn, "nonexistent_table_xyz")
            assert schema is None


@pytest.mark.integration
class TestTableCreation:
    """Integration tests for table creation."""

    def test_create_table_function_exists(self) -> None:
        """Test that create_table function exists."""
        from src.csv_postgres_pipeline.database import create_table

        assert create_table is not None

    def test_create_table_from_headers(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test table creation from CSV headers."""
        from src.csv_postgres_pipeline.database import (
            create_connection,
            create_table,
            get_table_schema,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        headers = ["id", "name", "email"]
        table_name = "test_create_table"

        with create_connection(db_config) as conn:
            # Ensure table doesn't exist
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

            # Create table
            create_table(conn, table_name, headers)
            conn.commit()

            # Verify table was created
            schema = get_table_schema(conn, table_name)
            assert schema is not None
            assert set(schema.get_column_names()) == set(headers)

            # Cleanup
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

    def test_create_table_all_text_columns(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test that created table has all TEXT columns."""
        from src.csv_postgres_pipeline.database import (
            create_connection,
            create_table,
            get_table_schema,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        headers = ["col1", "col2", "col3"]
        table_name = "test_text_columns"

        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

            create_table(conn, table_name, headers)
            conn.commit()

            schema = get_table_schema(conn, table_name)
            assert schema is not None
            for column in schema.columns:
                assert column.data_type.upper() == "TEXT"

            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()


@pytest.mark.integration
class TestCOPYExecution:
    """Integration tests for COPY protocol execution."""

    def test_copy_rows_function_exists(self) -> None:
        """Test that copy_rows function exists."""
        from src.csv_postgres_pipeline.database import copy_rows

        assert copy_rows is not None

    def test_copy_rows_inserts_data(
        self,
        sample_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test COPY inserts data correctly."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows, read_headers
        from src.csv_postgres_pipeline.database import (
            copy_rows,
            create_connection,
            create_table,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        table_name = "test_copy_rows"

        with create_connection(db_config) as conn:
            # Setup
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

            headers = read_headers(sample_csv_file)
            create_table(conn, table_name, headers)
            conn.commit()

            # Execute COPY
            rows = list(iterate_rows(sample_csv_file))
            rows_copied = copy_rows(conn, table_name, headers, rows)
            conn.commit()

            assert rows_copied == 3

            # Verify data
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
                result = cur.fetchone()
                assert result is not None
                count = result[0]
                assert count == 3

            # Cleanup
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

    def test_copy_rows_returns_count(
        self,
        sample_csv_file: Path,
        db_connection_params: Any,
    ) -> None:
        """Test COPY returns correct row count."""
        from src.csv_postgres_pipeline.csv_reader import iterate_rows, read_headers
        from src.csv_postgres_pipeline.database import (
            copy_rows,
            create_connection,
            create_table,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        table_name = "test_copy_count"

        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()

            headers = read_headers(sample_csv_file)
            create_table(conn, table_name, headers)
            conn.commit()

            rows = list(iterate_rows(sample_csv_file))
            rows_copied = copy_rows(conn, table_name, headers, rows)

            assert rows_copied == len(rows)

            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()


@pytest.mark.integration
class TestSchemaComparison:
    """Integration tests for schema comparison."""

    def test_compare_schemas_function_exists(self) -> None:
        """Test that compare_schemas function exists."""
        from src.csv_postgres_pipeline.database import compare_schemas

        assert compare_schemas is not None

    def test_compare_schemas_matching(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test schema comparison with matching schemas."""
        from src.csv_postgres_pipeline.database import (
            compare_schemas,
            create_connection,
            get_table_schema,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_headers = ["id", "name", "email"]

        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_match_schema (
                        id TEXT,
                        name TEXT,
                        email TEXT
                    )
                """)
            conn.commit()

            table_schema = get_table_schema(conn, "test_match_schema")
            assert table_schema is not None
            result = compare_schemas(csv_headers, table_schema)

            assert result.is_match is True
            assert len(result.missing_in_table) == 0
            assert len(result.missing_in_csv) == 0

            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_match_schema")
            conn.commit()

    def test_compare_schemas_missing_in_table(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test schema comparison detects columns missing in table."""
        from src.csv_postgres_pipeline.database import (
            compare_schemas,
            create_connection,
            get_table_schema,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        csv_headers = ["id", "name", "email", "phone"]  # phone is extra

        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_missing_col (
                        id TEXT,
                        name TEXT,
                        email TEXT
                    )
                """)
            conn.commit()

            table_schema = get_table_schema(conn, "test_missing_col")
            assert table_schema is not None
            result = compare_schemas(csv_headers, table_schema)

            assert result.is_match is False
            assert "phone" in result.missing_in_table

            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_missing_col")
            conn.commit()


@pytest.mark.integration
class TestTransactionWrapper:
    """Integration tests for atomic transaction wrapper."""

    def test_transaction_rollback_on_error(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test transaction rollback on error."""
        pytest.importorskip("psycopg", reason="psycopg not installed")

        from src.csv_postgres_pipeline.database import create_connection
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)

        with create_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_rollback")
                cur.execute("CREATE TABLE test_rollback (id TEXT)")
            conn.commit()

            # Start a transaction that will fail
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO test_rollback VALUES ('1')")
                    # Force an error
                    cur.execute("SELECT * FROM nonexistent_table")
            except Exception:
                conn.rollback()

            # Verify rollback happened
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM test_rollback")
                result = cur.fetchone()
                assert result is not None
                count = result[0]
                assert count == 0

            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS test_rollback")
            conn.commit()


@pytest.mark.integration
class TestConnectionPooling:
    """Integration tests for connection pooling (T053)."""

    def test_create_pool_function_exists(self) -> None:
        """Test that create_pool function exists."""
        from src.csv_postgres_pipeline.database import create_pool

        assert create_pool is not None

    def test_close_pool_function_exists(self) -> None:
        """Test that close_pool function exists."""
        from src.csv_postgres_pipeline.database import close_pool

        assert close_pool is not None

    def test_get_pooled_connection_function_exists(self) -> None:
        """Test that get_pooled_connection function exists."""
        from src.csv_postgres_pipeline.database import get_pooled_connection

        assert get_pooled_connection is not None

    def test_create_pool_basic(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test creating a connection pool."""
        from src.csv_postgres_pipeline.database import close_pool, create_pool
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        pool = create_pool(db_config)

        try:
            assert pool is not None
            # Pool should have min connections available
            assert pool.min_size == db_config.pool_min_size
            assert pool.max_size == db_config.pool_max_size
        finally:
            close_pool(pool)

    def test_get_pooled_connection_works(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test getting a connection from the pool."""
        from src.csv_postgres_pipeline.database import (
            close_pool,
            create_pool,
            get_pooled_connection,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(**db_connection_params)
        pool = create_pool(db_config)

        try:
            with get_pooled_connection(pool) as conn:
                assert conn is not None
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    assert result is not None
                    assert result[0] == 1
        finally:
            close_pool(pool)

    def test_connection_reuse(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test that connections are reused from pool."""
        from src.csv_postgres_pipeline.database import (
            close_pool,
            create_pool,
            get_pooled_connection,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        # Use max_size=1 to guarantee connection reuse (only one connection exists)
        db_config = DatabaseConfig(
            **db_connection_params,
            pool_min_size=1,
            pool_max_size=1,
        )
        pool = create_pool(db_config)

        try:
            # Get a connection, use it, return it
            with get_pooled_connection(pool) as conn1, conn1.cursor() as cur:  # noqa: SIM117
                cur.execute("SELECT pg_backend_pid()")
                result1 = cur.fetchone()
                assert result1 is not None
                pid1 = result1[0]

            # Get another connection - must be reused since max_size=1
            with get_pooled_connection(pool) as conn2, conn2.cursor() as cur:  # noqa: SIM117
                cur.execute("SELECT pg_backend_pid()")
                result2 = cur.fetchone()
                assert result2 is not None
                pid2 = result2[0]

            # Same PID means connection was reused
            assert pid1 == pid2
        finally:
            close_pool(pool)

    def test_pool_custom_size(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test pool respects custom min/max sizes."""
        from src.csv_postgres_pipeline.database import close_pool, create_pool
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(
            **db_connection_params,
            pool_min_size=2,
            pool_max_size=10,
        )
        pool = create_pool(db_config)

        try:
            assert pool.min_size == 2
            assert pool.max_size == 10
        finally:
            close_pool(pool)

    def test_pool_multiple_concurrent_connections(
        self,
        db_connection_params: Any,
    ) -> None:
        """Test pool can provide multiple concurrent connections."""
        from src.csv_postgres_pipeline.database import (
            close_pool,
            create_pool,
            get_pooled_connection,
        )
        from src.csv_postgres_pipeline.models import DatabaseConfig

        db_config = DatabaseConfig(
            **db_connection_params,
            pool_min_size=1,
            pool_max_size=3,
        )
        pool = create_pool(db_config)

        try:
            # Hold two connections simultaneously
            with (
                get_pooled_connection(pool) as conn1,
                get_pooled_connection(pool) as conn2,
            ):
                # Both should work independently
                with conn1.cursor() as cur1:
                    cur1.execute("SELECT 1")
                    result1 = cur1.fetchone()
                    assert result1 is not None
                    assert result1[0] == 1
                with conn2.cursor() as cur2:
                    cur2.execute("SELECT 2")
                    result2 = cur2.fetchone()
                    assert result2 is not None
                    assert result2[0] == 2
        finally:
            close_pool(pool)
