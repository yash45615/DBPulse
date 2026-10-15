"""Repeatable read, write, and mixed database workloads."""

from dataclasses import dataclass
from time import perf_counter_ns

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from dbpulse.models import WorkloadRecord


@dataclass(frozen=True)
class WorkloadResult:
    """Measurements collected from one workload execution."""

    workload: str
    iterations: int
    reads: int
    writes: int
    latencies_ms: tuple[float, ...]

    @property
    def total_duration_ms(self) -> float:
        """Return the sum of measured operation durations."""
        return sum(self.latencies_ms)

    @property
    def average_latency_ms(self) -> float:
        """Return average operation latency."""
        return self.total_duration_ms / len(self.latencies_ms)

    @property
    def min_latency_ms(self) -> float:
        """Return minimum operation latency."""
        return min(self.latencies_ms)

    @property
    def max_latency_ms(self) -> float:
        """Return maximum operation latency."""
        return max(self.latencies_ms)


def seed_dataset(engine: Engine, dataset_size: int) -> int:
    """Ensure the table contains at least dataset_size records."""
    if dataset_size < 1:
        raise ValueError("Dataset size must be at least 1")

    with engine.begin() as connection:
        current_count = connection.scalar(
            select(func.count()).select_from(WorkloadRecord)
        )
        missing = max(0, dataset_size - int(current_count or 0))

        if missing:
            connection.execute(
                WorkloadRecord.__table__.insert(),
                [
                    {
                        "category": f"category-{index % 5}",
                        "payload": f"DBPulse synthetic benchmark record {index}",
                    }
                    for index in range(missing)
                ],
            )

        return int(current_count or 0) + missing


def run_workload(
    engine: Engine,
    workload: str,
    iterations: int,
) -> WorkloadResult:
    """Execute a read, write, or mixed workload and record operation latency."""
    supported = {"read", "write", "mixed"}

    if workload not in supported:
        raise ValueError(
            f"Unsupported workload {workload!r}. "
            f"Choose from: {', '.join(sorted(supported))}"
        )

    if iterations < 1:
        raise ValueError("Iterations must be at least 1")

    latencies: list[float] = []
    reads = 0
    writes = 0

    for index in range(iterations):
        # Mixed workload: four reads followed by one write.
        is_write = workload == "write" or (workload == "mixed" and index % 5 == 4)

        started = perf_counter_ns()

        with engine.begin() as connection:
            if is_write:
                connection.execute(
                    WorkloadRecord.__table__.insert().values(
                        category=f"generated-{index % 5}",
                        payload=f"DBPulse generated record {index}",
                    )
                )
                writes += 1
            else:
                connection.execute(
                    select(WorkloadRecord.id).order_by(WorkloadRecord.id).limit(1)
                ).first()
                reads += 1

        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        latencies.append(elapsed_ms)

    return WorkloadResult(
        workload=workload,
        iterations=iterations,
        reads=reads,
        writes=writes,
        latencies_ms=tuple(latencies),
    )
