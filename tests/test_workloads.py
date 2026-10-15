"""Tests for repeatable database workloads."""

import pytest
from sqlalchemy import func, select

from dbpulse.db import create_database_engine, initialize_schema
from dbpulse.models import WorkloadRecord
from dbpulse.workloads import run_workload, seed_dataset


@pytest.fixture
def engine(tmp_path):
    """Provide an isolated SQLite database for each test."""
    database_path = tmp_path / "workloads.db"
    test_engine = create_database_engine(f"sqlite:///{database_path}")
    initialize_schema(test_engine)
    yield test_engine
    test_engine.dispose()


def test_seed_dataset_creates_requested_records(engine):
    assert seed_dataset(engine, 20) == 20

    with engine.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(WorkloadRecord))

    assert count == 20


def test_seed_dataset_does_not_duplicate_existing_records(engine):
    seed_dataset(engine, 10)

    assert seed_dataset(engine, 10) == 10

    with engine.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(WorkloadRecord))

    assert count == 10


def test_read_workload_records_latency(engine):
    seed_dataset(engine, 10)

    result = run_workload(engine, "read", 5)

    assert result.workload == "read"
    assert result.iterations == 5
    assert result.reads == 5
    assert result.writes == 0
    assert len(result.latencies_ms) == 5
    assert all(latency >= 0 for latency in result.latencies_ms)


def test_write_workload_inserts_records(engine):
    result = run_workload(engine, "write", 4)

    assert result.reads == 0
    assert result.writes == 4

    with engine.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(WorkloadRecord))

    assert count == 4


def test_mixed_workload_uses_four_to_one_pattern(engine):
    seed_dataset(engine, 10)

    result = run_workload(engine, "mixed", 10)

    assert result.reads == 8
    assert result.writes == 2
    assert len(result.latencies_ms) == 10


@pytest.mark.parametrize(
    ("workload", "iterations"),
    [
        ("invalid", 5),
        ("read", 0),
        ("write", -1),
    ],
)
def test_invalid_workload_arguments_are_rejected(engine, workload, iterations):
    with pytest.raises(ValueError):
        run_workload(engine, workload, iterations)
