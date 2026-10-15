"""Tests for structured benchmark reports."""

import json

from dbpulse.reports import build_comparison_report, write_json_report


def make_report():
    """Build a representative comparison report for testing."""
    return build_comparison_report(
        baseline_run_id=10,
        candidate_run_id=11,
        baseline_name="baseline",
        candidate_name="candidate",
        workload="read",
        baseline_latencies=(10.0, 12.0, 14.0, 16.0, 18.0),
        candidate_latencies=(12.0, 14.0, 16.0, 18.0, 20.0),
        threshold_percent=10.0,
    )


def test_report_contains_run_details_and_statistics():
    report = make_report()

    assert report["report_version"] == 1
    assert report["workload"] == "read"
    assert report["baseline"]["run_id"] == 10
    assert report["candidate"]["run_id"] == 11
    assert report["baseline"]["statistics"]["count"] == 5.0
    assert "p95_ms" in report["candidate"]["statistics"]


def test_report_detects_regression():
    report = make_report()

    assert report["comparison"]["has_regression"] is True

    mean = next(
        metric
        for metric in report["comparison"]["metrics"]
        if metric["metric"] == "mean"
    )
    assert mean["regressed"] is True
    assert mean["change_percent"] > 10.0


def test_report_can_be_written_and_read_as_json(tmp_path):
    report = make_report()
    output = tmp_path / "nested" / "comparison.json"

    saved_path = write_json_report(report, output)

    assert saved_path.exists()

    with saved_path.open(encoding="utf-8") as report_file:
        loaded = json.load(report_file)

    assert loaded["workload"] == "read"
    assert loaded["comparison"]["has_regression"] is True


def test_zero_baseline_is_json_safe(tmp_path):
    report = build_comparison_report(
        baseline_run_id=1,
        candidate_run_id=2,
        baseline_name="zero-baseline",
        candidate_name="positive-candidate",
        workload="read",
        baseline_latencies=(0.0, 0.0, 0.0),
        candidate_latencies=(1.0, 2.0, 3.0),
        threshold_percent=10.0,
    )

    output = tmp_path / "zero-baseline.json"
    write_json_report(report, output)

    mean = next(
        metric
        for metric in report["comparison"]["metrics"]
        if metric["metric"] == "mean"
    )

    assert mean["change_percent"] is None
    assert mean["change_display"] == "+infinity%"

    with output.open(encoding="utf-8") as report_file:
        json.load(report_file)
