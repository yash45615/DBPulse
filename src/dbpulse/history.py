"""Persistence and retrieval for benchmark history."""

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from dbpulse.models import BenchmarkMeasurement, BenchmarkRun
from dbpulse.workloads import WorkloadResult


def save_workload_result(
    engine: Engine,
    name: str,
    result: WorkloadResult,
    metadata: dict | None = None,
) -> int:
    """Persist a completed workload, its measurements, and its metadata."""
    if not name.strip():
        raise ValueError("Run name must not be empty")

    run_metadata = dict(metadata) if metadata is not None else {}

    with Session(engine) as session, session.begin():
        run = BenchmarkRun(
            name=name.strip(),
            workload=result.workload,
            status="completed",
            metadata_json=run_metadata,
        )
        session.add(run)
        session.flush()

        measurements = []

        for index, latency in enumerate(result.latencies_ms):
            is_write = result.workload == "write" or (
                result.workload == "mixed" and index % 5 == 4
            )

            measurements.append(
                BenchmarkMeasurement(
                    run_id=run.id,
                    operation_index=index + 1,
                    operation_type="write" if is_write else "read",
                    latency_ms=latency,
                )
            )

        session.add_all(measurements)
        session.flush()

        return run.id


def list_runs(engine: Engine, limit: int = 20) -> list[BenchmarkRun]:
    """Return the newest benchmark runs first."""
    if limit < 1:
        raise ValueError("Limit must be at least 1")

    with Session(engine) as session:
        runs = session.scalars(
            select(BenchmarkRun).order_by(BenchmarkRun.id.desc()).limit(limit)
        ).all()

        return list(runs)


def get_run_measurements(
    engine: Engine,
    run_id: int,
) -> tuple[BenchmarkRun, list[BenchmarkMeasurement]] | None:
    """Return a run and its measurements, or None if it doesn't exist."""
    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)

        if run is None:
            return None

        measurements = session.scalars(
            select(BenchmarkMeasurement)
            .where(BenchmarkMeasurement.run_id == run_id)
            .order_by(BenchmarkMeasurement.operation_index)
        ).all()

        return run, list(measurements)
