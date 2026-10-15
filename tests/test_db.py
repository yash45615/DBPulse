"""Tests for database connectivity and schema initialization."""

import pytest
from sqlalchemy import inspect

from dbpulse.db import (
    check_database_connection,
    create_database_engine,
    initialize_schema,
)


def test_sqlite_connection_health() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    try:
        assert check_database_connection(engine) is True
    finally:
        engine.dispose()


def test_schema_initialization_creates_benchmark_table(
    tmp_path,
) -> None:
    database_path = tmp_path / "test.db"
    engine = create_database_engine(f"sqlite:///{database_path}")

    try:
        initialize_schema(engine)

        table_names = inspect(engine).get_table_names()
        assert "benchmark_runs" in table_names
    finally:
        engine.dispose()


def test_schema_initialization_is_repeatable(tmp_path) -> None:
    database_path = tmp_path / "repeatable.db"
    engine = create_database_engine(f"sqlite:///{database_path}")

    try:
        initialize_schema(engine)
        initialize_schema(engine)

        assert "benchmark_runs" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_empty_database_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        create_database_engine("")
