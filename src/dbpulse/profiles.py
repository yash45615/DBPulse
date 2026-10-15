"""Named, lightweight benchmark profiles for DBPulse."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BenchmarkProfile:
    """Workload parameters for a repeatable benchmark profile."""

    name: str
    iterations: int
    dataset_size: int
    description: str


PROFILES: dict[str, BenchmarkProfile] = {
    "smoke": BenchmarkProfile(
        name="smoke",
        iterations=20,
        dataset_size=100,
        description="Quick functional check with a small dataset.",
    ),
    "standard": BenchmarkProfile(
        name="standard",
        iterations=100,
        dataset_size=1000,
        description="Default local benchmark for routine comparisons.",
    ),
    "repeatable": BenchmarkProfile(
        name="repeatable",
        iterations=500,
        dataset_size=1000,
        description="Longer run for more stable latency distributions.",
    ),
}


def get_profile(name: str) -> BenchmarkProfile:
    """Return a named profile or raise a useful validation error."""
    normalized = name.strip().lower()

    try:
        return PROFILES[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise ValueError(
            f"Unknown benchmark profile {name!r}. Available profiles: {available}"
        ) from exc


def list_profiles() -> list[dict[str, object]]:
    """Return profile details suitable for display or JSON serialization."""
    return [asdict(PROFILES[name]) for name in sorted(PROFILES)]
