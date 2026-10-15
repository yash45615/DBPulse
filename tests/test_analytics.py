"""Tests for latency analytics."""

import pytest

from dbpulse.analytics import latency_summary, percentile


def test_percentile_calculations():
    values = tuple(float(value) for value in range(1, 101))

    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 99) == 99


def test_percentile_is_independent_of_input_order():
    assert percentile((100.0, 10.0, 30.0, 20.0), 50) == 20.0


def test_latency_summary():
    result = latency_summary((1.0, 2.0, 3.0, 4.0, 100.0))

    assert result["count"] == 5.0
    assert result["mean_ms"] == 22.0
    assert result["min_ms"] == 1.0
    assert result["max_ms"] == 100.0
    assert result["p50_ms"] == 3.0
    assert result["p95_ms"] == 100.0
    assert result["p99_ms"] == 100.0


@pytest.mark.parametrize(
    "percent",
    [-1, 101],
)
def test_invalid_percentile_is_rejected(percent):
    with pytest.raises(ValueError):
        percentile((1.0, 2.0), percent)


def test_empty_measurements_are_rejected():
    with pytest.raises(ValueError):
        latency_summary(())

    with pytest.raises(ValueError):
        percentile((), 50)
