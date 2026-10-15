"""Compare benchmark runs and detect latency regressions."""

from dataclasses import dataclass

from dbpulse.analytics import latency_summary


@dataclass(frozen=True)
class MetricComparison:
    """Comparison of one latency metric between two runs."""

    metric: str
    baseline_ms: float
    candidate_ms: float
    change_percent: float
    regressed: bool


@dataclass(frozen=True)
class RegressionReport:
    """Result of comparing a baseline and candidate benchmark."""

    baseline_run_id: int
    candidate_run_id: int
    threshold_percent: float
    metrics: tuple[MetricComparison, ...]

    @property
    def has_regression(self) -> bool:
        """Return True when any measured metric exceeds the threshold."""
        return any(metric.regressed for metric in self.metrics)


def compare_latency_values(
    baseline_run_id: int,
    candidate_run_id: int,
    baseline_latencies: tuple[float, ...],
    candidate_latencies: tuple[float, ...],
    threshold_percent: float = 10.0,
) -> RegressionReport:
    """Compare latency distributions and identify regressions."""
    if baseline_run_id < 1 or candidate_run_id < 1:
        raise ValueError("Run IDs must be positive integers")

    if baseline_run_id == candidate_run_id:
        raise ValueError("Baseline and candidate run IDs must be different")

    if threshold_percent < 0:
        raise ValueError("Regression threshold cannot be negative")

    if not baseline_latencies or not candidate_latencies:
        raise ValueError("Both runs must contain latency measurements")

    if any(value < 0 for value in baseline_latencies + candidate_latencies):
        raise ValueError("Latency measurements cannot be negative")

    baseline = latency_summary(baseline_latencies)
    candidate = latency_summary(candidate_latencies)

    comparisons = []

    for key, label in (
        ("mean_ms", "mean"),
        ("p95_ms", "p95"),
        ("p99_ms", "p99"),
    ):
        before = baseline[key]
        after = candidate[key]

        if before == 0:
            change = 0.0 if after == 0 else float("inf")
        else:
            change = ((after - before) / before) * 100

        comparisons.append(
            MetricComparison(
                metric=label,
                baseline_ms=before,
                candidate_ms=after,
                change_percent=change,
                regressed=change > threshold_percent,
            )
        )

    return RegressionReport(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        threshold_percent=threshold_percent,
        metrics=tuple(comparisons),
    )
