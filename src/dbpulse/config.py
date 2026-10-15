"""Configuration loading and validation for DBPulse."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    name: str
    environment: str


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    pool_size: int


@dataclass(frozen=True)
class BenchmarkConfig:
    default_workload: str
    iterations: int
    warmup_iterations: int
    concurrency: int
    dataset_size: int


@dataclass(frozen=True)
class RegressionConfig:
    latency_threshold_percent: float
    minimum_samples: int


@dataclass(frozen=True)
class ReportsConfig:
    output_dir: str


@dataclass(frozen=True)
class DBPulseConfig:
    app: AppConfig
    database: DatabaseConfig
    benchmark: BenchmarkConfig
    regression: RegressionConfig
    reports: ReportsConfig


def _require_keys(
    data: dict,
    required: set[str],
    section: str,
) -> None:
    missing = required - data.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Missing configuration keys in [{section}]: {names}")


def load_config(path: str | Path = "config/dbpulse.toml") -> DBPulseConfig:
    """Load and validate DBPulse settings from a TOML file."""
    config_path = Path(path)

    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    sections = {
        "app": {"name", "environment"},
        "database": {"url", "pool_size"},
        "benchmark": {
            "default_workload",
            "iterations",
            "warmup_iterations",
            "concurrency",
            "dataset_size",
        },
        "regression": {
            "latency_threshold_percent",
            "minimum_samples",
        },
        "reports": {"output_dir"},
    }

    for section, required in sections.items():
        value = raw.get(section)
        if not isinstance(value, dict):
            raise ValueError(f"Missing or invalid [{section}] section")
        _require_keys(value, required, section)

    app = AppConfig(**raw["app"])
    database = DatabaseConfig(**raw["database"])
    benchmark = BenchmarkConfig(**raw["benchmark"])
    regression = RegressionConfig(**raw["regression"])
    reports = ReportsConfig(**raw["reports"])

    if not app.name.strip():
        raise ValueError("app.name must not be empty")

    if not app.environment.strip():
        raise ValueError("app.environment must not be empty")

    if not database.url.strip():
        raise ValueError("database.url must not be empty")

    if database.pool_size < 1:
        raise ValueError("database.pool_size must be at least 1")

    if benchmark.default_workload not in {"read", "write", "mixed"}:
        raise ValueError("benchmark.default_workload must be read, write, or mixed")

    if benchmark.iterations < 1:
        raise ValueError("benchmark.iterations must be at least 1")

    if benchmark.warmup_iterations < 0:
        raise ValueError("benchmark.warmup_iterations cannot be negative")

    if benchmark.concurrency < 1:
        raise ValueError("benchmark.concurrency must be at least 1")

    if benchmark.dataset_size < 1:
        raise ValueError("benchmark.dataset_size must be at least 1")

    if regression.latency_threshold_percent < 0:
        raise ValueError("regression.latency_threshold_percent cannot be negative")

    if regression.minimum_samples < 1:
        raise ValueError("regression.minimum_samples must be at least 1")

    if not reports.output_dir.strip():
        raise ValueError("reports.output_dir must not be empty")

    return DBPulseConfig(
        app=app,
        database=database,
        benchmark=benchmark,
        regression=regression,
        reports=reports,
    )
