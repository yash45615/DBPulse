"""Tests for benchmark history persistence."""

import pytest
from sqlalchemy import func, select

from dbpulse.db import create_database_engine, initialize_schema
from dbpulse.history import (
    get_run_measurements,
    list_runs,
    save_workload_result,
)
from dbpulse.models import BenchmarkMeasurement
from dbpulse.workloads import run_workload, seed_dataset


@pytest.fixture
def engine(tmp_path):
    database_path = tmp_path / "history.db"
    test_engine = create_database_engine(f"sqlite:///{database_path}")
    initialize_schema(test_engine)
    yield test_engine
    test_engine.dispose()


def test_save_and_retrieve_read_run(engine):
    seed_dataset(engine, 10)
    result = run_workload(engine, "read", 5)

    run_id = save_workload_result(engine, "read-test", result)
    retrieved = get_run_measurements(engine, run_id)

    assert retrieved is not None
    run, measurements = retrieved
    assert run.name == "read-test"
    assert run.workload == "read"
    assert run.status == "completed"
    assert len(measurements) == 5
    assert all(item.operation_type == "read" for item in measurements)


def test_mixed_run_saves_operation_types(engine):
    seed_dataset(engine, 10)
    result = run_workload(engine, "mixed", 10)

    run_id = save_workload_result(engine, "mixed-test", result)
    retrieved = get_run_measurements(engine, run_id)

    assert retrieved is not None
    _, measurements = retrieved
    assert sum(item.operation_type == "read" for item in measurements) == 8
    assert sum(item.operation_type == "write" for item in measurements) == 2


def test_list_runs_returns_newest_first(engine):
    seed_dataset(engine, 10)

    first = save_workload_result(engine, "first", run_workload(engine, "read", 2))
    second = save_workload_result(engine, "second", run_workload(engine, "write", 2))

    runs = list_runs(engine)

    assert [run.id for run in runs[:2]] == [second, first]


def test_missing_run_returns_none(engine):
    assert get_run_measurements(engine, 9999) is None


def test_saved_measurement_count_matches_operations(engine):
    seed_dataset(engine, 10)
    result = run_workload(engine, "mixed", 15)
    run_id = save_workload_result(engine, "count-test", result)

    with engine.connect() as connection:
        count = connection.scalar(
            select(func.count())
            .select_from(BenchmarkMeasurement)
            .where(BenchmarkMeasurement.run_id == run_id)
        )

    assert count == 15


def test_empty_run_name_is_rejected(engine):
    result = run_workload(engine, "read", 1)

    with pytest.raises(ValueError, match="Run name"):
        save_workload_result(engine, "  ", result)


def test_history_limit_must_be_positive(engine):
    with pytest.raises(ValueError, match="Limit"):
        list_runs(engine, limit=0)


def test_each_run_is_stored_as_completed(engine):
    result = run_workload(engine, "read", 1)
    run_id = save_workload_result(engine, "completed-test", result)

    runs = list_runs(engine)
    assert any(run.id == run_id and run.status == "completed" for run in runs)
    assert runs[0].status == "completed"
    assert runs[0].id == run_id
    assert runs[0].name == "completed-test"


def test_run_metadata_is_saved_and_retrieved(engine):
    """A benchmark's metadata should survive a database round trip."""
    result = run_workload(engine, "read", 3)

    metadata = {
        "profile": {"name": "smoke"},
        "workload": {
            "type": "read",
            "iterations": 3,
            "dataset_size": 10,
        },
    }

    run_id = save_workload_result(
        engine,
        "metadata-test",
        result,
        metadata=metadata,
    )

    retrieved = get_run_measurements(engine, run_id)

    assert retrieved is not None
    run, measurements = retrieved
    assert run.metadata_json == metadata
    assert len(measurements) == 3


def test_run_without_metadata_uses_empty_dictionary(engine):
    """Older call sites that omit metadata should remain compatible."""
    result = run_workload(engine, "read", 2)

    run_id = save_workload_result(
        engine,
        "metadata-default-test",
        result,
    )

    retrieved = get_run_measurements(engine, run_id)

    assert retrieved is not None
    run, _ = retrieved
    assert run.metadata_json == {}


def test_metadata_migration_is_repeatable(engine):
    """Running the migration twice should not fail."""
    from sqlalchemy import inspect

    from dbpulse.db import migrate_benchmark_run_metadata

    migrate_benchmark_run_metadata(engine)
    migrate_benchmark_run_metadata(engine)

    columns = {
        column["name"] for column in inspect(engine).get_columns("benchmark_runs")
    }

    assert "metadata_json" in columns
