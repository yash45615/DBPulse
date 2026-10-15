"""Tests for latency regression detection."""

import pytest

from dbpulse.regression import compare_latency_values


def test_detects_regression_above_threshold():
    report = compare_latency_values(
        1,
        2,
        (10.0,) * 100,
        (12.0,) * 100,
        threshold_percent=10.0,
    )

    assert report.has_regression
    assert all(metric.regressed for metric in report.metrics)


def test_does_not_flag_change_within_threshold():
    report = compare_latency_values(
        1,
        2,
        (10.0,) * 100,
        (10.5,) * 100,
        threshold_percent=10.0,
    )

    assert not report.has_regression


def test_detects_regression_in_tail_latency():
    # Make the slowest 10% of operations visible at P95.
    baseline = (10.0,) * 90 + (20.0,) * 10
    candidate = (10.0,) * 90 + (30.0,) * 10

    report = compare_latency_values(
        1,
        2,
        baseline,
        candidate,
        threshold_percent=10.0,
    )

    p95 = next(metric for metric in report.metrics if metric.metric == "p95")

    assert p95.baseline_ms == 20.0
    assert p95.candidate_ms == 30.0
    assert p95.change_percent == 50.0
    assert p95.regressed
    assert report.has_regression


@pytest.mark.parametrize(
    ("baseline_id", "candidate_id", "threshold"),
    [
        (0, 2, 10.0),
        (1, 1, 10.0),
        (1, 2, -1.0),
    ],
)
def test_invalid_comparison_arguments_are_rejected(
    baseline_id, candidate_id, threshold
):
    with pytest.raises(ValueError):
        compare_latency_values(
            baseline_id,
            candidate_id,
            (10.0, 20.0),
            (11.0, 21.0),
            threshold,
        )


def test_empty_measurements_are_rejected():
    with pytest.raises(ValueError):
        compare_latency_values(1, 2, (), (10.0,))


def test_negative_latency_is_rejected():
    with pytest.raises(ValueError):
        compare_latency_values(1, 2, (-1.0,), (10.0,))
