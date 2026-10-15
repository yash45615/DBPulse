"""Latency statistics for benchmark measurements."""

from math import ceil
from statistics import fmean


def percentile(values: tuple[float, ...], percent: float) -> float:
    """Return a nearest-rank percentile using a 1-based rank."""
    if not values:
        raise ValueError("At least one measurement is required")

    if not 0 <= percent <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    ordered = sorted(values)

    if percent == 0:
        return ordered[0]

    rank = ceil((percent / 100) * len(ordered))
    return ordered[max(0, rank - 1)]


def latency_summary(values: tuple[float, ...]) -> dict[str, float]:
    """Calculate common latency statistics in milliseconds."""
    if not values:
        raise ValueError("At least one measurement is required")

    return {
        "count": float(len(values)),
        "mean_ms": fmean(values),
        "min_ms": min(values),
        "max_ms": max(values),
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
    }
