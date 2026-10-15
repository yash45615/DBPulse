"""Generate and export structured benchmark comparison reports."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dbpulse.analytics import latency_summary
from dbpulse.regression import compare_latency_values


def build_comparison_report(
    baseline_run_id: int,
    candidate_run_id: int,
    baseline_name: str,
    candidate_name: str,
    workload: str,
    baseline_latencies: tuple[float, ...],
    candidate_latencies: tuple[float, ...],
    threshold_percent: float = 10.0,
) -> dict[str, Any]:
    """Build a JSON-serializable comparison report."""
    baseline_stats = latency_summary(baseline_latencies)
    candidate_stats = latency_summary(candidate_latencies)

    comparison = compare_latency_values(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        baseline_latencies=baseline_latencies,
        candidate_latencies=candidate_latencies,
        threshold_percent=threshold_percent,
    )

    metrics = []

    for metric in comparison.metrics:
        metrics.append(
            {
                "metric": metric.metric,
                "baseline_ms": metric.baseline_ms,
                "candidate_ms": metric.candidate_ms,
                "change_percent": (
                    metric.change_percent
                    if metric.change_percent != float("inf")
                    else None
                ),
                "change_display": (
                    "+infinity%"
                    if metric.change_percent == float("inf")
                    else f"{metric.change_percent:+.2f}%"
                ),
                "regressed": metric.regressed,
            }
        )

    return {
        "report_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "workload": workload,
        "threshold_percent": threshold_percent,
        "baseline": {
            "run_id": baseline_run_id,
            "name": baseline_name,
            "statistics": baseline_stats,
        },
        "candidate": {
            "run_id": candidate_run_id,
            "name": candidate_name,
            "statistics": candidate_stats,
        },
        "comparison": {
            "has_regression": comparison.has_regression,
            "metrics": metrics,
        },
    }


def write_json_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a comparison report to a JSON file."""
    destination = Path(output_path)

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, allow_nan=False)
        report_file.write("\n")

    return destination
