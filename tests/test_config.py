"""Tests for DBPulse configuration loading."""

import pytest

from dbpulse.config import load_config

CONFIG_PATH = "config/dbpulse.toml"


def test_load_default_configuration() -> None:
    config = load_config(CONFIG_PATH)

    assert config.app.name == "DBPulse"
    assert config.app.environment == "local"
    assert config.benchmark.default_workload == "read"
    assert config.benchmark.iterations == 100
    assert config.benchmark.warmup_iterations == 10
    assert config.regression.latency_threshold_percent == 10.0


def test_configuration_file_must_exist(tmp_path) -> None:
    missing = tmp_path / "missing.toml"

    with pytest.raises(FileNotFoundError):
        load_config(missing)


def test_invalid_workload_is_rejected(tmp_path) -> None:
    config_file = tmp_path / "invalid.toml"
    config_file.write_text(
        """
[app]
name = "DBPulse"
environment = "test"

[database]
url = "sqlite:///test.db"
pool_size = 5

[benchmark]
default_workload = "unknown"
iterations = 10
warmup_iterations = 1
concurrency = 1
dataset_size = 100

[regression]
latency_threshold_percent = 10.0
minimum_samples = 5

[reports]
output_dir = "reports"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="default_workload"):
        load_config(config_file)


def test_negative_warmup_is_rejected(tmp_path) -> None:
    config_file = tmp_path / "invalid.toml"
    config_file.write_text(
        """
[app]
name = "DBPulse"
environment = "test"

[database]
url = "sqlite:///test.db"
pool_size = 5

[benchmark]
default_workload = "read"
iterations = 10
warmup_iterations = -1
concurrency = 1
dataset_size = 100

[regression]
latency_threshold_percent = 10.0
minimum_samples = 5

[reports]
output_dir = "reports"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="warmup_iterations"):
        load_config(config_file)
